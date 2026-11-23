mod compact;
mod filter;
mod lowercase;
mod preflight;
mod request;
mod sha256;

use arrow_array::*;
use arrow_schema::{DataType, Schema, TimeUnit};
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use parquet::file::reader::FileReader;
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, OpenOptions};
use std::io::{self, BufWriter, Write};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::PathBuf;
use std::process::ExitCode;

const MAX_INPUT: u64 = 512 * 1024 * 1024;
const MAX_OUTPUT: u64 = 2 * 1024 * 1024 * 1024;
const MAX_MEMORY: u64 = 1024 * 1024 * 1024;

#[derive(Debug)]
enum Error {
    Arguments,
    Input,
    Limit,
    Io,
    Validation,
    NoRows,
    FilterLimit,
}
impl Error {
    fn details(&self) -> (u8, &'static str) {
        match self {
            Self::Arguments => (2, "arguments"),
            Self::Input => (3, "input_rejected"),
            Self::Limit => (4, "resource_limit"),
            Self::Io => (5, "io_error"),
            Self::Validation => (6, "validation_error"),
            Self::NoRows => (7, "no_rows_matched_filter"),
            Self::FilterLimit => (8, "parquet_filter_row_limit_exceeded"),
        }
    }
}
struct Config {
    root: PathBuf,
    memory: u64,
    cpu: u64,
    output: u64,
    parent: u64,
    admission: u64,
    wall: u64,
}
fn args() -> Result<Config, Error> {
    let mut values = BTreeMap::new();
    let mut args = std::env::args().skip(1);
    while let Some(key) = args.next() {
        if ![
            "--request-root",
            "--max-memory-bytes",
            "--max-cpu-seconds",
            "--max-output-bytes",
            "--parent-pid",
            "--admission-fd",
            "--max-wall-seconds",
        ]
        .contains(&key.as_str())
            || values.contains_key(&key)
        {
            return Err(Error::Arguments);
        }
        values.insert(key, args.next().ok_or(Error::Arguments)?);
    }
    let number = |name: &str, ceiling: u64| -> Result<u64, Error> {
        let raw = values.get(name).ok_or(Error::Arguments)?;
        if !raw.bytes().all(|b| b.is_ascii_digit()) {
            return Err(Error::Arguments);
        }
        let n: u64 = raw.parse().map_err(|_| Error::Arguments)?;
        if n == 0 || n > ceiling {
            return Err(Error::Arguments);
        }
        Ok(n)
    };
    Ok(Config {
        root: PathBuf::from(values.get("--request-root").ok_or(Error::Arguments)?),
        memory: number("--max-memory-bytes", MAX_MEMORY)?,
        cpu: number("--max-cpu-seconds", 120)?,
        output: number("--max-output-bytes", MAX_OUTPUT)?,
        parent: number("--parent-pid", i32::MAX as u64)?,
        admission: number("--admission-fd", i32::MAX as u64)?,
        wall: number("--max-wall-seconds", 180)?,
    })
}
fn set_limits(c: &Config) -> Result<(), Error> {
    // SAFETY: prctl installs termination for this child only; expected PID closes
    // the race where its parent exits before PR_SET_PDEATHSIG is installed.
    unsafe {
        libc::alarm(c.wall as u32);
        if libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGKILL) != 0
            || libc::getppid() as u64 != c.parent
            || libc::fcntl(c.admission as i32, libc::F_GETFD) < 0
        {
            return Err(Error::Arguments);
        }
    }

    for (kind, value) in [
        (libc::RLIMIT_CORE, 0),
        (libc::RLIMIT_AS, c.memory),
        (libc::RLIMIT_CPU, c.cpu),
        (libc::RLIMIT_FSIZE, c.output),
        (libc::RLIMIT_NOFILE, 64),
    ] {
        let limit = libc::rlimit {
            rlim_cur: value,
            rlim_max: value,
        };
        // SAFETY: valid pointer to an initialized rlimit; changes only this child.
        if unsafe { libc::setrlimit(kind, &limit) } != 0 {
            return Err(Error::Limit);
        }
    }
    Ok(())
}

struct Limited<W> {
    inner: W,
    bytes: u64,
    max: u64,
}
impl<W: Write> Write for Limited<W> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        if buf.len() as u64 > self.max.saturating_sub(self.bytes) {
            return Err(io::Error::new(io::ErrorKind::FileTooLarge, "output limit"));
        }
        let n = self.inner.write(buf)?;
        self.bytes += n as u64;
        Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}
fn output_error(e: io::Error) -> Error {
    if e.kind() == io::ErrorKind::FileTooLarge {
        Error::Limit
    } else {
        Error::Io
    }
}
// Production Python 3.12 csv.writer quotes comma, quote, LF and CR.
fn record<W: Write>(w: &mut W, cells: &[String]) -> io::Result<()> {
    for (i, s) in cells.iter().enumerate() {
        if i > 0 {
            w.write_all(b",")?;
        }
        let quote = (cells.len() == 1 && s.is_empty())
            || s.bytes().any(|b| matches!(b, b',' | b'"' | b'\n' | b'\r'));
        if quote {
            w.write_all(b"\"")?;
            let mut start = 0;
            for (j, b) in s.bytes().enumerate() {
                if b == b'"' {
                    w.write_all(&s.as_bytes()[start..=j])?;
                    w.write_all(b"\"")?;
                    start = j + 1;
                }
            }
            w.write_all(&s.as_bytes()[start..])?;
            w.write_all(b"\"")?;
        } else {
            w.write_all(s.as_bytes())?;
        }
    }
    w.write_all(b"\n")
}
fn python_float(x: f64) -> String {
    if x.is_nan() {
        return String::new();
    }
    if x == f64::INFINITY {
        return "inf".into();
    }
    if x == f64::NEG_INFINITY {
        return "-inf".into();
    }
    if x == 0.0 {
        return if x.is_sign_negative() { "-0.0" } else { "0.0" }.into();
    }
    let mut buffer = ryu::Buffer::new();
    let raw = buffer.format_finite(x);
    let negative = raw.starts_with('-');
    let raw = raw.trim_start_matches('-');
    let (mantissa, exp) = raw
        .split_once('e')
        .map(|(m, e)| (m, e.parse::<i32>().unwrap()))
        .unwrap_or((raw, 0));
    let decimal = mantissa.find('.').unwrap_or(mantissa.len()) as i32;
    let all = mantissa.replace('.', "");
    let lead = all.bytes().take_while(|b| *b == b'0').count();
    let digits = all[lead..].trim_end_matches('0');
    let exponent = decimal + exp - lead as i32 - 1;
    let mut out = if negative {
        "-".to_owned()
    } else {
        String::new()
    };
    if !(-4..16).contains(&exponent) {
        out.push_str(&digits[..1]);
        if digits.len() > 1 {
            out.push('.');
            out.push_str(&digits[1..]);
        }
        out.push_str(&format!("e{:+03}", exponent));
    } else if exponent < 0 {
        out.push_str("0.");
        out.push_str(&"0".repeat((-exponent - 1) as usize));
        out.push_str(digits);
    } else {
        let split = (exponent + 1) as usize;
        if digits.len() <= split {
            out.push_str(digits);
            out.push_str(&"0".repeat(split - digits.len()));
            out.push_str(".0");
        } else {
            out.push_str(&digits[..split]);
            out.push('.');
            out.push_str(&digits[split..]);
        }
    }
    out
}
fn supported(t: &DataType) -> bool {
    matches!(
        t,
        DataType::Null
            | DataType::Binary
            | DataType::LargeBinary
            | DataType::Timestamp(_, None)
            | DataType::Int8
            | DataType::Int16
            | DataType::Int32
            | DataType::Int64
            | DataType::UInt8
            | DataType::UInt16
            | DataType::UInt32
            | DataType::UInt64
            | DataType::Float32
            | DataType::Float64
            | DataType::Boolean
            | DataType::Utf8
            | DataType::LargeUtf8
    )
}
fn columns(schema: &Schema, filtered: bool) -> Result<(Vec<usize>, Vec<String>), Error> {
    let mut indices = BTreeSet::from(["__index_level_0__".to_owned()]);
    let pandas = match schema.metadata().get("pandas") {
        None => None,
        Some(raw) => match serde_json::from_str::<Value>(raw) {
            Ok(value) => Some(value),
            Err(error) => {
                // These pinned-serde parser limits are not malformed syntax.
                // Ignoring them could expose an otherwise omitted index field.
                let message = error.to_string();
                if message.starts_with("recursion limit exceeded")
                    || message.starts_with("number out of range")
                {
                    return Err(Error::Input);
                }
                None
            }
        },
    };
    if let Some(value) = pandas {
        if !value.is_object() || value.get("index_columns").is_some_and(|v| !v.is_array()) {
            return Err(Error::Input);
        }
        if let Some(items) = value.get("index_columns").and_then(Value::as_array) {
            for item in items {
                if let Some(name) = item
                    .as_str()
                    .or_else(|| item.get("name").and_then(Value::as_str))
                {
                    indices.insert(name.to_owned());
                }
            }
        }
    }
    let mut selected = Vec::new();
    let mut labels = Vec::new();
    let input_names: Vec<String> = if filtered {
        filter::names(schema)?
    } else {
        schema.fields().iter().map(|f| f.name().clone()).collect()
    };
    if !filtered && input_names.iter().collect::<BTreeSet<_>>().len() != input_names.len() {
        return Err(Error::Input);
    }
    for (i, physical) in schema.fields().iter().enumerate() {
        let name = &input_names[i];
        let f = schema.fields().iter().rev().find(|f| f.name() == name);
        // Index metadata controls presentation, never input trust. The reader
        // decodes every physical field, so validate even omitted columns.
        if !supported(physical.data_type())
            || physical
                .metadata()
                .get("ARROW:extension:name")
                .is_some_and(|v| {
                    v != "geoarrow.wkb"
                        || !matches!(
                            physical.data_type(),
                            DataType::Binary | DataType::LargeBinary
                        )
                })
        {
            return Err(Error::Input);
        }
        if indices.contains(name) {
            continue;
        }
        let mut label = name.clone();
        if let Some(units) = f
            .and_then(|field| field.metadata().get("units"))
            .map(|s| {
                s.trim_matches(|c: char| c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c))
            })
            .filter(|s| !s.is_empty())
        {
            let suffix = format!("({units})");
            if !label.contains(&suffix) {
                label.push(' ');
                label.push_str(&suffix);
            }
        }
        selected.push(i);
        labels.push(label);
    }
    // Python to_pylist dictionaries repeat the last value for duplicate labels.
    for i in 0..selected.len() {
        let last = labels
            .iter()
            .rposition(|label| label == &labels[i])
            .unwrap();
        selected[i] = selected[last];
    }
    Ok((selected, labels))
}
fn cell(a: &dyn Array, row: usize) -> String {
    if a.is_null(row) {
        return String::new();
    }
    macro_rules! num {
        ($t:ty) => {
            a.as_any()
                .downcast_ref::<$t>()
                .unwrap()
                .value(row)
                .to_string()
        };
    }
    match a.data_type() {
        DataType::Null => String::new(),
        DataType::Binary => {
            python_bytes(a.as_any().downcast_ref::<BinaryArray>().unwrap().value(row))
        }
        DataType::LargeBinary => python_bytes(
            a.as_any()
                .downcast_ref::<LargeBinaryArray>()
                .unwrap()
                .value(row),
        ),
        DataType::Timestamp(_, None) => timestamp(a, row, true),
        DataType::Int8 => num!(Int8Array),
        DataType::Int16 => num!(Int16Array),
        DataType::Int32 => num!(Int32Array),
        DataType::Int64 => num!(Int64Array),
        DataType::UInt8 => num!(UInt8Array),
        DataType::UInt16 => num!(UInt16Array),
        DataType::UInt32 => num!(UInt32Array),
        DataType::UInt64 => num!(UInt64Array),
        DataType::Float32 => python_float(
            a.as_any()
                .downcast_ref::<Float32Array>()
                .unwrap()
                .value(row) as f64,
        ),
        DataType::Float64 => python_float(
            a.as_any()
                .downcast_ref::<Float64Array>()
                .unwrap()
                .value(row),
        ),
        DataType::Boolean => if a
            .as_any()
            .downcast_ref::<BooleanArray>()
            .unwrap()
            .value(row)
        {
            "True"
        } else {
            "False"
        }
        .into(),
        DataType::Utf8 => a
            .as_any()
            .downcast_ref::<StringArray>()
            .unwrap()
            .value(row)
            .to_owned(),
        DataType::LargeUtf8 => a
            .as_any()
            .downcast_ref::<LargeStringArray>()
            .unwrap()
            .value(row)
            .to_owned(),
        _ => unreachable!("schema checked before conversion"),
    }
}
fn timestamp(a: &dyn Array, row: usize, nat: bool) -> String {
    let DataType::Timestamp(unit, None) = a.data_type() else {
        unreachable!("checked timestamp type")
    };
    if nat
        && *unit == TimeUnit::Nanosecond
        && a.as_any()
            .downcast_ref::<TimestampNanosecondArray>()
            .unwrap()
            .value(row)
            == i64::MIN
    {
        return "NaT".into();
    }

    let (value, scale) = match unit {
        TimeUnit::Second => (
            a.as_any()
                .downcast_ref::<TimestampSecondArray>()
                .unwrap()
                .value(row),
            1i64,
        ),
        TimeUnit::Millisecond => (
            a.as_any()
                .downcast_ref::<TimestampMillisecondArray>()
                .unwrap()
                .value(row),
            1000,
        ),
        TimeUnit::Microsecond => (
            a.as_any()
                .downcast_ref::<TimestampMicrosecondArray>()
                .unwrap()
                .value(row),
            1_000_000,
        ),
        TimeUnit::Nanosecond => (
            a.as_any()
                .downcast_ref::<TimestampNanosecondArray>()
                .unwrap()
                .value(row),
            1_000_000_000,
        ),
    };
    let nanos = (value.rem_euclid(scale) * (1_000_000_000 / scale)) as u32;
    let dt = chrono::DateTime::from_timestamp(value.div_euclid(scale), nanos)
        .expect("validated timestamp range");
    let mut out = dt.format("%Y-%m-%d %H:%M:%S").to_string();
    if nanos != 0 {
        if nanos % 1000 == 0 {
            out.push_str(&format!(".{:06}", nanos / 1000));
        } else {
            out.push_str(&format!(".{nanos:09}"));
        }
    }
    out
}
fn python_bytes(bytes: &[u8]) -> String {
    let quote = if bytes.contains(&b'\'') && !bytes.contains(&b'"') {
        b'"'
    } else {
        b'\''
    };
    let mut s = String::from("b");
    s.push(quote as char);
    for &b in bytes {
        match b {
            b'\\' => s.push_str("\\\\"),
            b'\n' => s.push_str("\\n"),
            b'\r' => s.push_str("\\r"),
            b'\t' => s.push_str("\\t"),
            b if b == quote => {
                s.push('\\');
                s.push(b as char);
            }
            32..=126 => s.push(b as char),
            _ => s.push_str(&format!("\\x{b:02x}")),
        }
    }
    s.push(quote as char);
    s
}
fn validate_batch(batch: &RecordBatch) -> Result<(), Error> {
    for column in batch.columns() {
        if let DataType::Timestamp(unit, None) = column.data_type() {
            for row in 0..column.len() {
                if column.is_null(row) {
                    continue;
                }
                let seconds = match unit {
                    TimeUnit::Second => column
                        .as_any()
                        .downcast_ref::<TimestampSecondArray>()
                        .unwrap()
                        .value(row),
                    TimeUnit::Millisecond => column
                        .as_any()
                        .downcast_ref::<TimestampMillisecondArray>()
                        .unwrap()
                        .value(row)
                        .div_euclid(1000),
                    TimeUnit::Microsecond => column
                        .as_any()
                        .downcast_ref::<TimestampMicrosecondArray>()
                        .unwrap()
                        .value(row)
                        .div_euclid(1_000_000),
                    TimeUnit::Nanosecond => column
                        .as_any()
                        .downcast_ref::<TimestampNanosecondArray>()
                        .unwrap()
                        .value(row)
                        .div_euclid(1_000_000_000),
                };
                // Python datetime's supported years are 1..=9999. Check omitted
                // fields too, before filtering or presentation can access values.
                if !(-62_135_596_800..=253_402_300_799).contains(&seconds) {
                    return Err(Error::Input);
                }
            }
        }
    }
    Ok(())
}
fn run(c: Config) -> Result<Value, Error> {
    set_limits(&c)?;
    let meta = fs::symlink_metadata(&c.root).map_err(|_| Error::Io)?;
    // SAFETY: geteuid has no arguments and only reads process identity.
    if !meta.is_dir() || meta.uid() != unsafe { libc::geteuid() } || meta.mode() & 0o077 != 0 {
        return Err(Error::Input);
    }
    let source = preflight::open(&c.root, &c.root.join("input.parquet"), MAX_INPUT)
        .map_err(|_| Error::Input)?;
    let builder =
        ParquetRecordBatchReaderBuilder::try_new(source.source.try_clone().map_err(|_| Error::Io)?)
            .map_err(|_| Error::Input)?;
    let filter = filter::Filter::parse(&request::read(&c.root)?, builder.schema())?;
    let (selected, labels) = columns(builder.schema(), filter.is_some())?;
    let reader = builder
        .with_batch_size(8192)
        .build()
        .map_err(|_| Error::Input)?;
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .custom_flags(libc::O_NOFOLLOW)
        .open(c.root.join("output.csv"))
        .map_err(|_| Error::Io)?;
    let mut writer = BufWriter::with_capacity(
        65536,
        Limited {
            inner: file,
            bytes: 0,
            max: c.output,
        },
    );
    record(&mut writer, &labels).map_err(output_error)?;
    let mut rows = 0u64;
    let mut decoded_rows = 0u64;
    let mut matched_rows = 0u64;
    let mut cells = Vec::with_capacity(selected.len());
    for batch in reader {
        let batch = batch.map_err(|_| Error::Input)?;
        validate_batch(&batch)?;
        for row in 0..batch.num_rows() {
            decoded_rows += 1;
            if filter.as_ref().is_some_and(|f| !f.matches(&batch, row)) {
                continue;
            }
            matched_rows += 1;
            if filter.is_some() && matched_rows > 2_000_000 {
                return Err(Error::FilterLimit);
            }
            if selected.is_empty() {
                continue;
            }
            cells.clear();
            for i in &selected {
                cells.push(cell(batch.column(*i).as_ref(), row));
            }
            record(&mut writer, &cells).map_err(output_error)?;
            rows += 1;
        }
    }
    if decoded_rows as i64 != source.reader.metadata().file_metadata().num_rows() {
        return Err(Error::Input);
    }
    if filter.is_some() && matched_rows == 0 {
        return Err(Error::NoRows);
    }
    writer.flush().map_err(output_error)?;
    writer.get_ref().inner.sync_all().map_err(|_| Error::Io)?;
    if preflight::identity(&source.source).map_err(|_| Error::Input)? != source.identity
        || sha256::file(&source.source, source.identity.len).map_err(|_| Error::Input)?
            != source.digest
    {
        return Err(Error::Input);
    }
    let digest = source
        .digest
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<String>();
    // SAFETY: getrusage initializes a valid rusage allocation for this process.
    let mut usage = std::mem::MaybeUninit::<libc::rusage>::uninit();
    if unsafe { libc::getrusage(libc::RUSAGE_SELF, usage.as_mut_ptr()) } != 0 {
        return Err(Error::Io);
    }
    let usage = unsafe { usage.assume_init() };
    let cpu = usage.ru_utime.tv_sec as f64
        + usage.ru_stime.tv_sec as f64
        + (usage.ru_utime.tv_usec + usage.ru_stime.tv_usec) as f64 / 1e6;
    Ok(
        json!({"version":2,"status":"ok","rows":rows,"bytes":writer.get_ref().bytes,"input_sha256":digest,"peak_rss_kib":usage.ru_maxrss,"cpu_seconds":cpu}),
    )
}
fn main() -> ExitCode {
    if std::env::args().collect::<Vec<_>>()
        == ["parquet_csv_cli".to_string(), "--version".to_string()]
        || (std::env::args().len() == 2 && std::env::args().nth(1).as_deref() == Some("--version"))
    {
        println!("parquet_csv_cli 0.2.0");
        return ExitCode::SUCCESS;
    }
    match args().and_then(run) {
        Ok(result) => {
            println!("{result}");
            ExitCode::SUCCESS
        }
        Err(e) => {
            let (code, name) = e.details();
            eprintln!("{}", json!({"version":2,"status":"error","code":name}));
            ExitCode::from(code)
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn float_notation() {
        for (x, s) in [
            (1e16, "1e+16"),
            (1e-5, "1e-05"),
            (1e-4, "0.0001"),
            (12.0, "12.0"),
            (-0.0, "-0.0"),
            (1.2e20, "1.2e+20"),
        ] {
            assert_eq!(python_float(x), s);
        }
    }
    #[test]
    fn disk_full_is_io_error() {
        let file = OpenOptions::new().write(true).open("/dev/full").unwrap();
        let mut w = Limited {
            inner: file,
            bytes: 0,
            max: 1024,
        };
        let error = record(&mut w, &["value".into()]).unwrap_err();
        assert!(matches!(output_error(error), Error::Io));
    }
    #[test]
    fn quote_python() {
        let mut b = Vec::new();
        record(&mut b, &["a\rb".into(), "x\ny".into(), "a\"b".into()]).unwrap();
        assert_eq!(b, b"\"a\rb\",\"x\ny\",\"a\"\"b\"\n");
    }
}

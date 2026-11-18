mod compact;
mod preflight;
mod sha256;

use arrow_array::*;
use arrow_schema::{DataType, Schema};
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
}
impl Error {
    fn details(&self) -> (u8, &'static str) {
        match self {
            Self::Arguments => (2, "arguments"),
            Self::Input => (3, "input_rejected"),
            Self::Limit => (4, "resource_limit"),
            Self::Io => (5, "io_error"),
        }
    }
}
struct Config {
    root: PathBuf,
    memory: u64,
    cpu: u64,
    output: u64,
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
    })
}
fn set_limits(c: &Config) -> Result<(), Error> {
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
        DataType::Int8
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
fn columns(schema: &Schema) -> Result<(Vec<usize>, Vec<String>), Error> {
    let mut indices = BTreeSet::from(["__index_level_0__".to_owned()]);
    if let Some(raw) = schema.metadata().get("pandas")
        && let Ok(value) = serde_json::from_str::<Value>(raw)
    {
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
    let mut seen = BTreeSet::new();
    for (i, f) in schema.fields().iter().enumerate() {
        // Index metadata controls presentation, never input trust. The reader
        // decodes every physical field, so validate even omitted columns.
        if !supported(f.data_type()) || f.metadata().contains_key("ARROW:extension:name") {
            return Err(Error::Input);
        }
        if indices.contains(f.name()) {
            continue;
        }
        let mut label = f.name().clone();
        if let Some(units) = f
            .metadata()
            .get("units")
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
        if !seen.insert(label.clone()) {
            return Err(Error::Input);
        }
        selected.push(i);
        labels.push(label);
    }
    if selected.is_empty() {
        return Err(Error::Input);
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
    let (selected, labels) = columns(builder.schema())?;
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
    let mut cells = Vec::with_capacity(selected.len());
    for batch in reader {
        let batch = batch.map_err(|_| Error::Input)?;
        for row in 0..batch.num_rows() {
            cells.clear();
            for i in &selected {
                cells.push(cell(batch.column(*i).as_ref(), row));
            }
            record(&mut writer, &cells).map_err(output_error)?;
            rows += 1;
        }
    }
    if rows as i64 != source.reader.metadata().file_metadata().num_rows() {
        return Err(Error::Input);
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
        json!({"version":1,"status":"ok","rows":rows,"bytes":writer.get_ref().bytes,"input_sha256":digest,"peak_rss_kib":usage.ru_maxrss,"cpu_seconds":cpu}),
    )
}
fn main() -> ExitCode {
    if std::env::args().collect::<Vec<_>>()
        == ["parquet_csv_cli".to_string(), "--version".to_string()]
        || (std::env::args().len() == 2 && std::env::args().nth(1).as_deref() == Some("--version"))
    {
        println!("parquet_csv_cli 0.1.0");
        return ExitCode::SUCCESS;
    }
    match args().and_then(run) {
        Ok(result) => {
            println!("{result}");
            ExitCode::SUCCESS
        }
        Err(e) => {
            let (code, name) = e.details();
            eprintln!("{}", json!({"version":1,"status":"error","code":name}));
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

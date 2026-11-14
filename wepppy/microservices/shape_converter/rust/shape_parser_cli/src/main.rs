use serde::Serialize;
use serde_json::{Number, Value, json};
use shapefile::{Patch, Point, PointM, PointZ, PolygonRing, Shape};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufWriter, Read, Seek, Write};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

const EXIT_PARSE_ERROR: u8 = 1;
const EXIT_ARGUMENT_ERROR: u8 = 2;
const EXIT_OUTPUT_ERROR: u8 = 3;
const EXIT_FEATURE_LIMIT: u8 = 4;
const EXIT_VERTEX_LIMIT: u8 = 5;
const MAX_PRJ_BYTES: u64 = 1_048_576;

#[derive(Debug)]
enum AppError {
    Argument,
    Parse,
    Output,
    FeatureLimit,
    VertexLimit,
}

impl AppError {
    fn exit_code(&self) -> u8 {
        match self {
            Self::Argument => EXIT_ARGUMENT_ERROR,
            Self::Parse => EXIT_PARSE_ERROR,
            Self::Output => EXIT_OUTPUT_ERROR,
            Self::FeatureLimit => EXIT_FEATURE_LIMIT,
            Self::VertexLimit => EXIT_VERTEX_LIMIT,
        }
    }
}

#[derive(Debug)]
struct Config {
    request_root: PathBuf,
    shp_path: PathBuf,
    output_path: PathBuf,
    max_payload_bytes: u64,
    max_input_bytes: u64,
    max_features: usize,
    max_vertices_per_feature: usize,
    max_memory_bytes: u64,
    max_cpu_seconds: u64,
    max_open_files: u64,
}

#[derive(Serialize)]
struct ParserPayload {
    properties: Vec<BTreeMap<String, Value>>,
    geometries: Vec<Value>,
    source_bounds: [f64; 4],
    source_crs_wkt: Option<String>,
}

struct DbfRecord {
    deleted: bool,
    properties: BTreeMap<String, Value>,
}

struct DbfField {
    name: String,
    kind: u8,
    length: usize,
    decimal_count: u8,
}

trait Coordinate {
    fn values(&self) -> Value;
}

impl Coordinate for Point {
    fn values(&self) -> Value {
        json!([self.x, self.y])
    }
}

impl Coordinate for PointM {
    fn values(&self) -> Value {
        json!([self.x, self.y])
    }
}

impl Coordinate for PointZ {
    fn values(&self) -> Value {
        json!([self.x, self.y, self.z])
    }
}

fn main() -> ExitCode {
    if env::args().len() == 2 && env::args().nth(1).as_deref() == Some("--version") {
        println!("shape_parser_cli {}", env!("CARGO_PKG_VERSION"));
        return ExitCode::SUCCESS;
    }

    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{}", fixed_error_message(&error));
            ExitCode::from(error.exit_code())
        }
    }
}

fn fixed_error_message(error: &AppError) -> &'static str {
    match error {
        AppError::Argument => "Invalid parser arguments.",
        AppError::Parse => "Parser failed to parse the dataset.",
        AppError::Output => "Parser failed to publish a valid payload.",
        AppError::FeatureLimit => "Feature count exceeded limit.",
        AppError::VertexLimit => "Vertex count exceeded limit.",
    }
}

fn run() -> Result<(), AppError> {
    let config = parse_args(env::args().skip(1))?;
    validate_paths_and_sizes(&config)?;
    apply_resource_limits(&config)?;
    let payload = parse_dataset(&config)?;
    write_payload_atomically(&config, &payload)
}

fn parse_args<I>(args: I) -> Result<Config, AppError>
where
    I: IntoIterator<Item = String>,
{
    let mut values = BTreeMap::new();
    let mut iter = args.into_iter();
    while let Some(flag) = iter.next() {
        if !flag.starts_with("--") || values.contains_key(&flag) {
            return Err(AppError::Argument);
        }
        let value = iter.next().ok_or(AppError::Argument)?;
        values.insert(flag, value);
    }

    let take_path = |name: &str| -> Result<PathBuf, AppError> {
        values
            .get(name)
            .filter(|value| !value.is_empty())
            .map(PathBuf::from)
            .ok_or(AppError::Argument)
    };
    let take_u64 = |name: &str| -> Result<u64, AppError> {
        values
            .get(name)
            .and_then(|value| value.parse::<u64>().ok())
            .filter(|value| *value > 0)
            .ok_or(AppError::Argument)
    };
    let take_usize = |name: &str| -> Result<usize, AppError> {
        values
            .get(name)
            .and_then(|value| value.parse::<usize>().ok())
            .filter(|value| *value > 0)
            .ok_or(AppError::Argument)
    };

    let config = Config {
        request_root: take_path("--request-root")?,
        shp_path: take_path("--shp-path")?,
        output_path: take_path("--output-path")?,
        max_payload_bytes: take_u64("--max-payload-bytes")?,
        max_input_bytes: take_u64("--max-input-bytes")?,
        max_features: take_usize("--max-features")?,
        max_vertices_per_feature: take_usize("--max-vertices-per-feature")?,
        max_memory_bytes: take_u64("--max-memory-bytes")?,
        max_cpu_seconds: take_u64("--max-cpu-seconds")?,
        max_open_files: take_u64("--max-open-files")?,
    };

    if values.len() != 10 {
        return Err(AppError::Argument);
    }
    Ok(config)
}

fn validate_paths_and_sizes(config: &Config) -> Result<(), AppError> {
    let request_root = config
        .request_root
        .canonicalize()
        .map_err(|_| AppError::Argument)?;
    let shp_path = config
        .shp_path
        .canonicalize()
        .map_err(|_| AppError::Argument)?;
    if !shp_path.starts_with(&request_root)
        || shp_path.extension().and_then(|value| value.to_str()) != Some("shp")
    {
        return Err(AppError::Argument);
    }

    let output_parent = config.output_path.parent().ok_or(AppError::Argument)?;
    let output_parent = output_parent
        .canonicalize()
        .map_err(|_| AppError::Argument)?;
    if !output_parent.starts_with(&request_root) || config.output_path.exists() {
        return Err(AppError::Argument);
    }

    let mut total_bytes = 0_u64;
    for extension in ["shp", "shx", "dbf", "prj", "cpg"] {
        let path = config.shp_path.with_extension(extension);
        if !path.exists() {
            if matches!(extension, "shp" | "shx" | "dbf") {
                return Err(AppError::Parse);
            }
            continue;
        }
        let metadata = fs::symlink_metadata(&path).map_err(|_| AppError::Parse)?;
        if metadata.file_type().is_symlink() || !metadata.is_file() {
            return Err(AppError::Parse);
        }
        total_bytes = total_bytes
            .checked_add(metadata.len())
            .ok_or(AppError::Parse)?;
        if total_bytes > config.max_input_bytes {
            return Err(AppError::Parse);
        }
    }

    validate_main_file_header(&config.shp_path)?;
    validate_main_file_header(&config.shp_path.with_extension("shx"))?;
    validate_record_alignment(config)?;
    Ok(())
}

fn validate_main_file_header(path: &Path) -> Result<(), AppError> {
    let actual_len = fs::metadata(path).map_err(|_| AppError::Parse)?.len();
    if actual_len < 100 || actual_len % 2 != 0 {
        return Err(AppError::Parse);
    }
    let mut source = File::open(path).map_err(|_| AppError::Parse)?;
    let mut header = [0_u8; 100];
    source
        .read_exact(&mut header)
        .map_err(|_| AppError::Parse)?;
    let file_code = u32::from_be_bytes(header[0..4].try_into().map_err(|_| AppError::Parse)?);
    let length_words =
        u32::from_be_bytes(header[24..28].try_into().map_err(|_| AppError::Parse)?) as u64;
    let version = u32::from_le_bytes(header[28..32].try_into().map_err(|_| AppError::Parse)?);
    let declared_len = length_words.checked_mul(2).ok_or(AppError::Parse)?;
    if file_code != 9994 || version != 1000 || declared_len != actual_len {
        return Err(AppError::Parse);
    }
    Ok(())
}

fn validate_record_alignment(config: &Config) -> Result<(), AppError> {
    let mut shp = File::open(&config.shp_path).map_err(|_| AppError::Parse)?;
    let shp_len = shp.metadata().map_err(|_| AppError::Parse)?.len();
    let mut shp_offset = 100_u64;
    let mut records = Vec::new();
    while shp_offset < shp_len {
        shp.seek(io::SeekFrom::Start(shp_offset))
            .map_err(|_| AppError::Parse)?;
        let mut header = [0_u8; 8];
        shp.read_exact(&mut header).map_err(|_| AppError::Parse)?;
        let record_number =
            u32::from_be_bytes(header[0..4].try_into().map_err(|_| AppError::Parse)?);
        let content_words =
            u32::from_be_bytes(header[4..8].try_into().map_err(|_| AppError::Parse)?);
        let expected_number = u32::try_from(records.len() + 1).map_err(|_| AppError::Parse)?;
        let content_bytes = u64::from(content_words)
            .checked_mul(2)
            .ok_or(AppError::Parse)?;
        if record_number != expected_number || content_bytes < 4 {
            return Err(AppError::Parse);
        }
        let next_offset = shp_offset
            .checked_add(8)
            .and_then(|value| value.checked_add(content_bytes))
            .ok_or(AppError::Parse)?;
        if next_offset > shp_len {
            return Err(AppError::Parse);
        }
        records.push((shp_offset / 2, u64::from(content_words)));
        shp_offset = next_offset;
    }
    if shp_offset != shp_len || records.len() > config.max_features {
        return Err(if records.len() > config.max_features {
            AppError::FeatureLimit
        } else {
            AppError::Parse
        });
    }

    let mut shx = File::open(config.shp_path.with_extension("shx")).map_err(|_| AppError::Parse)?;
    shx.seek(io::SeekFrom::Start(100))
        .map_err(|_| AppError::Parse)?;
    for (expected_offset, expected_content_words) in &records {
        let mut entry = [0_u8; 8];
        shx.read_exact(&mut entry).map_err(|_| AppError::Parse)?;
        let offset = u64::from(u32::from_be_bytes(
            entry[0..4].try_into().map_err(|_| AppError::Parse)?,
        ));
        let content_words = u64::from(u32::from_be_bytes(
            entry[4..8].try_into().map_err(|_| AppError::Parse)?,
        ));
        if offset != *expected_offset || content_words != *expected_content_words {
            return Err(AppError::Parse);
        }
    }
    let mut trailing = [0_u8; 1];
    if shx.read(&mut trailing).map_err(|_| AppError::Parse)? != 0 {
        return Err(AppError::Parse);
    }

    let mut dbf = File::open(config.shp_path.with_extension("dbf")).map_err(|_| AppError::Parse)?;
    let mut header = [0_u8; 8];
    dbf.read_exact(&mut header).map_err(|_| AppError::Parse)?;
    let record_count =
        u32::from_le_bytes(header[4..8].try_into().map_err(|_| AppError::Parse)?) as u64;
    if records.len() as u64 != record_count {
        return Err(AppError::Parse);
    }
    Ok(())
}

fn apply_resource_limits(config: &Config) -> Result<(), AppError> {
    set_limit(libc::RLIMIT_CORE, 0)?;
    set_limit(libc::RLIMIT_AS, config.max_memory_bytes)?;
    set_limit(libc::RLIMIT_CPU, config.max_cpu_seconds)?;
    set_limit(libc::RLIMIT_FSIZE, config.max_payload_bytes)?;
    set_limit(libc::RLIMIT_NOFILE, config.max_open_files)?;
    Ok(())
}

fn set_limit(resource: libc::__rlimit_resource_t, value: u64) -> Result<(), AppError> {
    let limit = libc::rlimit {
        rlim_cur: value as libc::rlim_t,
        rlim_max: value as libc::rlim_t,
    };
    // SAFETY: `limit` points to a fully initialized `rlimit`; the resource
    // constants are fixed by this executable and no pointer escapes the call.
    let result = unsafe { libc::setrlimit(resource, &limit) };
    if result == 0 {
        Ok(())
    } else {
        Err(AppError::Argument)
    }
}

fn parse_dataset(config: &Config) -> Result<ParserPayload, AppError> {
    let mut reader =
        shapefile::ShapeReader::from_path(&config.shp_path).map_err(|_| AppError::Parse)?;
    let bbox = reader.header().bbox;
    let source_bounds = [bbox.min.x, bbox.min.y, bbox.max.x, bbox.max.y];
    if source_bounds.iter().any(|value| !value.is_finite())
        || source_bounds[0] > source_bounds[2]
        || source_bounds[1] > source_bounds[3]
    {
        return Err(AppError::Parse);
    }

    let mut properties = Vec::new();
    let mut geometries = Vec::new();
    properties
        .try_reserve_exact(config.max_features.min(4096))
        .map_err(|_| AppError::Parse)?;
    geometries
        .try_reserve_exact(config.max_features.min(4096))
        .map_err(|_| AppError::Parse)?;

    let dbf_records = read_dbf_records(config)?;
    let mut shape_count = 0_usize;
    for (index, item) in reader.iter_shapes().enumerate() {
        let record = dbf_records.get(index).ok_or(AppError::Parse)?;
        shape_count += 1;
        let shape = item.map_err(|_| AppError::Parse)?;
        if record.deleted {
            continue;
        }
        if properties.len() >= config.max_features {
            return Err(AppError::FeatureLimit);
        }
        if shape_vertex_count(&shape) > config.max_vertices_per_feature {
            return Err(AppError::VertexLimit);
        }
        geometries.push(shape_to_json(shape)?);
        properties.push(record.properties.clone());
    }
    if shape_count != dbf_records.len() || shape_count != record_count_from_shx(&config.shp_path)? {
        return Err(AppError::Parse);
    }

    Ok(ParserPayload {
        properties,
        geometries,
        source_bounds,
        source_crs_wkt: read_optional_prj(&config.shp_path)?,
    })
}

fn read_optional_prj(shp_path: &Path) -> Result<Option<String>, AppError> {
    let path = shp_path.with_extension("prj");
    if !path.exists() {
        return Ok(None);
    }
    let metadata = fs::metadata(&path).map_err(|_| AppError::Parse)?;
    if metadata.len() == 0 || metadata.len() > MAX_PRJ_BYTES {
        return Err(AppError::Parse);
    }
    let value = fs::read_to_string(path).map_err(|_| AppError::Parse)?;
    let trimmed = value.trim();
    if trimmed.is_empty() {
        Err(AppError::Parse)
    } else {
        Ok(Some(trimmed.to_owned()))
    }
}

fn read_dbf_records(config: &Config) -> Result<Vec<DbfRecord>, AppError> {
    let path = config.shp_path.with_extension("dbf");
    let file_len = fs::metadata(&path).map_err(|_| AppError::Parse)?.len();
    let mut source = File::open(path).map_err(|_| AppError::Parse)?;
    let mut header = [0_u8; 32];
    source
        .read_exact(&mut header)
        .map_err(|_| AppError::Parse)?;
    let record_count =
        u32::from_le_bytes(header[4..8].try_into().map_err(|_| AppError::Parse)?) as usize;
    let header_len = u16::from_le_bytes([header[8], header[9]]) as usize;
    let record_len = u16::from_le_bytes([header[10], header[11]]) as usize;
    if header_len < 33 || record_len < 1 || record_count > config.max_features {
        return Err(if record_count > config.max_features {
            AppError::FeatureLimit
        } else {
            AppError::Parse
        });
    }
    let expected_len = header_len
        .checked_add(
            record_count
                .checked_mul(record_len)
                .ok_or(AppError::Parse)?,
        )
        .ok_or(AppError::Parse)? as u64;
    if expected_len > file_len || header_len > 65_535 || record_len > 65_535 {
        return Err(AppError::Parse);
    }

    let descriptor_bytes_len = header_len - 32;
    let mut descriptor_bytes = vec![0_u8; descriptor_bytes_len];
    source
        .read_exact(&mut descriptor_bytes)
        .map_err(|_| AppError::Parse)?;
    let terminator = descriptor_bytes
        .iter()
        .position(|byte| *byte == 0x0d)
        .ok_or(AppError::Parse)?;
    if terminator % 32 != 0 || terminator / 32 > 2048 {
        return Err(AppError::Parse);
    }
    let mut fields = Vec::with_capacity(terminator / 32);
    let mut field_names = BTreeSet::new();
    let mut computed_record_len = 1_usize;
    for descriptor in descriptor_bytes[..terminator].chunks_exact(32) {
        let name_end = descriptor[..11]
            .iter()
            .position(|byte| *byte == 0)
            .unwrap_or(11);
        let name = std::str::from_utf8(&descriptor[..name_end])
            .map_err(|_| AppError::Parse)?
            .trim();
        if name.is_empty() {
            return Err(AppError::Parse);
        }
        if !field_names.insert(name.to_ascii_lowercase()) {
            return Err(AppError::Parse);
        }
        let length = descriptor[16] as usize;
        if length == 0 {
            return Err(AppError::Parse);
        }
        computed_record_len = computed_record_len
            .checked_add(length)
            .ok_or(AppError::Parse)?;
        fields.push(DbfField {
            name: name.to_owned(),
            kind: descriptor[11],
            length,
            decimal_count: descriptor[17],
        });
    }
    if computed_record_len != record_len {
        return Err(AppError::Parse);
    }

    let encoding = dbf_encoding(&config.shp_path, header[29])?;
    let mut records = Vec::new();
    records
        .try_reserve_exact(record_count.min(4096))
        .map_err(|_| AppError::Parse)?;
    for _ in 0..record_count {
        let mut raw = vec![0_u8; record_len];
        source.read_exact(&mut raw).map_err(|_| AppError::Parse)?;
        let deleted = match raw[0] {
            b' ' => false,
            b'*' => true,
            _ => return Err(AppError::Parse),
        };
        let mut offset = 1_usize;
        let mut properties = BTreeMap::new();
        for field in &fields {
            let end = offset.checked_add(field.length).ok_or(AppError::Parse)?;
            let value = dbf_field_value(field, &raw[offset..end], encoding)?;
            properties.insert(field.name.clone(), value);
            offset = end;
        }
        records.push(DbfRecord {
            deleted,
            properties,
        });
    }
    let mut trailer = [0_u8; 1];
    match source.read(&mut trailer).map_err(|_| AppError::Parse)? {
        0 => {}
        1 if trailer[0] == 0x1a => {
            if source.read(&mut trailer).map_err(|_| AppError::Parse)? != 0 {
                return Err(AppError::Parse);
            }
        }
        _ => return Err(AppError::Parse),
    }
    Ok(records)
}

fn dbf_encoding(
    shp_path: &Path,
    language_driver: u8,
) -> Result<&'static encoding_rs::Encoding, AppError> {
    let cpg_path = shp_path.with_extension("cpg");
    if !cpg_path.exists() {
        return match language_driver {
            0x00 | 0x03 | 0x57 => Ok(encoding_rs::WINDOWS_1252),
            0xc8 => Ok(encoding_rs::WINDOWS_1250),
            0xc9 => Ok(encoding_rs::WINDOWS_1251),
            _ => Err(AppError::Parse),
        };
    }
    let label = fs::read_to_string(cpg_path).map_err(|_| AppError::Parse)?;
    let normalized = label.trim().trim_start_matches('\u{feff}');
    match normalized {
        "65001" => Ok(encoding_rs::UTF_8),
        "1252" => Ok(encoding_rs::WINDOWS_1252),
        _ => encoding_rs::Encoding::for_label(normalized.as_bytes()).ok_or(AppError::Parse),
    }
}

fn dbf_field_value(
    field: &DbfField,
    raw: &[u8],
    encoding: &'static encoding_rs::Encoding,
) -> Result<Value, AppError> {
    let trimmed = trim_ascii(raw);
    if trimmed.is_empty()
        || (field.kind == b'D' && trimmed == b"00000000")
        || (matches!(field.kind, b'N' | b'F') && trimmed.iter().all(|byte| *byte == b'*'))
    {
        return Ok(Value::Null);
    }
    match field.kind {
        b'C' => {
            let (value, _, had_errors) = encoding.decode(trimmed);
            if had_errors {
                Err(AppError::Parse)
            } else {
                Ok(Value::String(value.into_owned()))
            }
        }
        b'N' if field.decimal_count == 0 => {
            let value = std::str::from_utf8(trimmed).map_err(|_| AppError::Parse)?;
            if let Ok(integer) = value.parse::<i64>() {
                Ok(Value::Number(integer.into()))
            } else {
                number(value.parse::<f64>().map_err(|_| AppError::Parse)?)
            }
        }
        b'N' | b'F' => {
            let value = std::str::from_utf8(trimmed).map_err(|_| AppError::Parse)?;
            number(value.parse::<f64>().map_err(|_| AppError::Parse)?)
        }
        b'L' => match trimmed[0] {
            b'1' | b'T' | b't' | b'Y' | b'y' => Ok(Value::Bool(true)),
            b'0' | b'F' | b'f' | b'N' | b'n' => Ok(Value::Bool(false)),
            b'?' => Ok(Value::Null),
            _ => Err(AppError::Parse),
        },
        b'D' => {
            if trimmed.len() != 8 || !trimmed.iter().all(u8::is_ascii_digit) {
                return Err(AppError::Parse);
            }
            let year = parse_date_component(&trimmed[0..4])?;
            let month = parse_date_component(&trimmed[4..6])?;
            let day = parse_date_component(&trimmed[6..8])?;
            if !valid_date(year, month, day) {
                return Err(AppError::Parse);
            }
            Ok(Value::String(format!(
                "{}-{}-{}",
                std::str::from_utf8(&trimmed[0..4]).map_err(|_| AppError::Parse)?,
                std::str::from_utf8(&trimmed[4..6]).map_err(|_| AppError::Parse)?,
                std::str::from_utf8(&trimmed[6..8]).map_err(|_| AppError::Parse)?
            )))
        }
        b'I' if raw.len() == 4 => Ok(Value::Number(
            i32::from_le_bytes(raw.try_into().map_err(|_| AppError::Parse)?).into(),
        )),
        b'O' if raw.len() == 8 => number(f64::from_le_bytes(
            raw.try_into().map_err(|_| AppError::Parse)?,
        )),
        b'Y' if raw.len() == 8 => number(
            i64::from_le_bytes(raw.try_into().map_err(|_| AppError::Parse)?) as f64 / 10_000.0,
        ),
        _ => Err(AppError::Parse),
    }
}

fn parse_date_component(raw: &[u8]) -> Result<u32, AppError> {
    std::str::from_utf8(raw)
        .map_err(|_| AppError::Parse)?
        .parse::<u32>()
        .map_err(|_| AppError::Parse)
}

fn valid_date(year: u32, month: u32, day: u32) -> bool {
    let leap_year =
        year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let max_day = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap_year => 29,
        2 => 28,
        _ => return false,
    };
    year > 0 && day > 0 && day <= max_day
}

fn trim_ascii(mut value: &[u8]) -> &[u8] {
    while value.first().is_some_and(u8::is_ascii_whitespace) {
        value = &value[1..];
    }
    while value.last().is_some_and(u8::is_ascii_whitespace) {
        value = &value[..value.len() - 1];
    }
    value
}

fn record_count_from_shx(shp_path: &Path) -> Result<usize, AppError> {
    let len = fs::metadata(shp_path.with_extension("shx"))
        .map_err(|_| AppError::Parse)?
        .len();
    if len < 100 || (len - 100) % 8 != 0 {
        return Err(AppError::Parse);
    }
    usize::try_from((len - 100) / 8).map_err(|_| AppError::Parse)
}

fn number(value: f64) -> Result<Value, AppError> {
    Number::from_f64(value)
        .map(Value::Number)
        .ok_or(AppError::Parse)
}

fn shape_vertex_count(shape: &Shape) -> usize {
    match shape {
        Shape::NullShape => 0,
        Shape::Point(_) | Shape::PointM(_) | Shape::PointZ(_) => 1,
        Shape::Polyline(value) => value.parts().iter().map(Vec::len).sum(),
        Shape::PolylineM(value) => value.parts().iter().map(Vec::len).sum(),
        Shape::PolylineZ(value) => value.parts().iter().map(Vec::len).sum(),
        Shape::Polygon(value) => value.rings().iter().map(PolygonRing::len).sum(),
        Shape::PolygonM(value) => value.rings().iter().map(PolygonRing::len).sum(),
        Shape::PolygonZ(value) => value.rings().iter().map(PolygonRing::len).sum(),
        Shape::Multipoint(value) => value.points().len(),
        Shape::MultipointM(value) => value.points().len(),
        Shape::MultipointZ(value) => value.points().len(),
        Shape::Multipatch(value) => value
            .patches()
            .iter()
            .map(|patch| patch.points().len())
            .sum(),
    }
}

fn shape_to_json(shape: Shape) -> Result<Value, AppError> {
    match shape {
        Shape::NullShape => Ok(Value::Null),
        Shape::Point(value) => geometry("Point", value.values()),
        Shape::PointM(value) => geometry("Point", value.values()),
        Shape::PointZ(value) => geometry("Point", value.values()),
        Shape::Polyline(value) => polyline_geometry(value.parts()),
        Shape::PolylineM(value) => polyline_geometry(value.parts()),
        Shape::PolylineZ(value) => polyline_geometry(value.parts()),
        Shape::Polygon(value) => polygon_geometry(value.rings()),
        Shape::PolygonM(value) => polygon_geometry(value.rings()),
        Shape::PolygonZ(value) => polygon_geometry(value.rings()),
        Shape::Multipoint(value) => multipoint_geometry(value.points()),
        Shape::MultipointM(value) => multipoint_geometry(value.points()),
        Shape::MultipointZ(value) => multipoint_geometry(value.points()),
        Shape::Multipatch(value) => multipatch_geometry(value.patches()),
    }
}

fn geometry(kind: &str, coordinates: Value) -> Result<Value, AppError> {
    if !coordinates_are_finite(&coordinates) {
        return Err(AppError::Parse);
    }
    Ok(json!({"type": kind, "coordinates": coordinates}))
}

fn coordinates_are_finite(value: &Value) -> bool {
    match value {
        Value::Number(number) => number.as_f64().is_some_and(f64::is_finite),
        Value::Array(values) => values.iter().all(coordinates_are_finite),
        _ => false,
    }
}

fn points_json<P: Coordinate>(points: &[P]) -> Value {
    Value::Array(points.iter().map(Coordinate::values).collect())
}

fn multipoint_geometry<P: Coordinate>(points: &[P]) -> Result<Value, AppError> {
    geometry("MultiPoint", points_json(points))
}

fn polyline_geometry<P: Coordinate>(parts: &[Vec<P>]) -> Result<Value, AppError> {
    if parts.is_empty() || parts.iter().any(Vec::is_empty) {
        return Err(AppError::Parse);
    }
    if parts.len() == 1 {
        geometry("LineString", points_json(&parts[0]))
    } else {
        geometry(
            "MultiLineString",
            Value::Array(parts.iter().map(|part| points_json(part)).collect()),
        )
    }
}

fn polygon_coordinates<P: Coordinate>(rings: &[PolygonRing<P>]) -> Result<Vec<Value>, AppError> {
    let mut polygons: Vec<Value> = Vec::new();
    let inverted_orientation = matches!(rings.first(), Some(PolygonRing::Inner(_)));
    for ring in rings {
        let coordinates = points_json(ring.points());
        let starts_polygon = matches!(ring, PolygonRing::Outer(_)) ^ inverted_orientation;
        if starts_polygon {
            polygons.push(Value::Array(vec![coordinates]));
        } else {
            let Some(Value::Array(active)) = polygons.last_mut() else {
                return Err(AppError::Parse);
            };
            active.push(coordinates);
        }
    }
    if polygons.is_empty() {
        Err(AppError::Parse)
    } else {
        Ok(polygons)
    }
}

fn polygon_geometry<P: Coordinate>(rings: &[PolygonRing<P>]) -> Result<Value, AppError> {
    let polygons = polygon_coordinates(rings)?;
    if polygons.len() == 1 {
        geometry(
            "Polygon",
            polygons.into_iter().next().ok_or(AppError::Parse)?,
        )
    } else {
        geometry("MultiPolygon", Value::Array(polygons))
    }
}

fn multipatch_geometry(patches: &[Patch]) -> Result<Value, AppError> {
    let mut members = Vec::new();
    let mut active_polygon: Option<Vec<Value>> = None;
    fn flush(active: &mut Option<Vec<Value>>, output: &mut Vec<Value>) -> Result<(), AppError> {
        if let Some(rings) = active.take() {
            output.push(geometry(
                "MultiPolygon",
                Value::Array(vec![Value::Array(rings)]),
            )?);
        }
        Ok(())
    }
    for patch in patches {
        match patch {
            Patch::OuterRing(points) | Patch::FirstRing(points) => {
                flush(&mut active_polygon, &mut members)?;
                active_polygon = Some(vec![points_json(points)]);
            }
            Patch::InnerRing(points) | Patch::Ring(points) => {
                let Some(rings) = active_polygon.as_mut() else {
                    return Err(AppError::Parse);
                };
                rings.push(points_json(points));
            }
            Patch::TriangleStrip(points) => {
                flush(&mut active_polygon, &mut members)?;
                for index in 2..points.len() {
                    let ring = Value::Array(vec![
                        points[index - 2].values(),
                        points[index - 1].values(),
                        points[index].values(),
                        points[index - 2].values(),
                    ]);
                    members.push(geometry(
                        "MultiPolygon",
                        Value::Array(vec![Value::Array(vec![ring])]),
                    )?);
                }
            }
            Patch::TriangleFan(points) => {
                flush(&mut active_polygon, &mut members)?;
                for index in 2..points.len() {
                    let ring = Value::Array(vec![
                        points[0].values(),
                        points[index - 1].values(),
                        points[index].values(),
                        points[0].values(),
                    ]);
                    members.push(geometry(
                        "MultiPolygon",
                        Value::Array(vec![Value::Array(vec![ring])]),
                    )?);
                }
            }
        }
    }
    flush(&mut active_polygon, &mut members)?;
    Ok(json!({"type": "GeometryCollection", "geometries": members}))
}

fn write_payload_atomically(config: &Config, payload: &ParserPayload) -> Result<(), AppError> {
    let temp_path = config
        .output_path
        .with_extension(format!("tmp.{}", std::process::id()));
    let file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&temp_path)
        .map_err(|_| AppError::Output)?;
    let mut writer = LimitedWriter::new(BufWriter::new(file), config.max_payload_bytes);
    let result = serde_json::to_writer(&mut writer, payload)
        .map_err(|_| AppError::Output)
        .and_then(|()| writer.flush().map_err(|_| AppError::Output))
        .and_then(|()| fs::rename(&temp_path, &config.output_path).map_err(|_| AppError::Output));
    if result.is_err() {
        let _ = fs::remove_file(&temp_path);
    }
    result
}

struct LimitedWriter<W> {
    inner: W,
    remaining: u64,
}

impl<W> LimitedWriter<W> {
    fn new(inner: W, limit: u64) -> Self {
        Self {
            inner,
            remaining: limit,
        }
    }
}

impl<W: Write> Write for LimitedWriter<W> {
    fn write(&mut self, buffer: &[u8]) -> io::Result<usize> {
        if buffer.len() as u64 > self.remaining {
            return Err(io::Error::new(
                io::ErrorKind::FileTooLarge,
                "payload limit exceeded",
            ));
        }
        let written = self.inner.write(buffer)?;
        self.remaining -= written as u64;
        Ok(written)
    }
    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn duplicate_arguments_fail_closed() {
        let args = ["--request-root", "/tmp", "--request-root", "/tmp"]
            .into_iter()
            .map(str::to_owned);
        assert!(matches!(parse_args(args), Err(AppError::Argument)));
    }

    #[test]
    fn limited_writer_rejects_oversize_write() {
        let mut writer = LimitedWriter::new(Vec::new(), 3);
        assert!(writer.write_all(b"four").is_err());
    }

    #[test]
    fn non_finite_number_is_rejected() {
        assert!(matches!(number(f64::NAN), Err(AppError::Parse)));
    }

    #[test]
    fn counterclockwise_first_ring_is_accepted_as_outer_ring() {
        let rings = vec![PolygonRing::Inner(vec![
            Point::new(0.0, 0.0),
            Point::new(1.0, 0.0),
            Point::new(1.0, 1.0),
            Point::new(0.0, 0.0),
        ])];
        let geometry = polygon_geometry(&rings).expect("counterclockwise fixture must parse");
        assert_eq!(geometry["type"], "Polygon");
    }

    #[test]
    fn dbf_dates_require_valid_calendar_values() {
        assert!(valid_date(2024, 2, 29));
        assert!(!valid_date(2026, 2, 29));
        assert!(!valid_date(2026, 13, 1));
        assert!(!valid_date(0, 1, 1));
    }
}

mod compact;
mod preflight;
mod sha256;
mod wkb;

use parquet::basic::{ConvertedType, Type as PhysicalType};
use parquet::file::reader::FileReader;
use parquet::record::Field;
use serde_json::{Map, Number, Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::ffi::CString;
use std::fs::{self, OpenOptions};
use std::io::{BufWriter, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::OpenOptionsExt;
use std::path::PathBuf;
use std::process::ExitCode;

const MAX_ROWS: usize = 100_000;
const MAX_VERTICES: usize = 250_000;
const MAX_JSON_VALUES: usize = 2_000_000;
const MAX_JSON_DEPTH: usize = 16;
const MAX_GEO_METADATA: usize = 64 * 1024;

#[derive(Debug)]
enum AppError {
    Argument,
    Invalid(&'static str),
    Limit(&'static str),
    Output,
}

impl AppError {
    fn exit_code(&self) -> u8 {
        match self {
            Self::Invalid(_) => 1,
            Self::Argument => 2,
            Self::Output => 3,
            Self::Limit(_) => 4,
        }
    }

    fn stable_code(&self) -> &'static str {
        match self {
            Self::Argument => "argument_invalid",
            Self::Invalid(code) | Self::Limit(code) => code,
            Self::Output => "output_invalid",
        }
    }
}

struct Config {
    request_root: PathBuf,
    input_path: PathBuf,
    output_path: PathBuf,
    max_payload_bytes: u64,
    max_input_bytes: u64,
    max_features: usize,
    max_vertices_per_feature: usize,
    max_memory_bytes: u64,
    max_cpu_seconds: u64,
    max_open_files: u64,
}

fn main() -> ExitCode {
    if env::args().len() == 2 && env::args().nth(1).as_deref() == Some("--version") {
        println!("geoparquet_parser_cli {}", env!("CARGO_PKG_VERSION"));
        return ExitCode::SUCCESS;
    }
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("geoparquet_parser_error:{}", error.stable_code());
            ExitCode::from(error.exit_code())
        }
    }
}

fn run() -> Result<(), AppError> {
    let config = parse_args(env::args().skip(1))?;
    apply_resource_limits(&config)?;
    validate_paths(&config)?;
    let payload = parse_file(&config)?;
    write_payload(&config, &payload)
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
        values.insert(flag, iter.next().ok_or(AppError::Argument)?);
    }
    let path = |name: &str| {
        values
            .get(name)
            .filter(|value| !value.is_empty())
            .map(PathBuf::from)
            .ok_or(AppError::Argument)
    };
    let u64_value = |name: &str| {
        values
            .get(name)
            .and_then(|value| value.parse::<u64>().ok())
            .filter(|value| *value > 0)
            .ok_or(AppError::Argument)
    };
    let usize_value = |name: &str| {
        values
            .get(name)
            .and_then(|value| value.parse::<usize>().ok())
            .filter(|value| *value > 0)
            .ok_or(AppError::Argument)
    };
    let config = Config {
        request_root: path("--request-root")?,
        input_path: path("--input-path")?,
        output_path: path("--output-path")?,
        max_payload_bytes: u64_value("--max-payload-bytes")?,
        max_input_bytes: u64_value("--max-input-bytes")?,
        max_features: usize_value("--max-features")?,
        max_vertices_per_feature: usize_value("--max-vertices-per-feature")?,
        max_memory_bytes: u64_value("--max-memory-bytes")?,
        max_cpu_seconds: u64_value("--max-cpu-seconds")?,
        max_open_files: u64_value("--max-open-files")?,
    };
    if values.len() != 10
        || config.max_input_bytes > 100 * 1024 * 1024
        || config.max_payload_bytes > 16 * 1024 * 1024
        || config.max_features > MAX_ROWS
        || config.max_vertices_per_feature > MAX_VERTICES
        || !(64 * 1024 * 1024..=384 * 1024 * 1024).contains(&config.max_memory_bytes)
        || !(1..=60).contains(&config.max_cpu_seconds)
        || !(8..=32).contains(&config.max_open_files)
    {
        return Err(AppError::Argument);
    }
    Ok(config)
}

#[repr(C)]
struct RLimit {
    current: u64,
    maximum: u64,
}

unsafe extern "C" {
    fn setrlimit(resource: i32, limit: *const RLimit) -> i32;
}

fn apply_resource_limits(config: &Config) -> Result<(), AppError> {
    set_limit(4, 0)?; // RLIMIT_CORE
    set_limit(9, config.max_memory_bytes)?; // RLIMIT_AS
    set_limit(0, config.max_cpu_seconds)?; // RLIMIT_CPU
    set_limit(1, config.max_payload_bytes)?; // RLIMIT_FSIZE
    set_limit(7, config.max_open_files)?; // RLIMIT_NOFILE
    Ok(())
}

fn set_limit(resource: i32, value: u64) -> Result<(), AppError> {
    let limit = RLimit {
        current: value,
        maximum: value,
    };
    // SAFETY: `limit` is a valid pointer for the duration of the call and the
    // Linux resource constants above are fixed by the shape-converter ABI.
    if unsafe { setrlimit(resource, &limit) } != 0 {
        return Err(AppError::Argument);
    }
    Ok(())
}

fn validate_paths(config: &Config) -> Result<(), AppError> {
    let root = config
        .request_root
        .canonicalize()
        .map_err(|_| AppError::Argument)?;
    let input = config
        .input_path
        .canonicalize()
        .map_err(|_| AppError::Argument)?;
    if !input.starts_with(&root)
        || !matches!(
            input.extension().and_then(|value| value.to_str()),
            Some("parquet" | "geoparquet")
        )
    {
        return Err(AppError::Argument);
    }
    let output_parent = config
        .output_path
        .parent()
        .ok_or(AppError::Argument)?
        .canonicalize()
        .map_err(|_| AppError::Argument)?;
    if !output_parent.starts_with(&root) || config.output_path.exists() {
        return Err(AppError::Argument);
    }
    Ok(())
}

fn parse_file(config: &Config) -> Result<Value, AppError> {
    let preflighted = preflight::open(
        &config.request_root,
        &config.input_path,
        config.max_input_bytes,
    )
    .map_err(map_preflight_error)?;
    let file_metadata = preflighted.reader.metadata().file_metadata();
    let expected_rows = usize::try_from(file_metadata.num_rows())
        .map_err(|_| AppError::Invalid("row_count_mismatch"))?;
    let profile = parse_geo_profile(file_metadata.key_value_metadata())?;
    validate_schema_profile(file_metadata.schema_descr(), &profile.primary_column)?;

    let mut properties = Vec::new();
    let mut geometries = Vec::new();
    let mut observed_types = BTreeSet::new();
    let mut observed_bounds = [
        f64::INFINITY,
        f64::INFINITY,
        f64::NEG_INFINITY,
        f64::NEG_INFINITY,
    ];
    let mut retained_values = 0_usize;
    count_json(&profile.source_crs, 0, &mut retained_values)?;
    let mut retained_bytes = serde_json::to_vec(&profile.source_crs)
        .map_err(|_| AppError::Invalid("crs_invalid"))?
        .len()
        .checked_add(1024)
        .ok_or(AppError::Limit("payload_limit"))?;
    let rows = preflighted
        .reader
        .get_row_iter(None)
        .map_err(|_| AppError::Invalid("row_decode"))?;
    for row in rows {
        if properties.len() >= config.max_features {
            return Err(AppError::Limit("feature_limit"));
        }
        let row = row.map_err(|_| AppError::Invalid("row_decode"))?;
        let mut row_properties = Map::new();
        let mut geometry = None;
        for (name, field) in row.into_columns() {
            if name == profile.primary_column {
                geometry = Some(match field {
                    Field::Null => Value::Null,
                    Field::Bytes(bytes) => {
                        let parsed = wkb::parse(bytes.data(), config.max_vertices_per_feature)
                            .map_err(|_| AppError::Invalid("wkb_invalid"))?;
                        observed_types.insert(if parsed.dimensions == 3 {
                            format!("{} Z", parsed.geometry_type)
                        } else {
                            parsed.geometry_type.to_owned()
                        });
                        merge_bounds(&mut observed_bounds, parsed.bounds);
                        parsed.value
                    }
                    _ => return Err(AppError::Invalid("geometry_column")),
                });
            } else {
                row_properties.insert(name, property_value(field)?);
            }
        }
        let geometry = geometry.ok_or(AppError::Invalid("geometry_column"))?;
        let row_properties = Value::Object(row_properties);
        count_json(&geometry, 0, &mut retained_values)?;
        count_json(&row_properties, 0, &mut retained_values)?;
        let row_bytes = serde_json::to_vec(&geometry)
            .map_err(|_| AppError::Invalid("geometry_value"))?
            .len()
            .checked_add(
                serde_json::to_vec(&row_properties)
                    .map_err(|_| AppError::Invalid("property_value"))?
                    .len(),
            )
            .and_then(|value| value.checked_add(2))
            .ok_or(AppError::Limit("payload_limit"))?;
        retained_bytes = retained_bytes
            .checked_add(row_bytes)
            .ok_or(AppError::Limit("payload_limit"))?;
        if retained_bytes as u64 > config.max_payload_bytes {
            return Err(AppError::Limit("payload_limit"));
        }
        geometries.push(geometry);
        properties.push(row_properties);
    }
    if properties.len() != expected_rows {
        return Err(AppError::Invalid("row_count_mismatch"));
    }
    if properties.is_empty() || !observed_bounds.iter().all(|value| value.is_finite()) {
        return Err(AppError::Invalid("geometry_empty"));
    }
    if !profile.claimed_types.is_empty() && profile.claimed_types != observed_types {
        return Err(AppError::Invalid("geometry_metadata_mismatch"));
    }
    if preflight::identity(&preflighted.source).map_err(map_preflight_error)?
        != preflighted.identity
        || sha256::file(&preflighted.source, preflighted.identity.len)
            .map_err(map_preflight_error)?
            != preflighted.digest
        || preflight::identity(&preflighted.source).map_err(map_preflight_error)?
            != preflighted.identity
    {
        return Err(AppError::Invalid("input_changed"));
    }

    let payload = json!({
        "schema": "geoparquet-parser-v1",
        "properties": properties,
        "geometries": geometries,
        "feature_count": properties.len(),
        "geometry_types": observed_types,
        "source_bounds": observed_bounds,
        "source_crs": profile.source_crs,
        "geoparquet_version": profile.version,
    });
    let mut values = 0_usize;
    count_json(&payload, 0, &mut values)?;
    Ok(payload)
}

struct GeoProfile {
    version: String,
    primary_column: String,
    claimed_types: BTreeSet<String>,
    source_crs: Value,
}

fn parse_geo_profile(
    metadata: Option<&Vec<parquet::file::metadata::KeyValue>>,
) -> Result<GeoProfile, AppError> {
    let metadata = metadata.ok_or(AppError::Invalid("geo_metadata_missing"))?;
    if metadata
        .iter()
        .any(|entry| entry.key.starts_with("ARROW:extension:"))
    {
        return Err(AppError::Invalid("extension_metadata"));
    }
    let mut geo_entries = metadata.iter().filter(|entry| entry.key == "geo");
    let geo = geo_entries
        .next()
        .and_then(|entry| entry.value.as_deref())
        .ok_or(AppError::Invalid("geo_metadata_missing"))?;
    if geo_entries.next().is_some() || !within_geo_metadata_limit(geo.len()) {
        return Err(AppError::Invalid("geo_metadata_invalid"));
    }
    let value: Value =
        serde_json::from_str(geo).map_err(|_| AppError::Invalid("geo_metadata_invalid"))?;
    let mut count = 0;
    count_json(&value, 0, &mut count)?;
    let object = value
        .as_object()
        .ok_or(AppError::Invalid("geo_metadata_invalid"))?;
    let top_level: BTreeSet<&str> = ["version", "primary_column", "columns"]
        .into_iter()
        .collect();
    if object.keys().any(|key| !top_level.contains(key.as_str())) {
        return Err(AppError::Invalid("geo_metadata_unsupported"));
    }
    let version = object
        .get("version")
        .and_then(Value::as_str)
        .filter(|version| matches!(*version, "1.0.0" | "1.1.0"))
        .ok_or(AppError::Invalid("geoparquet_version"))?
        .to_owned();
    let primary_column = object
        .get("primary_column")
        .and_then(Value::as_str)
        .filter(|name| !name.is_empty() && name.len() <= 256)
        .ok_or(AppError::Invalid("primary_column"))?
        .to_owned();
    let columns = object
        .get("columns")
        .and_then(Value::as_object)
        .filter(|columns| columns.len() == 1)
        .ok_or(AppError::Invalid("geometry_columns"))?;
    let column = columns
        .get(&primary_column)
        .and_then(Value::as_object)
        .ok_or(AppError::Invalid("primary_column"))?;
    let allowed: BTreeSet<&str> = [
        "encoding",
        "geometry_types",
        "crs",
        "bbox",
        "edges",
        "orientation",
    ]
    .into_iter()
    .collect();
    if column.keys().any(|key| !allowed.contains(key.as_str()))
        || column.get("encoding").and_then(Value::as_str) != Some("WKB")
        || column
            .get("edges")
            .is_some_and(|value| value.as_str() != Some("planar"))
        || column
            .get("orientation")
            .is_some_and(|value| value.as_str() != Some("counterclockwise"))
    {
        return Err(AppError::Invalid("geo_metadata_unsupported"));
    }
    let claimed_types = match column.get("geometry_types") {
        None => BTreeSet::new(),
        Some(Value::Array(values)) if values.len() <= 32 => values
            .iter()
            .map(|value| {
                value
                    .as_str()
                    .filter(|name| is_geometry_type(name))
                    .map(str::to_owned)
                    .ok_or(AppError::Invalid("geometry_types"))
            })
            .collect::<Result<BTreeSet<_>, _>>()?,
        _ => return Err(AppError::Invalid("geometry_types")),
    };
    let source_crs = match column.get("crs") {
        None => Value::String("OGC:CRS84".to_owned()),
        Some(Value::Null) => return Err(AppError::Invalid("crs_null")),
        Some(value @ Value::Object(crs))
            if crs
                .get("type")
                .and_then(Value::as_str)
                .is_some_and(is_projjson_type)
                && !crs.contains_key("coordinate_epoch") =>
        {
            value.clone()
        }
        _ => return Err(AppError::Invalid("crs_invalid")),
    };
    if let Some(bbox) = column.get("bbox") {
        let values = bbox
            .as_array()
            .filter(|values| matches!(values.len(), 4 | 6))
            .ok_or(AppError::Invalid("bbox_invalid"))?;
        let numbers = values
            .iter()
            .map(Value::as_f64)
            .collect::<Option<Vec<_>>>()
            .filter(|values| values.iter().all(|value| value.is_finite()))
            .ok_or(AppError::Invalid("bbox_invalid"))?;
        let half = numbers.len() / 2;
        if numbers[..half]
            .iter()
            .zip(&numbers[half..])
            .any(|(minimum, maximum)| minimum > maximum)
        {
            return Err(AppError::Invalid("bbox_invalid"));
        }
    }
    Ok(GeoProfile {
        version,
        primary_column,
        claimed_types,
        source_crs,
    })
}

fn within_geo_metadata_limit(length: usize) -> bool {
    length <= MAX_GEO_METADATA
}

fn validate_schema_profile(
    schema: &parquet::schema::types::SchemaDescriptor,
    geometry_column: &str,
) -> Result<(), AppError> {
    let mut found_geometry = false;
    for column in schema.columns() {
        let name = column.name();
        let physical = column.physical_type();
        let converted = column.converted_type();
        if name == geometry_column {
            if found_geometry
                || physical != PhysicalType::BYTE_ARRAY
                || converted != ConvertedType::NONE
            {
                return Err(AppError::Invalid("geometry_column"));
            }
            found_geometry = true;
            continue;
        }
        let allowed = match physical {
            PhysicalType::BOOLEAN | PhysicalType::FLOAT | PhysicalType::DOUBLE => {
                converted == ConvertedType::NONE
            }
            PhysicalType::INT32 => matches!(
                converted,
                ConvertedType::NONE
                    | ConvertedType::INT_8
                    | ConvertedType::INT_16
                    | ConvertedType::INT_32
                    | ConvertedType::UINT_8
                    | ConvertedType::UINT_16
                    | ConvertedType::UINT_32
            ),
            PhysicalType::INT64 => matches!(
                converted,
                ConvertedType::NONE | ConvertedType::INT_64 | ConvertedType::UINT_64
            ),
            PhysicalType::BYTE_ARRAY => converted == ConvertedType::UTF8,
            _ => false,
        };
        if !allowed {
            return Err(AppError::Invalid("property_schema"));
        }
    }
    if !found_geometry {
        return Err(AppError::Invalid("geometry_column"));
    }
    Ok(())
}

fn property_value(field: Field) -> Result<Value, AppError> {
    Ok(match field {
        Field::Null => Value::Null,
        Field::Bool(value) => Value::Bool(value),
        Field::Byte(value) => Value::Number(Number::from(value)),
        Field::Short(value) => Value::Number(Number::from(value)),
        Field::Int(value) => Value::Number(Number::from(value)),
        Field::Long(value) => Value::Number(Number::from(value)),
        Field::UByte(value) => Value::Number(Number::from(value)),
        Field::UShort(value) => Value::Number(Number::from(value)),
        Field::UInt(value) => Value::Number(Number::from(value)),
        Field::ULong(value) => Value::Number(Number::from(value)),
        Field::Float(value) if value.is_finite() => Number::from_f64(f64::from(value))
            .map(Value::Number)
            .ok_or(AppError::Invalid("property_nonfinite"))?,
        Field::Double(value) if value.is_finite() => Number::from_f64(value)
            .map(Value::Number)
            .ok_or(AppError::Invalid("property_nonfinite"))?,
        Field::Str(value) => Value::String(value),
        _ => return Err(AppError::Invalid("property_value")),
    })
}

fn count_json(value: &Value, depth: usize, count: &mut usize) -> Result<(), AppError> {
    if depth > MAX_JSON_DEPTH {
        return Err(AppError::Limit("json_depth_limit"));
    }
    *count = count
        .checked_add(1)
        .ok_or(AppError::Limit("json_value_limit"))?;
    if *count > MAX_JSON_VALUES {
        return Err(AppError::Limit("json_value_limit"));
    }
    match value {
        Value::Array(values) => values
            .iter()
            .try_for_each(|value| count_json(value, depth + 1, count)),
        Value::Object(values) => values
            .values()
            .try_for_each(|value| count_json(value, depth + 1, count)),
        _ => Ok(()),
    }
}

fn merge_bounds(target: &mut [f64; 4], source: [f64; 4]) {
    target[0] = target[0].min(source[0]);
    target[1] = target[1].min(source[1]);
    target[2] = target[2].max(source[2]);
    target[3] = target[3].max(source[3]);
}

fn is_geometry_type(name: &str) -> bool {
    let name = name.strip_suffix(" Z").unwrap_or(name);
    matches!(
        name,
        "Point"
            | "LineString"
            | "Polygon"
            | "MultiPoint"
            | "MultiLineString"
            | "MultiPolygon"
            | "GeometryCollection"
    )
}

fn is_projjson_type(name: &str) -> bool {
    matches!(
        name,
        "GeographicCRS"
            | "ProjectedCRS"
            | "VerticalCRS"
            | "CompoundCRS"
            | "BoundCRS"
            | "EngineeringCRS"
            | "ParametricCRS"
            | "TemporalCRS"
    )
}

fn map_preflight_error(code: &'static str) -> AppError {
    if code.contains("limit") || code.contains("size") {
        AppError::Limit(code)
    } else {
        AppError::Invalid(code)
    }
}

fn write_payload(config: &Config, payload: &Value) -> Result<(), AppError> {
    let bytes = serde_json::to_vec(payload).map_err(|_| AppError::Output)?;
    let total_bytes = bytes
        .len()
        .checked_add(1)
        .ok_or(AppError::Limit("payload_limit"))?;
    if total_bytes as u64 > config.max_payload_bytes {
        return Err(AppError::Limit("payload_limit"));
    }
    let partial = config.output_path.with_extension("json.partial");
    if partial.exists() {
        return Err(AppError::Output);
    }
    let result = (|| {
        let file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .mode(0o600)
            .custom_flags(O_NOFOLLOW | O_CLOEXEC)
            .open(&partial)
            .map_err(|_| AppError::Output)?;
        let mut writer = BufWriter::new(file);
        writer
            .write_all(&bytes)
            .and_then(|_| writer.write_all(b"\n"))
            .map_err(|_| AppError::Output)?;
        writer.flush().map_err(|_| AppError::Output)?;
        writer.get_ref().sync_all().map_err(|_| AppError::Output)?;
        drop(writer);
        rename_no_replace(&partial, &config.output_path)?;
        let parent = OpenOptions::new()
            .read(true)
            .custom_flags(O_DIRECTORY | O_CLOEXEC)
            .open(config.output_path.parent().ok_or(AppError::Output)?)
            .map_err(|_| AppError::Output)?;
        parent.sync_all().map_err(|_| AppError::Output)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&partial);
    }
    result
}

const O_CLOEXEC: i32 = 0x80000;
const O_DIRECTORY: i32 = 0x10000;
const O_NOFOLLOW: i32 = 0x20000;
const AT_FDCWD: i32 = -100;
const RENAME_NOREPLACE: u32 = 1;

unsafe extern "C" {
    fn renameat2(
        old_directory_fd: i32,
        old_path: *const i8,
        new_directory_fd: i32,
        new_path: *const i8,
        flags: u32,
    ) -> i32;
}

fn rename_no_replace(source: &std::path::Path, target: &std::path::Path) -> Result<(), AppError> {
    let source = CString::new(source.as_os_str().as_bytes()).map_err(|_| AppError::Output)?;
    let target = CString::new(target.as_os_str().as_bytes()).map_err(|_| AppError::Output)?;
    // SAFETY: both C strings remain valid for the call. RENAME_NOREPLACE makes
    // publication atomic without replacing a path created by another process.
    if unsafe {
        renameat2(
            AT_FDCWD,
            source.as_ptr(),
            AT_FDCWD,
            target.as_ptr(),
            RENAME_NOREPLACE,
        )
    } != 0
    {
        return Err(AppError::Output);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{Config, parse_file, write_payload};
    use serde_json::json;
    use std::fs;
    use std::os::unix::fs::symlink;
    use std::path::PathBuf;

    fn fixture(name: &str) -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../../../../docs/work-packages/20261116_vector_upload_normalization/artifacts/red_fixtures")
            .join(name)
    }

    fn config(name: &str) -> Config {
        let input_path = fixture(name);
        Config {
            request_root: input_path.parent().unwrap().to_owned(),
            input_path,
            output_path: PathBuf::from("unused"),
            max_payload_bytes: 16 * 1024 * 1024,
            max_input_bytes: 100 * 1024 * 1024,
            max_features: 100_000,
            max_vertices_per_feature: 250_000,
            max_memory_bytes: 384 * 1024 * 1024,
            max_cpu_seconds: 60,
            max_open_files: 32,
        }
    }

    #[test]
    fn valid_controls_decode() {
        for name in [
            "polygon-1.0.0-none.parquet",
            "polygon-1.1.0-snappy.parquet",
            "dictionary-control.parquet",
            "data-page-v2-control.parquet",
            "data-page-v2-snappy-control.parquet",
            "multiple-row-groups-control.parquet",
            "projected-crs-control.parquet",
        ] {
            let payload =
                parse_file(&config(name)).unwrap_or_else(|error| panic!("{name}: {error:?}"));
            assert_eq!(payload["schema"], "geoparquet-parser-v1");
        }
    }

    #[test]
    fn hostile_controls_reject() {
        for name in [
            "footer-list-bomb.parquet",
            "page-declared-expansion.parquet",
            "dictionary-value-count.parquet",
            "codec-gzip.parquet",
            "encoding-delta.parquet",
            "wkb-count-bomb.parquet",
            "coordinates-nonfinite.parquet",
            "crs-null.parquet",
            "external-path.parquet",
            "data-page-v2-row-mismatch.parquet",
            "data-page-v2-snappy-flag-mismatch.parquet",
        ] {
            assert!(parse_file(&config(name)).is_err(), "{name} was admitted");
        }
    }

    #[test]
    fn representative_rejections_have_stable_codes() {
        for (name, expected) in [
            ("magic-head.parquet", "magic"),
            ("page-declared-expansion.parquet", "page_size"),
            ("codec-gzip.parquet", "codec"),
            ("crs-null.parquet", "crs_null"),
            ("wkb-truncated.parquet", "wkb_invalid"),
        ] {
            let error = parse_file(&config(name)).expect_err(name);
            assert_eq!(error.stable_code(), expected, "{name}");
        }
    }

    #[test]
    fn complete_manifest_matches_parser_boundary() {
        let manifest: serde_json::Value =
            serde_json::from_slice(&std::fs::read(fixture("manifest.json")).unwrap()).unwrap();
        let mut checked = 0;
        for entry in manifest["fixtures"].as_array().unwrap() {
            let name = entry["file"].as_str().unwrap();
            if !name.ends_with(".parquet") {
                continue;
            }
            let expected = entry["expected"].as_str().unwrap();
            let category = entry["category"].as_str().unwrap();
            let result = parse_file(&config(name));
            let parser_accepts = expected == "convert" || category == "workflow-rejection";
            assert_eq!(
                result.is_ok(),
                parser_accepts,
                "unexpected parser disposition for {name}: {result:?}"
            );
            checked += 1;
        }
        assert_eq!(checked, 49);
    }

    fn scratch(name: &str) -> PathBuf {
        std::env::temp_dir().join(format!(
            "geoparquet-parser-test-{}-{name}",
            std::process::id()
        ))
    }

    #[test]
    fn rejects_symlink_input_at_descriptor_boundary() {
        let root = scratch("symlink");
        fs::create_dir_all(&root).unwrap();
        let link = root.join("input.parquet");
        symlink(fixture("polygon-1.0.0-none.parquet"), &link).unwrap();
        let result = super::preflight::open(&root, &link, 100 * 1024 * 1024);
        assert!(result.is_err());
        fs::remove_file(link).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn same_length_mutation_changes_descriptor_identity() {
        let root = scratch("identity");
        fs::create_dir_all(&root).unwrap();
        let input = root.join("input.parquet");
        fs::copy(fixture("polygon-1.0.0-none.parquet"), &input).unwrap();
        let opened = super::preflight::open(&root, &input, 100 * 1024 * 1024).unwrap();
        let mut bytes = fs::read(&input).unwrap();
        let index = bytes.len() / 2;
        bytes[index] ^= 1;
        fs::write(&input, bytes).unwrap();
        assert_ne!(
            super::sha256::file(&opened.source, opened.identity.len).unwrap(),
            opened.digest
        );
        fs::remove_file(input).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn output_publish_never_replaces_existing_target() {
        let root = scratch("no-replace");
        fs::create_dir_all(&root).unwrap();
        let output = root.join("output.json");
        fs::write(&output, b"sentinel").unwrap();
        let mut cfg = config("polygon-1.0.0-none.parquet");
        cfg.output_path = output.clone();
        assert!(write_payload(&cfg, &json!({"new": true})).is_err());
        assert_eq!(fs::read(&output).unwrap(), b"sentinel");
        assert!(!output.with_extension("json.partial").exists());
        fs::remove_file(output).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn payload_limit_includes_trailing_newline() {
        let root = scratch("payload-limit");
        fs::create_dir_all(&root).unwrap();
        let payload = json!({"a": 1});
        let mut cfg = config("polygon-1.0.0-none.parquet");
        cfg.output_path = root.join("output.json");
        cfg.max_payload_bytes = serde_json::to_vec(&payload).unwrap().len() as u64;
        assert!(write_payload(&cfg, &payload).is_err());
        assert!(!cfg.output_path.exists());
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn json_value_budget_accepts_exact_and_rejects_plus_one() {
        let exact =
            serde_json::Value::Array(vec![serde_json::Value::Null; super::MAX_JSON_VALUES - 1]);
        let mut count = 0;
        assert!(super::count_json(&exact, 0, &mut count).is_ok());
        assert_eq!(count, super::MAX_JSON_VALUES);
        let plus_one =
            serde_json::Value::Array(vec![serde_json::Value::Null; super::MAX_JSON_VALUES]);
        let mut count = 0;
        assert_eq!(
            super::count_json(&plus_one, 0, &mut count)
                .unwrap_err()
                .stable_code(),
            "json_value_limit"
        );
    }

    #[test]
    fn geo_metadata_budget_accepts_exact_and_rejects_plus_one() {
        assert!(super::within_geo_metadata_limit(super::MAX_GEO_METADATA));
        assert!(!super::within_geo_metadata_limit(
            super::MAX_GEO_METADATA + 1
        ));
    }

    #[test]
    fn json_depth_budget_accepts_exact_and_rejects_plus_one() {
        fn nested(depth: usize) -> serde_json::Value {
            let mut value = serde_json::Value::Null;
            for _ in 0..depth {
                value = serde_json::Value::Array(vec![value]);
            }
            value
        }
        let mut count = 0;
        assert!(super::count_json(&nested(super::MAX_JSON_DEPTH), 0, &mut count).is_ok());
        let mut count = 0;
        assert_eq!(
            super::count_json(&nested(super::MAX_JSON_DEPTH + 1), 0, &mut count)
                .unwrap_err()
                .stable_code(),
            "json_depth_limit"
        );
    }

    #[test]
    fn payload_budget_accepts_exact_serialized_size() {
        let root = scratch("payload-exact");
        fs::create_dir_all(&root).unwrap();
        let payload = json!({"a": 1});
        let mut cfg = config("polygon-1.0.0-none.parquet");
        cfg.output_path = root.join("output.json");
        cfg.max_payload_bytes = (serde_json::to_vec(&payload).unwrap().len() + 1) as u64;
        write_payload(&cfg, &payload).unwrap();
        assert_eq!(
            fs::metadata(&cfg.output_path).unwrap().len(),
            cfg.max_payload_bytes
        );
        fs::remove_file(cfg.output_path).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn literal_ipc_budget_accepts_exact_and_rejects_plus_one() {
        let root = scratch("payload-literal-edge");
        fs::create_dir_all(&root).unwrap();
        let cap = 16 * 1024 * 1024;
        let empty = serde_json::to_vec(&json!({"data": ""})).unwrap().len();
        let exact = json!({"data": "x".repeat(cap - empty - 1)});
        let mut cfg = config("polygon-1.0.0-none.parquet");
        cfg.output_path = root.join("exact.json");
        cfg.max_payload_bytes = cap as u64;
        write_payload(&cfg, &exact).unwrap();
        assert_eq!(fs::metadata(&cfg.output_path).unwrap().len(), cap as u64);
        fs::remove_file(&cfg.output_path).unwrap();

        let plus_one = json!({"data": "x".repeat(cap - empty)});
        cfg.output_path = root.join("plus-one.json");
        assert!(write_payload(&cfg, &plus_one).is_err());
        assert!(!cfg.output_path.exists());
        fs::remove_dir(root).unwrap();
    }
}

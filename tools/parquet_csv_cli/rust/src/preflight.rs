// Derived from owned shape-converter preflight.rs at dff2f29f7.
// CSV-specific envelope: ADR-0148; no changes to production parser.
use crate::compact::scan_struct;
use parquet::basic::{Compression, Encoding, Repetition};
use parquet::file::reader::{FileReader, SerializedFileReader};
use parquet::schema::types::SchemaDescriptor;
use std::ffi::CString;
use std::fs::{File, OpenOptions};
use std::os::fd::{AsRawFd, FromRawFd};
use std::os::unix::fs::{FileExt, MetadataExt, OpenOptionsExt};
use std::path::Path;

const FOOTER_MAX: usize = 1024 * 1024;
const PAGE_HEADER_MAX: usize = 64 * 1024;
const PAGE_BODY_MAX: u64 = 8 * 1024 * 1024;
const DECODED_PAGES_MAX: u64 = 4 * 1024 * 1024 * 1024;
const ROWS_MAX: i64 = 10_000_000;
const ROW_GROUPS_MAX: usize = 128;
const COLUMNS_MAX: usize = 128;
const PAGES_MAX: usize = 200_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Identity {
    dev: u64,
    ino: u64,
    pub len: u64,
    modified_seconds: i64,
    modified_nanoseconds: i64,
    changed_seconds: i64,
    changed_nanoseconds: i64,
}

pub struct Preflighted {
    pub reader: SerializedFileReader<File>,
    pub source: File,
    pub identity: Identity,
    pub digest: [u8; 32],
}

pub fn open(
    request_root: &Path,
    path: &Path,
    max_input_bytes: u64,
) -> Result<Preflighted, &'static str> {
    let source = open_beneath(request_root, path)?;
    let original_identity = identity(&source)?;
    if original_identity.len > max_input_bytes || original_identity.len < 12 {
        return Err("input_size");
    }
    let digest = crate::sha256::file(&source, original_identity.len)?;
    if identity(&source)? != original_identity {
        return Err("input_changed");
    }
    let (footer, footer_start) = read_footer(&source, original_identity.len)?;
    let scan = scan_struct(&footer, 16, 8_192, FOOTER_MAX).map_err(|_| "footer_structure")?;
    if scan.consumed != footer.len() {
        return Err("footer_trailing");
    }
    if scan.fields.contains(&vec![8])
        || scan.fields.contains(&vec![9])
        || scan.fields.iter().any(|path| {
            path.len() >= 3 && path[path.len() - 3..] == [4, 1, 8]
                || path.len() >= 3 && path[path.len() - 3..] == [4, 1, 9]
        })
    {
        return Err("encryption");
    }
    validate_footer_container_limits(&scan)?;
    let schema_count = scan.containers.get(&vec![2]).copied().unwrap_or(0);
    let schema_children = scan.integer_values.get(&vec![2, 5]);
    let schema_types = scan.integer_values.get(&vec![2, 1]);
    let schema_repetitions = scan.integer_values.get(&vec![2, 3]);
    if !(2..=COLUMNS_MAX + 1).contains(&schema_count)
        || schema_children
            .is_none_or(|values| values.len() != 1 || values[0] != (schema_count - 1) as i64)
        || schema_types.is_none_or(|values| values.len() != schema_count - 1)
        || schema_repetitions.is_none_or(|values| {
            !matches!(values.len(), value if value == schema_count - 1 || value == schema_count)
                || values.iter().any(|value| !matches!(value, 0 | 1))
        })
    {
        return Err("schema_structure");
    }

    let reader = SerializedFileReader::new(source.try_clone().map_err(|_| "input_open")?)
        .map_err(|_| "metadata_decode")?;
    validate_metadata(&source, footer_start, &reader)?;
    if identity(&source)? != original_identity {
        return Err("input_changed");
    }
    Ok(Preflighted {
        reader,
        source,
        identity: original_identity,
        digest,
    })
}

fn validate_footer_container_limits(scan: &crate::compact::ScanResult) -> Result<(), &'static str> {
    for (path, limit) in [
        (vec![2], COLUMNS_MAX + 1),
        (vec![4], ROW_GROUPS_MAX),
        (vec![4, 1], COLUMNS_MAX),
        (vec![5], 256_usize),
        (vec![4, 1, 3, 2], 4_usize),
        (vec![4, 1, 3, 3], 1_usize),
    ] {
        enforce_count(
            scan.containers.get(&path).copied().unwrap_or(0),
            limit,
            "footer_structure_limit",
        )?;
    }
    Ok(())
}

const O_NONBLOCK: i32 = 0x800;
const O_CLOEXEC: i32 = 0x80000;
const O_DIRECTORY: i32 = 0x10000;
const O_NOFOLLOW: i32 = 0x20000;
const O_RDONLY: i32 = 0;

unsafe extern "C" {
    fn openat(directory_fd: i32, path: *const i8, flags: i32) -> i32;
}

fn open_beneath(request_root: &Path, path: &Path) -> Result<File, &'static str> {
    let canonical_root = request_root.canonicalize().map_err(|_| "input_open")?;
    let canonical_parent = path
        .parent()
        .ok_or("input_open")?
        .canonicalize()
        .map_err(|_| "input_open")?;
    if canonical_parent != canonical_root {
        return Err("input_containment");
    }
    let filename = path
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or("input_open")?;
    if filename.is_empty() || filename == "." || filename == ".." || filename.contains('/') {
        return Err("input_open");
    }
    let directory = OpenOptions::new()
        .read(true)
        .custom_flags(O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        .open(&canonical_root)
        .map_err(|_| "input_open")?;
    let filename = CString::new(filename).map_err(|_| "input_open")?;
    // SAFETY: the directory descriptor and NUL-terminated basename remain valid
    // for this call. The basename has no separators and O_NOFOLLOW rejects a
    // symlink at the only untrusted path component.
    let descriptor = unsafe {
        openat(
            directory.as_raw_fd(),
            filename.as_ptr(),
            O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW,
        )
    };
    if descriptor < 0 {
        return Err("input_open");
    }
    // SAFETY: openat returned a new owned descriptor on success.
    Ok(unsafe { File::from_raw_fd(descriptor) })
}

pub fn identity(file: &File) -> Result<Identity, &'static str> {
    let metadata = file.metadata().map_err(|_| "input_stat")?;
    if !metadata.is_file() {
        return Err("input_type");
    }
    Ok(Identity {
        dev: metadata.dev(),
        ino: metadata.ino(),
        len: metadata.len(),
        modified_seconds: metadata.mtime(),
        modified_nanoseconds: metadata.mtime_nsec(),
        changed_seconds: metadata.ctime(),
        changed_nanoseconds: metadata.ctime_nsec(),
    })
}

fn read_footer(file: &File, length: u64) -> Result<(Vec<u8>, u64), &'static str> {
    let mut head = [0_u8; 4];
    read_exact_at(file, &mut head, 0)?;
    if &head != b"PAR1" {
        return Err("magic");
    }
    let mut trailer = [0_u8; 8];
    read_exact_at(file, &mut trailer, length - 8)?;
    if &trailer[4..] != b"PAR1" {
        return Err("magic");
    }
    let footer_len = usize::try_from(u32::from_le_bytes(
        trailer[..4].try_into().map_err(|_| "footer")?,
    ))
    .map_err(|_| "footer")?;
    if footer_len == 0 || footer_len > FOOTER_MAX || (footer_len as u64) > length - 12 {
        return Err("footer_size");
    }
    let offset = length - 8 - footer_len as u64;
    let mut footer = vec![0_u8; footer_len];
    read_exact_at(file, &mut footer, offset)?;
    Ok((footer, offset))
}

fn validate_metadata(
    file: &File,
    footer_start: u64,
    reader: &SerializedFileReader<File>,
) -> Result<(), &'static str> {
    let metadata = reader.metadata();
    let file_metadata = metadata.file_metadata();
    let rows = file_metadata.num_rows();
    if !(0..=ROWS_MAX).contains(&rows) {
        return Err("row_limit");
    }
    let row_groups = metadata.num_row_groups();
    if (row_groups == 0 && rows != 0) || row_groups > ROW_GROUPS_MAX {
        return Err("row_group_limit");
    }
    validate_schema(file_metadata.schema_descr())?;

    let mut aggregate_uncompressed = 0_u64;
    let mut row_total = 0_i64;
    let mut ranges = Vec::new();
    let mut aggregate_pages = 0_usize;
    for row_group in metadata.row_groups() {
        if row_group.num_rows() < 0 || row_group.num_rows() > ROWS_MAX {
            return Err("row_limit");
        }
        row_total = row_total
            .checked_add(row_group.num_rows())
            .ok_or("row_limit")?;
        for column in row_group.columns() {
            if column.file_path().is_some() {
                return Err("external_column");
            }
            if !matches!(
                column.compression(),
                Compression::UNCOMPRESSED | Compression::SNAPPY | Compression::ZSTD(_)
            ) {
                return Err("codec");
            }
            if column.num_values() != row_group.num_rows() {
                return Err("value_limit");
            }
            if !column.encodings().all(allowed_encoding) {
                return Err("encoding");
            }
            let start = column
                .dictionary_page_offset()
                .unwrap_or_else(|| column.data_page_offset());
            let length = column.compressed_size();
            // Parquet writers represent an empty non-dictionary column with
            // zero offsets and no pages. Validate its policy above, then its
            // exact empty metadata before skipping physical-page scanning.
            if row_group.num_rows() == 0
                && length == 0
                && start == 0
                && column.uncompressed_size() == 0
                && column.dictionary_page_offset().is_none()
            {
                continue;
            }
            if start < 4 || length <= 0 {
                return Err("page_range");
            }
            let start = u64::try_from(start).map_err(|_| "page_range")?;
            let length = u64::try_from(length).map_err(|_| "page_range")?;
            let end = start.checked_add(length).ok_or("page_range")?;
            if end > footer_start
                || (column.data_page_offset() < i64::try_from(start).map_err(|_| "page_range")?
                    && !(column.num_values() == 0 && column.data_page_offset() == 0))
                || u64::try_from(column.data_page_offset()).map_err(|_| "page_range")? >= end
            {
                return Err("page_range");
            }
            let expectations = ColumnExpectations {
                data_offset: u64::try_from(column.data_page_offset()).map_err(|_| "page_range")?,
                values: column.num_values(),
                uncompressed: u64::try_from(column.uncompressed_size()).map_err(|_| "page_size")?,
                uncompressed_codec: column.compression() == Compression::UNCOMPRESSED,
            };
            scan_column_pages(
                file,
                start,
                end,
                expectations,
                &mut aggregate_uncompressed,
                &mut aggregate_pages,
            )?;
            ranges.push((start, end));
        }
    }
    if row_total != rows {
        return Err("row_count_mismatch");
    }
    ranges.sort_unstable();
    if ranges.windows(2).any(|pair| pair[0].1 > pair[1].0) {
        return Err("page_range_overlap");
    }
    if aggregate_uncompressed > DECODED_PAGES_MAX {
        return Err("decoded_page_limit");
    }
    Ok(())
}

fn validate_schema(schema: &SchemaDescriptor) -> Result<(), &'static str> {
    if schema.num_columns() == 0 || schema.num_columns() > COLUMNS_MAX {
        return Err("schema_columns");
    }
    let fields = schema.root_schema().get_fields();
    if fields.len() != schema.num_columns() {
        return Err("nested_schema");
    }
    for field in fields {
        if !field.is_primitive() || field.get_basic_info().repetition() == Repetition::REPEATED {
            return Err("schema");
        }
    }
    Ok(())
}

struct ColumnExpectations {
    data_offset: u64,
    values: i64,
    uncompressed: u64,
    uncompressed_codec: bool,
}

fn scan_column_pages(
    file: &File,
    start: u64,
    end: u64,
    expected: ColumnExpectations,
    aggregate_uncompressed: &mut u64,
    aggregate_pages: &mut usize,
) -> Result<(), &'static str> {
    let mut offset = start;
    let mut page_count = 0_usize;
    let mut saw_dictionary = false;
    let mut saw_data = false;
    let mut data_values = 0_i64;
    let mut column_uncompressed = 0_u64;
    let mut first_data_offset = None;
    while offset < end {
        page_count = page_count.checked_add(1).ok_or("page_limit")?;
        *aggregate_pages = aggregate_pages.checked_add(1).ok_or("page_limit")?;
        enforce_count(page_count, 100_000, "page_limit")?;
        enforce_count(*aggregate_pages, PAGES_MAX, "page_limit")?;
        let available = usize::try_from((end - offset).min(PAGE_HEADER_MAX as u64))
            .map_err(|_| "page_header")?;
        let mut header = vec![0_u8; available];
        read_exact_at(file, &mut header, offset)?;
        let scan = scan_struct(&header, 16, 100_000, PAGE_HEADER_MAX).map_err(|_| "page_header")?;
        if scan.consumed == 0 || scan.consumed > PAGE_HEADER_MAX {
            return Err("page_header");
        }
        let page_type = required(&scan.integers, &[1])?;
        let uncompressed = positive_or_zero(required(&scan.integers, &[2])?)?;
        let compressed = positive_or_zero(required(&scan.integers, &[3])?)?;
        if uncompressed > PAGE_BODY_MAX || compressed > PAGE_BODY_MAX {
            return Err("page_size");
        }
        if expected.uncompressed_codec && compressed != uncompressed {
            return Err("page_size");
        }
        *aggregate_uncompressed = aggregate_uncompressed
            .checked_add(uncompressed)
            .ok_or("decoded_page_limit")?;
        column_uncompressed = column_uncompressed
            .checked_add(uncompressed)
            .and_then(|value| value.checked_add(scan.consumed as u64))
            .ok_or("decoded_page_limit")?;
        if *aggregate_uncompressed > DECODED_PAGES_MAX {
            return Err("decoded_page_limit");
        }
        match page_type {
            0 => {
                if !scan.fields.contains(&vec![5])
                    || scan.fields.contains(&vec![7])
                    || scan.fields.contains(&vec![8])
                    || scan.fields.contains(&vec![6])
                {
                    return Err("page_header");
                }
                let values = required(&scan.integers, &[5, 1])?;
                if !(0..=ROWS_MAX).contains(&values)
                    || !allowed_encoding_number(required(&scan.integers, &[5, 2])?)
                    || required(&scan.integers, &[5, 3])? != 3
                    || required(&scan.integers, &[5, 4])? != 3
                {
                    return Err("page_encoding");
                }
                data_values = data_values.checked_add(values).ok_or("value_limit")?;
                first_data_offset.get_or_insert(offset);
                saw_data = true;
            }
            2 => {
                if !scan.fields.contains(&vec![7])
                    || scan.fields.contains(&vec![5])
                    || scan.fields.contains(&vec![8])
                    || scan.fields.contains(&vec![6])
                {
                    return Err("page_header");
                }
                let entries = required(&scan.integers, &[7, 1])?;
                if saw_dictionary
                    || saw_data
                    || !(0..=131_072).contains(&entries)
                    || (expected.values == 0 && entries != 0)
                    || !matches!(required(&scan.integers, &[7, 2])?, 0 | 2)
                {
                    return Err("dictionary");
                }
                saw_dictionary = true;
            }
            3 => {
                if !scan.fields.contains(&vec![8])
                    || scan.fields.contains(&vec![5])
                    || scan.fields.contains(&vec![7])
                    || scan.fields.contains(&vec![6])
                {
                    return Err("page_header");
                }
                let values = required(&scan.integers, &[8, 1])?;
                let nulls = required(&scan.integers, &[8, 2])?;
                let rows = required(&scan.integers, &[8, 3])?;
                let definition = positive_or_zero(required(&scan.integers, &[8, 5])?)?;
                let repetition = positive_or_zero(required(&scan.integers, &[8, 6])?)?;
                let is_compressed = scan.booleans.get(&vec![8, 7]).copied().unwrap_or(true);
                if values < 0
                    || nulls < 0
                    || rows < 0
                    || nulls > values
                    || rows != values
                    || values > ROWS_MAX
                    || rows > ROWS_MAX
                    || !allowed_encoding_number(required(&scan.integers, &[8, 4])?)
                    || definition.checked_add(repetition).ok_or("page_size")? > compressed
                    || definition.checked_add(repetition).ok_or("page_size")? > uncompressed
                    || (!is_compressed && compressed != uncompressed)
                {
                    return Err("page_header");
                }
                data_values = data_values.checked_add(values).ok_or("value_limit")?;
                first_data_offset.get_or_insert(offset);
                saw_data = true;
            }
            _ => return Err("page_type"),
        }
        let next = offset
            .checked_add(scan.consumed as u64)
            .and_then(|value| value.checked_add(compressed))
            .ok_or("page_range")?;
        if next <= offset || next > end {
            return Err("page_range");
        }
        offset = next;
    }
    if offset != end
        || !(saw_data || expected.values == 0 && expected.data_offset == 0)
        // Some retained WEPP event files declare the column start (dictionary
        // offset) as data_page_offset. Accept only that bounded alias: every
        // intervening page was scanned and the first data page was observed.
        || (first_data_offset != Some(expected.data_offset)
            && !(saw_dictionary && expected.data_offset == start && first_data_offset.is_some())
            && !(expected.values == 0 && expected.data_offset == 0 && first_data_offset.is_none()))
        || data_values != expected.values
        || column_uncompressed != expected.uncompressed
    {
        return Err("page_range");
    }
    Ok(())
}

fn required(
    values: &std::collections::BTreeMap<Vec<i16>, i64>,
    path: &[i16],
) -> Result<i64, &'static str> {
    values.get(path).copied().ok_or("page_header")
}

fn enforce_count(value: usize, limit: usize, code: &'static str) -> Result<(), &'static str> {
    if value > limit { Err(code) } else { Ok(()) }
}

fn positive_or_zero(value: i64) -> Result<u64, &'static str> {
    if value < 0 {
        Err("page_size")
    } else {
        u64::try_from(value).map_err(|_| "page_size")
    }
}

fn allowed_encoding(encoding: Encoding) -> bool {
    matches!(
        encoding,
        Encoding::PLAIN | Encoding::RLE | Encoding::PLAIN_DICTIONARY | Encoding::RLE_DICTIONARY
    )
}

fn allowed_encoding_number(value: i64) -> bool {
    matches!(value, 0 | 2 | 3 | 8)
}

fn read_exact_at(file: &File, buffer: &mut [u8], mut offset: u64) -> Result<(), &'static str> {
    let mut filled = 0;
    while filled < buffer.len() {
        let read = file
            .read_at(&mut buffer[filled..], offset)
            .map_err(|_| "input_read")?;
        if read == 0 {
            return Err("input_read");
        }
        filled += read;
        offset = offset.checked_add(read as u64).ok_or("input_read")?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        ColumnExpectations, DECODED_PAGES_MAX, FOOTER_MAX, PAGE_BODY_MAX, PAGES_MAX,
        ROW_GROUPS_MAX, enforce_count, read_footer, scan_column_pages,
        validate_footer_container_limits,
    };
    use crate::compact::scan_struct;
    use std::fs::{self, OpenOptions};
    use std::io::Write;

    #[test]
    fn exact_count_edges_admit_limit_and_reject_limit_plus_one() {
        for limit in [ROW_GROUPS_MAX, PAGES_MAX] {
            assert!(enforce_count(limit, limit, "limit").is_ok());
            assert_eq!(enforce_count(limit + 1, limit, "limit"), Err("limit"));
        }
    }

    #[test]
    fn row_group_limit_is_extracted_from_compact_footer() {
        for (count, expected) in [
            (ROW_GROUPS_MAX, Ok(())),
            (ROW_GROUPS_MAX + 1, Err("footer_structure_limit")),
        ] {
            let mut encoded = vec![0x49, 0xfc, (count & 0x7f) as u8 | 0x80, (count >> 7) as u8];
            encoded.extend(std::iter::repeat_n(0_u8, count));
            encoded.push(0);
            let scan = scan_struct(&encoded, 16, 8_192, 1024 * 1024).unwrap();
            assert_eq!(scan.containers.get(&vec![4]), Some(&count));
            assert_eq!(validate_footer_container_limits(&scan), expected);
        }
    }

    fn varint(mut value: u64) -> Vec<u8> {
        let mut output = Vec::new();
        loop {
            let mut byte = (value & 0x7f) as u8;
            value >>= 7;
            if value != 0 {
                byte |= 0x80;
            }
            output.push(byte);
            if value == 0 {
                return output;
            }
        }
    }

    fn page(size: u64) -> Vec<u8> {
        let mut header = vec![0x15, 0];
        header.push(0x15);
        header.extend(varint(size * 2));
        header.push(0x15);
        header.extend(varint(size * 2));
        header.extend([0x2c, 0x15, 0, 0x15, 0, 0x15, 6, 0x15, 6, 0, 0]);
        header.resize(header.len() + size as usize, 0);
        header
    }

    fn dictionary_page(entries: u64) -> Vec<u8> {
        let mut bytes = vec![0x15, 4, 0x15, 2, 0x15, 2, 0x4c, 0x15];
        bytes.extend(varint(entries * 2));
        bytes.extend([0x15, 0, 0, 0]);
        bytes.push(0);
        bytes
    }

    fn temporary(name: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "geoparquet-preflight-{}-{name}",
            std::process::id()
        ))
    }

    #[test]
    fn page_body_and_aggregate_ledgers_accept_exact_and_reject_plus_one() {
        let exact = page(PAGE_BODY_MAX);
        let path = temporary("page-body");
        fs::write(&path, &exact).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        let expected = ColumnExpectations {
            data_offset: 0,
            values: 0,
            uncompressed: exact.len() as u64,
            uncompressed_codec: true,
        };
        let mut decoded = DECODED_PAGES_MAX - PAGE_BODY_MAX;
        let mut pages = PAGES_MAX - 1;
        assert!(
            scan_column_pages(
                &file,
                0,
                exact.len() as u64,
                expected,
                &mut decoded,
                &mut pages
            )
            .is_ok()
        );
        assert_eq!(decoded, DECODED_PAGES_MAX);
        assert_eq!(pages, PAGES_MAX);

        let too_large = page(PAGE_BODY_MAX + 1);
        fs::write(&path, &too_large[..64 * 1024]).unwrap();
        let file = OpenOptions::new().read(true).open(&path).unwrap();
        let expected = ColumnExpectations {
            data_offset: 0,
            values: 0,
            uncompressed: too_large.len() as u64,
            uncompressed_codec: true,
        };
        let mut decoded = 0;
        let mut pages = 0;
        assert_eq!(
            scan_column_pages(
                &file,
                0,
                too_large.len() as u64,
                expected,
                &mut decoded,
                &mut pages
            ),
            Err("page_size")
        );
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn footer_length_accepts_exact_and_rejects_plus_one() {
        let path = temporary("footer");
        for (size, expected) in [(FOOTER_MAX, true), (FOOTER_MAX + 1, false)] {
            let mut file = OpenOptions::new()
                .create(true)
                .truncate(true)
                .write(true)
                .open(&path)
                .unwrap();
            file.write_all(b"PAR1").unwrap();
            file.write_all(&vec![0_u8; size]).unwrap();
            file.write_all(&(size as u32).to_le_bytes()).unwrap();
            file.write_all(b"PAR1").unwrap();
            drop(file);
            let file = OpenOptions::new().read(true).open(&path).unwrap();
            assert_eq!(
                read_footer(&file, fs::metadata(&path).unwrap().len()).is_ok(),
                expected
            );
        }
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn input_length_accepts_exact_budget_and_rejects_plus_one_before_magic() {
        let root = temporary("input-root");
        fs::create_dir(&root).unwrap();
        let path = root.join("input.parquet");
        let file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&path)
            .unwrap();
        file.set_len(100 * 1024 * 1024).unwrap();
        drop(file);
        assert!(matches!(
            super::open(&root, &path, 100 * 1024 * 1024),
            Err("magic")
        ));
        let file = OpenOptions::new().write(true).open(&path).unwrap();
        file.set_len(100 * 1024 * 1024 + 1).unwrap();
        drop(file);
        assert!(matches!(
            super::open(&root, &path, 100 * 1024 * 1024),
            Err("input_size")
        ));
        fs::remove_file(path).unwrap();
        fs::remove_dir(root).unwrap();
    }

    #[test]
    fn dictionary_entry_header_accepts_exact_and_rejects_plus_one() {
        let path = temporary("dictionary");
        for (entries, expected) in [(131_072, "page_range"), (131_073, "dictionary")] {
            let bytes = dictionary_page(entries);
            fs::write(&path, &bytes).unwrap();
            let file = OpenOptions::new().read(true).open(&path).unwrap();
            let column = ColumnExpectations {
                data_offset: 0,
                values: 1,
                uncompressed: bytes.len() as u64,
                uncompressed_codec: true,
            };
            let mut decoded = 0;
            let mut pages = 0;
            assert_eq!(
                scan_column_pages(
                    &file,
                    0,
                    bytes.len() as u64,
                    column,
                    &mut decoded,
                    &mut pages,
                ),
                Err(expected)
            );
        }
        fs::remove_file(path).unwrap();
    }
}

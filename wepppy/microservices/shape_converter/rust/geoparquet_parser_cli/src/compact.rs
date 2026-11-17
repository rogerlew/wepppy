use std::collections::{BTreeMap, BTreeSet};

const STOP: u8 = 0;
const BOOL_TRUE: u8 = 1;
const BOOL_FALSE: u8 = 2;
const BYTE: u8 = 3;
const I16: u8 = 4;
const I32: u8 = 5;
const I64: u8 = 6;
const DOUBLE: u8 = 7;
const BINARY: u8 = 8;
const LIST: u8 = 9;
const SET: u8 = 10;
const MAP: u8 = 11;
const STRUCT: u8 = 12;

#[derive(Debug)]
pub struct ScanResult {
    pub consumed: usize,
    pub integers: BTreeMap<Vec<i16>, i64>,
    pub integer_values: BTreeMap<Vec<i16>, Vec<i64>>,
    pub booleans: BTreeMap<Vec<i16>, bool>,
    pub fields: BTreeSet<Vec<i16>>,
    pub containers: BTreeMap<Vec<i16>, usize>,
}

pub fn scan_struct(
    bytes: &[u8],
    max_depth: usize,
    max_container: usize,
    max_binary: usize,
) -> Result<ScanResult, ()> {
    let mut scanner = Scanner {
        bytes,
        pos: 0,
        max_depth,
        max_container,
        max_binary,
        integers: BTreeMap::new(),
        integer_values: BTreeMap::new(),
        booleans: BTreeMap::new(),
        fields: BTreeSet::new(),
        containers: BTreeMap::new(),
    };
    scanner.read_struct(0, &mut Vec::new())?;
    Ok(ScanResult {
        consumed: scanner.pos,
        integers: scanner.integers,
        integer_values: scanner.integer_values,
        booleans: scanner.booleans,
        fields: scanner.fields,
        containers: scanner.containers,
    })
}

struct Scanner<'a> {
    bytes: &'a [u8],
    pos: usize,
    max_depth: usize,
    max_container: usize,
    max_binary: usize,
    integers: BTreeMap<Vec<i16>, i64>,
    integer_values: BTreeMap<Vec<i16>, Vec<i64>>,
    booleans: BTreeMap<Vec<i16>, bool>,
    fields: BTreeSet<Vec<i16>>,
    containers: BTreeMap<Vec<i16>, usize>,
}

impl Scanner<'_> {
    fn byte(&mut self) -> Result<u8, ()> {
        let value = *self.bytes.get(self.pos).ok_or(())?;
        self.pos += 1;
        Ok(value)
    }

    fn take(&mut self, length: usize) -> Result<(), ()> {
        self.pos = self.pos.checked_add(length).ok_or(())?;
        if self.pos > self.bytes.len() {
            return Err(());
        }
        Ok(())
    }

    fn varint(&mut self) -> Result<u64, ()> {
        let mut value = 0_u64;
        for shift in (0..70).step_by(7) {
            let byte = self.byte()?;
            if shift == 63 && byte > 1 {
                return Err(());
            }
            value |= u64::from(byte & 0x7f) << shift;
            if byte & 0x80 == 0 {
                return Ok(value);
            }
        }
        Err(())
    }

    fn zigzag(&mut self) -> Result<i64, ()> {
        let value = self.varint()?;
        Ok(((value >> 1) as i64) ^ (-((value & 1) as i64)))
    }

    fn read_struct(&mut self, depth: usize, path: &mut Vec<i16>) -> Result<(), ()> {
        if depth >= self.max_depth {
            return Err(());
        }
        let mut previous = 0_i16;
        loop {
            let header = self.byte()?;
            let kind = header & 0x0f;
            if kind == STOP {
                return Ok(());
            }
            let delta = i16::from(header >> 4);
            let field_id = if delta == 0 {
                i16::try_from(self.zigzag()?).map_err(|_| ())?
            } else {
                previous.checked_add(delta).ok_or(())?
            };
            if field_id <= 0 {
                return Err(());
            }
            path.push(field_id);
            self.fields.insert(path.clone());
            match kind {
                BOOL_TRUE => {
                    self.booleans.insert(path.clone(), true);
                }
                BOOL_FALSE => {
                    self.booleans.insert(path.clone(), false);
                }
                I16 | I32 | I64 => {
                    let value = self.zigzag()?;
                    self.integers.insert(path.clone(), value);
                    self.integer_values
                        .entry(path.clone())
                        .or_default()
                        .push(value);
                }
                _ => self.skip_value(kind, depth + 1, path, true)?,
            }
            path.pop();
            previous = field_id;
        }
    }

    fn skip_value(
        &mut self,
        kind: u8,
        depth: usize,
        path: &mut Vec<i16>,
        bool_in_field: bool,
    ) -> Result<(), ()> {
        match kind {
            BOOL_TRUE | BOOL_FALSE if bool_in_field => Ok(()),
            BOOL_TRUE | BOOL_FALSE | BYTE => self.take(1),
            I16 | I32 | I64 => {
                self.zigzag()?;
                Ok(())
            }
            DOUBLE => self.take(8),
            BINARY => {
                let length = usize::try_from(self.varint()?).map_err(|_| ())?;
                if length > self.max_binary {
                    return Err(());
                }
                self.take(length)
            }
            LIST | SET => {
                if depth >= self.max_depth {
                    return Err(());
                }
                let header = self.byte()?;
                let mut count = usize::from(header >> 4);
                let element = header & 0x0f;
                if count == 15 {
                    count = usize::try_from(self.varint()?).map_err(|_| ())?;
                }
                if count > self.max_container || element == STOP {
                    return Err(());
                }
                self.containers
                    .entry(path.clone())
                    .and_modify(|current| *current = (*current).max(count))
                    .or_insert(count);
                for _ in 0..count {
                    self.skip_value(element, depth + 1, path, false)?;
                }
                Ok(())
            }
            MAP => {
                if depth >= self.max_depth {
                    return Err(());
                }
                let count = usize::try_from(self.varint()?).map_err(|_| ())?;
                if count > self.max_container {
                    return Err(());
                }
                self.containers
                    .entry(path.clone())
                    .and_modify(|current| *current = (*current).max(count))
                    .or_insert(count);
                if count == 0 {
                    return Ok(());
                }
                let kinds = self.byte()?;
                let key = kinds >> 4;
                let value = kinds & 0x0f;
                if key == STOP || value == STOP {
                    return Err(());
                }
                for _ in 0..count {
                    self.skip_value(key, depth + 1, path, false)?;
                    self.skip_value(value, depth + 1, path, false)?;
                }
                Ok(())
            }
            STRUCT => self.read_struct(depth, path),
            _ => Err(()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::scan_struct;

    #[test]
    fn captures_page_header_fields() {
        // fields 1,2,3 as compact i32 values 0, 8 and 4.
        let bytes = [0x15, 0x00, 0x15, 0x10, 0x15, 0x08, 0x00];
        let scan = scan_struct(&bytes, 8, 32, 1024).unwrap();
        assert_eq!(scan.consumed, bytes.len());
        assert_eq!(scan.integers[&vec![1]], 0);
        assert_eq!(scan.integers[&vec![2]], 8);
        assert_eq!(scan.integers[&vec![3]], 4);
    }

    #[test]
    fn rejects_oversize_container_before_iteration() {
        let bytes = [0x19, 0xfc, 0xff, 0xff, 0xff, 0xff, 0x07, 0x00];
        assert!(scan_struct(&bytes, 8, 1024, 1024).is_err());
    }

    #[test]
    fn byte_budget_accepts_exact_and_rejects_plus_one() {
        fn binary_field(payload: usize) -> Vec<u8> {
            let mut bytes = vec![0x18];
            let mut remaining = payload;
            loop {
                let mut byte = (remaining & 0x7f) as u8;
                remaining >>= 7;
                if remaining != 0 {
                    byte |= 0x80;
                }
                bytes.push(byte);
                if remaining == 0 {
                    break;
                }
            }
            bytes.resize(bytes.len() + payload, 0);
            bytes.push(0);
            bytes
        }
        let exact = binary_field(65_531);
        assert_eq!(exact.len(), 65_536);
        assert_eq!(
            scan_struct(&exact, 8, 100_000, 65_536).unwrap().consumed,
            65_536
        );
        let plus_one = binary_field(65_532);
        assert_eq!(plus_one.len(), 65_537);
        assert!(scan_struct(&plus_one[..65_536], 8, 100_000, 65_536).is_err());
    }
}

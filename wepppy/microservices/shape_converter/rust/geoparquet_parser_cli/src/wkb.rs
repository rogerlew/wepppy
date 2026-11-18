use serde_json::{Number, Value};

const MAX_NESTING: usize = 16;

pub struct Geometry {
    pub value: Value,
    pub geometry_type: &'static str,
    pub dimensions: usize,
    pub bounds: [f64; 4],
}

pub fn parse(bytes: &[u8], max_vertices: usize) -> Result<Geometry, ()> {
    if !within_size_limit(bytes.len()) {
        return Err(());
    }
    let mut reader = Reader {
        bytes,
        pos: 0,
        max_vertices,
        vertices: 0,
        bounds: [
            f64::INFINITY,
            f64::INFINITY,
            f64::NEG_INFINITY,
            f64::NEG_INFINITY,
        ],
    };
    let (value, geometry_type, _, dimensions) = reader.geometry(0, None)?;
    if reader.pos != bytes.len()
        || reader.vertices == 0
        || !reader.bounds.iter().all(|v| v.is_finite())
    {
        return Err(());
    }
    Ok(Geometry {
        value,
        geometry_type,
        dimensions,
        bounds: reader.bounds,
    })
}

fn within_size_limit(length: usize) -> bool {
    length <= 4 * 1024 * 1024
}

struct Reader<'a> {
    bytes: &'a [u8],
    pos: usize,
    max_vertices: usize,
    vertices: usize,
    bounds: [f64; 4],
}

impl Reader<'_> {
    fn take<const N: usize>(&mut self) -> Result<[u8; N], ()> {
        let end = self.pos.checked_add(N).ok_or(())?;
        let slice = self.bytes.get(self.pos..end).ok_or(())?;
        self.pos = end;
        slice.try_into().map_err(|_| ())
    }

    fn u32(&mut self, little: bool) -> Result<u32, ()> {
        let bytes = self.take::<4>()?;
        Ok(if little {
            u32::from_le_bytes(bytes)
        } else {
            u32::from_be_bytes(bytes)
        })
    }

    fn f64(&mut self, little: bool) -> Result<f64, ()> {
        let bytes = self.take::<8>()?;
        let value = if little {
            f64::from_le_bytes(bytes)
        } else {
            f64::from_be_bytes(bytes)
        };
        if !value.is_finite() {
            return Err(());
        }
        Ok(value)
    }

    fn count(&mut self, little: bool) -> Result<usize, ()> {
        usize::try_from(self.u32(little)?).map_err(|_| ())
    }

    fn coordinate(&mut self, little: bool, dimensions: usize) -> Result<Value, ()> {
        self.vertices = self.vertices.checked_add(1).ok_or(())?;
        if self.vertices > self.max_vertices {
            return Err(());
        }
        let x = self.f64(little)?;
        let y = self.f64(little)?;
        self.bounds[0] = self.bounds[0].min(x);
        self.bounds[1] = self.bounds[1].min(y);
        self.bounds[2] = self.bounds[2].max(x);
        self.bounds[3] = self.bounds[3].max(y);
        let mut coordinate = vec![number(x)?, number(y)?];
        if dimensions == 3 {
            coordinate.push(number(self.f64(little)?)?);
        }
        Ok(Value::Array(coordinate))
    }

    fn coordinate_sequence(
        &mut self,
        little: bool,
        dimensions: usize,
        minimum: usize,
        closed: bool,
    ) -> Result<Value, ()> {
        let count = self.count(little)?;
        if count < minimum || count > self.max_vertices.saturating_sub(self.vertices) {
            return Err(());
        }
        let mut coordinates = Vec::with_capacity(count.min(4096));
        for _ in 0..count {
            coordinates.push(self.coordinate(little, dimensions)?);
        }
        if closed && coordinates.first() != coordinates.last() {
            return Err(());
        }
        Ok(Value::Array(coordinates))
    }

    fn geometry(
        &mut self,
        depth: usize,
        expected: Option<(u32, usize)>,
    ) -> Result<(Value, &'static str, u32, usize), ()> {
        if depth >= MAX_NESTING {
            return Err(());
        }
        let little = match self.take::<1>()?[0] {
            0 => false,
            1 => true,
            _ => return Err(()),
        };
        let raw = self.u32(little)?;
        if raw & 0x6000_0000 != 0 {
            return Err(()); // M and SRID extensions.
        }
        let ewkb_z = raw & 0x8000_0000 != 0;
        let iso = raw & 0x1fff_ffff;
        let (base, dimensions) = if iso >= 3000 {
            return Err(()); // ZM
        } else if iso >= 2000 {
            return Err(()); // M
        } else if iso >= 1000 {
            (iso - 1000, 3)
        } else {
            (iso, if ewkb_z { 3 } else { 2 })
        };
        if !(1..=7).contains(&base)
            || expected.is_some_and(|(expected_base, expected_dimensions)| {
                expected_base != base || expected_dimensions != dimensions
            })
        {
            return Err(());
        }

        let (geometry_type, coordinates) = match base {
            1 => ("Point", self.coordinate(little, dimensions)?),
            2 => (
                "LineString",
                self.coordinate_sequence(little, dimensions, 2, false)?,
            ),
            3 => {
                let rings = self.count(little)?;
                if rings == 0 || rings > self.max_vertices.saturating_sub(self.vertices) {
                    return Err(());
                }
                let mut values = Vec::with_capacity(rings.min(1024));
                for _ in 0..rings {
                    values.push(self.coordinate_sequence(little, dimensions, 4, true)?);
                }
                ("Polygon", Value::Array(values))
            }
            4..=6 => {
                let count = self.count(little)?;
                if count == 0 || count > self.max_vertices.saturating_sub(self.vertices) {
                    return Err(());
                }
                let child_base = base - 3;
                let mut values = Vec::with_capacity(count.min(4096));
                for _ in 0..count {
                    let (child, _, _, _) =
                        self.geometry(depth + 1, Some((child_base, dimensions)))?;
                    values.push(child.get("coordinates").cloned().ok_or(())?);
                }
                let name = match base {
                    4 => "MultiPoint",
                    5 => "MultiLineString",
                    _ => "MultiPolygon",
                };
                (name, Value::Array(values))
            }
            7 => {
                let count = self.count(little)?;
                if count == 0 || count > self.max_vertices.saturating_sub(self.vertices) {
                    return Err(());
                }
                let mut values = Vec::with_capacity(count.min(1024));
                for _ in 0..count {
                    let (child, _, _, child_dimensions) = self.geometry(depth + 1, None)?;
                    if child_dimensions != dimensions {
                        return Err(());
                    }
                    values.push(child);
                }
                ("GeometryCollection", Value::Array(values))
            }
            _ => return Err(()),
        };
        let value = if base == 7 {
            serde_json::json!({"type": geometry_type, "geometries": coordinates})
        } else {
            serde_json::json!({"type": geometry_type, "coordinates": coordinates})
        };
        Ok((value, geometry_type, base, dimensions))
    }
}

fn number(value: f64) -> Result<Value, ()> {
    Number::from_f64(value).map(Value::Number).ok_or(())
}

#[cfg(test)]
mod tests {
    use super::parse;

    #[test]
    fn parses_little_endian_point() {
        let mut bytes = vec![1];
        bytes.extend_from_slice(&1_u32.to_le_bytes());
        bytes.extend_from_slice(&(-116.0_f64).to_le_bytes());
        bytes.extend_from_slice(&(44.0_f64).to_le_bytes());
        let geometry = parse(&bytes, 10).unwrap();
        assert_eq!(geometry.geometry_type, "Point");
        assert_eq!(geometry.dimensions, 2);
        assert_eq!(geometry.bounds, [-116.0, 44.0, -116.0, 44.0]);
    }

    #[test]
    fn rejects_nonfinite_coordinate() {
        let mut bytes = vec![1];
        bytes.extend_from_slice(&1_u32.to_le_bytes());
        bytes.extend_from_slice(&f64::INFINITY.to_le_bytes());
        bytes.extend_from_slice(&(44.0_f64).to_le_bytes());
        assert!(parse(&bytes, 10).is_err());
    }

    #[test]
    fn parses_big_endian_point() {
        let mut bytes = vec![0];
        bytes.extend_from_slice(&1_u32.to_be_bytes());
        bytes.extend_from_slice(&(-116.0_f64).to_be_bytes());
        bytes.extend_from_slice(&(44.0_f64).to_be_bytes());
        let geometry = parse(&bytes, 1).unwrap();
        assert_eq!(geometry.bounds, [-116.0, 44.0, -116.0, 44.0]);
    }

    #[test]
    fn parses_iso_z_point() {
        let mut bytes = vec![1];
        bytes.extend_from_slice(&1001_u32.to_le_bytes());
        bytes.extend_from_slice(&(-116.0_f64).to_le_bytes());
        bytes.extend_from_slice(&(44.0_f64).to_le_bytes());
        bytes.extend_from_slice(&(900.0_f64).to_le_bytes());
        let geometry = parse(&bytes, 10).unwrap();
        assert_eq!(geometry.geometry_type, "Point");
        assert_eq!(geometry.dimensions, 3);
        assert_eq!(geometry.value["coordinates"][2], 900.0);
    }

    #[test]
    fn rejects_mixed_dimension_multi_geometry() {
        let mut bytes = vec![1];
        bytes.extend_from_slice(&1004_u32.to_le_bytes());
        bytes.extend_from_slice(&1_u32.to_le_bytes());
        bytes.push(1);
        bytes.extend_from_slice(&1_u32.to_le_bytes());
        bytes.extend_from_slice(&(-116.0_f64).to_le_bytes());
        bytes.extend_from_slice(&(44.0_f64).to_le_bytes());
        assert!(parse(&bytes, 10).is_err());
    }

    #[test]
    fn vertex_budget_accepts_exact_and_rejects_plus_one() {
        fn line(count: usize) -> Vec<u8> {
            let mut bytes = vec![1];
            bytes.extend_from_slice(&2_u32.to_le_bytes());
            bytes.extend_from_slice(&(count as u32).to_le_bytes());
            for index in 0..count {
                bytes.extend_from_slice(&(index as f64).to_le_bytes());
                bytes.extend_from_slice(&(44.0_f64).to_le_bytes());
            }
            bytes
        }
        let limit = 250_000;
        assert!(parse(&line(limit), limit).is_ok());
        assert!(parse(&line(limit + 1), limit).is_err());
    }

    #[test]
    fn wkb_byte_budget_accepts_exact_and_rejects_plus_one() {
        assert!(super::within_size_limit(4 * 1024 * 1024));
        assert!(!super::within_size_limit(4 * 1024 * 1024 + 1));
    }
}

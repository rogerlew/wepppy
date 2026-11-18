//! Selection semantics match the existing DuckDB filter, before CSV projection.
use crate::{Error, cell, python_float};
use arrow_array::*;
use arrow_schema::{DataType, Schema};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

pub enum Filter {
    Group(bool, Vec<Filter>),
    Condition {
        index: usize,
        operator: String,
        value: String,
        number: Option<f64>,
        numeric: bool,
    },
}
pub fn names(schema: &Schema) -> Result<Vec<String>, Error> {
    let mut counts = BTreeMap::<String, usize>::new();
    let mut normalized = BTreeSet::new();
    let mut names = Vec::new();
    for (index, field) in schema.fields().iter().enumerate() {
        let mut name = field.name().clone();
        while let Some(count) = counts.get_mut(&name.to_ascii_lowercase()) {
            *count += 1;
            name = format!("{name}_{count}");
        }
        counts.insert(name.to_ascii_lowercase(), 0);
        if name.is_empty() {
            name = format!("C{index}");
        }
        // DuckDB rejects collisions introduced by its empty-name normalization.
        if !normalized.insert(name.to_ascii_lowercase()) {
            return Err(Error::Input);
        }
        names.push(name);
    }
    Ok(names)
}

fn numeric(t: &DataType) -> bool {
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
    )
}
impl Filter {
    pub fn parse(v: &Value, s: &Schema) -> Result<Option<Self>, Error> {
        if v.is_null() {
            return Ok(None);
        }
        Ok(Some(Self::node(v, s, &names(s)?, 1, &mut 0)?))
    }
    fn node(
        v: &Value,
        s: &Schema,
        names: &[String],
        depth: usize,
        count: &mut usize,
    ) -> Result<Self, Error> {
        *count += 1;
        if depth > 6 || *count > 50 {
            return Err(Error::Validation);
        }
        let o = v.as_object().ok_or(Error::Validation)?;
        match v["kind"].as_str() {
            Some("group") => {
                if o.len() != 3 || !o.contains_key("logic") || !o.contains_key("children") {
                    return Err(Error::Validation);
                }
                let and = match v["logic"].as_str() {
                    Some("AND") => true,
                    Some("OR") => false,
                    _ => return Err(Error::Validation),
                };
                let items = v["children"].as_array().ok_or(Error::Validation)?;
                if items.is_empty() {
                    return Err(Error::Validation);
                }
                Ok(Self::Group(
                    and,
                    items
                        .iter()
                        .map(|x| Self::node(x, s, names, depth + 1, count))
                        .collect::<Result<_, _>>()?,
                ))
            }
            Some("condition") => {
                if o.len() != 5
                    || !["field", "operator", "value", "number"]
                        .iter()
                        .all(|k| o.contains_key(*k))
                {
                    return Err(Error::Validation);
                }
                let field = v["field"].as_str().ok_or(Error::Validation)?;
                let value = v["value"].as_str().ok_or(Error::Validation)?;
                let operator = v["operator"].as_str().ok_or(Error::Validation)?;
                if field.is_empty()
                    || field.chars().count() > 128
                    || value.chars().count() > 512
                    || !["Equals", "NotEquals", "Contains", "GreaterThan", "LessThan"]
                        .contains(&operator)
                {
                    return Err(Error::Validation);
                }
                let source = s
                    .fields()
                    .iter()
                    .rev()
                    .find(|f| f.name() == field)
                    .ok_or(Error::Validation)?;
                let index = names
                    .iter()
                    .position(|n| n.eq_ignore_ascii_case(field))
                    .ok_or(Error::Validation)?;
                let numeric = numeric(source.data_type());
                let number = if v["number"].is_null() {
                    None
                } else {
                    Some(
                        v["number"]
                            .as_f64()
                            .filter(|x| x.is_finite())
                            .ok_or(Error::Validation)?,
                    )
                };
                if ((operator == "GreaterThan" || operator == "LessThan") && !numeric)
                    || (numeric && operator != "Contains" && number.is_none())
                {
                    return Err(Error::Validation);
                }
                Ok(Self::Condition {
                    index,
                    operator: operator.into(),
                    value: value.into(),
                    number,
                    numeric,
                })
            }
            _ => Err(Error::Validation),
        }
    }
    pub fn matches(&self, b: &RecordBatch, row: usize) -> bool {
        match self {
            Self::Group(and, children) => {
                if *and {
                    children.iter().all(|x| x.matches(b, row))
                } else {
                    children.iter().any(|x| x.matches(b, row))
                }
            }
            Self::Condition {
                index,
                operator,
                value,
                number,
                numeric,
            } => {
                let a = b.column(*index).as_ref();
                if a.is_null(row) {
                    return false;
                }
                if operator == "Contains" {
                    return lower(&varchar(a, row)).contains(&lower(value));
                }
                if *numeric {
                    // Rust's primitive integer -> f64 cast intentionally matches DOUBLE comparisons.
                    let x = double(a, row);
                    let y = number.unwrap();
                    if x.is_nan() {
                        return false;
                    }
                    match operator.as_str() {
                        "Equals" => x == y,
                        "NotEquals" => x != y,
                        "GreaterThan" => x > y,
                        "LessThan" => x < y,
                        _ => false,
                    }
                } else {
                    let x = varchar(a, row);
                    if operator == "Equals" {
                        x == *value
                    } else {
                        x != *value
                    }
                }
            }
        }
    }
}
fn double(a: &dyn Array, row: usize) -> f64 {
    if matches!(a.data_type(), DataType::Boolean) {
        return if a
            .as_any()
            .downcast_ref::<BooleanArray>()
            .unwrap()
            .value(row)
        {
            1.0
        } else {
            0.0
        };
    }
    let text = cell(a, row);
    let text = text.trim_matches(|c: char| c.is_ascii_whitespace() || c == '\u{000b}');
    let bytes = text.as_bytes();
    for (i, b) in bytes.iter().enumerate() {
        if *b == b'_'
            && (i == 0
                || i + 1 == bytes.len()
                || !bytes[i - 1].is_ascii_digit()
                || !bytes[i + 1].is_ascii_digit())
        {
            return f64::NAN;
        }
    }
    text.replace('_', "").parse::<f64>().unwrap_or(f64::NAN)
}

fn lower(s: &str) -> String {
    s.chars().map(crate::lowercase::lower).collect()
}
fn varchar(a: &dyn Array, row: usize) -> String {
    match a.data_type() {
        DataType::Boolean => cell(a, row).to_ascii_lowercase(),
        DataType::Float32 => {
            let x = a
                .as_any()
                .downcast_ref::<Float32Array>()
                .unwrap()
                .value(row);
            if x.is_nan() {
                "nan".into()
            } else if x.is_finite() {
                let mut b = ryu::Buffer::new();
                python_float(b.format_finite(x).parse().unwrap())
            } else {
                python_float(x as f64)
            }
        }
        DataType::Float64 => {
            let x = a
                .as_any()
                .downcast_ref::<Float64Array>()
                .unwrap()
                .value(row);
            if x.is_nan() {
                "nan".into()
            } else {
                python_float(x)
            }
        }
        DataType::Binary | DataType::LargeBinary => {
            let bytes = if matches!(a.data_type(), DataType::Binary) {
                a.as_any().downcast_ref::<BinaryArray>().unwrap().value(row)
            } else {
                a.as_any()
                    .downcast_ref::<LargeBinaryArray>()
                    .unwrap()
                    .value(row)
            };
            let mut s = String::new();
            for b in bytes {
                if (32..=126).contains(b) && *b != b'\\' {
                    s.push(*b as char);
                } else {
                    s.push_str(&format!("\\x{b:02X}"));
                }
            }
            s
        }
        DataType::Timestamp(_, _) => {
            let mut s = crate::timestamp(a, row, false);
            if s.contains('.') {
                while s.ends_with('0') {
                    s.pop();
                }
                if s.ends_with('.') {
                    s.pop();
                }
            }
            s
        }
        _ => cell(a, row),
    }
}

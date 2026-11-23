//! Bounded strict JSON request decoding. No SQL or caller-controlled resource policy.
use crate::Error;
use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Value};
use std::fmt;
use std::fs::OpenOptions;
use std::io::Read;
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::Path;

struct Strict(Value);
impl<'de> Deserialize<'de> for Strict {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Strict;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("strict JSON")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_f64<E: de::Error>(self, v: f64) -> Result<Strict, E> {
                serde_json::Number::from_f64(v)
                    .map(|n| Strict(Value::Number(n)))
                    .ok_or_else(|| E::custom("nonfinite"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_string<E: de::Error>(self, v: String) -> Result<Strict, E> {
                Ok(Strict(v.into()))
            }
            fn visit_unit<E: de::Error>(self) -> Result<Strict, E> {
                Ok(Strict(Value::Null))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> Result<Strict, A::Error> {
                let mut v = Vec::new();
                while let Some(Strict(x)) = a.next_element()? {
                    v.push(x);
                }
                Ok(Strict(Value::Array(v)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> Result<Strict, A::Error> {
                let mut v = Map::new();
                while let Some(k) = a.next_key::<String>()? {
                    if v.contains_key(&k) {
                        return Err(de::Error::custom("duplicate key"));
                    }
                    let Strict(x) = a.next_value()?;
                    v.insert(k, x);
                }
                Ok(Strict(Value::Object(v)))
            }
        }
        d.deserialize_any(V)
    }
}
pub fn read(root: &Path) -> Result<Value, Error> {
    let f = OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(root.join("request.json"))
        .map_err(|_| Error::Input)?;
    let m = f.metadata().map_err(|_| Error::Input)?;
    // SAFETY: geteuid only reads process identity.
    if !m.is_file()
        || m.len() > 131072
        || m.uid() != unsafe { libc::geteuid() }
        || m.mode() & 0o077 != 0
        || m.nlink() != 1
    {
        return Err(Error::Input);
    }
    let mut raw = Vec::new();
    f.take(131073)
        .read_to_end(&mut raw)
        .map_err(|_| Error::Io)?;
    if raw.len() > 131072 {
        return Err(Error::Input);
    }
    let mut d = serde_json::Deserializer::from_slice(&raw);
    let Strict(v) = Strict::deserialize(&mut d).map_err(|_| Error::Input)?;
    d.end().map_err(|_| Error::Input)?;
    let o = v.as_object().ok_or(Error::Input)?;
    if o.len() != 2
        || o.get("version").and_then(Value::as_u64) != Some(2)
        || !o.contains_key("filter")
    {
        return Err(Error::Input);
    }
    Ok(v["filter"].clone())
}

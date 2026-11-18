use parquet::file::{metadata::ParquetMetaDataReader, reader::{FileReader, SerializedFileReader}};
use std::{fs::File, env};

fn main() {
    let path = env::args().nth(1).expect("one bounded evaluation fixture path");
    if path == "footer-list-bomb" {
        // FileMetaData version=1 then schema list<struct> declares i32::MAX
        // elements with no element bytes. Source 60.1.0 rejects before allocation.
        let bytes = [0x15, 0x02, 0x19, 0xfc, 0xff, 0xff, 0xff, 0xff, 0x07];
        match ParquetMetaDataReader::decode_metadata(&bytes) {
            Ok(_) => panic!("malformed footer admitted"),
            Err(error) => println!("{}", serde_json::json!({"rejected": true, "error": error.to_string()})),
        }
        return;
    }
    let input = File::open(path).expect("fixture open");
    let reader = SerializedFileReader::new(input).expect("metadata parse");
    let rows = reader.get_row_iter(None).expect("row iterator").collect::<Result<Vec<_>, _>>();
    match rows {
        Ok(rows) => println!("{}", serde_json::json!({"rows": rows.len()})),
        Err(error) => println!("{}", serde_json::json!({"rejected": true, "error": error.to_string()})),
    }
}

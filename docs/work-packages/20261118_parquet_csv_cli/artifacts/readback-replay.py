import sys,pathlib,asyncio,csv,hashlib,json,importlib.util
sys.path.insert(0,'/tmp/parquet-csv-next/tools/parquet_csv_cli')
from harness import Converter
from harness.provenance import generate
import pyarrow as pa,pyarrow.parquet as pq
root=pathlib.Path('/tmp/parquet-csv-evaluation');tool=pathlib.Path('/tmp/parquet-csv-next/tools/parquet_csv_cli');binary=tool/'rust/target/release/parquet_csv_cli';side=root/'readback-binary.json';generate(binary,side)
spec=importlib.util.spec_from_file_location('oracle','/home/workdir/wepppy-parquet-csv-cli-package/wepppy/microservices/browse/parquet_tables.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
async def main():
 results=[];c=Converter(binary,side,root/'readback-scratch')
 for source in (root/'corpus').glob('*.parquet'):
  with await c.convert(source) as a:
   with a.path.open(newline='') as f:
    rows=csv.reader(f);headers=next(rows);count=0;first=last=None
    for row in rows:
     assert len(row)==len(headers)
     if first is None:first=row
     last=row;count+=1
   f=pq.ParquetFile(source);schema=f.schema_arrow
   expected_headers=None;oracle_first=oracle_last=None
   for batch in f.iter_batches(batch_size=8192):
    table=oracle.project_table_for_output(pa.Table.from_batches([batch]),source_schema=schema,include_units=True)
    if oracle_first is None:oracle_first=[oracle._format_csv_cell(v) for v in table.slice(0,1).to_pylist()[0].values()];expected_headers=table.column_names
    oracle_last=[oracle._format_csv_cell(v) for v in table.slice(table.num_rows-1,1).to_pylist()[0].values()]
   assert headers==expected_headers and count==f.metadata.num_rows and first==oracle_first and last==oracle_last
   results.append(dict(file=source.name,rows=count,columns=len(headers),header_parity=True,first_last_cell_parity=True,output_sha256=hashlib.file_digest(a.path.open('rb'),'sha256').hexdigest()))
 print(json.dumps(results,indent=2));(root/'readback-results.json').write_text(json.dumps(results,indent=2))
asyncio.run(main())

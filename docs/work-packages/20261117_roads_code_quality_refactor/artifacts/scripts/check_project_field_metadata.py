from pathlib import Path
import json
import pyarrow.parquet as pq
report=json.loads(Path('/tmp/roads-refactor-validation/project-candidate-20261117b-comparison.json').read_text())
checked=[]
for project in report['projects']:
 roots=list(map(Path,project['roots']))
 for item in project['details']:
  if not item['path'].endswith('.parquet'):continue
  schemas=[pq.read_schema(r/item['path']).with_metadata(None) for r in roots]
  assert schemas[0].equals(schemas[1],check_metadata=True),(project['design'],item['path'])
  checked.append([project['design'],item['path']])
receipt={'pass':True,'field_metadata_schemas_checked':len(checked),'artifacts':checked}
Path('/tmp/roads-refactor-validation/project-field-metadata-comparison.json').write_text(json.dumps(receipt,indent=2))
print('PASS',len(checked),'parquet schemas including field metadata')

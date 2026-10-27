"""Read-only final sample metadata; report only digests and catalog presence."""
import json,os,sys,time
from pathlib import Path
assert (os.getuid(),os.getgid())==(1002,130)
samples=json.loads((Path(sys.argv[1])/'samples-private.json').read_text())
rows=[]
for namespace,items in samples.items():
 for item in items:
  try:
   present=(Path(item['path'])/'_query_engine/catalog.json').is_file()
   rows.append(dict(namespace=namespace,digest=item['digest'],catalog_present=present))
  except OSError as exc:
   rows.append(dict(namespace=namespace,digest=item['digest'],error_type=type(exc).__name__,errno=exc.errno))
print(json.dumps(dict(epoch=time.time(),samples=rows)))

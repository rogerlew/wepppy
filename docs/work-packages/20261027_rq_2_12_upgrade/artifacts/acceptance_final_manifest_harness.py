import json,zipfile,hashlib
from pathlib import Path
ART=Path('/workdir/wepppy/docs/work-packages/20261027_rq_2_12_upgrade/artifacts')
r=json.loads((ART/'acceptance_archive_restore.json').read_text());wd=Path('/wc1/runs/rq/rq212-20261027-upgraded')
files={}
with zipfile.ZipFile(wd/'archives'/r['archive_manifest']['name']) as z:
 for name in z.namelist():
  if name.startswith(('wepp/runs/','wepp/output/')) and not name.endswith('/'):
   a=hashlib.sha256(z.read(name)).hexdigest();b=hashlib.sha256((wd/name).read_bytes()).hexdigest();assert a==b,name;files[name]=a
assert len(files)==417
(ART/'acceptance_final_repaired_manifest.json').write_text(json.dumps({'all417_archive_files_equal':True,'files':files},indent=2));print('PASS417 restored generated-file hashes against originalarchive')

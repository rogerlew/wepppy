"""Read-only follow-up: compare live CLI semantic values with accepted parquet."""
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from wepppy.climates.cligen import ClimateFile
R=Path('/wc1/runs/th/thespian-cleanness');O=Path(__file__).resolve().parent
f=R/'climate/wepp.cli';s=f.stat()
with f.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
a=ClimateFile(str(f)).as_dataframe(calc_peak_intensities=True);b=pd.read_parquet(R/'climate/wepp_cli.parquet')
assert len(a)==len(b)
checks={c:bool(np.array_equal(a[c].to_numpy(),b[c].to_numpy(),equal_nan=True)) for c in a.columns}
assert all(checks.values())
with (R/'climate/wepp_cli.parquet').open('rb') as stream:ph=hashlib.file_digest(stream,'sha256').hexdigest()
m=json.loads((R/'postfire_debris_flow/manifest.json').read_text());assert ph==m['sources_sha256'][str(R/'climate/wepp_cli.parquet')]
link=R/'wepp/runs/pw0.cli';t=link.stat()
d={'attempt':m['identity']['assessment_id'],'rows':len(a),'column_equality':checks,'cli_sha256_at_check':h,'parquet_sha256_matches_accepted':True,'same_inode_as_pw0_cli':(s.st_dev,s.st_ino)==(t.st_dev,t.st_ino),'link_count':s.st_nlink,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
assert (s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(f.stat().st_size,f.stat().st_mtime_ns,f.stat().st_ctime_ns)
(O/'evidence.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))

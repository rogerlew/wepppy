"""Verify pinned report downloads, actual CLI rows and post-browser preservation."""
import hashlib,json
from pathlib import Path
import pandas as pd
O=Path(__file__).resolve().parent;R=Path('/wc1/runs/th/thespian-cleanness');M=R/'postfire_debris_flow'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
before=json.loads((O/'protected_before.json').read_text())
changed=[n for n,h in before.items() if not (R/n).is_file() or sha(R/n)!=h]
tracked=sorted(str(p.relative_to(R)) for p in R.rglob('*') if p.is_file() and (p.suffix in ('.cli','.par','.prn','.nodb','.tif','.parquet','.sqlite','.csv','.json','.geojson') or p.name.endswith(('-wal','-shm'))))
added=sorted(set(tracked)-set(before))
manifest=json.loads((M/'manifest.json').read_text());assert manifest==json.loads((O/'result_manifest.json').read_text())
browser=json.loads((O/'browser/thespian-cleanness/evidence.json').read_text())
attachments=[]
for record in browser:
 if record.get('stage')=='attachment':
  name=record['name'];path=M/name
  if name=='valid_mask.tif':path=M/'attempts/8190121c8a4b45e1952861e74d909693/predictors'/name
  attachments.append({'name':name,'matches':sha(path)==record['sha256']})
assert len(attachments)==5 and all(a['matches'] for a in attachments)
assert [r['duration'] for r in browser if r.get('stage')=='currentness' and r['current']]==[15,30,60]
assert not any('error' in r or 'page_error' in r for r in browser)
assert any(r.get('stage')=='reload' and r['status']=='PASS' for r in browser)
cli=pd.read_csv(R/'climate/wepp.cli',sep=r'\s+',skiprows=15,header=None,names=['day_of_month','month','year','prcp','dur','tp','ip','tmax','tmin','rad','w-vl','w-dir','tdew'])
cache=pd.read_parquet(R/'climate/wepp_cli.parquet')
for col in ['day_of_month','month','year','prcp']:assert (cli[col].to_numpy()==cache[col].to_numpy()).all()
source_files=['wepppy/climates/cligen/cligen.py','wepppy/nodb/core/climate_build_helpers.py','wepppy/nodb/core/climate.py','wepppy/climates/daymet/daymet_singlelocation_client.py']
repo=Path('/workdir/wepppy')
source_hashes={n:sha(repo/n) for n in source_files}
log=(R/'climate/cligen_wepp.log').read_text();lines=log.splitlines()
errors=[{'line':i+1,'text':'\n'.join(lines[i:i+2])} for i,l in enumerate(lines) if '*** ERROR ***' in l]
result={'protected_files':len(before),'changed':changed,'new_tracked_files':added,'manifest_unchanged':True,'attachments':attachments,'browser_current_all_durations':True,'browser_errors':False,'cli_cache_dates_precipitation_match':True,'cli_rows':len(cli),'cli_sha256':sha(R/'climate/wepp.cli'),'source_code_hashes':source_hashes,'cligen_error_count':len(errors),'cligen_error_excerpts':errors}
(O/'closeout.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
assert not changed and not added

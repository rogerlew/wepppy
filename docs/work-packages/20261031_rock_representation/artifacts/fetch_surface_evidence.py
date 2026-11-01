"""Read-only, bounded NRCS surface-fragment query for four development materials."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
url='https://SDMDataAccess.nrcs.usda.gov/Tabular/post.rest'
query="""SELECT c.mukey,c.cokey,c.compname,c.comppct_r,s.cosurffragskey,s.sfragcov_l,s.sfragcov_r,s.sfragcov_h,s.sfragkind,s.sfragsize_l,s.sfragsize_r,s.sfragsize_h,s.sfraghard FROM component AS c LEFT JOIN cosurffrags AS s ON c.cokey=s.cokey WHERE c.mukey IN ('1718465','1718494','1856573','2711184') ORDER BY c.mukey,c.cokey,s.cosurffragskey"""
request={'url':url,'query':query,'format':'xml','requested_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'four public development materials only; no output fitting or withheld access'}
(a.out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
req=urllib.request.Request(url,data=urllib.parse.urlencode({'query':query,'format':'xml'}).encode(),headers={'Content-Type':'application/x-www-form-urlencoded; charset=utf-8'})
try:
    with urllib.request.urlopen(req,timeout=25) as response:
        payload=response.read();status=response.status
    (a.out/'response.xml').write_bytes(payload)
    result={'status':'retrieved','http_status':status,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'limitation':'Current survey metadata, not original run snapshot or field-measured road armor.'}
except (urllib.error.URLError, TimeoutError, OSError) as exc:
    # Explicit research acquisition boundary: retain failure, no substituted data.
    result={'status':'unavailable','error_type':type(exc).__name__,'message':str(exc),'fallback_used':False}
(a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

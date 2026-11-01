"""Acquire only four admitted public mapunits; retain exact response and metadata."""
import datetime,hashlib,json,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path('out/whole-soil-retention-20261101');OUT=ROOT/'sources-v1'
KEYS=('1718465','1718494','1856573','2711184')
FIELDS='cokey chkey hzname hzdepb_r hzdept_r hzthk_r dbthirdbar_r ksat_r sandtotal_r claytotal_r om_r cec7_r awc_l fraggt10_r frag3to10_r desgnmaster sieveno10_r wthirdbar_r wfifteenbar_r sandvf_r ll_r'.split()
def main():
 OUT.mkdir();allowed=','.join("'"+k+"'" for k in KEYS)
 queries={'horizons':f"SELECT c.mukey,c.compname,c.comppct_r,{','.join('h.'+f for f in FIELDS)} FROM component c INNER JOIN chorizon h ON c.cokey=h.cokey WHERE c.mukey IN ({allowed}) ORDER BY c.mukey,h.cokey,h.hzdept_r,h.chkey",'fragments':f"SELECT c.mukey,h.chkey,f.chfragskey,f.fragvol_l,f.fragvol_r,f.fragvol_h,f.fragkind,f.fragsize_l,f.fragsize_r,f.fragsize_h,f.fraghard FROM component c INNER JOIN chorizon h ON c.cokey=h.cokey INNER JOIN chfrags f ON h.chkey=f.chkey WHERE c.mukey IN ({allowed}) ORDER BY c.mukey,h.chkey,f.chfragskey"}
 receipt={'requested_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'allowed_mukeys':KEYS,'queries':queries,'scope':'Current source snapshot; not historical run inputs or field calibration','responses':{}}
 (OUT/'request.json').write_text(json.dumps(receipt,indent=2)+'\n')
 for name,query in queries.items():
  url='https://SDMDataAccess.nrcs.usda.gov/Tabular/post.rest';request=urllib.request.Request(url,data=urllib.parse.urlencode({'query':query,'format':'xml'}).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
  with urllib.request.urlopen(request,timeout=45) as response:data=response.read();status=response.status
  (OUT/(name+'.xml')).write_bytes(data);rows=[{c.tag:c.text for c in row} for row in ET.fromstring(data).iter('Table')]
  if not rows:raise ValueError('No source rows returned: '+name)
  if any(r['mukey'] not in KEYS for r in rows):raise ValueError('Source scope violation')
  key='chkey' if name=='horizons' else 'chfragskey'
  if len({r[key] for r in rows})!=len(rows):raise ValueError('Duplicate source key')
  (OUT/(name+'.json')).write_text(json.dumps(rows,indent=2)+'\n');receipt['responses'][name]=dict(url=url,status=status,sha256=hashlib.sha256(data).hexdigest(),rows=len(rows))
 url='https://www.nrcs.usda.gov/sites/default/files/2022-08/SSURGO-Metadata-Table-Column-Descriptions-Report.pdf'
 with urllib.request.urlopen(url,timeout=45) as response:data=response.read()
 (OUT/'ssurgo-definitions.pdf').write_bytes(data);receipt['metadata']=dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt['responses']))
if __name__=='__main__':main()

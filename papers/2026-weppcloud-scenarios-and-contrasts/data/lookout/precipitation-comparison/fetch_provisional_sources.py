from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin
import requests,bs4,json,hashlib
p=Path(__file__).resolve().parent/'raw'; p.mkdir(exist_ok=True); jobs=[]
for station,series in [('PRIMET','primet_230_a'),('UPLMET','uplmet_235_a'),('CENMET','cenmet_234_a'),('VARMET','varmet_302_a')]:
 url=f'https://andrewsforest.oregonstate.edu/sites/default/files/lter/data/weather/portal/{station}/data/index.html'
 soup=bs4.BeautifulSoup(requests.get(url,timeout=30).text,'html.parser')
 for a in soup.select('a[href]'):
  h=a['href'];name=h.split('/')[-1]
  if name.startswith(series) and (name.endswith('.csv') or name.endswith('-meta.txt')):
   jobs.append((station,urljoin(url,h),name))
def fetch(job):
 station,url,name=job;f=p/name
 if not f.exists():
  r=requests.get(url,timeout=60);r.raise_for_status();f.write_bytes(r.content)
 return {'station':station,'url':url,'file':name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
with ThreadPoolExecutor(max_workers=6) as ex:
 data=list(ex.map(fetch,jobs))
(p/'manifest.json').write_text(json.dumps(data,indent=2))
print('Downloaded',len(data),'files',sum(x['bytes'] for x in data))

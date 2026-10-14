"""Interrupt a real staged copy in a child process on forest's shared mount."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from osgeo import gdal
from wepppy.webservices.wmesque_catalog import publish_dataset, sync_catalog, read_catalog

root=Path(tempfile.mkdtemp(prefix='wmesque-interruption-',dir='/wc1'))
master=root/'master';replica=root/'replica';master.mkdir();replica.mkdir()
path=master/'test/map';path.mkdir(parents=True)

def raster(size,value):
    ds=gdal.GetDriverByName('GTiff').Create(str(path/'tile.tif'),size,size,1,gdal.GDT_Float32)
    ds.SetGeoTransform((500000,30,0,5100240,0,-30));ds.GetRasterBand(1).Fill(value);ds=None
    gdal.BuildVRT(str(path/'.vrt'),[str(path/'tile.tif')])

raster(8,1);publish_dataset(master,'test/map');sync_catalog(str(master),replica)
old=read_catalog(replica)
raster(8192,2);new=publish_dataset(master,'test/map')
process=subprocess.Popen([sys.executable,'-c','from wepppy.webservices.wmesque_catalog import sync_catalog; import sys; sync_catalog(sys.argv[1],sys.argv[2])',str(master),str(replica)])
deadline=time.monotonic()+30
observed=None
while time.monotonic()<deadline:
    files=list((replica/'.wmesque').glob('sync-*/'+new['revision']+'/data/test/map/tile.tif'))
    if files:
        os.kill(process.pid,signal.SIGSTOP)
        observed={'path':str(files[0]),'size':files[0].stat().st_size}
        process.kill();process.wait(timeout=5)
        break
    if process.poll() is not None:raise RuntimeError('Copy completed before interruption; no interruption evidence')
    time.sleep(.001)
if observed is None:
    process.kill();process.wait();raise RuntimeError('Staged copy was not observed')
assert read_catalog(replica)==old
result=sync_catalog(str(master),replica)
assert read_catalog(replica)['datasets']['test/map']==new['revision']
evidence={'root':str(root),'uid':os.getuid(),'gid':os.getgid(),'killed_pid':process.pid,'exit':process.returncode,
          'staged_copy':observed,'source_bytes':(path/'tile.tif').stat().st_size,
          'old_catalog_preserved':True,'retry_status':result['status']}
(root/'evidence.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence,indent=2))

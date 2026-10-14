"""Run inside forest weppcloud container; isolated files, real batch jobs, real GDAL."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen

import numpy as np
from osgeo import gdal, osr
import redis
from rq import Queue
from rq.job import Job

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.rq.wmesque_rq import enqueue_sync
from wepppy.webservices.wmesque_catalog import publish_dataset, read_catalog, resolve_dataset
from wepppy.all_your_base.geo.webclients.wmesque import wmesque_retrieve

root = Path(tempfile.mkdtemp(prefix="wmesque-acceptance-", dir="/wc1"))
master, replica = root / "master", root / "replica"
master.mkdir(); replica.mkdir()
evidence = {"root": str(root), "uid": os.getuid(), "gid": os.getgid(), "jobs": [], "checks": []}
connection = redis.Redis(**redis_connection_kwargs(RedisDB.RQ))
queue = Queue("batch", connection=connection)
os.environ["WMESQUE_SYNC_SOURCE"] = str(master)
os.environ["WMESQUE_SYNC_DESTINATION"] = str(replica)


def dataset(base, name, value):
    path = base / name; path.mkdir(parents=True, exist_ok=True)
    ds = gdal.GetDriverByName("GTiff").Create(str(path / "tile.tif"), 8, 8, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000,30,0,5100240,0,-30))
    srs=osr.SpatialReference();srs.ImportFromEPSG(32611);ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(np.full((8,8),value,dtype=np.uint8));ds=None
    gdal.BuildVRT(str(path/".vrt"),[str(path/"tile.tif")])


def scheduled_sync(expect="finished"):
    config=root/"scheduled.json"
    config.write_text(json.dumps({"tasks":[{"name":"wmesque_sync","func":"wepppy.rq.wmesque_rq.sync_wmesque_rq",
        "enabled":True,"interval_seconds":2,"initial_delay_seconds":0,"jitter_seconds":0,"queue":"batch","job_timeout":120}]}))
    # Use the actual scheduler entry point, then inspect its actual batch job.
    subprocess.run([sys.executable,"-m","wepppy.tools.scheduler","--config",str(config),"--once"],check=True)
    key="wmesque:sync:admission:"+hashlib.sha256(str(replica.resolve()).encode()).hexdigest()
    identifier=connection.get(key).decode()
    job=Job.fetch(identifier,connection=connection)
    for _ in range(120):
        status=job.get_status(refresh=True);status=getattr(status,"value",status)
        if status in {"finished","failed","stopped","canceled"}:break
        time.sleep(1)
    evidence["jobs"].append({"id":identifier,"status":status,"worker":job.worker_name,
                              "origin":job.origin,"func":job.func_name,"dependencies":job.dependency_ids})
    if status != expect:
        raise RuntimeError(f"Unexpected job {identifier}: {status}; {job.exc_info}")
    return job


def server(base):
    sock=socket.socket();sock.bind(("127.0.0.1",0));port=sock.getsockname()[1];sock.close()
    catalog=base/"legacy-catalog.txt";catalog.write_text("")
    env=dict(os.environ,GEODATA_DIR=str(base),CATALOG_PATH=str(catalog))
    log=(base/"server.log").open("w")
    process=subprocess.Popen([sys.executable,"-m","uvicorn","wepppy.webservices.wmesque2:app","--host","127.0.0.1","--port",str(port)],env=env,stdout=log,stderr=subprocess.STDOUT)
    url=f"http://127.0.0.1:{port}"
    for _ in range(100):
        if process.poll() is not None:raise RuntimeError("Test server failed")
        try:
            with urlopen(url+"/health",timeout=.2):return process,log,url
        except OSError:time.sleep(.1)
    raise RuntimeError("Test server startup timed out")


dataset(master,"test/map",7);dataset(replica,"test/map",3);dataset(replica,"local/only",9)
first=publish_dataset(master,"test/map")
scheduled_sync()
assert read_catalog(replica)["datasets"]["test/map"]==first["revision"]
evidence["checks"].append("real scheduled RQ sync and automatic local adoption")
assert gdal.Open(str(resolve_dataset(replica,"local/only")[0])).ReadAsArray()[0,0]==9
servers=[]
try:
    for base in (replica,master):servers.append(server(base))
    urls=[item[2] for item in servers]
    os.environ["WMESQUE_ENDPOINTS"]=json.dumps(urls)
    out=root/"result.tif"
    args=("test/map",[500000,5100000,500240,5100240],str(out),30)
    wmesque_retrieve(*args,extent_crs="EPSG:32611",expected_revision=first["revision"])
    assert np.all(gdal.Open(str(out)).ReadAsArray()==7)
    dataset(master,"test/map",12);second=publish_dataset(master,"test/map")
    # A stale local replica rejects the revision; master serves the exact request.
    wmesque_retrieve(*args,extent_crs="EPSG:32611",expected_revision=second["revision"])
    assert json.loads(Path(str(out)+".meta").read_text())["wmesque_retrieve"]["wmesque_endpoint"]==urls[1]
    # Corrupt transfer is a genuine failed RQ job; prior catalog stays usable.
    source=master/".wmesque/releases"/second["revision"]/"data/test/map/tile.tif"
    saved=source.read_bytes();source.write_bytes(b"interrupted-copy")
    scheduled_sync("failed")
    assert read_catalog(replica)["datasets"]["test/map"]==first["revision"]
    source.write_bytes(saved)
    reading = threading.Event()
    stop = threading.Event()
    def read_during_sync():
        observed = []
        target = root / "concurrent.tif"
        while not stop.is_set():
            wmesque_retrieve("test/map", args[1], str(target), 30,
                             extent_crs="EPSG:32611", wmesque_endpoint=urls[0])
            meta = json.loads(Path(str(target)+".meta").read_text())
            revision = meta["wmesque"]["revision"]
            expected = {first["revision"]:7, second["revision"]:12}[revision]
            assert np.all(gdal.Open(str(target)).ReadAsArray()==expected)
            observed.append(revision)
            reading.set()
        return observed
    with ThreadPoolExecutor(max_workers=1) as executor:
        reader = executor.submit(read_during_sync)
        assert reading.wait(timeout=30)
        try:
            scheduled_sync()
        finally:
            stop.set()
        evidence["concurrent_retrieval_revisions"] = reader.result()
    wmesque_retrieve(*args,extent_crs="EPSG:32611",expected_revision=second["revision"])
    assert np.all(gdal.Open(str(out)).ReadAsArray()==12)
    assert json.loads(Path(str(out)+".meta").read_text())["wmesque_retrieve"]["wmesque_endpoint"]==urls[0]
    servers[0][0].terminate();servers[0][0].wait(timeout=10)
    wmesque_retrieve(*args,extent_crs="EPSG:32611",expected_revision=second["revision"])
    assert json.loads(Path(str(out)+".meta").read_text())["wmesque_retrieve"]["wmesque_endpoint"]==urls[1]
    evidence["checks"] += ["stale revision fallback", "failed scheduled transfer preserves old catalog", "next scheduled attempt recovers", "concurrent retrieval matches one complete revision", "projected extent and pixel readback", "stopped local server falls back"]
finally:
    for process,log,_ in servers:
        if process.poll() is None:process.terminate();process.wait(timeout=10)
        log.close()
    (root/"evidence.json").write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence,indent=2))

import hashlib, importlib.metadata, json, os, socket, sysconfig
from pathlib import Path

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def tree(root):
    entries=[]
    for parent, dirs, files in os.walk(root,followlinks=False):
        dirs[:]=sorted(x for x in dirs if x not in {'.git','__pycache__','.pytest_cache'})
        for name in sorted(files):
            p=Path(parent)/name
            if p.suffix in {'.pyc','.pyo'}:continue
            entries.append((p.relative_to(root).as_posix(), 'link:'+os.readlink(p) if p.is_symlink() else digest(p)))
    return {'files':len(entries),'sha256':hashlib.sha256(json.dumps(sorted(entries),separators=(',',':')).encode()).hexdigest()}

base=Path('/workdir/wepppy')
files=['requirements-uv.txt','docker/scheduled-tasks.yml','scripts/deploy-production.sh','wepppy/rq/query_catalog_rq.py','wepppy/rq/notifications_rq.py','wepp_runner/bin/wepp_261029','wepp_runner/bin/wepp_261029_hill']
import wepppyo3.wepp_interchange as interchange
extension=Path(interchange.wepp_interchange_rust.__file__)
flags=['QUERY_CATALOG_REFRESH_ENABLED','QUERY_CATALOG_ROOTS_JSON','WEPPCLOUD_NOTIFICATIONS_SWEEP_ENABLED','WEPPCLOUD_RUN_CATALOG_READ_MODE','WEPPCLOUD_RUN_CATALOG_WRITE_MODE','WEPPCLOUD_RUN_CATALOG_SWEEP_ENABLED']
versions={name:importlib.metadata.version(name) for name in ('rq','croniter','redis','fastapi','narwhals','pkginfo','python-dateutil')}
result={'hostname':socket.gethostname(),'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'versions':versions,'flags':{k:os.environ.get(k) for k in flags},'files':{f:digest(base/f) for f in files},'interchange':{'path':str(extension),'sha256':digest(extension)},'vendors':{name:tree(Path('/opt/vendor')/name) for name in ('wepppyo3','weppcloud-wbt','weppcloud2')},'rosetta':tree(Path(sysconfig.get_paths()['purelib'])/'rosetta')}
assert versions['rq']=='2.12.0'
assert result['interchange']['sha256']=='7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad'
assert result['files']['wepp_runner/bin/wepp_261029']=='4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825'
assert result['files']['wepp_runner/bin/wepp_261029_hill']=='210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936'
print(json.dumps(result,indent=2))

"""Read back the four accepted model files and two public revision-2 artifacts."""
from pathlib import Path
import hashlib,json,subprocess
R=Path('/workdir/wepppy');N=Path('/workdir/wepp-forest-release-20261009')
models={'wepp_261029':'819b91721f67c4a86a5ecea14c5beb840e9a705025da2a2cedf2b97a5e067715','wepp_261029_hill':'21d8480041d2efed942abb8471271ce1a11c5f72190d45c0c42dbe0028c019ed','wepp_261029.json':'a04cb9b67751682634c7067442677768b62d44fc292205ea29783360095d8311','wepp_261029_hill.json':'53742416b34fe0ece9c27eeee745f9b35761c7da6a5a982c9b4b55dda1c3366f'}
public={'wepp_261029_release-notes-r2.pdf':'c94db60e60ccd561a96dcdda89bad8bed209c32a783d3e699beb0e72485ddf44','publication-manifest-r2.json':'28c3efb859ae339bfcf3d598b36f2a885486d219f62ddd7a9387d3310a93baf8'}
checked={}
for base in [R/'wepp_runner/bin',R/'out/261029-r2-isolated/wepp_runner/bin',N/'release']:
 for name,sha in models.items():
  p=base/name;actual=hashlib.sha256(p.read_bytes()).hexdigest();assert actual==sha,p;checked[str(p)]=actual
for root in [R,R/'out/261029-r2-isolated']:
 for name,sha in public.items():
  p=root/'wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029'/name;actual=hashlib.sha256(p.read_bytes()).hexdigest();assert actual==sha,p;checked[str(p)]=actual
print(json.dumps({'all_frozen_files_exact':True,'sha256':checked},indent=2))

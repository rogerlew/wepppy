"""Snapshot completed release integration/publication evidence for retention."""
from pathlib import Path
import json,shutil,subprocess
R=Path('/workdir/wepppy');N=Path('/workdir/wepp-forest-release-20261009');A=Path(__file__).resolve().parent;RAW=R/'out/roads-native-funding-20261031'
assert json.loads((A/'application-disposition.json').read_text())['completed_segmented_coverage']['failed']==0
assert (A/'report-download-check.json').is_file()
dest=RAW/'r3-delivery-snapshot';dest.mkdir(exist_ok=False)
shutil.copytree(A.parent,dest/'wepppy-package')
shutil.copytree(N/'docs/work-packages/20261031-roads-open-boundary-funding',dest/'native-package')
shutil.copytree(N/'docs/ablation/20261031_roads_open_boundary_funding',dest/'native-incident')
shutil.copytree(N/'docs/release-notes/wepp_261029',dest/'native-report',ignore=shutil.ignore_patterns('build','__pycache__'))
shutil.copytree(R/'wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029',dest/'public-reports')
for role in ['wepp_261029','wepp_261029_hill']:
 for suffix in ['', '.json']:shutil.copy2(R/'wepp_runner/bin'/(role+suffix),dest/(role+suffix))
for p in Path('/tmp').glob('roads-native-funding-r3-*.log'):
 shutil.copy2(p,dest/p.name)
subprocess.run(['python3',str(A/'retain_selected.py'),'--label','release-delivery-r3-v1','--directory','r3-delivery-snapshot','--directory','r3-integration','--directory','r3-selected-hill','--directory','r3-selected-watershed','--directory','r3-application-evidence','--directory','r3-final-pdf-review'],check=True)

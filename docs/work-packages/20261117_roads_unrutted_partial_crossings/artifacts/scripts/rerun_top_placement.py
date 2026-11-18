"""Revalidate final candidate, retaining the earlier attempt and unchanged inputs."""
import argparse,json,shutil
from pathlib import Path
from wepppy.nodb.mods.roads import Roads
import validate_forest as base
parser=argparse.ArgumentParser();parser.add_argument('--short-fill',action='store_true');args=parser.parse_args()
root=Path('/wc1/runs/ru/rupc2-misty-shortfill' if args.short_fill else '/wc1/runs/ru/rupc2-misty-validation')
prior=root/'validation-result-before-final.json'
if prior.exists():
    raise RuntimeError('Prior final-candidate evidence exists; do not overwrite')
shutil.copy2(root/'validation-result.json',prior)
before=base.inventory(base.SOURCE)
r=Roads.getInstance(str(root))
try:
    result=r.run_roads_wepp()
except RuntimeError:
    result=r._last_run_summary
    if args.short_fill or result.get('failed_segment_count')!=5:
        raise
    assert all(row['reason']=='failed_road_fill_exceeds_hillslope' for row in result['failed_segments'])
finally:
    (root/'validation-result.json').write_text(json.dumps(r._last_run_summary,indent=2))
    assert before==base.inventory(base.SOURCE)
print('FINAL',root.name,result['status'],result.get('executed_segment_count'),result.get('failed_segment_count',0),flush=True)

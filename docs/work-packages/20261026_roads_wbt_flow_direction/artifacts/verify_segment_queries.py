"""Verify UI detail data from the isolated regenerated project."""
from pathlib import Path
import json
from wepppy.nodb.mods.roads import Roads
base = Path('/wc1/ablation/20261026_roads_wbt_flow_direction')
controller = Roads.getInstance(str(base / 'candidate'))
result = {}
for number in (1,20,21,22,23):
    identifier = f'roads-seg-{number:06d}'
    detail = controller.query_segment_detail(identifier)
    assert detail['execution_status'] == 'completed'
    assert detail['trace_termination_reason'] == 'hit_channel'
    assert detail['profile_error'] is None
    result[identifier] = {key: detail[key] for key in (
        'execution_status','trace_termination_reason','buffer_length_m',
        'target_hillslope_wepp_id','segment_run_id','profile_error')}
(base / 'segment-query-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

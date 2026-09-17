"""Apply the canonical destination-only fork job-marker reset to our copied run."""
import json
from pathlib import Path

from wepppy.nodb.core import Ron
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.rq.project_rq import _reset_forked_run_job_markers

runid = 'qa-freshness-runtime-7e24c8d1'
root = Path('/wc1/runs/qa')/runid
assert not (root/'.redisprep-run-id').exists()
assert Ron.getInstance(str(root)).runid == runid
prep = RedisPrep.getInstance(str(root))
assert prep.run_id == runid
before = dict(prep.redis.hgetall(prep.run_id))
_reset_forked_run_job_markers(runid, str(root), runid+':fork')
after = dict(prep.redis.hgetall(prep.run_id))
assert not prep.get_rq_job_ids() and not prep.get_archive_job_id()
removed = {key: value for key, value in before.items() if key not in after}
changed = {key: {'before': value, 'after': after[key]} for key, value in before.items()
           if key in after and value != after[key]}
result = {'root': str(root), 'redis_identity': prep.run_id,
          'canonical_helper': '_reset_forked_run_job_markers', 'removed': removed, 'changed': changed}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
print('Cleared inherited job markers on', runid, '; removed keys:', len(removed))

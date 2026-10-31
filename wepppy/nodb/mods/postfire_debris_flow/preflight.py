"""Advisory task projection, separate from the numerical engine fingerprint."""
from datetime import datetime
import logging
import uuid
from redis.exceptions import RedisError, LockError

__all__ = ['notify']


def notify(wd):
    from .production import state_at
    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum, RedisPrepSnapshotError
    try:
        prep = RedisPrep.getInstance(str(wd))
        # Serialize notifiers, then read durable state: an older callback must
        # never restore completion after a newer accepted upload cleared it.
        with prep.redis.lock(f'{prep.run_id}:postfire-preflight', timeout=30, blocking_timeout=5) as lock:
            state = state_at(wd)
            result, active = state['last_successful_run'], state['active_dnbr']
            completed = None
            model = result.get('model', 'M1') if result else 'M1'
            if result and (model == 'M3' or (model == 'M1' and active and result['snapshot'].get('dnbr') == active['id'])):
                completed = int(datetime.fromisoformat(result['completed_at']).timestamp())
            if not lock.owned():
                raise LockError('Postfire preflight projection lease expired.')
            key = f'timestamps:{TaskEnum.run_postfire_debris_flow}'
            values = {'postfire_debris_flow:model': model,
                      'postfire_debris_flow:revision': uuid.uuid4().hex}
            remove = []
            if completed is None:
                remove.append(key)
            else:
                values[key] = completed
            policy = result.get('soil_policy') if result else None
            if policy is None:
                remove.append('postfire_debris_flow:soil_policy')
            else:
                values['postfire_debris_flow:soil_policy'] = policy
            prep.update_metadata(values, remove=tuple(remove))
    except (RedisError, OSError, RedisPrepSnapshotError):
        logging.getLogger(__name__).exception('Preflight notification failed after durable postfire state commit; reconcile the completion marker from durable state')

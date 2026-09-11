"""Advisory task projection, separate from the numerical engine fingerprint."""
from datetime import datetime
import logging
import uuid
from redis.exceptions import RedisError, LockError

__all__ = ['notify']


def notify(wd):
    from .production import state_at
    from wepppy.nodb.redis_prep import RedisPrep, TaskEnum
    try:
        prep = RedisPrep.getInstance(str(wd))
        # Serialize notifiers, then read durable state: an older callback must
        # never restore completion after a newer accepted upload cleared it.
        with prep.redis.lock(f'{prep.run_id}:postfire-preflight', timeout=30, blocking_timeout=5) as lock:
            state = state_at(wd)
            result, active = state['last_successful_run'], state['active_dnbr']
            completed = None
            if (result and active and result['snapshot'].get('dnbr') == active['id']
                    and result['snapshot'].get('frequency') == state['frequency_source']):
                completed = int(datetime.fromisoformat(result['completed_at']).timestamp())
            if not lock.owned():
                raise LockError('Postfire preflight projection lease expired.')
            key = f'timestamps:{TaskEnum.run_postfire_debris_flow}'
            with prep.redis.pipeline() as pipe:
                if completed is None:
                    pipe.hdel(prep.run_id, key)
                else:
                    pipe.hset(prep.run_id, key, completed)
                pipe.hset(prep.run_id, 'postfire_debris_flow:revision', uuid.uuid4().hex)
                pipe.execute()
            prep.dump()
    except (RedisError, OSError):
        logging.getLogger(__name__).exception('Preflight notification failed after durable postfire state commit; reconcile the completion marker from durable state')

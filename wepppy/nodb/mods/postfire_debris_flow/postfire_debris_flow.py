"""Optional NoDb state for the Staley M1 production workflow."""
from copy import deepcopy
import re

from wepppy.nodb.base import NoDbBase, _ensure_redis_lock_client
from redis.exceptions import LockError

__all__ = ['PostfireDebrisFlow']


def empty_state():
    return {'schema_version': 1, 'active_dnbr': None, 'upload_attempt': None,
            'run_attempt': None, 'model': 'M1', 'frequency_source': 'cli', 'last_successful_run': None}


class PostfireDebrisFlow(NoDbBase):
    __name__ = 'PostfireDebrisFlow'
    filename = 'postfire_debris_flow.nodb'

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)
        with self.locked():
            self._state = empty_state()

    @property
    def state(self):
        value = getattr(self, '_state', None)
        if value is None:
            return empty_state()
        if isinstance(value, dict) and 'model' not in value:
            value = {**value, 'model': 'M1'}
        if not isinstance(value, dict) or set(value) != set(empty_state()) or value['schema_version'] != 1:
            raise ValueError('Invalid post-fire debris-flow state.')
        if value['model'] not in ('M1', 'M3'):
            raise ValueError('Invalid post-fire debris-flow model.')
        if value['frequency_source'] not in ('cli', 'noaa'):
            raise ValueError('Invalid rainfall source in post-fire debris-flow state.')
        for key in ('upload_attempt','run_attempt','active_dnbr','last_successful_run'):
            record=value[key]
            if record is None: continue
            if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not re.fullmatch('[0-9a-f]{32}',record['id']):
                raise ValueError('Invalid post-fire debris-flow record.')
            if not isinstance(record.get('snapshot'),dict):
                raise ValueError('Invalid post-fire dependency snapshot.')
            if key in ('run_attempt', 'last_successful_run') and record.get('model', 'M1') not in ('M1', 'M3'):
                raise ValueError('Invalid post-fire model identity.')
            if key.endswith('_attempt'):
                if record.get('phase') not in ('staged','queued','running','needs_scale','complete','failed','superseded','enqueue_unknown'):
                    raise ValueError('Invalid post-fire operation state.')
                if not isinstance(record.get('created_at'),str) or not isinstance(record.get('retryable'),bool):
                    raise ValueError('Invalid post-fire operation metadata.')
            elif not isinstance(record.get('artifacts'),dict):
                raise ValueError('Invalid post-fire artifact metadata.')
        return deepcopy(value)

    def _mutation_gate(self):
        return _ensure_redis_lock_client().lock(f'postfire-state:{self.runid}', timeout=120, blocking_timeout=10)

    def change(self, callback):
        """Refresh while locked; only this facade's state is modified."""
        # Serialize short preference/worker mutations before the nonblocking NoDb
        # lock. Never hold this gate across scientific computation or publication.
        with self._mutation_gate() as gate:
            # Another thread may have refreshed the singleton while we waited.
            controller = type(self).getInstance(self.wd)
            with controller.locked():
                state = controller.state
                from .observability import record_attempts
                record_attempts(self.wd, state)
                previous = state['last_successful_run']
                callback(state)
                if not gate.owned():
                    raise LockError('Postfire state mutation lease expired.')
                controller._state = state
                controller.dump()
                record_attempts(self.wd, state)
        accepted = state['last_successful_run']
        if accepted and (not previous or accepted['id'] != previous['id']):
            from .publication import publish_outputs
            publish_outputs(self.wd)
        from .preflight import notify
        notify(self.wd)

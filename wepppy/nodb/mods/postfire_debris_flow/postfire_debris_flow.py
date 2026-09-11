"""Optional NoDb state for the Staley M1 production workflow."""
from copy import deepcopy
import re

from wepppy.nodb.base import NoDbBase

__all__ = ['PostfireDebrisFlow']


def empty_state():
    return {'schema_version': 1, 'active_dnbr': None, 'upload_attempt': None,
            'run_attempt': None, 'frequency_source': 'cli', 'last_successful_run': None}


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
        if not isinstance(value, dict) or set(value) != set(empty_state()) or value['schema_version'] != 1:
            raise ValueError('Invalid post-fire debris-flow state.')
        if value['frequency_source'] not in ('cli', 'noaa'):
            raise ValueError('Invalid rainfall source in post-fire debris-flow state.')
        for key in ('upload_attempt','run_attempt','active_dnbr','last_successful_run'):
            record=value[key]
            if record is None: continue
            if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not re.fullmatch('[0-9a-f]{32}',record['id']):
                raise ValueError('Invalid post-fire debris-flow record.')
            if not isinstance(record.get('snapshot'),dict):
                raise ValueError('Invalid post-fire dependency snapshot.')
            if key.endswith('_attempt'):
                if record.get('phase') not in ('staged','queued','running','needs_scale','complete','failed','superseded','enqueue_unknown'):
                    raise ValueError('Invalid post-fire operation state.')
                if not isinstance(record.get('created_at'),str) or not isinstance(record.get('retryable'),bool):
                    raise ValueError('Invalid post-fire operation metadata.')
            elif not isinstance(record.get('artifacts'),dict):
                raise ValueError('Invalid post-fire artifact metadata.')
        return deepcopy(value)

    def change(self, callback):
        """Refresh while locked; only this facade's state is modified."""
        with self.locked():
            type(self).getInstance(self.wd)
            state = self.state
            callback(state)
            self._state = state
        from .preflight import notify
        notify(self.wd)

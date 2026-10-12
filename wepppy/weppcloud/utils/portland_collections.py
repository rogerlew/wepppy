"""Server-owned Portland collection membership; PCV-01 read admission only."""
import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode


@lru_cache(maxsize=1)
def collections():
    """Load the versioned resource catalog, never caller-supplied membership."""
    with Path(__file__).with_suffix('.json').open(encoding='utf-8') as stream:
        return json.load(stream)['collections']


def portland_runids():
    return frozenset(run['runid'] for item in collections() for run in item['ws'])


def collection_urls(base_url):
    return [base_url + '?' + urlencode({
        key: json.dumps(value, separators=(',', ':'), allow_nan=False)
        if isinstance(value, (dict, list)) else value
        for key, value in item.items()
    }) for item in collections()]


def can_read_collection_run(runid, user, *, public):
    """Collection admission is distinct from ordinary ownerless resource access."""
    if public:
        return True
    if not user.is_authenticated or not user.is_active:
        return False
    if user.has_role('Admin') or user.has_role('Root'):
        return True
    if runid in portland_runids() and user.has_role('PortlandGroup'):
        return True
    from wepppy.weppcloud.utils.helpers import get_run_owners_lazy
    return any(owner.id == user.id for owner in get_run_owners_lazy(runid))

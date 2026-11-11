import pytest
from wepppy.nodb.stream_messages import sanitize_progress

pytestmark = pytest.mark.unit

@pytest.mark.parametrize('message', [
    'Working in /wc1/runs/example/input.sol',
    'POLARIS job options: {"token":"fixture-sensitive"}',
    'Ron.set_option -> fixture-sensitive',
    'rq:job EXCEPTION ValueError: fixture-sensitive',
    'Authorization: Bearer fixture-sensitive',
])
def test_confirmed_disclosures_removed(message):
    safe = sanitize_progress(message)
    assert 'fixture-sensitive' not in safe
    assert '/wc1/' not in safe

@pytest.mark.parametrize('message', [
    'Building soils: 50%',
    'rq:job TRIGGER wepp WEPP_RUN_TASK_COMPLETED',
    'rq:job COMPLETE run_sync_rq(example, cfg)',
])
def test_control_tokens_and_progress_preserved(message):
    assert sanitize_progress(message) == message

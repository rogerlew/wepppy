from dataclasses import replace

import pytest

from wepppy.rq.webhook_settlement import Member, evaluate

pytestmark = pytest.mark.unit


def node(key, status='finished', **kwargs):
    return Member(key, 'root', None if key == 'root' else 'root', status,
                  producer_closed=True, **kwargs)


def test_failed_parent_does_not_hide_running_sibling():
    members = {'root': node('root', 'failed'), 'child': node('child', 'started')}
    assert evaluate('root', members).state == 'waiting'
    members['child'] = node('child')
    assert evaluate('root', members).execution_status == 'failed'


def test_strict_block_propagates_through_allow_failure_without_mutation():
    members = {'root': node('root', 'failed'),
               'b': node('b', 'deferred', dependencies=('root',)),
               'c': node('c', 'deferred', dependencies=('b',), allow_failure=True)}
    assert evaluate('root', members).execution_status == 'failed'
    assert members['b'].status == 'deferred'
    members['c'] = node('c', 'deferred', dependencies=('root',), allow_failure=True)
    assert evaluate('root', members).state == 'waiting'


@pytest.mark.parametrize('field', ['retry_pending', 'release_pending'])
def test_retry_and_stopped_release_keep_failure_open(field):
    root = replace(node('root', 'failed'), **{field: True})
    assert evaluate('root', {'root': root}).state == 'waiting'


def test_callback_and_canceled_live_producer_keep_hierarchy_open():
    root = replace(node('root', 'canceled'), producer_closed=False)
    assert evaluate('root', {'root': root}).state == 'waiting'


@pytest.mark.parametrize('status', ['failed', 'stopped', 'canceled'])
def test_external_blocker_contributes_outcome_without_membership(status):
    members = {'root': node('root', 'deferred', dependencies=('external',))}
    external = {'external': Member('external', 'foreign', None, status, producer_closed=True)}
    assert evaluate('root', members, external).execution_status == status
    assert evaluate('root', members).state == 'unknown'


def test_cycles_and_missing_publication_are_unknown():
    members = {'root': node('root', dependencies=('child',)),
               'child': node('child', dependencies=('root',))}
    assert evaluate('root', members).reason == 'dependency_cycle'
    assert evaluate('root', {'root': replace(node('root'), published=False)}).state == 'unknown'
    assert evaluate('root', {'root': node('root')}, incomplete=True).state == 'unknown'


def test_finished_is_execution_only_and_precedence_is_stable():
    assert evaluate('root', {'root': node('root')}).execution_status == 'finished'
    members = {key: node(key, status) for key, status in [('root', 'finished'), ('a', 'canceled'), ('b', 'stopped')]}
    assert evaluate('root', members).execution_status == 'stopped'
    members['c'] = node('c', 'failed')
    assert evaluate('root', members).execution_status == 'failed'


def test_orphan_and_cross_root_binding_are_unknown():
    members = {'root': node('root'), 'child': replace(node('child'), root_id='foreign')}
    assert evaluate('root', members).reason == 'foreign_membership'
    members['child'] = replace(node('child'), parent_id='missing')
    assert evaluate('root', members).reason == 'missing_parent'

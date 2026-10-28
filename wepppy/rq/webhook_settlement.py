"""Generic, read-only execution settlement. Domain results are never inspected."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Mapping

from . import webhook_policy as policy


@dataclass(frozen=True)
class Member:
    job_id: str
    root_id: str
    parent_id: str | None
    status: str
    dependencies: tuple[str, ...] = ()
    allow_failure: bool = False
    published: bool = True
    producer_closed: bool = False
    retry_pending: bool = False
    release_pending: bool = False
    changed_at: float = 0
    returned: bool = False
    execution_id: str | None = None
    executions: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Settlement:
    state: str  # settled, waiting, unknown
    execution_status: str | None = None
    settled_at: float | None = None
    reason: str | None = None


def evaluation_steps(root_id: str, members: Mapping[str, Member], external: Mapping[str, Member] | None = None,
             *, incomplete: bool = False) -> Settlement:
    """Evaluate an immutable snapshot; the caller must condition commit on revision.

    External members are verified dependency observations only. They never enter
    membership or the payload. Closed receipts include callbacks and execution exit.
    """
    if incomplete or root_id not in members:
        return Settlement('unknown', reason='incomplete_membership')
    external = external or {}
    if len(members) > policy.ROOT_MEMBERS:
        return Settlement('unknown', reason='member_limit')
    if set(members) & set(external):
        return Settlement('unknown', reason='foreign_membership')
    children: dict[str, list[str]] = {key: [] for key in members}
    for index, (key, member) in enumerate(members.items()):
        if index % policy.PAGE_SIZE == 0:
            yield None
        if key != member.job_id or member.root_id != root_id:
            return Settlement('unknown', reason='foreign_membership')
        if key == root_id:
            if member.parent_id is not None:
                return Settlement('unknown', reason='root_parent')
        elif member.parent_id not in members:
            return Settlement('unknown', reason='missing_parent')
        else:
            children[member.parent_id].append(key)
    visited = set()
    pending = [root_id]
    while pending:
        if len(visited) % policy.PAGE_SIZE == 0:
            yield None
        key = pending.pop()
        if key in visited:
            return Settlement('unknown', reason='membership_cycle')
        visited.add(key)
        pending.extend(children[key])
    if len(visited) != len(members):
        return Settlement('unknown', reason='membership_cycle')

    observed = {**external, **members}
    edges = sum(len(m.dependencies) for m in members.values())
    if edges > policy.ROOT_EDGES:
        return Settlement('unknown', reason='edge_limit')
    # Build dependency order even for terminal members: malformed cycles are not
    # silently accepted merely because a status formatter says finished.
    degree = {key: 0 for key in members}
    dependents: dict[str, list[str]] = {key: [] for key in members}
    for index, (key, member) in enumerate(members.items()):
        if index % policy.PAGE_SIZE == 0:
            yield None
        if len(set(member.dependencies)) != len(member.dependencies):
            return Settlement('unknown', reason='invalid_dependencies')
        for edge_index, dependency in enumerate(member.dependencies):
            if edge_index % policy.PAGE_SIZE == 0:
                yield None
            if dependency not in observed:
                return Settlement('unknown', reason='missing_dependency')
            if dependency in members:
                degree[key] += 1
                dependents[dependency].append(key)
    ready = deque(key for key, count in degree.items() if count == 0)
    order = []
    while ready:
        if len(order) % policy.PAGE_SIZE == 0:
            yield None
        key = ready.popleft()
        order.append(key)
        for dependent in dependents[key]:
            degree[dependent] -= 1
            if degree[dependent] == 0:
                ready.append(dependent)
    if len(order) != len(members):
        return Settlement('unknown', reason='dependency_cycle')

    outcomes: dict[str, str] = {}
    waiting = False
    for index, member in enumerate(observed.values()):
        if index % policy.PAGE_SIZE == 0:
            yield None
        if not member.published or member.status not in policy.TERMINAL | {'created', 'queued', 'started', 'scheduled', 'deferred'}:
            return Settlement('unknown', reason='unverified_state')
    for index, key in enumerate(order):
        if index % policy.PAGE_SIZE == 0:
            yield None
        member = members[key]
        if member.retry_pending or not member.producer_closed or member.release_pending:
            waiting = True
            continue
        if member.status in policy.TERMINAL:
            outcomes[key] = member.status
            continue
        if member.status != 'deferred':
            waiting = True
            continue
        blockers = []
        for edge_index, dependency in enumerate(member.dependencies):
            if edge_index % policy.PAGE_SIZE == 0:
                yield None
            prerequisite = observed[dependency]
            if prerequisite.retry_pending or not prerequisite.producer_closed or prerequisite.release_pending:
                continue
            if prerequisite.status == 'deferred' and dependency in outcomes:
                # Logical blocking is never an actual FAILED status, including
                # an allow_failure descendant of a blocked strict prerequisite.
                blockers.append(outcomes[dependency])
            elif prerequisite.status in {'failed', 'stopped', 'canceled'}:
                if prerequisite.status == 'failed' and member.allow_failure:
                    continue
                blockers.append(prerequisite.status)
        if blockers:
            outcomes[key] = max(blockers, key=policy.PRECEDENCE.__getitem__)
        else:
            # Ready-but-deferred work may still be released; don't invent a block.
            waiting = True
    if waiting or len(outcomes) != len(members):
        return Settlement('waiting')
    return Settlement('settled', max(outcomes.values(), key=policy.PRECEDENCE.__getitem__),
                      max(member.changed_at for member in observed.values()))


def evaluate(root_id: str, members: Mapping[str, Member], external: Mapping[str, Member] | None = None,
             *, incomplete: bool = False) -> Settlement:
    """Synchronous convenience for tests; dispatcher advances evaluation_steps."""
    steps = evaluation_steps(root_id, members, external, incomplete=incomplete)
    while True:
        try:
            next(steps)
        except StopIteration as done:
            return done.value

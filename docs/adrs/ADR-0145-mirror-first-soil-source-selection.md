# ADR-0145: Mirror-first soil retrieval with recorded SDA fallback

Status: accepted direction; implementation pending.
Date: 2026-11-18
Decision venue: this operator/Codex conversation. Participants: Roger Lew and Codex.
Decision owner: Roger Lew. Implementer: Codex.

## Decision and rationale

The deployment may default new/unconfigured projects to the unofficial JSON mirror
with USDA SDA XML as fallback. Explicit saved project selections remain authoritative.
Fixture parity across SSURGO/STATSGO supports proceeding; comprehensive geographic
and live SDA comparisons are deferred until recovery. Actual source data still must
be imported and its declared scope retained. Forest activation is authorized now;
forest1 and production activation remain the next scope.

Fallback covers transient availability and missing mirror component coverage, not
numerical invalidity or malformed source/cache identity. Retry the entire requested
collection using SDA's separate cache, with at most 30 seconds of network acquisition
per source and 60 seconds across selection. There are no retry sleeps in this mode.
The budget excludes soil modeling and local persistence; existing explicit XML mode
retains its historical retry behavior. Optional missing rows do not trigger fallback.

Record attempts, fallback reason and actual supplier; preserve unknown upstream
release. No soil formula, threshold, serialization or invalid-soil substitution
heuristic changes. A source change can change underlying soil values: pin the mirror
release and make the fallback source visible rather than treating sources as identical.

## Alternatives and evidence

Reject waiting for nationwide live parity: it defeats outage resilience. Reject
row-level cross-source merging: it hides which release formed a soil profile.
Reject permanent automatic source switching: each later build should try the mirror.
Evidence: soil-data-access/artifacts/wepppy-parity/json-client/validation.json;
501 canonical files, 24,049 records and 499 verified base-soil sidecars.

## Risk and recovery

An unavailable SDA is not guaranteed recovery. Fail explicitly with both attempt
reasons if both sources fail. Corrupt metadata and contract violations remain visible.
Restore explicit XML configuration to opt out, retaining original caches and artifacts;
rollback the deployment default without rewriting existing project identities.

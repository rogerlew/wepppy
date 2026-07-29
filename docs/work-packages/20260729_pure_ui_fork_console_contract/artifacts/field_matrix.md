# SURF-04 Contract Evidence Matrix

| Boundary | Producer-owned identity | Executable evidence | Result |
| --- | --- | --- | --- |
| Authorized render | Exact source run/config, query-derived option defaults, bearer token only for authenticated users | Four route-context tests and three actual-render variants | Conforms |
| Anonymous CAP | Section `fork`, disabled submit, solved token only in direct fork POST | Actual render plus direct block/solve/submit Jest | Conforms |
| Authenticated submit | Renewable bearer/session authorization and exact form booleans | Direct real-client Jest plus rq-engine authorization tests | Conforms |
| Repeat execution | One initialization/submission owner per console | Direct repeated-import Jest | Conforms |
| Recovery | Encoded source/config key; identifiers only; invalid/cross-scope records removed | Direct valid, hostile, and cross-scope storage Jest | Conforms |
| Status lifecycle | Source `fork` channel, bounded heartbeat, stream-trigger reconciliation, poll-authoritative terminal state | Direct StatusStream/poller Jest and ADR-0021 evidence | Conforms |
| Cancellation | Exact accepted job id and renewable authorization | Direct success/stale-auth Jest plus rq-engine cancel tests | Conforms |
| API/enqueue | CAP/public or authenticated access, validated target/options, one accepted job/destination | RQ-engine fork-route tests | Conforms |
| Worker/destination | Copy exclusions, empty output directories, identity normalization, marker/cache handling, terminal triggers | Fork RQ/helper tests | Conforms |

## Findings

No production contradiction was found. The retained code changes are direct
regression coverage at the route/render/client seams.

The 2026-05-06 fork-copy package's sole accepted low-severity gap is closed:
query/default values are now proven through route context, actual hidden config
and checkboxes, and the exact client payload.

`wctl check-rq-graph` reports drift in the existing static graph artifacts.
SURF-04 changes no enqueue site, dependency edge, worker signature, or graph
artifact, so regeneration is outside this package.

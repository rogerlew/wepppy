# GridMET Redis admission contract

Status: implementation contract, 2026-09-07. Parameter provenance is in
[ADR-0050](../adrs/ADR-0050-gridmet-redis-admission.md).

## Scope and public configuration boundary

`wepppy.climates.gridmet.admission` coordinates one shared FIFO pool for point
JSON and gridded NetCDF HTTP attempts. Its frozen `GridMetAdmissionConfig`
contains primitive, pickle-safe values, never a connection, lock, or thread.
Public GridMET acquisition functions accept keyword-only `admission=None`.
Literal or omitted `None` always disables admission, even when the environment
is enabled. These functions never resolve environment implicitly. Disabled
calls construct no admission controller or Redis connection and perform no
Redis I/O. Existing result shapes, payload validation, retry policy, and atomic
NetCDF publication remain unchanged.
Specifically preserve redirect refusal, transient statuses, three attempts with
5/10-second retry sleeps, 32/512-MiB point/grid byte ceilings, and exact payload
date coverage from [ADR-0028](../adrs/ADR-0028-gridmet-download-retry-concurrency.md).

WEPPpy orchestration boundaries explicitly call
`GridMetAdmissionConfig.from_env()` once per operation and pass its result to
all GridMET calls. This includes observed GridMET, precipitation monthlies,
PRISM/Daymet GridMET wind, SNOTEL supplementation, and the multiple-interpolated
build service. Any intermediate public climate client accepts and forwards the
same optional argument; it does not reinterpret `None`. Process-pool tasks
receive the immutable configuration, with connections created in each child.
The multiple-interpolated build retains its local four-process ceiling.
The call inventory also covers `gridmet.client.retrieve_timeseries`, Daymet's
`_retrieve_historical_timeseries_wrapper` and `interpolate_daily_timeseries`
process-pool path, `_resolve_daymet_wind`, and GridMET branches of
`_apply_depnexrad_daily_temp_overrides`. Indirect library clients propagate
literal `None`; their NoDb orchestration callers resolve environment once.

## Configuration states and values

`from_env()` strips whitespace and compares the enable variable without case
sensitivity. Absent, `false`, `0`, `no`, and `off` return `None` without
parsing other admission variables. `true`, `1`, `yes`, and `on` enable parsing.
Every other value, including empty text, is a configuration error before Redis
or HTTP activity.

Enabled configuration uses the following defaults. Forest explicitly supplies
these values; the committed development Compose enable default is `false`.

| Environment variable | Enabled default | Meaning |
| --- | --- | --- |
| `GRIDMET_REDIS_ADMISSION_LIMIT` | `4` | Maximum live Redis permits, shared by point and grid |
| `GRIDMET_REDIS_ADMISSION_WAIT_TIMEOUT_SECONDS` | `900` | Overall deadline for scheduling admission across retries |
| `GRIDMET_REDIS_ADMISSION_LEASE_SECONDS` | `300` | Active lease duration after acquisition or renewal |
| `GRIDMET_REDIS_ADMISSION_QUEUE_TTL_SECONDS` | `60` | Ticket liveness since its last waiting heartbeat |
| `GRIDMET_REDIS_ADMISSION_POLL_INTERVAL_SECONDS` | `0.25` | Base wait-poll interval with bounded jitter |
| `GRIDMET_REDIS_ADMISSION_KEY` | `wepppy:gridmet:admission:v1` | Shared operational namespace |

The limit must be a positive integer, excluding booleans. Timings must be finite
positive numbers, excluding booleans, NaN, and infinity. The key must be a
nonempty bounded ASCII identifier using letters, digits, colon, underscore,
hyphen, or period; braces and whitespace are rejected. The length limit is 160
characters. Values in a supplied configuration are
validated as strictly as environment input.

Redis connect and socket timeouts are each two seconds, with automatic Redis
retries disabled. The renewal interval is `min(lease_seconds / 3, 5)` seconds.
Require `lease_seconds > 3 * (renewal_interval + 2)` and
`queue_ttl_seconds > 3 * (1.5 * poll_interval_seconds + 2)`. Waiting poll jitter
ranges from half to one-and-a-half times the configured interval, clipped to
the remaining admission deadline. These relationships leave multiple chances
to refresh live state without making the queue TTL an HTTP timeout.

Before an enabled HTTP attempt starts, require its lease duration to exceed
`max(connect_timeout, read_timeout) + renewal_interval + 2`. Current point and
grid timeouts remain `(10, 60)` and `(10, 120)` seconds. This is a check on
individual configured blocking intervals, not a total transfer-time guarantee.

## Redis authority, atomic state, and configuration agreement

Connection settings come only from `redis_connection_kwargs()` and
`RedisDB.LOCK`. Connections are lazy and process-local. All atomic script keys
use one Redis Cluster hash tag derived from the validated namespace, with
versioned suffixes for metadata, sequence, queue, ticket liveness, and active
leases. No cross-slot script is permitted.

Redis `TIME` is the authority for queue and lease expiry. A Redis sequence
orders unique tickets; a cryptographically random ownership token belongs to
one attempt. A ticket cannot be admitted without its matching live token.
Lua operations atomically prune expired entries, inspect live state, and move
only the live FIFO head into the active pool when capacity exists. Multiple
free slots are filled by successive FIFO transitions. FIFO refers to Redis
enqueue order among continuously live tickets, not process launch order.

A namespace records a protocol/configuration fingerprint covering its limit,
lease duration, queue TTL, wait timeout, and polling interval. Every mutating
operation rejects conflicting configuration before touching owned live state
or admitting a request. Concurrent clients must not independently enforce
different limits on the same key. An entirely idle namespace may atomically
initialize a new fingerprint; changing configuration while clients are still
running requires draining/recreating them together. A read-only inspection may
report the authoritative fingerprint without adopting a caller's policy.

No bare increment/decrement counter, unexpiring owner set, pub/sub notification,
or client wall clock is a correctness boundary. Redis key retention must exceed
live entry expiry and eventually reclaim idle namespace metadata; observation
prunes stale logical entries even when no background janitor is running.

## State transitions and ownership

| State | Required behavior |
| --- | --- |
| Enabled, valid, Redis reachable | Enqueue a unique owned ticket and evaluate admission atomically |
| Enabled, invalid | Raise configuration error before outbound HTTP |
| Redis unavailable or command outcome unknown | Fail closed; never assume a permit was acquired or renewed |
| Namespace absent or empty | Initialize policy atomically; head may acquire if capacity exists |
| Populated queue | Refresh only the caller's live ticket; report queue position and occupancy |
| Stale waiting ticket | Prune after queue TTL; it no longer blocks FIFO; a resumed owner must obtain a fresh ticket |
| Active | Count toward limit; renew only while token matches and original lease is still live |
| Expired lease | Prune; renewal cannot resurrect it; former owner raises lost-lease error |
| Canceled or timed out waiter | Remove only matching owned queued state; later attempts get a new sequence |
| Released holder | Remove only matching live owned permit; no capacity counter underflow |
| Foreign ownership | Reject renew/release/cancel; never alter another owner's entry |
| Configuration conflict | Explicit error; no admission under competing policy |
| Corrupted Redis types or malformed state | Fail closed with sanitized state/configuration error; do not delete or repair foreign state |

Abandoned waiters become eligible for removal within queue TTL of their last
heartbeat; abandoned holders within lease duration of their last successful
renewal. Removal occurs at the next Redis operation, or eventual whole-key
expiry when the namespace is idle. A killed process cannot permanently consume
capacity. Cleanup after exceptions attempts only owned state, uses bounded
Redis calls, and preserves the primary error while reporting cleanup failure.

## Permit lifecycle, errors, and timeout accounting

The controller exposes an ownership-safe permit context manager and an
immutable snapshot. Snapshot fields include ticket state, zero-based waiting
position (`None` when not queued), queued count, active count, configured limit,
and monotonic elapsed wait. Counts describe live state at one atomic instant;
position is not an ETA. Observation does not renew another client's liveness.

The implementation interface shared by clients is
`GridMetAdmissionController(config).acquire(deadline=..., request_kind=...)`,
returning a context manager whose entered permit exposes `check()`.
The deadline is an absolute `time.monotonic()` value initialized once before
the first admission attempt. The context starts background lease renewal
before returning control to HTTP code. `check()` raises any recorded
renewal failure or lost lease. It also independently rejects local lease expiry,
even when the renewal thread has not run after a process pause. The local
monotonic expiry is conservatively bounded by the acquire/renew command's
pre-call monotonic timestamp plus the granted lease duration, never the reply
receipt time plus duration. Delayed replies past that bound cannot authorize
HTTP. Only a confirmed matching live renewal advances the local bound. Exit
stops renewal, performs ownership-safe
release, and raises a recorded admission failure even if payload receipt
otherwise appeared successful. Redis construction stays inside enabled paths.

Clients check validity immediately before and after `requests.get()`, before
and after each blocking stream iteration, and after response close. Hold the
permit through response closing, then release it before parsing/validation,
conversion, atomic file publication, or retry backoff. Every retry reenters
FIFO with a new token. One monotonic admission deadline covers elapsed queue
wait, completed transfers, validation, and backoff across retries; it is never
reset by a retry. No new admission starts once exhausted. An already admitted
transfer may finish after the admission deadline if its lease remains valid;
this deadline is not a total HTTP-transfer timeout.

Distinct exceptions identify invalid/conflicting configuration, admission wait
exhaustion, Redis unavailability, and lost lease. They remain distinct from
ordinary upstream failures through dedicated `GridMetAcquisitionError`
subclasses and are not retried as transient upstream errors.
Redis/ownership failures are fail-closed even during streaming. Sanitized
messages include operation kind and bounded queue/active context when known,
never credentials, tokens, Redis connection URLs, or full GridMET query URLs.

## Safety guarantee and limits

The atomic boundary guarantees at most `limit` live Redis permits. Cooperative
clients check ownership and stop consuming/publishing results after detected
permit loss. A Redis lease does not fence the upstream GridMET server: expiry
cannot forcibly terminate an existing remote request. A paused process,
partition, prolonged DNS resolution, or trickling response can outlive a lease
or delay local cancellation. Consequently this design does not promise a hard
upstream socket ceiling under arbitrary process suspension or network failure.

Background renewal is required during blocked reads; renewal only between
chunks is insufficient. On renewal failure the owner records the failure,
stops admitting further HTTP work, and closes the response as soon as control
returns. Requests read timeouts bound socket inactivity rather than total
streamed wall time; DNS and a thread stalled inside I/O do not have a hard
application wall-time bound. Tests must separately prove live-permit occupancy,
cooperative HTTP failure behavior, and killed-owner reclamation. They must not
claim these establish upstream fencing. A hard remote concurrency guarantee
would require upstream fencing or a separately bounded transport, outside this
contract.

## Acceptance and operations

Use real Redis, independent processes, and two Forest containers to prove FIFO,
peak occupancy equal to a test limit of two with at least six contenders,
observable queuing, foreign-token rejection, mismatch rejection, expiry,
cancellation, clock disagreement, and empty final state. Independently observe
one actual public GridMET client enter admission and return a valid result.
A failed upstream call can prove cleanup but cannot satisfy successful download
acceptance. Test namespaces include a unique candidate/timestamp suffix; probes
refuse mutating test operations on both the default canonical key and the
effective configured operational key (including an overridden environment
value), and never flush Redis. Inspection of either operational key is read-only.
Regressions must cover a paused foreground resuming before its renewal thread,
as well as acquire/renew replies delayed beyond their conservative validity.

Inspect the operational namespace read-only. Rollback sets enable false and
recreates the same affected Forest workers, then verifies fresh configuration
resolves to `None`. Drain existing clients before deleting any exact namespace.
Forest acceptance excludes batches, production Compose, registry builds, and
Kubernetes deployment. The later openwepp.org batch remains operator-owned.

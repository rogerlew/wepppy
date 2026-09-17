# PF-R01 logical soil currentness: justified unresolved

Independent correctness review of the proposed bounded process cache, the
retained SQLite reproductions, and the measured snapshot reader. Production,
tests, named projects and canonical contracts were not changed by this review.

**Disposition: PF-R01 remains a confirmed medium-severity false-stale limitation,
recorded as justified unresolved.** A bounded process cache is a useful possible
optimization, but it cannot satisfy all seven cases under the existing read-only
polling and retained-snapshot requirements. No partial implementation or new
storage policy is approved here. Package closeout must disclose this limitation;
it must not describe all accepted M3 currentness as logical-content based.

## Confirmed behavior and the smallest relevant boundary

[The retained baseline](postfire_remaining_freshness_review.md) and
`postfire_remaining_probe.py` exercise real SQLite reads, inventory, accepted
comparison and strict verification. Link, chmod, touch, byte-identical atomic
replacement, VACUUM, committed-WAL checkpoint and unrelated-table insertion all
preserve the consumed schema and typed logical component/chorizon hashes but
make accepted M3 equality stale. The first four preserve main-file bytes; the
last three change physical representation. These are actual bounded reproductions,
not a claim of a complete numerical M3 execution or SQLite cache collision.

`production.sources(model='M3')` inserts `production_soils.inventory` into
`selections['soil_inputs']`. `inventory` returns raw dependency states and
main/WAL/SHM state. `_source_snapshots_current` still compares those selections
exactly. Removing ordinary-file timestamps elsewhere therefore cannot resolve
this boundary. Moreover, removing only `cache_state` would leave the main
database stat tuple in `dependencies` and preserve the false-stale behavior.

The appropriate eventual equality is the already consumed `source_schema` and
`logical_sha256`, plus the other soil authority/dependency fields. Keep typed
values, duplicate ordering, nonfinite encoding, selected columns, policy and
absence semantics unchanged. Collection/MUKEY evidence, source paths, raster
masks, THICK bytes/units/grid/bounds and prepared evidence remain independent
dependencies. A SQLite equality amendment would not complete raster closure.

Strict execution is a different comparison: `soil_snapshot.verify_snapshot`
checks schema, raw source state and logical hashes; `production_soils.verify_soil`
also checks dependency state. `production.execute_m3` verifies the soil outside
the acceptance lock, then `_current_authority` and strict artifact checks guard
locked publication. All those checks remain unchanged. Their rejection of the
seven mutations during an active build is expected and must remain tested.

## What a process cache could and could not prove

A bounded in-process mapping could remember a successfully observed physical
generation's consumed logical identity. Its physical key would need the actual
selected path, verified main bytes, WAL bytes or explicit absence, and the
logical interpretation version. It would need a coherent association between
that key and the original snapshot read, not a hash obtained later from a
different generation. Main/WAL/SHM state, journal rejection, no-follow admission,
limits and source rechecks remain guards around observation. SHM bookkeeping is
not a substitute for logical content or an independent scientific dependency.

With an already proven mapping, new metadata for byte-identical files can cause
hash revalidation followed by logical reuse. Existing verified-digest admission
and access checks would still apply. A logical cache stores a small identity;
it need not retain parsed rows or introduce a persistent datastore.

However, an unknown physical key after checkpoint, VACUUM or an unrelated-table
edit has no value to look up. A digest cannot distinguish an irrelevant table
edit from a consumed horizon edit. It must obtain a fresh logical observation.
Worker/process boundaries, eviction and restart also invalidate any assumption
that a needed mapping happens to be warm. The RQ worker's in-memory observation
is not automatically present in the state-serving process.

Existing accepted predictor artifacts can establish an earlier logical identity
only after verifying their binding to the accepted result. They cannot assign
that identity to an unknown current physical key. Current snapshot manifests
record source stat state and logical hashes, not an original-main/WAL digest
receipt. Copy-side SQLite housekeeping also prevents assuming that later copy
bytes are an original physical receipt. Do not reconstruct historical proof by
hashing today's source, attach a current stat tuple to an older read, or loosen
legacy equality merely because a plausible manifest exists.

Consequently, a warm-cache optimization alone does not remove all seven cases.
Returning stale on a miss would retain the reported limitation. Returning
current without observing the new logical core would introduce false-current
behavior. Neither outcome is a completed PF-R01 correction.

## Exact policy conflict on a cache miss

The controlling clauses require all of the following:

| Canonical owner | Existing requirement | Consequence |
| --- | --- | --- |
| [Production M3, source delivery and freshness](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md), lines 129–134 | “Preflight stays bounded and read-only; no raster computation or network work during state refresh.” | A state poll does not create a new project snapshot attempt. |
| [M3 runtime, raw records](../../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3_runtime.md), lines 183–189 | “Never connect SQLite to the shared source.” Copy main and existing WAL into a “fresh visible attempt-owned” snapshot directory and retain copies for lossless replay. | Reading live SQLite directly is forbidden; the existing safe logical reader creates retained files. |
| Same runtime, lines 170–181 and 400–406 | Keep source main/WAL/SHM guards; `snapshot_cache` and `verify_snapshot` require a fresh visible output directory for each read. | A process cache does not authorize an alternate reader or change transaction guards. |
| [Artifact observability, required design gate](../../../standards/artifact-observability-standard.md), items 1–5 | Project work products and failed copies must be visible through normal tools and included in archive/restore; an exception requires explicit operator approval. | A hidden temporary directory, deleted copy, or unintegrated off-project directory is not a compliant escape. |

There is therefore **no currently authorized runtime location** for a newly
created polling-time logical snapshot. The existing module's visible
attempt-owned layout is appropriate during an authorized mutation/build, but
creating it during a state read violates read-only preflight. `/tmp`, process
memory treated as a substitute for retained records, and `/wc1/batch` do not
gain normal project browse/archive coverage merely by being accessible on disk.
The disposable QA batch root is evidence storage for this investigation, not a
new production storage precedent. Existing attempt reconciliation in `get_state`
does not authorize unrelated scientific snapshot creation.

## Cost and future decision boundary

[QA's retained measurements](soil_logical_identity_performance_qa.md) survey 54
local project caches and measure three actual source sets without connecting
SQLite to a named source. Warmed coherent logical snapshots cost 46–209 ms and
retain roughly 0.19–1.29 MB per observation. Verified physical-set checks settle
at 0.29–0.64 ms with zero source bytes read, versus 1.5–14.5 ms for existing soil
inventory. The physical measurement includes SHM and is diagnostic; it is not
the implemented performance of a proposed main/WAL logical cache. These are
OS-cache-warm results, not cold-storage/NFS acceptance or supported-limit costs.

A future correction requires a separately reviewed, operator-authorized
readiness/snapshot policy that reconciles when retained logical observations may
be created with read-only state polling. Its contract must name retention,
browse/archive, legacy accepted proof, process-cold/eviction behavior and measured
state-refresh cost. Alternatively, a bounded evaluation of an owned native
read-only logical reader could establish a different primitive; it must prove
committed-WAL parity, noninterference and the artifact policy before adoption.
Neither a new SQLite algorithm nor a service, watcher, persistent cache or
background acquisition is proposed or authorized by this review.

Retain PF-R01 as justified unresolved and preserve all current strict guards.
The work-package [complexity budget](../package.md#complexity-budget) expressly
allows that inventory disposition. Closeout must distinguish this remaining
false-stale limitation from the fixed ordinary-file consumers and PF-R02, and
must not silently claim semantic soil currentness, a new polling permission, or
runtime acceptance. No additional probe was needed: the seven retained actual
cases and the measured safe reader already establish the conflict.

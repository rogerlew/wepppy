# NFMS-01 consumer and failure-stage matrix

Discovery at `2f2bd0ef49f7521f0b888c94d4cdd16e473de416`, 2026-10-31 UTC.
Read-only audit by `/root/consumer_audit`, plus primary base review.
“Confirmed defect” below means source establishes exposure; the base and real Soils probes
have executed reproduction so far. No row implies repaired behavior.

| Boundary / caller | Identity / file / lifetime | Failure stage and owner | Existing recovery / evidence | Disposition |
| --- | --- | --- | --- | --- |
| `base.py:1647 locked`, `:773 nodb_setter` | Live singleton or detached object; controller file; held references survive call | Domain or persistence failure after own acquisition | Unlock only; `baseline_probe.py` proves held/cache B and subsequent B+C persistence | Confirmed defect; shared recovery |
| `base.py:1701 dump_and_unlock` | Same object; controller file | Dump pre/postcommit, unlock, validation or hook failure | No recovery; context caller unlocks only | Confirmed defect; classify commit, preserve direct caller semantics |
| `base.py:1774 dump` | Caller object and file | Precommit failure while token owned; postreplace errors also possible | Temp cleanup, stale rejection; intentional explicit retry tests | Verified intentional low-level retry; do not discard payload by default |
| `base.py:1380 getInstance` | Cached singleton held across operations | Unchanged disk after failed mutation | Signature equality returns dirty cached object | Confirmed defect; cannot infer memory clean from disk signature |
| `core/wepp.py:1643 parse_inputs` | Wepp and nested option objects; wepp.nodb | Valid parse then persistence fault; owned context | Shared context only | Confirmed exposure; inject replace failure after valid input |
| `core/soils.py:2016 _build_gridded` | Soils; soils.nodb; held controller | Assigns initial saturation/ksflag before missing SSURGO error at 2040 | Shared context only | Confirmed reachable domain defect; baseline_probe.py reproduces rejected 0.9 saturation in later save |
| `core/wepp.py:1887 _check_and_set_phosphorus_map` and `:1962 _check_and_set_baseflow_map` | Aliased options in live Wepp; wepp.nodb | Later raster read fails before lock acquisition | Mutates options before final locked block | Confirmed defect outside shared recovery; stage locally |
| `core/wepp.py:1933 _prep_phosphorus`, `:2001 _prep_baseflow` | Retained option aliases; phosphorus.txt / gwcoeff.txt | Consume option state after map helpers | No failed-state check | Confirmed consequence path; reacquire accepted options; prepared readback pending |
| `batch_runner.py:489 set_rq_job_id_fresh` | Fresh-hydrated same BatchRunner; batch_runner.nodb | Acquired failure; acquisition failure separately guarded | Clears only mtime; `tests/nodb/test_batch_receipt_transaction.py` tests next-read refresh | Confirmed held-reference gap; preserve acquisition protection |
| `_derived_build.py:64 finalize` | Fresh-hydrated controller; per-controller file | Apply/dump fails, possibly after artifact publication | Signature invalidation; commit outcome classification exists | Confirmed held-reference gap; preserve artifact policy |
| `single_input_sources.py:142 _accept_source` | Controller metadata; landuse/soils file | Manual mutation/dump, recovery load can fail | Finally reloads selected source metadata | Confirmed recovery-failure gap; preserve primary exception |
| `microservices/rq_engine/wepp_run_payload.py:319 _apply_grouped...` | Soils and Watershed; two files | Before any or after first commit | Restores snapshots and redumps on exception | Confirmed commit-aware conflict; reconcile existing bounded rollback before editing |
| `mods/postfire_debris_flow/migration.py:115 _admission`, `:381 _commit` | Controller _state; domain file | Manual acquisition then state assignment/dump failure | Unlock boundary lacks live-state repair | Confirmed manual gap; domain contract required |
| Postfire `publication.py:24`, `source_preparation.py:314` | Reads controller under lock | Artifact publication, no NoDb mutation in audited block | File publication boundary separate | Verified unaffected by NoDb mutation recovery; do not rewrite |
| `core/climate.py:1414 _build_climate_prism`, postfire `postfire_debris_flow.py:60` | Live object; climate/postfire file | Explicit intermediate dump, then later failure | Shared context or manual flow | Confirmed commit-sensitive consumers; retain committed generation |
| `watershed_mixins.py:1021 require_centroid` | Watershed live state; watershed.nodb | Uses global islocked before mutation/dump | Ownership of actual caller unresolved | Unresolved; trace all callers before class closure |
| RQ scoped cache guards | Redis payload and hydrated controller | Before mutable hydration | Scoped cache clear prevents stale initial mirror only | Verified insufficient as recovery; preserve placement |
| Subclass hooks and transient caches | Wepp/Soils/Landuse/mod hooks; Watershed transient fields | Reload or postcommit hook error | Legacy normalization, logging and resource lifecycle | Unresolved until lifecycle/fault tests; no universal snapshot assumption |
| Optional/initial/detached/readonly reads | No prior file or detached object | Initialization failure / absent optional | Existing allow_nonexistent and readonly paths | Compatibility gate pending; do not fabricate file or reject valid absence |

## Aliases and indirect consumers

WEPP map helpers are reached through `wepp_prep_service.py:92`,
`rq/wepp_rq.py:802,971,1043`, `rq/project_rq.py:1092`, and
`batch_runner.py:762`. These consumers must use accepted options after failure;
top-level replacement cannot repair arbitrary previously returned nested aliases.
The full descendant/catch-and-continue inventory remains an implementation gate.

## Required evidence not yet executed

Retain file, exception stage, owner and reference identity in each new regression.
Cover cancellation, serialization, temp write/fsync, replace, stale generation,
owner loss, postcommit metadata/notification/unlock/hook, intermediate commit,
failed recovery and subsequent explicit recovery. Test same-process readers/writers
and real Redis if lock coordination changes. No resource/performance or prepared
artifact repair evidence exists yet. No class-wide closure is claimed.

Same-object token replacement requires explicit regression: `_ACTIVE_LOCK_TOKENS`
is keyed by controller identity, so replacement acquisition may overwrite the
old context's token. Cleanup must use transaction-specific ownership.

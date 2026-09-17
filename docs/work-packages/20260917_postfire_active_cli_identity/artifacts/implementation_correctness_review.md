# Independent implementation correctness review

2026-09-17. Reviewer: `active_cli_correctness`.

**Final correctness and runtime acceptance: PASS. All review gates complete.**
No open correctness finding remains in the final reviewed production delta. No production or test files edited by this reviewer.

## Findings and disposition

- **P2, closed: hashless M3 source-preparation rebase acquired a new hash.**
  An admitted legacy snapshot without `content_sha256` can correctly pass
  exact-stat admission. After absent-source preparation,
  `run_preparation.py::prepare_for_run.rebase` assigns the newly sampled full
  snapshot, adding hashes. A subsequent CLI ctime change then gains the new
  exception despite no admission-time digest. Preserve the original absence
  of `content_sha256` in the rebased snapshot after verifying the fresh snapshot.
  The implementation now does so. `legacy_baseline.log` reproduces the missing
  omission; `legacy_final.log` passes 21 targeted cases. Its new native test
  verifies hashless durable rebase, successful unchanged M3 execution, subsequent
  actual WEPP link rejection and prior acceptance preservation. This closes the
  checkpoint's explicit hashless compatibility requirement.

- **P2, closed: malformed snapshot types retain rejection behavior.**
  Admitted `inputs=None` or a list, or hashless `files=None`, previously failed
  snapshot equality as `superseded`. The new helper can instead raise an
  incidental `TypeError`/`AttributeError`. The final helper now requires both
  snapshots and their `files` mappings to be dictionaries before self-validation.
  Eight direct regressions cover `None`/list snapshot or files values on each
  side of comparison. `final_boundary_pass.log` passes all 107 selected cases,
  including 45 freshness cases, M1 integration and native M3 admission stages.
  No broader schema or valid-state behavior changed.

- **P2, closed:** the first admission revision checked `expected.get('dnbr')`
  and unintentionally accepted missing M3 `dnbr` or unexpected outer snapshot
  keys. Both admission paths now compare every non-input field exactly against
  the required dNBR/frequency mapping before the narrow input comparison.
- **Test fixture issues, closed:** the expanded M1 integration
  initially ignored `content=False`, then included climate in the watershed-only
  upload mock. The latter made climate an uploaded dNBR artifact, correctly
  rejected by the unchanged strict artifact finalizer. These were fixture defects,
  corrected without relaxing publication guards; `focused_final.log` passes.
- **Coverage expanded:** native M3 initially exercised only link creation.
  The matrix now includes unlink/rematerialization at all four stages, across
  two authentic soil fixture variants, with the actual WEPP materializer and
  real NoDb/native model boundary. All 24 cases pass in `focused_final.log`.

## Code and contract review

Checkpoint `567eacf7d45b77008629444e9c14fcd6378e7de8` is the current ancestor
commit and contains the contract decision, independent reviews, canonical
amendments and failing native M3 baseline. Production changes remain in its
working-tree descendant, satisfying the ancestor checkpoint sequence.

`production.py::_worker_source_snapshots_current` validates available complete
hash maps, compares non-hash fields exactly, and normalizes only the current
active CLI record to the admitted record after confirming identical path, size
and mtime. The normalization cannot erase a difference in another input or
selection. Only a pre-existing valid admitted hash authorizes the exception.
`signature(..., strong=True)` calls the uncached descriptor-bound digest and
checks the resulting stat record against the sampled current snapshot. Hashless
attempts retain exact metadata behavior.

Both worker admission paths retain a deep copy of the admitted authority.
The shared authority guard covers M1 Kf preparation, M3 source verification,
both pre-publication checks, and both locked finalizers. The M3 preparation
rebase invokes the same comparator after its existing exclusion of owned source
preparation assets. It still verifies the promoted metadata candidate hash.
Existing attempt ownership, dNBR checks, eligibility, readonly behavior,
SQLite/soil verification, result/predictor artifact guards, and model equations
are unchanged.

Tests directly exercise the filesystem boundary: original hard-link failure,
unchanged link/unlink/rematerialization, changed bytes with restored mtime,
path and source-selection differences, another dependency's ctime drift,
hashless/malformed hash maps, cached-digest bypass, symlinks, replacement and
observable read-generation races. M1 coverage uses real model artifacts but
mocks source discovery; native M3 tests exercise real owner discovery.

## Reviewed runtime and regression evidence

- `focused_final.log`: **153 passed**, including the 24 native M3 stage cases,
  M1 admission/pre-publication/locked-publication, and adversarial helper checks.
  Six subsequently added malformed-outer-snapshot cases are included in the
  full suite; their source was independently reviewed.
- `restart_workers.log`, `restart_web.log`, `post_restart.json`: rq-worker,
  rq-engine and web restarted; ordinary worker identity is uid 1000/gid 993,
  groups 993, umask 022. Queues were idle at the recorded restart boundary.
- Successful ordinary UI/RQ job `fa299be5-45b0-448b-b1d1-718445c1529a`
  ran 18:49:11–18:49:44 UTC on the independent disposable clone. The actual
  WEPP materializer created, removed and recreated its CLI hard link after
  predictor execution started. The mutation occurred at 18:49:19 UTC, inside
  the job interval. Native M3 completed and its report/download checks passed.
- `live_overlap_identity.json` records unchanged path/size/mtime/content and
  changed ctime, with inode shared by the actual WEPP input. Independent readback
  of the clone's accepted attempt `status.json` confirms the original admitted
  ctime `1789670233637306862` was retained, rather than rewritten to the newer
  ctime `1789670959164274455` to evade the guard.
- Negative UI/RQ job `5bff6acb-16ad-4252-aeae-f3668c4e3509` mutated one CLI
  digit during native execution while keeping file size and restoring mtime.
  It correctly became `superseded` before publication. Prior acceptance
  `68186dc8d0d74673a04be41ca9767853` remained selected. The original CLI bytes
  were then restored. Independent file hashing confirms restored SHA-256
  `884cb1660dc22d413d77547860fdbd0af2f50459eb8b3558ed3cf442dc3f1f9f`.
- `browser_clone_records.log`: ordinary authenticated browse returned HTTP 200
  for failed status/error records and the accepted results. The report remained
  current after restoration. Failed evidence was retained.
- `archive_regression.log`: canonical record archive/restore regression passes
  (1 passed, 24 deselected). This is automated archive coverage, not a claim
  that the entire live clone was archived during this review.
- `source_copy_verification.json`: clone setup verified unchanged source bytes
  across 6,840,257,872 bytes. `strong_hash_timing.json`: uncached verification of
  the actual 1,151,532-byte CLI took 9.48 ms on this host.

The overlap invokes the normal owned WEPP input materializer in the actual
worker container while a normal native M3 RQ job runs; it does not run a second
complete WEPP watershed simulation. That is the precise filesystem boundary
that caused this incident. There is no mocked comparison or model calculation
in this live acceptance.

## Named recovery and final acceptance

Named recovery job `0fd409ce-8e3c-480a-af2c-8a5fd571c7f8` completed through
its normal Run control, accepting `0c7899f7ac6f464e80e3f873a4c75fe1`.
`browser_named_settled.log`, `browser_named_records.log` and
`named_recovery_identity.json` retain current-after-reload status, five verified
attachments, and ordinary HTTP 200 access to original failure status/error and
new results. Independent on-disk readback confirms completed status and the
same current/admitted CLI SHA-256 as the successful disposable overlap. The
prior accepted `f493a714df9d4fbfbfd4370c46ad54f8` and failed
`932b890ecffa4f659d438bcf0dad68e5` attempt directories remain present.
Scientific input hashes match the failed incident attempt; only engine identity
changed. Named recovery is therefore **PASS**, not inferred from earlier
transient admission conflicts.

Commit `2b00c4165` contains the reviewed initial implementation and descends
from checkpoint `567eacf7d`. The final frozen production delta also includes
reviewed guards for malformed snapshot types and preservation of hashless legacy
rebases. Final implementation `1003fe9addfcfc308ecdfdce56a3f36011845536`
contains these last corrections. Independently hashed committed production and
preparation files match `runtime_code_identity_final.json` exactly. Final
rq-engine/rq-worker/web restart logs confirm the frozen code was reloaded.

`full_suite.log` passes **8,971 tests, 99 skipped**, in 23 minutes 21 seconds.
That full run began on the main repair; the later legacy/type conformance
corrections are additionally covered by `legacy_final.log` (21 passed) and
`final_boundary_pass.log` (107 passed). Do not describe the entire full suite
as having started on the final commit. `final_native_legacy.log` additionally
passes both native legacy variants on frozen commit `1003fe9ad` (2 passed,
66 deselected, 36.99 seconds).

After the final restart, named job `0c3bb451-0e7a-4814-95f5-3f1d2f219d49`
completed, accepting `8190121c8a4b45e1952861e74d909693`. The final browser log
confirms current status after reload and all five report downloads.
`browser_named_final_records.log` confirms the original failed status/error and
new accepted results remain ordinarily browsable. The final named identity
record matches all scientific source hashes from the original failed attempt.
Independent reviewer on-disk status/hash readback additionally confirms the
accepted engine hashes for both changed production files equal frozen commit
`1003fe9ad`, and the current CLI bytes equal the admitted original digest.
This final success supersedes the intermediate engine-refresh status above;
no correctness or runtime-acceptance work remains outstanding.
All production findings are closed.
A legacy-only preservation fix does not invalidate the reviewed modern hashed
runtime behavior; no additional unrelated model run is required solely for it.

Mutation during the coherent verification window may still fail explicitly;
the repair promises unchanged-byte acceptance for settled ctime-only drift,
not arbitrary-writer snapshot isolation. Existing model-selection semantics
remain outside the changed delta: persisted UI selection is separate from
immutable attempt model/frequency, as defined in `docs/model_selection.md`.

# MIPA-01 producer implementation evidence

User approval: “approved. proceed”. Contract ancestor: `4579b11ce`.
WEPPpy implementation: `390bc4f59` (local). Paired Rust: `5e3540f` (published).
Producer source repairs are implemented; native acceptance and package closure
remain HOLD. See the [canonical contract](../../../schemas/mofe-input-identity-contract.md)
and [operator/developer guide](../../../dev-notes/mofe-input-preparation.md).

## Repaired boundaries

| Findings | Source repair and evidence |
| --- | --- |
| PMET-01/02/03 | Enumerate every staged crop; resolve final Disturbed element class and staged soil texture. Deterministic eight-character aliases distinguish original name, coefficient pair and physical plant definition. Rebind initial/year/residue graphs; preserve original mapping keys, repeated bytes and archive/restore. Distinct real Disturbed fixture checks every year crop against the intended pair. |
| MAN-01 | Both merge paths remap residue operation 10/12 plant references; distinct downstream residue properties survive serialized readback. |
| MAN-02/03 | Flatten complete chronological source cycles, preserve common period without N, or emit exactly explicit N. Fix repeated rotation year-count serialization and independent expanded years. Actual coprime 991/997-cycle write with N=3 avoids common-period allocation. |
| SOIL-01/02 | Per-element developed exemption and 9005 texture in normal/debug serializers; both reversed orders and final restrictive-layer alias tested. |
| COVER-01 | Numeric contiguous IDs and identical band/year element sets in both real cover writers; 12 distinct blocks exercise ordering. |
| SLOPE-01/02 | Rust rejects nonpositive/nonfinite enabled buffers and lengths that serialize to zero before opening output. Preserve exact normalized endpoints and equal/overlong-buffer controls. |
| Map equality / stale deck / nested source | Equal map fractions now fail instead of gaining cells. Real staged slope/soil/management counts must agree; each soil stack member must contain one OFE. |

Secondary review found stale header provenance after reusing a prepared management
in MOFE/rotation synthesis, then same-original/same-pair distinct plant definitions
collapsing. Scenario-carried provenance and definition-aware aliases resolve both.
Safe raw native duplicate labels with equal PMET pairs remain valid without graph
rewriting; all potentially retained native keys are reserved before alias allocation.
No parameterization formula, value, fallback policy or native capacity cap changed.
API-01's inherited ignored `min_length` remains a separate behavior decision.

## Actual artifacts and source isolation

The owned `prepare_fork_run` path produced `/wc1/runs/mi/mipa-awake-20261102`
from `/wc1/runs/aw/awake-versatility`. Source manifest is retained in
`actual_project_fork_v2.json`; source files remained unchanged. The first candidate,
calm-amalgamation, had no required MOFE soil files and was not fabricated into an
acceptance case. An initial `/workdir` destination was unwritable by the container
worker; the canonical `/wc1/runs` destination works under uid 1000/gid 993.

`prepare_actual_clone.py` calls real landuse synthesis, `Wepp._prep_multi_ofe`
and `Wepp._prep_pmet`; it reparses staged files, checks 72 hills/235 elements over 35 years (1–11 elements per hill) and
byte-identical repeated PMET. `readback_actual_coefficients.py` independently
joins every final class/texture to every serialized year's crop key. Receipts:
`actual_project_prepared_v3.json` and `actual_project_coefficients_v3.json`.
The 24 table rows share pair 0.95/0.8 in this actual project, so the distinct-pair
fixture, not this control, proves discrimination. Source/module hashes are in
those receipts and the final implementation manifest. No model was run on the
copied project, and no fresh runoff/ET/report consequence is claimed.

The first readback script attempted nonexistent `Management.rotations` after
preparation; `actual_project_preparation_attempt1.log` preserves that failure.
Corrected readback uses the real `man.loops` hierarchy.

## Rust provenance

Sibling commit `5e3540f684c8606f4140afcd72ed5a21df5ab85f` is pushed and verified
on upstream main. Only MOFE/map sources and scoped docs were committed; unrelated
calendar/HBP/registry edits remain untouched. Unit commands use
`PYO3_PYTHON=/usr/bin/python3.12 RUSTFLAGS='-C link-arg=-lpython3.12'`:

- `cargo test -p wepp_interchange_rust --lib mofe::tests --offline`: 4 passed.
- `cargo test -p watershed_abstraction_rust --lib --offline`: 5 passed.
- `cargo build -p wepp_interchange_rust --offline`: succeeded; private candidate
  loaded directly by `probe_rust_candidate.py`, with generated/readback files in
  `rust_candidate_v1/`. Installed release extensions remain unchanged.

Candidate extension SHA256:
`dfb30d5734debd07618899189d24ace75b06ee226cfdc1c99c065cd7dc46389e`.
This is source/candidate producer validation, not production release validation.

## Validation and review

Validation is complete for the authorized producer scope. Final results are
summarized below; the intervening entries retain the execution history. Retained interim
checks: focused management/soils/Disturbed/RAP/staging/archive suites passed 295,
then 304 tests; 149 management/Disturbed tests passed after scenario provenance;
new definition-aware tests pass before continuing the broader treatment suite.
`wctl run-stubtest wepppy.wepp.management.utils.multi_ofe` and
`wctl check-test-stubs` pass. Broad-exception enforcement against `4579b11ce`
passes with zero net new broad handlers.

`wctl run-pytest tests --maxfail=1` stopped with 485 passed/27 skipped at
`tests/disturbed/test_matrix_contracts.py::test_published_report_sources_and_content_are_current`:
the published benchmark pins the old management writer hash. This is related
freshness debt, not an unrelated pass or evidence of numerical regression. The
historical report/provenance was preserved by ancestor/hash before the fresh
refresh documented below. A continuation excluding only that
known pin and already-run native matrix reached 2663 passes/122 skips before a
placeholder slope fixture failed the new count guard; it is corrected to a real
five-element slope matching that test's soil and management.

Independent artifacts: `m2_correctness_review.md`, `m2_qa_review.md`,
`m2_security_review.md`. Linked-source preservation and visible failed-attempt
recovery were independently reviewed; canonical archive/restore tests use real
filesystem operations. Native capacities differ by selected binary; no universal
cap was imposed. NATIVE-01/02/03 and selected 9005 consumer validation remain
unresolved. Correct producer files cannot close native FC/HK ownership or prove
PMET dynamic lookup. No deployment or automatic existing-project repair occurred.

## Source quality and final review disposition

Correctness, QA and security each pass for the bounded producer sources, with no
unresolved source findings. Independent final selections passed 45 correctness
checks and 9 security checks; QA independently replayed its description-only
composition case and reviewed the 31-test identity/Disturbed result. The final
combined management/soil/Disturbed/RAP/staging/archive selection passed **306**
tests (`final_focused.log`). Source hashes in `implementation_source_manifest.json`
and the v2 actual-project receipts match that reviewed implementation. The v2
receipt hashes the actual installed Rust `.so`, while v1's field identifies only
its Python package wrapper; neither receipt claims the candidate replaced it.

Code-quality telemetry was run separately under `/tmp/mipa-quality.*` to preserve
unrelated repository reports. Radon is unavailable, so cyclomatic-complexity
numbers are not established. The main PMET helper is now 160 lines: the increase
is the bounded resolution/alias/graph/publication pipeline, with existing walker
and signature reuse. QA accepted this structure and recorded private-helper
coupling as non-blocking maintenance debt; no speculative graph framework was
added. Broad-exception enforcement has zero net added broad catches.

The historical benchmark freshness failure is resolved by its documented refresh
procedure. A fresh 96-case single-OFE matrix passed **99 tests** in an unused
root. All **768** standard output hashes equal the retained 2026-10-10 baseline;
192 generated input hashes changed (96 management and 96 soil files).
`disturbed_matrix_comparison.json` retains every difference. Canonical context,
report and provenance were regenerated by `refresh_disturbed_report.py`; the
report/Usersum contract selection passed **16 tests**. Existing historical native
evidence and the original report remain identifiable by ancestor/hash. The
pre-existing dirty Usersum generated index was not modified or staged by this
refresh, per the root instruction. This single-OFE benchmark does not exercise
copied heterogeneous projects or close any native MOFE acceptance dependency.

The fresh matrix is retained at
`/wc1/holdouts/mipa-disturbed-producer-20261102/disturbed_matrix0` (5,873,301,289
bytes), with all 1,056 input and 768 output manifest entries rehashed after copy.
`disturbed_matrix_durable.json` records retention. Canonical source freshness now
also pins the executed soil helper, horizon boundary and soil utility module;
these were missing from the earlier benchmark's source list. QA independently
verified all entries, all 37 source pins and the final report hash.

Extended testing also exposed legacy fixture inconsistencies at the new deck
count guard. Treatment tests now supply a real five-element slope; scenario
artifact tests now use real two-element slope/soil decks instead of bypassing
copying with an empty soil stub; mapped-kslast tests synthesize the two-element
management their existing slope and soil require. Production count validation
was retained. These are test-data repairs, not loosened preparation rules.

Final additional checks: **257 passed** for identity and treatment-soil artifacts
(the identity collection preceded the final description-only test, which is
covered by the final 306 and 31-test selections); **90 passed** for real scenario
artifact propagation after replacing placeholders; **10 passed** for canonical
report/freshness contracts after adding all soil-source pins. The broad
continuation has separately passed the repaired mapped-kslast module; its final
result is recorded below when complete.

Packaging inspection found bootstrap errors in the earlier actual-project probe:
its top-level orchestration lacked the multiprocessing main guard. Although final
artifact readback succeeded, that log is not a clean normal-preparation receipt.
The harness now uses `if __name__ == '__main__'`; a fresh full preparation and
readback produced v3 receipts with exact reviewed source hashes, 72 hills/235
matching elements, unchanged source and repeat-byte equality, with no traceback
or runtime error. Earlier v1/v2 receipts and raw logs remain retained.

Source/document `git diff --check` passes when excluding retained raw console
logs. Those logs intentionally preserve original trailing whitespace and terminal
blank lines; they are evidence, not formatted source. No diagnostic text was
removed to make a formatting check green.

Committed-code observability confirms PMET helper length 33→160 lines (red
observe-only band) and file SLOC 35→201 (green). The bounded graph pipeline and
reviewed private-helper reuse explain the growth; the rationale above remains
applicable. Cyclomatic complexity is unavailable because Radon is not installed.
Final broad-exception enforcement still passes with zero net new broad handlers.

A later continuation passed 4,407 tests before exposing working-directory
coupling in a new test fixture. All newly added fixture paths now resolve from
`__file__`; identity tests deliberately change into a temporary directory. The
next WEPP segment passed 516 tests before a legacy rotation-boundary fixture
looked for the old year-count comment. Its locator now matches the canonical
serializer label; the 1000/1001 boundary assertions remain unchanged. These
follow-up repairs change tests only, leaving reviewed producer source hashes
and native benchmark evidence intact. Focused Disturbed/archive path checks
passed 4 tests. Remaining terminal coverage is recorded below.

## Final disposition

**Producer source acceptance: PASS.** Correctness, QA and security findings are
closed. WEPPpy source commit `390bc4f59` and published Rust source commit `5e3540f`
contain the repairs. Follow-up test changes remove working-directory assumptions
and align a fixture's rotation label; producer source hashes did not change.

The terminal continuation passed **2,529 tests** (`broad_terminal_final.log`),
including the corrected 1000/1001 rotation boundary, WEPP runner and WEPPcloud.
Combined with the retained earlier passing segments and targeted reruns of each
failed fixture, no exercised regression remains unresolved. Validation was split
at failures; this is not a claim of one uninterrupted green `pytest tests` run.
No single aggregate pass count is quoted because several selections overlap.

Final decisive gates:

- 306 focused management/soil/Disturbed/RAP/staging/archive tests pass.
- 257 identity/treatment and 90 scenario-artifact checks pass, with the snapshot
  qualification above; final identity cases also pass from a temporary cwd.
- 99 benchmark tests pass; all 768 fresh native output files equal the retained
  single-OFE baseline. Report/Usersum checks pass 16, final freshness checks 10.
- 4 Rust slope tests and 5 Rust map tests pass; isolated candidate binding readback
  succeeds. Installed release extensions remain unchanged.
- Stubtest, test-stub checks, documentation lint, relative-link checks and source
  whitespace checks pass. Raw console whitespace is retained deliberately.

**Package/native acceptance: HOLD.** NATIVE-01 capacity, NATIVE-02 adapter lookup,
NATIVE-03 FC/HK ownership, selected 9005 consumption, full job/browse/output/report
validation and a paired release remain open. No native engine repair, production
deployment or existing-project regeneration is claimed. The next work requires
that separately scoped authority and selected-binary evidence; do not close the
package or infer unrestricted heterogeneous correctness from producer acceptance.

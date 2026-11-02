# MIPA-01 secondary QA review

Reviewer: `mipa_qa`, 2026-11-02. Contract ancestor: `4579b11ce`.
Scope: current Python producer/test changes and the bounded Rust changes in
`wepp_interchange/src/mofe.rs` and `watershed_abstraction/src/lib.rs`. Unrelated
dirty files and native-engine implementation are outside this review.

## Disposition

**PASS for bounded producer source quality.** QA findings are resolved. The
primary review's prepared-plant provenance and distinct-definition findings now
have discriminating regressions and passing readback. No unresolved QA blocker
remains; the independent correctness and security artifacts retain their own
dispositions. This review does not grant deployment or native acceptance.

## QA findings and resolution

| ID | Finding | Resolution |
| --- | --- | --- |
| QA-01 | The new Disturbed MOFE lookup branch initially lacked a direct writer regression; generic PMET helper tests could not detect a class/soil join error. | Added a real two-OFE soil/management fixture with distinct textures, final classes and coefficient pairs, actual yearly-reference readback, and byte-identical retry. |
| QA-02 | Sorting expected/actual coefficient values would allow a crop-to-coefficient permutation to pass. Unsafe-token coverage was also missing. | The regression now checks every alias against its original mapping key and exercises long, space/comma, Unicode and quoted source names. |
| QA-03 | Replacing Disturbed preparation removed its existing entry diagnostics. | A concise preparation log was restored; detailed per-file failures retain input/rebuild context. |
| QA-04 | Medium: after adding physical-definition alias discrimination, description-only differences still made the binder reject equal native plants as conflicting. Alias allocation used landuse/data while plant deduplication included descriptive text. | Resolved: plant deduplication uses the same native-definition identity as alias allocation. A regression and independent actual-writer reproduction now pass synthesis, readback and byte-identical retry. |

The correctness review separately found stale provenance after management
synthesis, then a distinct-plant-definition collision. The repair carries
validated metadata on each plant through existing graph copies and renames,
and includes native plant parameters in alias identity. The regressions exercise
ordinary/deduplicated MOFE and rotation synthesis, original-name mappings,
distinct active-crop `hmax` values on both OFEs, and stable repeated preparation.

QA-04 direct reproduction used `wctl exec weppcloud python -c ...` with a
temporary directory: prepare the oats rotation fixture with scalar 0.5/0.8,
parse and deep-copy it, change only the second copy's first plant
`description[0]`, write `ManagementMultipleOfeSynth([first, second]).build()`,
then call the real `pmetpara_prep` again. It raised
`ValueError: Conflicting plant definitions for L84_Oats in p1.man.` Native
parameters and intended coefficients were identical; descriptive text alone
must not manufacture a conflicting native identity.

The same direct reproduction now passes, including real management readback and
an additional byte-identical PMET retry. The full command and output are retained
in `m2_qa_description_final.log`. Passing `pmetpara.py` SHA256:
`6e5ed8973c92c356a2527eb06ba2f9bd697df97b3c77abe60ff3cc07ae1fad3f`.
Reviewed `managements.py` SHA256:
`c83275c7b2dd5331f991086158b3a2605a056c9431551d388128391872842664`.

## Test quality and evidence

The tests use actual management and soil serialization/readback, real file
replacement and archive operations, distinct downstream values, both merge modes,
and malformed-input failure assertions. NoDb singleton stubs isolate setup while
leaving the changed writers real. Rust tests preserve an existing destination on
invalid input and inspect normalized endpoint records on a representable short
segment. These tests discriminate the reported producer failures.

Independent QA command:

```sh
wctl run-pytest tests/wepp/management/test_mofe_input_identity.py tests/wepp/soils/test_mofe_identity.py tests/nodb/test_wepp_multi_ofe_management_propagation.py tests/nodb/mods/test_rap_ts_cover_transform.py --maxfail=1
```

Result: **33 passed**, 2 dependency warnings. This was before the subsequent
provenance fixes; retained output is `m2_qa_targeted.log`. The implementer's later
149-test management/Disturbed run passed after the scenario-carried metadata
change. After the definition and description-equivalence fixes, the implementer
ran `wctl run-pytest tests/wepp/management/test_mofe_input_identity.py
tests/nodb/mods/disturbed/test_pmetpara_prep.py --maxfail=1`: **31 passed**;
QA inspected that completed log and the added assertions. These counts describe
different snapshots and must not be summed or presented as a full-suite pass.

## Residual debt and limits

`wepppy/wepp/management/pmetpara.py::_write_prepared_pmet` is the main complexity
increase: it resolves contexts, allocates aliases, binds graphs and publishes
files. The stages remain visible, with validation before writes and a small
source-preserving replacement helper. Reusing `ManagementRotationSynth`'s private
reference walker and signature helpers avoids duplicating the graph rules, but
creates coupling. If another graph consumer is added, give those shared helpers
an explicit internal interface and preserve the synthesis-to-PMET regressions;
no new abstraction is necessary to finish this bounded repair.

Ambiguous duplicate scenario labels remain an explicit limit when a graph must
be rewritten: the existing parser/synthesizer machinery is name-keyed. Ordinary
safe duplicate labels with equal coefficients retain their original native
numeric-reference bytes through the no-rewrite path. Reconstructing ambiguous
numeric references for aliased rewrites is not justified here: normal synthesis
assigns distinct labels, strict uploads require uniqueness, and Disturbed is
excluded for uploads. Keep this limitation explicit rather than claiming all
arbitrary legacy managements can be rewritten.

Producer tests do not establish native PMET selection, capacity safety, FC/HK
ownership, 9005 consumer behavior, or fresh report correctness. The actual-project
case has uniform coefficient pairs, so distinct coefficient identity relies on
the discriminating fixture rather than that control alone. Native and deployment
HOLDs remain separate from this source-quality assessment.

## Follow-up benchmark and final receipt review

The related published-report freshness failure was repaired through a fresh
96-case single-OFE benchmark, not by merely replacing expected hashes. QA
inspected the completed **99-pass** benchmark log, refresh script, canonical
report/context diff, comparison receipt and final provenance. Only the reviewed
date and explicit single-OFE/native-HOLD scope changed in the report; its
numerical tables remain unchanged.

An independent `wctl` readback rehashed all **1,056 input entries and 768 output
entries** from the fresh matrix and compared them with both current provenance
and the contract ancestor's published baseline. Exactly **192 input entries**
changed (`.man`/`.sol`); **zero outputs** changed. The comparison receipt matched
the independently computed changes. Command/output:
`m2_qa_evidence_review.log`. QA also verified the report hash and all listed
source hashes.

Two evidence omissions found during this follow-up were resolved: the canonical
source list now includes the changed soil utility and its boundary/serialization
helpers, and the fresh matrix was copied from container scratch to
`/wc1/holdouts/mipa-disturbed-producer-20261102/disturbed_matrix0`. QA inspected
`preserve_disturbed_matrix.py` and its completed
[durable-copy receipt](disturbed_matrix_durable.json), which verifies all 1,056
input and 768 output entries after copying 5,873,301,289 bytes. The canonical
provenance points to that retained root; QA independently checked all 37 current
source pins after the addition. The historical baseline remains retained.

The final versioned actual-project receipts now bind the reviewed producer source
hashes and identify the installed Rust `.so` by actual module path and hash. QA
independently checked those hashes and the 72-hillslope/235-OFE agreeing deck
counts. The installed extension remains distinct from the isolated candidate;
the configured `wepp_260803` engine was not executed in the copied-project probe.
All 235 coefficient checks use the same 0.95/0.8 pair, so the separate distinct-
coefficient fixture remains necessary. These receipts strengthen final-source
producer evidence without proving heterogeneous native behavior. No new QA
blocker remains; any extended-suite outcome belongs in the final validation
inventory rather than being inferred from this benchmark.

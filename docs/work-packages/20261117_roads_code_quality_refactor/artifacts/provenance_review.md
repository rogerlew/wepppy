# Roads historical source-ledger provenance review

Date: 2026-11-17 UTC. Independent reviewer: `roads_final_qa`.

## Disposition and limits

**Accept acknowledgment of the traced preexisting source drift in the historical
staleness ledger. No unresolved medium/high provenance finding.** Preserve
`stale_full_project_routing`, the existing notice, all recorded execution-source
hashes, report/results/provenance bytes and the vendored report. A ledger update
must retain the previous reviewed identities and cite this review, not silently
replace hashes or claim that historical outputs were rerun or recertified.

This review covers the four unchanged task-baseline files omitted from the current
refactor's 18-file source review, plus the earlier RUPC changes in `roads.py`.
It distinguishes that earlier behavior change from the separately reviewed
baseline-to-candidate extraction and two current-policy harness files. No source
or ledger file was edited by this review.

The governing rule is the rerun/review-or-explicit-staleness requirement in
[Roads validation suite contract](../../../schemas/roads-validation-suite-contract.md#evidence-and-report-semantics),
with [RUPC-02](../../../schemas/roads-unrutted-strip-contract.md#rupc-02-top-of-hillslope-placement)
and [ADR-0146](../../../adrs/ADR-0146-unrutted-partial-crossing-strips.md) defining
the accepted geometry and lifecycle policy. The operator explicitly approved
using RUPC-02 as authority; [contract_reconciliation.md](contract_reconciliation.md)
records that decision and the prohibition on recertifying historical reports.
Older work-package reviews below are provenance evidence, not living authority.

## Exact lineage

Task baseline is `96555f2f95326350d2d7007c19327378ea831ab0`.
Direct `git show` byte hashing and `git merge-base --is-ancestor` checks establish:

- RUPC-01 contract checkpoint `8e87b2363` precedes implementation
  `e6989a622f7aea86126d098f48e2e57c15f35b61`.
- RUPC-02 contract checkpoint `f46d59422009d5adb8641b1d2b7494cd5f9b788a`
  precedes implementation `43a44ec0da6fd9ee2070d9f5cad90e9f79ef50e6`.
- All four commits are ancestors of the immutable task baseline.

| Path | Last ledger-reviewed SHA-256, or original published identity | Task-baseline SHA-256 |
| --- | --- | --- |
| `wepppy/nodb/mods/roads/_parameterization_comparisons.py` | `6e6ee7abbebc1916931a056477cd8064fc83b83262ef5e9791b781df4d293f0a` | `394599497dd62f6ac2cee494829aef44239bb5caf1504745c00596228fe4ba04` |
| `wepppy/nodb/mods/roads/_unrutted.py` | Absent from original provenance and ledger | `9ab3aa83737b259ee6fe9a74b21391764de4757db6e62e3e50a5891d50bc9784` |
| `wepppy/nodb/mods/roads/monotonic_segments.py` | Original published `2b8d6be522233b6444ca21639dfc46a63775125178f97241cc8c4120f911ad5f` | `6600bdf6b03f675f31165dce8442d712dd093e7c0fc9c069691ef8d1c8b6ae06` |
| `wepppy/wepp/interchange/_roads_lifecycle.py` | `187f6b3003859ba1b5a02bffc9909243951409313100e5dcd5ba0a8966ff2760` | `86019c49af0c34382f6f1301d22588e53bb10c048b13744e4ac4499457352eaa` |
| `wepppy/nodb/mods/roads/roads.py` | `72c38b63ec51ffade9fc10268cd092204bd071272099906a51ddbd9c8fd81c52` | `ddb110e083fbc85eb29da9efbc66c636ee3333247e1ddbbd6a7337588564f7c5` |

The first four files are byte-identical between baseline and this task's candidate.
The fifth subsequently changes through the reviewed refactor to
`a53920220275bc46afc2ba405f061788c3621b87fc22b4c0bcbd3a3796775321`;
[QA](qa_review.md), [correctness](correctness_review.md) and
[security](security_review.md) cover that separate interval.

`_parameterization_comparisons.py`'s last ledger hash is exactly its content at
sanitization commit `3fea2f06d`; its remaining delta is the ten-line RUPC-01
zero-contributor comparison branch. It accepts an empty summary only when the
manifest has no completed/failed profiles, otherwise raises, and records an
unavailable baseline-equivalent comparison. The baseline hash is exactly the
RUPC-01 implementation hash.

`monotonic_segments.py`'s original published hash is exactly its content before
RUPC-01. Its only subsequent delta adds `split_elevation_reversals=True` and
disables that splitting for resolved `outslope_unrutted` inputs. Other designs
retain the prior default. This is an approved preparation-policy change.

`_unrutted.py` was added by RUPC-01 at
`0bb89e7559f632c240924ca1bb571539dfeadc2e4da75a936b7432dde13ccfac`:
connected-crossing normalization, physical road geometry, precise slope writing
and emitted-area checks. RUPC-02 adds placement, downhill compensation and native
role/layout helpers, reaching the baseline hash above. These implement the
accepted abstraction and scientific limitations; they are not merely code motion.

`_roads_lifecycle.py`'s last ledger-reviewed hash is exactly commit `4654150c9`,
whose upload rollback helper was accepted in the
[earlier provenance disposition](../../20261116_vector_upload_normalization/artifacts/20261117_resumed_qa_review.md#roads-publication-provenance-disposition).
Its remaining delta is RUPC-02: durable-state reading, prepared-design/source
membership checks, summary/row placement-policy admission, and restoration of
valid old-policy archives as historical after ordinary artifact validation.
Corrupt artifacts and failed executions remain inadmissible.

`roads.py`'s last ledger-reviewed hash is exactly commit `0e861887e`. The only
file-changing commits from there to this task baseline are RUPC-01 and RUPC-02.
RUPC-01 reaches
`84d8658f8cedd892aaf6d2c432d03e019855e8bec45a0f21052e42adb632bbf2`,
adding crossing/area-conserving strip integration, membership-aware queries and
prepared-policy checks. RUPC-02 reaches the baseline hash, integrating top
placement, native role order, explicit road/fill overflow failures, downstream
compensation and retained execution provenance. The ledger must acknowledge this
behavior-changing interval separately from the current behavior-preserving
refactor; a refactor-only rationale would be incomplete.

## Accepted review and native identity evidence

RUPC-01 [correctness](../../20261117_roads_unrutted_partial_crossings/artifacts/20261117_correctness_review.md)
and [security](../../20261117_roads_unrutted_partial_crossings/artifacts/20261117_security_review.md)
reviews report no unresolved medium/high findings. They cover zero-contributor
comparison, membership, prepared-policy admission, finite areas and crossing
normalization, including closure of the dense-linework performance finding.
Its [native receipt](../../20261117_roads_unrutted_partial_crossings/artifacts/20261117_native_evidence.json)
binds the exact baseline hashes of comparisons and monotonic conversion, and the
intermediate RUPC-01 hashes of `_unrutted.py` and `roads.py`.

RUPC-02 [implementation reviews](../../20261117_roads_unrutted_partial_crossings/artifacts/20261117_top_placement_reviews.md)
accept correctness and security after exact-fit, failure-provenance, restore
validation and design-relabeling findings were closed. Its
[native receipt](../../20261117_roads_unrutted_partial_crossings/artifacts/20261117_top_placement_native_evidence.json)
binds the exact task-baseline hashes of `_unrutted.py`, `roads.py` and lifecycle.
That receipt distinguishes top-placement success from five retained road/fill
overflow failures and includes separate native shape controls. These scoped
receipts are evidence for those accepted implementations, not refreshed evidence
for the old published report or authorization for deployment.

## Historical artifact preservation

Readback confirms each artifact is byte-identical to the task baseline:

- `tests/roads/analysis_provenance_current.json`:
  `44e3f899ef18162e046e983cf0b518923e19abb3838dbcd4cb45e196a5d8e3f0`.
- `tests/roads/analysis_results_current.md` and its Usersum vendor copy:
  `263174f8f56c94a9fb2773572d16f65593453df4816a6d38b7a069e97a924d7a`.
- `tests/roads/matrix_results_current.json`:
  `1735920cb524f8ac11bb7161c9e05a1b6806d849fb96b482dca788d0ba815e62`.

The report still starts with the exact retained stale notice. The appropriate
ledger action is an explicit subsequent review entry for this preexisting RUPC
interval, plus the separately reviewed refactor/harness interval, updating only
reviewed current identities. Keep the original provenance's `recorded` hashes.
`test_roads_publication.py` must continue detecting any later unreviewed source
drift; do not weaken it or alter source discovery to make this gate pass.

## Ledger and runtime closure

The integrator's resulting `tests/roads/analysis_staleness_current.json` is
accepted at SHA-256
`40fdb5224ed193fb8c50a72e7e74d512c24f52a02deca1221458756c61120cfc`.
Independent readback confirms exactly 24 reviewed identity transitions, correct
previous/current hashes, and an appended review entry naming the prior RUPC
interval, current refactor/harness interval and this evidence. Every original
`recorded` value still matches execution provenance. Earlier review entries,
stale status/notice, rationale and historical report/provenance hash fields are
unchanged. The source-discovery and publication-test implementations are unchanged.

`/tmp/roads-refactor-validation/publication-final.log` records **3 passed** against
the guarded candidate checkout. This closes the historical-staleness disclosure
gate and preserves detection of later unreviewed drift. The ledger's `5ef264810`
review label identifies the execution snapshot, including explicit harness hashes;
all 37 tested production/harness files independently match the later commit
`d6ecf9a2af77b4c39bdc834aba912cc3d1125c76` and current working bytes.

[Candidate validation](candidate_validation.md) separately establishes 527 native
tests, 6,192 raw-identical files across 516 profiles, 516 exact parsed summaries,
and 4,577 artifact comparisons across five project controls. The
[QA closure](qa_review.md#runtime-and-ledger-closure) accepts those runtime receipts
and the source identity. Historical scientific outputs remain historical; these
fresh comparisons do not recertify them. The integrator's broad-suite gate is
still pending and is not represented as passed by this provenance closure.

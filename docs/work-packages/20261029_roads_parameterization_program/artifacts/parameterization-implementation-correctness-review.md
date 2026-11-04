# Roads parameterization implementation correctness review

Status: **PASS for final source, native propagation, comparison and lifecycle evidence**.
IC-01 through IC-08 are closed. The final validation receipt separately owns the
repository-wide gate result; this review does not turn a partial broad run into a
pass. Accepted contract ancestor: `73b5da4ac`; reviewed proposal ancestor:
`9532a2968`. This is independent read-only source/science review, not the author's
self-approval. Source hashes and focused validation evidence are recorded below; refresh this
review if those bytes change before final workflow certification.

## Scope

Review `parameterization.py`, all Roads soil/management writer integration,
NoDb save/prepare/run binding and transient-state boundaries, current-result
receipt identity, role/source readback and compatible run comparisons. Check the
approved repository/project contracts against actual executable behavior. Static
source review does not certify real browser, worker, native or archive boundaries.

## Findings and dispositions

### IC-01 — medium: retained baseline precision must survive default assembly

The first helper implementation rounded all baseline header values to six
significant digits while parsing. Existing writers only format road Ki/Kr that
way; conductivity, critical shear and fill/buffer source headers are copied.
A valid retained AVKE `8.1234567` therefore passed saved-state validation but
failed default-only native readback against an artificial `8.12346` expectation.
The source baseline must retain raw numeric precision; only actual writer/override
serialization should determine rounding. Road Ki/Kr formatting applies even at
high traffic. A focused retained-precision regression is required.

Disposition: model owner preserves raw baseline precision and applies six-digit
formatting only where writers/overrides actually do so; retained-precision
regression added. Focused model/shared-management tests pass (214 tests at this review step);
additional 48-case all-template/traffic default parity passes (114 focused model
tests total). Source readback
confirms raw copied fields preserve precision and high/low road formatting matches
the production writers. This does
not change current repository numbers or authorize default adoption.

### IC-02 — medium: completed provenance cannot silently become partial

Initial `_attach_parameterization_records` accepted a completed record without a
matching soil readback, assigning empty OFEs/input files and an unavailable reason.
It also omitted missing slope/management files silently. Completed publication
must bind actual soil, slope and management inputs. Failed/skipped attempts may
retain explicit partial records, but cannot be promoted as complete evidence.
Require completed-record validation and regression coverage; the receipt's
configuration hash alone does not prove native input propagation.

Disposition: capture moved inside the native runner after input copies, binding
actual `p<id>.sol/.slp/.man`; completed records now require all three unchanged
inputs and nonempty role readbacks. Partial records remain explicit. Controller focused suite passes70 tests, including actual post-copy input
provenance and missing management rejection. Native/browser workflow evidence
remains separately required.

### IC-03 — medium: comparison requires successful publication evidence

The initial comparison reader admitted a derived snapshot with `status=completed`
without checking the original publication receipt. Snapshot generation precedes
publication; a later failure could retain it as historical diagnostics and then
incorrectly present it as a completed comparable run. Require original successful
receipt/configuration binding for both current and retained candidates, and
exclude failed/prepublication snapshots even when their raw files remain intact.

Disposition: resolved. Reader requires original completed publication receipt,
matching configuration and a publication-bound comparison snapshot SHA256. The
current candidate also passes current-result admission; retained candidates remain
explicitly historical. Prepublication and metadata-tamper regressions pass.

### IC-04 — medium: comparison must bind runtime control inputs

The initial compatibility identity covered binaries, climate, slope, management
and nonoverride soil fields but omitted runtime controls such as `wepp_ui.txt`.
A user change to those physical settings between default/custom executions could
then be attributed to the overrides. Bind actual relevant control-sidecar content
and explicit absence, retaining all sources used to establish comparability.

Disposition: resolved. Compatibility binds actual `wepp_ui.txt`, `pmetpara.txt`,
`snow.txt` and `gwcoeff.txt` content or explicit absence, as consumed by the runner,
plus normalized native run-file inputs. Comparison suite passes13 tests including
changed runtime controls and preparation-local-ID normalization.

### IC-05 — medium: preserve the ordinary `roads_params` response contract

The initial facade returned ordinary params plus a read-only parameterization
query object. The route wrapped that result inside `roads_params` as well as
providing a separate parameterization field. Existing clients roundtripping
`roads_params` would submit read-only status/groups as the strict new payload and
fail. Preserve the original ordinary-params facade return and provide the new
query field only at its documented additive response location.

Disposition: resolved in facade source; ordinary params-only return restored.
Two focused controller tests pass, including ordinary params roundtrip preserving
custom overrides. Route-level response regression is tracked with UI validation.
No existing field or ordinary API coercion was changed.

## Earlier source checks

The source separates project NoDb authority from retained source content and
transient materialized paths/readbacks. `TRANSIENT_FIELDS` uses the existing NoDb
serialization seam. Saved overrides are validated across the full retained
template/traffic set, then applied after existing traffic adjustments. Explicit
zero and native underflow are rejected, preserving native estimation-sentinel
semantics. Default/multiply/absolute are separate states rather than inferred from
a numeric zero. The source role mapping covers all template Forest rows, including
unrutted upstream/remainder roles, and does not mean arbitrary source landuse.

The downstream receipt validator reads durable NoDb JSON without controller
creation, binds saved configuration to preparation and receipt identities, and
preserves absent-key legacy receipt admission. The completed-row hash check adds
a publication barrier, but is not a substitute for IC-02 actual input evidence.

## Initial focused evidence and scope (historical checkpoint)

Model tests pass114 cases, including all16 current soil templates ×3 traffic
choices through the implemented default-only helper and repeated Forest roles.
The earlier focused run also passed148 existing shared-management tests. Controller
suite passed70 tests before the later history refinements; subsequent focused
history tests and ordinary-response roundtrip regressions pass. Comparison suite
passes13 tests, covering published receipt/snapshot identity, unavailable/single-
storm manifest binding, runtime-control differences and incompatible actual inputs.
Exact commands/results are retained by the implementation owners and parent
validation receipt; these counts are not an uninterrupted repository-suite claim.

Source readback confirms IC-01 through IC-05 corrected. Security's historical
readback follow-up is also reflected in contained paths, complete original receipt,
snapshot/manifest hashes and actual input hashes. Even unavailable/single-storm
comparison snapshots bind their manifest, without fabricating scalar metrics.

Real browser/worker/native execution, fork/archive/restore, full repository gates
and final independently read artifact evidence remain to be assessed. This source
pass does not certify those process boundaries or deployment. Parent should request
a final evidence rereview after the workflow receipt is complete.


## Source checkpoint hashes

```json
{
  "wepppy/nodb/mods/roads/parameterization.py": "e5ce6f6972ecfa7eee88f11846269235d727f0d2f4e7675e0f3e37a8707c1d14",
  "wepppy/nodb/mods/roads/roads.py": "ae418b53f7f6d9580e48ba10981dc0ac9a3c016f634c2942a7b79a1134dab735",
  "wepppy/nodb/mods/roads/_parameterization_comparisons.py": "1281d82b3e49d0b73907c01c1d1bf280920fa414b479ec365923e51d6be7b40e",
  "wepppy/wepp/interchange/_roads_lifecycle.py": "b3c68420eb79d0a6472c264f6acd56700f6257fe5fe89a8592e21198ab9da255",
  "wepppy/wepp/management/managements.py": "7b2d0624eba784313052721a4e50b2dc27104fcdcdee5fb4f9fe9960f0ff1f9d",
  "tests/nodb/mods/test_roads_parameterization.py": "80c03d3ec553ce5a2891462d5d632e7ea7ccb648051f75edfb158cc635051322",
  "tests/nodb/mods/test_roads_controller.py": "47bef842f44ffd7fb7b1811adaa756ee9dc1db382c9b6546a48d3fc96d3afde3",
  "tests/nodb/mods/test_roads_parameterization_comparisons.py": "98989a2831973fec358880b3bc7cc0b29a225426b987de3e535c67190e80527c",
  "tests/wepp/interchange/test_roads_lifecycle.py": "2a88efdf73aec06be563a5afccbe1628661d027ad8fa5741c97b3709ada30e94"
}
```

## Canonical lifecycle evidence closure

The reviewer inspected `parameterization_workflow_lifecycle_readback.py` and its
retained successful receipts. The helper decodes the owning NoDb codec without
post-load/cache hydration, validates actual native role headers and hashes, and
checks current admission. Archive inspection reads ZIP members rather than merely
checking RQ success. Canonical archive job `9666fd05-b6ed-4496-81eb-7dc849f672e9`
preserved retained parameterization and 8,131 members; Reset/Save retained the
baseline and historical custom publication while rejecting current admission.
Restore job `bd84ca55-28b3-437f-af0b-de72086b7fb4` and full fork job
`76f3b219-189d-4293-9c5b-3784faeaeacb` each restored exact custom authority, all 105
native inputs and role records, 7,223 Roads artifacts and current eligibility.
Every lifecycle readback preserved 907 baseline and 4,731 source-study files.

Evidence is `lifecycle-archive-v1.json`, `lifecycle-reset-v1.json`,
`lifecycle-restored-v1.json`, `lifecycle-fork-v1.json`, and canonical browser
receipts `archive.json`, `ui-reset.json`, `restore.json`, `fork-ready.json`.
The helper SHA256 is
`3f8236d9d4a0462c2a06fcd272c313d00280e7e96fc616f6f8c9894d417ebdab`.
`fork-private-auth-csrf-valid.json` records the final private-project authorization
checks; security review owns their boundary assessment. Failed readiness/auth
harness attempts remain retained and are not counted as successful operations.

## Confirmed shared-parser publication consumer: Disturbed

The substantive Python gate reached and passed all 96 native Disturbed cases,
then failed its publication source-identity check because `managements.py` changed
from `c83275c7b2dd5331f991086158b3a2605a056c9431551d388128391872842664` to the
reviewed `7b2d0624eba784313052721a4e50b2dc27104fcdcdee5fb4f9fe9960f0ff1f9d`.
The complete diff is the opt-in `StrictLegacyRoads` 97.3 parsing boundary; the
ordinary Disturbed producer never selects that mode. This is a real provenance
gate failure, not a failed native experiment or evidence of changed science.

Before accepting a disposition, the reviewer retained the fresh broad matrix at
`parameterization-workflow-v1/disturbed-broad-matrix-v1` and compared it with the
original publication's case hashes. All 768 native output files and 960 input
checks, including all 96 management files, are byte-identical. The other 96 inputs
are soils: each differs only in exactly one generated `#   Build Date:` comment;
all remaining bytes match the original retained files, whose original hashes
were also verified. Raw comparisons are `disturbed-broad-parity-v1.json` and
`disturbed-broad-soil-comment-review-v1.json`. No native experiment was repeated
solely to repair metadata.

The bounded fix keeps `analysis_results_current.md` and its original provenance
byte-identical. `tests/disturbed/analysis_source_reviews_current.json` records
only the exact reviewed old/current source delta and pins both original files.
The existing fast publication check now requires exact equality between all
actual source drift and the reviewed inventory, so additional or changed drift
still fails. `tests/disturbed/PLAN.md` documents this source-only compatibility
review and explicitly prohibits relabeling historical executions or bypassing a
scientific refresh. The confirmed publication consumers of this parser identity
are Roads and Disturbed; both now retain reviewed exact deltas and preserve their
original report classifications.

Focused validation: `wctl run-pytest tests/disturbed/test_matrix_contracts.py -q`
passes **10 tests, 2 warnings in 8.94 seconds**; log
`independent-disturbed-provenance-final-v1.log`. The original Disturbed report
SHA256 remains `31cbd80b8996db905a9bdb4b20666132af8a124c93abbbeebb75a98ba770b947`
and provenance SHA256 remains
`8928a034a2dce03ad0efd5b4285407830f92664879019c5ad577b36ceb951220`.
This review author implemented only the bounded test/metadata disposition, which
received a separate security-agent **PASS**. That reviewer independently rehashed
all 96 cases, confirmed unchanged original report/provenance bytes, and inspected
the exact-delta gate; raw receipt `disturbed-security-source-review-v1.json` binds
the assessment. Final gate SHA256 is
`029c7bf4d6f048912e2942d15236a7be09f9798a18cc043b85a60cf608beae67`;
review-sidecar SHA256 is
`f3425335eb9da1a37076d719a4df4724e3d8b9c3a340da335256764aab9e2124`.
Production source remains independently reviewed and unchanged.

## Historical publication provenance review

Narrow independent metadata review passes. `roads_analysis.source_hashes` now
includes the owned `managements.py` parser dependency; its one-line addition does
not regenerate results. All 11 reviewed source deltas match current file SHA-256.
The latest six-source review entry matches both current hashes and predecessor
identities (the lifecycle predecessor is the original provenance identity, because
it had no prior drift). Earlier review entries, stale notice/status, and recorded
publication identities are preserved.

Byte comparison against both HEAD and accepted ancestor `73b5da4ac` confirms these
historical publications are unchanged:

| Artifact | SHA-256 |
| --- | --- |
| `analysis_results_current.md` | `263174f8f56c94a9fb2773572d16f65593453df4816a6d38b7a069e97a924d7a` |
| `matrix_results_current.json` | `1735920cb524f8ac11bb7161c9e05a1b6806d849fb96b482dca788d0ba815e62` |
| `analysis_provenance_current.json` | `44e3f899ef18162e046e983cf0b518923e19abb3838dbcd4cb45e196a5d8e3f0` |

Independent `wctl run-pytest tests/roads/test_roads_publication.py -q` passes all
three tests (8.83 seconds), including exact drift inventory, retained report/result
hashes and vendor identity. The published full-project routing evidence remains
explicitly stale. This metadata review is not a scientific rerun or refresh, and
does not establish the pending native workflow outcome.

## IC-06 — high: durable NoDb envelope bypassed receipt binding

The native workflow exposed a gap in the prior source checkpoint: actual
`roads.nodb` uses the jsonpickle `py/state` envelope, while the lifecycle reader
looked for `_parameterization` at the plain JSON root. A bound project therefore
published the three-key legacy receipt, bypassing its configuration and snapshot
binding. The focused fixtures used flat dictionaries and missed the real wire
format. This finding reopens the source pass until the owned decode path and
realistic serialized fixtures pass, followed by a fresh native workflow.

Failure-class scan locates the production raw lookup in the shared lifecycle
identity helper. Publication and current admission both consume it; current
comparison admission delegates to that lifecycle boundary. Historical receipts
must continue checking their original evidence independently of current NoDb
identity. Preserve the failed runtime receipt as evidence and rerun the full
workflow; do not republish the existing outputs as a substitute.

### IC-06 source correction and regression closure

Independent review accepts the corrected reader: a coherent `_read_retry` opened
snapshot goes through `Roads` preprocessing and its owned jsonpickle decoder,
then validates the owning controller type and accesses its actual attributes.
It does not call post-load hydration or controller caches. Missing legacy
parameterization remains distinct from present-null or malformed state.

The lifecycle fixture now serializes a real Roads instance, explicitly asserting
`py/state` plus a shared override mapping encoded with `py/id`. Publication,
changed-authority, malformed-baseline, missing provenance, and changed snapshot
regressions use that representation. Added tests check absent legacy state,
present-null, wrong decoded type, forbidden post-load/cache calls, and unchanged
filesystem bytes during admission. Independent full lifecycle module run:
`wctl run-pytest tests/wepp/interchange/test_roads_lifecycle.py -q`: **30 passed**,
20.34 seconds. No further confirmed source gap; actual failed receipt retention
and a fresh full native workflow remain required for runtime closure.

Corrected checkpoint identities (supersede the earlier lifecycle rows):

- `wepppy/wepp/interchange/_roads_lifecycle.py`: `daf24fbc23c3fb411a0cadd0d1cb3a13a7b4bdf4f673edcf0c7647940cda9d54`
- `tests/wepp/interchange/test_roads_lifecycle.py`: `36ba3f886a893e4ba6281e25d565af0e03f4dac6644bedb955869283572342bf`

### IC-06 default runtime closure (2026-11-03 resumption)

The independent correctness reviewer reread the restarted default evidence and
the actual retained files after custom Save. Prepare job
`75640f2d-3397-41c9-9525-842c6ec12bab` and Run job
`90043676-79c3-436c-8393-27ea6558d6da` have successful browser/RQ receipts.
The corrected lifecycle source and test hashes above still match the worktree.

Raw evidence root is
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-workflow-v1/`.
`native-default-restarted-readback.json` SHA256 is
`d05b52ad662c243668b9c28090d84fd70dd1f40388dd49b7aa3a1a241c83846c`.
Independent byte checks verified all 105 soil/slope/management inputs against that
receipt and `default-native-inputs-restarted/`; all 105 role headers have expected
default conductivity/Ki/Kr/shear values; all 36 hillslope/watershed traces retain
`binary_identity_status=ok` and `WEPP COMPLETED`. The five-key publication receipt
binds configuration `6cbbdeace9b618c35a55783208561ae098e3f3c92efe0af6b7f085af9879343c`
and the actual comparison-snapshot hash, and every required report resource exists.
After custom Save, these bytes remain under the disposable project's
`wepp/roads/history/2735603bb90b44e787db50e0375acb86`; query labels them historical.
An additional direct hash comparison verifies all 105 restarted default inputs
against the preserved prefeature study source
`revised-project-sensitivity-v1/w4-f30/wepp/roads/runs/`; every file matches.

This closes the default publication/admission bypass exposed by IC-06. The failed
pre-restart attempts remain evidence and are not rehabilitated by a later passing
run. The previous unbound/disabled-Save diagnosis was unsupported: configuration
hash is computed from durable `_parameterization`, and unchanged bound defaults
correctly disable Save. Custom propagation and canonical lifecycle operations are
separate remaining acceptance checks.

## IC-07 — medium: bound projects do not display repository drift

The settings contract's “Save, reset, adoption and transport” section requires
drift information while keeping adoption unavailable. `query_parameterization`
returns the retained baseline identity but never compares it with current
repository assets, and the dedicated view has only static future-adoption text.
Thus a restored or long-lived project correctly retains its baseline but cannot
tell the user that repository defaults differ. This is a visibility contract gap,
not evidence that the project was silently rebound.

Correction is assigned to a separate implementation worker. Acceptance requires
a read-only matching/different/unavailable repository diagnostic, continued use of
retained sources when repository inspection fails, no adoption mutation, and
regressions proving bound state and generated artifact bytes remain unchanged.

Disposition: independent source review accepts `repository_baseline` query
diagnostics and escaped dedicated-view disclosure. The regression uses actual
copied repository assets, changes a comment to produce a different identity, then
removes the asset. Both cases preserve bound status, configuration hash, resolved
groups and durable NoDb bytes. Repository inspection errors remain diagnostic;
they do not invalidate retained state or change execution inputs. The worker
reports 22 focused Python tests and the full 1,033-test frontend suite passing.
The independent UX final-v2 browser pass confirms matching repository status and
native conversion disclosure after web reload; differing/unavailable states are
covered by source and backend/frontend regressions without mutating repository
science.

## Independent default/custom artifact and metric verification

The resumption's independent reviewer ran read-only checks through `wctl
run-python` against actual current custom and retained default artifacts.
`independent-correctness-readback-v1.json` under the raw evidence root retains the
results and hashes of browser/native receipts. It verifies 210 native input files
across the two executions, all 105 role headers per execution, and unchanged bytes
for the 70 custom slope/management files. Each custom driver is exactly twice its
default counterpart after native serialization; nonparameter soil contents and
all compatibility inputs also match through the retained source hashes and exact
compatibility objects.
`independent-correctness-compatibility-v1.json` adds a direct comparison of all
35 climate, slope, management and native run files byte-for-byte, all 35 soils
with only the four adjustable header values masked, and all four runtime
sidecars. Every comparison passes without relying on stored compatibility hashes.

For each execution, the reviewer independently summed 35 generated report rows
and then recomputed runoff and particle sediment from 204,540 selected daily PASS
rows. Both approaches agree with the snapshot and visible comparison. The actual
calendar is 2000–2015, modeled area is 10,737.7 m² and the shared compatibility hash
is `2409c7e1c09ab0c57ff22e34eeaac5fe53ecefed1b98638225ec2711ac7b82aa`.

| Modeled-profile quantity | Default | All twelve drivers multiplied by 2 |
| --- | ---: | ---: |
| Annual runoff (m³/year) | 2311.088949775 | 1993.68161468125 |
| Annual EVENT particle sediment (kg/year) | 9025.416676122857 | 7334.8223578414945 |
| Annual runoff depth (mm/year) | 215.23128321474803 | 185.6711972471991 |
| Annual sediment density (kg/m²/year) | 0.84053537313604 | 0.683090639321409 |

Custom Run job `28cc318e-6608-4ccc-b9b1-28fb38962546` binds configuration
`9908b75c468dfd4fc6d14460a8fee6c8842ae530237b37199908c3f71b940e15` and snapshot
`e351a5791f1bdbb13acc5b3bd4562f4d43f329725c9907a74b2f035517f8139a`.
The comparison excludes the two retained pre-restart runs with missing bound
publication receipts and reports explicit diagnostics for them. This is successful
software propagation and compatible combined-change evidence; it establishes
neither independent driver sensitivity nor watershed outlet yield, calibration,
recommended ranges or scientific default adoption.

## Final reviewed source identities

The following final-worktree hashes supersede earlier source checkpoints above.
The later changes add query-only repository disclosure, native-unit explanatory
text and scoped layout corrections; native input assembly, publication and
comparison computation bytes are unchanged from the successful native workflow.
Consequently the workflow does not need a scientific rerun for these display
changes; the web process was reloaded and final rendered evidence binds them.

The reviewer appended the IC-06 codec and IC-07 query-disclosure source deltas to
`tests/roads/analysis_staleness_current.json`, preserving every earlier review and
the original execution identities. Report, matrix results and provenance remain
byte-identical to HEAD and explicitly stale. Final focused publication gate:
`wctl run-pytest tests/roads/test_roads_publication.py -q`, **3 passed, 2 warnings,
9.51 seconds**; raw log `independent-publication-provenance-final-v1.log`.

```json
{
  "wepppy/nodb/mods/roads/parameterization.py": "e5ce6f6972ecfa7eee88f11846269235d727f0d2f4e7675e0f3e37a8707c1d14",
  "wepppy/nodb/mods/roads/roads.py": "b65713d1356143ca8ac76c62e5c28437f5e35f439df5c6af771266dd6bc5fb0a",
  "wepppy/nodb/mods/roads/_parameterization_comparisons.py": "1281d82b3e49d0b73907c01c1d1bf280920fa414b479ec365923e51d6be7b40e",
  "wepppy/wepp/interchange/_roads_lifecycle.py": "daf24fbc23c3fb411a0cadd0d1cb3a13a7b4bdf4f673edcf0c7647940cda9d54",
  "wepppy/wepp/management/managements.py": "7b2d0624eba784313052721a4e50b2dc27104fcdcdee5fb4f9fe9960f0ff1f9d",
  "wepppy/weppcloud/routes/nodb_api/roads_bp.py": "f35c73ec3a9f5b639575f3cd55de34fdc1c08a54bfc5862046cc165fdf6692fa",
  "wepppy/weppcloud/controllers_js/roads_parameterization.js": "df43f5653dde239ec1b9537afcbd2d56d8568ea1e4ce8693f90bde37c27575f4",
  "wepppy/weppcloud/templates/roads/parameterization.htm": "42d271efd290409d6172c4e589db9e61633f252db701a75199f427887f5b1beb",
  "tests/nodb/mods/test_roads_parameterization.py": "80c03d3ec553ce5a2891462d5d632e7ea7ccb648051f75edfb158cc635051322",
  "tests/nodb/mods/test_roads_controller.py": "b03ac91b83063b31f719f4a56e95f2110f0ccfbbb3702a2b7692a0e36770a6ef",
  "tests/nodb/mods/test_roads_parameterization_comparisons.py": "98989a2831973fec358880b3bc7cc0b29a225426b987de3e535c67190e80527c",
  "tests/wepp/interchange/test_roads_lifecycle.py": "36ba3f886a893e4ba6281e25d565af0e03f4dac6644bedb955869283572342bf",
  "tests/weppcloud/routes/test_roads_bp.py": "a48a3646c1b3b6360390d146fd3fe9f9d21b012136174dbc6b66eb37c779813e",
  "wepppy/weppcloud/controllers_js/__tests__/roads_parameterization.test.js": "d88361966676c94f0707394a1fac9f8651965bc90eb780b00d5eb3df379a1cac"
}
```

## IC-08 — medium: dedicated page omitted the shared stale-bundle guard

The broad gate passed 12,892 tests with 423 skips before the shared template-wiring
check detected the dedicated page's missing `controllers_gl_stale_check.js`.
Without it, the page lacked the established stale-client reload notice even
though it loaded the shared controller bundle. Earlier focused route/UI checks
did not cover the repository-wide script-pair invariant.

Disposition: source correction accepted. The dedicated `script_extras` block now
loads the existing stale-check script immediately after `controllers-gl.js`, with
both using `static_url` and `defer`. `base_pure.htm` already supplies the expected
build identity; the shared guard runs after the deferred controller bundle. The
reviewer reconstructed the prior block and recovered the exact earlier template
hash `24c62d40b20d0dc0793d753dc10e010031366e9af1ed1c7c96875b8a28816d2b`, proving
the delta is limited to that script pair. Final template hash is
`42d271efd290409d6172c4e589db9e61633f252db701a75199f427887f5b1beb`.
No Python, native input assembly, comparison, authorization or publication behavior
changes; the earlier native/lifecycle evidence remains applicable. Focused
wiring/route/render checks and final live UX evidence close this finding:

- `implementation-validation-v2/template-final-result.json` and its retained log
  record **287 passed, 6 warnings in 21.68 seconds**, including shared script
  wiring, Roads routes and Pure control rendering.
- `parameterization-implementation-ux-final-stale-v3/readback.json` records the
  actual loaded guard, both deferred scripts in order, matching expected/actual
  build ID `2026-11-04T02:31:24Z`, no false stale banner and no JavaScript errors.
  The independent UX reviewer rechecked all 420 native values and 12 comparison
  cells; desktop/mobile document widths remain 1440/1440 and 390/390.
  The correctness reviewer independently checked the guard/build/error/width
  fields and bound this readback SHA256:
  `6f65bad2e7b7ec935778dfbc0bb9fd65d82060a614e22cc0ff482873e3954c46`.

The initial broad failure remains retained. Validation's exact ordered collection
reconciliation and failed/unexecuted-tail run own broad coverage closure; this
focused pass is not presented as an uninterrupted full-suite pass.

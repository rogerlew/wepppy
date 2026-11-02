# MIPA-01 producer correctness review

## Metadata and reviewed scope

Reviewer: `mipa_contract_correctness`, independent review, 2026-11-02.
Contract ancestor: `4579b11ce`; production changes reviewed in the working tree.
Authority: [MOFE input identity](../../../schemas/mofe-input-identity-contract.md),
the existing management/Disturbed/upload contracts, and the generated-artifact
and observability standards. This review concerns producer correctness and
local evidence, not native physics, deployment or project recovery.

Inspected management parsing/serialization, calendar expansion, MOFE synthesis,
generic/Disturbed PMET, soil stacking/serialization/modifiers, RAP ordering,
the joint staging count check, and owned Rust slope/map validation changes.
Related independent review: [security](m2_security_review.md); QA follows the
final correctness disposition. Unrelated dirty files and historical rock/water
artifacts were not edited or treated as part of this change.

## Finding requiring disposition

### MIPA-IMP-01 — Medium: generated PMET identity must survive graph composition

The initial root-only `_pmet_plant_names` map became stale when ordinary MOFE,
deduplicated mixed-source MOFE, or rotation synthesis renamed/added plants.
All three actual writers emitted files that the new parser rejected with
`Inconsistent PMET identity provenance; rebuild managements.` This is a shared
consumer regression, including supported re-use of generated one-OFE 98.4 inputs.

The first remediation attaches validated `_pmet_identity` records to plant
scenarios, allowing copies/renames and the serializer to carry current keys.
That fixes stale-header readback, but a second direct probe found a remaining
collision: prepare oats, copy the prepared object with OFE2 plant `hmax=0.123`,
combine both through ordinary MOFE synthesis, then invoke scalar PMET. Synthesis
readback succeeds with six crops, but PMET raises
`Conflicting plant definitions for L84_Oats in p1.man.` The original-name/pair
alias key collapses distinct crop definitions after provenance removes the
synthesis namespace.

Required correction: distinguish the original coefficient-mapping key from
the generated plant-definition identity. Equal coefficient pairs may share
values, but scientifically different plant definitions must remain independently
addressable. Preserve deterministic retry, mixed prepared/unprepared sources,
ordinary and deduplicated MOFE, rotation composition and original mapping keys.
Do not discard alias provenance or reintroduce first-reference selection.

The next remediation adds serialized plant-definition identity to alias allocation
and passes an independent active-crop check (OFE heights `0.49988` and `0.123`,
with byte-identical repeat). QA then reproduced the complementary case: changing
only a prepared plant description still produces a conflict, because alias
allocation compares executable plant data while deduplication compares the full
object including descriptions. Those equivalence rules must agree; a description
difference cannot turn scientifically identical plant definitions into an error.

Both probes used real writers/parsers under `wctl exec weppcloud`, disposable
temporary directories and the existing oats/corn fixtures. They changed no
repository source or actual project. The earlier exploratory source-count probe
was abandoned before producing a valid fixture; it is not acceptance evidence.

## Interim findings already dispositioned

- Lost provenance on ordinary parser/write cycles now has explicit reader and
  serializer support. An independent actual-writer probe confirmed original-name
  mappings survive read/write, and deleting the header from marked alias output
  raises a rebuild error before PMET replacement.
- Expected OFE count equality is checked in both directions, and normal staging
  now checks slope/soil/management counts before publishing the management.
- Arbitrary global application of checked-upload scenario limits was removed.
  Exact selected-native limits remain an explicit M4 dependency; no producer
  success is permission to execute an expanded graph beyond those limits.
- Native-safe, coefficient-unambiguous ordinary controls preserve management
  bytes. Legal duplicate native labels with distinct numeric scenarios and equal
  coefficients remain eligible for that fast path; ambiguous name-keyed graph
  rewriting still fails explicitly.
- Explicit `sim_years` reaches `build`, `render` and `write`. A serialized
  coprime-period/short-N test exercises bounded expansion. Horizon-independent
  landuse generation retains full reusable cycles and the existing period limit;
  it does not infer a climate horizon or truncate later-editable phases.

## User outcomes and state coverage

| State or input family | Required outcome | Reviewed evidence |
| --- | --- | --- |
| Ordinary single-OFE/native-safe names | Complete PMET rows; unchanged management bytes | Direct regression |
| Empty collection | Existing zero-row table; no ready-deck claim | Source path; final validation inventory must state execution coverage |
| Populated MOFE, shared crops, different coefficients | Distinct native identities and correct per-OFE graph references | Real binder regression; real Disturbed staged soil/management regression |
| Multiple rotations and mixed periods | Exactly N chronological years and complete downstream phases | Real serialization/readback, both merge branches, explicit bounded writer |
| Residue operations 10/12 | Intended plant reference on each OFE | Distinct source definitions and both merge branches |
| Soil order/developed exemptions | Per-element modifier policy and final restrictive-layer alias | Reversed-order serialized soil regression |
| 9005 distinct textures | Current-OFE enum in ordinary/debug output | Real serializer/readback; native consumer still pending |
| Twelve RAP elements | Numeric element ordering in ordinary/transformed writers | Actual cover-file readback |
| Unsafe/Unicode crop labels | Native-token-safe aliases with original-name provenance | Real parser/writer/repeat regressions; native reader acceptance pending |
| Missing provenance, mismatched counts | Explicit failure without false readiness | Real parser/staging regressions |
| Linked files and failed publication | Source preservation, visible attempt, normal retry | Dedicated security review and real writer tests |
| Archive/restore | Byte retention of prepared management, PMET and failed attempt | Canonical archive regression; environment browse/download still pending |

Malformed-state errors use existing caller/worker failure handling; optional
absence does not acquire a new corruption policy. No route, queue, NoDb locking,
scientific default or native limit changes are approved by this review.

## Generated artifact evidence and execution

Independent canonical focused command:

    wctl run-pytest tests/wepp/management/test_mofe_input_identity.py tests/wepp/soils/test_mofe_identity.py tests/nodb/mods/disturbed/test_pmetpara_prep.py tests/nodb/mods/test_rap_ts_cover_transform.py tests/nodb/test_wepp_multi_ofe_management_propagation.py --maxfail=1

Result at the pre-composition-fix snapshot: **39 passed**, two existing dependency
deprecation warnings. The primary agent subsequently reports **149 passed** across
management and Disturbed suites; final disposition must bind the corrected source.
Unit success does not close MIPA-IMP-01 without its discriminating readback.

Inspected [Rust candidate readback](rust_candidate_v1/readback.json), which binds
an isolated freshly built extension and records invalid-buffer/tiny-segment
rejection plus ordinary/equal/overlong-buffer output. The installed release is
not claimed refreshed. Rust changes preserve output precision and validate before
destination creation; map equal-boundary rejection covers the confirmed shared
failure class. Native model consumption remains unverified.

The actual-project fork/inventory establishes a supported heterogeneous clone.
Normal producer preparation and its final semantic receipt are being completed
by the primary agent; a fork receipt alone is not preparation acceptance. The
native PMET capacity, trustworthy observation, 9005 consumer and FC/HK ownership
dependencies remain open. No fresh native model outputs or user-facing reports
from repaired inputs are claimed.

## Verdict pending final readback

Local producer review: **hold** for MIPA-IMP-01. Unresolved source findings:
High 0, Medium 1, Low 0. The source may be corrected incrementally, but neither
the package nor unrestricted heterogeneous native correctness is approved.

Final readback must resolve the composition finding, bind tests and source hashes,
record the broad-suite result accurately, and retain actual-project/native and
environment limits. Deployment and affected-resource recovery remain separate.

## Final local-source disposition — 2026-11-02

**MIPA-IMP-01 resolved.** Validated provenance now travels on each plant scenario
through copying, renaming, pruning and synthesis. Serialization derives current
header keys from those scenarios; mixed prepared/unprepared sources retain only
the records they actually own, while every marked alias must have a valid record.
PMET identity distinguishes original mapping name, coefficient pair and serialized
native plant definition. Plant deduplication uses the same definition equivalence
as alias allocation, so description-only differences do not conflict and different
scientific definitions remain distinct. All safe names retained by the ordinary
fast path are reserved before allocating any generated alias.

Independent direct readback followed the first year's actual yearly/plant
references after composing two prepared source variants: OFE heights remained
`[0.49988, 0.123]`, and repeated PMET preparation was byte-identical. The first
exploratory version of this probe changed an unused plant and incorrectly expected
the first active crop to change; that assertion was a probe error, not a producer
failure. The corrected probe explicitly resolves the active crop before mutation.
QA independently replayed the description-only variant successfully after the
same-equivalence correction. Regression coverage now retains both variants.

Latest independent canonical command:

    wctl run-pytest tests/wepp/management/test_mofe_input_identity.py tests/nodb/mods/disturbed/test_pmetpara_prep.py tests/wepp/test_single_input_references.py tests/rq/test_project_rq_archive.py -k 'mofe_input_identity or pmet or references' --maxfail=1

Result: **45 passed, 54 deselected**, three existing deprecation warnings.
This includes all identity regressions, real Disturbed staged-file processing,
native contour/drainage reference regression coverage and canonical PMET
archive/restore byte retention. It supplements the earlier independent 39-test
soil/RAP/staging selection and the primary agent's wider test results.

Final reviewed source hashes:

| Source | SHA256 |
| --- | --- |
| `wepppy/wepp/management/pmetpara.py` | `6e5ed8973c92c356a2527eb06ba2f9bd697df97b3c77abe60ff3cc07ae1fad3f` |
| `wepppy/wepp/management/managements.py` | `c83275c7b2dd5331f991086158b3a2605a056c9431551d388128391872842664` |
| `wepppy/wepp/management/utils/multi_ofe.py` | `834787b7d53d778686f3aae834133072a3dfeab48ca225351c175a3c9e1dc8e4` |
| `wepppy/nodb/core/wepp.py` | `92f8cf62ac36ee9721404f55589827b23464d703398c567c80714da27c7207aa` |
| `wepppy/nodb/mods/disturbed/disturbed.py` | `e6e9d54d4c6880d22a102f1dc84aebad8f67ff2944ee634786356166cf25063e` |
| `wepppy/nodb/mods/rap/rap_ts.py` | `f7de49875d62a50355fcbb74b9c6c248e52de150dd013a61a1ade4474eda11be` |
| `wepppy/wepp/soils/utils/multi_ofe.py` | `3c4880820d4f70adfd86cd06ea4b897fe2396afdf77022610f92f0a2bbda2683` |
| `wepppy/wepp/soils/utils/wepp_soil_util.py` | `367e94103f75d8746f99fb5c440fe84059534d1efb50ec2d3431fcbfb76243ba` |
| `wepppyo3/wepp_interchange/src/mofe.rs` | `8606a1b99f3217d7d371e87d6256eb8826bc780719fdb0dd9af6684b3d9bcd19` |
| `wepppyo3/watershed_abstraction/src/lib.rs` | `3f5d6031a1038f3ea3c31622bfba1a3b407d750e183a1facb5b802d8405b96a0` |

The [actual-project producer receipt](actual_project_prepared_v1.json) reports
72 hillslopes, 235 OFEs, 24 PMET rows, agreeing deck counts, repeated PMET byte
identity and unchanged source files on the supported clone under UID 1000/GID
993. This reviewer inspected that receipt; it is not a reviewer-run model or
native acceptance. The receipt lacks executed-source hashes, so a retained,
versioned final candidate binding is still required for the stronger
exact-candidate environment claim. Preserve that original receipt when adding
later evidence.

Final **local producer-source correctness verdict: pass**. Unresolved reviewed
source findings: High 0, Medium 0, Low 0. The highest supported overall code claim
is **implemented and locally validated**, subject to the exact source hashes
above and the primary validation inventory. The full suite did not pass end to
end: the primary agent reported a published Disturbed-report freshness stop after
485 passes and is recording its disposition. This review does not waive that
check or claim it is green.

Release/package acceptance remains **HOLD** for final evidence binding, any
remaining broad-validation gate, normal environment browse/download evidence and
NATIVE-01/02/03 plus the selected 9005 consumer. Native execution, fresh corrected
outputs/reports, installed Rust release refresh, deployment and affected-project
recovery are not approved by this local-source verdict.

Residual API limitation: the existing parser resolves scenarios by name. Safe
duplicate native labels with distinct numeric scenarios and equal PMET pairs
remain byte-preserved when no graph rewrite is required. An ambiguous duplicate
label that requires alias rewriting still fails explicitly. Normal generators
produce unique names, checked uploads require uniqueness, and upload policy
excludes Disturbed; no additional supported production consumer requiring numeric
reference reconstruction was established. Do not describe this as exhaustive
support for arbitrary hand-authored duplicate-label graphs.

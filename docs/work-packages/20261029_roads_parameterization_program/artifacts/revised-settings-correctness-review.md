# Roads settings proposal: independent correctness review

## Metadata and authority

Reviewer: independent `settings_correctness` agent, 2026-11-03. Starting source
checkpoint: `6cf8dcad6`. Reviewed proposal:
`docs/schemas/roads-settings-contract.md`, proposed ADR-0135 and
`artifacts/revised-settings-layout-draft.html`. No production editor implementation
is reviewed or authorized. Explicit human specification/layout approval is absent.

Canonical authorities: Roads specification (API validation, defaults, attribute
mapping and required unrutted geometry), Roads preparation lifecycle (admission,
retention and archive/restore), output-scope contract (baseline isolation), NoDb
persistence/concurrency (authoritative hydration and atomic mutation), CSRF and
shared controller contracts. Contract-first ancestor and human gate remain required.

## User outcome and structural assessment

The five-field proposal enables ordinary users to edit existing fallbacks without
manual input files. Feature precedence stays intact; width footprint effects and
fill applicability are visible. Reset changes the draft and Save commits it; this
avoids unexpectedly changing uploaded geometry or mappings. The no-op Save decision
is explicitly client-only and preserves existing accepted API invalidation.

The selected structure uses existing routes, state and history rather than adding
queues, policy adoption or global overrides. Generated research soils are correctly
separate from production legacy templates. Study ranges are not calibrated ranges.
Source inspection confirms that the numeric keys exist in `Roads.set_params`,
`query_inputs` can render saved input state without model-result admission, and
execution manifests are lists with additive per-profile records.

## Valid-state and user-error policy

| State | Contract assessment | Implementation evidence required after approval |
| --- | --- | --- |
| Absent/never-used Roads | Baseline remains available; no read-time metadata writes | Real render and state-byte readback |
| Present empty/no upload | Authorized Save permitted; Prepare reports missing upload | Actual route/save/reload and unchanged baseline |
| Populated/current results | Save invalidates Roads only, retains visible history | Real lifecycle, report rejection, fresh native run |
| Legacy missing metadata/keys | Existing values and supported absent-key defaults retained | Reload/fork/restore without enrollment on read |
| Unsupported metadata | Explicit status; no guessed scientific policy | Real malformed/unknown metadata readback |
| Malformed present saved value | Explicit repair state separates malformed-present from absent legacy keys | Explicit error and deliberate complete Save recovery |
| Invalid request | Atomic rejection before retention/persistence | Null/bool/nonfinite/range/enums plus current receipt bytes |
| Readonly/unauthorized/CSRF | Existing server denial preserved | Real boundary rejection, no state/artifact change |
| Busy/late client response | Preserve draft and currentness contract | Concurrent requests and stale response suppression |
| Failed run | Partial artifacts inspectable, no current receipt | Actual failed native/output path and retry |
| Fork/archive/restore | Values, metadata and artifacts coherent | Canonical byte/permission roundtrip and legacy archive |

Invalid user input, readonly state and an occupied lifecycle guard are expected
errors with existing envelopes and useful recovery. Persistence, retention or
native failures are explicit exceptional outcomes; the proposal correctly avoids
claiming distributed rollback or re-admitting old outputs. Optional absence is not
corruption. Direct source reads reveal two previously accepted scalar coercions
that the proposal changes; these must be named in the intended delta (SC-02).

## Artifact chain and observability

Request, reloaded NoDb, visible preparation summary, execution record, emitted
native input, native output and scoped reports are all identified. Their successful
validation remains **pending**, because this is a preimplementation proposal.
Current controller-only studies cannot prove browser/RQ or archive parity.

The revised contract preserves the manifest list and defines per-record additive
configuration/segment provenance, actual source labels and input hashes. Its
`emitted_geometry` retains every ordered slope point, including transition points,
rather than collapsing each OFE into a nominal scalar. Missing/failed values remain
explicitly unavailable. Aggregate usage counts unique original segment identities
and separates unresolved conflicts rather than dropping multiple profiles.
Existing visible summary/manifest/history paths are suitable; no new hidden or
archive-excluded storage is proposed.

Required postapproval acceptance includes unmocked persistence/filesystem/restore
boundaries and actual browser/download evidence under service identities. No
artifact stage is waived. Highest supported claim now: structurally accepted proposal
with completed bounded scientific outcome citations; neither wired behavior nor workflow validation.

## Findings

| ID | Severity | Surface | Finding and required action | Status |
| --- | --- | --- | --- | --- |
| SC-01 | Medium | Execution provenance and usage | Define exact additive per-record schema, source/emitted applicability, missing values and aggregate counts. Preserve manifest list shape; current rows do not already carry all requested semantics. | Resolved in revised contract/ADR; independently rechecked |
| SC-02 | Medium | API compatibility and ADR delta | `float(True)` currently admits 1 for numeric fields; `traffic_default=null` stringifies to `none`. Proposal rejects them. Name this intentional validation delta and required regressions instead of claiming all API behavior unchanged. No change before human approval. | Resolved in revised contract/ADR; independently rechecked |
| SC-03 | Medium | Persisted malformed state | Define handling of present-invalid saved five-field values separately from supported absent legacy keys and unsupported metadata; no silent replacement. Specify deliberate complete Save repair and unrelated-state preservation. | Resolved in revised contract/ADR; independently rechecked |
| SC-04 | Low | Concurrency language | Existing serialization and stale-controller checks do not prevent a later valid browser Save replacing another user's saved five values. Clarify last accepted explicit Save semantics; do not imply cross-session merge/conflict detection without tokens. No automatic retry remains appropriate. | Resolved in revised contract/ADR; independently rechecked |
| SC-05 | Medium | Adjacent panel actions/draft ownership | Parent source review found mapping action submits fallback fields and passive refresh rewrites them. Explicitly isolate mapping-only versus five-setting payloads; dirty drafts block adjacent mutations; matching Save response owns hydration; Cancel rereads without mutation. | Resolved; independent source/delta recheck including pending Save actions |

## Verdict

**PASS for the revised structural contract proposal; no unresolved correctness
finding.** SC-01 through SC-05 are resolved and independently rechecked. The explicit
null/boolean validation delta and malformed-saved-state repair are proposed intended
behavior, not already implemented conformance. Source precedence, ordinary API
aliases/numeric strings, omitted fields and unrelated parameters remain preserved.

The completed scientific outcome citations have been checked against the final
independent scientific review. No pending-study condition remains for presenting
this proposal. This correctness review does not substitute for the separate
scientific review, explicit human approval or implementation permission. Production
workflow evidence remains a separate postapproval gate; material field/schema/
behavior revisions require re-review.

## Reviewed structural revision identities

- `docs/schemas/roads-settings-contract.md`: `a838760b703bc012f47e1db657a7de5248c19480384fc93273be7f4757f4863f`.
- `docs/adrs/ADR-0135-roads-settings-controls.md`: `e223b9ca19951a4a753ace0d869b43dd1916fd56a99aaf298ed0611be4f0f1a2`.
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/revised-settings-layout-draft.html`: `d2e51740f622629eb5cf2965abd02b4ad9eefc06ebc4eb5ddc1a53dd7cdde9f7`.

## Adjacent-action amendment review

Parent identified a concrete integration omission after the initial structural
review: `roads.js::applyAttributeMapping` currently merges
`readFallbackDefaultsFromForm()` into its request and uses
`renderAttributeMappingState()` on completion. Leaving this behavior intact would
save a settings draft through a different action or replace its values during a
passive response. The revised “Adjacent actions and draft ownership” section
correctly isolates payloads, blocks adjacent mutations while dirty, preserves local
drafts across passive responses and gives only matching Save success ownership of
hydration. Clean-state mapping still uses the existing API and workflow.

Cancel now explicitly discards then rereads authoritative state without mutation;
a failed reload cannot silently authorize execution. The required controller/browser
matrix includes payload separation, dirty action attempts, late responses, double
Save, failed Save and Cancel. These are contract obligations for postapproval
implementation, not tests claimed to have run against an editor that does not exist.
A final clarification makes Cancel/Reset disabled during pending Save, avoiding an
implied ability to roll back an already-submitted mutation. The wording is now present and SC-05 is resolved. The exact source finding and new
client behavior must remain in the parent contract-decision delta.

Adjacent-action revision identities (supersede earlier proposal hashes):

- `docs/schemas/roads-settings-contract.md`: `fb106ac84d37b74e10c25208f650dd6b944384f8d8388a90de37f2f5aaeb96e8`.
- `docs/adrs/ADR-0135-roads-settings-controls.md`: `6d67f688ad52da195c6276bef2892eac8ee47253eddc47ebf89f2c257c6316e2`.
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/revised-settings-layout-draft.html`: `5f33ec1f0b0b356b92b725474832334378dd33e5aaa2ffbfc4bcef2840f494bf`.

## Final evidence linkage and proposal verdict

The final contract, ADR and static layout now cite the completed 47-profile and
four-project studies and the independent `revised-sensitivity-science-review.md`.
Their stated width/fill/traffic contrasts match the retained reports. The 47-profile
count contains 40 production-template cases plus seven conditioned generated cases;
the latter retain their own baseline and are not policy adoption. Surface is an
existing supported choice without an isolated paired effect claim in this panel.

The proposal correctly distinguishes whole-strip area scaling, total versus density
responses, nonmonotonic traffic, study values versus validity bounds, and absence of
field calibration. It does not extend the profile lane's 47 strict EVENT passes to
the project lane. PASS EVENT particle support versus terminal non-EVENT sediment
is retained as a limit, not represented as complete particle/storage closure.

Focused recheck confirms the intended settings fields, metadata/per-record schema,
legacy and malformed-state rules, action isolation, explicit validation delta and
human gate remain as structurally reviewed. Only evidence/status/help-text integration
is newly accepted here. **Final proposal correctness verdict: PASS, no unresolved
correctness findings and no remaining pending-study citation condition.** This is a
reviewable proposed checkpoint, not an accepted implementation ancestor. Human
specification/layout approval and postapproval browser/persistence/native/report,
readonly, reset, fork and archive/restore acceptance remain open.

Final proposal identities (supersede all prior review hashes):

- `docs/schemas/roads-settings-contract.md`: `7bd11c84814707480656f7b26ab9abd5b63962bd7c2836424a069ffb07a291ca`.
- `docs/adrs/ADR-0135-roads-settings-controls.md`: `1693bcac4ff41f8c75bcfb8a7761fe429dbe5e69bf39b040276a75e484511bc4`.
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/revised-settings-layout-draft.html`: `e6acb4990e7c79adae37560a8db3d8de11bd1f46cc1a423440a7887ea048b910`.
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/revised-sensitivity-science-review.md`: `2af21faeb1abffc6816ad82c4aa5a0fcecadfc90d4222ccb815cc65e8400f56f`.

## Final proposal checkpoint metadata check

Independently inspected `20261103_revised_settings_contract_decision.md`, ledger
v34, and the current revised sections of package/tracker/ExecPlan. **PASS for the
proposal-only checkpoint.** The decision names the starting revision, separate
conformance commits, exact prospective UI/API/provenance/draft-ownership delta,
applicable canonical authorities, compatibility plan and high security triage.
It links completed independent reviews while explicitly withholding human approval,
production settings wiring, deployment and full-program completion.

All eight ledger-v34 evidence hashes and its predecessor hash match current files.
Final contract/ADR/layout/science-review identities remain unchanged from the final
proposal review above. The project report introduction now links the completed
joint scientific review. Study counts distinguish 47 isolated profiles, 140 project
profiles and four watershed calls; strict EVENT audit scope is not inflated to the
project lane. No reserved-material or default-adoption claim is introduced.

The repository sanity gate is accurately reported as active at this check, including
separate late calendar-guard validation. This review does not turn an active gate
into a pass. Its final outcome must be retained before a final validation claim.
A proposal commit is not the accepted implementation ancestor: explicit approval of
both specification and layout, ratified canonical checkpoint, and later actual
browser/persistence/native/report workflow evidence remain required.

Checkpoint identity at this review:
`20261103_revised_settings_contract_decision.md` SHA256 `54e376de5c6cf56e81551d3fcef334a3624d510f746d4545a63c64bda4817d0f`.

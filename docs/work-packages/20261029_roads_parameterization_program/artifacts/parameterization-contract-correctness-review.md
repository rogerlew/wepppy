# Roads parameterization contract correctness/security review

Reviewer: independent `project_contract_review` agent, 2026-11-03.
Scope: proposed project contract and repository baseline contract, compared with
current Roads NoDb/route/lifecycle implementation and shared NoDb rules. This is a
pre-implementation contract review, not certification of production wiring.

## Initial disposition (superseded by final readback)

**Changes required** before approval. No production source was modified. The single
NoDb authority, retained template text, role-wide override ordering and explicit
approval boundary are sound in principle. The following gaps need exact decisions.

| ID | Priority | Finding and required correction |
| --- | --- | --- |
| PC-01 | Medium | Saved baseline validation must require the exact supported asset set, reject missing/extra/path aliases, verify each text hash and recompute baseline identity. Archived/restored NoDb is an input boundary; server-owned API fields alone do not validate it. Apply format/schema validation before materialization, never use untrusted paths. |
| PC-02 | Medium | Save promises every resolved value is valid but permits no-upload and absent-role states. Define validation over every selectable retained template and traffic adjustment combination, with emitted native representability checked again during execution. Otherwise a valid save can become numerically invalid simply by changing surface/traffic or adding a segment. |
| PC-03 | Medium | Legacy first Save is said to bind default entries, conflicting with a first Save containing custom entries. Specify atomic binding of baseline plus the submitted validated overrides; Prepare with no prior configuration binds all-default entries. |
| PC-04 | Medium | Legacy prepared/unbound direct Run is unspecified. Native soil/management assembly currently occurs during Run. Require a fresh Prepare for new unbound legacy execution, or explicitly define atomic Run binding plus identity update. Preserve old completed-result inspection. Record any intentional compatibility delta and its user-facing recovery. |
| PC-05 | Medium | Describe native artifact timing accurately: current Prepare emits geometry/context; Run materializes soil/management. The view must not fabricate prepared native values after geometry-only preparation. Show unavailable until actual input readback and distinguish failed/completed attempts. |
| PC-06 | Medium | Require display-safe text rendering/escaping for persisted source names, diagnostics and restored content; ensure optional absent Roads inspection does not create or write a controller. Name the valid absent/disabled outcome rather than relying solely on the current query handler, which requires an initialized controller. |

## Evidence inspected

- `wepppy/nodb/mods/roads/roads.py`: `_default_params`, `set_params`,
  `_require_prepare_state_current`, `prepare_segments`, `run_roads_wepp`, soil
  writers and template selection. `set_params` currently retains artifacts and
  saves `_roads_params`; soil writers are consumed in native execution branches.
- `wepppy/weppcloud/routes/nodb_api/roads_bp.py`: `_sync_roads_enabled_state`,
  POST `tasks/roads/set_params`, POST `api/roads/config`, existing query handlers.
  Existing response envelopes and old parameter keys must remain compatible.
- `wepppy/wepp/interchange/_roads_lifecycle.py`: `mutation`, `inspection`,
  `retain`, `restore_operation`; catalog/operation ownership and non-current
  retained outputs must remain authoritative.
- `docs/schemas/nodb-persistence-concurrency-contract.md` and
  `docs/schemas/roads-preparation-lifecycle-contract.md`: fresh locked state,
  atomic NoDb persistence, nonblocking lifecycle order, historical/current split.

No claim is made that float representability establishes physical safety or native
success for all positive inputs. The proposed explicit native-failure behavior is
appropriate, with bounded studies kept separate from validated field ranges.

## Final readback

**PASS for the revised proposal; no unresolved correctness findings.** PC-01 through
PC-06 were corrected and independently read back. The project contract now requires
fixed asset allowlists and complete hash/id/format validation; all selectable
baseline/traffic combinations are validated even without uploaded segments; first
Save binds submitted custom entries; unbound legacy execution requires Prepare;
actual native-value visibility begins at input assembly during Run; persisted
content is escaped and absent/disabled inspection performs no hidden writes.

Follow-up exactness corrections also passed: repair accepts only boolean true with
all 12 entries in default mode, cannot rebase a valid bound/unbound project, and
retains invalid state before replacement. Template scenario3 overrides include
upstream/remainder template Forest while excluding independent source landuse.
Unsupported resolvers remain inspectable without evaluation and cannot be silently
downgraded. The ADR and lifecycle amendment explicitly record the intentional
Prepare-before-new-Run compatibility delta while preserving existing completed
result viewing.

### Independent prototype artifact audit

Reviewed `parameterization_binding_prototype.py` and the receipt, then independently
read all 168 cases and recomputed comparisons/hashes for **336 soil/management file
pairs**. Every repository-generated file equals its retained-text-generated peer.
Raw-result, script, Roads-source and matrix-reader hashes match the receipt. The
prototype meaningfully demonstrates default source-content retention and artifact
parity across its matrix. It does not exercise actual NoDb locking/persistence,
production routing, native execution or canonical fork/archive/restore; those
limits are accurately stated and remain required after implementation.

### Reviewed identities

- `docs/schemas/roads-settings-contract.md`: `8c849bbc6ee34926caa505d78c6c076407a440cee75fc64ad659107110d18ed7`
- `docs/schemas/roads-parameterization-baseline-contract.md`: `d2a73ccd22884b1f9040d259c54c374589e2576201c1ca1ebade9b5220e37aea`
- `docs/adrs/ADR-0135-roads-settings-controls.md`: `c24df1c900787ff7f21cb76805915d2f86c28da40c1f954b80a10ef94f62c42e`
- `docs/schemas/roads-preparation-lifecycle-contract.md`: `9a16c0545e9138565cb7906ee141be83121ac1f7c1aed3dd737cd749eb4ca284`
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization-binding-results.json`: `b7c4196d28d7b4e1f285a5b4421b092de2844eba0c8df506948d4ac991ffed46`
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization_binding_prototype.py`: `a0ba84dcf8b14cc3b48f593d936f211e07197d247cb1e4efaf7f50badbbaf7bb`

No production implementation approval is granted by this review. Explicit human
specification/layout approval, the accepted contract-first ancestor and future
workflow validation remain required. This review accepts only the exact proposal
and bounded prototype evidence above, not all possible runtime parameter values.

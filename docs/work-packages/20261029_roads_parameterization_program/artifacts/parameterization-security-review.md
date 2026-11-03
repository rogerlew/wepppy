# Roads parameterization security and noninterference review

Date: 2026-11-03. Scope: proposed dedicated view and embedded project baseline in
`docs/schemas/roads-settings-contract.md` and
`docs/schemas/roads-parameterization-baseline-contract.md`. No production wiring
exists. This is a preimplementation contract review, not operational certification.

Status: **PASS for the revised preimplementation contract; S1–S4 resolved**.
The findings below preserve the original review record; see the disposition section.

## Findings

### S1 — medium: validate retained content before materialization/native use

The proposed schema calls paths allowlisted and rejects direct client asset writes,
but stored/restored text is checked only by its self-declared hash. Such a hash
establishes integrity, not trust: altered text plus a matching altered hash still
passes. The contract needs a resolver-version-specific exact asset-name set,
complete membership/count rules, bounded UTF-8 text sizes, native file-version and
structural parse validation before use. A materializer must write only validated
names under its owned run scratch/output root and reject symlink escape or unsafe
preexisting targets; never resolve an arbitrary persisted path. Retained older
valid baseline contents must remain usable despite current repository drift.

Acceptance: valid saved baseline after repository drift succeeds unchanged;
unknown/absolute/traversing asset names, missing/extra files, oversized/malformed
records and symlinked escape targets fail before native execution or out-of-root
writes. Matching a supplied hash must not bypass these checks.

### S2 — medium: make dynamic display escaping explicit

The new page displays template/source names, mixed-segment membership, diagnostics
and optional artifact content. The contract does not explicitly state how these
persisted or uploaded strings are rendered. Require text/escaped HTML rendering,
safe JSON serialization in page bootstrap, and no interpolation of values into
executable markup or script. Diagnostic messages must not expose credentials or
arbitrary server paths. Browser tests should include hostile segment names and
restored malformed diagnostics while preserving useful readable descriptions.

### S3 — medium: absent-state behavior is not executable as specified

The valid-state list includes absent Roads, and GET is required to avoid writes.
Current reused query routes call `_sync_roads_enabled_state`, which raises when no
Roads controller exists (`roads_bp.py:57`). Define the dedicated GET/query behavior
for absent/disabled Roads and the explicit authorized initialization path for
Save/Prepare. A public read cannot create `roads.nodb` merely to display defaults;
an authorized fresh enabled project must still have a path to its first Save.
Existing run authorization, module enablement and readonly restrictions remain.

Acceptance: absent enabled mutable, absent readonly, disabled and legacy states
have clear expected responses; GET does not mutate, and intended first-use actions
work without bypassing module/access restrictions.

### S4 — medium: repair must not become a hidden adoption operation

The proposed request allows optional `repair:true` and specifies that repair binds
repository defaults/removes overrides. It does not restrict this action to an
invalid current parameterization. Without that condition, repair can rebase a
valid bound project despite the explicit no-adoption v1 contract. Require server
validation against refreshed state: repair is valid only for a present invalid
record, never a bound valid or absent legacy record. Preserve the full invalid
record as diagnostic evidence before replacement and fail explicitly if retention
fails. Save with `repair:false` should either be explicitly rejected or defined;
do not coerce arbitrary truthy values.

Acceptance: repair on valid bound or absent state rejects before invalidation;
explicit repair of an invalid record retains evidence and binds the reviewed
replacement under existing permissions/locks. Rejected and failed repairs cannot
silently replace current values or re-enable old results.

## Existing sound constraints

Single Roads-owned persisted state avoids a second mutable parameter store.
Clients cannot select source paths/text or resolver versions. Positive, finite,
representable numeric inputs reject native zero/sentinel ambiguity. Override scope
is limited to template-owned roles and preserves baseline WEPP/shared Disturbed
state. The proposal preserves authorization, CSRF, readonly state, canonical locks,
fail-closed invalidation and explicit native failure. Artifact browsing remains
separate from current-result eligibility. Explicit reset versus adoption, no
read-time migration and full retained baseline text support project reproducibility.

## Required implementation evidence

After the independent contract gate and human approval, exercise real save/reload,
concurrency, native materialization and archive restoration under canonical service
identities/mounts. Test valid and hostile cases at the actual boundary; mocks and
static layout previews cannot prove those behaviors. No deployment or runtime
security approval follows from this review.

## Disposition after contract amendment

- S1 resolved: saved schema now requires all 18 fixed resolver-v1 names, recomputed
  identity/hashes, UTF-8 without NUL, 256 KiB per asset/1 MiB total, owned soil and
  management structure validation, fresh contained materialization and symlink
  rejection. It explicitly distinguishes integrity from trust and preserves bound
  projects across repository drift. Current source text totals 167,705 bytes.
- S2 resolved: view contract requires escaped text for source/segment/diagnostic
  data and established safe JSON embedding, prohibiting unsafe HTML/script
  interpolation. Shared error contracts continue to govern safe diagnostics.
- S3 resolved: dedicated GET/query is nonmutating for absent/disabled Roads, with
  an existing enablement-workflow link and explicit authorized Save/Prepare
  initialization for enabled absent state. Readonly and module checks remain.
- S4 resolved: repair is rejected on valid bound or unbound state and is confined
  to explicit invalid-state recovery with retained evidence and reviewed
  consequence. It cannot become reset-to-latest or implicit adoption.

Unsupported resolver versions remain explicit errors for execution while ordinary
authorized historical artifact inspection remains available. The contract does not
require current repository hash equality for a structurally valid retained baseline.
No added security rule makes normal legacy read access perform a mutation.

Final production acceptance still requires direct boundary tests. This review
accepts a contract design and does not certify implementation, deployment, native
parser robustness or archive restoration under production identities.

## Final reviewed checkpoint

Reread completed after strict repair-boolean/default-entry validation and explicit
unsupported-resolver inspection rules were added. Repair is boolean true only,
requires all 12 default entries, rejects bound-valid and absent state, and cannot
coerce or silently discard custom entries. Unsupported rules are never evaluated;
normal Save/Run is blocked while authorized historical inspection remains available.
Explicit repair retains the old record and reviews the reset consequence.

No unresolved security/noninterference findings remain in this proposal scope.
Hashes bind the reviewed bytes; later material amendments require rereview.

| Reviewed file | SHA256 |
| --- | --- |
| `docs/schemas/roads-settings-contract.md` | `8c849bbc6ee34926caa505d78c6c076407a440cee75fc64ad659107110d18ed7` |
| `docs/schemas/roads-parameterization-baseline-contract.md` | `d2a73ccd22884b1f9040d259c54c374589e2576201c1ca1ebade9b5220e37aea` |
| `docs/adrs/ADR-0135-roads-settings-controls.md` | `c24df1c900787ff7f21cb76805915d2f86c28da40c1f954b80a10ef94f62c42e` |

Final source-validation amendment reread: raw numeric fields are validated before
permissive parser normalization, role fragment markers are exact, and baseline
parsing disables coefficient recomputation. This strengthens S1 without changing
valid retained-baseline semantics; final PASS and the updated settings hash apply.

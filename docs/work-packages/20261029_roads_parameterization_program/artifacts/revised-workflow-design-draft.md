# Roads settings workflow design draft

Status: design input, not an approved specification, 2026-11-03. Sensitivity results
and independent reviews remain prerequisites for a final proposal. No production
view, persistence or default adoption is implemented by this document.

## Existing behavior and proposed scope

The current Roads panel exposes upload, design/surface/traffic attribute mapping,
surface and traffic fallbacks, preparation and execution. `Roads.set_params` also
accepts width, fill length, fill slope, texture and profile-fragment fallbacks;
those numeric settings are not currently exposed in the panel. Production soil
assembly uses legacy templates. The conditioned generated-soil study is a separate
research lane and must not be advertised as an installed generated-soil policy.

Reuse the Roads `control_shell`, `select_field`, numeric field and `button_row`
patterns, normal summary/status/Details panels, and readonly behavior. The Disturbed
editor provides familiar Save/Reset actions, but neither its CSV grid nor a new
standalone settings dashboard is appropriate here. Place a **Roads settings**
fieldset after Attribute Mapping and before Prepare/Run. Preserve the uploaded
filename, map preview and existing commands. Integrate existing surface/traffic
fallbacks into this one settings editor rather than duplicate them in two forms.

The useful first increment exposes existing fallback choices, with source and
applicability feedback. It does not add a silent project override of mapped feature
values. A project-wide override mode would be a separate normative change requiring
explicit semantics, sensitivity and review. Do not imply a fallback changes every
segment: present an actual resolved usage summary after a completed run, and label it
as applying to that execution. Before a current completed run, say “Run Roads to see actual
settings use”; do not invent affected counts.

## Candidate fields for the concrete proposal

| UI label / saved key | Existing value and validation | Applicability and precedence | Evidence needed before final exposure |
| --- | --- | --- | --- |
| Surface fallback / `surface_default` | `gravel`; gravel or paved | Road soil; recognized mapped/legacy feature surface wins | Explicit surface/traffic aliases by design and native emitted rows |
| Traffic fallback / `traffic_default` | `low`; high, low or none | Road management/soil; recognized mapped/legacy traffic wins | Traffic paired runs, event/annual effects and management consumer readback |
| Road width fallback (m) / `road_width_m_default` | 4; finite 0.3–100 inclusive | Feature width wins; profile transformation differs for unrutted | Requested/emitted geometry, actual modeled area, width contrasts |
| Fill length fallback (m) / `fill_length_default_m` | 30; finite 0.3–100 inclusive | Outslope rutted only; feature fill length wins; no inslope fill | Paired contrasts and width interaction; distinguish unrutted required geometry |
| Fill slope fallback (%) / `fill_slope_default_pct` | 10; finite 0.1–150 inclusive; helper preserves this interval | Outslope rutted only; feature fill slope wins | Bounded fill-slope contrast before exposing editable control |
| Soil texture fallback / `soil_texture_default` | loam; clay, silt, sand, loam | Template classification, not measured generated-soil composition | Inventory consumer mapping and honest template labeling; may remain read-only in first proposal |
| Profile rock fragments (%) / `rfg_pct_default` | 20; finite 0–100 inclusive | Existing soil profile fraction; not surface armor | Native basis/role verification and sensitivity needed; do not expose merely because it is numeric |

Existing validity bounds are parser/model constraints, not studied or calibrated
ranges. Final labels must report exact studied values from the accepted sensitivity
receipt separately. No field-calibrated range has been established by this program.
Do not expose Ki/Kr, frost toggles, surface armor, a global buffer-length override,
trace iteration limits or generated-policy selection in this first editor.
Buffers are trace-derived for additive designs; unrutted explicit geometry has its
own required-field contract and cannot silently consume new defaults.

## Edit, save, reset and reload

View mode shows saved effective fallbacks, Default/Custom status relative to the
pinned baseline, applicable designs and available provenance. **Edit settings**
opens an inline draft. **Save settings** sends one complete allowlisted settings
object. **Cancel** discards only the draft. **Reset to defaults** fills the draft
with the baseline values and marks it unsaved; Save is the explicit committing
operation. Reset must not unexpectedly discard the uploaded map or attribute
mapping. If mapping is integrated into the same form, its reset scope must be
stated separately rather than silently cleared.

Save validates the entire request before mutation, including finite numbers,
enums, unknown keys, current run authorization and existing operation guard.
A field error keeps the draft, focuses the first invalid field and leaves saved
state/current outputs unchanged. Preserve the normal server error envelope and
CSRF helpers. A busy response retains the draft and tells the user to retry after
the existing Roads operation. Successful Save reloads authoritative saved values
and shows “Settings saved. Prepare and run Roads to generate results.”

Saving a model-affecting change invokes existing Roads lifecycle invalidation and
history retention under the existing guards. Old reports cannot remain current;
baseline reports remain unchanged. Do not add a new job queue, generation identity
or background notification system. A settings editor cannot certify a fresh run.
Final acceptance reads new prepared inputs and completed native/report artifacts.

## Versioning, provenance and compatibility

The final canonical specification must name an immutable baseline identifier and
an additive settings schema version. These record reproducible values and meanings;
they are not user-facing preparation versions or segment identities. Existing
projects retain their saved values and template policy. Missing new metadata is
legacy provenance, not permission to rewrite saved values or adopt a generated
policy. Any adoption action must be explicit and reviewed; no adoption control is
included in this draft.

Capture saved values, baseline identity, source/fallback status and emitted values
in visible run artifacts, including aliases, rejected/fallback feature values and
clipped geometry. Link the prepared/execution provenance from normal Details or
file browsing. Fork copies selections and lineage; restore restores a coherent
settings/input/result state under the canonical archive and Roads lifecycle locks.
No filename match or saved flag alone establishes current-result eligibility.

## Required state and boundary evidence

| State | Required observable behavior |
| --- | --- |
| Roads absent / never used | Normal baseline remains usable; settings show defaults without creating hidden mutations |
| Present but empty / no upload | Editing permitted for authorized users; Prepare explains missing upload; no fabricated results |
| Populated, prepared or completed | Save/reset-save invalidates Roads current results and retains history; next preparation uses saved values |
| Supported legacy settings | Preserve current values; disclose missing provenance; no implicit policy/default adoption |
| Invalid request or malformed saved state | Invalid request fails atomically; saved corruption is explicit, not silently replaced by defaults |
| Readonly / unauthorized | Values inspectable only within normal access; edit/save/reset unavailable and server mutation denied |
| Concurrent run or stale response | Existing busy contract; late response cannot revive invalid results or overwrite a newer draft |
| Failed run / partial artifacts | Error visible, diagnostics inspectable, no current receipt; retry uses saved inputs |
| Fork / archive restore | Settings and provenance retained; coherent restored outputs only, with legacy limitations disclosed |

After human approval, validate real browser request -> saved reload -> preparation
-> emitted native inputs -> native execution -> fresh Roads reports, plus invalid,
readonly, reset, reload, fork and restore paths. Use production-equivalent service
identities, groups, mounts, umask and orchestration. Existing controller-only
studies are useful but cannot satisfy these boundaries. Preserve baseline byte
manifests and inspect actual role inputs/outputs, not only response codes.

## Review and approval status

The companion `revised-settings-layout-draft.html` is a static illustration of
placement and language. Its values are existing defaults, not sensitivity results.
The parent agent must reconcile final control selection and bounds with the
inventory/study, promote the exact normative contract, obtain independent reviews,
and present the concrete specification/layout for explicit human approval under
“End-user workflow and closure” in the adjudication contract. Approval is absent.

Review refinement: the proposed canonical contract now owns exact per-row manifest
provenance, the five-field boolean/null validation delta, explicit malformed saved
state repair, and last-accepted-write concurrency semantics. The static draft includes
clearly illustrative state examples and a calibration limitation for all settings.

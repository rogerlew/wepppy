# Mutation request payload contract

Status: MRS-01 accepted contract, 2026-10-30; local implementation evidence in the MRS-01 work package.
Operator authorizes rejecting malformed requests before side effects while
preserving intentional empty/default requests. Checkpoint commit authority granted 2026-10-30. This contract governs repository-owned Flask and rq-engine mutation
and submission request parsing, including indirect webhook and upload adapters.
It does not change authentication, CSRF, scientific defaults, queues or artifacts.

## Transport acceptance

Select the decoder from the media type, case-insensitively, ignoring media-type
parameters for selection. Preserve framework JSON decoding of supported Unicode
encodings; invalid encoding is a client error. JSON text uses the existing decoder,
not a new duplicate-key parser. JSON duplicate keys retain decoder last-key-wins
compatibility; conflicting *distinct aliases* remain subject to field validation.
Reject non-finite JSON numeric values before mutation, using the decoder's existing
hooks or a structural validation pass, without coercing ordinary numeric fields.

| Request | Result before domain validation | Rationale |
| --- | --- | --- |
| Genuinely zero body bytes, including no Content-Length | Empty payload where omission is supported | Existing body-optional operations run deliberate defaults |
| JSON `{}` | Empty object; no form fallback | Deliberate defaults are distinct from failed decoding |
| JSON object | Object; preserve raw structure for validation and existing domain adapters | Arrays nested inside an object are data, not scalar flags |
| Whitespace-only JSON, truncated JSON, invalid encoding | HTTP 400 `invalid_request` | Supplied bytes cannot become an absent request |
| JSON null, scalar or top-level array | HTTP 400 `invalid_request` on object routes | Falsy JSON is not absence |
| `application/json` or `application/*+json` | JSON decoder; never form fallback | Flask already recognizes structured JSON media types |
| URL-encoded form, including zero-byte form | Form decoder; preserve repeated fields | Existing browser and legacy form callers remain supported |
| Multipart form | Owning bounded upload/form decoder | Do not buffer uploads through the JSON path |
| Missing or empty Content-Type, nonempty body | Strict JSON compatibility decoding; no form guessing | rq-engine historically accepts headerless JSON; malformed bytes must fail |
| Unsupported media type, nonempty body | HTTP 400 `invalid_request` | No new global 415 convention; body cannot be ignored into defaults |

Zero-byte multipart with a declared boundary is incomplete multipart, not a valid
empty form. An empty multipart form requires a complete closing boundary. Invalid
or missing boundaries, truncated parts and incomplete termination fail before
promotion or mutation. Existing upload limits and 413 responses remain authoritative.
Determine absence from actual stream/body completion, never Content-Length alone.
Do not consume a stream twice. Preserve cached decoded data for later consumers.
Infrastructure errors, disconnects and cancellation must propagate through their
operational boundary and cleanup; they are never converted to `{}` or successful
submissions. Catch only known decoder/validation exceptions as malformed input.

The explicit structural exception is Omni scenario-list submission: its supported
top-level JSON list remains a list and is validated as scenario records before
mutation. Existing Flask Disturbed/Geneva CSV list editors retain their top-level list
contracts. Recorder events retain an object envelope with a nested `events` list;
this is not a top-level array exception. Form-only and JSON-only routes retain their
existing supported transports; the table does not add transports to them. Raw
file, ZIP and specialized structured API bodies retain their owning schemas.
Read-only lookup/polling parsing is outside this mutation repair. The enabled
Flask test-support create-run endpoint is included because it creates project
state; its enablement/auth policy remains unchanged.

## Scalar flags, omissions and aliases

Only declared scalar flags are boolean-normalized. Accept native booleans, numeric
0/1 (including 0.0/1.0), and case-insensitive legacy string tokens `true/false`,
`1/0`, `yes/no`, `on/off` after existing whitespace trimming. Explicit false/zero
must survive. Other numbers and unrecognized nonblank strings are invalid.
JSON lists and objects supplied as scalar flags are invalid even when empty or
single-element. Validate their raw shape before existing normalization can collapse
a list. Do not recursively coerce flag containers.
Ordinary numeric/string fields and legitimate nested objects/multiselects retain
their own normalization contracts, including existing nonflag singleton-list
normalization and trim-disabled text. Keep raw-list adapters for Omni/RAP and
other legitimate collection consumers; do not change all nonflag shapes as a
side effect of strict scalar validation.

Missing fields retain each operation's existing default or required-field error.
Null and blank are distinct domain sentinels, not malformed transport. The shared
normalizer preserves them for the following domain validation instead of converting
them to a universal boolean/default:

| Domain | Null / blank semantics |
| --- | --- |
| RHEM `clean`, `prep`, `run` and `*_hillslopes` aliases | Null defers to non-null alias then enabled default; blank retains false/skip semantics |
| WEPP routine checkboxes and `delete_after_interchange` | Null/blank retain sparse no-override behavior |
| WEPP clipping/export flags, DSS excludes | Null/blank retain false behavior; omission retains current/default state |
| Flask project public/readonly/TTL/enabled and WEPP state setters | Null/blank rejected; preserve required-state checks |
| Flask bootstrap `disabled` | Omission defaults true; supplied null/blank false |
| Flask soils `ksflag` | Null rejected; legacy blank disables (false) |
| Flask climate adjust/wind/quality-guard and WATAR wind setters | Null rejected; preserve legacy blank sentinel without treating it as true |
| Landuse burn aliases | Null canonical defers to alias; blank canonical is false |
| Watershed declared flags; Omni optional output flags | Null/blank mean unchanged / no override |
| RAP `force_refresh` | Null omitted; blank false |
| Polaris flags | Null uses stored/default state; blank rejected; legacy `y/n` additionally accepted here only |
| RUSLE `force_polaris_refresh` | Null defaults false; blank rejected |
| Geneva `force_rebuild` / `rebuild` | Supplied null/blank rejected |
| Batch run_directives keys present in the existing batch directive mapping | Omission preserves existing directive; supplied null/blank rejected; unknown keys and known TaskEnum members absent from that mapping retain ignore behavior |
| Soil cache-clear, OpenET refresh, SWAT print, fork undisturbify/skip-output, landuse replace, migration create_archive, run-sync flags | Null/blank false; omission retains existing default (including run-sync migrations enabled) |

These explicit blank/null exceptions preserve legacy setter outcomes without
allowing arbitrary nonblank text or containers to enable actions. A later cleanup
of stored sentinel types needs its own compatibility decision.

This sentinel policy does not authorize new field requirements or changing a
scientific/default value. Narrower existing field rules remain in force: fork's
`skip_omni_scenarios_contrasts` requires a native boolean for JSON, accepts its
existing form boolean tokens, and retains its own omission policy. Geneva
configuration boolean fields retain native-only validation and reject string
booleans under `wepppy/nodb/mods/geneva/specification.md` section 7; generic token
support does not widen strict configuration schemas.

For repeated form scalar flags, accept repetitions only when each supplied value
is valid and all normalize to the same semantic value. Reject conflicting values;
no arbitrary first/last-value choice. Preserve ordinary repeated fields and
multiselects. An existing hidden-input/checkbox pair may be exempted only by an
explicit field-specific contract with caller evidence before implementation.
Canonical/legacy boolean aliases may both be supplied only if their effective
values agree. Null defer semantics above are evaluated before comparing RHEM
aliases. In particular, apply this rule to RHEM stage aliases and landuse
`checkbox_burn_shrubs`/`burn_shrubs`, `checkbox_burn_grass`/`burn_grass`.

## Bounded numeric validation

This repair changes silent invalid-to-default handling only for the named numeric
consumers below. Preserve existing finite numeric conversions, including existing
integer conversion/truncation and nonflag collection selection; do not introduce
a new integrality policy or scientific range. Reject malformed nonempty numeric
text and non-finite values, including form strings such as `NaN`/`Infinity`, before
mutation. A boolean is not a supplied numeric override for WEPP clipping/saturation
or watershed integer options that already exclude booleans; reject it rather than
silently ignoring it. Existing domain validators remain additive.

| Fields | Missing/null/blank | Other supplied values |
| --- | --- | --- |
| WEPP clip depths, initial_sat and clipping length aliases | No override; preserve existing empty-collection/first-nonempty selection | Existing finite int/float conversion; invalid selected value rejects |
| Watershed clipping length and three MOFE numeric options | No override; preserve existing first-item collection selection | Existing finite conversion; invalid selected value rejects |
| DSS export mode | No mode override | Existing conversion; result must be existing mode 1 or 2 |
| DSS excluded orders/channel ID lists | Preserve empty list, omitted/null behavior and skipping null/blank entries | Preserve comma/list syntax and deduplication; malformed nonblank entries reject; existing excluded-order domain is 1–5 |
| Soil build initial_sat/sol_ver | Preserve existing required/default/clearing policy; no new required field | Existing validation must finish before source promotion |
| Ash mode 1 ini_black_depth/ini_white_depth; mode 0 ini_black_load/ini_white_load/field_black_bulkdensity/field_white_bulkdensity; fire_date | Preserve mode-specific required fields and null/omitted date behavior | Numeric inputs must be finite; supplied date must pass existing YearlessDate parsing before settings or uploads |
| WATAR low_/mod_/high_ fields for configured contaminant keys, plus reservoir_capacity/reservoir_storage | Omission preserves stored values; explicit nonnumeric/null/blank values reject | Existing float conversion, including zero; finite supplied values only, with no new scientific ranges; unrelated form keys remain ignored |
| Agent chat ttl_seconds | Omission/null/exact empty string/native numeric zero/false retain the existing 1800-second default; true retains 1 second | Scalar finite integer conversion retained; containers and whitespace-only text reject; selected nonpositive values reject before spawn/publish because Redis cannot accept that TTL |

For WEPP clipping length, preserve
[the exact numeric alias precedence](../ui-docs/contracts/wepp-hillslope-clipping-contract.md#user-controls):
`hillslope_clip_length` wins unless its extracted value is None/all-empty; scalar
blank does not fall through to `clip_hillslope_length`. This numeric precedence is
separate from boolean-alias conflict rejection. Previously persisted invalid length
and finite zero/negative values retain the existing asynchronous preparation failure
policy; newly supplied malformed/non-finite values fail synchronously before mutation.

The separately ratified `kslast` omission/clearing and first-nonempty contract is
unchanged. State-dependent mode/capability checks still run under their owning
admission rules. This bounded list does not authorize generic scientific-range
validation across every numeric field.

## Errors and side-effect ordering

Use a narrow request-validation exception and HTTP 400 canonical JSON envelope:
`{"error":{"code":"invalid_request","message":"Invalid request payload."}}`.
Optional details may identify an allowlisted field and validation reason; do not
echo supplied values, bodies, uploads, paths, secrets or tracebacks. Existing
specific field/upload/capability errors retain their codes and status conventions.
Local broad catches, decorators and framework handlers must preserve this mapping;
HTML, 500, success and default execution are not valid translations.

Existing authentication, authorization, CSRF and config-access checks retain their
precedence. Existing request lifecycle locking remains an allowed operational
effect; do not move parsing outside that authorized boundary. Finish transport and supplied scalar/structural validation before eager
controller creation, NoDir recovery, controller persistence, clearing completion
timestamps, replacing receipts/hints, callback reservation, source promotion,
file deletion, enqueue or external execution. Temporary transport buffering,
request logging and rate accounting are allowed; temporary resources must close
on rejection, disconnect and cancellation.

Read-only domain validation may follow admission when it requires admitted state.
[WAM-01](wepp-run-input-contract.md#admission-before-proposed-input-mutation-wam-01)
leases, active-job error precedence, prior-work reconciliation and no-prep prepared
files remain authoritative. Active-job rejection may still precede domain payload
errors; transport failure cannot fall through to input application. Validate all
supplied fields in a bounded multi-field update before saving any of those fields.
This includes confirmed soil `sol_ver`, landuse mode/mapping/burn flags, Geneva
config fields and watershed supplied numeric options; invalid supplied values must
not be silently discarded into default execution. Preserve valid omission, numeric
ranges and scientific formulas. Specifically, reject invalid supplied WEPP
`clip_soils_depth`, `clip_soils_minimum_depth`, `initial_sat`,
`hillslope_clip_length`/`clip_hillslope_length`; watershed `clip_hillslope_length`,
`mofe_target_length`, `mofe_buffer_length`, `mofe_max_ofes`; and DSS export mode/
order entries before any save/enqueue. Preserve the separately ratified WEPP
`kslast` omission/clearing contract. Validate required mapping/upload presence
before treatments/Ash mode changes. Preserve `fire_date:null` clearing, blank
project name/scenario behavior and observed CSV text with trimming disabled.
No rollback promise is made for later storage,
queue or computation failures after valid admission/application begins.

Webhook option parsing shares transport classification and request-body reuse.
Complete transport, raw structural/scalar-flag and state-independent supplied-value
validation before reserving callback records. Existing reserve/replay lookup may
precede state-dependent domain admission/validation, so a valid replay does not
need to re-admit work or revalidate changed project state. If that later validation
rejects a newly reserved request, apply the existing prepublication cleanup contract;
retain only its defined recovery/tombstone state, never an orphan active reservation.
Accepted idempotent
replay retains its receipt/digest/job identity and must not reapply inputs or
rerun state-dependent admission. Preserve prepublication cleanup and publication
uncertainty under the [webhook contract](rq-webhook-contract.md). Do not parse
bounded landuse/soil uploads through the generic webhook form reader first.

## User and operator behavior

For invalid input, correct the named field or encoding and resubmit. No new job,
source replacement or proposed input update occurs for the rejected request.
Send `{}` or a genuinely absent body only on operations that support defaults;
use explicit false to disable a stage. Existing form clients remain supported.
A callback publication-uncertainty response retains its existing same-key retry
instructions; it is not an invalid-input response.

Health signals are canonical 400 responses with no mutation plus successful valid
empty/form/false submissions. Danger signals are default jobs after malformed
input, 500/HTML validation responses, leaked temporary files or false rejection of
valid legacy requests. A recurrence warrants a new incident record and reinspection
of both adapters, all enclosing catches and the first mutation. Deployment and
production observation are separate from local conformance.

## Developer integration

`wepppy.request_payload` owns shared classification and the bounded
`RequestPayloadError`. Flask uses `PayloadRequest` plus the route helpers in
`routes/_common.py`; rq-engine uses `PayloadRoute` and `payloads.py`. Local broad
route catches must propagate the typed failure to these canonical JSON boundaries.
Do not replace a parse failure with an empty payload or initialize optional
controllers before independent input validation.

Use `request_form` and the bounded single-input adapter to reuse multipart state;
close transport resources on rejection, cancellation and disconnect. Validate
supplied files before promoting them. A sibling temporary file preserves relative
VRT dependencies; clean staged files and newly created empty directories on failure.
Temporary buffering is not accepted project state. Keep Flask form memory limits
before body reads and preserve deferred parser errors after CSRF consumes forms.

When adding a field, choose its scalar/list/raw adapter and null/blank/alias policy
from its domain contract. Test a registered route, rejection before its first
effect, and a valid same-process follow-up. Use actual controller/file readback for
changes to persistence or upload boundaries; controller mocks alone cannot prove it.

## Required conformance evidence

Exercise real HTTP decoding in Flask and FastAPI for the transport/flag matrix,
including absent Content-Length, duplicates, aliases, non-finite values and
multipart cleanup. Trace every repaired route through its actual exception
wrappers. Verify no enqueue, timestamp clearing, receipt replacement, source
promotion/deletion or persisted/cached proposed input change. Use real NoDb
save/reload and a same-process valid follow-up for representative boundaries.

Cover absent optional state, present-empty state, populated state, supported
legacy state, busy/replay state and malformed state separately from flag cases.
At minimum include RHEM cleanup sentinels, the five WAM-01 routes, a Flask default
mutation and actual multipart landuse/soil consumers. Preserve valid defaults,
false/zero, batch/base saves, aliases, callback replay and uploads. Read actual
prepared-input files for changed preparation boundaries; mock enqueue only where
needed to avoid model execution. An untested consumer remains unresolved.

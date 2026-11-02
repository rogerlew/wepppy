# MOFE input identity contract

**Status:** Accepted MIPA-01 checkpoint, 2026-11-02. The operator approved the
reviewed decisions and standalone checkpoint commit with “approved. proceed”.
Implementation conformance is pending; deployment is not authorized.

## Scope and related authority

MIPA-01 addresses the producer defects PMET-01–03, MAN-01–03, SOIL-01–02,
COVER-01 and SLOPE-01–02. An overland flow element (OFE) is an ordered segment
of a hillslope. Its identity must agree in generated management, soil, slope
and cover files and in the prepared copies consumed by WEPP.

The [MOFE management contract](mofe-management-artifact-contract.md) retains
mapping and cover precedence. The [Disturbed mapping contract](disturbed-mofe-mapping-contract.md)
retains class selection. The [single user-defined input contract](single-user-defined-inputs-contract.md)
retains upload admission, immutable source preservation and parameterization
exclusions. The [WEPP input contract](wepp-run-input-contract.md) retains
omission and explicit modifier semantics. No request fields, persisted keys,
formats, filenames, scientific lookup values or native limits change.

## Management schedules and references

Each source management contributes one OFE. Multi-OFE sources supplied as a
single stack member are outside this synthesis API; reject them before writing,
rather than declaring one element while emitting several. Validate this risk
with a real stacked-source reproduction before adding a guard.

Preserve the complete source calendar in chronological rotation/year order,
including every crop within a year. When combining different calendar periods,
repeat each complete source calendar independently with their least common
multiple as the logical repeat period. This retains all phases for later simulation-length expansion; using
the first OFE's period silently discards downstream years. Expansion to N years
must emit exactly N years from that combined timeline, including nonmultiples
of the period. When N is known, expand directly to N without first allocating
the complete common period. A standalone synthesis without N may represent the
full period, but any preallocation rejection must cite an existing applicable
limit; do not invent a ceiling. A large common period alone cannot reject an
otherwise supported bounded N-year request. Prove this with coprime source
periods and a small requested N. Normalize generated calendars to one rotation containing that
timeline, with independent year/OFE objects and consistent parent/root references.
Do not multiply N by the number of source rotations. Preserve ordinary one-year
and equal-period crop order, initial conditions and operation values.

Both ordinary and deduplicating synthesis must remap every plant reference,
including residue operations 10/12, initial residues and yearly crops. Reuse
scenarios only when their full referenced meaning is equivalent. Preserve
contour, drainage, operation and surface references. Parser/serializer changes
must cover legacy multiple-rotation readback as well as normalized new output;
changing synthesis alone cannot close the shared serialization defect.

Keep existing explicit resource/native scenario limits; do not add a new
scientific limit or truncate an unsupported graph. Identify any existing limit
that a complete timeline exceeds before count-driven allocation or publication and fail with actionable
input/count guidance. Native limits and execution evidence remain separate gates.

## Crop-keyed PMET identity

PMET remains a run-global crop-name table. Discover every plant scenario in all
staged hillslope managements, including rotation crops and residue-only scenarios
that the native reader enumerates. Retain the existing exclusion of management
filenames containing `pw0` (warm-up runs); do not introduce a general channel filter.
Enumerate files and rows deterministically. Scalar coefficients apply to every
discovered crop; mapping inputs must cover every discovered source name. Missing
mapping entries fail before replacing the table. No-management directory behavior
remains the existing empty table, with no implication that a native deck is ready.

Native crop names are eight-character keys. Equal native keys with equal intended
coefficients may share a row. Different coefficient pairs must have different
native keys and matching management references, independent of table row order.
Use deterministic generated aliases of at most eight characters from letters,
digits and underscore, beginning with a letter. Alias any identity that cannot
round-trip through both the native fixed-width name reader and list-directed
PMET token reader (including whitespace, separators, quotes and control bytes).
Check uniqueness against all retained native keys, and rewrite only generated
management copies. Keep full original identity and coefficient-context provenance
in machine-readable ordinary generated comments, and validate/recover it when
reparsing; the current management parser's discarded comments cannot be assumed
to preserve that mapping. Repeated preparation, direct repeated PMET calls and
archive/restore must resolve the same original mapping keys and reproduce stable
aliases/references without accumulating aliases or scenarios. Changing a mapping
value must still address the original source name, not a previous generated alias.
Missing or contradictory provenance on an already-aliased generated deck is an
explicit rebuild error; unchanged legacy unaliased decks remain supported.
Never change immutable uploaded files or rely on first-row selection to resolve
a collision. Generic mapping keys continue to refer to pre-alias source names.

For Disturbed, resolve each final OFE's management class and assigned soil
texture through the existing lookup and fallback rules. Join that result to
the actual staged crop scenarios and all their yearly uses. Do not substitute
hillslope-dominant assignments for populated MOFE state. When one scenario is
shared across elements that require different coefficients, separate its affected
reference graph before assigning aliases; silently assigning one pair is invalid.
Deduplication must include coefficient context. Preserve existing single-OFE
lookup values and uploaded-input exclusions. Missing or inconsistent populated
segment provenance fails with rebuild guidance before declaring preparation done.

This is an identity correction, not a new coefficient policy. Missing PMET-file
native behavior, native first-row fallback and PMET activation stay unchanged.
If implementation needs to alter fallback, defaults or parameter selection beyond
the existing per-segment lookup, stop and obtain a parameterization ADR decision.

## Soil and cover identity

Apply the existing developed-landuse exemption for `kslast` separately to each
generated OFE. In upload preservation mode, explicit overrides still apply to
every eligible input regardless of descriptive labels. The top-level restrictive
layer alias retains the final OFE's actual resulting restrictive record; it must
not overwrite an exempt final OFE. Absent overrides preserve existing values.

Version 9005 ordinary and debug serializers derive texture from the current OFE's
surface sand/clay. Preservation-mode serialization retains explicit admitted
fields; this proposal does not admit 9005 uploads or expand upload versions.
No texture classification thresholds, hydraulic predictions or fallback change.

Both RAP cover writers emit numerically ordered OFEs, so 2 precedes 10. The
requested OFE set must match across bands and years; missing/malformed populated
data is an explicit preparation error, not permission to use another element.
Existing single-OFE fallback, transform formulas and fire-year semantics remain.

## Slope representation

Enabled buffers require finite, strictly positive length. Zero is an invalid
enabled buffer, not an instruction to disable it: implicit disabling would change
element identities across other decks. Disabled buffers retain current behavior.
Positive buffers equal to or longer than the hillslope retain the current
single-element result. A count limit incompatible with the requested buffer
partition fails explicitly; it must not shorten the hillslope silently.

Automatic and explicit writers validate the same finite source geometry and
strictly increasing normalized boundaries. Each emitted segment has both 0 and 1
endpoints, finite values, and a positive length at the existing two-decimal
precision. Reject unrepresentable tiny segments before opening the destination;
do not merge them or invent a minimum scientific length. Retain existing output
precision and quantify total rounding error against the per-segment rounding
bound. Keep slope/map equality-boundary behavior consistent after reproducing the
shared failure. `min_length` remains historically non-enforcing (API-01); no new
minimum, unit conversion or segmentation heuristic is authorized here.

## State, errors and artifact lifecycle

| Runtime state | Required outcome |
| --- | --- |
| Feature never used; ordinary single-OFE project | Existing ordinary preparation and coefficients |
| Empty collector directory | Existing zero-row PMET result; no model-ready claim |
| Populated consistent MOFE assignments | Complete per-element calendars, coefficients and ordered files |
| Valid legacy generated names/calendars | Read existing data; regenerate corrected copies through normal preparation |
| Immutable uploaded sources | Retain bytes, admitted versions and excluded Disturbed behavior |
| Missing populated assignment or stale/count-mismatched deck | Explicit rebuild/preparation failure; no success status |
| Invalid enabled buffer, nonfinite geometry or unrepresentable interval | Existing bounded input/error translation; no invalid new slope publication |
| Writer failure or interrupted preparation | Existing failed job/status, visible partial evidence; retry normal preparation |
| Archive/restore or supported clone | Preserve source and generated artifact inventory and bytes under existing tools |

Malformed conditions are exceptional input/preparation failures. Optional absence
keeps its established create/no-op behavior; it is not reclassified as corruption.
No new route envelope, queue, transaction protocol, hidden directory or archive
exclusion is introduced. Existing normal project browse/download paths expose
`landuse/hill_*.mofe.man`, `soils/*`, slope/cover intermediates and `wepp/runs/*`,
with ordinary job diagnostics and completion status. File existence does not
override a failed preparation. Failures retain useful partial records; successful
retry regenerates from durable intent, not hand-edited derived files.

## Acceptance and operational boundary

Read generated and prepared files, verify relative-path SHA256 manifests and
element/crop/calendar semantics, then observe actual native coefficient selection
and fresh outputs/reports on a supported clone of an actual heterogeneous project.
Exercise distinct downstream crops, rotations, coefficient contexts, same-crop
reuse, single-OFE controls, both soil orders and twelve distinct cover blocks.
Repeat PMET preparation with scalar and mapping inputs, change an original-name
mapping between calls, reverse row order, and exercise space/comma/quote/Unicode
source names against both native readers; prove no token ambiguity or provenance
loss after ordinary serialization and archive/restore.
Include real failure/retry and archive/restore byte retention, and inspect normal
browse/download under representative worker identity, mounts and configuration.

Bind the exact Python modules, Rust extension and selected native executable.
Select a 9005-capable consumer for soil/cover acceptance. Unresolved PMET capacity
and adapter observation issues prohibit broader native claims. The existing
[FC/HK ownership HOLD](whole-soil-water-capacity-contract.md#known-native-coefficient-ownership-defect)
is unchanged. Producer validation cannot close that native defect.

Users receive corrections only after supported regeneration/preparation/rerun.
Operators must inspect intended per-segment selections and retain baseline inputs
and reports before any separately authorized recovery. Deployment, bulk existing
project regeneration and native-engine repair are excluded. Developers must retain
before/after discriminating artifacts and independent correctness review; a green
unit suite is not end-to-end acceptance.

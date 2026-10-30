# Standardize generated soil horizon insertion

## Purpose


Ensure every generated WEPP soil writer emits an explicit 200 mm boundary when
an input horizon crosses that depth, preserving its physical properties. The
operator authorized consistency across WEPPpy/wepppyo3 after observing that
native conductivity can propagate below 200 mm for an unsplit source horizon.
This is faithful generated-artifact behavior, not a surrogate calibration. Wired
completion requires emitted files and actual WEPP preparation/native evidence.

## Progress


- [x] Audit primary Python writers and Rust ownership; record compatibility scope.
- [x] Implement one canonical boundary operation and wire confirmed writers.
- [x] Test geometry/property preservation, idempotence and native capacity failures.
- [x] Exercise direct writers, ordinary/Disturbed/MOFE/prepared and native inputs.
- [x] Finish repository gates, docs, writer inventory and closeout.

## Context and orientation


Work from `/workdir/wepppy`; `/workdir/wepppyo3` contains the owned native kernels.
Existing uncommitted work in both repositories is unrelated and must remain.
The prior scientific packages are immutable evidence. Do not rewrite their raw
soil fixtures to conform retroactively. No branch change, commit or deployment
is required. Native WEPP remains `wepp_261026`.

`wepppy/wepp/soils/utils/wepp_soil_util.py` serializes ordinary modern soils and
has separate preservation-only uploaded serialization. Its disturbed converters
already split at 200 mm. `multi_ofe.py` concatenates component profiles. Direct
writers exist in SSURGO, ESDAC, ISRIC, SIFT and legacy Australian tools; Roads
also assembles legacy templates directly. Rust `wepp_interchange::soil_anisotropy`
returns per-horizon values and explicitly leaves file I/O to Python. Other Rust
soil modules serialize model outputs to Parquet, not model-input horizons.

## Plan of work


First inventory all emitted soil paths and define the generated-input contract
and parameterization ADR. Preserve the existing upload-only preservation path
unless the operator explicitly changes that scope. Treat copying immutable source
assets separately from constructing generated/prepared model inputs.

Second implement a small shared text-preserving boundary normalizer. Soil rows
use cumulative bottom depth in millimeters. Find the row spanning 200 mm, insert
a copy with only its bottom-depth token changed, and increase that OFE's declared
layer count. Preserve all physical/hydraulic tokens and metadata. Leave exact
boundaries and profiles shallower than 200 mm unchanged. Validate structural
inputs before publication and reject required insertion that exceeds ten layers;
never delete or merge deeper material to make room. Reuse at the serialization
boundary so direct dataset writers and composed profiles follow one rule.

Third wire ordinary generated serialization and each confirmed direct writer.
Disturbed conversion retains its existing top-layer parameter treatment; the
normalizer must be idempotent on those already-split outputs. Keep uploaded
serialization separate, preserving explicit Rosetta/native values and topology.
Rust needs no duplicate implementation when it does not write soil inputs.
Document ownership and all intentional exclusions in the audit artifact.

Fourth validate actual emitted profiles and downstream prepared copies. Reuse
the sandy-loam reproducer, preserving original source files, to show generated
unsplit and already-split sources now emit equivalent layered inputs under the
exact study binary. This is a compatibility change that may increase sediment,
not evidence of improved physical calibration. Test non-road ordinary preparation
as well as Roads/MOFE and landuse-conditioned consumers.

## Validation and acceptance


Meaningful tests cover insertion in a first or later horizon, multiple OFEs,
unchanged deeper properties, precise appended hydraulic tokens, restrictive
records, exact boundary idempotence, shallow profiles and capacity failure.
Check ordinary serialization does not mutate its source object. Validate upload
preservation separately. Run targeted `wctl run-pytest`, applicable stub checks,
then full repository coverage. Review generated files in scratch `wepp/runs`,
not just in-memory state or job success. Document all failures and corrections.
Use `wctl doc-lint`, spelling previews and `git diff --check` for documentation.

## Concrete steps


Create `wepppy/wepp/soils/horizon_boundary.py` and focused tests under
`tests/soils/`. Exact commands/results will be retained in artifacts/validation.md.
Use `/wc1/runs/so/soil-boundary-consistency-20261029` for disposable generated
inputs and native outputs. No original project or benchmark inputs are edited.

## Idempotence and recovery


Normalization must return identical text on a second invocation. Stage generated
text before opening destination files so capacity/structure errors do not truncate
valid artifacts. Native experiment directories refuse existing destinations.
Preserve unrelated dirty files, especially generated docs_index.json and Rust
calendar/HBP work. No native .so or WEPP executable modification is planned.

## Surprises & Discoveries

The final writer search also found two channel-soil serializers, now covered.
Rust has no input-soil writer: its soil modules emit model outputs, and its
anisotropy kernel returns values to Python. Disturbed conversion can create an
eleventh layer before final serialization; final capacity validation covers that
path too. Australian legacy headers declared one layer while emitting two; the
count is corrected. Independent legacy SIFT/Australian header-field omissions
remain documented in the writer audit, without inventing new parameter defaults.

Three existing ESDAC/anisotropy/developer-mode expectations required new emitted
horizon counts. Source fixtures remain unchanged. Anisotropy assignment still
precedes final serialization and copied pieces inherit assigned values.

## Decision Log

2026-10-29: Standardize generated output at 200 mm, preserving physical tokens,
source objects and uploaded-soil preservation. Include watershed channel writers
and valid zero-channel output. Reject more than ten generated layers rather than
merge or discard material. Keep Disturbed overrides and the 500 mm anisotropy
classification policy separate. Do not duplicate Python input serialization in
Rust or change native WEPP. These decisions are normative in the boundary
contract and ADR-0110, with ownership and limitations in artifacts/writer-audit.md.

2026-10-29: After the broad gate found the developer-mode count assertion, retain
its 5,367 successful prefix nodes and continue from the exact corrected case.
Fresh collection and node hashes prove all 6,201 remaining nodes are covered.

## Outcomes & Retrospective

Complete locally: shared normalization is wired into every confirmed generated
input writer. Fresh repository coverage totals 12,135 passed and 298 skipped,
with the corrected failure revalidated and no uncovered cases. Stub checks,
documentation lint, syntax parsing and whitespace checks pass. Native v4 replay
has identical model records and all output hashes, including complete daily WAT
calendars, for normalized split/unsplit sources under exact wepp_261026.

The matching sediment result remains 4473.288 kg/year; writer consistency does
not establish physical field accuracy or complete Roads calibration. Existing
uploaded topology remains an explicit exception. No deployment, binary rebuild,
source-catalog rewrite or unrelated Rust edit was made. See artifacts/validation.md
for commands, initial failures/corrections, coverage proof and limitations.

## Interfaces and dependencies


Use Python standard-library text handling and existing soil/WEPP tools. No new
external dependency. The shared normalizer returns soil text and performs no
I/O; existing owners retain publication. Additive public helper is documented
and covered; existing public imports and native module interfaces stay stable.

Initial revision: 2026-10-29, recording user-authorized cross-writer consistency.

Final revision: 2026-10-29, recording completed implementation, native parity,
all repository coverage, writer limitations and documentation closeout.

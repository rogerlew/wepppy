# Independent contract review B

Reviewer: `/root/prism_contract_review_b`, 2026-10-08 UTC. Read-only contract
review against starting implementation `199fa5b1ea74e715804467849535205f2a13acc0`.
Scope: historic PRISM contract, ADR-0082, climate lineage delta, checkpoint and
ExecPlan; source inspection of existing observed adapters, PRN writer, bulk
cache, staged publication and monthly revision. No implementation changes.

## Findings

### CRB-01 — Medium: numerical acceptance omits PRN quantization

The PRISM contract's spatial/transformations and persistence sections promise
wet/dry calendar preservation and precipitation/temperature parity at CLI
rounding precision. The established writer at
`wepppy/climates/cligen/cligen.py:672–679` rounds precipitation to hundredths of
an inch (0.254 mm) and temperatures to integer Fahrenheit (5/9 C increments).
For example, 0.1 mm becomes zero and 10.2 C becomes 10 C before CLIGEN executes.
This exceeds final CLI rounding and can remove trace-rain days. Monthly ratios
and final serialization can also round small positive precipitation to zero.

Required correction: explicitly define parity against PRN-quantized forcing,
followed by the applicable monthly revision, declared scaling and final CLI
serialization. State trace-rain loss and retain counts/before-after diagnostics.
Keep raw source tables exact. Do not restore rain after CLIGEN without a separate
decision on formerly dry days' storm duration/intensity. Include trace rain and
temperature-rounding cases in real PRN/CLI readback acceptance.

### CRB-02 — Medium: ADR lacks required decision provenance and rollback

ADR-0082 records intent and rationale but omits explicit decision venue/timezone,
participants, decision owner, implementer, evidence links and risk/rollback notes
required by `docs/standards/parameterization-adr-standard.md`. These matter here
because the new adapter introduces a radiation conversion and formally carries
forward a scientifically consequential dewpoint transformation.

Required correction: add concise provenance for this user/Codex conversation,
link the checkpoint and relevant prior evidence, and state rollback to a
previous supported dataset with a normal rebuild. Never imply existing PRISM
raw records require numeric conversion or deletion during rollback.

## Contract strengths and implementation acceptance risks

The additive enum preserves legacy mode meanings. Both requested spatial methods
are distinct; nearest-cell reuse introduces no interpolation or extra monthly
adjustment. Full-year coverage, explicit provider failures, unchanged endpoint
authorization and outside-lock collection/fresh-input finalization are adequate
contract choices. A failed Multiple revision explicitly leaves centroid-only
state unready for WEPP, without success hooks.

The contract requires visible project-owned evidence, canonical archive/restore
and live prepared CLI/WEPP output readback; implementation evidence remains
pending. Specific source-backed risks to verify during implementation:

- `PrismBulkClient._attempt` retains failed extraction data only in the shared
  cache and raises without returned provenance. The integration needs to retain
  its own attributable failed acquisition records in the project attempt, as
  well as source and fresh-check receipts on warm cache hits. Do not discover
  ownership by sweeping unrelated concurrent cache attempts.
- A switch to another dataset currently reaches whole-directory cleanup in
  `climate_build_router.py:19–64`. Test retention of prior PRISM attempts across
  dataset changes as well as repeat PRISM builds.
- Recompute post-revision dewpoint from raw tdmean and final Tmin; flooring the
  already floored centroid series would retain an excessive floor when a
  hillslope becomes colder.
- Readback must prove complete hillslope mappings for nearest-cell mode;
  existing `Climate.has_climate` checks mappings only for Multiple. Failure
  tests must not accept a centroid-only nearest-cell result as complete.
- Archive/restore must use the canonical implementation and read actual bytes,
  and browser/download checks must use ordinary forest service identities.
  Mocked publication or a successful RQ job cannot release this change.

## Verdict

Initial gate: **hold** pending CRB-01 and CRB-02 corrections and independent
post-fix confirmation. No high-severity authority, security or locking conflict
found. No implementation or environment conformance claim is made by this
pre-implementation review.

## Post-fix confirmation

2026-10-08 UTC: independently reread the amended PRISM contract, ADR-0082,
checkpoint, lineage delta and Project Config capability amendment. Implementation
and tests remain unchanged at this checkpoint.

- **CRB-01 resolved.** The contract now states 0.254 mm/integer-F PRN
  quantization, trace-rain dates/counts, quantized numerical acceptance and the
  prohibition on restoring rain onto a generated zero-duration storm. It
  qualifies wet/dry preservation by final rounding. Original source values
  remain available for comparison. Monthly revision and existing precipitation
  scaling retain their separately stated transformations.
- **CRB-02 resolved.** ADR-0082 now identifies conversation venue/date/timezone,
  participants, owner and implementer, links source/checkpoint evidence, and
  records risks and rollback. Missing exact message time is disclosed rather
  than invented. Rollback preserves archived source and the capability reader
  floor.
- The contract additionally requires attributable failed acquisition paths and
  explicit raw-dewpoint reuse for revision. These resolve ambiguity in the
  intended behavior; actual retention and numerical conformance still need the
  planned implementation tests.
- The Project Config amendment names old and new immutable structures, preserves
  historical stored authority, requires explicit eligible refresh, and requires
  forest reader-floor acceptance before writers. Independent stdlib hashing of
  the existing CONUS payload with the declared dataset/method additions confirms
  `2c2934682af720fac7d022aa22f830087a10f2f423e4cb329d2a23c88c6ef1d3`
  when the new dataset follows GridMET. This composes the named reader boundary
  without advancing unrelated Project Config initiatives.

Final contract gate: **pass**. Unresolved contract findings: high 0, medium 0,
low 0. Approve the reviewed documents for the standalone pre-implementation
ancestor checkpoint. This does not approve deployment or establish artifact,
archive, persistence or WEPP runtime conformance. The implementation acceptance
risks above remain required review targets.

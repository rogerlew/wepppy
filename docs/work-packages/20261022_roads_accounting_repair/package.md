# Roads modeled-area accounting repair

**Status**: Active — final contract checkpoint review (2026-10-22)  
**Timezone**: UTC

## Purpose and approved scope

Implement the explicit Roads modeled-area contract in wepppyo3 and integrate it
into WEPPpy. Roger authorized implementation, task-scoped commits in both repos,
PASS reconstruction and fresh routing validation. His latest direction is to keep
full modeled MOFE footprint areas without determining geographic overlap.

For point-source targets retain all contributor MOFEs, use baseline remainder
max(A-C,0), and report modeled area max(A,C). Existing replacement strips and
remainders replace baseline with their summed modeled area and preserve replacement
precedence. PASS and WAT use one represented-area ledger, with explicit source
serialization reconciliation. Geographic union, new fill/buffer positioning and
spatial-overlap inputs are out of scope. Earlier GIS proposals are superseded.

This is modeled-area response mixing, not rerunning residual baseline hydrology
or certifying geographic/whole-system water closure. Roads routed outputs change;
baseline runs, executable physics, connectivity and AgFields behavior do not.
No production rollout or in-place historical run repair is included.

## Deliverables and complexity budget

Deliver the canonical contract/ADR and reviewed ancestor checkpoint; a Roads
strategy in the existing native weighted PASS combiner; native ledger-aware
water aggregation plus equivalent average-report WAT; WEPPpy integration before
routing; cache/readiness provenance; tests and isolated UM1 routed/report evidence.
No new services, queues, dependencies, Python numerical fallbacks or topology.

## Compatibility and regression plan

Preserve baseline APIs/results, report names/columns/units and raw native archives.
Use WAT stationary OFE area for continuous ledgers and PASS-header area for
single storms. Record product-specific weights. Preserve original PASS for
untouched targets; zero-road continuous reports must match baseline. Keep
TotalWatSed Q diagnostics distinct from physical Q in derived report WAT.
Optional sources retain native source-qualified support weighting and null rules.

Cover C<A, C=A, C>A, multi-OFE contributors, replacement/remainder, mixed precedence,
empty and missing manifests, legacy provenance, intentionally skipped versus
failed execution, area/schema/date/terminal errors, particle-header differences,
optional partial observations, cache freshness and baseline isolation. Validate
actual serialized inputs and fresh routed/model/report outputs, not mock success.

## Authority and rationale

Roger's 2026-10-22 conversation explicitly authorizes modeled footprints and
questions geographic overlap. The max remainder/expansion rule preserves full
MOFE sources while avoiding negative baseline representation and permits modeled
expansion as requested. The decisive rule lives in
[Roads modeled-area accounting](../../schemas/roads-water-accounting-contract.md)
and [ADR-0102](../../adrs/ADR-0102-roads-modeled-area-accounting.md).

Task-scoped commits are authorized. Two independent reviews and the committed
contract ancestor are required before runtime edits. Unrelated dirty changes
in both repos remain excluded. Earlier geographic steering is historical only.

## Validation and review

Security triage: **high** for file/path and execution-input publication changes;
a dedicated security artifact is required. No new auth, public endpoint,
credential, subprocess mechanism or queue wiring is planned.

Run native and focused WEPPpy tests, required API/stub checks, full WEPPpy sanity,
and independent correctness/security reviews. Retain source/native binary hashes,
build provenance, artifact lineage, complete UM1 daily/yearly comparisons and
fresh watershed inputs/outputs. No implementation or deployment claim yet.

## References

- [ExecPlan](prompts/active/repair_execplan.md)
- [Tracker](tracker.md)
- [Investigation](../20261022_roads_lateral_flow_investigation/diagnosis.md)
- [Contract decision](artifacts/20261022_contract_decision.md)
- [Geographic audit (superseded allocation proposal)](artifacts/20261022_geometry_review.md)

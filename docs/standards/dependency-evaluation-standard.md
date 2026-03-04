# Dependency Evaluation Standard

Gate for evaluating proposed external dependencies before adoption. Agents encountering "should we use X?" questions must run through these gates before recommending integration or starting implementation work.

## Applies When

- A stakeholder, user, or agent proposes adding a new external library.
- A proposal suggests replacing an existing owned component with an external one.
- An institutional or marketing source promotes a tool for adoption.

## The Owned Stack (Performance Baseline)

These components exist because measured Python-only alternatives were inadequate:

| Component | Language | What it replaces | Measured advantage |
|-----------|----------|------------------|--------------------|
| weppcloud-wbt | Rust | WhiteboxTools upstream | Custom hydrology algorithms, VRT windowed reads (17.5x faster, 32x less memory) |
| wepppyo3 | Rust+PyO3 | Pure Python raster classification | Raster key classification, climate interpolation, SBS mapping |
| oxidized-rasterstats | Rust | python-rasterstats | 8-17x faster zonal/point stats, 127 tests, 11 regression denylists |
| peridot | Rust | Python watershed abstraction | Flowpath construction and watershed abstraction |

Any proposal to replace or supplement these must benchmark against them, not against the Python libraries they already replaced.

## Evaluation Gates (Sequential)

### Gate 1: Precedent Check
Search the precedent registry (below) for prior evaluations of the same or similar dependency. If a completed evaluation exists, reference its outcome before starting new work.

### Gate 2: Capability Overlap Audit
Map the proposed dependency's capabilities against what the current stack already provides. Use `ARCHITECTURE.md` and the owned-stack table above. If the majority of proposed capabilities are already covered, the burden of proof is on the proposal.

### Gate 3: Dependency Tax Assessment
Quantify: transitive dependency count and known CVE exposure, API stability history (breaking changes per year), maintenance activity (last release, bus factor, funding model), framework lock-in risk (does it impose its own data model?), build/install complexity (does it require a separate environment?).

### Gate 4: Performance Benchmark (required for critical paths)
For any dependency touching geospatial, raster, hydrology, climate, or model execution paths: design benchmarks from WEPPpy-representative workloads (not toy examples), require parity assertions (output equivalence, not just "it runs"), measure on production-representative hardware, include memory and I/O telemetry (not runtime alone).

### Gate 5: Marketing Claims vs Evidence
When a dependency is promoted with performance or capability claims: treat marketing copy and institutional endorsements as hypotheses (not evidence), audit source code for claimed capabilities, require reproducible benchmarks before accepting efficiency claims, document which claims are verified, unverified, or contradicted.

## Precedent Registry

| Date | Dependency | Outcome | Evidence |
|------|------------|---------|----------|
| 2026-03 | raster_tools (USDA RMRS) | defer | `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/artifacts/adoption_recommendation.md` |

Add new rows as evaluations complete. Link to the work package recommendation artifact, not raw data.

## Work Package Pattern for Evaluations

When an evaluation is warranted, create a scoped work package under `docs/work-packages/` following the standard template. The raster_tools package serves as the reference implementation for the evaluation workflow: cross-walk first, then benchmark only on confirmed overlap.

## References

- Manifesto philosophy: `AGENTIC_AI_SYSTEMS_MANIFESTO.md` section "Own the Stack"
- Existing standards: `docs/standards/`
- Work package process: `docs/work-packages/README.md`

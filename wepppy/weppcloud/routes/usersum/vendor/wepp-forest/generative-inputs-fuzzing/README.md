# Generative Inputs Fuzzing for WEPP-Forest

This document defines a practical, evidence-driven plan to use property-based and
constrained generative fuzzing to find arithmetic failure boundaries (`SIGFPE`,
invalid-domain math, and related runtime traps) in WEPP-Forest.

The approach combines:
- wrapper-level property testing (Hypothesis-style) for input parse/validation/serialization code,
- targeted domain generators for soil and landuse/management inputs,
- high-volume execution of trap-enabled WEPP binaries,
- routine-level crash clustering and upstream traceability to input parameters.

## 1) Goals and Success Criteria

Primary goals:
1. Discover new reproducible trap conditions before production run payloads hit them.
2. Map each discovered trap boundary to a concrete routine-level arithmetic condition.
3. Trace each condition to upstream input parameters and wrapper contracts.
4. Convert confirmed boundaries into permanent regression tests and narrower guards.

Success criteria:
- New campaign runs produce deterministic crash signatures with full repro artifacts.
- Each confirmed trap includes:
  - routine/top-frame signature,
  - minimum repro input snapshot,
  - upstream parameter lineage,
  - explicit keep/rollback outcome in ablation records.
- Known historical trap classes are rediscovered by targeted generators (sanity check).

## 2) Scope and Non-Goals

In scope:
- `wepp` and `wepp_hill` trap-enabled execution campaigns.
- Input families that influence hydraulic, frost, routing, and seepage arithmetic.
- Wrapper contract checks where input files are assembled or transformed.

Out of scope (initial tranche):
- Pure random byte-level fuzzing of Fortran text readers.
- Full climate generator redesign.
- Scientific parity adjudication for all generated runs.

## 3) Core Strategy (Three Layers)

### Layer A: Wrapper Contract Properties

Use property tests on wrapper code that reads/writes WEPP inputs and run contracts.

Required properties:
1. Parse/serialize round-trip stability for supported formats.
2. Deterministic output: same canonical input -> byte-identical generated files.
3. Explicit failure on malformed/unsupported states (no silent coercion).
4. Contract invariants preserved across adapters (for example layer counts, units,
   and required key presence).

Why first:
- Removes wrapper noise before binary-level fuzzing.
- Ensures crashes are tied to modeled states, not writer corruption.

### Layer B: Constrained Domain Generators

Use plausible-but-pathological generators, not unconstrained random values.

Generator modes:
- `VALID_BASELINE`: physically plausible, contract-valid inputs.
- `BOUNDARY_STRESS`: near-zero, near-limit, and boundary-transition values.
- `PATHOLOGY_INJECTION`: controlled violations for explicit-failure checks.

### Layer C: Trap-Enabled Binary Campaigns

Run generated cases through `wepp` / `wepp_hill` builds with floating-point traps
enabled (current build policy already uses `-ffpe-trap=invalid,zero,overflow`).

Capture per case:
- exact binary path and build provenance,
- input snapshot (all generated files + seed metadata),
- stdout/stderr,
- observe markers (`wepp_observe.on` when enabled),
- classification (`PASS`, `SIGFPE`, and other runtime-failure classes per
  `specs/canonical_result_schema.md`; timeout classification is handled by the
  campaign runner layer).

## 4) First Tranche Parameter Subset

Start with parameters most likely to trigger divide/power/index boundaries in known
high-risk paths.

### Soil (layered)

Per layer fields (initial target set):
- `thickness`
- `sand`, `silt`, `clay`
- `bulk_density`
- `rock_fragment`
- `organic_matter`
- `ksat` / saturated conductivity terms
- `porosity` or derived pore terms
- water-content boundary terms used by hourly/percolation logic

Cross-layer invariants:
- layer count consistency with profile metadata,
- strictly positive thickness,
- texture fractions sum within tolerance,
- monotonic depth accumulation,
- bounded physical ranges for density/porosity/water terms.

Boundary stressors:
- denominator-near-zero states,
- impermeable lower-layer transitions (`ksat -> 0` style boundaries),
- thin-layer transitions around frost lookup depth boundaries,
- exponent base values near 0 with fractional exponents.

### Landuse / Management

Initial target set:
- canopy/residue cover fractions,
- roughness terms,
- root depth,
- LAI trajectory anchors,
- event timing/duration terms relevant to routing intensity calculations,
- management schedule transition edges.

Boundary stressors:
- zero-duration with non-zero runoff-driving context,
- abrupt cover/roughness phase shifts,
- root depth interacting with shallow/degenerate soil layers,
- minimum/maximum schedule values at event boundaries.

## 5) Routine-First Trap Mapping Workflow

For each discovered or historical trap class, maintain a map:

1. Routine + expression class
2. Math risk type
3. Candidate upstream soil/landuse contributors
4. Generator dimensions required to activate the risk
5. Existing guard status
6. Regression coverage status

Initial seed map from recent incidents:
- `wshpas`: divide boundaries around runoff intensity and rise-time terms.
- `perc/purk/watbal_hourly`: harmonic-mean and seepage denominator boundaries.
- `locate/frostn`: layer index/depth boundary assumptions.
- `saxfun/watdst`: power/divide domain boundaries in frost-season distributions.

## 6) Harness Architecture

### Inputs
- Base seed corpus from real fixtures and staged run payloads.
- Generator config profile (`baseline`, `stress`, `pathology`).
- Campaign manifest (case count, random seed, binary lane, timeout).

### Execution
- Materialize each generated case in an isolated run directory.
- Execute chosen binary with hard timeout.
- Parse logs for completion markers and trap signatures.
- Record structured result row per case.

### Outputs
- `manifest.csv` / `results.csv` (or parquet equivalent),
- per-case artifact folders,
- clustered signature report,
- minimized reproducer catalog.

## 7) Crash Signature and Minimization

When a trap occurs:
1. Parse top frame/call chain from stderr.
2. Assign canonical signature key:
   - `(signal_class, top_frame, routine_chain_hash, last_marker_tag)`.
3. Deduplicate identical signatures.
4. Run minimization (delta-debugging style) against generator dimensions to find
   smallest parameter set that still reproduces.
5. Emit a stable repro bundle for ablation workflow.

Minimization deliverable per signature:
- smallest known failing input,
- exact seed and generator configuration,
- one-command replay script.

## 8) Throughput Plan

Recommended starting scale:
- Daily developer lane: 1k-5k generated cases.
- Nightly CI lane: 10k-50k cases (sharded by routine risk family).

Sharding strategy:
- by routine family (`wshpas`, `perc`, `frost`),
- by generator mode,
- by binary (`wepp`, `wepp_hill`).

Use stable pseudo-random seeds so failures are reproducible and bisectable.

## 9) Integration with Existing Ablation Protocol

Every novel signature promoted to investigation should create/update an incident
package under `docs/ablation/` and follow `docs/ablation/protocol.md`.

Required linkage:
- fuzz campaign signature ID -> ablation incident ID,
- minimized repro path -> incident artifacts,
- keep/rollback decision -> incident notes and final report.

## 10) Proposed Repository Layout

Recommended initial structure in this repo:

```text
generative-inputs-fuzzing/
  README.md
  specs/
    routine_trap_map.md
    parameter_contracts.md
  seeds/
    README.md
  results/
    .gitignore
  scripts/
    run_campaign.py
    classify_signatures.py
    minimize_case.py
```

If wrapper-level property tests live in `wepppy`, keep shared specs synchronized
via mirrored docs or explicit cross-repo references.

## 11) Rollout Milestones

### Milestone 0: Instrument and Baseline
- Confirm binary lanes and trap settings.
- Define canonical result schema and signature parser.
- Validate harness replay on known historical failing cases.

### Milestone 1: Wrapper Property Suite
- Add/expand Hypothesis-style tests for input writer/parser boundaries.
- Lock deterministic serialization and explicit-failure contracts.

### Milestone 2: Soil/Landuse Generators (First Tranche)
- Implement constrained generators for target parameter subset.
- Validate generation quality against physical/contract invariants.

### Milestone 3: Scale Campaign + Signature Clustering
- Run multi-thousand-case campaigns.
- Cluster, dedupe, and minimize failing cases.

### Milestone 4: Routine-by-Routine Closure
- Trace each signature to upstream parameters and routines.
- Create targeted guards or upstream contract constraints.
- Add regression tests for each confirmed boundary.

### Milestone 0 Completion (2026-04-21)
- [x] Confirmed binary lanes and trap settings in
  `specs/milestone0_binary_lanes.md`.
- [x] Defined canonical case/signature schema in
  `specs/canonical_result_schema.md`.
- [x] Built a deterministic signature parser + replay validator:
  `scripts/classify_signatures.py`.
- [x] Validated replay against known historical failing artifacts from
  `docs/ablation/*` via `seeds/milestone0_known_failures.csv`.

Milestone 0 validation command:

```bash
cd /home/workdir/wepp-forest
python generative-inputs-fuzzing/scripts/classify_signatures.py \
  --manifest generative-inputs-fuzzing/seeds/milestone0_known_failures.csv \
  --base-dir /home/workdir/wepp-forest \
  --enforce-expected \
  --json-out generative-inputs-fuzzing/results/milestone0_validation.json \
  --csv-out generative-inputs-fuzzing/results/milestone0_validation.csv
```

## 12) Risks and Controls

Risk: high false-positive noise from impossible physical states.
Control: strict constrained generators + mode separation (`VALID_BASELINE` vs
`PATHOLOGY_INJECTION`).

Risk: non-deterministic campaign outcomes.
Control: pinned seeds, pinned binaries, pinned fixture corpora, deterministic
run directory materialization.

Risk: large artifact volume.
Control: retain all failing/minimized cases; sample or TTL-prune passing cases.

Risk: broad guard creep without evidence.
Control: enforce ablation protocol and keep/rollback discipline per signature.

## 13) Immediate Next Steps (Concrete)

1. Build `routine_trap_map.md` with current known signatures and upstream
   candidate parameters.
2. Implement a minimal campaign runner that executes generated run dirs and emits
   normalized result rows.
3. Add first constrained generators for:
   - soil layer thickness/texture/density/conductivity family,
   - landuse event duration/cover/roughness family.
4. Run a pilot campaign (500-1,000 cases) and verify signature clustering quality.
5. Promote first confirmed novel signature into a formal ablation incident package.

---

This plan intentionally starts narrow, prioritizes routine-level traceability,
and expands only after reproducible signal quality is proven.

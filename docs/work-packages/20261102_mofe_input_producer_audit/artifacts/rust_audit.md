# Rust MOFE producer audit

Status: confirmed native writer readback and bounded static audit, 2026-11-02.
No runtime source, release artifact, or active parent-program test was changed.
This report uses the docs-maintainer skill. Production remediation is pending.

## Findings

### R1: invalid enabled buffer lengths produce invalid slope files

Priority: high. Confirmed with the actual installed native API.
`/workdir/wepppyo3/wepp_interchange/src/mofe.rs:61` substitutes zero for nonfinite
buffer lengths and does not reject zero/negative lengths. Lines 87-89 append that
boundary; lines 323-327 normalize by a possibly zero segment width.
On a 100 m source, `apply_buffer=True, buffer_length=0` succeeds and emits a first
OFE with one point, length `0.00`, and coordinate `NaN`. Length `-10` succeeds
and emits a first OFE of length `-10.00`.

Production entrypoints pass numeric values without a positivity guard:
`wepppy/microservices/rq_engine/watershed_routes.py:1100`,
`wepppy/nodb/core/watershed.py:764`, and
`wepppy/nodb/core/watershed_mixins.py:259`.
This establishes reachable producer behavior, not an affected project count.

Smallest repair: define the active-buffer validity contract, reject invalid
values at the native boundary, translate errors through existing contracts, and
check serialized OFEs before publication. Do not silently redefine zero as a
different requested configuration. Exercise zero, negative, nonfinite,
equal-to-hillslope and greater-than-hillslope lengths with real writer readback.

### R2: explicit intervals can collapse during serialization

Priority: medium. Confirmed with the actual installed native API.
`mofe.rs:180-218` accepts strictly increasing finite breakpoints. Line 318 compares
global distances rounded to four places before including the endpoint. Line 337
serializes length to two decimal places without a representability check.
Breakpoints `[0, 0.00001, 1]` on a 100 m source return two OFEs, but the first is
one point at normalized distance zero with length `0.00`.

The AgFields caller validates order/contiguity but not serialized size at
`wepppy/nodb/mods/ag_fields/concept1_inputs.py:92-107` and invokes the writer at
line 131. Planner fractions derive from cell counts at
`concept1_planner.py:921-922`. Tiny intervals are a plausible application trigger;
an affected real project has not been established.

Smallest repair: preserve normalized endpoints independently of global rounding
and explicitly handle intervals whose requested length cannot be represented.
Do not silently merge OFEs: management/soil identity depends on the topology.
Acceptance needs tiny intervals, nearby source vertices, ordinary intervals,
total-length readback, coupled deck count checks and native consumer execution.

### R3: exposed minimum length is ignored

Priority: low; confirmed behavior with an unresolved API contract.
`wepppy/topo/watershed_abstraction/slope_file.py:272-281` and
`wepp_interchange/src/lib.rs:1239-1257` expose `min_length`, but Rust accepts it as
unused `_min_length` at `mofe.rs:24`. Setting `target_length=1, min_length=10,
max_ofes=200` on a 100 m source emits 100 one-meter OFEs.
The legacy Python implementation also ignores this parameter; it is not a
new Rust migration regression. Define compatibility before enforcing a minimum
or native count cap. Parameterization changes require the applicable ADR.

## Coverage and limits

- The native slope writer iterates every output OFE. No first-OFE-only loop was
  found. Explicit segmentation checks source geometry and a 20-OFE limit;
  automatic segmentation lacks equivalent full source-profile validation.
- The raster MOFE label producer checks shapes, requested IDs, source cells and
  contiguous labels, with an existing rank-assignment repair. Its fraction
  validator allows equal adjacent boundaries
  (`watershed_abstraction/src/lib.rs:244`), so it does not consistently reject
  zero-length intervals from a slope. Include this peer in R1/R2 assessment;
  actual map corruption is not established here.
- No Rust PMET, WEPP soil or management-file producer was found in the inspected
  modules. Those writers remain Python-owned. `roads_flowpath` returns geometry;
  climate writers operate at climate-file scope without OFE-indexed branches.
- This is not an exhaustive climate, output-interchange, or every-crate audit.
  No builds, broad tests or full WEPP simulations were run.

## Reproduction and provenance

Run from `/workdir/wepppy`; the output directory must not already exist:

```sh
PYTHONPATH=/workdir/wepppyo3/release/linux/py312 python3.12 docs/work-packages/20261102_mofe_input_producer_audit/artifacts/reproduce_rust_audit.py /tmp/mofe-rust-audit-new
```

The [reproducer](reproduce_rust_audit.py) calls the real exported native writers,
records the resolved extension hash, source checkout HEAD/status and output
hashes. It intentionally captures current behavior rather than claiming native
WEPP acceptance. A future fixed writer may reject these cases; retain this
historical evidence and add separate post-repair evidence.

Retained [readback](rust_reproduction/readback.json) and inputs/outputs reside in
`rust_reproduction/`. The audited source HEAD was
`4d4c075421c4013cba99a0addc76482229e7f3f7`. The executed extension SHA256 was
`7f67d3a8e56066d43b2fdb1ffc5360d357d61f2fcc963190c67fe288373702ad`.
These identify source and binary separately; no assertion is made that this
binary was built from the inspected HEAD.

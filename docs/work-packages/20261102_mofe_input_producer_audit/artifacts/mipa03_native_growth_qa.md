# MIPA-03 independent actual-growth compatibility QA

Reviewer: `mipa03_native_qa`, 2026-11-03 UTC. **PASS for the bounded actual-GROW
comparison described here.** This is not release, full-history, hydraulic,
initialization/cutting, residue, or configured-project acceptance.

## Executable method and provenance

Native `tests/test_specialized_rap_growth.py` compiles unmodified reference
`grow.for` and `rtpart.for` from model source
`2e5928702edd5526a119216bd6be5997729ec72e`, with their transitive original
include dependencies, separately from current `grow_rap.for`, `rtpart.for`
and `rap_state.f90`. The reference snapshot has 33 source/include files totaling
93,471 bytes under `tests/fixtures/specialized_rap_reference`; its manifest binds
source commit and every file hash. Mandatory tests need no external checkout or
private project. These native source fixtures are internal resources, not public
release-report attachments.

Both programs receive identical prescribed state. They execute actual native
arithmetic and emit canopy, height, biomass, root mass/depth, LAI, heat-unit state,
shared `rdmax` and root partition values for 12 ordered OFEs. OFEs 2 and 10 have
distinct tree cover and soil depth. There is no Python model of the equations.
Reference capacities remain unchanged; candidate probes use its supported hill
capacity includes. All compilation occurs in private temporary directories.

Compiler: `/usr/bin/gfortran`, `-O2 -fcheck=all -fno-align-commons
-mcmodel=medium -finit-local-zero -ffpe-trap=invalid,zero,overflow
-ffp-contract=off`. This establishes same-compiler consumer compatibility, not
binary equivalence with the historical executable or final release compiler
wrappers. `RESUP` is an error sentinel: invoking it fails instead of simulating
successful residue behavior. Actual `RTPART` is compiled and executed.

## Results

Command from the selected native checkout:

```sh
PATH=/usr/bin:/bin:$PATH pytest tests/test_specialized_rap_growth.py -x -q
```

Observed: **69 passed in 3.68 seconds**. The matrix compares exact printed
native bytes for 64 cases: eight class/state modes, observed/transformed flag,
fire-eve/fire-day and following-year January/anniversary dates. Each case uses
12 OFEs and reports 12 state quantities per OFE. Counts are state observations,
not independent scientific studies or complete daily/hourly histories.

Discriminating behavior checks additionally establish:

- transformed forest can increase canopy from .4 to its reference TREE assignment;
  OFEs 2 and 10 retain distinct assignments;
- a January date after the fire year takes the different reference anniversary
  branch, exactly as directed by the operator;
- shallow OFE 2 mutates the shared crop `rdmax`, affecting later elements;
  reversing processing order produces the same reference-dependent difference
  in both executables; this is compatibility, not independent root ownership;
- the uncapped canopy-one case causes a reference floating-point failure and a
  candidate explicit logarithm-domain failure. No numeric floor or clamp shift
  turns that invalid state into a successful history;
- fixture SHA verification protects the reference oracle from silent replacement.

## Retention and limitations

Evidence root: `/wc1/holdouts/mipa-native-r7-20261103/growth-qa`.
It retains `v1.log`, `v2.log`, representative stdout/stderr pairs, `receipt.json`
with probe binary hashes, and the complete copied `compiled-v2` directories with
`compiled-v2-manifest.json`. The first run stopped after 23 passes because a test
incorrectly demanded different OFE outputs even when a legitimate common cover
limit and shared-root state made them equal. Source parity already passed; the
assertion was replaced by direct identity and specifically discriminating tests.
No failed result was relabeled successful.

Coverage is active/inactive growth and selected reference root/cover transitions.
It does not exercise senescence via RESUP, initialization/cutting LAI, whole-model
residue burn-down, infiltration, observer neutrality, final binary pair, reports,
or complete service preparation. Those remain separate parent acceptance gates.
Ordinary GROW is not changed by this QA task. No production source, shared build,
installed binary, original project, or branch was modified by this reviewer.

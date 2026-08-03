# Hillslope Replay Fixtures

The local fixture root is:

```text
/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes
```

It contains burned, undisturbed, and high-severity inputs for H49 through H61.
These are the 13 hillslopes in the complete contributing area of channel
WEPP_ID 173 and include the contributing sets of channel WEPP_IDs 169 and 172.

The high-severity scenario is an additive forest counterfactual. H50-H56 and
H58-H61 use the canonical `forest high sev fire` management and texture-specific
soil coefficients. Its soils retain the canonical lookup values: `ksflag=0`,
`ksatadj=1`, `ksatfac=100`, and `ksatrec=0.3`. In this `wepp-forest` path,
`ksatadj=1` activates the forest-specific saturation-dependent conductivity
calculation independently of the soil-file `ksflag`. H49 (shrub/scrub) and H57
(deciduous forest) remain byte-identical undisturbed controls.

The fixture is hillslope-only. It deliberately excludes `pw0.*`, production
output, and watershed execution. The paired binary and its release metadata
sidecar are staged under `bin/`:

```text
bin/wepp_260803_hill
bin/wepp_260803_hill.json
```

Each scenario retains the runtime sidecars copied from its production run:

- `gwcoeff.txt`
- `snow.txt`
- `pmetpara.txt`
- `wepp_ui.txt`
- `chntyp.txt`
- `tc.txt`
- `chan.inp`

Some of these files are primarily associated with broader WEPPcloud run
contracts rather than a single hillslope invocation. They are retained so the
fixture does not silently change behavior through an incomplete run-directory
environment.

## Setup

```bash
docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/setup_hillslope_fixtures.sh
```

The setup script copies only H49-H61 inputs and sidecars. It excludes stale
production `.err` files and does not copy production output. It then invokes
`add_high_severity_hillslope_fixture.py` to rebuild the third scenario from the
undisturbed inputs. Rebuilding clears only the explicitly named
`high_severity/wepp/runs` and `high_severity/wepp/output` directories; the two
production-derived scenarios are untouched.

## Run

Run all 39 scenario/hillslope combinations:

```bash
docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/run_hillslope_fixtures.sh
```

Run one scenario or one hillslope:

```bash
# All burned hillslopes
docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/run_hillslope_fixtures.sh burned

# Burned H59 only
docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/run_hillslope_fixtures.sh burned 59

# All high-severity hillslopes
docs/investigations/2026-08-03-stevens-canyon-peak-flow-inversion/artifacts/run_hillslope_fixtures.sh high_severity
```

The staged `.run` files preserve the production output settings and
additionally enable WEPP's large-graphics output. Under
`wepp_260803_hill`, `H*.wat.dat` contains daily full-profile soil-water
storage, profile depth, porosity capacity, field-capacity storage, and
wilting-point storage. `H*.grph.dat` contains total soil water and soil water in
layers 1 through 10. The runner checks both contracts after every replay so a
run cannot be reported as successful with missing full-depth output.

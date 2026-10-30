# Runtime and configuration audit

Read-only source/metadata audit, 2026-10-30 UTC. No new candidate selected.

## Confirmed baseline distinctions

`Roads._prepare_roads_runs_workspace` copies shared baseline files, including
`wepp_ui.txt` where present. Native source `main.for:163–171` checks file presence;
format 9002 and the binary name do not independently activate that mode.

`Roads._resolve_legacy_soil_template_path` distinguishes rocked ditch (`tau=10`)
and paved inslope-bare/rutted (`tau=1`) from other configurations (`tau=2`).
Its soil builders divide road Ki and Kr by four for low/no traffic and set the
road marker to 65% for gravel or 95% for paved. Fill marker is `(buffer rock+65)/2`.
The actual emitted values and their physical interpretation must be preserved when
constructing a modern generated-soil candidate; generic bare/bare/forest replacement
alone is not a configuration-faithful baseline.

The actual production builders currently use legacy soil templates. Adopting a
modern generated-soil parameterization is a versioned Roads feature, not merely a
change to the general SSURGO writer. Existing projects must retain their current
version unless they explicitly adopt the new model.

FSWEPP2's configuration mapping and production Roads mapping are not interchangeable
by name alone. Actual Roads management selection uses inslope templates as the
source for its assembled arrangements. Production unrutted profiles may include
upstream and downstream landuse OFEs; the simplified FSWEPP three-OFE profile does
not automatically share that footprint or outlet. Use matched-reference geometry
and report the distinction rather than fitting away area/routing differences.

## Existing infrastructure

- `tests/roads/roads_matrix.py`: 516 production-builder cases; direct, two-OFE,
  rutted and upstream-landuse unrutted arrangements, geometry stress controls,
  shared runtime-file staging and readback.
- `tests/roads/roads_project.py`: disposable full-project upload/prepare/run checks.
- `tests/roads/data/site.json`: source geometry and shared-file provenance. The
  existing fixture binary is the site's `wepp_260409`, so reuse builders/data with
  an explicit `wepp_261026` execution identity; do not call its old report current
  validation for the new binary.
- `/workdir/fswepp2/parity-runs/wepproad`: original reference runs and inputs.
- `/workdir/fswepp2/api/wepproad.py`: original template, surface/traffic and geometry
  semantics. Retain the source commit and hashes before deriving references.

## Sampling evidence

Read generated source profiles only; no additional native outputs were inspected.
The two available source projects contain 32 distinct material profiles, of which
25 were not represented in the preceding studies. `design-v1.json` reserves six
additional profiles spanning lithic, low-conductivity mineral, and no-identified-
restriction cases plus the four surface texture families. Known loam/holdout material
is counted once. All other unused profiles remain reserved unless explicitly assigned
to a future panel before their outputs are examined.

## Immediate execution decisions

First reproduce the known negative-flux case with/without UI mode at unchanged
inputs. In parallel with interpretation, construct modern generated-soil candidates
that retain source material but apply supported configuration/role distinctions.
Compare generic-role, configuration-aware erosion and configuration-aware surface
hydraulic hypotheses under declared runtime settings. Any such screen remains
development evidence; no withheld soil output is needed to choose the first trials.

The product view will expose selected supported configuration parameters through
labeled inputs. Internal storage and the final field list remain undecided until
the physical model is supported. CSV editing is not required.

## Native input interpretation

Pinned native source `input.for:616` caps soil rock fraction at 85%, including the
legacy paved marker of 95%. The user view must distinguish written input from the
effective native range; 95% is not evidence that the engine models 95% rock volume.
No binary change is proposed.

`infile.for:1539` switches from original Penman to Penman-Monteith when
`pmetpara.txt` exists. `pmetcoef.for:54–80` matches crop names, then uses the first
record with a notice when no crop matches. The site fixture contains repeated
`Tah_4899` forest coefficients (Kcb 0.95, RAW fraction 0.8). Therefore copying that
file into a road experiment is an explicit ET treatment, not neutral runtime
plumbing. Final validation must retain and inspect the actual crop match/fallback
notices alongside project preparation settings. The UI-only screen intentionally
keeps this factor out of the first road-surface contrast.

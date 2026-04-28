# wepppyo3 Repositioning

**Status**: Complete
**Timezone**: UTC

## Overview

This package scopes a documentation repositioning pass for `/workdir/wepppyo3`. The codebase has outgrown the simple description "Rust/PyO3 extension modules for wepppy." It now acts as WEPPpy's owned native compute and interchange substrate: Python-callable Rust modules for hot geospatial, climate, WEPP/SWAT interchange, roads, MOFE, SBS, and visualization kernels where Python remains the orchestration layer.

The posture determined by the initial review is: **wepppyo3 is the WEPPpy native kernel and interchange substrate, not a miscellaneous accelerator bundle.** It should be documented as a contract-backed owned-stack layer with module maturity, release provenance, and evidence-bounded performance claims.

## Objectives

- Reframe `/workdir/wepppyo3/README.md` around the native-substrate posture.
- Separate production-critical native contracts from optional accelerators and incubating modules.
- Define boundaries between `wepppyo3`, Peridot, `weppcloud-wbt`, and Python orchestration.
- Add a canonical module registry that records purpose, WEPPpy callsites, maturity, release artifact, tests, and evidence status.
- Add release/provenance guidance for the canonical `release/linux/py312/wepppyo3/` package.
- Apply claim discipline to performance statements using `confirmed`, `inference`, and `hypothesis` labels.
- Align relevant WEPPpy references to the new canonical posture docs where appropriate.

## Scope

### Included

- Documentation updates in `/workdir/wepppyo3`, especially `README.md` and new docs under `/workdir/wepppyo3/docs/`.
- WEPPpy documentation references where they describe `wepppyo3` positioning, release, or native dependency posture.
- Work-package artifacts under `/workdir/wepppy/docs/work-packages/20260428_wepppyo3_repositioning/`.
- A communication kit with claim statement, figure specification, and metrics definitions.
- Validation of documentation links and package docs.

### Explicitly Out of Scope

- Runtime behavior changes in `wepppyo3` or WEPPpy.
- Rebuilding, replacing, or deploying `.so` release artifacts.
- Renaming public Python modules or changing import paths.
- Reclassifying module support status without evidence from tests, callsites, or operator decisions.
- Broad benchmark execution beyond collecting existing evidence and identifying gaps.

## Stakeholders

- **Primary**: WEPPpy and wepppyo3 maintainers.
- **Reviewers**: Native-kernel maintainers, WEPP/SWAT interchange maintainers, climate/raster workflow maintainers, documentation maintainers.
- **Security Reviewer**: Not required unless execution expands into release automation, deployment paths, binary signing, or external package distribution.
- **Informed**: Operators who deploy `release/linux/py312/wepppyo3/`, agents planning Rust hot-path migrations, and maintainers deciding whether Python fallback paths remain supported.

## Success Criteria

- [x] `wepppyo3` README front matter explains why the project matters and states the native-substrate posture clearly.
- [x] A canonical module registry distinguishes production-critical, optional, and incubating modules.
- [x] Docs define boundaries between `wepppyo3`, Peridot, `weppcloud-wbt`, Python orchestration, and one-off Rust crates.
- [x] Release/provenance docs identify `release/linux/py312/wepppyo3/` as the canonical deployable package and record version/provenance gaps.
- [x] Performance and adoption claims are labeled as `confirmed`, `inference`, or `hypothesis`.
- [x] WEPPpy references are aligned to the canonical docs where appropriate.
- [x] Scoped documentation validation passes.

## Determined Posture

`confirmed`: `/workdir/wepppyo3` is a Rust workspace with Python extension modules for climate, raster characteristics, SBS, WEPP interchange, SWAT interchange, SWAT utilities, roads flowpaths, watershed abstraction helpers, and WEPP visualization.

`confirmed`: WEPPpy imports `wepppyo3` across production climate, landuse, soils, roads, SWAT, WEPP interchange, MOFE, BAER/SBS, RHEM, RAP, Omni, and visualization paths.

`inference`: The codebase should be positioned as the native substrate that turns WEPPpy's Python orchestration into scalable, contract-backed scientific production workflows.

`hypothesis`: A clearer posture will reduce duplicate Python implementations, make release/provenance work easier, and help future agents decide when new Rust code belongs in `wepppyo3` versus Peridot or another owned component.

## Related Packages

- **Related**: [20260423_mofe_landuse_pair_counts_wepppyo3](../20260423_mofe_landuse_pair_counts_wepppyo3/package.md).
- **Related**: [20260423_mofe_map_wepppyo3](../20260423_mofe_map_wepppyo3/package.md).
- **Related**: [20260422_segmented_multiple_ofe_wepppyo3_pool](../20260422_segmented_multiple_ofe_wepppyo3_pool/package.md).
- **Related**: [20260320_rusle_r_static_hyetograph_api](../20260320_rusle_r_static_hyetograph_api/package.md).
- **Related**: [20260124_sbs_map_refactor](../20260124_sbs_map_refactor/package.md).
- **Related**: [20260426_peridot_documentation_repositioning](../20260426_peridot_documentation_repositioning/package.md).

## Timeline Estimate

- **Expected duration**: 1-2 focused documentation sessions.
- **Complexity**: Medium, because the codebase spans many domains and needs clear boundaries rather than more catalog prose.
- **Risk level**: Low for docs-only repositioning; medium if release/provenance or module maturity labels become normative for deployment.

## Security Impact and Review Gate

- **Security impact triage**: `none`
- **Dedicated security review required**: `no`
- **Triage rationale**: The scoped work is documentation and posture only. It does not change auth, public routes, secrets, binary release mechanics, deployment automation, subprocess execution, or external egress.
- **Security review artifact**: `N/A`

## Deliverables

- Updated `/workdir/wepppyo3/README.md` positioning.
- New `/workdir/wepppyo3/docs/module-registry.md`.
- New `/workdir/wepppyo3/docs/architecture-and-boundaries.md`.
- New `/workdir/wepppyo3/docs/release-provenance.md`.
- New `/workdir/wepppyo3/docs/claim-discipline.md`.
- WEPPpy reference alignment in `ARCHITECTURE.md`, `readme.md`, `wepppy/README.md`, and `docs/standards/dependency-evaluation-standard.md`.
- Work-package tracker, archived ExecPlan, and validation artifacts.

## Closure

**Closed**: 2026-04-28 17:38 UTC

**Outcome**: Completed as a docs-first repositioning. `wepppyo3` is now documented as WEPPpy's native kernel and interchange substrate, with explicit boundaries against Peridot, `weppcloud-wbt`, and WEPPpy orchestration. Canonical docs now capture module registry evidence, release provenance gaps, and claim discipline.

**Validation**: See `artifacts/2026-04-28_validation_summary.md`.

**Runtime impact**: None. No code, tests, release shared objects, or deploy artifacts were modified.

## Follow-up Work

- Binary provenance/version-stamping package if release artifacts need stronger traceability.
- Module maturity audit if maintainers want support labels to become operational policy.
- Benchmark evidence curation for high-visibility modules where current claims are scattered across package histories.

# Type Hints & Documentation Status

## Overview
The NoDb core controllers now follow the module documentation workflow (`docs/prompt_templates/module_documentation_workflow.prompt.md`). Each module was audited for three pillars:
- clear module-level documentation (Google-style narrative docstrings)
- comprehensive runtime type hints
- parallel `.pyi` stubs that mirror the exported surface

The table below captures the current status so we can see which modules are fully modernized and which still need attention.

## Current Coverage (NoDb Core)
| Module | Lines | Documentation | Type Hints | `.pyi` Stub | Notes |
| --- | ---: | --- | --- | --- | --- |
| `wepppy/nodb/core/climate.py` | 2914 | Complete | Complete | Present | Detailed module docstring, exhaustive annotations across 118 methods, `wepppy/nodb/core/climate.pyi` aligned. |
| `wepppy/nodb/core/soils.py` | 1357 | Complete | Complete | Present | Module docstring covers soil data pipeline; `.pyi` mirrors public API. |
| `wepppy/nodb/core/landuse.py` | 1288 | Complete | Complete | Present | Documented management workflows with examples; stub kept in sync. |
| `wepppy/nodb/core/watershed.py` | 1652 | Complete | Complete | Present | Updated docstring describes delineation backends; annotations propagated to helper classes; `.pyi` validated. |
| `wepppy/nodb/core/wepp.py` | 2706 | Complete | Complete | Present | Extensive module docstring outlining WEPP runs; `.pyi` captures enums, dataclasses, and controller surface. |
| `wepppy/nodb/core/topaz.py` | 250 | Complete | Complete | Present | Module docstring documents TOPAZ preprocessing workflow; annotations and stub remain in sync. |
| `wepppy/nodb/core/ron.py` | 897 | Complete | Complete | Present | Narrative docstring added for project bootstrap and external dependencies. |
| `wepppy/nodb/base.py` | 1880 | Complete | Partial | Missing | Docstring now documents NoDb philosophy; additional annotations and a `.pyi` stub still outstanding. |

## NoDb Mods
Quick audit across 68 modules under `wepppy/nodb/mods` shows only **5/68** files currently ship with module docstrings and just **6/45** executable modules achieve full annotation coverage (no `.pyi` stubs exist yet). The table highlights the most frequently used mods so we can prioritize doc and typing work.

| Module | Documentation | Type Hints | `.pyi` Stub | Notes |
| --- | --- | --- | --- | --- |
| `wepppy/nodb/mods/disturbed/disturbed.py` | Complete | Complete | Missing | New docstring outlines disturbance workflow; all public APIs annotated. |
| `wepppy/nodb/mods/path_ce/path_cost_effective.py` | Complete | Complete | Missing | Controller plus helpers (`data_loader`, `path_ce_solver`) now documented but still need stubs. |
| `wepppy/nodb/mods/path_ce/data_loader.py` | Complete | Complete | Missing | Loader is documented and typed; add stub once controller surface stabilizes. |
| `wepppy/nodb/mods/path_ce/path_ce_solver.py` | Complete | Complete | Missing | Solver utilities fully typed/documented; good target for `.pyi`. |
| `wepppy/nodb/mods/omni/omni.py` | Missing | Partial | Missing | Core analytics mod; only ~27% of functions carry annotations. |
| `wepppy/nodb/mods/ag_fields/ag_fields.py` | Missing | Sparse | Missing | Heavy raster processing file lacks docstring and most signatures. |
| `wepppy/nodb/mods/ash_transport/ash.py` | Complete | Complete | Present | Module docstring, annotations, and `ash.pyi` align with module documentation workflow. |
| `wepppy/nodb/mods/baer/baer.py` | Complete | Complete | Present | Added module docstring, full annotations, and `baer.pyi`; validated with stubtest (via `wctl`). |
| `wepppy/nodb/mods/rangeland_cover/rangeland_cover.py` | Complete | Complete | Present | Module docstring plus `rangeland_cover.pyi` align with the modernization workflow. |
| `wepppy/nodb/mods/rap/rap.py` | Missing | None | Missing | RAP data ingestion lacks documentation and typing. |
| `wepppy/nodb/mods/rap/rap_ts.py` | Missing | None | Missing | Time-series RAP utilities mirror the same gap as `rap.py`. |
| `wepppy/nodb/mods/revegetation/revegetation.py` | Missing | Partial | Missing | Some annotations exist (~36%); add docstring and complete typing. |
| `wepppy/nodb/mods/shrubland/shrubland.py` | Missing | None | Missing | Shrubland classifiers require full documentation and typing pass. |
| `wepppy/nodb/mods/treatments/treatments.py` | Missing | Sparse | Missing | Controller logic lightly annotated; needs docstring, typing, and stub. |
| `wepppy/nodb/mods/treecanopy/treecanopy.py` | Missing | None | Missing | Tree canopy mod is undoc'd and untyped; high priority for UI workflows. |
| `wepppy/nodb/mods/debris_flow/debris_flow.py` | Missing | None | Missing | Debris flow mod lacks docstring and type hints despite being user-facing. |
| `wepppy/nodb/mods/rhem/rhem.py` | Missing | None | Missing | RHEM summaries remain untyped and undocumented. |

## Highlights
- **Fully modernized controllers**  
  Climate, Soils, Landuse, Watershed, and Wepp now ship with descriptive module docstrings, saturated type hints, and synchronized `.pyi` stubs. Their docs explain primary workflows, enumerate key enums and dataclasses, and provide runnable examples that align with the template guidance.

- **Topaz and Ron documentation filled in**  
  These controllers now describe their responsibilities, required inputs, and downstream consumers. The docstrings align with the workflow template and give operators a clear launch checklist.

- **NoDb mods baseline in place**  
  Disturbed, PathCE, Ash Transport, and Rangeland Cover mods now include narrative docstrings; the aggregator (`wepppy.nodb.mods.__init__`) documents the lazy loader. The remaining high-traffic mods still need docstrings, annotations, and `.pyi` coverage.

- **Base infrastructure**  
  `wepppy.nodb.base` introduces a thorough docstring describing locking and Redis integration, yet its runtime annotations remain incomplete and no `.pyi` stub exists. It should be the next target so downstream controllers can rely on typed primitives.

## Recommended Validation Workflow
Whenever a module is updated, run the validation sequence from the template:
```bash
wctl run-stubtest wepppy.nodb.core.<module_name>
wctl run-pytest tests/nodb/test_type_hints.py
python tools/sync_stubs.py  # keep stubs/wepppy/ in sync with inline .pyi files
```

## Outstanding Work
1. Expand type hints in `wepppy/nodb/base.py`, create a matching `.pyi`, and validate with `stubtest`.
2. Author module docstrings and add annotations for priority mods: `omni`, `ag_fields`, and `rhem`.
3. Introduce `.pyi` stubs for NoDb mods once runtime signatures stabilize; Disturbed, PathCE, and BAER now have complete annotations.
4. Re-run `uk2us` on touched files to maintain American English spellings and repeat the validation workflow once base typing is complete.

## References
- `docs/prompt_templates/module_documentation_workflow.prompt.md`
- `AGENTS.md` (Type Stub Management)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [mypy documentation](https://mypy.readthedocs.io/)

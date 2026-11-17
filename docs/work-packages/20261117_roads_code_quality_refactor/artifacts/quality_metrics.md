# Roads code quality measurements

Measured 2026-11-17 UTC against baseline
`96555f2f95326350d2d7007c19327378ea831ab0` and candidate HEAD
`5ef26481068cada863371d34b2d62ffd2c6e77fa`. The
[machine-readable receipt](quality_metrics.json) binds all 18 production files by
SHA-256 and records interpreter, analyzer and Radon identity.

## Reproduction and interpretation

From the candidate checkout root:

```bash
/usr/bin/python docs/work-packages/20261117_roads_code_quality_refactor/artifacts/scripts/quality_metrics.py > docs/work-packages/20261117_roads_code_quality_refactor/artifacts/quality_metrics.json
```

The interpreter is `/usr/bin/python`, Python 3.12.3, with Radon 6.0.1 from
`/usr/lib/python3/dist-packages/radon/__init__.py`. No dependency was installed.
Earlier measurements using the default `python3` could not import Radon; that
interpreter resolves to a separate Linuxbrew installation. Discovering this
existing interpreter makes complexity measurable. It does not turn earlier null
results into passes or establish that the environment changed after the restart.

SLOC and maximum physical function span use
`tools/code_quality_observability.py`; complexity is the maximum reported Radon
score for each file. A dash means the extracted module did not exist at baseline,
not zero baseline complexity or wholly new behavior. The aggregate comparison
covers the original facade versus the final facade plus its 17 extracted modules;
unchanged existing Roads collaborators are excluded from both sides.

Root guidance makes these metrics observe-only. A smaller facade is useful, but
the total source grew from 5,907 to 7,739 SLOC: **+1,832, or 31.0%**. Explicit
compatibility wrappers and execution stage parameters account for this tradeoff.
The review makes no claim that total source or actual broad-handler count fell.

## Per-file measurements

| Module | Baseline SLOC | Candidate SLOC | Baseline max span | Candidate max span | Baseline max CC | Candidate max CC | Candidate broad handlers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `roads.py` | 5907 | 1888 | 2069 | 269 | 158 | 25 | 10 |
| `_constants.py` | — | 122 | — | 7 | — | 3 | 0 |
| `_inputs.py` | — | 770 | — | 140 | — | 44 | 1 |
| `_prepare.py` | — | 151 | — | 81 | — | 8 | 0 |
| `_soil_inputs.py` | — | 349 | — | 106 | — | 25 | 0 |
| `_management_inputs.py` | — | 241 | — | 96 | — | 27 | 0 |
| `_slope_inputs.py` | — | 210 | — | 43 | — | 15 | 0 |
| `_spatial.py` | — | 231 | — | 103 | — | 27 | 0 |
| `_queries.py` | — | 562 | — | 157 | — | 61 | 2 |
| `_parameterization_support.py` | — | 100 | — | 29 | — | 14 | 0 |
| `_pass_routing.py` | — | 141 | — | 46 | — | 7 | 0 |
| `_native_runner.py` | — | 52 | — | 52 | — | 7 | 0 |
| `_reporting.py` | — | 207 | — | 163 | — | 24 | 0 |
| `_execution.py` | — | 233 | — | 49 | — | 8 | 0 |
| `_point_source.py` | — | 869 | — | 149 | — | 12 | 2 |
| `_unrutted_execution.py` | — | 341 | — | 116 | — | 10 | 2 |
| `_unrutted_planning.py` | — | 723 | — | 122 | — | 22 | 0 |
| `_unrutted_native.py` | — | 549 | — | 90 | — | 3 | 2 |

The broad-handler inventory counts bare catches and catches naming `Exception`
or `BaseException`, including tuple catches. Both baseline and candidate have 19
handlers across the compared scope. Boundary annotations reduce unsuppressed
inventory findings, not the number of exception handlers.

## Residual hotspots and rationale

The receipt independently compares each of these moved function bodies against
the original facade and confirms AST identity:

- `_inputs._validated_params_payload`: CC 44 before and after. Required input
  validation branches were preserved; their debt was relocated, not resolved.
- `_queries.query_segment_detail`: CC 40 before and after, 157 physical lines.
  It still combines profile, manifest and routing detail assembly.
- `_queries._last_parameterization_readback`: CC 61 before and after. Artifact
  admission and diagnostic branches remain concentrated in one reader.
- `_reporting._regenerate_roads_report_resources`: CC 24 before and after,
  163 physical lines. Publication ordering and readiness checks remain coupled.

`Roads.run_roads_wepp` remains 269 physical lines and the facade remains above the
1,200-SLOC triage band. Its retained lifecycle, persistence and publication
boundaries explain the residual size. Execution is now staged across focused
modules; no extracted execution function exceeds 149 lines. Keep these remaining
hotspots as targeted follow-ups with branch/artifact characterization. Further
splitting only to cross a metric band would add navigation and adapter overhead
without demonstrated quality benefit.

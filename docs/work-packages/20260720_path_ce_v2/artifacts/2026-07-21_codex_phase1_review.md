# Codex Phase 1 Review — Findings and Dispositions

**Date**: 2026-07-21 02:40 UTC
**Reviewer**: Codex (MCP, read-only sandbox), dispatched by Roger's direction; thread `019f8201-1018-7e41-b30b-47d54e8b0728`
**Scope**: Phase 1 vendored modules, seam code, parity tests, fixtures, ADR-0023
**Reviewer verdict**: request changes — vendored algorithm bodies confirmed faithful to upstream `4e3b4a6`; two seam contracts found unimplemented/untested.
**Disposition evidence class**: Executional — all fixes verified by rerunning the suite in the weppcloud container (`/opt/venv` pytest): **59 passed** (36 path_ce incl. 12 new seam tests + 23 adjacent) after remediation.

| # | Sev | Finding (condensed) | Disposition |
|---|-----|---------------------|-------------|
| 1 | High | Acre cost seam not implemented: `area_sum` is hectares (m²×1e-4); solver multiplied ha × $/acre — upstream's unit defect propagated while ADR claimed acres. Verified: golden cost $207,714.38 = 167.85 ha × 2475 × 0.5. | **Accepted, fixed.** `convert_area_to_acres()` (×2.47105) applied in the wrapper seam (`prepare_solver_inputs`); faithful core stays hectare-based. Core-parity tests certify upstream behavior on ha; new seam tests certify acre costs formula-derived from the frame (`test_wrapper_costs_are_acre_based`, subset variant). ADR §3 corrected. |
| 2 | High | Treatment↔reduction-column pairing is positional in the core; reordered/subset treatment configs silently mis-assign costs to another treatment's effects (upstream QMD aligns at the caller; that behavior wasn't brought over). | **Accepted, fixed.** `_align_frame_and_treatments()`: validates configured labels against frame reduction columns (error lists available labels), prunes unconfigured reduction columns, realigns vectors to column order, checks Sddc/Sdyd family order consistency. `SolverResult` gained a `treatments` field reporting the aligned order. Tests: order invariance, subset support, unknown-label error, prune/reorder unit test. ADR §4 amended. |
| 3 | Med | `normalize_treatment` accepts `None`→`"None"`/NaN labels and non-finite numerics; wrapper validated only vector lengths. | **Accepted, fixed.** Presets reject null/float labels and require `math.isfinite`; wrapper (`prepare_solver_inputs`) enforces finite treatment metadata + thresholds, unique labels, length match. Negative/NaN/inf tests added. |
| 4 | Med | Parity oracle weaker than claimed: counts/sums instead of full outputs; `upstream_commit` not asserted. | **Accepted, fixed.** Goldens regenerated from unmodified upstream (`make_goldens_enriched.py`, pinned venv) with full ordered payloads: untreatable id sets, increase-class ids, complete final-Sdyd table, per-treatment cost-vector sums, reduction-threshold sum. Tests assert all of it plus `upstream_commit == 4e3b4a6`. |
| 5 | Med | No filtered (slope/severity) parity coverage despite Phase 0 plan requiring one filtered case. | **Accepted, fixed.** Upstream-generated goldens added: honeyed slope-only and slope+severity solver cases (both exercised the secondary path with materially different selections: 68 and 23 sites); austere slope-filtered data-prep frame golden with a not-equal-to-unfiltered guard. |
| 6 | Med | ADR described grouped severity as "area-dominant"; code uses most-frequent-by-row-count with largest-code tie-break. | **Accepted, fixed (docs).** ADR §5 and the validation-run artifact corrected; noted area-weighting would be a ratifiable behavior change, not a fidelity edit. |
| 7 | Low | New modules lacked `__all__` per NoDb conventions. | **Accepted, fixed.** `__all__` added to all three modules. |
| 8 | Low | Fixtures placed in `tests/fixtures/` vs documented `tests/data/<area>/` convention (tests/AGENTS.md §Adding New Tests). | **Accepted, fixed.** Moved to `tests/data/path_ce/`; test paths updated; pre-existing `tests/fixtures/` left as found. |

## Notes

- Finding 1's numeric verification was reproduced independently before accepting (group 12: 1,678,500 m² → 167.85 ha → $208,214.38 with fixed cost, matching the CBC objective).
- Findings 1+2 mean the pre-review "Phase 1 complete" claim was accurate for **faithfulness** but not for the **seam contracts** — the parity suite was green while certifying upstream's unit defect. The two-layer test split (core parity on hectares vs seam tests on acres) makes that distinction structural.
- Wrapper acre conversion scales variable costs uniformly (×2.47105) but not fixed costs, so selections can in principle differ from upstream on datasets where fixed-vs-variable tradeoffs bind; on all three golden datasets the austere selections were verified unchanged, and seam tests assert selection stability there.
- No findings rejected.

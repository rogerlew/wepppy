# Audit accepted Daymet M3 assessment

## Purpose / Big Picture

Provide a reproducible verdict on the current Dead Horse Creek Daymet assessment and its relationship to observed 2021 debris flows. This is an audit of saved results, not model calibration.

## Progress

- [x] (2026-09-17 UTC) Establish scope and accepted attempt.
- [x] Independently verify climate lineage and all numerical result rows.
- [x] Compare historical climate assessments and published event window.
- [x] Verify report through normal login and prove source/result preservation.
- [x] Write findings, validate documentation, and close package.

## Surprises & Discoveries

The stored generic climate mode is ObservedPRISM, while the owner catalog is observed_daymet and the retained source is daymet_1980-2024.parquet. The owner also retains a CLIGEN convergence warning. Source tracing confirms df_to_prn mutates the input before build_observed_daymet overwrites the retained parquet, leaving converted units under original labels. The correctly scaled CLI remains consistent with PRN and publisher rainfall.

## Decision Log

2026-09-17 UTC, Codex: keep this audit read-only and separate from completed repair and GridMET packages. Existing accepted outputs permit full arithmetic and report verification without another run.

## Outcomes & Retrospective

All 14,025 result rows pass independent arithmetic; all three browser durations are current, five downloaded artifacts match, and 858 protected files are unchanged. Publisher 2021 rainfall matches the retained PRN-quantized values. August 5–12 is dry in both Daymet and CLI, preventing an event validation claim. The audit exposed mislabeled source-parquet units and retained CLIGEN convergence warning; findings record follow-up scope without altering runtime behavior.

## Context and Orientation

Run root: /wc1/runs/th/thespian-cleanness. Accepted attempt: 8190121c8a4b45e1952861e74d909693. Results and predictor rasters live under postfire_debris_flow/attempts/<id>; published tables and manifest live directly under postfire_debris_flow. Climate lives under climate/. Earlier GridMET attempt f493a714df9d4fbfbfd4370c46ad54f8 and synthetic PRISM attempt 0a34c96cd0dc4e6bb7bb7780d8f8915b supply retained comparisons. The paper is https://nhess.copernicus.org/articles/24/2093/2024/.

## Plan of Work

Adapt the existing read-only numerical audit into artifacts/audit_saved.py, pin the current attempt, and protect CLI content alongside raster, NoDb, and table files. Add artifacts/compare_daymet.py to trace source daily rainfall, quantify differences from prior design tables, and export the paper window. Adapt artifacts/browser_audit.cjs for authenticated current report checks. Write artifacts/findings.md with evidence and limitations.

## Concrete Steps

From /home/workdir/wepppy, run `wctl exec weppcloud python /workdir/wepppy/docs/work-packages/20260917_dead_horse_daymet_audit/artifacts/audit_saved.py` and the sibling compare_daymet.py. Run `node docs/work-packages/20260917_dead_horse_daymet_audit/artifacts/browser_audit.cjs`. Expect arithmetic assertions and browser checks to pass, with all published hashes matching and no protected changes. Run `wctl doc-lint --path docs/work-packages/20260917_dead_horse_daymet_audit`.

## Validation and Acceptance

All available rows must satisfy independent M3 logistic equations and depth/intensity conversions within 1e-12; event dates/rainfall and partial-duration ranks must match source CLI. Browser payloads must identify the pinned accepted M3 attempt as current for each duration, and authenticated downloads must match pinned hashes. Report source daily rainfall and modeled subdaily limitations separately. Confirm protected file hashes and accepted manifest remain unchanged.

## Idempotence and Recovery

Scripts write only adjacent audit artifacts. If accepted state changes concurrently, stop pinning conclusions to current status and retain the mismatch evidence. Repeating checks does not rebuild climate or mutate results; preserve initial hashes and failed/intermediate evidence.

## Artifacts and Notes

Retain JSON, CSV, browser text, screenshot, and command logs under artifacts. Do not retain login credentials or session tokens.

## Interfaces and Dependencies

Use existing pandas, numpy, rasterio, report read interface, and Playwright from repository environments. No new dependencies or runtime interfaces.

Revision: initial plan, 2026-09-17 UTC; scoped to the user's Daymet re-audit request.

Revision: closeout, 2026-09-17 UTC; all audit acceptance checks complete, with findings retained rather than silently expanding into a runtime repair. Final evidence is artifacts/closeout.json; documentation lint reports four files, zero errors/warnings.

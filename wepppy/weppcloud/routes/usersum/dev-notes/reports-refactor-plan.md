# Reports Refactor Plan

This note outlines a staged refactor to modernise the `wepppy.wepp.stats`
module by consolidating report logic under `wepppy.wepp.reports`, aligning
class naming, and documenting the reporting interface.

---

## Phase 1 – Package Relocation (Wepp Stats → Wepp Reports)

1. **Create `wepppy/wepp/reports/` namespace**
   - ✅ All former `wepppy.wepp.stats` modules now live under
     `wepppy/wepp/reports/` with updated relative imports.

2. **Update imports**
   - Replace all `from wepppy.wepp.stats...` references with
     `from wepppy.wepp.reports...` across the codebase (core modules,
     Flask routes, CLI scripts, tests, etc.).
   - Keep temporary shims if necessary (e.g., re-export key classes from
     the old path) until downstream changes are complete.

3. **Regression checks**
   - Run the targeted report tests (`tests/wepp/reports/...`) and the
     integration suite that exercises report routes to ensure nothing
     regresses after the package rename.

---

## Phase 2 – Class Naming Conventions

1. **Rename report classes**
   - ✅ All `ReportBase` subclasses now carry the `Report` suffix
     (`AverageAnnualsByLanduseReport`, `ChannelWatbalReport`, etc.).

2. **Adjust instantiation sites**
   - Update all call sites to use the new class names (Flask routes,
     `nodb.core.wepp`, scripts, tests).
   - Provide deprecated aliases in `wepppy/wepp/reports/__init__.py` if
     needed for a transition period.

3. **Verify interface consistency**
   - Ensure the renamed classes still expose the same public attributes
     (`header`, `units_d`, `__iter__`, etc.) so the templates continue to
     render correctly.

---

## Phase 3 – Cache Location & Standardisation

1. **Consolidate cache storage**
   - ✅ `ReportCacheManager` standardises caches at
     `<run>/wepp/reports/cache/` with version metadata.

2. **Cache invalidation strategy**
   - Add helper utilities to version cached assets (e.g., embed schema
     version metadata) so future schema changes can safely invalidate old
     caches.

3. **Configuration hooks**
   - Provide a small abstraction (e.g., `ReportCacheManager`) for
     constructing cache paths and reading/writing parquet files, reducing
     duplication across report classes.

---

## Phase 4 – Developer Documentation

1. **ReportBase guide**
   - ✅ `reports/reportbase-guide.md` captures the shared helpers and
     expectations for `ReportBase` implementations.

2. **Report catalogue**
   - ✅ `reports/report-catalog.md` outlines purpose, datasets, caches and
     surfaces for each report class.

3. **Update onboarding docs**
   - Reference the new reports documentation from developer onboarding
     material so future contributors know where to look for report
     guidance.

---

## Additional Ideas

- Introduce a small test harness that exercises every report class with a
  synthetic interchange directory, ensuring that everything loads and
  caches without the full WEPP runtime. (A stub now lives at
  `wepppy/wepp/reports/harness.py` with a smoke test in
  `tests/wepp/reports/test_harness_stub.py`.)
- Build shared helpers to reduce boilerplate: a `ReportQueryContext`
  wrapper for DuckDB/catalog setup, streamlined cache utilities, and
  unit metadata extraction from parquet schemas (so we no longer rely on
  column-name hacks to embed units).
- Provide a `to_dataframe()` helper (and optional CSV export) via a mixin
  or base implementation so individual reports no longer need to spell
  out export logic.

This phased approach keeps the refactor manageable while improving
consistency and documentation across the reporting stack.

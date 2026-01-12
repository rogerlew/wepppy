# Mini Work Package: Remove remaining jQuery script imports
Status: Completed (2026-01-02)
Last Updated: 2026-01-03
Primary Areas: `wepppy/weppcloud/templates`, `wepppy/weppcloud/routes`, `wepppy/weppcloud/static/js`, legacy HTML fixtures

## Objective
Remove jquery.js imports and migrate remaining jQuery usage to vanilla JS while keeping existing UI behavior intact.

## Scope
- Templates and route templates that still import jquery.js.
- JS modules referenced by those templates that rely on jQuery.
- HTML fixtures/tests that still load jquery (keep or replace intentionally).

## Non-goals
- Rewriting third-party libraries unless a vanilla replacement is selected.
- Editing generated assets in `wepppy/weppcloud/static/ui-lab/` (change `static-src` instead).

## Plan
- [x] Audit jQuery usage in JS (search for `$(...)`, `jQuery`, `$.ajax`, `$.on`, etc.).
- [x] For each jquery import, map dependent scripts/features before removal.
- [x] Replace DOM/event/AJAX usage with vanilla JS or existing helpers.
- [x] Remove jquery import tags once dependencies are migrated.
- [x] Run targeted smoke/tests (`wctl run-npm test`, relevant pytest if needed).

## Completed
- [x] `wepppy/weppcloud/routes/rq/job_dashboard/templates/dashboard.htm` - Remove jquery import; replace jQuery AJAX and DOM hooks with vanilla JS (2026-01-02). Removed entirely in 2026-01-03 (RQ job dashboard Pure migration).
- [x] `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/routes/batch_runner/templates/layout.j2` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/templates/reports/_page_container.htm` - Remove jquery import; convert unitizer handlers to vanilla JS; drop bootstrap bundle dependency (2026-01-02).
- [x] `wepppy/weppcloud/templates/reports/_base_report.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/templates/locations/joh/index.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/templates/locations/portland/index.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/templates/locations/seattle/index.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/templates/locations/spu/index.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/templates/bounds_ws_viewer.htm` - Remove jquery/datatable imports; convert jquery usage to vanilla JS; drop bootstrap bundle dependency (2026-01-02).
- [x] `wepppy/weppcloud/templates/combined_ws_viewer.htm` - Remove jquery/datatable imports; convert jquery usage to vanilla JS; drop bootstrap bundle dependency (2026-01-02).
- [x] `wepppy/weppcloud/templates/combined_ws_viewer2.htm` - Remove jquery/datatable imports; convert jquery usage to vanilla JS; drop bootstrap bundle dependency (2026-01-02).
- [x] `wepppy/weppcloud/routes/pivottable.py` - Replace jQuery PivotTable UI with vanilla JS controls; pivottable is deprecated in favor of D-Tale (2026-01-02).
- [x] `wepppy/weppcloud/templates/combined_ws_viewer_url_gen.htm` - Remove jquery import and bootstrap bundle (2026-01-02).
- [x] `wepppy/weppcloud/templates/controls/edit_csv.htm` - Remove jquery import; replace `$.post` with `fetch` (2026-01-02).
- [x] `wepppy/climates/climatena_ca/tests/api6_test.htm` - Remove jquery import; replace `$.ajax` with `fetch` (2026-01-02).
- [x] `wepppy/weppcloud/templates/user/profile.html` - Remove jquery import; replace jQuery handlers with vanilla JS `fetch` (2026-01-02).
- [x] `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm` - Remove jquery import (2026-01-02).
- [x] `wepppy/weppcloud/routes/run_0/templates/run_page_bootstrap.js.j2` - Remove jQuery-dependent TOC initialization (2026-01-02).
- [x] `wepppy/weppcloud/static-src/package.json` - Remove jQuery/DataTables dependencies from the static build pipeline (2026-01-02).
- [x] `wepppy/weppcloud/static-src/scripts/build.mjs` - Stop copying jQuery/DataTables/bootstrap-toc into `dist/vendor`; drop unused Bootstrap JS bundle now that jQuery is gone (2026-01-03).
- [x] `wepppy/weppcloud/static/vendor/jquery/` + `wepppy/weppcloud/static/vendor/datatables/` + `wepppy/weppcloud/static/vendor/bootstrap-toc/` - Remove unused jQuery-based vendor artifacts (2026-01-02).
- [x] `wepppy/weppcloud/static/js/jquery-3.1.1.min.js` - Remove legacy jQuery asset (2026-01-02).
- [x] `wepppy/weppcloud/static/js/input-unit-converters.js` - Replace jQuery data/event/value handling with vanilla DOM utilities (2026-01-02).
- [x] `wepppy/weppcloud/templates/bounds_ws_viewer.htm` - Avoid double-decoding URLSearchParams values; parse JSON safely (2026-01-02).
- [x] `wepppy/weppcloud/templates/combined_ws_viewer.htm` - Avoid double-decoding URLSearchParams values; parse JSON safely (2026-01-02).
- [x] `wepppy/weppcloud/templates/combined_ws_viewer2.htm` - Avoid double-decoding URLSearchParams values; parse JSON safely (2026-01-02).
- [x] `wepppy/weppcloud/static-src/README.md` - Update vendor-sources example after bootstrap-toc removal (2026-01-02).
- [x] `wepppy/weppcloud/static-src/vendor-sources/bootstrap-toc/` - Remove deprecated bootstrap-toc sources (2026-01-02).

## Handoff
- Status: jQuery imports and usage removed across templates/routes/controllers; static build pipeline no longer ships jQuery/DataTables/bootstrap-toc or the Bootstrap JS bundle; legacy vendor artifacts deleted.
- Verification: `wctl build-static-assets` (development) and `wctl run-npm test` (PASS 50 suites / 293 tests). Warnings observed were the usual VM Modules/console noise in Jest output.
- Notes: `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm` left untouched per request; TOC bootstrap now uses vanilla navigation, so reintroducing bootstrap-toc would require restoring vendor sources + init; pivottable UI is simplified and the route is deprecated in favor of D-Tale.

## Script import inventory (94 total, 0 jquery)
Legend: [jquery] [generated] [tests]
- [ ] `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm:24` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm:25` - `<script src="{{ url_for('static', filename='js/console_utils.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm:26` - `<script src="{{ url_for('static', filename='js/status_stream.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/archive_dashboard/templates/rq-archive-dashboard.htm:27` - `<script src="{{ url_for('static', filename='js/archive_console.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/batch_runner/templates/create.htm:6` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/batch_runner/templates/layout.j2:19` - `<script src="{{ site_prefix }}/static/js/controllers-gl.js"></script>`
- [ ] `wepppy/weppcloud/routes/batch_runner/templates/manage_pure.htm:6` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/browse/templates/browse/data_table.htm:13` - `<script src="/weppcloud/static/js/sorttable.js"></script>`
- [ ] `wepppy/weppcloud/routes/browse/templates/browse/dss_file.htm:13` - `<script src="/weppcloud/static/js/sorttable.js"></script>`
- [ ] `wepppy/weppcloud/routes/browse/templates/browse/markdown_file.htm:12` - `<script src="{{ static_url('js/status_stream.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/command_bar/templates/command-bar.htm:325` - `<script type="text/javascript" src="{{ url_for('command_bar.static', filename='vendor/marked.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/command_bar/templates/command-bar.htm:326` - `<script type="text/javascript" src="{{ url_for('command_bar.static', filename='command-bar.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/diff/templates/comparer.htm:424` - `<script defer src="{{ url_for('diff.static', filename='diff_viewer.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm:134` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm:135` - `<script src="{{ url_for('static', filename='js/console_utils.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm:136` - `<script src="{{ url_for('static', filename='js/status_stream.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm:141` - `<script src="{{ cap_asset_base_url }}/widget.js" defer></script>`
- [ ] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm:142` - `<script src="{{ cap_asset_base_url }}/floating.js" defer></script>`
- [ ] `wepppy/weppcloud/routes/fork_console/templates/rq-fork-console.htm:144` - `<script src="{{ url_for('static', filename='js/fork_console.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/pivottable.py:24` - `<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/4.1.2/papaparse.min.js"></script>`
- [ ] `wepppy/weppcloud/routes/readme_md/templates/readme_editor.htm:7` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/readme_md/templates/readme_view.htm:7` - `<script src="{{ url_for('static', filename='js/status_stream.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:31` - `<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:35` - `<script src="https://unpkg.com/@deck.gl/widgets@^9.0.0/dist.min.js"`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:38` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:39` - `<script src="{{ url_for('static', filename='js/preflight.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:40` - `<script src="{{ url_for('static', filename='js/input-unit-converters.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:273` - `<script src="{{ url_for('static', filename='js/tinyqueue.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:274` - `<script src="{{ url_for('static', filename='js/polylabel.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:275` - `<script src="{{ url_for('static', filename='js/underscore.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:276` - `<script src="{{ url_for('static', filename='js/colormap.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:277` - `<script src="{{ url_for('static', filename='js/geotiff.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm:278` - `<script src="{{ url_for('static', filename='js/plotty.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/run_sync_dashboard/templates/rq-run-sync-dashboard.htm:143` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}"></script>`
- [ ] `wepppy/weppcloud/routes/usersum/templates/usersum/layout.j2:10` - `<script src="{{ static_url('js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/static/ui-lab/index-light.html:8` - `<script type="module" crossorigin src="./assets/light-CJBhTeht.js"></script>` [generated]
- [ ] `wepppy/weppcloud/static/ui-lab/index.html:8` - `<script type="module" crossorigin src="./assets/main-OvI7e7dC.js"></script>` [generated]
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:15` - `<script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:234` - `<script type="text/javascript" src="{{ url_for('static', filename='js/spin.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:235` - `<script type="text/javascript" src="{{ url_for('static', filename='js/tinyqueue.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:236` - `<script type="text/javascript" src="{{ url_for('static', filename='js/polylabel.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:237` - `<script type="text/javascript" src="{{ url_for('static', filename='js/underscore.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:238` - `<script type="text/javascript" src="{{ url_for('static', filename='js/colormap.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:239` - `<script type="text/javascript" src="{{ url_for('static', filename='js/geotiff.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:240` - `<script type="text/javascript" src="{{ url_for('static', filename='js/plotty.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:241` - `<script type="text/javascript" src="{{ url_for('static', filename='js/leaflet-spin.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/bounds_ws_viewer.htm:242` - `<script type="text/javascript" src="{{ url_for('static', filename='js/leaflet-geotiff.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/cap_gate.htm:43` - `<script src="{{ cap_asset_base_url }}/widget.js" defer></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:15` - `<script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:619` - `<script type="text/javascript" src="{{ url_for('static', filename='js/spin.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:620` - `<script type="text/javascript" src="{{ url_for('static', filename='js/tinyqueue.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:621` - `<script type="text/javascript" src="{{ url_for('static', filename='js/polylabel.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:622` - `<script type="text/javascript" src="{{ url_for('static', filename='js/underscore.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:623` - `<script type="text/javascript" src="{{ url_for('static', filename='js/colormap.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:624` - `<script type="text/javascript" src="{{ url_for('static', filename='js/geotiff.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:625` - `<script type="text/javascript" src="{{ url_for('static', filename='js/plotty.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:626` - `<script type="text/javascript" src="{{ url_for('static', filename='js/leaflet-spin.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer.htm:627` - `<script type="text/javascript" src="{{ url_for('static', filename='js/leaflet-geotiff.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer2.htm:33` - `<script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer2.htm:34` - `<script src="{{ url_for('static', filename='js/glify-browser.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/combined_ws_viewer2.htm:35` - `<script src="{{ url_for('static', filename='js/leaflet-glify-layer.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/controls/edit_csv.htm:3` - `<script src="https://bossanova.uk/jspreadsheet/v4/jexcel.js"></script>`
- [ ] `wepppy/weppcloud/templates/controls/edit_csv.htm:5` - `<script src="https://jsuites.net/v4/jsuites.js"></script>`
- [ ] `wepppy/weppcloud/templates/gl_dashboard.htm:1059` - `<script src="https://unpkg.com/geotiff@2.1.3/dist-browser/geotiff.js"></script>`
- [ ] `wepppy/weppcloud/templates/gl_dashboard.htm:1060` - `<script src="{{ static_url('js/colormap.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/gl_dashboard.htm:1061` - `<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>`
- [ ] `wepppy/weppcloud/templates/gl_dashboard.htm:1062` - `<script src="{{ static_url('js/gl-dashboard.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/huc-fire/index.html:8` - `<script src="{{ url_for('static', filename='vendor/leaflet/leaflet.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/interfaces.htm:603` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/interfaces.htm:608` - `<script src="{{ cap_asset_base_url }}/widget.js" defer></script>`
- [ ] `wepppy/weppcloud/templates/interfaces.htm:609` - `<script src="{{ cap_asset_base_url }}/floating.js" defer></script>`
- [ ] `wepppy/weppcloud/templates/landing.htm:9` - `<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>`
- [ ] `wepppy/weppcloud/templates/landing.htm:10` - `<script src="https://unpkg.com/maplibre-gl@3.6.0/dist/maplibre-gl.js"></script>`
- [ ] `wepppy/weppcloud/templates/locations/portland/index.htm:159` - `<script async src="https://www.googletagmanager.com/gtag/js?id=UA-116992009-1"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:121` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:122` - `<script src="{{ url_for('static', filename='js/report_csv.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:135` - `<script type="text/javascript" src="{{ url_for('static', filename='js/tinyqueue.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:136` - `<script type="text/javascript" src="{{ url_for('static', filename='js/polylabel.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:137` - `<script type="text/javascript" src="{{ url_for('static', filename='js/underscore.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:138` - `<script type="text/javascript" src="{{ url_for('static', filename='js/copytext.js') }}?20180904"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_base_report.htm:139` - `<script type="text/javascript" src="{{ url_for('static', filename='js/sorttable.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_page_container.htm:15` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_page_container.htm:72` - `<script type="text/javascript" src="{{ url_for('static', filename='js/tinyqueue.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_page_container.htm:73` - `<script type="text/javascript" src="{{ url_for('static', filename='js/polylabel.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_page_container.htm:74` - `<script type="text/javascript" src="{{ url_for('static', filename='js/underscore.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_page_container.htm:75` - `<script type="text/javascript" src="{{ url_for('static', filename='js/copytext.js') }}?20180904"></script>`
- [ ] `wepppy/weppcloud/templates/reports/_page_container.htm:76` - `<script src="/weppcloud/static/js/sorttable.js"></script>`
- [ ] `wepppy/weppcloud/templates/reports/storm_event_analyzer.htm:75` - `<script type="module" src="{{ static_url('js/storm-event-analyzer/main.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/reports/wepp/daily_streamflow_graph.htm:8` - `<script src="{{ url_for('static', filename='js/d3.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/reports/wepp/observed.htm:8` - `<script src="{{ url_for('static', filename='js/d3.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/ui_showcase/component_gallery.htm:682` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}"></script>`
- [ ] `wepppy/weppcloud/templates/user/runs2.html:806` - `<script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>`
- [ ] `wepppy/weppcloud/templates/user/runs2.html:807` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`
- [ ] `wepppy/weppcloud/templates/user/usermod.html:120` - `<script src="{{ url_for('static', filename='js/controllers-gl.js') }}" defer></script>`

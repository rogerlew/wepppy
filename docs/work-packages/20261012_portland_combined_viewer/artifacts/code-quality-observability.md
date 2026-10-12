# Candidate code quality telemetry

Candidate `c1e919210`; base `d75460acc`. Observe-only, not a release gate.
Python cyclomatic complexity is unavailable because radon is not installed;
SLOC/function length and JavaScript complexity were measured.

The existing red template-test module grows by two SLOC to supply required
render context; its largest function is unchanged. New yellow JavaScript
complexity is confined to explicit complete-data validation and the browser
acceptance matrix. Keeping those checks adjacent makes missing/optional values
and complete joins reviewable; no additional abstraction is warranted here.

## Changed files

- Files analyzed: `14`; highest severity red: `1`, yellow: `2`; worsened metric entries: `7` (exceptions: `0`, actionable: `7`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/weppcloud/routes/test_combined_watershed_viewer_security.py` | `python` | `green` | python_file_sloc 123->192 (worsened, green)<br>python_function_len 30->30 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_pure_controls_render.py` | `python` | `red` | python_file_sloc 4521->4523 (worsened, red)<br>python_function_len 181->181 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_combined_viewer_generator.py` | `python` | `green` | python_file_sloc n/a->25 (new, green)<br>python_function_len n/a->15 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/test_combined_viewer_preparation.py` | `python` | `green` | python_file_sloc n/a->84 (new, green)<br>python_function_len n/a->16 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/combined_viewer_preparation.py` | `python` | `green` | python_file_sloc n/a->186 (new, green)<br>python_function_len n/a->69 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/combined_watershed_viewer_generator.py` | `python` | `green` | python_file_sloc 80->55 (improved, green)<br>python_function_len 101->30 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/combined_watershed_viewer.py` | `python` | `green` | python_file_sloc 108->148 (worsened, green)<br>python_function_len 43->46 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/routes/locations.py` | `python` | `green` | python_file_sloc 142->144 (worsened, green)<br>python_function_len 32->32 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/static-src/tests/smoke/combined-viewer.spec.js` | `javascript` | `yellow` | js_file_sloc n/a->329 (new, green)<br>js_cc n/a->18 (new, yellow) |
| `wepppy/weppcloud/static/js/gl-dashboard/__tests__/combined-viewer.test.js` | `javascript` | `green` | js_file_sloc n/a->53 (new, green)<br>js_cc n/a->2 (new, green) |
| `wepppy/weppcloud/static/js/gl-dashboard/combined-viewer-data.js` | `javascript` | `yellow` | js_file_sloc n/a->77 (new, green)<br>js_cc n/a->21 (new, yellow) |
| `wepppy/weppcloud/static/js/gl-dashboard/combined-viewer.js` | `javascript` | `green` | js_file_sloc n/a->124 (new, green)<br>js_cc n/a->9 (new, green) |
| `wepppy/weppcloud/static/js/gl-dashboard/map/controller.js` | `javascript` | `green` | js_file_sloc 33->35 (worsened, green)<br>js_cc 1->2 (worsened, green) |
| `wepppy/weppcloud/utils/portland_collections.py` | `python` | `green` | python_file_sloc n/a->30 (new, green)<br>python_function_len n/a->12 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |

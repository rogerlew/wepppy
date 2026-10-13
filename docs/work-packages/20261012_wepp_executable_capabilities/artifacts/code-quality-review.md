# CBEXEC-01 code quality observation

## Changed Files

- Files analyzed: `22`; highest severity red: `8`, yellow: `5`; worsened metric entries: `18` (exceptions: `0`, actionable: `18`)

| File | Lang | Highest | Key Metric Deltas |
| --- | --- | --- | --- |
| `tests/microservices/test_rq_engine_schema_defaults_routes.py` | `python` | `red` | python_file_sloc 1626->1659 (worsened, red)<br>python_function_len 99->99 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/microservices/test_rq_engine_wepp_routes.py` | `python` | `red` | python_file_sloc 1531->1532 (worsened, red)<br>python_function_len 92->92 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_builder_snapshot.py` | `python` | `green` | python_file_sloc 118->135 (worsened, green)<br>python_function_len 25->25 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_project_config_registry_serializer.py` | `python` | `green` | python_file_sloc 537->564 (worsened, green)<br>python_function_len 33->33 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_single_input_policy.py` | `python` | `green` | python_file_sloc 46->58 (worsened, green)<br>python_function_len 11->10 (improved, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/nodb/test_wepp_binary_policy.py` | `python` | `green` | python_file_sloc n/a->119 (new, green)<br>python_function_len n/a->23 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/wepp_runner/test_binary_capabilities.py` | `python` | `green` | python_file_sloc n/a->90 (new, green)<br>python_function_len n/a->15 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `tests/weppcloud/routes/test_run_0_openet_admin_gate.py` | `python` | `red` | python_file_sloc 1268->1230 (improved, red)<br>python_function_len 101->101 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/schema_defaults_routes.py` | `python` | `red` | python_file_sloc 5291->5329 (worsened, red)<br>python_function_len 2243->2243 (unchanged, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/microservices/rq_engine/wepp_run_payload.py` | `python` | `red` | python_file_sloc 600->565 (improved, green)<br>python_function_len 293->258 (improved, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/registry.py` | `python` | `red` | python_file_sloc 687->696 (worsened, yellow)<br>python_function_len 228->229 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/resolver.py` | `python` | `red` | python_file_sloc 523->531 (worsened, green)<br>python_function_len 171->176 (worsened, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/config_builder/schema.py` | `python` | `green` | python_file_sloc 155->157 (worsened, green)<br>python_function_len 7->7 (unchanged, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/core/wepp_input_parser.py` | `python` | `yellow` | python_file_sloc 148->150 (worsened, green)<br>python_function_len 147->148 (worsened, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/locales/capability_graph.py` | `python` | `yellow` | python_file_sloc 896->901 (worsened, yellow)<br>python_function_len 119->119 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/project_config_capabilities.py` | `python` | `yellow` | python_file_sloc 661->661 (unchanged, yellow)<br>python_function_len 147->147 (unchanged, yellow)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/single_input_policy.py` | `python` | `green` | python_file_sloc 77->91 (worsened, green)<br>python_function_len 25->35 (worsened, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/nodb/wepp_binary_policy.py` | `python` | `green` | python_file_sloc n/a->37 (new, green)<br>python_function_len n/a->25 (new, green)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/controllers_js/__tests__/config_builder.test.js` | `javascript` | `green` | js_file_sloc 698->761 (worsened, green)<br>js_cc 5->5 (unchanged, green) |
| `wepppy/weppcloud/controllers_js/config_builder.js` | `javascript` | `yellow` | js_file_sloc 594->616 (worsened, green)<br>js_cc 19->19 (unchanged, yellow) |
| `wepppy/weppcloud/routes/run_0/run_0_bp.py` | `python` | `red` | python_file_sloc 2451->2401 (improved, red)<br>python_function_len 415->396 (improved, red)<br>python_cc n/a->n/a (n/a, unknown) |
| `wepppy/weppcloud/static-src/tests/smoke/wepp-executable-capabilities.spec.js` | `javascript` | `yellow` | js_file_sloc n/a->233 (new, green)<br>js_cc n/a->17 (new, yellow) |


Observe-only report against `b4c950ced`. Python complexity measurement was unavailable
(`radon` is not installed). Existing large schema/registry/resolver modules gained
bounded fields and calls to a shared selection policy; no structural refactor is
needed for this change. The schema module gains38 source lines to keep field
enums, full model tuples and freshness identity consistent. Run-page and grouped
payload code shrink by removing frozen-binary checks. Builder JS maximum
complexity is unchanged. New shared policy and reader logic are bounded; no new
service, dependency, cache or privilege is introduced.

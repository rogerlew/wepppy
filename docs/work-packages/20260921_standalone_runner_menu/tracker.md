# Tracker

- Base: `f97dab846`.
- Decision and canonical amendment accepted; both independent prereviews pass.
- Checkpoint committed before source/test changes: `ed3ee034e`.
- Pre-fix real-registry regression fails for Dev because both runners appear.
- Three-line menu filter implemented; 335 tests pass (6 warnings, 19.53 seconds):
  `wctl run-pytest tests/weppcloud/routes/test_feature_registry_runtime.py tests/weppcloud/routes/test_pure_controls_render.py --maxfail=1`.
- Real registry matrix covers 100 role/backend/include-all/active-state cases;
  real header rendering confirms absent runner toggles and retained Omni.
- Final independent review `/root/runner_menu_contract1`: PASS, no findings;
  test-completion condition met. Registry, routes, state and ordering unchanged.
- Scoped docs lint, broad-exception delta-zero gate and diff check pass.
- Full numerical suite and npm gates omitted: no numerical, template, JS,
  persistence or transport logic changed. No live restart, push or deployment.

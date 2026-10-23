# Validation

Checkpoint: `5194433d0`, committed before the one-literal production edit.

- `wctl run-pytest tests/weppcloud/routes/test_roads_bp.py -q`: 21 passed,
  four dependency deprecation warnings, 9.00 seconds.
- `wctl exec weppcloud python docs/work-packages/20261023_roads_activation_messaging/artifacts/check_message.py`:
  passes for both mismatch directions, both agreeing states and absent controller.
  Executes the actual guard and standard exception factory with supplied controller
  states. No persistence/filesystem boundary changes or project mutations.
- Initial readback expected the bare message; the shared exception factory retains
  `RuntimeError: ` before the message. Corrected the one-off assertion to reflect
  unchanged production response handling; rerun passed. Existing traceback details
  and HTTP 500 remain.
- Package, Roads specification and user-guide Markdown lint: pass.
- Scoped `git diff --check`: pass.
- Full repository rerun omitted for this text-only change; no executable decision,
  model behavior, state mutation, auth, response schema or frontend logic changes.
- No production deployment or project repair performed.

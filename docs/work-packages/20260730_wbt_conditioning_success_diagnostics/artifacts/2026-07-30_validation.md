# Validation - WBT Conditioning Success Diagnostics

## Producer

- WBT commits: `bd8e0e4` (four sidecars) and `ef69a38` (exclusive temp
  creation and residual-count correction), both pushed to `origin/master`.
- Installed binary SHA-256:
  `491f892aabf83a6ecde7639473f94c63004935b275f3d846f9eddaee1c5cb14f`.
- `cargo check -p whitebox-tools-app`: pass.
- `cargo test -p whitebox-tools-app conditioning_diagnostics`: 2 passed.
- `cargo build --release -p whitebox-tools-app`: pass.
- Four incident-fixture executions produced valid sidecars. Direct Fill
  measured a maximum raise of `379.02203369140625 m`.

## Consumer and Presentation

- Focused topo/RQ/job-status suite: 93 passed.
- Channel and Channel GL controller suite: 35 passed.
- Full frontend suite: 105 suites and 753 tests passed.
- Frontend lint and generated controller bundle: pass.
- RQ dependency graph: current.
- Changed broad-exception gate: pass, net delta `-1`.
- Python compilation and diff whitespace check: pass.
- Package, schema, and user-guide documentation lint: pass.

The full 5,803-test Python suite is deferred to the production-promotion gate;
it is not claimed as local completion evidence.

Independent final governance and operations/security reviews passed with no
unresolved high- or medium-severity findings.

## Completion-summary overwrite follow-up

- Live root job: `ea906fe3-bb11-4268-bfe7-b63a38274614`.
- Producer child: `f26c3083-b3ff-4aaf-bfb1-198d633f863b`.
- Aggregate `jobstatus` correctly returned the validated fill diagnostic with
  maximum raise `379.22729369142326 m`.
- The controller wrote that summary before `channel.show()` replaced it with
  layer-loading status. The conformance fix preserves the validated summary as
  the terminal status after the asynchronous layer refresh.

Operator review subsequently corrected the presentation boundary: the durable
channel Summary Panel, rather than the transient status panel, owns this text.
The report route revalidates the sidecar on every render, so the diagnostic
ships with the summary report independently of RQ metadata retention.

- Channel-report route/template regressions: 3 passed.
- Focused watershed route suite: 6 passed.
- Full frontend suite: 105 suites and 755 tests passed.
- Frontend lint, generated controller bundle, documentation lint, and changed
  broad-exception enforcement: pass.

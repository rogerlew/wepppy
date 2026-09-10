# Validation and publication

Implementation commits: WEPPpy `9e1c48f4d`; native source `125edc1`, deployed
release `d6641ab`. Contract ancestry is recorded in baseline.md.

Confirmed gates:

- Rust fmt/check: pass; library tests: 8 passed.
- Canonical installed raster Python suite: 43 passed.
- Project-grid/stacker/ordinary+MOFE tests: 28 passed, including real soil files.
- Existing MOFE/WeppPrepService focused tests passed with the initial combined
  21-case suite; broad-suite coverage passed.
- Configured geo stubtest and check-test-stubs: pass.
- Broad-exception enforcement: pass, no added broad handlers.
- Changed documentation lint and spelling preview: pass; root AGENTS size gate: pass.
- Local final restart and fresh-process native hashes: pass.
- Independent full-grid mean and all 1259 generated OFE comparison: pass.
- Native scan timing and process memory: recorded in kernel_validation.md.
- Independent correctness and security code findings: all medium findings closed.

Full watershed/postprocessing job tree and final output verification passed: 15 jobs, 505 hillslopes, 1259 OFEs, 25 tables.
`wctl run-pytest tests --maxfail=1`: **8174 passed, 72 skipped**, 3110 warnings, 900.45 seconds.
Both validated revisions pushed and remote-verified; see [publication receipt](publication.json).
Raw logs remain at `/tmp/kslast-area-weighted-20260909/`; unrelated preexisting
code-quality-report.json and code-quality-summary.md were not overwritten.

Observed code-quality deltas: shared kslast collaborator is 89 source lines and
its preparation function 67 lines (green bands). Existing Wepp and prep-service
source lengths decrease. raster_stacker grows from 115 to 129 function lines
(yellow) to validate sentinel representability and actual resampling/conversion
before output creation; the explicit-option path is kept together so publication
cannot precede validation. No unrelated hotspot refactoring was introduced.

## Owner QA disposition

Root Codex reviewed maintainability and test quality separately from independent
correctness/security review. Pass: one shared domain collaborator removes both
centroid loops; Rust retains a generic API; no new dependency or queue wiring.
Tests use real rasters and actual soil parser/writers, with an executor seam only
for orchestration ordering; direct containment and lock tests exercise the real
boundary. Legacy no-map/worker arguments remain covered. The broad suite passes.
The observed stacker size increase is justified above. Remaining limits are the
explicit projected-grid contract and workload-bounded performance evidence;
no claim of exhaustive malformed-raster or extreme-size coverage is made.

Validated release/evidence SHAs: WEPPpy `252bac87998a3c2a900b64bb4495f0078466e04b`; wepppyo3 `d6641abfe3a932826b0e161494c7eafd0ba4e8d8`. The final WEPPpy documentation-closeout commit is also pushed and its local/remote tip equality checked at handoff.

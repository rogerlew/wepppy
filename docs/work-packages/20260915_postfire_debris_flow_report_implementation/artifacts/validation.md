# Implementation validation

Date: 2026-09-16 UTC. Development host: forest. Contract ancestor: `ac4deb681`.
No production deployment, model rerun, source acquisition or push was performed.
Existing development Gunicorn workers were reloaded after building the controller
bundle with the canonical container command; no worker jobs were submitted.

## Automated gates

- Reader/routes/actual rendered shell: 44 passed, 14.39s. Tests use actual
  accepted parquet/NoDb fixtures, filesystem boundaries and Jinja inheritance.
- Existing results/runtime-M3/integration/publication selection: 105 passed.
- Canonical postfire archive/restore: 1 passed, 21 unrelated deselected; proves
  retained source, failed-attempt and output records survive archive/restore.
- Focused controller: 21 passed, including real UnitizerClient API, response
  races, local error retries, explicit fraction exports and off-page selection.
- Full frontend lint/tests: pass; 112 suites, 898 tests, 8.072s.
- Full Python `wctl run-pytest tests --maxfail=1`: 8,672 passed, 103 skipped,
  3,128 warnings, 1114.47s. No failures.
- `wctl check-test-stubs`: pass. Broad-exception changed-file enforcement:
  5 production Python files, zero unsuppressed catches, pass.
- Scoped Markdown lint/spelling preview and `git diff --check`: pass; repeat
  after final closeout edits. Code-quality observability is nonblocking;
  final committed-HEAD report analyzes 9 files: zero red, two yellow. The
  existing results-reader function length is unchanged; new report controller
  complexity 16 is slightly above yellow, localized to presentation/state
  handling with direct tests. No speculative abstraction was added to lower it.
  Python complexity is unavailable because radon is absent; no dependency added.
  Captured CSV retains original browser CRLF bytes; staged whitespace validation
  uses `git -c core.whitespace=cr-at-eol diff --cached --check` for those artifacts.

The full Python run started before the final rendered-shell regression was
added; the final 44-test focused run covers that added case. Frontend final
reruns cover all late controller conformance fixes.

## Genuine saved assessments

| Saved project | Model/source | Unique events | Evidence |
| --- | --- | ---: | --- |
| overpriced-sprawl | M1 / NOAA | 9,150 | m1_saved_validation.json; browser_m1_verified/ |
| pfdf-m3-validation-20260914b | M3 / CLI | 30 | m3_saved_validation.json; browser_m3_verified/ |

M3 is an existing controlled development validation basin, not a full-scale
storm-catalog performance claim. Both saved runs truthfully show stale under
existing engine-source identity checks after the additive results reader edit.
No freshness bypass or recomputation was used.

Direct Arrow comparisons validate all three duration pages, saved design and
inverse tables, unique counts and attachment hashes. Saved checks protect
23/28 files including accepted-attempt artifacts. Browser checks independently
protect 18/23 root/module files and reject every run mutation except the exact
existing recorder/events observability endpoint. Session/recorder effects are
not scientific or project-state changes and are not claimed absent.

Browser tasks include keyboard event/scenario selection, all three event
durations, paging, local SI/English switching, precise displayed CSV, no-store
fixed artifacts, normal authorized browse/download, desktop/narrow and three
theme screenshots. Controlled first/last-detail and paging 503 responses test
local retry and coherent retained results without causing server failures.
Final rebuilt-browser records pass at 04:05 UTC, including off-page selected
event retention through a duration reset and subsequent paging back to the event.

## Failed/intermediate evidence and limitations

browser_m1/browser.json retains the first live detail-render failure.
browser_m1_final/ retains the later passive Unitizer persistence failure.
Both led to fixes and regression tests, not waived assertions. The harness's
first M3 ordinary-browse attempt used config rather than the run's actual
disturbed9002_wbt; correcting the harness required no route change.
The final verification directories are repeatable latest-pass evidence.

UX review is expert agent review, not a human study or accessibility certificate.
Its optional low-priority muted-help text polish remains deferred. No new
scientific thresholds, parameterization defaults, dependencies or schema changes.

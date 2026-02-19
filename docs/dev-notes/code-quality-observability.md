# Code Quality Observability (Observe-Only)

## Purpose

This repository uses an observe-only code-quality model. The goal is high signal with low friction: surface complexity and file-size risk early, but do not block delivery based on thresholds alone.

This is intentionally a telemetry system, not a hard gate. Improvements are made opportunistically when touching nearby code or during dedicated maintenance windows.

## Policy

- CI publishes code-quality summaries and artifacts for pull requests and scheduled audits.
- Thresholds are severity bands (`green`, `yellow`, `red`) used for visibility and triage only.
- Exceeding a threshold does not fail the workflow.
- Reviewers should focus on changed-file deltas first, then persistent hotspot files.
- If a touched file worsens materially, include brief rationale in the review or PR description.

## Current Severity Bands

The baseline was derived from repository percentiles and tuned to reduce noise in a large legacy codebase.

| Metric | Yellow | Red |
| --- | ---: | ---: |
| `python_file_sloc` | 650 | 1200 |
| `python_function_len` | 80 | 150 |
| `python_cc` | 15 | 30 |
| `js_file_sloc` | 1500 | 2500 |
| `js_cc` | 15 | 30 |

Notes:
- `python_cc` and `js_cc` are cyclomatic complexity maxima.
- JavaScript scope is source-focused (`controllers_js`, `static-src`, `static/js/gl-dashboard`, `tools`) and intentionally excludes generated/vendor trees.

## Local Usage

Run from repo root:

```bash
python3 tools/code_quality_observability.py \
  --base-ref origin/master \
  --json-out /tmp/code-quality-report.json \
  --md-out /tmp/code-quality-summary.md
```

- `--base-ref` enables changed-file deltas (`improved`, `unchanged`, `worsened`).
- Outputs are always generated in observe-only mode.

## CI Workflow

Workflow: `Code Quality Observability`

- Triggered on pull requests and weekly schedule.
- Publishes:
  - `code-quality-summary.md` to job summary
  - `code-quality-report.json` + markdown as artifacts
- On pull requests, posts/updates a sticky summary comment for reviewers.

## Review Integration

Code review should include a code-quality pass:

1. Read the changed-file section of the observability report.
2. Note any `red` or worsened metrics in touched files.
3. Decide whether to:
   - make a small opportunistic cleanup now, or
   - capture a short deferred cleanup note in the PR.

The objective is steady trend improvement without blocking feature delivery.

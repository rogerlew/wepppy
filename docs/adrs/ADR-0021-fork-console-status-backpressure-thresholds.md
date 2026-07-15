# ADR: Fork Console Status Backpressure Thresholds

Status: Accepted
Date: 2026-07-15
Review Date: 2026-07-29

## Context

A production project fork completed successfully in RQ after 56 minutes 53 seconds, but a background fork-console tab continued draining high-volume rsync messages and delayed terminal-state presentation. Fixing the incident requires explicit operational thresholds for worker heartbeats, retained browser messages, batched DOM rendering, and bounded failure output.

## Decision

Fork rsync will emit one replaceable heartbeat at most every 10 seconds while the subprocess is active. The fork console will retain at most 400 append-only messages. Shared StatusStream DOM rendering will batch updates with a 100 millisecond interval and will defer hidden-page rendering until visibility returns. Worker stdout and stderr diagnostic tails will each retain at most 200 lines for final summary/error reporting.

Important lifecycle, trigger, warning, and error messages receive retention preference over ordinary log lines, but the total browser log remains hard bounded.

## Decision Provenance

Decision Venue: Codex work-package execution conversation, 2026-07-15 10:15 PDT
Participants Present: WEPPpy requesting maintainer, Codex
Decision Owner(s): WEPPpy requesting maintainer
Implementer(s): Codex

## Change Summary

Previously, rsync used `-av --progress`, every drained output line was published, the fork console retained up to 3,000 messages, and StatusStream rewrote the entire retained log for every frame. There was no worker heartbeat interval, render-batch interval, or bounded subprocess diagnostic tail.

The new behavior uses a 10-second heartbeat, 400 retained fork-console messages, 100-millisecond render batching, and 200-line stdout/stderr tails. Raw per-file and per-progress output is not published.

## Rationale

Ten seconds provides visible proof of activity without producing material traffic during hour-scale copies. A 400-entry log retains stage history while bounding join/DOM costs. A 100-millisecond render batch keeps interactive feedback responsive while coalescing bursts. Two hundred diagnostic lines per stream are sufficient for rsync context while preventing unbounded worker memory growth.

## Alternatives Considered

1. Keep raw output and only optimize DOM rendering - rejected because it preserves unnecessary Redis/WebSocket traffic and browser queues.
2. Poll job status with no copy heartbeat - rejected because `started` alone gives weak feedback during long copies.
3. Publish parsed byte-level progress - deferred because parsing rsync progress adds complexity and continued high-rate updates without a demonstrated user need.
4. Retain 3,000 entries - rejected because the incident showed that the existing volume is not operationally safe.

## Consequences

Users no longer see individual copied filenames or byte counters. They receive stage transitions, elapsed-time heartbeats, final summary information, and explicit failure diagnostics. The browser and worker have bounded memory/rendering behavior. Threshold changes require updating this ADR, tests, and work-package documentation.

## Evidence

- `docs/work-packages/20260715_fork_console_status_backpressure/`
- Production job `299b8d3c-bdca-42cd-abe2-506b6b410a8e` on wepp1.
- `wepppy/rq/project_rq_fork.py`
- `wepppy/weppcloud/controllers_js/status_stream.js`

## Risk and Rollback Notes

The primary risk is that sparse telemetry feels inactive or bounded tails omit an early diagnostic line. Review repeated user reports of unclear activity or incomplete rsync failures during the 14-day observation window. Rollback should adjust one documented threshold or restore a bounded summary field; do not restore raw per-line publication without new load evidence and review.

## Implementation Notes

Threshold constants must have descriptive names and direct regression coverage. Heartbeats are presentation hints only; `/jobstatus/<job_id>` remains authoritative for lifecycle state.

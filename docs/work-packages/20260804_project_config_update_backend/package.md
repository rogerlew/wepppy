# Project Config Update Backend (WP08)

**Status**: Complete (2026-08-26)
**Initiative branch**: `feature/project-owned-config`
**Starting revision**: `3754fbf2d`
**Security impact**: high; dedicated review required

## Objective

Implement the dormant project-owned configuration update backend: read-only
availability and preview, authenticated explicit apply, an asynchronous RQ
merge-only job, and crash-recoverable config/manifest persistence. WP09 owns
the run-header and modal UI; WP10 owns fork/archive coordination.

## Compatibility and Regression Plan

This package mutates project-scoped `config.cfg` and `config-manifest.json`
only after an authenticated owner/Admin/Root apply request. Before editing,
compatibility is fixed as follows: availability and preview never write;
ordinary `config_get_*` misses never write; legacy or invalid-manifest projects
remain unchanged; existing flattened values are byte-semantically preserved;
only missing attributes from the recorded, still-active parent chain may be
added; and one invalid, ambiguous, overwrite, removal, or secret-bearing item
rejects the complete batch. Tests must validate generated run artifacts as
well as pure resolver output.

Concurrency regression coverage must exercise same-delta deduplication,
preview staleness, failures before and between replacements, deterministic
journal recovery, and worker-time authorization. Queue wiring changes require
the RQ dependency catalog and graph gate.

## Owned Requirements

PC-14 and PC-15: N-006 through N-010, N-012, N-079, N-080, N-084, N-085,
N-094; R-018 through R-025, R-027, R-028, and R-050.

## Success Criteria

- [x] Availability and preview resolve the complete registered merge without writes.
- [x] Apply requires owner/Admin/Root at enqueue and worker execution.
- [x] A current preview enqueues one canonical RQ job; stale or unavailable previews do not.
- [x] The job adds all and only missing registered values and preserves existing values.
- [x] Config and manifest recover to one consistent state across crash points.
- [x] Concurrency, provenance, secret, queue-graph, docs, and full-suite gates pass.

## Rollout

The update backend is dormant by default. WP09 and WP10 must pass before WP11
Forest promotion; no deployment default is enabled here.

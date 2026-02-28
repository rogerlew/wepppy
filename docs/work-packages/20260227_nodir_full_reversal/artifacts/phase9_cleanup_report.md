# Phase 9 Vestigial Complexity Cleanup Report

- Date: 2026-02-28
- Scope: post-Phase-8 behavior-preserving complexity reduction.

## What Changed

1. `wepppy/weppcloud/utils/helpers.py`
- Centralized primary-vs-legacy run path selection.
- Centralized omni child path resolution (including legacy candidate fallback).
- Kept existing behavior, but reduced duplicated conditional branches.

2. `wepppy/runtime_paths/wepp_inputs.py`
- Consolidated retired/no-op compatibility flag handling into explicit helper functions.
- Kept existing compatibility signatures for callers that still pass legacy kwargs.

3. `wepppy/runtime_paths/{__init__,fs,projections,mutations}.py`
- Updated module framing text to directory-only operational wording.

4. `tests/weppcloud/utils/test_helpers_paths.py`
- Added regression tests for omni scenario primary-hit and legacy-hit path-exists branches.

## Retained (Intentional)

- Legacy run root fallback (`/geodata/weppcloud_runs`) remains active for backward compatibility.
- Legacy omni archive-link compatibility in shared input wiring remains active.
- Compatibility kwargs in runtime path APIs remain accepted to avoid callsite breakage.

## Validation Summary

- Targeted helper/runtime-path tests: pass.
- Full test suite: pass.
- Broad-exception enforcement: pass.
- Code-quality observability: pass (observe-only).
- Work-package doc lint: pass.
- Subagent closure: unresolved high/medium = `0`.

## Outcome

Phase 9 cleanup is complete for the scoped vestigial surfaces, with no contract removals and no test regressions.

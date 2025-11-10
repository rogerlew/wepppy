# Work Package: Profile Playback Code Coverage Mapping

| | |
|---|---|
| **Status** | `In Progress` |
| **Creation Date** | `2025-11-09` |
| **Completion Date** | |
| **Stakeholders** | `@rogerlew`, `@GitHub-Copilot`, `@gpt-5-codex` |
| **Work Package Lead** | `@gpt-5-codex` |

## 1. Scope & Objectives

### 1.1. Problem Statement
The `wepppy` repository has 19+ profile playback tests that exercise different backend workflows. However, there is no visibility into which Python modules, classes, or functions each profile actually uses. This makes it difficult to assess test coverage, identify redundant tests, or find gaps in testing.

### 1.2. Objectives
- Instrument WEPPcloud so every profile playback request can opt-in to backend Python coverage tracing without modifying individual routes/controllers.
- Produce a reliable mapping between playback profiles and the Python files/classes/functions they execute, backed by both dynamic coverage data and a static symbol catalog.
- Ship a reporting pipeline that emits per-profile coverage artifacts plus cross-profile summaries (matrix, leaderboards, gap reports) every night.
- Keep developer ergonomics high: tracing must be entirely opt-in, documented, and runnable locally through `wctl` wrappers.

### 1.3. Success Criteria
- Each nightly playback run uploads a `{profile_slug}.coverage` artifact plus JSON/HTML summaries derived from it.
- A static symbol inventory (class/function definitions with line spans) exists under `docs/work-packages/20251109_profile_playback_coverage/artifacts/`.
- The nightly workflow publishes:  
  1. `profile -> symbols` coverage matrix,  
  2. `symbol -> profiles` reverse index,  
  3. a gap report listing uncovered modules.  
  These outputs live under `artifacts/` and attach to the CI run.
- Playback tracing adds **≤25%** wall-clock time to the slowest profile job in CI (baseline gathered before rollout).
- Documentation in `AGENTS.md` and `tests/README.md` tells contributors how to run, inspect, and interpret profile coverage locally.

## 2. Deliverables

1. **Conceptual Framework Document** (`notes/01-conceptual-framework.md`) — living design reference (complete).
2. **Instrumentation**  
   - Flask coverage middleware + app factory wiring.  
   - RQ worker bootstrap + enqueue helpers that propagate the profile slug.  
   - Dedicated `coverage.profile-playback.ini`.
3. **Playback Client Enhancements** — `wctl playback --trace-code` flag, header injection, env toggles.
4. **Reporting Scripts** — `tools/profile_coverage/generate_reports.py` (per-profile outputs) and `tools/profile_coverage/build_matrix.py` (cross-profile aggregation) plus the static symbol inventory builder.
5. **CI/CD Integration** — updated workflow generator, regenerated playback workflows, nightly aggregator job, artifact uploads, and retention policy.
6. **Documentation** — updates to `AGENTS.md`, `tests/README.md`, and a new `docs/dev-notes/profile-coverage.md` quick-start.

## 3. Scope Guardrails

- **In Scope:** Python backend execution triggered by playback (Flask routes, NoDb controllers, RQ workers, orchestrators). Only line coverage; branch data captured but not yet surfaced.
- **Out of Scope:**  
  - Front-end/JavaScript coverage.  
  - Native/Fortran/Rust binaries called from Python.  
  - Manual test sessions (non-playback) unless they explicitly set `X-Profile-Trace`.  
  - Call-count profiling (`cProfile`, `sys.setprofile`) and runtime hot-path analysis.
- **Assumptions:**  
  - Profile playback already runs deterministically in CI.  
  - `coverage.py` remains available inside the Docker images and base virtualenvs.  
  - Nightly jobs can upload up to ~250 MB of artifacts without hitting quotas.

## 4. Milestones

| Milestone | Target | Exit Criteria |
|---|---|---|
| **M1 – Instrumentation Ready** | 2025‑11‑16 | Middleware + worker hooks merged, basic local profile run produces `{slug}.coverage`. |
| **M2 – Reporting Toolchain** | 2025‑11‑20 | Symbol inventory committed, per-profile JSON/HTML generator + matrix builder verified on sample data. |
| **M3 – Nightly CI Rollout** | 2025‑11‑27 | GitHub Actions emits per-profile artifacts + aggregated matrix, docs updated. |
| **M4 – Stabilization** | 2025‑12‑04 | Performance budget validated, flaky coverage gaps resolved, work package closed or moved to maintenance. |

## 5. References & Links

- **Conceptual Framework**: [notes/01-conceptual-framework.md](./notes/01-conceptual-framework.md)
- **AGENTS.md (Work Package Guide)**: `../../../../AGENTS.md#creating-a-work-package`
- **Root Project Tracker**: `../../../../PROJECT_TRACKER.md`

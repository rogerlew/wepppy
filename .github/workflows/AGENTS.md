# GitHub Workflows - Agent Development Guide

## Authorship
**This document is maintained by AI agents. Update when workflow patterns, available resources, or CI/CD infrastructure changes.**

---

## Overview

This directory contains GitHub Actions workflows for CI/CD automation. Agents working on workflow development have access to the full CodeQL Action source code for reference and debugging.

---

## Workflow Generation System

Most workflows are **generated** from specs under `.github/forest_workflows/` using the builder script `scripts/build_forest_workflows.py`. Do **not** edit the files under `.github/workflows/` directly; they are overwritten every time the builder runs.

### Key Inputs

| File | Purpose |
| --- | --- |
| `.github/forest_workflows/bootstrap.yml` | Shared env + setup/cleanup steps (checkout, `docker/.env`, wctl shim, redis cleanup) |
| `.github/forest_workflows/*.yml` | Workflow-specific specs (docs-quality, npm-tests, etc.) |
| `.github/forest_workflows/playback-profiles.yml` | Single source of truth for nightly profile runs/forks/archives (title, PT schedule, description, profile slug, artifact name, etc.) |

### Builder Script (`scripts/build_forest_workflows.py`)

The script:
1. Loads bootstrap + spec files (and playback profiles).
2. Generates every workflow under `.github/workflows/` with a warning header.
3. Rebuilds the “Dev Server Nightly Profile Tests” table in `readme.md` from the playback data.
4. Supports a `--check` mode for CI validation (non-zero exit if workflows/readme are stale).

### Editing Workflow Logic

1. Update the relevant spec in `.github/forest_workflows/` (or add an entry to `playback-profiles.yml` for nightlies).
2. Run `scripts/build_forest_workflows.py` from the repo root.
3. Inspect the diff under `.github/workflows/` + `readme.md`.
4. For validations (e.g., in CI), use `scripts/build_forest_workflows.py --check`.

### Why keep the builder under `scripts/`?

`scripts/build_forest_workflows.py` is used repo-wide (not just by GitHub Actions), so it intentionally lives in `scripts/` alongside other tooling. Keeping it there avoids special-casing `.github/` during linting or packaging.

---

## Available Resources

### CodeQL Action Source Code

**Location:** `/workdir/codeql-action`

The complete source code for the `github/codeql-action` repository is available locally for agent reference. This enables:
- **Deep inspection** of SARIF upload behavior and post-processing logic
- **Debugging** workflow issues without relying solely on documentation
- **Understanding** internal implementation details for troubleshooting
- **Version verification** when diagnosing compatibility issues

---

**Repository details:**
- **URL:** https://github.com/github/codeql-action
- **Purpose:** Code scanning and SARIF upload actions
- **Current version:** v3 (v2 retired January 2025)
- **Key files:**
  - `src/upload-sarif-action.ts` - Main upload logic
  - `src/upload-lib.ts` - Core upload library
  - `lib/` - Compiled JavaScript actions

---

## Further Reading

- **CI/CD Strategy:** `docs/dev-notes/cicd-strategy.md` - Comprehensive CI/CD planning and implementation guide
- **CodeQL Action Repository:** `/workdir/codeql-action` - Full source code for reference
- **GitHub Actions Documentation:** https://docs.github.com/en/actions
- **SARIF Specification:** https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
- **Self-Hosted Runners:** https://docs.github.com/en/actions/hosting-your-own-runners

---

**Document Version:** 1.0.0  
**Last Updated:** 2025-10-29  
**Maintainer:** AI Agents  
**Review Cadence:** Update when workflows change or new resources become available

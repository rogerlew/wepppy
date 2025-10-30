# GitHub Workflows - Agent Development Guide

## Authorship
**This document is maintained by AI agents. Update when workflow patterns, available resources, or CI/CD infrastructure changes.**

---

## Overview

This directory contains GitHub Actions workflows for CI/CD automation. Agents working on workflow development have access to the full CodeQL Action source code for reference and debugging.

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

# VPAT Workspace

This directory is the operational workspace for WEPPcloud accessibility procurement artifacts.

Use it to keep one mutable staging package for the next buyer-facing issue and a clean append-only archive of issued VPAT / ACR snapshots.

## Structure

```text
docs/ui-docs/vpats/
  AGENTS.md
  README.md
  templates/
    iti-vpat-2.5rev-int-2025-04/
      source-url.md
      notes.md
  current/
    manifest.md
    scope.md
    environment-matrix.md
    evidence-index.md
    open-items.md
  issued/
    README.md
    YYYY-MM-DD_<shortsha>/
      ...
```

## Operating Model

- `current/` is the staging area for the next VPAT / ACR issue.
- `issued/` contains immutable buyer-facing snapshots that were actually cut.
- `templates/` preserves official template provenance and local transfer notes.

## Update Policy

Refresh `current/` when any of these change:

- conformance-impacting UI behavior
- authentication or account-recovery UX
- AA-validated theme baseline
- support documentation or support channels
- in-scope product surfaces
- evaluation environment or browser / OS / AT matrix
- major accessibility remediation
- official template version

Production rule:

- stack related changes in `current/` while they remain pre-production
- before deploying to production, if any trigger above changed since the last issued package, refresh `current/` and cut a new issue package for the frozen deployment snapshot

## Source Of Truth

- Living conformance worksheet: `docs/ui-docs/acr-draft-int.md`
- Strategy and evidence map: `docs/ui-docs/accessiblity.md`
- Current manual pass evidence: `docs/ui-docs/manual-at-pass-20260331.md`

## Archive Naming

Issued directories use `YYYY-MM-DD_<shortsha>/`, for example `2026-03-31_bb0fbb1cb/`.

This keeps the archive human-readable while still freezing the exact evaluated code state.


# AGENTS.md

## Purpose

- This directory is the canonical workspace for WEPPcloud VPAT / ACR lifecycle management.
- Use it to stage the next buyer-facing issue, archive immutable issued snapshots, and preserve the official template source material.
- Keep this directory operational. Put policy and broad accessibility strategy in `docs/ui-docs/accessiblity.md`, not here.

## Directory Model

- `current/` is the mutable staging package for the next VPAT / ACR issue.
- `issued/` is append-only history for buyer-facing issues that were actually cut.
- `templates/` stores official template provenance and local notes about how WEPPcloud maps into the template.

## Canonical Inputs

Read these first when preparing or updating a VPAT:

- `docs/ui-docs/acr-draft-int.md`
- `docs/ui-docs/accessiblity.md`
- `docs/ui-docs/manual-at-pass-20260331.md`
- `docs/ui-docs/vpats/current/manifest.md`
- `docs/ui-docs/vpats/current/evidence-index.md`
- `docs/ui-docs/vpats/current/open-items.md`

## Mutable vs Immutable

- `current/` is expected to change as evidence, scope, or deployment posture changes.
- `issued/*` is immutable after issue except for a clearly documented clerical correction or supersession note.
- Do not rewrite history by editing an issued package to reflect a later product state.

## Naming Rules

- Issued package directories must use `YYYY-MM-DD_<shortsha>/`.
- Example: `2026-03-31_bb0fbb1cb/`
- Date is the issue date, not the first draft date.
- SHA is the exact evaluated repository snapshot for that issue.

## Update Triggers

Refresh `current/` when any of these change:

- conformance-impacting UI behavior
- authentication, sign-in, or account-recovery UX
- AA-validated theme baseline or theme-labeling posture
- support documentation or support channels
- scope of in-scope product surfaces
- evaluation environment, browser matrix, operating-system matrix, or assistive-technology matrix
- major accessibility remediation that changes conformance remarks
- official ITI template version

Before production deployment:

- if any trigger above changed since the last issued package, update `current/`
- stack related UI and accessibility changes into the same `current/` package while they are still pre-production
- cut a new `issued/` package only when the production-bound deployment snapshot is frozen

## Runbook

1. Refresh the canonical evidence docs outside this directory first.
2. Update `current/manifest.md` with the target snapshot, date, deployment intent, and template version.
3. Update `current/scope.md`, `current/environment-matrix.md`, and `current/evidence-index.md`.
4. Reconcile `current/open-items.md` against `docs/ui-docs/acr-draft-int.md`.
5. If the production snapshot is frozen, copy the staged package into a new `issued/YYYY-MM-DD_<shortsha>/` directory and include the final ACR / VPAT artifact there.
6. Never archive a package for an internal-only draft that was not actually used for a buyer-facing issue.

## Authoring Rules

- Prefer conservative wording.
- Keep the conformance baseline limited to the AA-validated theme set.
- Keep sensory-preference themes visible only as supplemental user-choice themes outside the conformance set.
- Distinguish clearly between evidence inputs, staging artifacts, and final procurement artifacts.

## Validation

- Run `wctl doc-lint --path docs/ui-docs/vpats`
- Run `wctl doc-lint` on any other touched docs under `docs/ui-docs/`
- If evidence changed, re-run the relevant repo validations before updating conformance remarks


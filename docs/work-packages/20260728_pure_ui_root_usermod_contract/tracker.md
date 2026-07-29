# Tracker - SURF-15 Pure UI Root User Modification Contract

## Status

Verified 2026-07-28 UTC.

## Progress

- [x] Registered SURF-15 after verified SURF-14.
- [x] Ratified the Root-only render, validation, mutation, persistence, reload,
  and self-Root protection contract.
- [x] Added direct render and real-inline-client evidence.
- [x] Added route, CSRF, validation, persistence, and reload evidence.
- [x] Repaired Root authority, strict validation, self-Root protection, and
  visible safe client feedback.
- [x] Completed security review, focused/broad gates, parent reconciliation,
  commit, and clean closeout.

## Decisions

- Both the page and mutation route are Root-only; Admin has no read-only view.
- Only PowerUser, Admin, Dev, and Root can be changed.
- The acting Root cannot remove their own Root role.
- Account lifecycle, session revocation, and audit-log expansion are excluded.

## Conformance Classification

Direct regressions confirmed and repaired the route-authority, self-Root,
payload-type, malformed-body, HTTP-status, and console-only feedback
mismatches. No role, account operation, or session behavior was added.

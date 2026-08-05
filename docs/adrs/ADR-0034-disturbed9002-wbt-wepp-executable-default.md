# ADR-0034: Disturbed9002 WBT WEPP Executable Default

Status: Superseded (2026-08-05)

Date: 2026-07-30

## Supersession

This historical default decision is no longer active. The configuration now
uses `wepp_260803`, and WEPPpy withdrew `wepp_260727` and
`wepp_260727_hill` on 2026-08-05 because their HBP-only pass contract cannot be
combined with legacy flat-file pass inputs. Existing projects are not silently
migrated; they must select a compatible installed binary and regenerate
dependent pass artifacts.

## Context

New projects created from `disturbed9002_wbt.cfg` currently initialize the
watershed WEPP executable as `wepp_260430`. The repository already ships the
newer paired watershed and hillslope executables `wepp_260727` and
`wepp_260727_hill` with release metadata, checksums, and compatibility details.

## Decision

Change only the `[wepp] bin` default in `disturbed9002_wbt.cfg` to
`wepp_260727`. Do not change other configurations, rewrite existing persisted
project state, or change the pass-family default.

## Decision Provenance

Decision Venue: Codex API workspace thread, 2026-07-30 09:04 PDT

Participants Present: requesting WEPPcloud operator; Codex

Decision Owner(s): requesting WEPPcloud operator

Implementer(s): Codex

## Change Summary

Old behavior: a newly initialized `disturbed9002_wbt` project uses
`wepp_260430`.

New behavior: a newly initialized `disturbed9002_wbt` project uses
`wepp_260727`. Existing projects retain their persisted executable, and all
other configuration defaults remain unchanged.

## Rationale

The operator selected `wepp_260727` as the new default for this configuration.
The exact watershed/hillslope binary pair is already shipped, its recorded
checksums match the files, and its metadata declares support for both HBP and
legacy ASCII pass families.

## Alternatives Considered

1. Retain `wepp_260430` - rejected by the operator's explicit default change.
2. Change every config using `wepp_260430` - rejected because the requested
   scope is only `disturbed9002_wbt`.
3. Rewrite existing `wepp.nodb` state - rejected because a default change does
   not authorize migration of existing projects or their result provenance.

## Consequences

New `disturbed9002_wbt` projects can produce different WEPP inputs or outputs
than projects initialized with `wepp_260430`. Executable identity remains
persisted in project state for provenance. Existing runs remain reproducible
with their saved executable, and the selector can still choose another
installed binary.

## Evidence

- `wepp_runner/bin/wepp_260727.json`
- `wepp_runner/bin/wepp_260727_hill.json`
- `tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_260727
  wepp_runner/bin/wepp_260727_hill`
- Watershed SHA-256:
  `cbcfac30e484613c5314e7a91b694863d26138905fcf04947650bc2c6c148918`
- Hillslope SHA-256:
  `d79a4bfde31feab8e3aff5ea5ae5d14b898f85b5f8fae5e471bc43d4078eddcc`

## Risk and Rollback Notes

The primary risk is scientifically meaningful output drift between executable
releases. Monitor new-project execution failures, pass-file compatibility
errors, and unexpected output regressions. Roll back by restoring only
`disturbed9002_wbt.cfg` to `bin=wepp_260430`; do not mutate projects that
already persisted `wepp_260727`.

## Implementation Notes

Keep the implementation limited to the one configuration. Validate the edited
configuration parses to the exact requested value and retain the binary
provenance check as release evidence; no dedicated regression-test module is
required for this single config-line default.

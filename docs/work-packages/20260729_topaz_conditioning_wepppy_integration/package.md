# Topaz Conditioning WEPPpy Integration

**Status**: Complete

**Timezone**: UTC

**Package ID**: DOM-05A

**Parent owner**: DOM-05 Channel Delineation

## Overview

Release the source-faithful `TopazConditionDem` tool from `weppcloud-wbt` and
make it an additive Channel Delineation depression-conditioning choice in
WEPPpy. New runs created with `disturbed9002_wbt` select this algorithm by
default; existing persisted runs and all legacy choices remain unchanged.

## Scope

Included work is the contract and ADR checkpoint, WBT release binary build and
runtime installation, bounded native-process containment, one additive `topaz`
token through the rendered control, controller payload, RQ persistence,
`Watershed`, and WBT emulator dispatch, the `disturbed9002_wbt.cfg` default,
user/developer documentation, and focused contract plus integration tests.
Canonical config/run integrity and fail-closed enum validation are prerequisite
conformance repairs on the same mutation path.

This package does not change queue topology, endpoints, authentication, CSRF,
NoDb serialization shape, D8/stream algorithms after conditioning, global WBT
defaults, or other WEPPcloud configurations. After the planned reviews, the
operator separately authorized local E2E mutation of run `austere-inaction`;
that run's downstream watershed steps were invalidated as expected.

## Fidelity and Evidence

- **Target**: faithful wired integration.
- **Conditioning authority**: `weppcloud-wbt` `TopazConditionDem`, translated
  from TOPAZ FILDEP and RELIEF at TOPAZ revision
  `116607fc1185800ca78e387454ef1ccd3ffd73b4`.
- **Required generated-output evidence**: the freshly installed
  `/workdir/weppcloud-wbt/WBT/whitebox_tools` must discover and execute
  `TopazConditionDem`; WEPPpy must dispatch the `topaz` token to that binary and
  create `dem/wbt/relief.tif`.

## Success Criteria

- [x] A standalone documentation-only contract checkpoint is independently
  reviewed and committed before implementation.
- [x] The select renders `Topaz Conditioning Algorithm` with token `topaz`,
  persists it, and hydrates it on reload.
- [x] `topaz` invokes WBT `TopazConditionDem` with explicit obstruction width
  2; legacy tokens retain their existing implementations.
- [x] `disturbed9002_wbt.cfg` defaults new runs to `topaz`; existing persisted
  projects do not migrate.
- [x] The installed WBT release binary exposes and executes the tool from the
  WEPPpy runtime.
- [x] Contract, Python, frontend, documentation, and generated-output gates
  pass.

## Security and Parameterization

- **Security impact**: `high`.
- **Dedicated security review**: required at
  `artifacts/2026-07-30_security_review.md`.
- **Rationale**: the additive enum crosses an authenticated browser mutation,
  rq-engine, persisted NoDb state, worker, and subprocess boundary. No auth or
  queue edge changes are intended.
- **Parameterization change**: yes. ADR-0032 governs the
  `disturbed9002_wbt.cfg` default change.

## Deliverables

- Contract decision, two independent checkpoint reviews, post-fix
  confirmations, disposition, and standalone ancestor commit.
- ADR-0032 and amended DOM-05 canonical field matrix.
- Released WBT runtime binary containing `TopazConditionDem` plus bounded
  process-tree timeout/cleanup.
- WEPPpy UI, persistence, dispatch, configuration, stubs, docs, and tests.
- Validation and final review artifacts.

## References

- `docs/standards/contract-first-change-standard.md`
- `docs/standards/parameterization-adr-standard.md`
- `docs/work-packages/20260728_channel_delineation_ui_contract/`
- `/workdir/weppcloud-wbt/docs/release-build-install.md`
- `/workdir/weppcloud-wbt/docs/work-packages/20260729_topaz_condition_dem_parity_hardening/`

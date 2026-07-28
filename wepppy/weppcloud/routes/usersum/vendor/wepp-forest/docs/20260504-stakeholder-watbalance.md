# Technical Reference: WEPP-Forest Water-Balance Modernization

Original date: 2026-05-04

Revised: 2026-07-28

Audience: Hydrologists, land managers, program staff, and analysts who use WEPP results

## Current status

This brief originally described the May 2026 `wepp-forest` process-kernel
rewrite as the intended production direction. That is no longer accurate.

On 2026-06-05, the project:

1. abandoned the process-kernel rewrite as the forward development line;
2. returned the legacy comparator to the `wepp_260430` lineage;
3. ported only the corrected negative-melt calculation into that comparator;
   and
4. promoted [openWEPP](https://github.com/rogerlew/openWEPP) as the forward
   development path for WEPP architecture and science.

The May work remains useful as investigation history. Its closure audits,
failure cases, and regression evidence still identify important risks. Its
claims about the process kernels being the current release architecture,
however, are superseded.

## What the May campaign established

The campaign showed that WEPP's large fixed-form `watbal.for` and
`watbal_hourly.for` routines make water accounting difficult to isolate and
test. Daily, hourly, snow, interception, runoff, and storage behavior share
implicit state and partially duplicated code paths.

Fine-grained closure audits exposed several accounting and integration
problems, including:

- an hourly transport-capacity bypass;
- a snowmelt double-count in an audit basis;
- missing interception-storage export;
- rain and melt routing ambiguity;
- inconsistent per-OFE `QOFE` accounting on multi-OFE hillslopes; and
- defects introduced by the experimental process-kernel implementation itself.

The campaign also demonstrated why a successful test cohort is not sufficient
authority for a broad hydrologic rewrite. Some repairs closed their seed cases
but failed on wider cohorts, and the new kernel path accumulated its own
trajectory and state-ownership problems.

## Why the project reverted

The process-kernel line had become a second implementation of WEPP physics
inside the legacy Fortran codebase. That created dual authority: the old
routines still defined much of the operational behavior while the new kernels
attempted to replace selected portions of it. Comparator agreement, closure,
and physical correctness could then point in different directions.

The project preserved that line for archaeology under the
`kernel-rewrite-abandoned-20260605` tag. It did not promote the line as the
long-term production architecture.

Instead, the active legacy reference was re-anchored to `wepp_260430` plus one
isolated correction for the negative-melt sign defect:

- branch: `wepp_260430_negmeltfix_comparator`
- tag: `wepp_260430_negmeltfix_comparator_47ac4c32faee`
- commit: `47ac4c32faeea81bb99081f955a14c38b815ef4d`
- source change: the negative-melt branch in `src/winter.for`

This comparator is a reproducible investigation aid, not a universal
correctness oracle. A difference from it is a signal to investigate units,
lineage, conservation, and governing science; it is not automatically an
openWEPP defect.

## Forward development

[openWEPP](https://github.com/rogerlew/openWEPP) is the active development
project for a modern WEPP engine. It provides a clean architecture in which
process ownership, state transitions, units, conservation contracts, and
output schemas can be explicit rather than layered into the legacy Fortran
runtime.

The division of responsibility is:

- **WEPP-Forest `wepp_260430` plus the negative-melt fix:** stable legacy
  provenance and comparator behavior.
- **openWEPP:** forward model architecture, science implementation, validation,
  and new engine development.
- **wepppy/WEPPcloud:** orchestration, run management, integration, and user
  delivery.

New scientific behavior should be developed and validated in openWEPP.
WEPP-Forest changes should remain narrow, auditable compatibility or comparator
work unless a later decision explicitly changes this posture.

## Practical guidance

- Do not select the May process-kernel builds merely because the original
  version of this brief described them as the modern path.
- Use an explicitly identified legacy binary when reproducibility against
  historical WEPP-Forest behavior is required.
- Use the corrected `wepp_260430` comparator when investigating negative-melt
  behavior.
- Treat comparator differences as evidence to adjudicate, not values that
  openWEPP must reproduce without independent scientific support.
- Follow openWEPP contracts, conservation checks, and validation evidence for
  forward-development decisions.

## Bottom line

The May 2026 campaign produced valuable diagnostics, but its proposed
process-kernel architecture was not retained. WEPP-Forest reverted to the
`wepp_260430` lineage with the corrected negative-melt calculation, and
openWEPP became the forward development path.

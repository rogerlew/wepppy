# Production M1 decision register

Proposed 2026-09-10 UTC. Detailed operator approval is required before the
contract checkpoint. This file tracks decisions; current domain/UI contracts
hold the normative behavior once accepted.

| ID | Concrete proposal | Disposition needed |
| --- | --- | --- |
| U01 | Single Post-fire debris flow control: compact prerequisites, dNBR upload, design rainfall source, Run debris-flow model; exact labels/states in UI contract. | Owner review of layout/copy. No report or dashboard; completion and file access only. |
| U02 | Project climate is design-source default; NOAA remains selectable when available. Always evaluate project wet events. Fixed 15/30/60 minutes, 1/2/5/10 years, 50% inverse target. | Approve defaults and record ADR; no hidden parameter picker or automatic source switch. |
| U03 | Owner requests Auto-default scale select, no image dates, differenced Normalized Burn Ratio label, persistent accepted filename, visible format/datatype guidance; VRT-only companion picker. | UI revisions accepted. Auto must attempt detection from the value distribution and show upload details/applied scale in a wc-control__panel-summary table; ambiguity requests preset/custom selection using retained candidate. Freeze evidence, candidate retry/expiry and errors before implementation; evaluate distribution criteria under ADR-0063; no dtype-only or single-extreme shortcut. |
| U04 | Required project data and NOAA availability update in realtime through preflight; unavailable NOAA disabled. | Owner-directed behavior. Freeze additive checklist keys, producer invalidations, reconnect and stale handling; no silent rainfall-source switch. |
| P01 | Upload normalization and M1 execution use queued workers; one model job composes predictors/results. Duplicate matching submission returns current job. | Freeze routes, multipart/JSON schemas, statuses, retry/timeout and idempotency before code. |
| P02 | New NoDb state and immutable per-attempt upload/run directories; publish pointer only after ownership/source rechecks. | Freeze versioned keys, transitions, atomicity, permissions, cleanup/retention and recovery; preserve old debris_flow.nodb. |
| P03 | Check current owner artifacts/identities; upload needs only eligibility/grid/access, model needs Soils/SBS/K/dNBR/Climate and selected NOAA. | Resolve effective CONUS/legacy us and cross-boundary policy via existing authority. No new M1 10 m restriction. |
| P04 | Changed dependencies mark prior result outdated; stale dNBR on grid change requires explicit re-normalization action. | Specify whether the existing Upload dNBR action can reuse stored source or requires reselecting it. Recommend re-upload initially; no extra rebuild controls. |
| P05 | Reuse existing authorized run-file access for completed fixed bundle artifacts. | Verify access paths and private worker/web modes; no new generic archive service or reports. |
| P06 | User's later 10 m project validates upload/run on designated target after preflight. | Target URL/host is not yet supplied. Do local/production-equivalent validation first; obtain target authority before installation/deployment. |

Engineering tasks, not user-facing choices: safe staging/VRT allowlist, finite
NoData adaptation, exact file association, source hash checks, job-tree/catalog
updates, worker WBT capability, namespace/module registration and NoDb cache
refresh. These do not justify adding interface controls.

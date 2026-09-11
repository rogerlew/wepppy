# Production M1 decision register

Accepted through owner execution authorization and contract checkpoints `5c0a172ee`
and `595816476`. Current normative rules are the module production contract,
UI contract and ADR-0063; this register records package disposition.

| ID | Accepted decision and disposition |
| --- | --- |
| U01 | Implemented single minimal preparation/upload/run control; no report or dashboard. |
| U02 | Project climate default; available NOAA selectable; always evaluate project wet events. Fixed 15/30/60 minutes, 1/2/5/10 years, 50% inverse target (ADR-0063). |
| U03 | Implemented exact dNBR name, no date fields, Auto/preset/custom, persistent filename and format/type help. Distribution-v1 and two-column wc-control__panel-summary are validated; ambiguous candidates support retained-file correction. |
| U04 | Live preflight updates requirements/NOAA; disconnected or failed state fetch disables Run. No silent source switch. Actual browser invalidation/recovery passed. |
| P01 | Authorized queued normalization and one predictor/results model job; exact planned job receipts survive ambiguous Redis submission. |
| P02 | Additive optional NoDb schema1 and immutable hidden per-attempt artifacts; short final publication lock, old legacy controller untouched. No automatic deletion. |
| P03 | Canonical continental-us authority and WBT; no new M1 10 m restriction. Upload needs grid/access only; model requires owner-current Soils/SBS/K/dNBR/Climate and selected NOAA. |
| P04 | Changed dependencies mark prior results stale. Existing Upload dNBR action can re-normalize accepted source; unaccepted candidates expire after 24 h. |
| P05 | Dedicated authenticated fixed-file route exposes only the latest accepted event/design/inverse/manifest bundle. No general source/staging access. |
| P06 | Development WBT installed with recorded backup/hash and actual worker/browser validation. Owner's later real 10 m project and any other-host deployment remain separate handoff actions. |

Engineering decisions are documented in production_m1.md: bounded safe raster
staging, candidate association, pre-decoder limits, source hashing, exact receipt
reconciliation, module enablement, owner freshness and verified predictor reuse.

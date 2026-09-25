# Contract decision: Omni thinning 60/70

Date: 2026-09-25 UTC. Starting implementation: `cf6437095fead72722f91ccc124119c7f824d65e`.
Classification: intended additive enhancement; conformance pending.

## Authority and operator approval

Operator explicitly requested scaffolding and executing this package, using
20260920_omni_thinning_30_50 as the recipe, with 30/40/50/60/65/70 choices and
65 retained because removing it would break old projects. This authorizes the
bounded implementation and necessary checkpoint commits, not deployment.

Applicable contracts: omni-thinning-contract.md (amended); shared controller
contract, MOFE management artifact contract, NoDb persistence/concurrency and
Disturbed treatment soil lookup contract (unchanged). ADR-0074 records exact
parameterization/provenance. Historical package is read-only evidence.

## Delta and exclusions

Add canopy 60/70 crossed with ground 75/85/90/93. Only static cancov becomes
0.60/0.70; other source parameters equal corresponding 40% files. Five existing
catalogs gain eight records each; preserve every old record/file/ID. UI order
30/40/50/60/65/70, default 40%. Ground order/default and soil rules unchanged.
No schema, transport, eligibility, storage, lifecycle, auth or queue changes.
Security impact none. No new dependencies or operational mechanisms.

## State and evidence matrix

| State | Outcome | Evidence |
| --- | --- | --- |
| Never used / absent | Can add default 40/93 row | Existing/new-row controller test |
| Present empty | Can add default 40/93 row | Controller empty-list test |
| Populated new | 60/70 reload and submit unchanged | Hydration/serialization tests |
| Legacy populated | 30/40/50/65 retain selection/assets | Legacy bytes/records comparison, hydration |
| Malformed/missing | Existing explicit failure behavior | Existing Omni validation tests |
| Working/failed/completed | Existing visibility and lifecycle unchanged | Existing artifact tests; no changed status path |
| Archived/restored | New/legacy files preserve bytes | Canonical archive/restore tests |

Read parsed source, single-OFE, combined multiple-OFE and prepared management
canopy/rill/interrill. Verify new soil prefixes consume thinning row. No fresh
model-output or live browser/deployment claim without those separate gates.

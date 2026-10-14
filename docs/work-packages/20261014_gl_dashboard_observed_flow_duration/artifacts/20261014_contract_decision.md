# Contract decision: observed flow-duration overlay

Date: 2026-10-14 UTC. Starting revision: ebaed5a23cc9132424db90a38241f1e9f090fafc.
Amendment: FDC-OBS-01. Classification: requested capability, not conformance repair.

## Authority and scope

Operator request: “scaffold and execute work-package to add this abailty, when a
project has observed streamflow data users should be able to add the distribution
to both the hillslope streamflow and channel outlet discharge plots”. This authorizes
this package and its required checkpoint execution. No unrelated owner/package is
advanced. Preserve upload/model-fit contracts and existing authorization.

## Applicable contracts and normative delta

Amend docs/ui-docs/contracts/gl-dashboard-flow-duration-contract.md, adding Observed
streamflow overlay; ADR-0093 specifies conversion/population. Compose unchanged
controller-contract.md and output-scope-contract.md. Existing NoDb persistence and
CSRF contracts are unchanged because there are no writes or new endpoints.
Implementation conformance is pending. Exact behavior, valid-state matrix and
rationale are in the canonical amendment, not inferred from existing code.

## Compatibility, data and security

Additive optional state/bootstrap fields, no persisted schema or artifact mutations.
CSV and area parquet reads remain inside the authorized project root; canonical
Omni lineage is the existing project boundary. High security triage (new file/path handling): reject escaping
symlinks before file parsing, keep nonfinite values as strings, render text safely.
No new auth, query, queue or dependency. Read-only filesystem boundary tests required.

## Regression evidence and review

Tests cover missing/empty/unsupported/malformed observations, no area, invalid area,
escaping paths, Roads, child lineage, raw CSV Julian conversion, independent
ranking and checkbox wiring. Browser verification uses actual graph modules.
Two independent reviews and their disposition are required before checkpoint commit.

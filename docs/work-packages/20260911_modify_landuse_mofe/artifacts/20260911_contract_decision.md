# Contract decision checkpoint

Starting revision: `507061d0b34e4f9d465ed5d10a413afdb51c6212`.

Operator approval of outcome (2026-09-11): “clicking \"Modify Landuse\" should
regenerate the MOFE files and the landuse summary should include the modifed
landuse class”. This authorizes implementation of that outcome; commit authority
has not been explicitly granted.

Classification: newly specified selected-hillslope behavior; the existing
Disturbed MOFE mapping contract covers severity remapping only.

Applicable contracts: new `docs/schemas/landuse-modification-contract.md`;
`docs/schemas/disturbed-mofe-mapping-contract.md` (unchanged burn behavior);
`docs/schemas/nodb-persistence-concurrency-contract.md` (unchanged persistence);
`docs/schemas/rq-response-contract.md` and `weppcloud-csrf-contract.md`
(unchanged transport and authorization); `docs/ui-docs/controller-contract.md`
(unchanged browser runtime). Artifact observability remains required.

Normative delta: selected classes reach OFE assignments, generated management
files, and summary area before success. Preserve configured buffers and geometry.
Rationale: saved thinning must correspond to usable management inputs, not just
a hillslope display. Raster rebuild that loses explicit edits is rejected.

Compatibility: no schema, endpoint, key, column, formula, or default changes.
Security: low; preserve existing run boundary, locks, errors, and file locations.
Regression/state matrix and artifact acceptance are specified in the new contract.

Independent reviews: `/root/contract_review_1` and `/root/contract_review_2`
reviewed read-only on 2026-09-11. Both requested explicit legacy/optional/runtime
states and failure freshness/retry policy (medium). Added the state table and
route error/controller panel/log/retry requirements. Both reviewers re-read the
amendment and confirmed all findings resolved and checkpoint approval.
Ancestor commit: pending authority. Contract and package doc lint passed.

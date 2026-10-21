# Gregorian calendar repair

Status: Complete (source repair and isolated generated-output validation), 2026-10-21.
No deployed release or original project output was replaced.

Fixed Gregorian execution, incomplete/EOF climate handling, daily PASS validation,
explicit HBP compatibility policy and downstream padding conversion. CLIGEN already
uses Gregorian dates and requires no change. Maintained native sources and the
261010 ASCII backport both complete the full 104-hillslope, 200-year project.

Both 200-year paths have 73,048 climate-aligned daily records and 7,596,992 unique
hillslope-day Parquet rows. Both compact 400-year simulations complete; new HBP
interchange has 146,097 unique dates. Unaffected 44-year output and observability
parity checks pass. Native broad gates retain documented external-fixture/cache
limitations; no full-green release-readiness claim.

- [Validation and limitations](artifacts/validation.md)
- [Plan](prompts/completed/repair_execplan.md) and [tracker](tracker.md)
- [Decision and compatibility rationale](../../adrs/ADR-0100-wepp-gregorian-execution-calendar.md)
- [Maintained source patch](artifacts/maintained-source-repair.patch),
  [ASCII release backport](artifacts/ascii-release-backport.patch), and
  [interchange padding patch](artifacts/interchange-padding.patch)
- [Candidate binary hashes](artifacts/binary-hashes.json) and
  [evidence provenance](artifacts/provenance.json)

Operational cutover requires a paired binary release plus the corrected interchange
library, followed by regeneration of all hillslopes, watershed and interchange.
Keep valid existing CLIGEN climate; never relabel old PASS dates or policies.

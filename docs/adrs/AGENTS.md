# ADR authoring

- Start from `ADR-template.md`; use `ADR-NNNN-short-description.md`.
- Every numbered ADR requires an explicit, valid `Date: YYYY-MM-DD` in its
  preamble, before the first section heading. Replace the template placeholder.
- Use the original decision date and retain its recorded timezone in provenance.
  Preserve that date when adding amendments; later review, implementation and
  deployment dates belong in their respective sections.
- Dates only in status/provenance prose do not satisfy the catalog's Date field.
- Before committing ADR changes, run `python3 tools/check_adr_dates.py` from the
  repository root, plus `wctl doc-lint --path <changed ADR>`.
- Docs Quality CI enforces the date check for all numbered ADRs, using the same
  parser as Usersum. README/template files are excluded.
- Follow `docs/standards/parameterization-adr-standard.md` for scientific
  parameterization decisions, including explicit decision provenance.

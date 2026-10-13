# Tracker

2026-10-13 UTC: implementation and focused acceptance complete; final review disposition retained in artifacts.

- Contract checkpoint: `b4be200b4`, preceded all production changes. Independent correctness/security reviews passed; None/empty-map precision and schema discovery metadata addressed.
- D01 literal config/readback: new projects select wepp_261010; vendored watershed/hillslope binaries exist. No changes to saved selections or scientific-parity claim.
- D02: unknown palettes admitted; direct native regression covers unknown/mixed/unburned-only, manual remapping, source masks and display/export distinction. Existing native/error and upload checks retained.
- D13/D14/D18: ORCID indefinitely deferred in docs, Mariana contact, official FAQ title. No runtime OAuth removal or privilege changes.
- Other 13 audit dispositions remain follow-up work.

Canonical decisions: SBS raster contract (Unknown palette colors), upload-endpoint contract (SBS palette admission), ADR-0089/0090. ADR-0045 display semantics remain unchanged. No deployment or index rebuild performed. Validation: 182 passed/1 skipped; docs/catalog/broad-exception gates pass. See artifacts/validation.md.

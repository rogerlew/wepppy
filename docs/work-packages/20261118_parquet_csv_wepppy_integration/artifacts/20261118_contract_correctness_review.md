# Independent M0 correctness review

Date: 2026-11-18 UTC. Reviewer: csv_contract_correctness (read-only agent).
Verdict: approved for checkpoint commit; no unresolved medium/high findings.
Reviewed integration contract SHA-256:
`c9c94c0b4430710c3a922b8d287587adac27abbfef6a4f0b3552ec39a8b20907`.

Findings closed before source implementation:

- Live NoDir directory CSV ignored pqf: unify selection and retain actual-route tests.
- Numeric comparisons require DOUBLE casting, while Contains uses DuckDB VARCHAR
  and simple Unicode lowercase; physical index fields remain filterable.
- Observed timestamp/null/WKB/ZSTD support is mandatory, including hidden fields.
- Fixed2,000,000 cap applies only to active filters, never unfiltered H.wat.
- Parent normalization preserves Python numeric grammar and Unicode length rules.
- Duplicate projected labels retain repeat-last-value behavior; unfiltered raw
  duplicate names remain ambiguous, filtered duplicates use DuckDB disambiguation,
  including preexisting suffix collisions. Differential evidence remains required.
- Operator explicitly approved invalid-UTF8 metadata rejection with raw access.
- NaN exclusion is scoped to comparisons; Contains can match numeric nan text.
- Normalized IPC has128KiB headroom above64KiB external JSON; retain emoji-boundary test.
- Native wall alarm maps to timeout504; other unexpected signals remain failures.

The review directly probed old duplicate/metadata and DuckDB scalar behavior.
Inventory156 nonempty files does not replace empty, legacy and malformed fixtures.
Contract readiness is not implementation conformance: parity, dependency/resource,
lifecycle, exact-image HTTP and final independent implementation reviews remain.

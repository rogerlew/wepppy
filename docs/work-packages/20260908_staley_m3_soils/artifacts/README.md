# M3 soil evidence catalog

The offline experiment is complete; [source decision](soil_decision.md)
recommends retaining original STATSGO pending scientific approval. No production
SSURGO substitution, availability cutoff or live Soils rebuild is implemented.

- [Inventory](source_inventory.csv), [protocol](study_protocol.md), and
  [canonical contract pointer](soil_contract.md).
- [72 comparisons](source_comparison.csv), [924 M3 diagnostics](m3_sensitivity.csv),
  [plot](soil_comparison.png), and [coverage](catchment_coverage.csv).
- [Component and interval audit](component_audit.csv): both policies, interval
  sum/union/endpoint, inclusions, exclusions and reasons. This combines the
  originally planned separate interval/component audit tables.
- [Map-unit audit](mapunit_audit.csv): known/valid/omitted component denominators.
- [WBT commands](commands.json), [code/input identities](environment.json),
  [reproducibility](reproducibility.json), and [validation](validation.md).
- [Correctness review](20260909_correctness_review.md) and
  [security review](20260909_security_review.md): all findings closed.
- [Explicit acquisition recipe](acquire_sources.py), [offline harness](run_study.py).
- [Frozen public inputs and hashes](../../../../tests/nodb/mods/fixtures/postfire_debris_flow_soils/README.md).

Generated rasters and disposable SQLite databases remain in
`/tmp/staley-m3-soils-study/evaluation-final/`; they are reproducible from the
frozen inputs and the sibling WBT terrain fixtures. The committed tables,
metadata, commands and hashes survive deletion of temporary outputs. No
publisher PDF, GPL source/tests, whole project database or live soil artifact
is redistributed here. The stable module contract and ADR-0053 own future rules.

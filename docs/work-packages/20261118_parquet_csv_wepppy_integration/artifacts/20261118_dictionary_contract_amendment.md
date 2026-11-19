# Dictionary compatibility checkpoint amendment

Date:2026-11-18 UTC. Status: independently approved before threshold source edit.
Parent contract checkpoint:a1f40de48bce439520fd47bb5e8d3f9ae0167bd0.
Implementation is in progress; no dictionary threshold source change yet.

A broader real-file parity run rejected watershed/flowpaths.parquet after five
successful schemas. Bounded dictionary-header scanning across the156-file
inventory confirms seven dictionaries above100,000, maximum125,855. Input hashes
are retained in compatibility-inventory.json; exact occurrences are retained in
dictionary-compatibility.json. This is observed valid-state evidence, not a
speculative limit increase. Native support is required by the approved cutover.

Amend ADR-0149 and the canonical integration contract to131,072 dictionary entries.
Other process, page, cumulative decode and service capacity ceilings are unchanged.
No new dependency or backend. Test exact threshold and threshold+1 and rerun real
flowpath/road-event CSV bytes. Reviewer disposition and this documentation commit
must precede the threshold source edit. Operator execution authority covers this
bounded engineering choice; deployment remains unauthorized.

## Independent review disposition

Correctness reviewer `csv_contract_correctness` and security reviewer
`csv_contract_security` approved this checkpoint on 2026-11-18. Both independently
verified all seven counts and hashes of the three affected source files. Neither
found a blocker. Exact-cap/cap-plus-one tests, real flowpath/road-event byte parity
and resource evidence remain implementation gates; approval is not acceptance.

# Correctness review

Reviewer: independent `contract_correctness` agent. Final disposition: ACCEPT.

Closed findings:

- Preserve and revalidate unmigrated external dependencies; never refresh their
  signatures to accept a changed input during recovery.
- Resume partial root/nested-name relocation with directory-aware containment.
- Independently reconstruct the JSON hash graph; never trust report-supplied
  rewrite mappings or planned state as authority.
- Anchor every accepted inventory member to original NoDb path/size/SHA; reject
  omitted or forged entries. Preserve exact original metadata in visible storage.
- Write preparation status before backups; block new writes on unmigrated trees.
- Retain initial upload receipts and failed transfer bytes/diagnostics before enqueue.

Real failure/recovery/tamper tests, the worker-identity migration, current freshness,
ten browser download hashes and 148-file canonical archive/restore close the
acceptance gates. The final soil change removes only counting-raster deletion;
35 soil tests pass with exact retained pixel/NoData assertions. No blocking finding
remains. Evidence scope is the development instance and explicit project migration;
no fleet rollout is claimed. Public four-file replacement retains its documented
per-file interruption semantics.

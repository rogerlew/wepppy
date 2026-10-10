# FDC-01 preimplementation checkpoint

Starting implementation revision: 189d10649793f0be1bdae5aeb90e8af9a810d977.
Classification: intended additive behavior. Operator explicitly authorized
commit and execution, forest stack restart and integration testing on 2026-10-10.

Applicable authority: docs/ui-docs/contracts/gl-dashboard-flow-duration-contract.md;
docs/ui-docs/controller-contract.md; docs/ui-docs/gl-dashboard.md;
wepppy/weppcloud/static/js/gl-dashboard/README.md; output-scope and CSRF contracts;
ADR-0085. Normative delta and valid-state matrix are in the FDC contract.

Exact boundary: existing dashboard route/bootstrap template, graph loader,
controller, state, mode registration and numeric probability renderer; focused
unit/route/browser tests. No model outputs, schemas, auth, queue or other graphs
change. Read existing daily Parquets via scenario-aware Query Engine. Missing
child data never substitutes baseline. Independent records are operator-selected
for performance. No shared-record join or premature truncation.

Security impact: data-query/readiness boundary, retain dedicated independent
security artifact. Existing path containment and authorization apply. Bootstrap
metadata validates canonical file/catalog ownership and outlet mapping. No new
query service or raw file endpoint. Integration uses the real authenticated
browser and unmocked filesystem/query boundaries. Readonly is not a readiness gate.

Evidence planned: mathematical oracle, invalid/missing/zero/unequal-period cases,
source ownership and symlink/catalog tests, direct real-source numerical oracle,
visible graph/hover under both sources/scales, keyboard/resize/mode regressions,
actual forest stack health/restart and existing GL smoke tests. Two independent
read-only reviews and dispositions required before this checkpoint commit.

Review disposition: independent correctness and security reviews passed after
clarifying outlet topology, coverage/filter precedence, VARCHAR nonfinite
transport, catalog root/entry ownership and Roads unavailability. See sibling
review artifacts. No open high/medium checkpoint findings. Implementation and
integration evidence remain pending; reviews do not claim runtime conformance.

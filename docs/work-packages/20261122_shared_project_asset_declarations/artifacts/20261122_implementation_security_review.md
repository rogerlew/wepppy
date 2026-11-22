# Implementation security review

Independent security reviewer, 2026-11-22 UTC. Reviewed the runtime diff from `a957440abbc00b51ddb356e74d84b50382edae3f` through `f17ec6ca3681efd5f93207a8b825b1059c94c177`. Security impact is high because the same asset name can refer to local or inherited physical data, across two consumers with different authority. The review covers the two migrated asset families. The [correctness review](20261122_implementation_correctness_review.md) records producer and consumer compatibility findings.

## Findings and disposition

The static review found no new authority to read another project or publish an ineligible asset. During review the Feature Export adapter was changed to pass expanded declarations through the existing locator shape and allowed-kind checks. Both declaration forms now flow through that validation. No open high, medium or low findings on the implementation.

| Surface | Evidence and decision |
| --- | --- |
| Template and identity | The registry accepts exact relative components and the bounded output-scope placeholder. It rejects duplicate IDs and colliding logical keys. Feature Export looks up shipped IDs and accepts only named scenario or contrast projections for baseline hill loss. Unknown or mixed references fail on catalog load. |
| Query scope and valid states | The query adapter reads one published catalog, checks for duplicate selected keys, and constructs a named projection only from a single child component. An absent key returns the existing missing outcome. The metadata entry can contain a stored physical pointer. Callers that read bytes must use the scoped planner and executor. Existing scope resolution governs local overrides, parent inheritance, relocation, external and sibling denial. The Roads lifecycle continues to own currentness checks. |
| Export scope | Lowering produces the existing `kind` and `value` before planning. Existing selector normalization, parent-relative spelling, dependency containment, requiredness and authorized NoDb lookup still apply. Query and export have distinct parent access rules. The declaration itself contains no executable getter or physical path supplied by a project. |
| Producer writes and data integrity | Reviewed Peridot, the native LOSS wrapper, legacy migration and Roads helpers against their prior destinations. The native result check requires the declared hill output in the native publication response. Directory selection, NoDb persistence, receipt routing, locks and worker scheduling remain governed by their existing owners. |
| Authentication, secrets, queues, CI and egress | The diff adds in-process naming helpers and local tests. No changes to HTTP or MCP entry points, auth/session/CSRF policy, worker edges, package dependencies, workflows, secrets, service mounts or outbound calls. |
| Operational evidence and privacy | Reviewed the observer and replay isolation design. Live observations use read-only NFS bindings with a separate network namespace and private scratch. The [matched normal-project replay](20261122_private_replay.md) used a private writable copy and isolated Redis. Its observed module hashes, source generation, dependency fingerprints and query/readback outcomes bind it to the two named revisions. Project mappings and raw rows belong outside the repository. Coverage and generation checks are recorded by the production operator in the [production protocol and evidence](production_validation.md). |

## Local boundary evidence

The isolated wctl run passed 23 tests on the reviewed commit. Its receipt `665040566c004fbea5d053c14b22c26b` records zero source changes. The run covered declaration validation and collisions, named query views with distinct Parquet values, ambiguous and invalid projections, denied sibling read and publication paths, scoped relocation, permitted parent export dependencies and out-of-parent rejection. It exercised the actual scoped reader and retained catalog, including the distinction between a child-direct key and an absent parent projection.

## Release disposition

Code security review applies to the exact revision above. The package requires separate correctness review and completed original-project comparisons and matched private export replay before operational acceptance. The study does not authorize production activation.

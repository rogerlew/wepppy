# Correctness Review - Batch Climate and RAP NoDb Contention

**Disposition**: Pass; no unresolved high or medium findings.
**Independent reviewer**: `/root/correctness` (read-only); final re-review on 2026-09-07.
**Authority**: unchanged NoDb Writer Ownership and Mutation Topology contract.
**Deployment acceptance**: excluded by operator, unmeasured.

The reviewer confirmed explicit derived-field application, fresh disk hydration,
six RAP cover bands, unchanged batch semantics, and preserved valid states.
The initial findings were resolved and re-reviewed:

| Finding | Severity | Resolution |
| --- | --- | --- |
| Artifact rollback after an already committed NoDb replace | High | Exact intended-payload readback distinguishes own commit; unknown outcomes retain recovery copies. |
| PRISM omitted upstream climate inputs | High | Observed year/station/settings snapshot is compared alongside spatial/CLI inputs. |
| Old calendar/NOAA sidecars survived successful rebuild | Medium | Successful observed publication removes obsolete sidecars with reversible backups. |
| RAP accidentally included uncertainty bands | High | Restored the original six-band allowlist and exact band regression. |

Direct regressions cover collection/finalization failure, relevant and unrelated
rewrites, empty/legacy/malformed RAP state, single/multi-OFE data, and real
raster-to-parquet-to-WEPP-cover propagation. Later edge tests cover unknown
commit outcome and lock takeover. Test execution was by the primary agent;
reviewers did not independently rerun reported suites.

The deployment writer remains unknown. Multi-file publication is not
crash-atomic, and copied batch lock/status identity is a separate follow-up.


## User outcome and valid-state matrix

Users retain compatible Climate/RAP results while unrelated controller edits
survive. Relevant changes fail explicitly as superseded; batch domain failures
remain retry eligible.

| State | Required behavior | Direct evidence |
| --- | --- | --- |
| RAP feature/source absent | Acquisition initializes manager/year state; analysis requires acquired sources. | Controller fixture initialization; missing-source regression. |
| Present-empty summary | Replace old summary with typed empty parquet. | `test_rap_collection_and_empty_results`. |
| Populated single-/multi-OFE | Retain six cover bands, units, and cover output. | Unrelated rewrite, multi-OFE, and real-raster propagation tests. |
| Legacy embedded/int dataset keys | Read existing values and analyze supported inputs. | Legacy embedded and integer dataset key tests. |
| Malformed years/embedded data | Explicit bounded failure; no result publication. | GridMET malformed input and RAP malformed embedded tests. |
| Managed/unmanaged path | Preserve managed projection; reject or unlink unmanaged directory per entrypoint contract. | Direct containment and router symlink tests. |

## User-reachable error policy

| Condition | Classification and outcome | Authority |
| --- | --- | --- |
| Relevant input changes during collection | Expected contention: explicit superseded `RuntimeError`, no collected output published. | NoDb collect/finalize conflict clause. |
| Missing required raster/manager or malformed state | Invalid stage prerequisite/input: explicit file/value/runtime error before publication. | Existing stage prerequisite plus bounded invalid-state policy. |
| Remote/raster collection failure | Exceptional backend failure propagates; previous durable state/files survive. | NoDb collection-failure clause. |
| Dump or artifact publication failure | Exceptional; restore old files before commit, retain matching new files after own commit, retain recovery evidence if uncertain. | NoDb strict persistence and ownership rules. |

Inputs and filesystem states are separate test dimensions. The direct NoDb
boundary is unmocked; only remote/compute seams are injected for deterministic
interleavings. Read-only review signed off by `/root/correctness` on 2026-09-07.
Base revision is `aafeecc8c3bc3ba9dbf16fec66891770742b35f4`. The gate passes
with zero unresolved medium/high findings; no exhaustive deployment claim is
made. Full validation is in [validation](2026-09-07_validation.md).

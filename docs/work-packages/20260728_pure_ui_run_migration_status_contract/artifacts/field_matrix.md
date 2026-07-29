# SURF-08 Run Migration Status Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Flask host | run authorization, migration need, owner/admin capability | inspected route + render branches |
| Render | exact inventory, readonly state, archive option, skip/run actions | permission-aware direct render |
| Bootstrap | safely embedded run/config and run-scoped URLs | direct render + real inline Jest |
| Enqueue | one session-token POST with native `create_archive` | real inline Jest + rq-engine |
| Duplicate | disabled client action plus server active-job rejection | real inline Jest + inspected route |
| Poll | returned status URL, configured auth compatibility, bounded backoff | real inline Jest + job routes |
| Terminal | finished/failed/stopped/canceled/not-found stop and UI | real inline Jest + inspected branches |
| Worker | archive option, migration result, version, readonly restoration | two direct worker tests |
| Security | scope, session marker, run access, locks, archive confinement | route evidence + independent PASS |

Run-sync, migration inventory changes, queue topology, and archive format are
excluded.

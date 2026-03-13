# Infrastructure Knowledgebase
> Consolidated deployment, operations, and tuning references for WEPPcloud.

## Scope
- Deployment topology and compose runtime baselines.
- Reverse-proxy and app-server tuning levers.
- Storage lifecycle behavior on NFS-backed run trees.
- Operational failure signatures and verification commands.

## Core Documents
| Document | Purpose |
| --- | --- |
| [deployment-tuning-knowledgebase.md](deployment-tuning-knowledgebase.md) | Primary operations knowledgebase (deployment baselines, tuning knobs, failure signatures, package synthesis). |
| [incident-2026-02-26-wepp1-rq-topaz-dednm-hang.md](incident-2026-02-26-wepp1-rq-topaz-dednm-hang.md) | Incident report for wepp1 responsiveness degradation tied to TOPAZ `dednm` pruning loop hang and remediation. |
| [incident-2026-03-12-forest-nfs-client-path-degradation.md](incident-2026-03-12-forest-nfs-client-path-degradation.md) | Incident note for `forest` create/catalog timeouts tied to degraded NFS client-path behavior and follow-up network comparison. |
| [secrets.md](secrets.md) | Canonical secrets handling policy (Compose secrets now; Kubernetes worker pools next). |
| [ui-rcds-nfs-vs-dev-nfs.md](ui-rcds-nfs-vs-dev-nfs.md) | NFS metadata workload benchmark for delete/recreate performance comparisons. |

## Curation Notes
- This directory is a knowledgebase, not a ticket queue.
- Use work packages for implementation plans and execution tracking.
- Add only high-signal operational findings with reproducible commands.

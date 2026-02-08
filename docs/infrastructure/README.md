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
| [ui-rcds-nfs-vs-dev-nfs.md](ui-rcds-nfs-vs-dev-nfs.md) | NFS metadata workload benchmark for delete/recreate performance comparisons. |

## Curation Notes
- This directory is a knowledgebase, not a ticket queue.
- Use work packages for implementation plans and execution tracking.
- Add only high-signal operational findings with reproducible commands.

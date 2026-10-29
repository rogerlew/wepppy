# DM-02 correctness contract review

Date: 2026-10-29 UTC. Independent reviewer: `/root/contract_correctness`.
Scope: canonical DM-02, planned Usersum guidance and work package against actual template, controller, getter and report consumers. Read-only review; no runtime conformance claim.

| Finding | Severity | Disposition |
| --- | --- | --- |
| DM2-C1: report shells include the modal but common routes omit Disturbed context; defaulting absent Jinja state to Base breaks active Extended reports | Medium | Closed: canonical contract and plan require bounded existing-state resolution for the authorized active root, no controller creation, and real report tests for explicit Extended, legacy Extended and Base without supplied context |
| DM2-C2: loading can already select Extended through legacy file fallback | Low | Closed: guide says verify selection and select Extended if needed, preserving getter behavior |
| DM2-C3: frontend gates were conditional on JS changes | Low | Closed: frontend lint/full tests required for template-only implementation; bundle rebuild remains conditional on controller-source changes |

The independent reviewer confirmed all three corrections closed. No remaining blocking findings or operator decisions. Predicate, explicit-Base treatment, missing-file recovery visibility, stable same-page layout and no backend enforcement are coherent. Implementation and real-runtime evidence remain pending.

# Independent correctness / contract review

Reviewer: `/root/report_contract_review` (`reviewer` role). Date: 2026-09-15 UTC.
Scope: report contract, package/implementation plan/matrix and module links;
read-only inspection of production/result readers and scientific authorities.
This is documentation review, not runtime conformance or owner ratification.

## Findings and author disposition

| ID | Severity | Finding | Amendment |
| --- | --- | --- | --- |
| COR-01 | Medium | Blanket raster-read prohibition conflicts with `open_results` → `result_support.read_support`, which verifies saved v2 mask pixels. | Data authority permits bounded fixed saved-mask validation and existing scalar consistency checks; upstream reads/new model calculation remain prohibited. |
| COR-02 | Medium | `ResultCatalog` retains manifest/events only; proposed design/inverse views need an explicit reader addition. | Contract, plan milestone 0/1, decision and matrix require minimal additive validated projection, canonical amendment and compatibility/hash/schema/race tests. |
| COR-03 | Low | Record length could imply continuous complete climate history. | Interpretation and matrix bind “Years represented” and label bounds to accepted frequency metadata; wet-year count separate. |

## Post-amendment confirmation

The independent reviewer reread amendments and confirmed COR-01–03 resolved:
“Documentation-readiness verdict: pass. No remaining medium/high correctness
findings.” The reviewer also ran `git diff --check` successfully.

Residual gates: exact browser payload/error contracts, owner ratification,
standalone checkpoint ancestor, real-file implementation tests, performance
measurements and live browser acceptance. None is represented as completed here.

# SURF-17 RQ Info Details Contract Matrix

| Boundary | Risk-bearing contract | Required evidence |
| --- | --- | --- |
| Authorization | authenticated Admin or Root only | route authorization tests |
| Snapshot | read-only Redis/RQ listing; no mutation or polling | producer inspection + route tests |
| Queue selection | default `default,batch`; trim surrounding whitespace, preserve spelling/order, first duplicate wins | route tests |
| Active grouping | stripped producer queue compares case-sensitively; exact isolation, ordered panels, explicit empty state | route + direct render |
| Recent/failed | combined tables retain Queue column and lookbacks | route + direct render |
| Metadata | escaped job/run/worker/function/submitter/timestamps | hostile direct render |
| Navigation | protected job and run links; safe external-tab relationship | direct render |
| Failure | logged explicit error boundary | route test |
| Security | role boundary and privileged metadata do not widen | dedicated review |

Queue mutation, queue wiring, polling, retention, and job-payload expansion are
excluded.

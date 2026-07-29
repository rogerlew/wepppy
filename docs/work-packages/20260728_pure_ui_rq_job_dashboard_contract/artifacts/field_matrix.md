# SURF-07 RQ Job Dashboard Contract Matrix

| Boundary | Risk-bearing contract | Verified evidence |
| --- | --- | --- |
| Flask host | CAP gate and 32-character UUID normalization | inspected route + focused route evidence |
| Render | exact job id, summary/tree/cancel/QR targets and assets | direct Jinja render + asset assertions |
| Poll | encoded jobinfo URL, configured auth compatibility, bounded schedule | real inline Jest + rq-engine modes |
| Tree | root/children/order progress, expanded state, terminal precedence | real inline Jest + payload tests |
| Safety | escaped descriptions, ids, errors, traceback, QR failure | real inline Jest + inspected render helpers |
| Rate limit | canonical 429 recognition and 30-second bounded backoff | real inline Jest + rq-engine |
| Tokens | run session token then authenticated fallback token | real inline Jest + session/token routes |
| Cancel | confirmation, disabled state, one bearer POST, refresh/errors | real inline Jest + rq-engine |
| Security | CAP, scope, revocation, session marker, run ownership | retained route tests + independent PASS |

Queue creation, worker behavior, job retention, SURF-17, and SURF-18 are
excluded.

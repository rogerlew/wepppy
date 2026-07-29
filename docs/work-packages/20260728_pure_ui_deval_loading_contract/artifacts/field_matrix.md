# SURF-18 DEVAL Loading Contract Matrix

| Boundary | Risk-bearing contract | Required evidence |
| --- | --- | --- |
| Access | run/config authorization plus anonymous CAP challenge | real wrapper and registered-route tests |
| Context | active root, config, parent-owned PUP refresh/tracking identity | route and two-parent PUP tests |
| Cache | fixed confined artifact hit; no-store inline response | route/filesystem tests |
| Enqueue | reuse only owned active job; exact args/options/timeouts | route/RQ tests |
| Loading host | safe run/config/job/status/URLs and no-cache notice | direct render |
| Polling | canonical active/success/failure states; one request at a time | 5 inline Jest tests |
| Recovery | bounded transient retry and 429 exponential backoff | inline Jest |
| Error | nested canonical message as text; malformed/unknown fail closed | inline Jest |
| Worker | confined active root, retired-root guard, command/log/output/status | 9 worker tests |
| Handoff | finished refresh serves generated report | route/reload |
| Security | no access widening, XSS, symlink escape, or job cross-scope | dedicated review and regressions |

Report content, shared polling architecture, queue wiring, and renderer
parameters are excluded.

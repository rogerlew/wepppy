# SURF-01 Contract Evidence Matrix

| Surface | Producer-owned identity | Executable evidence | Result |
| --- | --- | --- | --- |
| Public interfaces | Registry-permitted cards, one maturity label, exact POST configuration and optional overrides | Anonymous actual-render tests plus existing registry route tests | Conforms |
| Public CAP sections | Section-owned token, disabled action until solve, prompt on missing token | Four direct `interfaces_captcha.js` Jest tests | Conforms |
| Authenticated create index | Server-owned configuration catalog and exact override variants; no anonymous CAP | Authenticated actual-render tests | Conforms |
| Portland | `portland-wepp_bd16b69_snow`, `portland-simfire-eagle-snow`, `portland-simfire-norse-snow` | Parameterized actual-render tests | Conforms |
| Seattle | `seattle-snow`, `seattle-simfire-eagle-snow`, `seattle-simfire-norse-snow` | Parameterized actual-render tests | Conforms |
| SPU | `seattle-snow`, `seattle-simfire-eagle-snow`, `seattle-simfire-norse-snow` | Parameterized actual-render tests | Conforms |
| JOH | Presentation/iframe content; no creation mutation | Actual-render test | Conforms |
| CAP gate | Solve, CSRF-bearing verification POST, confined continuation, visible retryable failure | Three direct inline-script Jest tests plus CAP route tests | Conforms |
| Creation boundary | Missing/rejected CAP fails closed; valid CAP reaches creation with exact payload | CAP, route, and rq-engine project-route tests | Conforms |

## Findings

No production contradiction was found. The retained change is regression
coverage at the previously weak executable-client and exact-render seams.

The authenticated create-index route is login-required. Its template retains a
defensive anonymous branch, but SURF-01 does not expand that unreachable branch
into a supported public contract.

Repeated execution replaces the launch button's `onclick` handler. Widget
callbacks may repeat the same token assignment, while the direct regression
proves a solved launch still performs one native `requestSubmit()`.

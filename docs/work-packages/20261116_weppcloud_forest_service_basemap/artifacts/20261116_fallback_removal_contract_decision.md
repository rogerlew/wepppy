# FSBASE-03 — Remove the legacy landing fallback

Starting revision: `abd9f6156`. Earlier basemap implementation remains uncommitted.
Operator explicitly requested removal on 2026-11-16: “is the fallback the dark
theme? this is too complicated. remove the fallback”. Light and dark remain.

Canonical authority: `docs/ui-docs/contracts/forest-service-basemap-contract.md`
(Landing delivery and navigation), plus shared controller contract. The shared
contract has no fallback delivery rule requiring amendment. FSBASE-03 supersedes
only FSBASE-01/02's fallback preservation/repair; the header repair remains.

Normative delta: delete legacy template and fallback; required missing/unreadable
HTML export returns a logged, plain HTTP 503. Existing theme selection and state
injection remain. Rationale: eliminate duplicate maintenance and SEC-03's old
attribution sink. Compatibility: incomplete builds fail visibly; existing builds
continue unchanged. No new dependency, origin, access rule, or persistence change.

State matrix: present valid light/dark HTML -> matching 200; missing export ->503;
unreadable export ->503; absent optional user data remains normal anonymous state.
Input matrix: root, landing, explicit light, explicit dark; no new input surface.
Regression evidence: route tests with real temporary files, controlled read errors,
real Flask route missing/directory-unreadable checks, live both-theme browser
checks and legacy-reference search. Final correctness/security review required.
Implementation conformance pending accepted ancestor checkpoint.

## Independent checkpoint reviews

2026-11-16: `/root/contract_correctness` and `/root/contract_security` each
returned pass, no findings, in read-only reviews before removal edits. Both
require final live/theme and missing/unreadable-export validation. SEC-03 is
pending removal verification. Accepted checkpoint; operator approval above.

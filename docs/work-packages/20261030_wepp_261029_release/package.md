# WEPP 261029 promotion and scientific report

Status: completed and pushed, 2026-10-30 UTC. Promoted the reviewed matched Linux pair
and published revision 1 of the report describing the local-input, hourly timing,
shared ET and fixed-width output repairs, with retained portability changes.
Existing defaults and production deployment are unchanged.

[Completed plan](prompts/completed/release_execplan.md) · [Tracker](tracker.md).
Normative decision: [ADR-0112](../../adrs/ADR-0112-native-negative-balance-local-inputs.md).
Scientific program: [Roads parameterization](../20261029_roads_parameterization_program/package.md).

Native implementation and review evidence live in the canonical default checkout
`/workdir/wepp-forest-release-20261009`, under the 20261029 local-input and
20261030 hourly-return work packages. The frozen candidate passes 663 native
tests, 13 watchlist cases, 99 Disturbed tests, 96/96 Roads development cases and
full Cedar execution/artifact checks. Independent scientific, implementation and
publication reviews accepted the bounded release; matched pair and reviewed PDF
are vendored. Actual runtime selection/readers and HTTP download checks pass.
The final broad WEPPpy suite passes 12,210 tests with 298 skips. Native release
47183b0fb and WEPPpy promotion 7077dc7ca are pushed.

No new service, dependency, authority or authentication change. Only the matched
executables/sidecars and reviewed public PDF/manifest are published; native
source patches and raw evidence remain internal.

Security impact: low. No new service, privilege, auth, execution boundary or
external dependency; dedicated security review is not required. Complexity budget:
existing matched executables/sidecars, fixtures, docs and existing discovery paths.
[Correctness review](artifacts/20261030_correctness_review.md) records generated
artifact readback and supported/legacy states.

Final evidence: [gate summary](artifacts/final-gates.json),
[validation](artifacts/validation.md), and [illustrated report (PDF)](/weppcloud/static/reports/wepp/release-notes/wepp_261029/wepp_261029_release-notes-r1.pdf).
The Roads program continues with withheld-soil/geometry validation and its
parameterization view; this package does not accept Roads defaults.

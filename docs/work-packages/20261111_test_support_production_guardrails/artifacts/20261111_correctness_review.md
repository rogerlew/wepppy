# Correctness review — F7

Reviewer: `contract_correctness` (independent read-only reviewer), 2026-11-12 UTC.
Contract ancestor: `21a75b794`; reviewed implementation recorded in `c2507338f`.
Verdict: source approved; M4/release acceptance HOLD.

## Valid states and evidence

| State | Required outcome | Evidence/disposition |
| --- | --- | --- |
| Absent/empty/production profile, flag false | startup; no support rules | configuration matrix; actual full app 484 rules, zero support |
| Production with flag true | fail before secrets | focused configuration test |
| Development/test, flag false | normal startup; no support rules | configuration and URL-map tests |
| Development/test, flag true, scoped JWT | ping/create/delete payloads preserved | component tests; real create/page pass; NFS delete fails absence |
| Missing/invalid/expired/wrong-audience credential | 401 before side effects | real signing and filesystem sentinel tests |
| Valid credential without scope | 403 before side effects | sentinel and real signing tests |
| Cookie without bearer | no authority | CSRF-enabled Flask client tests |
| Unknown profile | actionable startup failure | configuration matrix |
| Legacy anonymous smoke caller | migration through automatic wrapper/helper | all six consumers migrated; live wrapper acceptance pending |
| Issuer unavailable/malformed output | stop before ping/npm; no raw output | real mint-helper failure and CLI tests |
| Delete cannot remove path | must not count as cleanup acceptance | actual NFS 200 plus remaining directory retained as blocker |

## Findings and disposition

- Medium: native Node test lived in Playwright discovery directory. Moved to
  `tests/node`; npm test runs it explicitly. Independent discovery recheck passed.
- Medium: helper rejected configured custom application prefixes. It now accepts
  the configured prefix plus legacy root/weppcloud aliases; real HTTP regression
  independently passed.
- Preliminary traceback-local exposure was retracted after checking installed
  Typer defaults. Explicit no-local rendering now pins credential-handling intent.
- Independent operations review found a valid dev startup regression in lazy
  Flask consumers. Common Compose anchors now supply profiles; all eight
  full-stack consumers and both worker-only consumers were rendered and tested.

No unresolved medium/high changed-code finding. The unmocked cleanup failure is
not waived: source approval does not establish runtime acceptance. See
[validation](20261112_validation.md) for exact commands and limitations.

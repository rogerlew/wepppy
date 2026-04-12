# WP-09B Work Package: Parser Containment and GDAL CVE-2026-4738 Remediation
Status: not_started
Last Updated: 2026-04-12
Owner: Codex (WP-09B authoring)
Parent Plan: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md`
Primary Spec: `/workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md`

## Objective
Resolve both residual security risks deferred at WP-09 closeout:
1. Replace timeout/cancellation-only parser containment with explicit subprocess process-group kill semantics.
2. Remove release-cut uncertainty for `CVE-2026-4738` by remediating the shape-converter GDAL runtime (upgrade or patch backport) and recording verifiable evidence.

This package is complete only when all WP-09B gates pass:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

## Scope
### In scope
- Implement parser execution boundary for inspect/convert geospatial parsing and conversion steps:
  - dedicated subprocess boundary,
  - process-group creation,
  - hard timeout,
  - deterministic SIGTERM -> SIGKILL escalation for full process group on timeout/cancel.
- Preserve existing API error contract and request-scoped cleanup behavior while introducing subprocess containment.
- Remediate `CVE-2026-4738` exposure risk for shape-converter runtime by either:
  - upgrading to fixed GDAL line (`>=3.11.0`), or
  - applying and documenting patch/backport evidence with equivalent fix.
- Add targeted unit/integration regressions proving subprocess timeout/kill paths and no regression in canonical inspect/convert behavior.
- Capture local and hosted CI evidence for release-cut confidence after remediation.
- Run dedicated code, QA, and security reviews and disposition all Medium/High findings.
- Update implementation-plan board state and evidence notes.

### Out of scope
- WEPPcloud route/controller feature changes.
- Shape-converter API contract expansion unrelated to containment/CVE remediation.
- Cross-request artifact staging (explicitly remains disallowed).

## Constraints and Invariants
- Follow AGENTS.md instructions (root + nearest).
- No branch creation unless explicitly requested by human operator.
- Do not modify unrelated dirty files.
- Explicitly ignore dirty generated file `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Keep inspect/convert independent uploads; no cross-request staging.
- Keep WEPPcloud route/controller changes out of scope.
- Preserve canonical API error contract (`error.code`, `error.message`, `error.details`).
- Do not hand-edit generated `.github/workflows/*.yml`; edit `.github/forest_workflows/*.yml` and regenerate via `scripts/build_forest_workflows.py`.

## Required WP-09B Risk-Closure Contract
1. Parser non-termination containment implementation
   - Runtime parser path no longer relies only on outer request timeout.
   - Parser/convert subprocesses run in isolated process groups.
   - Timeout/cancel handling sends termination to entire process group and escalates to kill if needed.
   - No scratch-leak regressions on timeout/cancel/failure paths.
2. GDAL CVE-2026-4738 remediation
   - Shape-converter runtime demonstrates fixed/mitigated GDAL for `CVE-2026-4738`.
   - Evidence includes concrete runtime version and patch provenance.
   - Security disposition explicitly states whether Debian tracker state is still external/pending and why service runtime is still safe.
3. Regression and gate evidence
   - Focused/full shape-converter unit and integration gates pass.
   - Manual proxied smoke checks pass.
   - Hosted shape-converter gate workflow shows success on remediation commit.
4. Review closure
   - Code/QA/security reviews executed.
   - All High findings closed.
   - Medium findings closed or explicitly deferred with owner/date and risk acceptance rationale.

## Review and Disposition Requirements (Mandatory)
Execute all three review tracks before closing WP-09B:
1. Code review
   - Review parser subprocess orchestration, signal handling, cleanup contracts, and dependency/runtime changes.
2. QA review
   - Review gate outputs and proxied smoke matrix for regressions.
3. Security review
   - Review process-group kill semantics, CVE remediation evidence, and residual-risk register.

Disposition policy:
- Critical/High findings: must be fixed before WP close.
- Medium findings: must be fixed or explicitly deferred with rationale, owner, and target follow-up.
- Low findings: may be deferred with rationale.

Disposition ledger (fill during execution):
| Finding ID | Reviewer Track | Severity | Summary | Disposition | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| CR-01 | code | TBD | TBD | Open | TBD | TBD |
| QA-01 | qa | TBD | TBD | Open | TBD | TBD |
| SEC-01 | security | TBD | TBD | Open | TBD | TBD |

Medium/High disposition status: **TBD**.

## Target File Plan
Expected new/modified files for WP-09B (adjust only if justified):
- `wepppy/microservices/shape_converter/convert.py`
- `wepppy/microservices/shape_converter/inspect.py` (if parser boundary touches inspect path)
- `wepppy/microservices/shape_converter/app.py` (timeout/orchestration glue as needed)
- `wepppy/microservices/shape_converter/*` (new subprocess runner module if introduced)
- `tests/shape_converter/unit/test_convert_endpoint.py`
- `tests/shape_converter/unit/test_inspect_endpoint.py`
- `tests/shape_converter/unit/test_cleanup_lifecycle.py`
- `tests/shape_converter/integration/test_convert_api.py`
- `tests/shape_converter/integration/test_inspect_api.py`
- `docker/Dockerfile.dev` and/or other runtime build manifests used by `shape-converter` service
- `docker/docker-compose.dev.yml` and production compose files (if shape-converter runtime image wiring changes)
- `wepppy/microservices/shape_converter/docs/work-packages/wp-09b_parser_containment_and_gdal_cve_remediation.md`
- `wepppy/microservices/shape_converter/docs/implementation-plan.md`
- `wepppy/microservices/shape_converter/docs/specification.md` (only if contract wording changes)

## Implementation Steps (Execute Sequentially)
1. Confirm baseline parser path and signal-handling gap in current runtime code.
2. Implement subprocess parser boundary with process-group creation and timeout/cancel kill escalation.
3. Add deterministic unit tests for timeout/cancel group-termination path and canonical error payload preservation.
4. Add integration tests covering timeout/cancel behavior through API endpoints and cleanup invariants.
5. Remediate GDAL runtime for `CVE-2026-4738` (upgrade or backport patch) and document provenance.
6. Rebuild shape-converter runtime and capture version evidence from running container.
7. Run required focused/full gates and smoke matrix.
8. Capture hosted CI success evidence for shape-converter gate workflow on remediation commit.
9. Run code/QA/security reviews and disposition all findings.
10. Update this WP evidence log and implementation-plan row with final go/no-go and residual risks.

## Commands and Validation
## Focused unit iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit -k "archive or inspect or convert or cleanup or abuse or hardening or ui or health or crs or serialization" --maxfail=1
```

## Full unit gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/unit
```

## Focused integration iteration
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration -k "inspect or convert or abuse or hardening or ui" --maxfail=1
```

## Full integration gate
```bash
cd /workdir/wepppy
wctl run-pytest tests/shape_converter/integration
```

## Security hygiene check for changed files
```bash
cd /workdir/wepppy
python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
```

## Workflow generation consistency checks
```bash
cd /workdir/wepppy
scripts/build_forest_workflows.py
scripts/build_forest_workflows.py --check
```

## Runtime build/version evidence (CVE remediation)
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml build shape-converter
docker compose -f docker/docker-compose.dev.yml up -d shape-converter caddy
docker exec wepppy-shape-converter ogr2ogr --version
docker exec wepppy-shape-converter /opt/venv/bin/python -c "import fiona, pyproj; print(fiona.__version__, fiona.__gdal_version__, pyproj.__version__, pyproj.proj_version_str)"
```

## Manual proxied smoke checks
```bash
cd /workdir/wepppy
docker compose -f docker/docker-compose.dev.yml up -d caddy shape-converter

# inspect success path
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  http://127.0.0.1:8080/utils/shape-converter/v1/inspect

# convert success path
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<valid_zip>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert

# convert canonical error path (unknown CRS)
curl -i -H 'X-Forwarded-Proto: https' \
  -F 'archive=@<zip_missing_prj>' \
  -F 'output_format=geojson' \
  -F 'target_crs=wgs84' \
  http://127.0.0.1:8080/utils/shape-converter/v1/convert
```

## Hosted CI evidence checks
```bash
cd /workdir/wepppy
gh run list --workflow "Shape-Converter Gates" --limit 5 --json databaseId,status,conclusion,headSha,createdAt,url
```

Expected:
- Parser timeout/cancel containment is enforced via process-group kill semantics.
- GDAL runtime evidence demonstrates `CVE-2026-4738` mitigation for shape-converter service.
- Required local/hosted gates pass.

## Gate Checklist
## Code gate
- [ ] WP-09B implementation scope complete.
- [ ] Code review completed and findings dispositioned.
- [ ] Lint/static checks for touched files pass.

## Shape-converter unit-test gate
- [ ] Focused unit iteration command passes.
- [ ] `wctl run-pytest tests/shape_converter/unit` passes.

## QA gate
- [ ] Focused/full integration commands pass.
- [ ] Manual proxied smoke checklist completed.
- [ ] QA review findings dispositioned.

## Security review gate
- [ ] Parser subprocess process-group timeout/kill semantics are implemented and validated.
- [ ] GDAL `CVE-2026-4738` remediation evidence is captured and dispositioned.
- [ ] Security review findings dispositioned (no unresolved High findings).

## Evidence Log (Fill During Execution)
| Item | Evidence |
| --- | --- |
| Commit SHA(s) | TBD |
| Parser containment implementation evidence | TBD |
| GDAL CVE remediation evidence | TBD |
| Unit gate output | TBD |
| Integration gate output | TBD |
| Workflow generation output | TBD |
| Hosted CI evidence | TBD |
| QA smoke output | TBD |
| Code review reference | TBD |
| QA review reference | TBD |
| Security review reference | TBD |
| Disposition ledger summary | TBD |
| Final go/no-go decision | TBD |
| Residual risks register | TBD |

## Completion Criteria
WP-09B is `done` only when:
- All four gates are `pass` (or explicitly waived with rationale/approver).
- Parser process-group kill semantics are in production runtime path and test-validated.
- GDAL `CVE-2026-4738` remediation evidence is recorded for shape-converter runtime.
- Code/QA/security findings are fully dispositioned and recorded.
- Implementation-plan board is updated with final WP-09B state and evidence.

## Agent Execution Prompt (E2E)
Use this prompt to run WP-09B end-to-end with mandatory reviews/dispositions:

```text
You are working in /workdir/wepppy.

Execute WP-09B end-to-end using:
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/work-packages/wp-09b_parser_containment_and_gdal_cve_remediation.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/implementation-plan.md
- /workdir/wepppy/wepppy/microservices/shape_converter/docs/specification.md

Goal:
Deliver WP-09B by resolving both residual security risks:
1) parser non-termination containment gap (process-group kill semantics), and
2) GDAL CVE-2026-4738 remediation evidence for shape-converter runtime.

Required gates:
- Code gate
- Shape-converter unit-test gate
- QA gate
- Security review gate

Hard constraints:
- Follow AGENTS.md instructions (root + nearest).
- Do not create/switch branches.
- Do not modify unrelated files.
- Explicitly ignore dirty generated file: wepppy/weppcloud/routes/usersum/generated/docs_index.json.
- Keep WEPPcloud route/controller changes out of scope.
- Keep inspect/convert as independent uploads (no cross-request staging).
- Do not edit generated workflow files directly under `.github/workflows/`; update `.github/forest_workflows/` specs and regenerate via `scripts/build_forest_workflows.py`.

Implementation outcomes:
1. Implement and validate parser subprocess process-group timeout/cancel kill semantics.
2. Remediate shape-converter GDAL runtime for CVE-2026-4738 (upgrade or patch-backport with evidence).
3. Add/extend unit+integration tests for containment and cleanup invariants.
4. Run required local validation gates and proxied smoke matrix.
5. Capture hosted `Shape-Converter Gates` CI success evidence on remediation commit.
6. Run code/QA/security reviews and disposition all Medium/High findings.
7. Update WP-09B evidence and implementation-plan WP-09B row.

Final response format:
- Findings first (bugs/risks/blockers with file:line), if any.
- Then concise change summary with exact files touched.
- Include exact validation commands run and outcomes.
- Include code/QA/security review findings and explicit dispositions.
- Include final go/no-go decision.
- Include residual risks (if any) with owner and target follow-up.
```

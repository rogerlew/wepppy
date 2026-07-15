# Security Review - Dependabot PR Triage and Local Stack Rebuild

## Metadata

- **Package**: `docs/work-packages/20260715_dependabot_pr_triage_stack_rebuild/`
- **Reviewer**: Codex
- **Date**: 2026-07-15
- **Scope reviewed**: all 37 frozen Dependabot PR heads and the 35-update
  aggregate merge candidate, followed by the merged-master local rollout
- **Commit/branch context**: package opened at `cc31c121f`; merged rollout at
  `1c4fd3c50`
- **Related artifacts**:
  - PR decisions: `artifacts/pr_decisions.md`
  - Validation: `artifacts/validation.md`

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: open PRs affect authentication, JWT, cryptography,
  multipart and markup parsing, network clients, and production build inputs.
- **Threat model assumptions**:
  - Dependabot branches are untrusted supply-chain inputs until their exact
    manifests, upstream source, and resolved lock changes are reviewed.
  - Existing application auth, CSRF, upload, proxy, and path contracts must not
    widen as an incidental dependency effect.
  - No GitHub merge/close action occurs as part of this review.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Docker and CAO cryptography | Version 46.0.7 fixes CVE-2026-39892, a noncontiguous buffer overflow. | Upstream cryptography changelog; PRs #548/#549; rebuilt image and CAO tests | Merge both paired updates first | Resolved in candidate |
| SEC-02 | High | Docker XML parsing | lxml 6.1.0 fixes CVE-2026-41066 in `iterparse()` and `ETCompatXMLParser`. | Upstream lxml change record; PR #562; aggregate parser tests | Prioritize merge despite major version | Resolved in candidate |
| SEC-03 | High | Native geospatial build | GDAL 3.13 bindings cannot build against the image's libgdal 3.10.3. Forcing the Python pin would produce an invalid native stack. | Reproduced no-cache build failure for PR #570 | Defer to coordinated base-image/libgdal migration | Mitigated by exclusion |
| SEC-04 | Medium | Docker ASGI framework | PR #576 targets stale Starlette 1.0.1 while current compatible releases are newer; merging it independently risks an obsolete framework lock. | PR target comparison and FastAPI compatibility review | Close/recreate as a current FastAPI/Starlette pair | Mitigated by exclusion |
| SEC-05 | Medium | Major build/MCP dependencies | Vite 8 and FastMCP 3 include documented migration changes. | UI clean install/lint/build; CAO locked install, import smoke, and 20 tests | Merge only the tested exact lock resolutions | Resolved in candidate |

## Verdict

- **Gate status**: `pass` for the 35-PR merge candidate.
- **Unresolved findings**:
  - High: 0 in the merge candidate
  - Medium: 0 in the merge candidate
  - Low: 0
- **Release recommendation**: satisfied. Security fixes and the tested updates
  were incorporated in ecosystem batches; #570, recreated #586, and #576 were
  excluded and closed.

## Surface Checks

### Auth, Session, and Authorization

- [x] Authlib, PyJWT, cryptography, Starlette, and related transitive changes
  preserve token/session/authorization behavior.

### Secrets and Credential Handling

- [x] Candidate changes only dependency manifests and introduce no secret
  defaults, logs, or build arguments.

### Input Validation and Output Safety

- [x] Multipart, lxml, Mistune, Pillow, and nbconvert updates preserve upload,
  rendering, and parser boundaries.

### Queue, Worker, and Subprocess Surfaces

- [x] Container and worker dependency changes pass focused tests and the
  aggregate suite through the recorded non-dependency test-infrastructure
  exceptions.

### Network and External Integrations

- [x] urllib3, idna, Tornado, Starlette, and CAO HTTP behavior remain compatible.

### CI/CD and Supply Chain

- [x] Every candidate dependency has repository precedent and an upstream
  release within the existing ecosystem.
- [x] Lockfiles resolve without unexpected new package sources or executable
  install hooks.
- [x] Container rebuild uses the reviewed manifests and exact candidate base.

### Logging, Monitoring, and Incident Readiness

- [x] Stack startup, service health, and rollback commands are recorded.

## Validation Evidence

The no-cache candidate image rebuilt after excluding GDAL #570. The complete
stack was recreated from the candidate, `/health` checks passed, and installed
versions were inspected in the running containers. Static npm lint plus 629
tests passed; UI lab lint plus production build passed; CAO installed from its
locked resolution and all 20 declared service tests passed. Full-suite details,
including two preexisting test-infrastructure exceptions, are recorded in
`artifacts/validation.md`.

The subsequent merged-master no-cache build and local redeploy also passed.
The primary stack retained the reviewed security versions, both health endpoints
returned `OK`, and the complete controlled Python run passed 4,897 tests with 58
skips. No new security finding arose during the merged rollout.

## Residual Risk

- **Accepted residual risks**: major updates retain normal regression risk, so
  newly generated Dependabot heads must be reviewed rather than assumed
  equivalent to this frozen candidate.
- **Follow-up packages/issues**:
  - GDAL 3.13 base image and native library migration for #570.
  - Current Docker FastAPI/Starlette lock update replacing #576.
  - Test-isolation cleanup for the synthetic Flask module in the Daymet test.

## Sign-off

- **Security reviewer**: Codex, pass for the 35-update merge candidate
- **Package owner**: 35 reviewed intents incorporated; 34 PRs report `MERGED`
  and auto-superseded #564 is retained through exact reviewed merge ancestry

## Upstream References

- [cryptography changelog](https://cryptography.io/en/stable/changelog/)
- [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/)
- [FastMCP 2 to 3 migration](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2)
- [Vite 8 migration guide](https://vite.dev/guide/migration.html)

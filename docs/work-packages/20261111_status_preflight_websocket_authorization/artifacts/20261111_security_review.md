# Security review - Status and preflight WebSocket run authorization

**Status**: Pending implementation and independent security review  
**Date opened**: 2026-11-11 UTC  
**Reviewer**: Unassigned  
**Security impact**: High

## Threat Model Under Review

- Assets: private run/status/preflight data, Redis channels, browser sessions,
  signing keys and deployment configuration.
- Adversaries: anonymous and unrelated authenticated callers, cross-run token
  replay, hostile Origins, XSS-assisted token theft, and accidental credential
  logging.
- Boundaries: mint route, browser memory, WebSocket protocol header, Caddy,
  status2/preflight2 validation, Redis DB 11 session state and stream Redis.
- Required invariant: no socket acceptance or run-specific Redis access without
  a valid, live, least-privileged credential for that exact run and service.

## Required Security Checks

- [ ] Canonical contract, public/private matrix and lifetime are ratified before
      implementation; any threshold ADR is accepted.
- [ ] A vetted verifier rejects disallowed algorithms, forged signatures,
      malformed claims and ambiguous audience/scope forms.
- [ ] Issuer, audience, token class, scope, run/config, time and live
      marker/revocation checks all fail closed.
- [ ] Both services authenticate before `websocket.Accept` and before selecting
      or subscribing to a run Redis channel.
- [ ] Token minting reuses canonical run access and same-origin session/CSRF
      controls without broadening public access.
- [ ] Browser transport does not place credentials in URLs, localStorage,
      selected protocols, logs, traces, screenshots, videos or retained output.
- [ ] Credential cache/refresh lifetime is bounded and reconnect does not create
      an unauthenticated fallback or denial-of-service loop.
- [ ] Exact Origins are configured; empty values fail closed outside any
      explicit default-off local mode; Origin is not authorization.
- [ ] Signing material is mounted from a secret file with no tracked/default
      value or raw Compose environment exposure.
- [ ] Service errors and audit logs are useful but contain no token, private path,
      exception detail or sensitive option value.
- [ ] Message-field inventory and redaction cover every confirmed publisher and
      consumer without claiming F5's general error contract.
- [ ] Cross-run, revoked-session, wrong-audience/scope and hostile-Origin tests
      directly exercise both services and assert no Redis access.
- [ ] Forest Playwright evidence is sanitized and bound to the reviewed revision
      and redeployed container identities.
- [ ] Rollback preserves service availability but is not mislabeled as SEC-04
      closure when it restores unauthenticated behavior.

## CWE / OWASP Mapping

- CWE-862: Missing Authorization
- CWE-639: Authorization Bypass Through User-Controlled Key
- CWE-922: Insecure Storage of Sensitive Information, if credentials leak
- OWASP Top 10 2021 A01: Broken Access Control
- OWASP Top 10 2021 A02: Cryptographic Failures, for credential lifecycle and
  secret-handling defects

## Findings

Populate with severity, affected location, concrete attack path, exploitability,
business impact, correction, regression evidence and disposition. A unit-test
pass without actual forest frontend evidence is insufficient for this package.

## Gate Verdict

**FAIL / PENDING** - the security-sensitive implementation and mandatory forest
acceptance do not yet exist. This scaffold does not close F4/SEC-04.

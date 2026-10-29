# Security review — project developer mode

Reviewer: `/root/contract_security`, 2026-10-29 UTC. Scope: implementation after contract ancestor `44746ff63`, paired native commit `4d4c075`, and local boundary evidence. Security impact: high (privileged public activation route).

## Verdict

Pass for inspected implementation and local boundary evidence; no unresolved medium/high security findings. This is not production deployment approval. Exact Dev membership authorizes dedicated activation; normal project authorization governs later operations. Archive/failed-fork recovery uses incoming state by explicit operator decision.

## Findings and disposition

SEC-IMP-01 (medium): initial header edits inadvertently exposed the TTL control to Dev-only users. Restored original PowerUser/Admin/Root TTL gates in both headers; `test_dev_only_header_does_not_grant_ttl_control` covers both. Independent reviewer confirmed closure.

## Surface checks and evidence

- Real project authorization, CSRF, readonly and locked Ron persistence: `test_developer_activation_real_authorization_and_persistence`; identity/path/ownership lookups are scoped, authorization and persistence boundaries are real. Denied requests preserve state; allowed Dev requests persist it.
- Exact roles, malformed/spoofed payloads and CSRF: `tests/weppcloud/routes/test_project_bp.py`; ordinary Admin/Root/PowerUser alone cannot activate.
- Role presentation: Dev-only panel gets no other action grid; both header TTL regressions pass. Successful action updates maxima without losing unsaved values; failure requires readback.
- State integrity: strict booleans, missing-false legacy state, stale-controller fresh hydration and real lifecycle-guard barrier tests in `tests/nodb/test_project_developer_mode.py`.
- Lifecycle: actual archive/restore incoming-state tests and capture interleaving pass; failed-fork endpoint replacement plus real rsync tests cover true/false/missing mode. Queue admission in the recovery test is stubbed; completed real fork-worker evidence complements it.
- Native trust: policy originates from Ron, not user payload; finite/minimum checks remain; native default is normal mode. Paired pin and release receipt are retained.
- Secrets, network egress, CI, queue topology and unrelated entitlements unchanged. Existing project tools expose generated artifacts; no new hidden artifact surface.

## Runtime evidence and limits

`runtime.json` and `validate_runtime.py` retain actual local Flask activation with CSRF and a synthetic request principal, ordinary no-Dev parsing, completed RQ preparation/model/fork jobs and real output readback. No database accounts or roles were changed. `browser.json` verifies public project presentation and normal browse/download hashes. This does not establish a separately provisioned Dev account's login flow; existing authentication is unchanged. Production deployment remains separate.

Reviewer sign-off: independent security reviewer confirmed implementation pass and SEC-IMP-01 closure; generated-output/browser evidence and correctness acceptance remain separately recorded in the validation/correctness artifacts.

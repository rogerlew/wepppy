# WP-10 Execution Prompt: QA/Security Closeout and Release Readiness

Use this prompt verbatim in a new Codex/Copilot session to execute WP-10.

---

Execute WP-10 end-to-end for Geneva and close the package.

Authoritative docs:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/specification.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-09_end_to_end_integration_and_performance_validation.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-10_qa_security_closeout_and_release_readiness.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-02_rust_hru_hsg_kernel_prepare_hrus.md`

Scope (must complete):
1. Consolidate Geneva package evidence for WP-00..WP-09 and produce a final unresolved-risk inventory.
2. Resolve any remaining fix-now findings (including pre-existing in-review blockers) or record explicit, bounded waivers with owner and rationale.
3. Run final release-readiness validation gates for both repos and capture exact outcomes.
4. Execute final release-candidate manual smoke checks through Geneva results/query/report flow and record observations.
5. Produce explicit go/no-go recommendation with rationale, residual risks, and mitigation ownership.
6. Complete code review, QA review, and security review; resolve fix-now findings before closeout.
7. Update WP-10 evidence and implementation-plan row to `done` only after all required gates/manual checks pass and recommendation is documented.

Required gates (`/workdir/wepppy`):
- `cd /workdir/wepppy && wctl run-pytest tests/nodb/mods/geneva --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests/nodb --maxfail=1`
- `cd /workdir/wepppy && wctl run-pytest tests --maxfail=1`
- `cd /workdir/wepppy && wctl doc-lint --path wepppy/nodb/mods/geneva`
- `cd /workdir/wepppy && python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`
- `cd /workdir/wepppy && wctl check-rq-graph` (required only if queue wiring changes)

Required kernel gates (`/workdir/wepppyo3`) for release closeout:
- `cd /workdir/wepppyo3 && cargo test -p geneva_core`
- `cd /workdir/wepppyo3 && cargo test -p cli_revision`
- `cd /workdir/wepppyo3 && cargo fmt --check`
- `cd /workdir/wepppyo3 && cargo clippy --all-targets -- -D warnings`

UI gates (only if frontend/templates/js touched in WP-10):
- `cd /workdir/wepppy && wctl run-npm lint`
- `cd /workdir/wepppy && wctl run-npm test`

Mandatory review workflow:
- Code review
- QA review
- Security review
- Resolve fix-now findings before closeout

Evidence updates required:
- `/workdir/wepppy/wepppy/nodb/mods/geneva/work-packages/wp-10_qa_security_closeout_and_release_readiness.md`
- `/workdir/wepppy/wepppy/nodb/mods/geneva/implementation-plan.md` (WP-10 row state/gates/evidence link)

Manual integration evidence required:
- Final release-candidate Geneva smoke run through results/query/report surface.
- Record consistency observations for status/warnings/query/report payloads.
- Record any residual limitations and mitigation/ownership.

Constraints:
- Do not modify `wepppy/weppcloud/routes/usersum/generated/docs_index.json`.
- Ignore unrelated dirty files outside Geneva/WP-10 scope.
- Keep scope bounded to WP-10 closeout; do not start post-release feature work.

---

# Accepted checkpoint commit scope

Prepared 2026-10-30 23:38 UTC. Commit authority pending. Intended standalone
commit message: `Establish malformed-request side-effect repair contract`.
Do not include source implementation or unrelated working-tree changes.

## Complete paths

- `docs/schemas/request-payload-contract.md`
- `docs/schemas/rq-response-contract.md`
- `docs/schemas/rq-webhook-contract.md`
- `docs/schemas/wepp-run-input-contract.md`
- `docs/schemas/single-user-defined-inputs-contract.md`
- `docs/schemas/rq-engine-agent-api-contract.md`
- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/ui-docs/contracts/wepp-hillslope-clipping-contract.md`
- `docs/work-packages/20261030_malformed_request_side_effects/` (package, plan,
  retained operator request, matrix, safe diagnostic probe/baseline, reviews,
  tracker and this manifest)

## Partial path

`PROJECT_TRACKER.md`: include only the new MRS-01 Active entry. The file already
contained unrelated Roads/release changes at task start; do not stage its whole
diff. Compare the staged diff to this allowlist before committing.

After explicit authority, create this checkpoint commit, record its SHA in the
package tracker and verify it is an ancestor of implementation. Do not create or
switch branches. Historical packages, ADR/road changes and generated usersum index
remain outside the commit.

## Executed verification

- Safe baseline probe: ten actual HTTP cases in each framework, production
  parsers invoked through probe endpoints, no project/queue access. Output in
  `parser-baseline.jsonl`; malformed JSON returned empty payloads in both.
- `wctl doc-lint --path <path>`: all eight canonical files and PROJECT_TRACKER
  individually passed, zero errors/warnings; package directory passed.
- `git diff --check`: passed.
- `uk2us` preview: new package wording normalized; unrelated existing CSRF
  `non-public` retained to avoid scope churn.
- Independent reviews: both approved checkpoint, no medium/high contract findings.
- Production tests, persistence/upload/WAM-01 regressions and full suite: pending
  implementation; not represented as passing. No deployment or production jobs.

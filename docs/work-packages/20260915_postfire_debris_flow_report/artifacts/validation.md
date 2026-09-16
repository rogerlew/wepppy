# Documentation and review-role validation

Date: 2026-09-15 UTC. Scope: proposal, work package, module links, project board,
`.codex/config.toml` and `.codex/agents/ux_reviewer.toml`.

## Checks

- `wctl doc-lint --path docs/ui-docs/contracts/postfire-debris-flow-report-contract.md`: pass.
- `wctl doc-lint --path docs/work-packages/20260915_postfire_debris_flow_report`: pass.
- `wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow/specification.md`: pass.
- `wctl doc-lint --path wepppy/nodb/mods/postfire_debris_flow/implementation_roadmap.md`: pass.
- `wctl doc-lint --path PROJECT_TRACKER.md`: pass.
- `git diff --check`: pass.
- `uk2us` spelling previews: new documents unchanged; existing-document preview
  reviewed without unrelated prose normalization.
- Python `tomllib` parsing of both configuration files: pass; `ux_reviewer`
  registration resolves to an existing role with matching name, description and
  nonempty instructions. No model/tool/permission/concurrency changes.

Completed prompts moved with `wctl doc-mv --force`, preserving inbound links.
All package cross-references are retained; review artifacts remain inspectable.

## Independent review evidence

[Correctness](20260915_correctness_review.md),
[security](20260915_security_review.md) and [UX](20260915_ux_review.md)
all include independent post-amendment confirmations. The
[disposition](review_disposition.md) closes all recorded findings.

The UX role follows existing project role registration and
[official custom-agent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents#custom-agents)
for standalone name/description/instructions. No runtime discovery reload was
tested; this session's independent UX reviewer used the retained explicit brief.

## Evidence limits

No Python/frontend application suite, live report browser test, human user study,
model rerun or deployment was performed: no application code changed. The future
implementation plan names those gates. No commit/push or owner ratification of
exact proposed UX is claimed. Unrelated dirty `code-quality-report.json` and
`code-quality-summary.md` are preserved outside this change set.

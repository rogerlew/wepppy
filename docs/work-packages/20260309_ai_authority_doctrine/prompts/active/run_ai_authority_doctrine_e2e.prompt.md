# Prompt: Advance AI Authority Doctrine Package End-to-End

You are advancing the AI authority doctrine package for WEPPpy.

## Mandatory startup
1. Read `/workdir/wepppy/AGENTS.md`.
2. Read `/workdir/wepppy/AI_AUTHORITY_DOCTRINE.md`.
3. Read `/workdir/wepppy/AI_AUTHORITY_OPERATING_PRACTICES.md`.
4. Read `/workdir/wepppy/docs/work-packages/20260309_ai_authority_doctrine/package.md`.
5. Read `/workdir/wepppy/docs/work-packages/20260309_ai_authority_doctrine/tracker.md`.
6. Read `/workdir/wepppy/docs/work-packages/20260309_ai_authority_doctrine/prompts/active/ai_authority_doctrine_execplan.md`.
7. Read `/workdir/wepppy/AGENTIC_AI_SYSTEMS_MANIFESTO.md`.
8. Read `/workdir/ghosts-in-the-machine/dialectic-003-the-authority-vacuum.md`.
9. Read `/workdir/wepppy/compliance/eu-ai-act.md`.
10. Read `/workdir/wepppy/compliance/NIST.AI.600-1.md`.
11. Read `/workdir/wepppy/compliance/NIST.SP.800-218A.md`.

## Execution rule
Follow the active ExecPlan milestone-by-milestone. Keep plan `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` synchronized while drafting.

## Required scope
1. Preserve the existing Draft 1 doctrine and operating-standard content unless a contradiction or compliance issue requires revision.
2. Preserve the existing task-class execution matrix unless discussion or validation exposes a real classification defect.
3. Preserve the existing minimum-sufficient evidence and succession breadcrumb rules unless discussion or validation exposes a real gap.
4. Preserve the existing hybrid record-location model unless discussion or validation exposes a real contradiction.
5. Preserve the lightweight templates for authority grants, competence reviews, and revocation or tripwire handling unless discussion exposes a real contradiction or missing field.
6. Keep `package.md`, `tracker.md`, the active ExecPlan, and `PROJECT_TRACKER.md` current.
7. If no contradiction or missing case is found, move the package toward review and closeout rather than adding more open-ended doctrine text.

## Required gates
- `wctl doc-lint --path AI_AUTHORITY_DOCTRINE.md`
- `wctl doc-lint --path AI_AUTHORITY_OPERATING_PRACTICES.md`
- `wctl doc-lint --path PROJECT_TRACKER.md`
- `wctl doc-lint --path docs/work-packages/20260309_ai_authority_doctrine`
- `diff -u AI_AUTHORITY_DOCTRINE.md <(uk2us AI_AUTHORITY_DOCTRINE.md)`
- `diff -u AI_AUTHORITY_OPERATING_PRACTICES.md <(uk2us AI_AUTHORITY_OPERATING_PRACTICES.md)`

## Handoff format
Provide:
1. What changed in the doctrine and operating standard.
2. Whether Draft 2 operationalization remains incomplete or the package is now in review and closeout.
3. Compliance hooks added or refined.
4. Commands run and outcomes.
5. Remaining open questions and recommended next steps.

# Outcome (2026-01-12)
- Authored the observed schema usage report and captured open questions in the tracker.

# Agent Prompt: Error Schema Standardization Inventory

You are tasked with producing a comprehensive inventory of rq/api response schemas and their client usage so the team can standardize error handling and remove redundant `success`/`Success` flags.

## Goal
Author the report:
`docs/work-packages/20260111_error_schema_standardization/artifacts/observed-error-schema-usages-report.md`

## Scope
- **Backend endpoints**:
  - rq-engine: `wepppy/microservices/rq_engine/`
  - weppcloud rq/api routes: `wepppy/weppcloud/routes/` and related helpers
- **Client callsites**:
  - Frontend: `wepppy/weppcloud/controllers_js/`, `wepppy/weppcloud/static-src/`
  - Backend: any Python clients invoking rq/api or rq-engine routes
- **Schemas**: JSON payloads, HTTP status codes, and how `success`/`Success` is interpreted (redundant vs job-status semantics).

## Required Output Structure
Use this outline in the report and keep it terse:

1. **Summary of Observed Patterns**
   - List each distinct schema pattern (keys, casing, error fields) and the semantic meaning.
2. **Endpoint Inventory** (table)
   - Columns: Endpoint, Method, Status Codes, Response Schema (keys), Uses `success`/`Success`, Semantic Meaning, Callers.
3. **Client Callsite Inventory**
   - Frontend callsites with file paths and how they interpret responses.
   - Backend callsites with file paths and how they interpret responses.
4. **Redundancy Analysis**
   - Identify where `success`/`Success` duplicates HTTP status code meaning vs job lifecycle meaning.
5. **Recommendations (Draft)**
   - Proposed target schema rules (status-code-first, error payload shape, job status fields).
   - Risks and migration notes.

## Evidence Collection Tips
- Use `rg -n "Success|success" wepppy/` to locate response payloads and client checks.
- Cross-check `wepppy/microservices/rq_engine/responses.py` and any response helpers.
- Include endpoint definitions and their status code usage.
- For each callsite, note whether it checks HTTP status vs JSON body vs job status.

## Constraints
- Do **not** implement code changes.
- Keep documentation concise and factual.
- Use ASCII only.

## Deliverable
Save the report to:
`docs/work-packages/20260111_error_schema_standardization/artifacts/observed-error-schema-usages-report.md`

## Update Tracker
Add a progress note in:
`docs/work-packages/20260111_error_schema_standardization/tracker.md`

Include the date, what was inventoried, and any open questions.

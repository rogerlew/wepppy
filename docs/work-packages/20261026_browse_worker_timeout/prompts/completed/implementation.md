# Implement the production browse timeout

Outcome: literal timeout implementation and parser validation completed. Roger
subsequently expanded scope to filesystem transparency; the active ExecPlan
records that implementation and final package closure. No deployment occurred.

From /workdir/wepppy, add --timeout 120 only to the browse command in
docker/docker-compose.prod.wepp1.yml. Record the rationale in ADR-0108 and
the deployment tuning knowledgebase. Render the combined production Compose
configuration and parse its command through Gunicorn; confirm eight workers,
120-second timeout and 30-second graceful timeout. Run scoped doc lint and
git diff --check. Record review and validation, close the package, archive this
prompt and commit only this task's files. Do not deploy or include unrelated
query-catalog edits. This bounded literal edit does not require an ExecPlan.

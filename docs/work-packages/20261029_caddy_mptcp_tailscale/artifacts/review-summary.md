# Independent correctness and QA reviews

## Correctness

Reviewer: caddy_correctness_review, 2026-10-29. All five sysctl edits pass.
Rendered default dev/prod/wepp1 ports match HEAD, and Caddy adapts in generic HTTP
and named-host HTTPS modes. Finding: deploy-production.sh reads URLs directly from
docker/.env. Resolved by aligning host settings in docker/.env and root .env.
Documented exact-host health probes and expected body because wrong Host returns
an empty Caddy200. Runtime Redis refusal during recreation was investigated and
resolved; later stale PostgreSQL pools required both web processes to restart.

## QA

Reviewer: caddy_qa_review, 2026-10-29. Source review passes with no blocking
maintainability or test-quality findings. Optional bind prefixes preserve defaults,
the Redis exception is explicit, and configuration reuses existing Caddy/wctl.
Parser/default-parity checks and browser/runtime probes fit this configuration-only
scope; broad pytest expansion is unnecessary. Forest1 login remains unverified.

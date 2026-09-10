# Fixed-file publication amendment

Base contract ancestor: 5c0a172ee. Runtime upload/model/control first draft exists;
this amendment precedes adding the new fixed-file endpoint and removing the public
copy path. Intended protected model-file access is unchanged.

Use hidden complete bundles and accepted NoDb identity as sole publication
boundary. Fixed rq-engine export adapter streams four allowlisted files after
rq:export/run/config checks, accepted ID/signature validation and open-once handle
validation. Browser uses session-token blob download. No archive/path API.

Independent read-only reviews: contract_security approves; contract_correctness
approves 2026-09-10 21:29:09 UTC after using canonical rq:export scope. No open
high/medium amendment findings. Verify unauthorized/unaccepted attempts, valid
stale downloads, changed files and handle closure before runtime acceptance.

# WEPPcloud Authentication Tokens

This document describes the JSON Web Token (JWT) format issued by WEPPcloud and
the shared configuration used by downstream services (Query Engine MCP API,
R-based services, etc.).

## Environment Configuration

The token issuer (and any service that validates tokens) relies on the
following environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `WEPP_AUTH_JWT_SECRET` | **Required.** Shared HMAC secret. | – |
| `WEPP_AUTH_JWT_ALGORITHMS` | Comma separated list of allowed algorithms (`HS256`, `HS384`, `HS512`). | `HS256` |
| `WEPP_AUTH_JWT_ISSUER` | Optional issuer string (`iss` claim). | unset |
| `WEPP_AUTH_JWT_DEFAULT_AUDIENCE` | Optional audience automatically included in tokens. | unset |
| `WEPP_AUTH_JWT_DEFAULT_TTL_SECONDS` | Default lifetime for issued tokens. | `3600` |
| `WEPP_AUTH_JWT_SCOPE_SEPARATOR` | String used to join scope values. | single space |
| `WEPP_AUTH_JWT_LEEWAY` | Validation leeway in seconds for `exp`, `nbf`, `iat`. | `0` |

## Claims

Issued tokens contain the following fields:

- `sub` – Subject (user/service identifier).
- `scope` – Space-separated list of scopes (e.g. `runs:read queries:execute`).
- `runs` – Optional list of WEPPcloud run identifiers the token can access.
- `aud` – Audience string or list. Defaults to `WEPP_AUTH_JWT_DEFAULT_AUDIENCE`.
- `iss`, `iat`, `exp`, `nbf` – Standard JWT time/issuer claims.
- Additional custom claims are preserved verbatim.

Downstream services should verify signatures using
`WEPP_AUTH_JWT_SECRET` and ensure the audience and scopes are
appropriate for the requested operation.

## Token Issuance Utility

The script `_scripts/issue_auth_token.py` issues tokens from the CLI:

```bash
python -m wepppy.weppcloud._scripts.issue_auth_token user123 \
  --scope runs:read --scope queries:execute \
  --runs run-1,run-2 --audience query-engine --expires-in 900 \
  --json
```

Environment variables above must be set before running the script. The
`--json` flag prints both the token and the resolved claims, which is
handy for auditing.

## Validation

Token validation utilities live in `wepppy/weppcloud/utils/auth_tokens.py`.
They expose `decode_token` and reuse the shared configuration so
services can enforce identical requirements (issuer/audience/leeway).

For Python callers:

```python
from wepppy.weppcloud.utils.auth_tokens import decode_token

claims = decode_token(token, audience="query-engine")
```

If validation fails a `JWTDecodeError` is raised.

## Service Scopes

| Scope | Purpose |
| --- | --- |
| `runs:read` | List or fetch metadata about accessible runs. |
| `queries:validate` | Validate payloads against dataset schema. |
| `queries:execute` | Execute queries (POST to `/query`). |

Scopes are additive; downstream services should check presence before
performing an operation.


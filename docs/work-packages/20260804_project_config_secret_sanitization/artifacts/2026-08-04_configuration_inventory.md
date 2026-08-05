# WP00A Configuration Sanitization Inventory

## Corpus

The inventory at revision `5d43a8bb00` covers 270 tracked source files beneath
`wepppy/nodb/configs`: 130 top-level active/default files, 139 legacy files, and
one batch file. The scanner includes `.cfg` and `.toml` sources.

## Findings and Disposition

| Form | Occurrences | Classification | Disposition |
| --- | ---: | --- | --- |
| `[general] w3w_api_key` with one repeated literal | 7 | stale credential | Removed from `_defaults.toml`, three active presets, and three legacy sources |
| Other secret-bearing option names | 0 | prohibited | Scanner-enforced |
| Explicit runtime-host-bound keys | 0 | prohibited in materialized config | Scanner-enforced |
| Environment-variable references | 0 | prohibited | Scanner-enforced |
| `/run/secrets` or `docker/secrets` paths | 0 | prohibited | Scanner-enforced |
| Credential-bearing URIs | 0 | prohibited | Scanner-enforced |

Repository tracing found no read of `w3w_api_key` and no live What3Words API
client. `Ron.w3w` only reads persisted historical `_w3w` display state and does
not depend on the removed config key. There is therefore no runtime secret to
migrate or rotate within this package.

## Classification Contract

The materialization gate rejects keys containing secret-bearing tokens such as
API/access/private keys, passwords, secrets, tokens, or credentials. It rejects
the explicit runtime connection keys `host`, `hostname`, `port`, `socket`,
`socket_path`, `dsn`, `database_url`, `redis_host`, `redis_port`, and
`redis_url`. It also rejects environment references, runtime secret-file paths,
and URIs containing user information. Ordinary scientific paths, data roots,
dataset IDs, and public data URLs are not rejected merely for being strings.

Diagnostics are redacted by construction: violation records contain source,
location, key, and rule only. Raw values are neither stored nor rendered.

## Evidence

    project-config sanitization passed: 1 path(s)
    16 passed, 2 warnings

The two warnings are preexisting dependency deprecations from `pytz` and
`pyparsing`. Synthetic tests cover a generated config, recursive manifest,
project directory, ZIP archive, and tar archive.

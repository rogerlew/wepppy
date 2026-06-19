# Download Microservice

The download microservice serves critical exact WEPPcloud artifacts outside the interactive `browse` worker pool.

Initial scope is intentionally narrow:

- `GET /weppcloud/runs/{runid}/{config}/download/archives/{name}.zip`
- `HEAD /weppcloud/runs/{runid}/{config}/download/archives/{name}.zip`
- `GET /health`

It preserves the existing public archive URL shape. Caddy decides whether the exact archive route goes to `download:9011` or falls back to `browse:9009`.

## Boundary

`download` owns exact archive ZIP delivery only. `browse` remains responsible for directory listings, previews, schema/files APIs, D-Tale handoff, `gdalinfo`, aria2c manifests, parquet-to-CSV exports, culvert downloads, batch downloads, and all non-migrated compatibility routes.

The service reuses the canonical browse authorization and path security helpers:

- `wepppy.microservices.browse.auth`
- `wepppy.microservices.browse.security`
- `docs/schemas/weppcloud-browse-auth-contract.md`

## Range and Resume Behavior

Archive responses advertise `Accept-Ranges: bytes`.

Supported request forms:

- Full `GET` -> `200 OK`
- `HEAD` -> same metadata as `GET` without a response body
- Single byte range, for example `Range: bytes=0-1023` -> `206 Partial Content`
- Open-ended range, for example `Range: bytes=1024-` -> `206 Partial Content`
- Suffix range, for example `Range: bytes=-1024` -> `206 Partial Content`
- Invalid or multi-range request -> `416 Range Not Satisfiable`

Multi-range responses are not implemented in the initial service because browser/download-client resume only needs single ranges.

## Logging

Each completed request writes one `download.complete` log line with:

- route family, request id, run id, config
- sanitized path category and basename
- file size, status, range start/end
- bytes sent, duration, outcome, error reason
- client IP and user agent

Logs must not include Authorization headers, cookies, JWTs, raw query strings, or absolute filesystem paths.

## Docker/Caddy

The service listens on port `9011` in Docker. Compose definitions live in:

- `docker/docker-compose.dev.yml`
- `docker/docker-compose.prod.yml`
- `docker/docker-compose.prod.wepp1.yml`

Caddy route definitions live in:

- `docker/caddy/Caddyfile`
- `docker/caddy/Caddyfile.wepp1`

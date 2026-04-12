# Mini Work Package: Sandboxed Shapefile Conversion Web App Spec
Status: Draft
Last Updated: 2026-04-12
Primary Areas: `docker/docker-compose.dev.yml`, `docker/caddy/Caddyfile`, `wepppy/microservices/*`, `wepppy/all_your_base/geo/geo.py`, `wepppy/weppcloud/*`

## Objective
Provide a sandboxed upload/conversion service where users can upload a ZIP containing a shapefile and convert it to GeoJSON or GeoParquet, with explicit CRS handling options:
- Same as shapefile
- WGS84
- UTM (zone determined the same way WEPPpy currently determines UTM from the upper-left extent)

The service must report projection and attribute schema in the UI, and must delete uploaded ZIPs, extracted shapefile sidecars, and generated artifacts after each request completes.

## Why This Is Needed
Users currently struggle with local shapefile conversion workflows. A dedicated conversion service removes desktop GIS friction while centralizing security controls for high-risk ZIP and geospatial parser inputs.

## Scope
### In scope
- New standalone containerized microservice for conversion.
- Browser UI for upload, CRS option selection, and metadata reporting.
- Output formats: GeoJSON, GeoParquet.
- Strict upload validation, extraction controls, parser hardening, and cleanup lifecycle.
- Comprehensive negative/security test coverage for ZIP and shapefile risks.

### Out of scope
- General-purpose GIS editing.
- Multi-format archive support beyond ZIP.
- Persistent dataset storage.
- Long-running async job queue (v1 should be synchronous with strict timeouts).
- WEPPcloud route/controller updates to consume new relay flow (separate scope).

## User Experience
1. User opens converter page and sees one `Upload` control panel.
2. User selects `.zip` (containing exactly one logical shapefile dataset) in a single archive input.
3. User can choose output format (`GeoJSON`/`GeoParquet`) and target CRS (`same_as_shapefile`/`wgs84`/`utm_wepppy_upper_left`) in that same panel.
4. User clicks `Inspect Upload` (secondary action) to populate metadata panels:
   - Projection status (detected CRS / unknown).
   - Geometry summary (feature count, geometry types, bounds).
   - Attribute schema table (field name, type, width/precision where available).
   - Warnings (lossy/null/geometry/CRS caveats).
5. User clicks `Convert And Download` (primary action) to run conversion and download the artifact.
6. `inspect` and `convert` remain independent request-scoped uploads by backend contract; the browser may reuse the same selected local file, but each action sends its own multipart request and no server-side cross-request staging is allowed.
7. Service deletes all artifacts created by each request.

## Functional Requirements
### Upload and input requirements
- Accept only `multipart/form-data` with one file field: `archive`.
- Accept only `.zip` extension and ZIP signature/magic-byte validation.
- Reject password-protected/encrypted ZIP entries.
- Reject nested archives by policy in v1.
- Require shapefile core sidecars by shared prefix: `.shp`, `.shx`, `.dbf`.
- Permit optional sidecars: `.prj`, `.cpg`, `.sbn`, `.sbx`, `.qix`.
- Allow `.shp.xml` metadata sidecars as non-fatal input but immediately unlink them after extraction.
- Allow `.qmd` metadata sidecars as non-fatal input but immediately unlink them after extraction.
- Emit an explicit warning when `.shp.xml` is removed that it is generally not advisable to pack `.shp.xml` in shapefile ZIPs because metadata may leak sensitive details.
- Reject other non-required XML sidecars (`.xml`, `.gml`) in v1.
- Reject archives containing multiple shapefile prefixes unless user explicitly selects one (v1 default: reject).
- `inspect` and `convert` are independent uploads by design; no server-side file staging across requests.

### Access model (explicit)
- This is a **public unauthenticated service**.
- `inspect` and `convert` endpoints require **no login, no JWT, and no session cookie**.
- Service must remain stateless with no per-user persistence.
- Because there is no auth, abuse controls are mandatory:
  - Per-IP request rate limits and concurrent conversion caps.
  - Strict payload size, expansion, and runtime limits.
  - Fast-fail `429`/`503` behavior under saturation.
  - Trusted client identity rules:
    - Only proxy-set forwarding headers are trusted.
    - Edge strips inbound `X-Forwarded-*` from clients and sets canonical values.
    - Service trusts only configured proxy hops.
    - IPv6 rate-limit keys are aggregated to `/64`.

### CRS behavior
- `same_as_shapefile`:
  - Preserve source CRS if present.
  - If source CRS missing/unknown, keep coordinates as-is and mark projection as unknown in response/UI.
- `wgs84`:
  - Reproject to EPSG:4326 (longitude, latitude axis order in outputs).
  - If source CRS missing/unknown, fail with explicit error requiring known CRS.
- `utm_wepppy_upper_left`:
  - Determine target UTM zone from upper-left extent in WGS84 using the same approach as `wepppy/all_your_base/geo/geo.py` (`utm.from_latlon(north, west)` using bbox top-left).
  - Use hemisphere from north coordinate sign (`north > 0` => northern hemisphere, else southern), consistent with current WEPPpy behavior.
  - If source CRS missing/unknown, fail with explicit error requiring known CRS.
  - Fail with explicit `utm_not_supported_for_extent` when extent is outside supported UTM latitude domain.

### Output requirements
- GeoJSON output:
  - When `target_crs=wgs84`, emit RFC 7946-compatible GeoJSON.
  - When `target_crs` is projected (for example UTM), emit non-RFC-7946 GeoJSON with coordinates in the selected CRS.
  - For projected GeoJSON, include explicit CRS details in API metadata and compatibility warning in `warnings`.
  - For projected GeoJSON, use `application/json` content type (not `application/geo+json`) to avoid claiming RFC 7946 compliance.
- GeoParquet output:
  - Write valid GeoParquet metadata (`geo` metadata key, `primary_column`, `columns`, `crs` where known).
- UI/API metadata response must include:
  - `detected_crs` (authority/WKT/PROJJSON when available)
  - `projection_status` (`known`, `unknown`, `invalid`)
  - `attribute_schema` array
  - `geometry_types`
  - `feature_count`
  - `bbox`
  - `warnings` array (for example: lossy-field mapping, null-value caveats, CRS/extent caveats)

### WEPPcloud browser relay mode (`json_body`)
- Convert supports:
  - `response_mode=download` (default; unchanged behavior).
  - `response_mode=json_body` only when `output_format=geojson`.
- Relay success behavior:
  - `200 application/json` response containing `request_id`, `geojson`, and `metadata`.
- Relay validation behavior:
  - Unsupported relay combinations (for example `output_format=geoparquet` + `response_mode=json_body`) fail with canonical `400 invalid_request` and explicit `error.details`.
  - Unknown `response_mode` values fail with canonical `400 invalid_request`.
- Human-facing converter UI remains download-oriented (`response_mode=download`) and does not expose a relay-mode selector.
- `json_body` is an API-level mode for programmatic relay clients.
- Browser client forwards resulting relay payload to WEPPcloud endpoint over authenticated WEPPcloud session/API.
- Relay mode keeps `.zip` and shapefile sidecars processed/deleted inside shape-converter request scope.
- Shape-converter does not require WEPPcloud credentials and does not call WEPPcloud directly.

## Non-Functional Requirements
- Dedicated container/service (no embedding conversion in existing web app process).
- Sandboxed runtime:
  - Non-root user.
  - Read-only root filesystem.
  - `no-new-privileges`.
  - Drop all Linux capabilities except explicit minimum.
  - Seccomp/AppArmor (or SELinux) enabled.
  - Disable outbound network by default.
  - Treat GDAL/OGR parser execution as hostile-input boundary and run it only in bounded subprocesses with hard timeout + process-group termination.
- Resource limits (initial defaults, tune with data):
  - Request timeout: 30s metadata scan, 120s conversion hard timeout.
  - Max ZIP upload size: 100 MB.
  - Max total uncompressed bytes: 600 MB.
  - Max member count: 200.
  - Max features: 1,000,000.
  - Max vertices per feature: configurable guardrail (start 250,000).
- Observability:
  - Request ID, rejection reason codes, parse duration, convert duration, cleanup success/failure.
  - Do not log raw uploaded content.

## Service Design
### Deployment shape
- New service: `shape-converter`.
- New Caddy utility namespace route: `/utils/shape-converter`.
- Caddy matcher must be tightened to avoid prefix bleed (do not use `/utils/shape-converter*` glob matching).
- Required Caddy route shape:
```caddy
@shape_converter_exact path /utils/shape-converter /utils/shape-converter/
@shape_converter_subtree path /utils/shape-converter/*

handle @shape_converter_exact {
    redir /utils/shape-converter/ 308
}

handle_path /utils/shape-converter/* {
    reverse_proxy shape-converter:8060 {
        header_up X-Forwarded-Prefix /utils/shape-converter
        header_up X-Forwarded-Proto {scheme}
        header_up Host {host}
    }
}
```
- UI can be:
  - Minimal static page served by this service, or
  - Embedded WEPPcloud page that POSTs directly to `shape-converter`.

### Container specification (detailed)
#### Image and runtime
- Multi-stage image build:
  - Stage 1: build/install app dependencies and pinned geospatial tooling (`gdal`, `proj`, `geos`).
  - Stage 2: minimal runtime image with only runtime libs and app code.
- Run as non-root fixed UID/GID (for example `10001:10001`).
- Root filesystem read-only.
- Writable paths only via `tmpfs` mounts:
  - `/tmp` for request scratch (archive, extraction, generated output).
  - `/run/shape-converter` for process/runtime state.
- No host path mounts except explicit config/secrets mounts.

#### Compose-level hardening contract
- `read_only: true`
- `user: "10001:10001"`
- `security_opt` includes `no-new-privileges:true`
- `cap_drop: [ALL]`
- `pids_limit` (for example `256`)
- `mem_limit` and `cpus` must be set (no unlimited defaults)
- `tmpfs` mounts use `noexec,nosuid,nodev` options
- Service is attached only to a dedicated internal network segment and proxied by Caddy
- East-west access to other app services is denied by network policy
- Outbound egress is deny-all (including DNS) unless explicitly allowlisted
- No Docker socket mount, no privileged mode, no host PID/IPC namespaces
- Runtime image and base image are digest-pinned in build/deploy manifests

#### Health and lifecycle
- `GET /utils/shape-converter/health/live` for liveness.
- `GET /utils/shape-converter/health/ready` for readiness (checks temp dir writability, toolchain availability, and required runtime sandbox mode).
- Graceful shutdown:
  - Stop accepting new work.
  - Wait for in-flight conversions up to shutdown timeout.
  - SIGKILL any remaining conversion subprocess group after timeout.
- Startup self-check:
  - Validate `ogr2ogr --version`.
  - Validate writable scratch root and cleanup permissions.
  - Validate parser subprocess sandbox mode (production hard requirement).

#### Performance and concurrency contract
- Bound active conversions with semaphore:
  - `MAX_ACTIVE_CONVERSIONS_PER_WORKER` default `2`.
- Bound active requests:
  - `MAX_INFLIGHT_REQUESTS` with immediate `429` when saturated.
- Per-request timeout:
  - Metadata inspect timeout: 30 seconds.
  - Conversion timeout: 120 seconds.
  - Upload header/body read timeout and minimum upload data rate are enforced.
  - Response write/idle timeout and max download lifetime are enforced.
- Backpressure policy:
  - No unbounded in-memory queue.
  - Reject quickly with retry guidance once capacity is reached.
  - Multipart guardrails: max part count and max field size.

#### Storage and quota contract
- `tmpfs` scratch size is explicitly configured and must exceed max uncompressed archive bytes plus conversion headroom.
- Service performs free-space preflight checks before extraction and before conversion write.
- Per-request scratch quota is enforced independently of global tmpfs size.

#### Worker lock-up prevention contract
- Never run heavy geospatial conversion on event loop threads.
- Execute conversion and deep parse steps in isolated subprocesses (`ogr2ogr`/`ogrinfo` or equivalent) with:
  - Process-group creation.
  - Hard wall-clock timeout.
  - Kill entire process group on timeout/cancel.
- Keep ASGI handlers async and lightweight:
  - Upload validation.
  - Job orchestration.
  - Streaming response.
- Ensure all cleanup runs in `finally` blocks independent of client disconnect.
- In production, parser subprocesses MUST run inside a second sandbox boundary (gVisor/Kata/nsjail-equivalent); service must fail readiness if this requirement is not satisfied.

### Framework/runtime decision
#### Option comparison
| Option | Pros | Cons | Worker lock-up risk profile | Fit for this service |
| --- | --- | --- | --- | --- |
| Starlette (Python) | Minimal ASGI layer, low overhead, already aligned with WEPPpy `query-engine` patterns, few dependencies | More manual request validation/OpenAPI wiring than FastAPI | Low if conversion is subprocess-bound and concurrency is capped; high if blocking work leaks into event loop | Strong |
| FastAPI (Python) | Fast development, built-in validation/docs, based on Starlette/Pydantic | Slightly higher framework/validation overhead, extra abstraction for a very small API | Similar to Starlette for lock-up risk (risk is from blocking work, not framework choice) | Good but not necessary |
| Go (`net/http` or chi/gin) | Very strong concurrency model, low runtime overhead, each request served in goroutines | New language/toolchain in this repo, higher integration and maintenance overhead, geospatial stack still relies on GDAL subprocesses or CGO bindings | Very low runtime lock risk, but operational complexity is higher in this codebase | Viable v2, not v1 |

#### Final decision
- **Choose Starlette for v1**, with a strict subprocess execution model for geospatial work.
- Rationale:
  - Throughput here is dominated by GDAL/IO and archive processing, not JSON framework overhead.
  - Starlette keeps the control plane lean and matches existing repo ASGI patterns.
  - Worker lock-ups are prevented by design through bounded subprocess execution and hard timeouts.
  - This avoids introducing a new language/runtime stack prematurely.
- Revisit Go only if production data shows the ASGI control plane itself is a measurable bottleneck after subprocess isolation and concurrency tuning.

### Processing pipeline
1. `inspect` creates a request temp directory under isolated tmpfs mount.
2. `inspect` saves uploaded ZIP to temp dir.
3. Pre-scan ZIP central directory and validate all entries before extraction.
4. Extract with canonical-path enforcement into temp dir only.
5. Validate shapefile set and parse metadata.
6. If this is `convert`, perform requested reprojection/serialization and stream artifact.
7. In `finally`, cleanup deletes:
   - Uploaded ZIP
   - Extracted members
   - Generated output artifact
   - Request temp directory
8. Janitor removes stale temp directories left only by abnormal process termination.

## Cleanup Contract (Required)
- All request artifacts must be ephemeral and request-scoped.
- Deletion attempted on every code path (success, validation failure, conversion failure, timeout, client disconnect).
- Cleanup failures are logged as structured security events and retried by janitor.
- No artifact persistence after request terminal response.

## API Sketch (Draft)
### `POST /utils/shape-converter/v1/inspect`
Request:
- `archive` (ZIP)
- No auth credentials required.

Response 200:
- `request_id`
- `detected_crs`
- `projection_status`
- `feature_count`
- `geometry_types`
- `bbox`
- `attribute_schema`
- `warnings`

### `POST /utils/shape-converter/v1/convert`
Request:
- `archive` (ZIP)
- `output_format` = `geojson|geoparquet`
- `target_crs` = `same_as_shapefile|wgs84|utm_wepppy_upper_left`
- `response_mode` supports `download|json_body` (default `download`)
- `response_mode=json_body` is valid only with `output_format=geojson`
- No auth credentials required.

Response 200:
- `response_mode=download`: streamed artifact download + metadata sidecar JSON endpoint keyed by `request_id`
- `response_mode=json_body`: JSON payload with:
  - `request_id`
  - `geojson`
  - `metadata`

Error response contract:
- Follow canonical WEPPpy error payload style (`error.code`, `error.message`, `error.details` required).
- Use explicit codes like:
  - `invalid_request`
  - `invalid_archive`
  - `archive_path_traversal`
  - `archive_quota_exceeded`
  - `missing_required_sidecar`
  - `invalid_shapefile`
  - `unknown_source_crs`
  - `reprojection_failed`
  - `utm_not_supported_for_extent`
- Error status mapping (minimum):
  - `400`: validation/input errors.
  - `404`: metadata sidecar `request_id` not found.
  - `413`: upload/body/expansion quota exceeded.
  - `429`: rate-limit or concurrency saturation.
  - `500`: unexpected internal failure.

## ZIP Upload Risk Matrix (Comprehensive)
| Risk | Why it matters | Required mitigations | Required tests |
| --- | --- | --- | --- |
| Path traversal (`../`, absolute paths, drive paths) | Write outside extraction root | Canonicalize + `commonpath` enforcement per member; reject violators | Archive with `../../etc/passwd`, `/tmp/x`, `C:\\...` rejected |
| Zip Slip variants via encoded names | Bypass naive prefix checks | Normalize Unicode + separators before path checks | Mixed separator + encoded traversal payloads rejected |
| Symlink entries | Indirect traversal/overwrite | Reject symlink members and special file types | ZIP containing symlink entry rejected |
| Duplicate member names | Overwrite confusion | Reject duplicate normalized extraction paths | ZIP with duplicate filenames rejected deterministically |
| Case-collision names | Cross-platform overwrite ambiguity | Normalize policy to lowercase compare for collision detection | `Road.shp` + `road.shp` rejected |
| ZIP bombs / high compression ratio | Disk and memory exhaustion | Cap compressed size, uncompressed size, and ratio; stream with counters | Known zip-bomb fixtures rejected before extraction |
| Excessive member count | Inode/CPU exhaustion | Max member cap | ZIP with > cap rejected |
| Nested archives | Recursive bomb/smuggling | Reject nested archives in v1 | ZIP containing `.zip` members rejected |
| Encrypted/password ZIPs | Uninspectable content, operational failures | Reject encrypted flag entries | Encrypted ZIP rejected with explicit error |
| Unsupported compression methods | Parser exceptions/DoS | Allowlist supported compression methods only | Unsupported compression method returns validation error |
| Corrupt CRC/central directory | Crash/undefined behavior | Validate archive integrity before extraction | Truncated/corrupt ZIP rejected |
| Oversize filenames/path depth | FS/path handling failures | Enforce max filename length and max path depth | Very deep path archive rejected |
| Hidden/system files in archive | Ambiguous behavior | Allowlist required extensions and optional sidecars only; sanitize known metadata sidecars (`.shp.xml`, `.qmd`) by immediate unlink | `.exe`, `.dll`, `.py` members rejected |
| Null-byte or control-char filenames | Sanitization bypass | Reject non-printable/control chars and null bytes | Crafted control-char names rejected |
| ZIP metadata trust issues | Spoofed types | Validate extension + signature + entry policy | Mismatched extension/signature rejected |
| Archive parser dependency CVEs | Parser compromise risk | Keep libraries patched, run in sandbox, pin versions | Dependency audit gate + CVE regression check |

## Shapefile Risk Matrix (Comprehensive)
| Risk | Why it matters | Required mitigations | Required tests |
| --- | --- | --- | --- |
| Missing required sidecars (`.shp/.shx/.dbf`) | Cannot reliably read dataset | Explicit required-file validation | Omit each required sidecar -> explicit failure |
| Multiple shapefile prefixes in one ZIP | Ambiguous conversion target | Reject unless explicit dataset selection implemented | ZIP with two prefixes rejected |
| Missing `.prj` | Unknown CRS; reprojection unsafe | Mark unknown for inspect; block CRS transforms requiring known source | Missing `.prj` + `wgs84/utm` request fails |
| Invalid `.prj` WKT | Bad reprojection | Parse CRS strictly; return `invalid_source_crs` | Corrupted `.prj` rejected |
| DBF encoding ambiguity (`.cpg`/LDID issues) | Attribute corruption | Detect/report source encoding; allow explicit override in future | Non-UTF8 DBF fixture preserved/flagged correctly |
| 10-char field name truncation collisions | Schema ambiguity/data loss | Report original + normalized names when possible; fail on unresolved duplicates | Collision fixture handled deterministically |
| Null-value semantics in DBF/shapefile | Silent value substitution | Surface null/substitution behavior in metadata warnings | Dataset with sentinel null-like values flagged |
| Attribute width/precision limits | Rounding/truncation | Preserve types carefully; emit warnings for lossy mappings | Large numeric precision fixture warning/assertion |
| Mixed/unsupported geometry content | Conversion failure or wrong output | Validate geometry types and null geometries before write | Mixed geometry fixture produces explicit policy error |
| Invalid geometries (self-intersections, ring issues) | Output unusable or crashes | Run geometry validity checks; optionally repair under explicit flag (off by default) | Invalid polygon fixture returns explicit error |
| Multipart/multipatch edge cases | Type coercion surprises | Normalize and report resulting geometry types | Multipatch/multipart fixtures validated and reported |
| Massive vertex counts | CPU/memory exhaustion | Vertex and complexity guardrails | High-vertex polygon fixture rejected by threshold |
| Record count mismatch (`.shp` vs `.dbf`) | Corrupt feature/attribute mapping | Cross-check record counts and fail if inconsistent | Tampered sidecar counts rejected |
| Malformed binary structures | Native parser crash risk | Parse in hardened sandbox process and fail safely | Fuzz corpus malformed files do not crash host |
| Out-of-range coordinates | Projection errors | Validate coordinate ranges by CRS before transform | Extreme-coordinate fixtures fail clearly |
| Anti-meridian/multi-zone extents | UTM ambiguity | Document UL-corner UTM behavior and emit warning if bbox spans zones | Multi-zone fixture warns, still deterministic |
| Shapefile size/component limits | Operational failures | Enforce file-size and feature-count caps before full load | Over-limit fixtures rejected early |
| XML sidecar entity expansion (`.xml`, `.gml`, `.shp.xml`) | CPU/memory DoS via parser | Reject generic XML sidecars; if `.shp.xml` is present, delete it immediately after extraction and enforce parser timeout + memory caps | Generic XML sidecar rejected; `.shp.xml` stripped with warning |
| Parser-triggered remote fetch (`/vsicurl/`, remote references) | Unwanted network egress/data exfil risk | Keep deny-all egress and disable remote parser sources by policy/config | Fixture attempting remote reference fails without outbound access |
| Metadata PII leak from metadata sidecars (`.shp.xml`, `.qmd`) | Exposure of usernames, contact details, host paths, org/process history | Never parse or return sidecar metadata; sanitize by immediate unlink; keep warnings/log fields free of raw sidecar content | Fixture containing PII in sidecar yields no PII in API payloads/logs |

## CRS Rules and UTM Determination Details
- Source of truth for UTM mode should mirror existing WEPPpy logic in `wepppy/all_your_base/geo/geo.py`:
  - Determine UTM zone from upper-left bbox corner (north, west).
  - Force lower-right corner into the same zone.
  - Set hemisphere from sign of north latitude.
- Practical implementation for converter:
  1. Compute source bbox.
  2. Transform bbox to WGS84 if needed.
  3. Use upper-left (`max_lat`, `min_lon`) to compute UTM zone.
  4. Build target CRS EPSG: `326xx` for north, `327xx` for south.
  5. Reproject all features.

## UI Requirements
- Layout and control contract:
  - One controls panel titled `Upload` with:
    - one archive file input
    - output format selector
    - target CRS selector
    - primary `Convert And Download` button
    - secondary `Inspect Upload` button
  - `Warnings` panel appears immediately after the `Upload` panel.
  - `Projection`, `Geometry Summary`, and `Attribute Schema` panels follow warning/error content.
  - All user-facing panels are the same width in the default layout.
  - Static asset URLs must resolve correctly behind proxied namespace `/utils/shape-converter/` (no root-relative asset assumptions).
- Visibility contract:
  - Initial load:
    - show `Upload` panel
    - hide `Warnings`, `Projection`, `Geometry Summary`, and `Attribute Schema`
  - Show `Projection`, `Geometry Summary`, and `Attribute Schema` only after a successful inspect payload provides content.
  - Keep `Warnings` hidden until there is warning/error/advisory content to show.
- Metadata rendering contract:
  - Projection panel:
    - Detected CRS (authority or unwrapped WKT when authority is unavailable)
    - Projection status badge (`known`, `unknown`, `invalid`)
    - Output CRS (after convert metadata is available)
  - Geometry summary:
    - Feature count
    - Geometry types
    - BBox
  - Attribute schema table:
    - Column name
    - Source type
    - Width/precision
    - Nullability note (if inferable)
- Interaction contract:
  - UI may reuse one selected local archive file for both actions, but each `Inspect`/`Convert` click sends a separate request.
  - Convert UI is download-oriented and submits `response_mode=download`.
  - Relay `response_mode=json_body` is available via API for programmatic clients and is not presented as a default end-user control.
- Error UX contract:
  - All API/network errors must be observable by users (no silent failures).
  - `inspect-status` and `convert-status` messages must use plain language with specific next-step guidance.
  - `429`/`503` abuse-control states must include clear retry guidance and display `Retry-After` when present.
- Keep messages explicit; no silent fallback behavior.

## Security Controls Baseline
- Follow OWASP file upload defense-in-depth: extension allowlist, signature checks, strict size/runtime limits, sandboxing, dependency patching, and abuse controls for anonymous access.
- Apply container hardening controls: non-root, no privilege escalation, seccomp/AppArmor/SELinux, read-only filesystem, resource limits.
- Require an additional runtime sandbox layer (e.g., gVisor runsc) in production for parser isolation.
- No container access to Docker socket, host root, or unrelated volumes.
- Public-service edge controls are required:
  - Edge request body size cap.
  - Edge upload/read/write timeouts and minimum upload data rate controls.
  - Edge forwarding-header sanitization and trusted-proxy configuration.
  - CORS policy for browser relay use-cases is required for `json_body` mode.
- Application-level controls are also required (authoritative when edge lacks native rate-limit module support):
  - Per-IP rate/concurrency controls in service middleware.
  - Per-request scratch quotas and timeout cancellation hooks.
  - Metadata sanitization and length bounds before serialization/logging.
- Supply-chain controls are required:
  - Runtime image digest pinning.
  - SBOM generation for release builds.
  - Vulnerability scan gate that blocks unresolved High/Critical issues in reachable runtime components.
- Parser dependency controls are required:
  - Track and triage GDAL/OGR parser vulnerabilities (including memory-corruption and parser-DoS classes) before each release; keep known examples such as `CVE-2021-45943` and `CVE-2025-29480` on the watchlist.
  - Maintain explicit timeout/kill behavior for parser non-termination classes (for example malformed WKB infinite-loop conditions).
  - Treat `/vsizip/` as an implementation detail, not a security boundary; archive and contained parser risks still require full validation/sandbox controls.
  - Maintain metadata-privacy policy that forbids exposing raw `.shp.xml` content in API payloads, logs, or warnings (only advisory removal notices are allowed).

## Test Plan
### Unit tests
- ZIP entry path canonicalization and collision handling.
- Size/count/ratio quota enforcement.
- CRS option validation matrix.
- UTM zone function parity with WEPPpy upper-left rule.

### Integration tests
- Valid uploads for point/line/polygon shapefiles.
- Missing sidecars and invalid `.prj` flows.
- GeoJSON and GeoParquet output metadata correctness.
- Browser relay flow correctness (`response_mode=json_body`) including success payload shape and invalid-combination failures.
- Cleanup verification: no residual files after request terminal state.

### Security tests
- Zip-Slip fixtures.
- Zip bomb fixtures.
- Encrypted ZIP fixtures.
- Malformed shapefile fuzz corpus.
- Parser timeout and cancellation behavior.
- XML sidecar bomb fixtures (`.shp.xml`/`.xml` entity expansion class payloads).
- Parser non-termination fixtures (malformed WKB parser-loop class).
- Metadata privacy fixtures: `.shp.xml` and `.qmd` containing usernames/paths/contact fields are not exposed in responses/logging.
- Runtime hardening verification:
  - `read_only`, `cap_drop=ALL`, `no-new-privileges`, seccomp/AppArmor/SELinux, pids/mem/cpu limits, deny-all egress.
- Slowloris and pinned-download resilience:
  - Slow upload/body timeout enforcement.
  - Slow download/write timeout cleanup behavior.
- Anonymous abuse controls:
  - Endpoints reachable without auth.
  - Proxy-validated IP rate limits return expected `429`.
  - Concurrent flood beyond caps does not starve healthy traffic.

### Performance tests
- Large-but-valid shapefile throughput.
- Concurrent conversion requests under CPU/memory limits.

## Acceptance Criteria
- Users can upload ZIP shapefiles and download GeoJSON/GeoParquet reliably.
- Service is publicly accessible without authentication by design.
- UI implements the single `Upload` controls panel (one archive input + output/CRS selectors + primary convert/secondary inspect actions).
- `Warnings` panel is positioned directly after `Upload` and is hidden until warning/error/advisory content exists.
- `Projection`, `Geometry Summary`, and `Attribute Schema` remain hidden until successful inspect metadata is available.
- Convert API supports both `response_mode=download` and relay `response_mode=json_body` (GeoJSON-only), with explicit canonical 4xx errors for unsupported combinations; the public UI remains download-oriented.
- CRS options behave exactly as specified (including WEPPpy UL-corner UTM mode and explicit out-of-domain failures).
- GeoJSON behavior is explicit: RFC 7946 in WGS84 mode and clearly labeled non-RFC projected mode for UTM/same-CRS output.
- ZIP and shapefile risk tests are implemented and passing.
- XML sidecar and parser-loop abuse tests are implemented and passing.
- No sidecar-derived PII (for example `.shp.xml`/`.qmd` usernames, contacts, file paths) is exposed by API metadata or logs.
- When `.shp.xml` is included, API warnings explicitly report removal and advise that packing `.shp.xml` in shapefile ZIPs is generally not advisable.
- When `.qmd` is included, it is sanitized via immediate unlink and never parsed or surfaced in API metadata.
- No uploaded or generated artifacts persist after each request terminal response (verified by tests).
- Service runs in its own hardened container and is reachable through Caddy.
- CI/security validation proves container hardening and runtime abuse controls are active.

## Source Notes
- Existing WEPPpy UTM upper-left behavior: `wepppy/all_your_base/geo/geo.py` lines 808-823.
- Internal prior risk evidence for ZIP/shapefile flow: `docs/culvert-at-risk-integration/audits/culvert-web-app-codebase-audit-2026-02-20.md` lines 116-127 and 152-167.

## External References
- OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- Python `zipfile` docs (extract warnings, traversal notes, decompression pitfalls): https://docs.python.org/3/library/zipfile.html
- NVD CVE-2024-55587 (archive extraction traversal class example): https://nvd.nist.gov/vuln/detail/CVE-2024-55587
- GDAL security model for untrusted input: https://gdal.org/en/stable/user/security.html
- GDAL ESRI Shapefile driver docs: https://gdal.org/en/stable/drivers/vector/shapefile.html
- GDAL issue #14039 (WKB parser infinite-loop class): https://github.com/OSGeo/gdal/issues/14039
- ESRI Shapefile Technical Description: https://www.esri.com/library/whitepapers/pdfs/shapefile.pdf
- ArcGIS shapefile output limitations: https://pro.arcgis.com/en/pro-app/latest/tool-reference/appendices/geoprocessing-considerations-for-shapefile-output.htm
- GeoParquet 1.1.0 specification: https://geoparquet.org/releases/v1.1.0/
- OWASP Docker Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
- gVisor architecture/security intro: https://gvisor.dev/docs/architecture_guide/intro/
- Starlette homepage/docs: https://www.starlette.io/
- FastAPI features: https://fastapi.tiangolo.com/features/
- Go `net/http` package docs: https://pkg.go.dev/net/http

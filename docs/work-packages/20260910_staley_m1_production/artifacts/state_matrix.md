# Valid-state and request matrix

Status: accepted at the contract checkpoint, 2026-09-10 UTC. Normative errors
and transitions are in current workflow/UI contracts. Validation maps targeted
regressions and real workflow evidence in [validation.md](validation.md); this
matrix is not a claim of exhaustive cross-product testing.

| Runtime state | User outcome | Server/worker obligation |
| --- | --- | --- |
| Eligible new project; NoDb absent | See prerequisites; upload available once delineation ready. | Read-only rendering does not create state; first authorized mutation initializes safely. |
| Present-empty NoDb | Same usable first-use control. | Default optional state without calling it corruption. |
| Missing soils/K/climate; grid ready | Upload works; run explains missing prerequisite with link. | Separate upload readiness from model readiness. |
| Upstream readiness changes while page open | Required-data rows and run explanation update without reload. | Publish current readiness/invalidation through preflight, including initial and reconnect snapshots. |
| NOAA missing or stale | NOAA disabled with explanation; no silent source switch. | Update via preflight; recheck selected source at submission and execution. |
| Preflight disconnected/reconnected | Existing connection status; reconciled readiness after reconnect. | Do not misrepresent cached readiness as live; no full raster hashing on heartbeat. |
| Auto encoding resolved | Upload prepares normally without extra fields. | Record distribution/metadata evidence and explicit factor/offset; show applied scale in persistent summary; apply exactly once. |
| Auto encoding ambiguous | Choose preset/custom and retry without retransferring staged file. | No accepted publication; candidate access, expiry and attempt checks enforced. |
| Read-only viewer | See allowed status/files; no write actions. | Enforce access on all mutation/download boundaries. |
| Ineligible backend/locale | Feature availability follows registry; direct calls fail clearly. | Use canonical effective config/locale, not UI strings. |
| Upload staged/normalizing | Progress survives reload; prior accepted dNBR remains visible. | Candidate cannot become active early. |
| Failed initial upload | Clear correction; retry available. | No false ready state or active pointer. |
| Failed replacement | Old dNBR/result preserved; failed attempt identified. | No deletion or partial replacement of accepted artifact. |
| Ready/current result | Run and file access available. | Validate current dependencies, do not trust client ready flag. |
| Queued/running model | One progress status and active job across reload/clicks. | Idempotent matching submission; bounded retries, fresh source checks. |
| Input changes during run | Result not current; request rerun. | Finalizer cannot publish against changed source/attempt. |
| New dNBR while prior model runs | New accepted map wins; prior job cannot overwrite current result. | Freeze attempt ownership/race policy and test real persistence. |
| Scientific partial support | Run completes with missing-probability explanation and files. | Keep T bounds/null and K/F policies; no fabricated zero. |
| Worker failure/timeout | Specific actionable message where known; previous output remains. | Terminal state survives reload; orphan/retry recovery specified. |
| Source removed or superseded | Inputs changed/missing; link to owner action. | Check artifact association plus content, not timestamp alone. |
| Supported legacy project | Existing old debris-flow data untouched; new feature behaves as optional. | No implicit migration of legacy controller or unproven provenance. |
| Malformed state or hostile upload | Bounded explicit error. | No traversal, embedded-path reads, unsafe VRT, decoder bypass or swallowed failure. |

Request matrix must cover fresh/replacement upload; each accepted raster format;
Auto/preset/custom encoding, default versus explicit metadata, conflicting metadata,
ambiguous low scaled values, expired/unauthorized candidate retry; no image-date
entry or missing-date gate; persistent accepted filename with escaped hostile names;
VRT companion missing/
valid/hostile; partial/no overlap; run source cli/noaa; missing artifacts; invalid/
duplicate payload keys; expired/missing auth/CSRF; duplicate submit; stale attempt;
and display-unit changes. Test meaningful cross-products with the state rows.
Every user-reachable error needs classification, normal copy, canonical reason
and direct evidence at its actual changed file/persistence boundary.

Detection fixtures must cover equivalent normalized and ×1,000 encodings,
negative/zero values, all-zero and low-integer ambiguous maps, masked sentinels,
isolated outliers, conflicting metadata, partial overlap and differing source
extents. Verify repeatable decisions and equivalent prepared dNBR/M1 F for known
encodings. Browser checks cover the summary table, source-versus-prepared labels,
SI/English cell size, reload, failed replacement and scale correction after Auto.

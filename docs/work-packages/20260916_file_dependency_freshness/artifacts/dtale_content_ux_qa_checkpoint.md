# D-Tale content checkpoint: UX and valid-state QA

Date: 2026-09-16. Scope: proposed D-Tale section of
`docs/schemas/file-dependency-freshness-contract.md` and
`dtale_content_contract_decision.md`; no production/test edits.

Disposition: scoped checkpoint QA PASS. The revised loader/grid error split is supported by installed
upstream behavior and an actual browser presentation probe. The bounded
invalidate-and-reopen lifecycle is compatible with the current lazy backend.
Implementation and real changed-source browser acceptance remain open.

## Error presentation: confirmed and resolved decision

Installed D-Tale version: **3.22.0**. Its `DataRepository.load` delegates to
`GenericRepository.getDataFromService`. Axios rejects non-2xx responses; the
generic getter logs the exception and returns `undefined`, discarding the body.
`DataViewer` renders `response.error` before consuming rows/columns;
`RemovableError` expects a string and presents it in `role="alert"`.

The original lazy-grid HTTP409 proposal cannot display its reopen guidance.
The owner revised it to the existing upstream convention:

```json
{"success": false, "error": "This file changed or cannot be verified. Reopen the dataset from browse.", "code": "changed_source"}
```

Return this with HTTP200 and no successful row/column payload. Do not use
`error: {code, message}` at the grid endpoint: the React component renders the
error value directly. DataRepository performs no normalization that removes
the top-level code or message. This narrow response choice avoids an unnecessary
upstream UI transport patch.

Keep HTTP409 for `/internal/load`, with structured `error.code/message` and a
matching top-level string `description`. The maintained browse bridge reads
`description` first and preserves the status; it does not use the grid getter.

Actual headless Chromium results with a disposable, live lazy-Parquet shell:

| Intercepted grid response | Requests intercepted | Visible reopen alert | Browser page errors |
| --- | --- | --- | --- |
| HTTP409, same JSON body | 1 | No | None |
| HTTP200, upstream error body | 1 | Yes | None |

Evidence: `dtale_ui_contract_probe.json`, `dtale_ui_contract_browser.log`,
`dtale_ui_grid_200.png`, `dtale_ui_grid_409.png`, and
`dtale_installed_ui_error_sources.json`. Reproduction scripts are
`dtale_ui_contract_probe.py` / `.cjs`. The browser used installed HTML/JS and
intercepted only its disposable dataset's grid response; local URL routing
reproduced the normal proxy's `/weppcloud` prefix stripping. The first direct-
service attempt lacked that mapping and rendered a blank page; its failed
evidence is retained with `_direct_service_unmapped` suffixes. This is response-
presentation proof, not a claim that production freshness logic is implemented.
Dataset cleanup returned 200 and only its temporary batch directory was removed.

## Reopen, filters and maps

- Reopening through browse must preserve the submitted `pqf` partition and
  recompile it against the new file schema. Compatible filters produce new
  bounded rows/counts. A removed column or now-invalid operator/type retains
  the canonical 422 validation error; do not drop the filter, broaden selection,
  or revive the prior schema shell after failed initialization.
- Reset server schema, dtypes, settings and cached count/sample together on
  changed-source launch. Same-byte metadata changes should retain current
  session state. Reusing the stable ID means an explicit relaunch also affects
  other tabs using it; the revised contract correctly avoids promising
  per-browser generation isolation.
- Already displayed browser rows may remain visible until the next page request;
  the scope is guarded reads, not a push invalidation service. On a rejected
  read, show the message and return no new successful rows. Keep native bounded
  Parquet reads and existing unsupported-action behavior.
- Optional GeoJSON disappearance or parse/read failure must not block a valid
  table. Remove the affected key from `REGISTERED_GEOJSON` and upstream
  `CUSTOM_GEOJSON`, prune matching `MAP_CHOICES`, and clear only defaults that
  reference that key. Allow remaining valid overlays to supply defaults.
  Discovery returning no controller/path needs the same cleanup as a missing
  file; otherwise `_ensure_geojson_assets` can skip registration entirely and
  leave obsolete dropdown/default references. Preserve unrelated overlays.
- Acceptance should exercise valid filtered relaunch, incompatible-schema 422,
  same-byte reuse, shared-ID relaunch, missing optional controller/path and
  restored optional GeoJSON, including aliases/default selection. The contract
  appropriately leaves full browser workflow and large-source latency as gates.

No need for full-data fallback, a new service/cache, version-token protocol, or
frontend fork was found. The owner also corrected the earlier decision paragraph
and recorded explicit filter recompilation, optional-overlay cleanup/defaults,
and resolved-target equality before same-byte dataset reuse. These clarifications
resolve the checkpoint concerns; implementation acceptance remains pending.

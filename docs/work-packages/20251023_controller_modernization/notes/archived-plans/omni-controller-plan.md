---
title: Omni Controller Modernization Plan
---

> Quick-reference contract for the helper-based Omni scenario runner. Use this alongside `docs/dev-notes/controller_foundations.md` whenever extending scenarios, templates, or backend routes.

## Overview
> Status: Completed (helper-first controller migration). See [controllers_js Modernization Retrospective](./controllers_js_jquery_retro.md).

- Omni now relies entirely on the shared helper stack (`WCDom`, `WCHttp`, `WCForms`, `WCEvents`, `controlBase`). jQuery dependencies and inline scripts have been removed.
- Scenario cards are rendered dynamically by `omni.js`; templates only declare markup shells (`#scenario-container`, buttons with `data-omni-action`) while the controller injects inputs per scenario definition.
- RQ submissions post `FormData` payloads containing a JSON `scenarios` list plus optional SBS uploads. Flask endpoints ingest everything via `parse_request_payload`, keeping JSON and multipart callers aligned.
- The controller exposes a scoped event emitter so neighbouring modules (unitizer, dashboards) can react without scraping DOM state.

## DOM hooks
- Buttons: `data-omni-action="add-scenario"` adds a blank card, `data-omni-action="run-scenarios"` submits the current list.
- Scenario selector: each card includes a `<select>` tagged with `data-omni-role="scenario-select"`; the controller repopulates options whenever Disturbed SBS state changes.
- Control container: per-card fields live under `[data-omni-scenario-controls]`. Generated inputs carry `data-omni-field="<name>"` so serialization and events can locate values.
- SBS uploads: file inputs include `data-omni-role="scenario-file"`; the controller enforces `.tif/.tiff/.img` extensions and a 100 MB cap before issuing a request.

## Event contract
`Omni.getInstance().events = WCEvents.useEventMap([...])` publishes the following signals:

| Event | Detail payload | Notes |
|-------|----------------|-------|
| `omni:scenario:added` | `{ scenario, element }` | Fired after a new card is rendered (prefill honoured). |
| `omni:scenario:removed` | `{ element }` | Always follows DOM removal; consumers should assume indices shift. |
| `omni:scenario:updated` | `{ scenario, element }` | Emitted on selector or control changes with the latest non-file values. |
| `omni:scenarios:loaded` | `{ scenarios }` | Triggered after `load_scenarios_from_backend()` hydrates the UI. |
| `omni:run:started` | `{ scenarios }` | Fired once the FormData payload is prepared and the WebSocket connects. |
| `omni:run:completed` | `{ jobId, scenarios }` | Emitted on immediate enqueue success; a second emission occurs when the RQ broadcast announces completion (`OMNI_SCENARIO_RUN_TASK_COMPLETED`). |
| `omni:run:error` | `{ error? , response? }` | Surfaces validation issues or HTTP errors; callers should not assume both keys exist. |

> Consumers must not mutate the provided scenario object; treat it as read-only metadata for dashboards/logging.

## Payload schema
- `scenarios`: JSON array of objects. Each entry must include `type` plus optional keys:
  - `thinning`: `canopy_cover` (`40%`, `65%`), `ground_cover` (`93%`, `90%`, `85%`, `75%`).
  - `mulch`: `ground_cover_increase` (`15%`, `30%`, `60%`), `base_scenario` (`uniform_low`, `uniform_moderate`, `uniform_high`, `sbs_map`).
  - `sbs_map`: `sbs_file_path` (string path) or a file upload under `scenarios[{idx}][sbs_file]`.
  - Other scenarios carry no additional fields.
- SBS uploads are staged to `{wd}/omni/_limbo/{idx:02d}/` via `save_run_file`. The helper returns a `Path` which the controller stores as `sbs_file_path` before invoking `Omni.parse_scenarios`.
- Backend routes (`run_omni`, `run_omni_contrasts`) normalise inputs through `_prepare_omni_scenarios`, trimming stray `"sbs_file"` markers and guaranteeing native Python types.

## Testing cadence
- **Frontend**: `wctl run-npm lint`, `wctl run-npm test -- omni`, `python wepppy/weppcloud/controllers_js/build_controllers_js.py`. The Jest suite (`controllers_js/__tests__/omni.test.js`) exercises FormData serialisation, scenario hydration, and SBS validation.
- **Backend**: `wctl run-pytest tests/weppcloud/routes/test_rq_api_omni.py`. Coverage includes JSON payloads, multipart uploads, Redis queue wiring, and SBS staging behaviour.
- **Smoke**: when possible, launch the dev stack and confirm scenario runs push status updates through the omni WebSocket channel (`{runid}:omni`).

## Follow-ups / open questions
- Contrast execution remains disabled in the Pure layout; enabling it will require extending both the controller and `/rq/api/run_omni_contrasts`.
- Scenario catalogue still lives inside `omni.js`. If future work introduces dynamic descriptors, consider moving definitions into a JSON seed similar to climate catalogues.
- Disturbed SBS availability continues to depend on the legacy controller’s synchronous `has_sbs()` call; migrating Disturbed to helpers will let us remove the synchronous fallback here.

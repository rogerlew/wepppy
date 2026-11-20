import { getValue } from '../state.js';
import { CATALOG_WAIT_MS, CatalogPreparationError, createCatalogReadiness, pollDelay } from './catalog-readiness.js';

/**
 * Query Engine HTTP helpers. No DOM/deck usage; relies on ctx for run context.
 * Returns POST wrappers scoped to the current run (and optional scenario).
 *
 * Query Engine runs as a separate service at /query-engine/ (no sitePrefix).
 * URL format: /query-engine/runs/{runid}/{config}/query
 * Scenario is passed in the request body as "scenario" parameter.
 */
export function createQueryEngine(ctx, { onCatalogState } = {}) {
  const catalog = onCatalogState ? createCatalogReadiness(onCatalogState) : null;
  let scenarioGeneration = 0;
  let roadsUnavailable = false;
  let roadsUnavailableReason = 'Run Roads to generate current results.';
  let roadsUnavailableCode = 'roads_results_unavailable';

  async function readResponse(resp, currentRun = true) {
    if (resp.status === 409) {
      const body = await resp.json();
      if (['roads_results_unavailable', 'roads_operation_busy'].includes(body.code)) {
        const reason = typeof body.error === 'string' ? body.error : body.error?.message;
        const message = typeof reason === 'string' && reason.trim() ? reason : (
          body.code === 'roads_operation_busy' ? 'Roads is busy; wait for the active operation to finish.' : 'Run Roads to generate current results.');
        if (!currentRun) {
          const error = new Error(message);
          error.code = body.code;
          error.foreignScenario = true;
          throw error;
        }
        roadsUnavailableCode = body.code;
        roadsUnavailableReason = message;
        if (!roadsUnavailable && typeof ctx.onRoadsUnavailable === 'function') {
          ctx.onRoadsUnavailable(roadsUnavailableReason);
        }
        roadsUnavailable = true;
      }
    }
    if (roadsUnavailable) {
      const error = new Error(roadsUnavailableReason);
      error.code = roadsUnavailableCode;
      throw error;
    }
    if (!resp.ok) return null;
    const result = await resp.json();
    if (roadsUnavailable) throw new Error('Roads results are no longer current.');
    return result;
  }

  function encodePathComponentPreserveSemicolons(value) {
    // Composite runids use ";;" delimiters. Preserve ";" for readability while still
    // encoding characters that would truncate or corrupt the request (e.g. #, ?, space).
    return encodeURIComponent(String(value || '')).replace(/%3B/gi, ';');
  }

  function getBaseUrl(runidOverride = null) {
    const runid = runidOverride || ctx.runid;
    let queryPath = `runs/${encodePathComponentPreserveSemicolons(runid)}`;
    if (ctx.config) {
      queryPath += `/${encodePathComponentPreserveSemicolons(ctx.config)}`;
    }
    return `/query-engine/${queryPath}/query`;
  }

  function resolveParentRunId(runid) {
    const raw = String(runid || '');
    const parts = raw.split(';;');
    if (
      parts.length >= 3 &&
      parts[parts.length - 2] &&
      (parts[parts.length - 2] === 'omni' || parts[parts.length - 2] === 'omni-contrast')
    ) {
      return parts.slice(0, -2).join(';;');
    }
    return raw;
  }

  function extractScenarioName(scenarioPath) {
    if (!scenarioPath) return null;
    const match = scenarioPath.match(/_pups\/omni\/scenarios\/([^/]+)/);
    return match ? match[1] : null;
  }

  function extractContrastId(scenarioPath) {
    if (!scenarioPath) return null;
    const match = scenarioPath.match(/_pups\/omni\/contrasts\/([^/]+)/);
    return match ? match[1] : null;
  }

  function resolveContrastRunId(scenarioPath) {
    const contrastId = extractContrastId(scenarioPath);
    if (!contrastId) return null;
    const parentRunId = resolveParentRunId(ctx.runid);
    return `${parentRunId};;omni-contrast;;${contrastId}`;
  }

  function scenarioTarget(scenarioPath) {
    const contrastRunId = resolveContrastRunId(scenarioPath);
    const scenario = contrastRunId ? null : extractScenarioName(scenarioPath);
    const runid = contrastRunId || (scenario ? resolveParentRunId(ctx.runid) : null);
    return [getBaseUrl(runid), scenario];
  }

  async function post(payload, target, currentRun, stillCurrent = () => true) {
    const [url, scenario] = target;
    const body = { ...payload };
    if (scenario) body.scenario = scenario;
    if (catalog) {
      if (!scenario) delete body.scenario;
      body.catalog_mode = 'wait';
    }
    const deadline = Date.now() + CATALOG_WAIT_MS;
    let nextDelay = 0;
    const ensureCurrent = () => {
      if (!stillCurrent()) throw new DOMException('Query target changed', 'AbortError');
    };
    while (true) {
      ensureCurrent();
      const entry = catalog?.start(url, scenario, deadline, nextDelay);
      await entry?.promise;
      ensureCurrent();
      if (entry?.error) throw entry.error;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify(body),
        signal: entry?.controller.signal,
      });
      ensureCurrent();
      if (catalog && [202, 409, 503].includes(response.status)) {
        const { code } = await response.clone().json().catch(() => ({}));
        ensureCurrent();
        const retry = code === 'catalog_preparing' ||
          (code === 'catalog_refresh_unavailable' && response.headers?.get('Retry-After'));
        if (retry && Date.now() < deadline) {
          // Drop a fulfilled readiness check without cancelling other queries
          // that have already been sent using it.
          catalog.invalidate(entry);
          nextDelay = pollDelay(response);
          continue;
        }
        if (['catalog_preparing', 'catalog_readonly', 'catalog_refresh_failed', 'catalog_refresh_unavailable'].includes(code)) {
          const error = new CatalogPreparationError(retry ? 'Results are taking longer to prepare.' : undefined);
          catalog.fail(entry, error);
          throw error;
        }
      }
      const result = await readResponse(response, currentRun);
      ensureCurrent();
      return result;
    }
  }

  function postQueryEngine(payload) {
    const path = getValue('currentScenarioPath');
    const [url, scenario] = scenarioTarget(path);
    const generation = scenarioGeneration;
    return post(payload, [url, scenario], url === getBaseUrl() && !scenario,
      () => scenarioGeneration === generation && getValue('currentScenarioPath') === path);
  }

  function postBaseQueryEngine(payload) {
    return post(payload, [getBaseUrl(), null], true);
  }

  function postQueryEngineForScenario(payload, scenarioPath) {
    const [url, scenario] = scenarioTarget(scenarioPath);
    return post(payload, [url, scenario], url === getBaseUrl() && !scenario);
  }

  function scenarioChanged(scenarioPath) {
    scenarioGeneration += 1;
    catalog?.keep([[getBaseUrl(), null], scenarioTarget(scenarioPath)]);
  }

  return { postQueryEngine, postBaseQueryEngine, postQueryEngineForScenario, scenarioChanged,
    resetCatalogReadiness: () => catalog?.keep([]), retryCatalogReadiness: () => catalog?.clearFailures() };
}

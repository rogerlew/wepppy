import { getValue } from '../state.js';

/**
 * Query Engine HTTP helpers. No DOM/deck usage; relies on ctx for run context.
 * Returns POST wrappers scoped to the current run (and optional scenario).
 * 
 * Query Engine runs as a separate service at /query-engine/ (no sitePrefix).
 * URL format: /query-engine/runs/{runid}/{config}/query
 * Scenario is passed in the request body as "scenario" parameter.
 */
export function createQueryEngine(ctx) {
  let roadsUnavailable = false;

  async function readResponse(resp) {
    if (resp.status === 409) {
      const body = await resp.json();
      if (body.code === 'roads_results_unavailable') {
        if (!roadsUnavailable && typeof ctx.onRoadsUnavailable === 'function') {
          ctx.onRoadsUnavailable();
        }
        roadsUnavailable = true;
      }
    }
    if (roadsUnavailable) {
      const error = new Error('Run Roads to generate current results.');
      error.code = 'roads_results_unavailable';
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

  async function postQueryEngine(payload) {
    const scenarioPath = getValue('currentScenarioPath');
    const contrastRunId = resolveContrastRunId(scenarioPath);
    const scenario = contrastRunId ? null : extractScenarioName(scenarioPath);
    const runidOverride = contrastRunId || (scenario ? resolveParentRunId(ctx.runid) : null);
    const targetUrl = getBaseUrl(runidOverride);
    const body = scenario ? { ...payload, scenario } : payload;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    });
    return readResponse(resp);
  }

  async function postBaseQueryEngine(payload) {
    const targetUrl = getBaseUrl();
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    return readResponse(resp);
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    const contrastRunId = resolveContrastRunId(scenarioPath);
    const scenario = contrastRunId ? null : extractScenarioName(scenarioPath);
    const runidOverride = contrastRunId || (scenario ? resolveParentRunId(ctx.runid) : null);
    const targetUrl = getBaseUrl(runidOverride);
    const body = scenario ? { ...payload, scenario } : payload;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    });
    return readResponse(resp);
  }

  return { postQueryEngine, postBaseQueryEngine, postQueryEngineForScenario };
}

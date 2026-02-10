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
  function getBaseUrl(runidOverride = null) {
    const runid = runidOverride || ctx.runid;
    let queryPath = `runs/${runid}`;
    if (ctx.config) {
      queryPath += `/${ctx.config}`;
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
    const targetUrl = getBaseUrl(contrastRunId);
    const scenario = contrastRunId ? null : extractScenarioName(scenarioPath);
    const body = scenario ? { ...payload, scenario } : payload;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postBaseQueryEngine(payload) {
    const targetUrl = getBaseUrl();
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    const contrastRunId = resolveContrastRunId(scenarioPath);
    const targetUrl = getBaseUrl(contrastRunId);
    const scenario = contrastRunId ? null : extractScenarioName(scenarioPath);
    const body = scenario ? { ...payload, scenario } : payload;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  return { postQueryEngine, postBaseQueryEngine, postQueryEngineForScenario };
}

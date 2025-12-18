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
  function getBaseUrl() {
    let queryPath = `runs/${ctx.runid}`;
    if (ctx.config) {
      queryPath += `/${ctx.config}`;
    }
    return `/query-engine/${queryPath}/query`;
  }

  async function postQueryEngine(payload) {
    const targetUrl = getBaseUrl();
    const scenarioPath = getValue('currentScenarioPath');
    // Extract scenario name from path like "_pups/omni/scenarios/scenario_name"
    let scenario = null;
    if (scenarioPath) {
      const match = scenarioPath.match(/_pups\/omni\/scenarios\/([^/]+)/);
      scenario = match ? match[1] : null;
    }
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
    const targetUrl = getBaseUrl();
    // Extract scenario name from path like "_pups/omni/scenarios/scenario_name"
    let scenario = null;
    if (scenarioPath) {
      const match = scenarioPath.match(/_pups\/omni\/scenarios\/([^/]+)/);
      scenario = match ? match[1] : null;
    }
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

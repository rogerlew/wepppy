import { getValue } from '../state.js';

/**
 * Query Engine HTTP helpers. No DOM/deck usage; relies on ctx for run context.
 * Returns POST wrappers scoped to the current run (and optional scenario).
 * 
 * Query Engine runs as a separate service at /query-engine/ (no sitePrefix).
 * URL format: /query-engine/runs/{runid}/{config}/query
 */
export function createQueryEngine(ctx) {
  async function postQueryEngine(payload) {
    let queryPath = `runs/${ctx.runid}`;
    if (ctx.config) {
      queryPath += `/${ctx.config}`;
    }
    const scenarioPath = getValue('currentScenarioPath');
    if (scenarioPath) {
      queryPath += `/${scenarioPath}`;
    }
    const targetUrl = `/query-engine/${queryPath}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postBaseQueryEngine(payload) {
    const basePath = ctx.config ? `runs/${ctx.runid}/${ctx.config}` : `runs/${ctx.runid}`;
    const targetUrl = `/query-engine/${basePath}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    // For scenario-specific queries, mimic main path + scenario
    let queryPath = `runs/${ctx.runid}`;
    if (ctx.config) {
      queryPath += `/${ctx.config}`;
    }
    if (scenarioPath) {
      queryPath += `/${scenarioPath}`;
    }
    const targetUrl = `/query-engine/${queryPath}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  return { postQueryEngine, postBaseQueryEngine, postQueryEngineForScenario };
}

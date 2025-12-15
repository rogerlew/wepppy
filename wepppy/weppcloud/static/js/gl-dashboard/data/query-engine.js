import { getValue } from '../state.js';

function getOrigin() {
  return window.location.origin || `${window.location.protocol}//${window.location.host}`;
}

export function createQueryEngine(ctx) {
  const origin = getOrigin();

  async function postQueryEngine(payload) {
    let queryPath = `runs/${ctx.runid}`;
    const scenarioPath = getValue('currentScenarioPath');
    if (scenarioPath) {
      queryPath += `/${scenarioPath}`;
    }
    const targetUrl = `${origin}/query-engine/${queryPath}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postBaseQueryEngine(payload) {
    const targetUrl = `${origin}/query-engine/runs/${ctx.runid}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    let queryPath = `runs/${ctx.runid}`;
    if (scenarioPath) {
      queryPath += `/${scenarioPath}`;
    }
    const targetUrl = `${origin}/query-engine/${queryPath}/query`;
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

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
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      let message = `Query Engine request failed (${resp.status})`;
      try {
        const data = await resp.json();
        if (data && data.error) {
          message = data.error;
        } else if (data && data.errors && data.errors[0] && data.errors[0].detail) {
          message = data.errors[0].detail;
        }
      } catch (error) {
        // ignore parse failure
      }
      const err = new Error(message);
      err.status = resp.status;
      throw err;
    }
    return resp.json();
  }

  async function postQueryEngineForScenario(payload, scenarioPath) {
    const targetUrl = getBaseUrl();
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
    if (!resp.ok) {
      let message = `Query Engine request failed (${resp.status})`;
      try {
        const data = await resp.json();
        if (data && data.error) {
          message = data.error;
        } else if (data && data.errors && data.errors[0] && data.errors[0].detail) {
          message = data.errors[0].detail;
        }
      } catch (error) {
        // ignore parse failure
      }
      const err = new Error(message);
      err.status = resp.status;
      throw err;
    }
    return resp.json();
  }

  return { postQueryEngine, postQueryEngineForScenario };
}

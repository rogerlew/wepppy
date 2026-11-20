export const CATALOG_WAIT_MS = 120000;
const DEFAULT_POLL_MS = 2000;

export class CatalogPreparationError extends Error {
  constructor(message = 'Could not prepare watershed results.') {
    super(message);
    this.code = 'catalog_preparation';
  }
}

function delay(ms, signal) {
  signal.throwIfAborted();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', cancel);
      resolve();
    }, ms);
    function cancel() {
      clearTimeout(timer);
      reject(signal.reason);
    }
    signal.addEventListener('abort', cancel, { once: true });
  });
}

export function pollDelay(response) {
  const seconds = Number(response.headers?.get('Retry-After'));
  return seconds > 0 ? seconds * 1000 : DEFAULT_POLL_MS;
}

export function createCatalogReadiness(onState) {
  const checks = new Map();

  async function check(url, scenario, entry, deadline, waitBeforePrepare) {
    const { signal } = entry.controller;
    const timer = setTimeout(() =>
      entry.controller.abort(new CatalogPreparationError('Results are taking longer to prepare.')),
    Math.max(0, deadline - Date.now()));
    const base = url.slice(0, -'/query'.length);
    const statusURL = base + '/catalog/status' +
      (scenario ? '?' + new URLSearchParams({ scenario }) : '');
    const prepare = () => fetch(base + '/catalog/prepare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(scenario ? { scenario } : {}),
      signal,
    });
    try {
      if (waitBeforePrepare) {
        onState(entry.key, 'preparing');
        await delay(waitBeforePrepare, signal);
      }
      let response = await prepare();
      while (response.status === 202 || (response.status === 503 && response.headers?.get('Retry-After'))) {
        onState(entry.key, 'preparing');
        await delay(pollDelay(response), signal);
        response = response.status === 202
          ? await fetch(statusURL, { headers: { Accept: 'application/json' }, signal })
          : await prepare();
      }
      const body = await response.json();
      if (!response.ok || body.state !== 'ready') {
        throw new CatalogPreparationError();
      }
      signal.throwIfAborted();
      onState(entry.key, 'ready');
    } catch (error) {
      if (checks.get(entry.key) !== entry) throw signal.reason || error;
      const failure = signal.reason instanceof CatalogPreparationError ? signal.reason : new CatalogPreparationError();
      fail(entry, failure);
      throw failure;
    } finally {
      clearTimeout(timer);
    }
  }

  function start(url, scenario, deadline, waitBeforePrepare) {
    const key = JSON.stringify([url, scenario]);
    let entry = checks.get(key);
    if (!entry) {
      entry = { key, controller: new AbortController() };
      checks.set(key, entry);
      entry.promise = check(url, scenario, entry, deadline, waitBeforePrepare);
    }
    return entry;
  }

  function invalidate(entry) {
    if (checks.get(entry.key) !== entry) return;
    checks.delete(entry.key);
    onState(entry.key, 'idle');
  }

  function discard(entry) {
    invalidate(entry);
    entry.controller.abort();
  }

  function keep(targets) {
    const keys = new Set(targets.map((target) => JSON.stringify(target)));
    for (const entry of checks.values()) {
      if (!keys.has(entry.key)) discard(entry);
    }
  }

  function fail(entry, error) {
    if (checks.get(entry.key) !== entry) return;
    entry.error = error;
    onState(entry.key, 'unavailable', error.message);
  }

  function clearFailures() {
    for (const entry of checks.values()) {
      if (entry.error) discard(entry);
    }
  }

  return { start, invalidate, keep, fail, clearFailures };
}

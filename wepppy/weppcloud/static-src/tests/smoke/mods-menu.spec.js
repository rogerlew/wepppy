/* eslint-env browser, node */
import { test, expect } from '@playwright/test';

// The Mods menu spec validates the relationship between the project checkboxes,
// preflight/TOC nav entries, and controller sections. Run it against a disturbed
// profile seed (for example, SMOKE_RUN_CONFIG=disturbed9002_wbt or a promoted
// profile under /workdir/wepppy-test-engine-data/profiles) so the Disturbed/SBS
// controller is present and runContext.mods reflects real project state.

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'disturbed9002_wbt';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;
let skipSuite = false;
let skipReason = 'Mods smoke requires a run. Provide SMOKE_RUN_PATH or enable SMOKE_CREATE_RUN.';

const MOD_DEPENDENCY_GRAPH = {
  omni: ['treatments']
};

function buildUrl(path) {
  const base = baseURL.replace(/\/$/, '');
  if (base.endsWith('/weppcloud') && path.startsWith('/weppcloud/')) {
    const relativePath = path.substring('/weppcloud'.length);
    return base + relativePath;
  }
  return new URL(path, base).toString();
}

function sanitizeRunUrl(url) {
  if (!url) return url;
  try {
    const parsed = new URL(url);
    parsed.searchParams.delete('playwright_load_all');
    return parsed.toString();
  } catch (_err) {
    try {
      const resolved = new URL(url, baseURL);
      resolved.searchParams.delete('playwright_load_all');
      return resolved.toString();
    } catch {
      return url;
    }
  }
}

function parseOverrides() {
  if (!process.env.SMOKE_RUN_OVERRIDES) {
    return {};
  }
  try {
    const parsed = JSON.parse(process.env.SMOKE_RUN_OVERRIDES);
    if (parsed && typeof parsed === 'object') {
      return parsed;
    }
    throw new Error('SMOKE_RUN_OVERRIDES must be a JSON object');
  } catch (err) {
    skipSuite = true;
    skipReason = `Invalid SMOKE_RUN_OVERRIDES JSON: ${err.message}`;
    return {};
  }
}

test.describe('run header mods menu', () => {
  test.beforeAll(async ({ request }) => {
    if (!targetRunPath && shouldProvision) {
      const overrides = parseOverrides();
      if (skipSuite) return;

      const createUrl = buildUrl('/weppcloud/tests/api/create-run');
      const response = await request.post(createUrl, {
        data: {
          config: configSlug,
          overrides
        }
      });

      if (!response.ok()) {
        skipSuite = true;
        skipReason = `Failed to provision run via ${createUrl}: ${response.status()} ${response.statusText()}`;
        return;
      }

      const payload = await response.json();
      if (!payload?.run?.url || !payload.run.runid) {
        skipSuite = true;
        skipReason = 'create-run returned an unexpected payload.';
        return;
      }

      createdRunId = payload.run.runid;
      targetRunPath = buildUrl(payload.run.url);
    }

    if (!targetRunPath) {
      skipSuite = true;
      return;
    }

    targetRunPath = sanitizeRunUrl(targetRunPath);
  });

  test.afterAll(async ({ request }) => {
    if (createdRunId && !keepRun && !skipSuite) {
      try {
        await request.delete(buildUrl(`/weppcloud/tests/api/run/${createdRunId}`));
      } catch (err) {
        console.warn('Failed to delete mods smoke run', err);
      }
    }
  });

  test('toggles sync project state, TOC, and controller sections', async ({ page }) => {
    if (skipSuite) test.skip(true, skipReason);

    await page.goto(targetRunPath, { waitUntil: 'networkidle' });
    await page.waitForFunction(() => Boolean(window.runContext && window.runContext.mods), null, { timeout: 15000 });

    const contextInfo = await page.evaluate(() => ({
      playwrightLoadAll: Boolean(window.runContext?.flags?.playwrightLoadAll),
      hasDisturbed: Boolean(window.runContext?.mods?.flags?.disturbed),
      initialMods: Array.isArray(window.runContext?.mods?.list) ? window.runContext.mods.list.slice() : []
    }));

    expect(contextInfo.playwrightLoadAll).toBeFalsy();
    expect(contextInfo.hasDisturbed).toBeTruthy();
    await expect(page.locator('#disturbed-sbs')).toBeVisible();

    const initialSnapshot = await page.evaluate(() => {
      const ctx = window.runContext?.mods;
      return {
        list: Array.isArray(ctx?.list) ? ctx.list.slice() : [],
        flags: ctx?.flags ? { ...ctx.flags } : {}
      };
    });

    const modsMenu = page.locator('.wc-run-header__mods');
    await modsMenu.waitFor();
    await modsMenu.evaluate((details) => { details.open = true; });

    const modMeta = await collectModMeta(page);
    expect(modMeta.length).toBeGreaterThan(0);

    const initialStates = {};
    for (const meta of modMeta) {
      const checkbox = page.locator(`input[data-project-mod="${meta.name}"]`);
      const checked = await checkbox.isChecked();
      initialStates[meta.name] = checked;
      await expectRunContextState(page, meta.name, checked, `Initial state mismatch for ${meta.label}`);
      await assertModUiState(page, meta.name, checked, meta.label);
    }

    const topoOrder = buildTopologicalOrder(modMeta.map((meta) => meta.name));

    await test.step('toggle every mod to the opposite state', async () => {
      await runModToggleCycle(page, topoOrder, initialStates, 'invert');
    });

    await test.step('toggle every mod back to its original state', async () => {
      await runModToggleCycle(page, topoOrder, initialStates, 'restore');
    });

    const finalSnapshot = await page.evaluate(() => {
      const ctx = window.runContext?.mods;
      return {
        list: Array.isArray(ctx?.list) ? ctx.list.slice() : [],
        flags: ctx?.flags ? { ...ctx.flags } : {}
      };
    });

    expect(sortStrings(finalSnapshot.list)).toEqual(sortStrings(initialSnapshot.list));
    for (const meta of modMeta) {
      const expectedState = initialStates[meta.name];
      expect(Boolean(finalSnapshot.flags[meta.name])).toBe(expectedState);
      await assertModUiState(page, meta.name, expectedState, meta.label);
    }
  });
});

async function collectModMeta(page) {
  const entries = await page.$$eval('[data-project-mod]', (nodes) => nodes.map((node) => {
    const name = node.getAttribute('data-project-mod');
    if (!name) return null;
    const labelNode = node.nextElementSibling;
    const label = labelNode ? labelNode.textContent.trim() : name;
    return { name, label };
  }));
  return entries.filter(Boolean);
}

async function expectRunContextState(page, modName, expected, message) {
  await page.waitForFunction(
    ({ name, state }) => {
      const ctx = window.runContext?.mods;
      if (!ctx) return false;
      const flags = ctx.flags || {};
      const list = Array.isArray(ctx.list) ? ctx.list : [];
      const flagMatch = Boolean(flags[name]) === state;
      const listMatch = state ? list.includes(name) : !list.includes(name);
      return flagMatch && listMatch;
    },
    { name: modName, state: expected },
    { timeout: 15000 }
  );
}

async function assertModUiState(page, modName, shouldBeEnabled, label) {
  const navLocator = page.locator(`[data-mod-nav="${modName}"]`);
  await expect(navLocator, `Nav entry missing for ${label || modName}`).toHaveCount(1);
  const navHidden = await navLocator.evaluate((el) => el.hasAttribute('hidden'));
  expect(navHidden).toBe(!shouldBeEnabled);

  const sectionLocator = page.locator(`[data-mod-section="${modName}"]`);
  await expect(sectionLocator, `Controller section missing for ${label || modName}`).toHaveCount(1);
  const sectionHidden = await sectionLocator.evaluate((el) => el.hasAttribute('hidden'));
  expect(sectionHidden).toBe(!shouldBeEnabled);

  const sectionCount = await sectionLocator.locator('section').count();
  if (shouldBeEnabled) {
    expect(sectionCount, `${label || modName} section should render controller markup`).toBeGreaterThan(0);
  } else {
    expect(sectionCount, `${label || modName} section should be empty when disabled`).toBe(0);
  }
}

async function ensureModState(page, modName, desiredState) {
  const checkbox = page.locator(`input[data-project-mod="${modName}"]`);
  const current = await checkbox.isChecked();
  if (current === desiredState) {
    await assertModUiState(page, modName, desiredState);
    return;
  }

  const modResponsePromise = page.waitForResponse((response) => {
    if (!response.url().includes('/tasks/set_mod') || response.request().method() !== 'POST') {
      return false;
    }
    try {
      const payload = JSON.parse(response.request().postData() || '{}');
      return payload.mod === modName;
    } catch {
      return false;
    }
  });
  const viewResponsePromise = desiredState
    ? page.waitForResponse((response) => response.url().includes(`/view/mod/${encodeURIComponent(modName)}`))
    : Promise.resolve();

  await checkbox.click();
  const modResponse = await modResponsePromise;
  const payload = await modResponse.json().catch(() => null);
  expect(payload?.Success).toBeTruthy();
  await viewResponsePromise;

  await expectRunContextState(page, modName, desiredState, `runContext failed to update for ${modName}`);
  await assertModUiState(page, modName, desiredState);
}

async function runModToggleCycle(page, topoOrder, initialStates, mode) {
  if (mode === 'invert') {
    const enableTargets = topoOrder.filter((name) => !initialStates[name]);
    for (const modName of enableTargets) {
      await ensureModState(page, modName, true);
    }
    const disableTargets = [...topoOrder].reverse().filter((name) => initialStates[name]);
    for (const modName of disableTargets) {
      await ensureModState(page, modName, false);
    }
    return;
  }

  if (mode === 'restore') {
    const enableTargets = topoOrder.filter((name) => initialStates[name]);
    for (const modName of enableTargets) {
      await ensureModState(page, modName, true);
    }
    const disableTargets = [...topoOrder].reverse().filter((name) => !initialStates[name]);
    for (const modName of disableTargets) {
      await ensureModState(page, modName, false);
    }
  }
}

function buildTopologicalOrder(modNames) {
  const nameSet = new Set(modNames);
  const visited = new Set();
  const visiting = new Set();
  const result = [];

  function dfs(node) {
    if (visited.has(node)) return;
    if (visiting.has(node)) {
      throw new Error(`Cycle detected while ordering mods: ${node}`);
    }
    visiting.add(node);
    const deps = MOD_DEPENDENCY_GRAPH[node] || [];
    for (const dep of deps) {
      if (nameSet.has(dep)) {
        dfs(dep);
      }
    }
    visiting.delete(node);
    visited.add(node);
    result.push(node);
  }

  for (const name of modNames) {
    dfs(name);
  }
  return result;
}

function sortStrings(values) {
  return [...values].sort((a, b) => (a > b ? 1 : a < b ? -1 : 0));
}

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import AxeBuilder from '@axe-core/playwright';
import { test, expect } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
const defaultAgentCredentialsFile = path.join(repoRoot, 'docker', 'secrets', 'ally-agent-smoke.env');

const baseURL = process.env.SMOKE_BASE_URL || 'http://localhost:8080';
const shouldProvision = process.env.SMOKE_CREATE_RUN !== 'false';
const keepRun = process.env.SMOKE_KEEP_RUN === 'true';
const configSlug = process.env.SMOKE_RUN_CONFIG || 'disturbed9002_wbt';
const reportDir = process.env.AXE_OUTPUT_DIR || path.join('test-results', 'a11y');
const axeTags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];
const disabledRules = ['color-contrast'];
const forwardedProtoHeader = { 'X-Forwarded-Proto': 'https' };
const agentAccountLabel = process.env.SMOKE_AGENT_ACCOUNT_LABEL || 'ally-agent';
const requireAgentCredentials = ['1', 'true', 'yes'].includes(
  String(process.env.SMOKE_AGENT_REQUIRED || '').trim().toLowerCase()
);
const agentCredentialsFile = process.env.SMOKE_AGENT_CREDENTIALS_FILE || defaultAgentCredentialsFile;

const sitePrefix = (() => {
  const hasSmokePrefix = Object.prototype.hasOwnProperty.call(process.env, 'SMOKE_SITE_PREFIX');
  if (hasSmokePrefix) {
    return process.env.SMOKE_SITE_PREFIX || '';
  }
  try {
    const parsed = new URL(baseURL);
    const normalizedPath = (parsed.pathname || '').trim();
    if (normalizedPath && normalizedPath !== '/') {
      return normalizedPath.endsWith('/') ? normalizedPath.slice(0, -1) : normalizedPath;
    }
  } catch (_err) {
    // ignore invalid URL and fall back to repository default prefix
  }
  return '/weppcloud';
})();

let targetRunPath = process.env.SMOKE_RUN_PATH || '';
let createdRunId = null;
let skipRunScan = false;
let runSkipReason = 'No target run available. Provide SMOKE_RUN_PATH or enable SMOKE_CREATE_RUN.';
let agentCredentials = null;
let agentCredentialsSource = '';
let runTargetPrepared = false;
let runTargetPromise = null;
const scanEntries = [];

function buildUrl(pathname) {
  if (!pathname) {
    return '';
  }

  if (/^https?:\/\//i.test(pathname)) {
    return pathname;
  }

  const base = baseURL.replace(/\/$/, '');
  if (base.endsWith('/weppcloud') && pathname.startsWith('/weppcloud/')) {
    const relativePath = pathname.substring('/weppcloud'.length);
    return base + relativePath;
  }

  return new URL(pathname, base).toString();
}

function withSitePrefix(pathname) {
  if (!pathname) {
    return pathname;
  }
  if (/^https?:\/\//i.test(pathname)) {
    return pathname;
  }
  const normalizedPath = pathname.startsWith('/') ? pathname : `/${pathname}`;
  const normalizedPrefix = (sitePrefix || '').trim();
  if (!normalizedPrefix || normalizedPrefix === '/') {
    return normalizedPath;
  }
  const safePrefix = normalizedPrefix.endsWith('/') ? normalizedPrefix.slice(0, -1) : normalizedPrefix;
  if (normalizedPath.startsWith(`${safePrefix}/`) || normalizedPath === safePrefix) {
    return normalizedPath;
  }
  return `${safePrefix}${normalizedPath}`;
}

function parseEnvFile(content) {
  const parsed = {};
  const lines = String(content || '').split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      continue;
    }
    const equalsIndex = trimmed.indexOf('=');
    if (equalsIndex <= 0) {
      continue;
    }
    const key = trimmed.slice(0, equalsIndex).trim();
    let value = trimmed.slice(equalsIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    parsed[key] = value;
  }
  return parsed;
}

function firstNonEmpty(values) {
  for (const value of values) {
    const normalized = String(value || '').trim();
    if (normalized) {
      return normalized;
    }
  }
  return '';
}

async function resolveAgentCredentials() {
  const envEmail = firstNonEmpty([process.env.ALLY_AGENT_EMAIL, process.env.SMOKE_AGENT_EMAIL]);
  const envPassword = firstNonEmpty([process.env.ALLY_AGENT_PASSWORD, process.env.SMOKE_AGENT_PASSWORD]);
  if (envEmail && envPassword) {
    return {
      credentials: { email: envEmail, password: envPassword },
      source: 'environment',
    };
  }

  try {
    const fileContent = await fs.readFile(agentCredentialsFile, 'utf-8');
    const parsed = parseEnvFile(fileContent);
    const fileEmail = firstNonEmpty([parsed.ALLY_AGENT_EMAIL, parsed.SMOKE_AGENT_EMAIL]);
    const filePassword = firstNonEmpty([parsed.ALLY_AGENT_PASSWORD, parsed.SMOKE_AGENT_PASSWORD]);
    if (fileEmail && filePassword) {
      return {
        credentials: { email: fileEmail, password: filePassword },
        source: agentCredentialsFile,
      };
    }
  } catch (err) {
    if (err && err.code !== 'ENOENT') {
      throw err;
    }
  }

  return { credentials: null, source: '' };
}

async function readCsrfToken(page) {
  const token = await page.evaluate(() => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) {
      const metaToken = String(meta.getAttribute('content') || '').trim();
      if (metaToken) {
        return metaToken;
      }
    }
    const field = document.querySelector('input[name="csrf_token"]');
    if (field instanceof HTMLInputElement) {
      const fieldToken = String(field.value || '').trim();
      if (fieldToken) {
        return fieldToken;
      }
    }
    return '';
  });
  return String(token || '').trim();
}

function csrfHeaders(token) {
  const headers = { ...forwardedProtoHeader };
  if (token) {
    headers['X-CSRFToken'] = token;
  }
  return headers;
}

async function probeAuthenticatedSession(page) {
  let csrfToken = await readCsrfToken(page);
  if (!csrfToken) {
    await page.goto(buildUrl(withSitePrefix('/interfaces/')), { waitUntil: 'domcontentloaded' });
    csrfToken = await readCsrfToken(page);
  }
  if (!csrfToken) {
    return {
      authenticated: false,
      status: 0,
      reason: 'Could not resolve CSRF token for auth probe.',
    };
  }

  const probeResponse = await page.request.post(buildUrl(withSitePrefix('/api/auth/rq-engine-token')), {
    headers: csrfHeaders(csrfToken),
  });
  if (probeResponse.ok()) {
    return { authenticated: true, status: probeResponse.status(), reason: 'authenticated' };
  }

  const body = (await probeResponse.text()).trim();
  const bodyPreview = body ? ` Body: ${body.slice(0, 160)}` : '';
  return {
    authenticated: false,
    status: probeResponse.status(),
    reason: `auth probe failed (${probeResponse.status()} ${probeResponse.statusText()}).${bodyPreview}`,
  };
}

async function mirrorSecureAuthCookiesForHttp(page) {
  const rootUrl = new URL(buildUrl(withSitePrefix('/')));
  const cookies = await page.context().cookies();
  const mirrored = cookies
    .filter((cookie) => (cookie.name === 'session' || cookie.name === 'remember_token') && cookie.secure)
    .map((cookie) => ({
      name: cookie.name,
      value: cookie.value,
      url: `${rootUrl.origin}${cookie.path || '/'}`,
      sameSite: cookie.sameSite,
      expires: cookie.expires,
      httpOnly: cookie.httpOnly,
      secure: false,
    }));
  if (mirrored.length === 0) {
    return 0;
  }
  await page.context().addCookies(mirrored);
  return mirrored.length;
}

async function ensureAgentSession(page) {
  if (!agentCredentials) {
    return {
      authenticated: false,
      reason: `No ${agentAccountLabel} credentials found. Set ALLY_AGENT_EMAIL/ALLY_AGENT_PASSWORD or populate ${agentCredentialsFile}.`,
    };
  }

  const loginUrl = buildUrl(withSitePrefix('/login'));
  await page.goto(loginUrl, { waitUntil: 'domcontentloaded' });

  const loginForm = page.locator('form[name="login_user_form"]');
  if ((await loginForm.count()) === 0) {
    return { authenticated: true, reason: `${agentAccountLabel} session already active.` };
  }

  const emailField = loginForm.locator('input[name="email"]');
  const usernameField = loginForm.locator('input[name="username"]');
  if ((await emailField.count()) > 0) {
    await emailField.fill(agentCredentials.email);
  } else if ((await usernameField.count()) > 0) {
    await usernameField.fill(agentCredentials.email);
  } else {
    return { authenticated: false, reason: 'Login form missing email/username field.' };
  }

  const passwordField = loginForm.locator('input[name="password"]');
  if ((await passwordField.count()) === 0) {
    return { authenticated: false, reason: 'Login form missing password field.' };
  }
  await passwordField.fill(agentCredentials.password);

  const rememberField = loginForm.locator('input[name="remember"]');
  if ((await rememberField.count()) > 0) {
    await rememberField.check({ force: true });
  }

  const submitButton = loginForm.locator('[type="submit"]').first();
  if ((await submitButton.count()) === 0) {
    return { authenticated: false, reason: 'Login form missing submit button.' };
  }

  await Promise.all([
    page.waitForLoadState('networkidle'),
    submitButton.click(),
  ]);

  if ((await page.locator('form[name="login_user_form"]').count()) > 0) {
    const messageText = (await page
      .locator('.wc-auth-message, .pure-form-message-inline[role="alert"]')
      .allTextContents())
      .map((text) => text.trim())
      .filter(Boolean)
      .join('; ');
    const details = messageText || 'no server error message rendered';
    return {
      authenticated: false,
      reason: `${agentAccountLabel} login failed (${details}).`,
    };
  }

  let authProbe = await probeAuthenticatedSession(page);
  if (authProbe.authenticated) {
    return { authenticated: true, reason: `${agentAccountLabel} login succeeded.` };
  }

  if (baseURL.startsWith('http://')) {
    const mirroredCount = await mirrorSecureAuthCookiesForHttp(page);
    if (mirroredCount > 0) {
      authProbe = await probeAuthenticatedSession(page);
      if (authProbe.authenticated) {
        return {
          authenticated: true,
          reason: `${agentAccountLabel} login succeeded after local HTTP cookie mirror.`,
        };
      }
    }
  }

  return { authenticated: false, reason: `${agentAccountLabel} login failed (${authProbe.reason})` };
}

async function ensureRunTarget(page) {
  if (runTargetPrepared) {
    return;
  }
  if (runTargetPromise) {
    await runTargetPromise;
    return;
  }

  runTargetPromise = (async () => {
    if (targetRunPath) {
      runTargetPrepared = true;
      return;
    }
    if (!shouldProvision) {
      skipRunScan = true;
      runSkipReason = 'Run scan skipped because SMOKE_CREATE_RUN=false and SMOKE_RUN_PATH is unset.';
      runTargetPrepared = true;
      return;
    }

    const loginResult = await ensureAgentSession(page);
    if (!loginResult.authenticated) {
      skipRunScan = true;
      runSkipReason = `Run scan skipped: ${loginResult.reason}`;
      runTargetPrepared = true;
      return;
    }

    let csrfToken = await readCsrfToken(page);
    if (!csrfToken) {
      await page.goto(buildUrl(withSitePrefix('/interfaces/')), { waitUntil: 'domcontentloaded' });
      csrfToken = await readCsrfToken(page);
    }
    if (!csrfToken) {
      skipRunScan = true;
      runSkipReason = 'Run scan skipped: could not resolve CSRF token after authenticated login.';
      runTargetPrepared = true;
      return;
    }

    const response = await page.request.post(buildUrl(withSitePrefix('/tests/api/create-run')), {
      data: { config: configSlug },
      headers: csrfHeaders(csrfToken),
    });

    if (!response.ok()) {
      const responseBody = (await response.text()).trim();
      const preview = responseBody ? ` Body: ${responseBody.slice(0, 200)}` : '';
      skipRunScan = true;
      runSkipReason = `Run scan skipped: create-run failed (${response.status()} ${response.statusText()}).${preview}`;
      runTargetPrepared = true;
      return;
    }

    const payload = await response.json();
    if (!payload?.run?.url || !payload.run.runid) {
      skipRunScan = true;
      runSkipReason = 'Run scan skipped: create-run returned an unexpected payload.';
      runTargetPrepared = true;
      return;
    }

    createdRunId = payload.run.runid;
    targetRunPath = buildUrl(payload.run.url);
    runTargetPrepared = true;
  })();

  await runTargetPromise;
}

async function cleanupProvisionedRun(page) {
  if (!createdRunId || keepRun) {
    return;
  }
  try {
    let csrfToken = await readCsrfToken(page);
    if (!csrfToken) {
      await page.goto(buildUrl(withSitePrefix('/interfaces/')), { waitUntil: 'domcontentloaded' });
      csrfToken = await readCsrfToken(page);
    }
    const response = await page.request.delete(buildUrl(withSitePrefix(`/tests/api/run/${createdRunId}`)), {
      headers: csrfHeaders(csrfToken),
    });
    if (!response.ok()) {
      const body = (await response.text()).trim();
      console.warn(`[axe] Failed to delete run ${createdRunId}: ${response.status()} ${response.statusText()} ${body}`);
    }
  } catch (err) {
    console.warn('Failed to delete axe smoke run', err);
  } finally {
    createdRunId = null;
  }
}

function countImpacts(violations) {
  const impactCounts = {
    critical: 0,
    serious: 0,
    moderate: 0,
    minor: 0,
    unknown: 0,
  };

  for (const violation of violations) {
    const key = violation.impact || 'unknown';
    if (!(key in impactCounts)) {
      impactCounts.unknown += 1;
      continue;
    }
    impactCounts[key] += 1;
  }

  return impactCounts;
}

async function runAxeScan(page, pageId) {
  const axeResults = await new AxeBuilder({ page })
    .withTags(axeTags)
    .disableRules(disabledRules)
    .analyze();

  const violations = axeResults.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact || 'unknown',
    help: violation.help,
    helpUrl: violation.helpUrl,
    nodeCount: violation.nodes.length,
    targets: violation.nodes.slice(0, 5).map((node) => node.target),
  }));

  const entry = {
    pageId,
    url: page.url(),
    scannedAt: new Date().toISOString(),
    violations,
    violationCount: violations.length,
    impactCounts: countImpacts(violations),
    incompleteCount: axeResults.incomplete.length,
    inapplicableCount: axeResults.inapplicable.length,
    passCount: axeResults.passes.length,
  };

  scanEntries.push(entry);
  return entry;
}

function buildReportPayload() {
  const totals = {
    pagesScanned: scanEntries.length,
    violations: 0,
    incomplete: 0,
    inapplicable: 0,
    passes: 0,
    impacts: {
      critical: 0,
      serious: 0,
      moderate: 0,
      minor: 0,
      unknown: 0,
    },
  };

  for (const entry of scanEntries) {
    totals.violations += entry.violationCount;
    totals.incomplete += entry.incompleteCount;
    totals.inapplicable += entry.inapplicableCount;
    totals.passes += entry.passCount;
    totals.impacts.critical += entry.impactCounts.critical;
    totals.impacts.serious += entry.impactCounts.serious;
    totals.impacts.moderate += entry.impactCounts.moderate;
    totals.impacts.minor += entry.impactCounts.minor;
    totals.impacts.unknown += entry.impactCounts.unknown;
  }

  return {
    generatedAt: new Date().toISOString(),
    baseURL,
    tags: axeTags,
    disabledRules,
    totals,
    scans: scanEntries,
  };
}

function buildMarkdownReport(payload) {
  const lines = [
    '# Axe Accessibility Summary',
    '',
    `Generated: ${payload.generatedAt}`,
    '',
    `Base URL: \`${payload.baseURL}\``,
    '',
    `Tags: ${payload.tags.join(', ')}`,
    '',
    `Disabled rules: ${payload.disabledRules.join(', ')}`,
    '',
    '## Totals',
    '',
    `- Pages scanned: ${payload.totals.pagesScanned}`,
    `- Violations: ${payload.totals.violations}`,
    `- Critical: ${payload.totals.impacts.critical}`,
    `- Serious: ${payload.totals.impacts.serious}`,
    `- Moderate: ${payload.totals.impacts.moderate}`,
    `- Minor: ${payload.totals.impacts.minor}`,
    `- Unknown impact: ${payload.totals.impacts.unknown}`,
    `- Incomplete checks: ${payload.totals.incomplete}`,
    '',
    '## Per Page',
    '',
    '| Page | URL | Violations | Critical | Serious | Moderate | Minor |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ];

  for (const entry of payload.scans) {
    lines.push(
      `| ${entry.pageId} | ${entry.url} | ${entry.violationCount} | ${entry.impactCounts.critical} | ${entry.impactCounts.serious} | ${entry.impactCounts.moderate} | ${entry.impactCounts.minor} |`
    );
  }

  lines.push('', '## Notes', '', '- This suite is manual-gate evidence and does not fail on violations by default.');
  return `${lines.join('\n')}\n`;
}

async function writeAxeReport() {
  const payload = buildReportPayload();
  await fs.mkdir(reportDir, { recursive: true });

  const jsonPath = path.join(reportDir, 'axe-violations.json');
  const markdownPath = path.join(reportDir, 'axe-summary.md');

  await fs.writeFile(jsonPath, JSON.stringify(payload, null, 2), 'utf-8');
  await fs.writeFile(markdownPath, buildMarkdownReport(payload), 'utf-8');

  console.log(`[axe] Reports written to ${reportDir}/`);
  console.log(`[axe] - JSON: ${jsonPath}`);
  console.log(`[axe] - Markdown: ${markdownPath}`);
}

test.describe('axe accessibility smoke', () => {
  test.beforeAll(async () => {
    const resolved = await resolveAgentCredentials();
    agentCredentials = resolved.credentials;
    agentCredentialsSource = resolved.source;

    if (agentCredentials) {
      console.log(`[axe] Using ${agentAccountLabel} credentials from ${agentCredentialsSource}`);
    } else if (requireAgentCredentials) {
      skipRunScan = true;
      runSkipReason = `Run scan skipped: ${agentAccountLabel} credentials are required but missing.`;
    } else {
      console.log(
        `[axe] ${agentAccountLabel} credentials not configured; suite may hit CAP gate for run pages.`
      );
    }
  });

  test.afterAll(async () => {
    await writeAxeReport();
  });

  test('axe accessibility scan for ui components theme lab', async ({ page }) => {
    await page.setExtraHTTPHeaders(forwardedProtoHeader);
    if (agentCredentials) {
      await ensureAgentSession(page);
    }

    const themeLabUrl = buildUrl(withSitePrefix('/ui/components/#theme-lab'));
    await page.goto(themeLabUrl, { waitUntil: 'networkidle' });
    await expect(page.locator('#themeContrastTargets')).toBeAttached();

    const entry = await runAxeScan(page, 'ui-components-theme-lab');
    console.log(`[axe] ${entry.pageId}: ${entry.violationCount} violations`);
  });

  test('axe accessibility scan for weppcloud root', async ({ page }) => {
    await page.setExtraHTTPHeaders(forwardedProtoHeader);
    if (agentCredentials) {
      await ensureAgentSession(page);
    }

    const rootUrl = buildUrl(withSitePrefix('/'));
    await page.goto(rootUrl, { waitUntil: 'networkidle' });
    await expect(page.locator('body')).toBeVisible();

    const entry = await runAxeScan(page, 'weppcloud-root');
    console.log(`[axe] ${entry.pageId}: ${entry.violationCount} violations`);
  });

  test('axe accessibility scan for weppcloud interfaces', async ({ page }) => {
    await page.setExtraHTTPHeaders(forwardedProtoHeader);
    if (agentCredentials) {
      await ensureAgentSession(page);
    }

    const interfacesUrl = buildUrl(withSitePrefix('/interfaces/'));
    await page.goto(interfacesUrl, { waitUntil: 'networkidle' });
    await expect(page.locator('body')).toBeVisible();

    const entry = await runAxeScan(page, 'weppcloud-interfaces');
    console.log(`[axe] ${entry.pageId}: ${entry.violationCount} violations`);
  });

  test('axe accessibility scan for runs0 dashboard', async ({ page }) => {
    await page.setExtraHTTPHeaders(forwardedProtoHeader);
    await ensureRunTarget(page);

    if (skipRunScan || !targetRunPath) {
      console.log(`[axe] ${runSkipReason}`);
      test.skip(true, runSkipReason);
    }

    try {
      await page.goto(targetRunPath, { waitUntil: 'networkidle' });
      if ((await page.locator('#cap-gate h1:has-text("Verification required")').count()) > 0) {
        throw new Error(
          `CAP gate still active for runs0. Configure ${agentAccountLabel} credentials via ${agentCredentialsFile}.`
        );
      }

      await expect(page.locator('form#setloc_form .wc-map')).toBeVisible();
      await expect(page.locator('form#landuse_form')).toBeVisible();

      const entry = await runAxeScan(page, 'runs0-dashboard');
      console.log(`[axe] ${entry.pageId}: ${entry.violationCount} violations`);
    } finally {
      await cleanupProvisionedRun(page);
    }
  });
});

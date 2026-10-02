/* Opt-in isolated full-app acceptance; see tests/weppcloud/feature_access_browser_server.py. */
import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('feature groups: real session, database, acknowledgment and removal', async ({ browser, baseURL }) => {
  test.skip(process.env.FEATURE_ACCESS_BROWSER !== '1', 'Requires the isolated feature-access server.');
  const credentials = JSON.parse(fs.readFileSync(path.resolve('../../../docker/secrets/m2-browser.json'), 'utf8'));
  const contexts = [];
  async function signedIn(label) {
    const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1100 } });
    contexts.push(context);
    await context.addCookies([{ name: credentials[label].name, value: credentials[label].value, url: baseURL,
      secure: true, httpOnly: true, sameSite: 'Lax' }]);
    return context.newPage();
  }
  const evidence = process.env.FEATURE_ACCESS_EVIDENCE_DIR;
  async function scan(page, name) {
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
    if (evidence) {
      fs.mkdirSync(evidence, { recursive: true });
      fs.writeFileSync(path.join(evidence, `${name}-axe.json`), JSON.stringify({ violations: results.violations }, null, 2));
      await page.screenshot({ path: path.join(evidence, `${name}.png`), fullPage: true });
    }
    expect(results.violations).toEqual([]);
  }
  try {
    const root = await signedIn('root');
    const user = await signedIn('collaborator');
    await user.goto(`${baseURL}/profile`);
    await expect(user.getByText('No feature group memberships.')).toBeVisible();
    expect((await (await user.request.get(`${baseURL}/test-feature-access-decision`)).json()).allowed).toBe(false);
    await root.goto(`${baseURL}/admin/feature-access`);
    await expect(root.getByRole('heading', { name: 'Feature access', exact: true })).toBeVisible();
    await root.getByLabel('Person (account ID)').focus();
    await root.keyboard.press('Tab');
    await expect(root.getByLabel('Feature group', { exact: true })).toBeFocused();
    await root.getByLabel('Person (account ID)').selectOption(String(credentials.collaborator.id));
    await root.getByLabel('Feature group', { exact: true }).selectOption('ag_fields');
    await root.getByLabel('Reason (required)').fill('Browser acceptance: bounded collaboration');
    await root.getByLabel('Expiration (UTC)').fill('invalid-date');
    await root.getByRole('button', { name: 'Save membership decision' }).press('Enter');
    await expect(root.locator('[data-access-status]')).toContainText('Dates must be UTC');
    await expect(root.locator('[data-access-status]')).toBeFocused();
    await root.getByLabel('Expiration (UTC)').fill('');
    const grant = root.waitForResponse(r => r.url().endsWith('/admin/feature-access/memberships') && r.status() === 200);
    await root.getByRole('button', { name: 'Save membership decision' }).press('Enter');
    expect((await (await grant).json()).result).toMatchObject({ member: true, changed: true });
    await root.getByRole('link', { name: 'Refresh membership and history' }).click();
    await expect(root.getByRole('table', { name: 'Retained membership events (UTC)' })).toContainText('Browser acceptance: bounded collaboration');
    await scan(root, 'admin-granted');
    await user.reload();
    await expect(user.getByText(/actions await acknowledgment/)).toBeVisible();
    expect((await (await user.request.get(`${baseURL}/test-feature-access-decision`)).json()).allowed).toBe(false);
    await scan(user, 'profile-pending');
    await user.getByRole('checkbox', { name: 'I have read and understand the internal access statement.' }).focus();
    await user.keyboard.press('Space');
    const acknowledged = user.waitForResponse(r => r.url().endsWith('/profile/internal-access/acknowledge') && r.status() === 200);
    await user.getByRole('button', { name: 'Accept internal access statement' }).press('Enter');
    expect((await (await acknowledged).json()).result.changed).toBe(true);
    expect((await (await user.request.get(`${baseURL}/test-feature-access-decision`)).json()).allowed).toBe(true);
    await user.getByRole('link', { name: 'Refresh access status' }).click();
    await expect(user.getByText('You have accepted this version.')).toBeVisible();
    await root.getByLabel('Person (account ID)').selectOption(String(credentials.collaborator.id));
    await root.getByLabel('Feature group', { exact: true }).selectOption('ag_fields');
    await root.getByLabel('Decision', { exact: true }).selectOption('remove');
    await expect(root.locator('[data-access-dates]')).toBeHidden();
    await root.getByLabel('Reason (required)').fill('Browser acceptance: collaboration ended');
    const removed = root.waitForResponse(r => r.url().endsWith('/admin/feature-access/memberships') && r.status() === 200);
    await root.getByRole('button', { name: 'Save membership decision' }).press('Enter');
    expect((await (await removed).json()).result).toMatchObject({ member: false, changed: true });
    expect((await (await user.request.get(`${baseURL}/test-feature-access-decision`)).json()).allowed).toBe(false);
    await root.getByRole('link', { name: 'Refresh membership and history' }).click();
    const history = root.getByRole('table', { name: 'Retained membership events (UTC)' });
    await expect(history).toContainText('Browser acceptance: bounded collaboration');
    await expect(history).toContainText('Browser acceptance: collaboration ended');
    await user.reload();
    await expect(user.getByText('No feature group memberships.')).toBeVisible();
    await expect(user.getByText('You have accepted this version.')).toBeVisible();
    if (evidence) {
      fs.writeFileSync(path.join(evidence, 'roundtrip.json'), JSON.stringify({
        fullApp: true, database: 'isolated PostgreSQL schema', sessions: 'real Flask-Security/Redis',
        csrf: 'standard middleware', evaluatorTransitions: [false, false, true, false],
        auditHistoryRetained: true, keyboardSubmission: true, errorFocus: true, axeViolations: 0
      }, null, 2));
    }
  } finally {
    await Promise.all(contexts.map(context => context.close()));
  }
});

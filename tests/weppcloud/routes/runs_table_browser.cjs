const {chromium, expect} = require(process.cwd() + '/node_modules/@playwright/test');
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    const origin = process.argv[2];
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => route.request().url().startsWith(origin) ? route.continue() : route.abort());
    const widths = () => page.locator('#runs_table thead th').evaluateAll(cells => cells.map(cell => cell.getBoundingClientRect().width));
    const ids = () => page.locator('#runs_table_body tr[data-run-row]').evaluateAll(rows => rows.map(row => row.id));
    async function loaded() { await expect(page.locator('#runs_empty_row')).toBeHidden(); }
    async function stable(expected) {
      const actual = await widths();
      expect(actual).toHaveLength(expected.length);
      actual.forEach((width, i) => expect(Math.abs(width - expected[i])).toBeLessThan(1));
    }
    await page.goto(origin + '/runs');
    await loaded();
    const initialWidths = await widths();
    await expect(page.getByRole('link', {name: 'How to keep your project', exact: true})).toHaveCount(1);
    await page.getByRole('link', {name: 'Sort Creation date ascending', exact: true}).click();
    await loaded();
    await stable(initialWidths);
    for (const direction of ['ascending', 'descending', 'ascending', 'descending', 'ascending']) {
      const link = page.getByRole('link', {name: 'Sort Automatic deletion ' + direction, exact: true});
      if (direction === 'descending') { await link.focus(); await page.keyboard.press('Enter'); }
      else await link.click();
      await loaded();
      expect(new URL(page.url()).searchParams.get('sort')).toBe('ttl_deletion_at');
      expect(new URL(page.url()).searchParams.get('direction')).toBe(direction === 'ascending' ? 'asc' : 'desc');
      expect(await ids()).toEqual(direction === 'ascending' ? ['early', 'late', 'unknown', 'disabled'] : ['late', 'early', 'unknown', 'disabled']);
      await stable(initialWidths);
      await expect(page.locator('#runs_table td a').filter({hasText:'How to keep'})).toHaveCount(0);
    }
    const wrapping = await page.locator('#early td').nth(initialWidths.length === 9 ? 2 : 1).evaluate(cell => ({scroll:cell.scrollWidth, width:cell.clientWidth, height:cell.getBoundingClientRect().height}));
    expect(wrapping.scroll).toBeLessThanOrEqual(wrapping.width + 1);
    expect(wrapping.height).toBeGreaterThan(48);
    await page.goto(origin + '/runs?sort=ttl_deletion_at&direction=asc&per_page=2');
    await loaded();
    await stable(initialWidths);
    await page.getByRole('button', {name:'2',exact:true}).click();
    expect(await ids()).toEqual(['unknown', 'disabled']);
    await stable(initialWidths);
    await page.locator('#runs_search_input').fill('no-matching-project');
    await page.getByRole('button', {name:'Search',exact:true}).click();
    await expect(page.locator('#runs_empty_row')).toBeVisible();
    await stable(initialWidths);
    await page.setViewportSize({width:375,height:812});
    expect(await page.locator('.wc-table-wrapper').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true);
    await page.getByRole('link', {name:'Sort Automatic deletion descending',exact:true}).click();
    await loaded();
    expect(await ids()).toEqual(['late', 'early']);
    expect(errors).toEqual([]);
    console.log('Runs table Chromium: PASS');
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exit(1);});

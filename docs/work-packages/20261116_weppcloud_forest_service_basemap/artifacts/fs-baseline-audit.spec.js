import { test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
const paths = ['gl-dashboard.js','gl-dashboard/config.js','gl-dashboard/map/basemap-controller.js','gl-dashboard/map/controller.js'];
test.beforeEach(async ({page}, info) => {
  test.skip(!/Omni full|RAP graph renders after Omni|Cumulative contribution:|Year slider stays/.test(info.title), 'Only isolate the four observed smoke failures');
  for (const path of paths) {
    const body=execFileSync('git',['show',`277d55fba:wepppy/weppcloud/static/js/${path}`],{encoding:'utf8'});
    await page.route(`**/static/js/${path}*`,route=>route.fulfill({body,contentType:'text/javascript'}));
  }
});
await import('./gl-dashboard-state-transitions.spec.js');

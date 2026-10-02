import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(new URL('../../../../wepppy/weppcloud/static-src/package.json', import.meta.url));
const { chromium } = require('@playwright/test');

const base = 'http://127.0.0.1:8080';
const proxyHeaders = { 'X-Forwarded-Proto': 'https' };
const results = {};

function dockerPython(source) {
  const completed = spawnSync('docker', ['exec', '-i', 'weppcloud', 'python', '-'], {
    input: source, encoding: 'utf8', timeout: 30000,
  });
  if (completed.status !== 0) throw new Error(completed.stderr);
  return completed.stdout.trim();
}

const prepared = JSON.parse(dockerPython(`
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from wepppy.weppcloud.app import app, User
from wepppy.weppcloud.utils.rq_engine_token import issue_user_rq_engine_token

private = Path('/wc1/batch/m3-private-acceptance')
public = Path('/wc1/batch/m3-public-acceptance')
query = Path('/wc1/batch/m3-query-acceptance/_base')
for path in (private / '_base', public / '_base', query / '_query_engine'):
    path.mkdir(parents=True, exist_ok=True)
(private / 'acceptance.csv').write_text('value\\nm3-private-canary-7f21\\n')
(public / 'acceptance.csv').write_text('value\\nm3-public-canary-92ae\\n')
(public / '_base' / 'PUBLIC').touch()
private_marker = private / '_base' / 'PUBLIC'
if private_marker.exists():
    private_marker.unlink()
pq.write_table(pa.table({'id': [1]}), query / 'declared.parquet')
external = Path('/wc1/batch/m3-query-private-canary.parquet')
pq.write_table(pa.table({'value': ['m3-query-private-canary-e117']}), external)
source = query / 'declared.parquet'
(query / '_query_engine' / 'catalog.json').write_text(json.dumps({
    'root': str(query),
    'files': [{'path': 'declared.parquet', 'extension': '.parquet',
               'size_bytes': source.stat().st_size, 'modified': '2026-10-02T00:00:00Z'}],
}))
with app.app_context():
    user = User.query.filter_by(email='rogerlew@gmail.com').one()
    print(json.dumps({'userId': user.id, 'token': issue_user_rq_engine_token(user)}))
`));
const token = prepared.token;

function membership(operation) {
  const source = `
from wepppy.weppcloud.app import app
from wepppy.weppcloud.utils import feature_access_web
with app.app_context():
    result = feature_access_web.access_store().change_membership_status(
        actor_id=${prepared.userId}, user_id=${prepared.userId}, group_key='batch_runner', operation='${operation}',
        reason='M3 production-equivalent private-resource acceptance ${operation}',
        features=feature_access_web.load_feature_registry())
    print(result)
`;
  dockerPython(source);
}

async function grid(context, dataId) {
  return context.request.get(`${base}/weppcloud/dtale/data/${dataId}?ids=${encodeURIComponent(JSON.stringify(['0-1']))}`);
}

async function query(context, computedColumns = undefined) {
  const payload = { datasets: ['declared.parquet'], limit: 1 };
  if (computedColumns) payload.computed_columns = computedColumns;
  return context.request.post(
    `${base}/query-engine/runs/batch;;m3-query-acceptance;;_base/query`,
    { data: payload, headers: { Origin: 'https://127.0.0.1' } },
  );
}

let browser;
let removed = false;
try {
  browser = await chromium.launch({ headless: true });
  const anonymous = await browser.newContext({ extraHTTPHeaders: proxyHeaders });
  const deniedLaunch = await anonymous.request.get(`${base}/weppcloud/batch/m3-private-acceptance/dtale/acceptance.csv`, { maxRedirects: 0 });
  results.privateAnonymousLaunch = deniedLaunch.status();

  const member = await browser.newContext({ extraHTTPHeaders: { ...proxyHeaders, Authorization: `Bearer ${token}` } });
  const page = await member.newPage();
  const loaded = await page.goto(`${base}/weppcloud/batch/m3-private-acceptance/dtale/acceptance.csv`, { waitUntil: 'domcontentloaded' });
  if (!loaded || loaded.status() !== 200) throw new Error(`private browser launch status ${loaded?.status()}`);
  const privateMatch = page.url().match(/\/main\/([^/?#]+)/);
  if (!privateMatch) throw new Error(`private data id missing from ${page.url()}`);
  const privateId = privateMatch[1];
  const memberGrid = await grid(member, privateId);
  results.privateMemberGrid = memberGrid.status();
  results.privateMemberCanary = (await memberGrid.text()).includes('m3-private-canary-7f21');
  const anonymousGrid = await grid(anonymous, privateId);
  results.privateAnonymousGrid = anonymousGrid.status();

  const declaredQuery = await query(member);
  results.declaredQuery = declaredQuery.status();
  results.declaredQueryValue = (await declaredQuery.json()).records?.[0]?.id;
  const externalQuery = await query(member, [{
    alias: 'leak',
    sql: "(SELECT value FROM read_parquet('/wc1/batch/m3-query-private-canary.parquet'))",
  }]);
  const externalQueryText = await externalQuery.text();
  results.externalQuery = externalQuery.status();
  results.externalQueryCanary = externalQueryText.includes('m3-query-private-canary-e117');

  membership('remove');
  removed = true;
  const removedGrid = await grid(member, privateId);
  results.privateRemovedMemberGrid = removedGrid.status();
  results.removedMemberQuery = (await query(member)).status();
  membership('add');
  removed = false;
  const restoredGrid = await grid(member, privateId);
  results.privateRestoredMemberGrid = restoredGrid.status();
  results.privateRestoredCanary = (await restoredGrid.text()).includes('m3-private-canary-7f21');
  results.restoredMemberQuery = (await query(member)).status();

  const publicPage = await anonymous.newPage();
  const publicLoaded = await publicPage.goto(`${base}/weppcloud/batch/m3-public-acceptance/dtale/acceptance.csv`, { waitUntil: 'domcontentloaded' });
  if (!publicLoaded || publicLoaded.status() !== 200) throw new Error(`public browser launch status ${publicLoaded?.status()}`);
  const publicMatch = publicPage.url().match(/\/main\/([^/?#]+)/);
  if (!publicMatch) throw new Error(`public data id missing from ${publicPage.url()}`);
  const publicGrid = await grid(anonymous, publicMatch[1]);
  results.publicAnonymousGrid = publicGrid.status();
  results.publicAnonymousCanary = (await publicGrid.text()).includes('m3-public-canary-92ae');

  const expected = {
    privateAnonymousLaunch: 401,
    privateMemberGrid: 200,
    privateMemberCanary: true,
    privateAnonymousGrid: 403,
    declaredQuery: 200,
    declaredQueryValue: 1,
    externalQuery: 500,
    externalQueryCanary: false,
    privateRemovedMemberGrid: 403,
    removedMemberQuery: 403,
    privateRestoredMemberGrid: 200,
    privateRestoredCanary: true,
    restoredMemberQuery: 200,
    publicAnonymousGrid: 200,
    publicAnonymousCanary: true,
  };
  for (const [key, value] of Object.entries(expected)) {
    if (results[key] !== value) throw new Error(`${key}: expected ${value}, observed ${results[key]}`);
  }
  console.log(JSON.stringify(results, null, 2));
  await anonymous.close();
  await member.close();
} finally {
  if (removed) membership('add');
  if (browser) await browser.close();
  dockerPython(`
from pathlib import Path
import shutil
for path in (
    Path('/wc1/batch/m3-private-acceptance'),
    Path('/wc1/batch/m3-public-acceptance'),
    Path('/wc1/batch/m3-query-acceptance'),
):
    if path.exists():
        shutil.rmtree(path)
external = Path('/wc1/batch/m3-query-private-canary.parquet')
if external.exists():
    external.unlink()
`);
}

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

function api(fetch = () => { throw Error('Unexpected fetch'); }) {
  const window = {};
  const document = { currentScript: { src: 'https://app.test/weppcloud/static/js/forest-service-basemap.js' } };
  vm.runInNewContext(readFileSync(new URL('../../../static/js/forest-service-basemap.js', import.meta.url), 'utf8'),
    { window, document, URL, fetch });
  return window.WCForestBasemap;
}
const root = 'https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer/';
test('resource boundary rejects foreign, credentialed, and traversal URLs before fetch', () => {
  const a = api();
  assert.equal(a.validateResource(root + 'tile/3/2/1.pbf'), root + 'tile/3/2/1.pbf');
  for (const url of ['https://app.test/tasks/delete', 'http://tiles.arcgis.com/a', root + '../other', root + 'tile/a?token=secret', root.replace('https://', 'https://user:pass@'), 'data:text/html,x']) {
    assert.throws(() => a.validateResource(url));
  }
});
test('style resolution preserves official layers but removes remote attribution and TileJSON requests', () => {
  const a = api();
  const style = a.prepareStyle({version: 8, glyphs:'../fonts/{fontstack}/{range}.pbf', sprite:'../sprites/sprite',
    sources:{esri:{type:'vector',url:'../../',minzoom:2,maxzoom:19,attribution:'<img onerror=evil()>'}},layers:[{id:'water',type:'fill',source:'esri'}]});
  assert.equal(style.sources.esri.attribution, '');
  assert.equal(style.sources.esri.url, undefined);
  assert.equal(style.sources.esri.tiles[0], root + 'tile/{z}/{y}/{x}.pbf');
  assert.equal(style.layers[0].id, 'water');
  assert.equal(style.glyphs, root + 'resources/fonts/{fontstack}/{range}.pbf');
  assert.throws(() => a.prepareStyle({version:8,sources:{bad:{type:'geojson',data:'https://app.test/private'}},layers:[]}));
});
test('protocol fetch omits credentials and referrer and rejects redirects', async () => {
  let options;
  const a = api(async (url, opts) => { options=opts; return {ok:true, arrayBuffer:async()=>new ArrayBuffer(2)}; });
  await a.fetchResource(root+'tile/3/2/1.pbf', {});
  assert.equal(options.credentials,'omit');
  assert.equal(options.referrerPolicy,'no-referrer');
  assert.equal(options.redirect,'error');
});

test('shared raster factory still works for the OSM-only combined viewer', async () => {
  const source = readFileSync(new URL('../../../static/js/gl-dashboard/map/basemap-controller.js', import.meta.url), 'utf8');
  const {createBasemapController} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
  const controller = createBasemapController({deck:{TileLayer:class {constructor(props){this.props=props;}}},
    basemapDefs:{osm:{template:'https://example.test/{z}/{x}/{y}',getUrl:()=>''}},getState:()=>({}),setValue:()=>{}});
  const layer=controller.createBaseLayer('osm');
  assert.equal(layer.props.data,'https://example.test/{z}/{x}/{y}');
});

test('invalid renderer and missing CSS become visible failures and allow retry', async () => {
  const {JSDOM} = await import('jsdom');
  const dom = new JSDOM('<div id="map"></div>', {url:'https://app.test/'});
  Object.defineProperty(dom.window.document,'currentScript',{value:{src:'https://app.test/static/js/forest-service-basemap.js'}});
  vm.runInNewContext(readFileSync(new URL('../../../static/js/forest-service-basemap.js', import.meta.url), 'utf8'), {
    window:dom.window,document:dom.window.document,URL,AbortController,
    fetch:async()=>({ok:true,json:async()=>({version:8,sources:{},layers:[]})})
  });
  const adapter=dom.window.WCForestBasemap.create({target:dom.window.document.getElementById('map')});
  let selection=adapter.select('forestService');
  dom.window.document.querySelector('link').onload();
  dom.window.document.querySelector('script').onload();
  await selection;
  assert.match(dom.window.document.querySelector('[role=status]').textContent,/unavailable/);
  assert.equal(dom.window.document.querySelectorAll('script,link').length,0);
  selection=adapter.select('forestService');
  dom.window.document.querySelector('link').onerror();
  await selection;
  assert.match(dom.window.document.querySelector('[role=status]').textContent,/unavailable/);
  await adapter.select('googleTerrain');
  assert.match(dom.window.document.querySelector('.wc-basemap-credit').textContent,/Google/);
  adapter.dispose();dom.window.close();
});

test('inherited provider names fall back initially and do not change interactive state', async () => {
  const source=readFileSync(new URL('../../../static/js/gl-dashboard/map/basemap-controller.js',import.meta.url),'utf8');
  const {createBasemapController}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  let mutations=0;
  const controller=createBasemapController({deck:{TileLayer:class{constructor(props){this.props=props;}}},
    basemapDefs:{googleTerrain:{template:'terrain'}},getState:()=>({}),setValue:()=>mutations++});
  for(const key of ['constructor','toString','__proto__','unknown']) {
    assert.equal(controller.createBaseLayer(key).props.data,'terrain');
    controller.setBasemap(key);
  }
  assert.equal(mutations,0);
});

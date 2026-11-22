import { createBasemapDefs } from './gl-dashboard/config.js';
import { createMapController } from './gl-dashboard/map/controller.js';
import { createBasemapController } from './gl-dashboard/map/basemap-controller.js';

const INITIAL_VIEW = { longitude: -98.5795, latitude: 39.8283, zoom: 3.5, minZoom: 1, maxZoom: 14, pitch: 35, bearing: 0 };
const PAN = { ArrowLeft: [-80, 0], ArrowRight: [80, 0], ArrowUp: [0, -80], ArrowDown: [0, 80] };

function tooltip({ object }) {
  if (!object) return null;
  const config = object.config === '' ? null : object.config;
  return [
    object.name || 'Unnamed run',
    `Run ID: ${object.run_id}`,
    `Location: ${object.latitude}, ${object.longitude}`,
    `Config: ${config ?? 'Unknown'}`,
    `Soil burn severity data: ${object.severity == null ? 'Unknown' : object.severity ? 'Yes' : 'No'}`,
    `Accesses: ${object.access_count ?? 'Unknown'}`,
    `Last accessed: ${object.last_accessed || 'Unknown'}`,
  ].join('\n');
}

function initAtlas(figure, deck) {
  const region = figure.querySelector('.wc-landing__atlas-map');
  const target = region.querySelector('.wc-landing__atlas-canvas');
  const status = figure.querySelector('.wc-landing__atlas-status');
  const controls = figure.querySelector('.wc-landing__atlas-controls');
  const keyboard = figure.querySelector('#atlas-keyboard');
  const inspection = figure.querySelector('.wc-landing__atlas-inspection');
  const rows = JSON.parse(figure.querySelector('[data-atlas-rows]').textContent);
  const initialView = { ...INITIAL_VIEW, zoom: innerWidth < 560 ? 2.5 : INITIAL_VIEW.zoom };
  const position = row => [row.longitude === 180 ? -180 : row.longitude, row.latitude];
  const { basemapDefs: { googleTerrain } } = createBasemapDefs();
  const basemaps = createBasemapController({
    deck,
    basemapDefs: {
      googleTerrain: {
        ...googleTerrain,
        getUrl(x, y, z) {
          if (!Number.isInteger(z) || z < 0 || z > 19 ||
              ![x, y].every(index => Number.isInteger(index) && index >= 0 && index < 2 ** z)) {
            throw new RangeError('Invalid Run Atlas tile coordinates.');
          }
          return googleTerrain.getUrl(x, y, z);
        },
      },
    },
  });
  const centroids = new deck.ScatterplotLayer({
    id: 'run-centroids',
    data: rows,
    pickable: true,
    radiusUnits: 'pixels',
    radiusMinPixels: 4,
    radiusMaxPixels: 60,
    getPosition: position,
    getRadius: row => Math.max(6, row.access_count ?? 1),
    getFillColor: row => row.severity ? [142, 73, 234, 200] : [2, 132, 199, 200],
    getLineColor: [255, 255, 255, 220],
    lineWidthUnits: 'pixels',
    getLineWidth: row => row.severity ? 3 : 1,
    stroked: true,
  });

  let camera = initialView;
  let inspected = -1;
  const baseLayer = basemaps.createBaseLayer('googleTerrain').clone({
    id: 'atlas-google-terrain',
    onViewportLoad(tiles) {
      if (tiles.length && tiles.every(tile => tile.content != null)) status.textContent = '';
    },
    onTileError(error) {
      status.textContent = 'Some map tiles are unavailable.';
      console.error(error);
    },
  });

  function layers() {
    return [baseLayer, centroids, new deck.TextLayer({
      id: 'run-labels',
      data: rows,
      visible: camera.zoom >= 5,
      getPosition: position,
      getText: row => row.name || row.run_id,
      getSize: 12,
      getColor: [30, 41, 59],
      fontSettings: { sdf: true },
      outlineWidth: 1,
      outlineColor: [255, 255, 255],
      getTextAnchor: 'start',
      getPixelOffset: [9, 0],
    })];
  }

  function updateCamera(next) {
    const labelsChanged = (camera.zoom >= 5) !== (next.zoom >= 5);
    camera = next;
    map.setViewState(camera);
    if (labelsChanged) map.applyLayers(layers());
  }

  status.textContent = 'Loading Run Atlas map…';
  region.hidden = false;
  const map = createMapController({
    deck, target, initialViewState: initialView,
    controllerOptions: { scrollZoom: false, dragRotate: false, touchRotate: false, keyboard: false },
    layers: layers(),
    getTooltip: tooltip,
    onViewStateChange: ({ viewState }) => updateCamera(viewState),
    onAfterRender() {
      const canvas = target.querySelector('canvas');
      if (canvas && !region.hidden && region.tabIndex !== 0) {
        canvas.tabIndex = -1;
        region.tabIndex = 0;
        controls.hidden = false;
        keyboard.hidden = false;
      }
    },
    onError(error, layer) {
      if (!layer) {
        region.hidden = true;
        controls.hidden = true;
        keyboard.hidden = true;
      }
      status.textContent = 'Interactive map unavailable.';
      console.error(error);
    },
  });
  map.setViewState(camera);

  region.addEventListener('keydown', event => {
    if (event.altKey || event.metaKey || event.ctrlKey) return;
    if (event.key === 'Enter') {
      event.preventDefault();
      if (!rows.length) {
        inspection.textContent = 'No project locations are plotted.';
        return;
      }
      if (inspected === -1) {
        inspected = event.shiftKey ? rows.length - 1 : 0;
      } else {
        inspected = (inspected + (event.shiftKey ? -1 : 1) + rows.length) % rows.length;
      }
      inspection.textContent = `Project ${inspected + 1} of ${rows.length}.
${tooltip({ object: rows[inspected] })}`;
      return;
    }
    if (!Object.hasOwn(PAN, event.key)) return;
    const [view] = map.deckgl.getViewports();
    if (!view) return;
    const [x, y] = PAN[event.key];
    const [longitude, latitude] = view.unproject([view.width / 2 + x, view.height / 2 + y]);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return;
    event.preventDefault();
    updateCamera({ ...camera, longitude, latitude });
  });

  for (const button of controls.querySelectorAll('[data-atlas-zoom]')) {
    button.addEventListener('click', () => {
      const zoom = Math.min(INITIAL_VIEW.maxZoom, Math.max(INITIAL_VIEW.minZoom, camera.zoom + Number(button.dataset.atlasZoom)));
      updateCamera({ ...camera, zoom });
    });
  }
  controls.querySelector('[data-atlas-reset]').addEventListener('click', () => updateCamera(initialView));

}

const atlas = document.querySelector('[data-run-atlas]');
if (atlas && globalThis.deck?.Deck) {
  try {
    initAtlas(atlas, globalThis.deck);
  } catch (error) {
    atlas.querySelector('.wc-landing__atlas-map').hidden = true;
    atlas.querySelector('.wc-landing__atlas-status').textContent =
      'Interactive map unavailable.';
    console.error(error);
  }
}

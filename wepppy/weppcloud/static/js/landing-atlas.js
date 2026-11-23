import { createMapController } from './gl-dashboard/map/controller.js';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json';
const CARTO_ASSETS = /^\/v\/\d{8}-\d{2}\/(?:vectortiles\/carto\.streets\/v2\/\d+\/\d+\/\d+\.mvt|fonts\/[^/]+\/\d+-\d+\.pbf|gl\/positron-gl-style\/sprite(?:@2x)?\.(?:json|png))$/;
const INITIAL_VIEW = { longitude: -98.5795, latitude: 39.8283, zoom: 3.5, minZoom: 1, maxZoom: 14, pitch: 0, bearing: 0 };
const PAN = { ArrowLeft: [-80, 0], ArrowRight: [80, 0], ArrowUp: [0, -80], ArrowDown: [0, 80] };

function basemapRequest(value) {
  const url = new URL(value);
  if (url.href !== MAP_STYLE && !(
    url.origin === 'https://tiles.basemaps.cartocdn.com' &&
    !url.username && !url.password && !url.search && !url.hash && CARTO_ASSETS.test(url.pathname)
  )) {
    throw new Error('Unexpected Run Atlas basemap resource.');
  }
  return { url: url.href, credentials: 'omit', referrerPolicy: 'no-referrer' };
}

function tooltip({ object }) {
  if (!object) return null;
  return [
    `Location: ${object.coordinates[1]}, ${object.coordinates[0]}`,
    `Config: ${object.config === '' ? 'Unknown' : object.config ?? 'Unknown'}`,
    `Soil burn severity data: ${object.has_sbs == null ? 'Unknown' : object.has_sbs ? 'Yes' : 'No'}`,
    `Hillslopes: ${object.hillslopes ?? 'Unknown'}`,
  ].join('\n');
}

function initAtlas(figure, deck, maplibre) {
  const region = figure.querySelector('.wc-landing__atlas-map');
  const target = region.querySelector('.wc-landing__atlas-canvas');
  const status = figure.querySelector('.wc-landing__atlas-status');
  const controls = figure.querySelector('.wc-landing__atlas-controls');
  const keyboard = figure.querySelector('#atlas-keyboard');
  const rows = JSON.parse(figure.querySelector('[data-atlas-rows]').textContent);
  region.hidden = false;
  function openingView() {
    const opening = new deck.WebMercatorViewport({
      width: region.clientWidth, height: region.clientHeight,
    }).fitBounds([[-125, 25], [-66, 50]], { padding: 16 });
    return { ...INITIAL_VIEW, longitude: opening.longitude, latitude: opening.latitude, zoom: opening.zoom };
  }
  const initialView = openingView();
  const position = row => [row.coordinates[0] === 180 ? -180 : row.coordinates[0], row.coordinates[1]];

  const centroids = new deck.ScatterplotLayer({
    id: 'run-centroids',
    data: rows,
    pickable: true,
    radiusUnits: 'pixels',
    radiusMinPixels: 4,
    radiusMaxPixels: 26,
    getPosition: position,
    getRadius: row => Math.sqrt(row.hillslopes ?? 0),
    getFillColor: row => row.has_sbs ? [173, 62, 10, 220] : [2, 132, 199, 200],
    getLineColor: [255, 255, 255, 220],
    lineWidthUnits: 'pixels',
    getLineWidth: row => row.has_sbs ? 3 : 1,
    stroked: true,
  });

  let camera = initialView;
  let atOpeningView = true;

  status.textContent = 'Loading Run Atlas map…';
  const basemap = new maplibre.Map({
    container: region.querySelector('.wc-landing__atlas-basemap'),
    style: MAP_STYLE,
    center: [camera.longitude, camera.latitude],
    zoom: camera.zoom,
    pitch: camera.pitch,
    bearing: camera.bearing,
    interactive: false,
    attributionControl: false,
    renderWorldCopies: false,
    transformRequest: basemapRequest,
  });
  basemap.getCanvas().tabIndex = -1;
  let basemapFailed = false;
  let basemapRemoved = false;
  const removeBasemap = () => {
    if (!basemapRemoved) {
      basemapRemoved = true;
      basemap.remove();
    }
  };
  basemap.once('style.load', () => {
    basemap.on('movestart', () => { basemapFailed = false; });
  });
  basemap.on('error', ({ error }) => {
    basemapFailed = true;
    status.textContent = 'Some Run Atlas basemap resources are unavailable.';
    console.error(error);
  });
  basemap.on('idle', () => {
    if (!basemapFailed) status.textContent = '';
  });

  function updateCamera(next, opening = false) {
    atOpeningView = opening;
    camera = next;
    map.setViewState(camera);
    basemap.jumpTo({
      center: [camera.longitude, camera.latitude],
      zoom: camera.zoom,
      pitch: camera.pitch,
      bearing: camera.bearing,
    });
  }

  const touchOnly = matchMedia('(pointer: coarse) and (not (any-pointer: fine))').matches;
  const deckOptions = {
    deck, target, initialViewState: initialView,
    touchAction: touchOnly ? 'pan-y' : 'none',
    controllerOptions: { dragPan: !touchOnly, scrollZoom: true, dragRotate: false, touchRotate: false, keyboard: false },
    layers: [centroids],
    getTooltip: tooltip,
    onViewStateChange: ({ viewState, interactionState }) => {
      const interacting = interactionState?.isDragging || interactionState?.isZooming ||
        interactionState?.isPanning || interactionState?.inTransition;
      updateCamera(viewState, atOpeningView && !interacting);
    },
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
        removeBasemap();
        region.hidden = true;
        controls.hidden = true;
        keyboard.hidden = true;
      }
      status.textContent = 'Interactive map unavailable.';
      console.error(error);
    },
  };
  let map;
  try {
    map = createMapController(deckOptions);
    map.setViewState(camera);
  } catch (error) {
    removeBasemap();
    throw error;
  }

  // Let ordinary wheel events scroll the page before Deck can consume them.
  region.addEventListener('wheel', event => {
    if (!event.ctrlKey) event.stopPropagation();
  }, { capture: true, passive: true });

  region.addEventListener('keydown', event => {
    if (!Object.hasOwn(PAN, event.key) || event.altKey || event.metaKey || event.ctrlKey) return;
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
  controls.querySelector('[data-atlas-reset]').addEventListener('click', () => updateCamera(openingView(), true));
  new ResizeObserver(() => {
    requestAnimationFrame(() => {
      if (atOpeningView && !region.hidden) updateCamera(openingView(), true);
    });
  }).observe(region);
}

const atlas = document.querySelector('[data-run-atlas]');
if (atlas && globalThis.deck?.Deck && globalThis.maplibregl?.Map) {
  try {
    initAtlas(atlas, globalThis.deck, globalThis.maplibregl);
  } catch (error) {
    atlas.querySelector('.wc-landing__atlas-map').hidden = true;
    atlas.querySelector('.wc-landing__atlas-status').textContent = 'Interactive map unavailable.';
    console.error(error);
  }
}

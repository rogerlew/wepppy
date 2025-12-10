(function () {
  const ctx = window.GL_DASHBOARD_CONTEXT || {};
  const target = document.getElementById('gl-dashboard-map');

  if (!target) {
    return;
  }

  if (typeof deck === 'undefined' || !deck.Deck) {
    target.innerHTML = '<div style="padding:1rem;color:#e11d48;">deck.gl script failed to load.</div>';
    return;
  }

  const tileTemplate =
    ctx.tileUrl || 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png';

  const initialViewState = {
    longitude: ctx.longitude || -114.5,
    latitude: ctx.latitude || 43.8,
    zoom: ctx.zoom || 5,
    minZoom: 2,
    maxZoom: 17,
    pitch: 0,
    bearing: 0,
  };

  const baseLayer = new deck.TileLayer({
    id: 'gl-dashboard-base-tiles',
    data: tileTemplate,
    minZoom: 0,
    maxZoom: 19,
    tileSize: 256,
    maxRequests: 8,
    getTileData: async ({ index, signal }) => {
      const { x, y, z } = index || {};
      if (![x, y, z].every(Number.isFinite)) {
        throw new Error(`Tile coords missing: x=${x} y=${y} z=${z}`);
      }
      const url = tileTemplate
        .replace('{x}', String(x))
        .replace('{y}', String(y))
        .replace('{z}', String(z));
      const response = await fetch(url, { signal, mode: 'cors' });
      if (!response.ok) {
        throw new Error(`Tile fetch failed ${response.status}: ${url}`);
      }
      const blob = await response.blob();
      return await createImageBitmap(blob);
    },
    onTileError: (err) => {
      // eslint-disable-next-line no-console
      console.error('gl-dashboard tile error', err);
    },
    renderSubLayers: (props) => {
      const tile = props.tile;
      const data = props.data;

      if (!tile || !data || !tile.bbox) {
        return null;
      }

      const { west, south, east, north } = tile.bbox;
      const bounds = [west, south, east, north];
      if (bounds.some((v) => !Number.isFinite(v))) {
        return null;
      }

      return new deck.BitmapLayer(props, {
        id: `${props.id}-${tile.id}`,
        data: null,
        image: data,
        bounds,
        pickable: false,
        opacity: 0.95,
      });
    },
  });

  const layerDefs = [
    {
      key: 'landuse',
      label: 'Landuse (nlcd.tif)',
      // NoDbBase.lc_fn
      paths: ['landuse/nlcd.tif'],
    },
    {
      key: 'soils',
      label: 'Soils (ssurgo.tif)',
      // NoDbBase.ssurgo_fn
      paths: ['soils/ssurgo.tif'],
    },
  ];

  const detectedLayers = [];
  const layerListEl = document.getElementById('gl-layer-list');
  const layerEmptyEl = document.getElementById('gl-layer-empty');

  async function detectSbsLayer() {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/baer_wgs_map`;
    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        return;
      }
      const payload = await resp.json();
      if (!payload || payload.Success !== true || !payload.Content) {
        return;
      }
      let bounds = payload.Content.bounds;
      const imgurl = payload.Content.imgurl;
      if (!bounds || !imgurl) {
        return;
      }
      // Normalize bounds: API returns [[lat1, lon1], [lat2, lon2]]
      if (Array.isArray(bounds) && bounds.length === 2 && Array.isArray(bounds[0]) && Array.isArray(bounds[1])) {
        const [lat1, lon1] = bounds[0];
        const [lat2, lon2] = bounds[1];
        bounds = [lon1, lat1, lon2, lat2];
      }
      if (!Array.isArray(bounds) || bounds.length !== 4 || bounds.some((v) => !Number.isFinite(v))) {
        return;
      }
      detectedLayers.push({
        key: 'sbs',
        label: 'SBS Map',
        path: 'query/baer_wgs_map',
        bounds,
        imageUrl: imgurl,
        visible: true,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load SBS map', err);
    }
  }

  function updateLayerList() {
    if (!layerListEl) return;
    layerListEl.innerHTML = '';
    if (!detectedLayers.length) {
      if (layerEmptyEl) {
        layerEmptyEl.hidden = false;
      }
      return;
    }
    if (layerEmptyEl) {
      layerEmptyEl.hidden = true;
    }
    detectedLayers.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = layer.visible;
      input.id = `layer-${layer.key}`;
      input.addEventListener('change', () => {
        layer.visible = input.checked;
        applyLayers();
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      label.textContent = layer.label;
      li.appendChild(input);
      li.appendChild(label);
      layerListEl.appendChild(li);
    });
  }

  function applyLayers() {
    const activeRasterLayers = detectedLayers
      .filter((layer) => layer.visible)
      .map((layer) => {
        if (layer.imageUrl) {
          const cacheBusted = `${layer.imageUrl}${layer.imageUrl.includes('?') ? '&' : '?'}t=${Date.now()}`;
          return new deck.BitmapLayer({
            id: `raster-${layer.key}`,
            image: cacheBusted,
            bounds: layer.bounds,
            pickable: false,
            opacity: 0.8,
          });
        }
        if (layer.canvas) {
          return new deck.BitmapLayer({
            id: `raster-${layer.key}`,
            image: layer.canvas,
            bounds: layer.bounds,
            pickable: false,
            opacity: 0.8,
          });
        }
        return null;
      })
      .filter(Boolean);
    deckgl.setProps({
      layers: [baseLayer, ...activeRasterLayers],
    });
  }

  function computeBoundsFromGdal(info) {
    const cc = info && info.cornerCoordinates;
    if (!cc) return null;
    const ll = cc.lowerLeft || cc.lowerleft || cc.LowerLeft;
    const ur = cc.upperRight || cc.upperright || cc.UpperRight;
    if (!ll || !ur) return null;
    const west = Math.min(ll[0], ur[0]);
    const east = Math.max(ll[0], ur[0]);
    const south = Math.min(ll[1], ur[1]);
    const north = Math.max(ll[1], ur[1]);
    if (![west, south, east, north].every(Number.isFinite)) return null;
    return [west, south, east, north];
  }

  function zoomToBounds(bounds) {
    if (!bounds || bounds.length !== 4) return;
    const [west, south, east, north] = bounds;
    const cx = (west + east) / 2;
    const cy = (south + north) / 2;
    const span = Math.max(east - west, north - south);
    const zoom = Math.max(2, Math.min(14, Math.log2(360 / (span || 0.001)) - 1));
    deckgl.setProps({
      viewState: {
        longitude: cx,
        latitude: cy,
        zoom,
        bearing: 0,
        pitch: 0,
      },
    });
  }

  async function fetchGdalInfo(path) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/gdalinfo/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) return null;
    return resp.json();
  }

  async function fetchRasterCanvas(path) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/download/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Raster fetch failed: ${resp.status}`);
    }
    if (typeof GeoTIFF === 'undefined' || typeof GeoTIFF.fromArrayBuffer !== 'function') {
      throw new Error('GeoTIFF library not available');
    }
    const array = await resp.arrayBuffer();
    const tiff = await GeoTIFF.fromArrayBuffer(array);
    const image = await tiff.getImage();
    const width = image.getWidth();
    const height = image.getHeight();
    const data = await image.readRasters({ interleave: true, samples: [0] });
    const values = data;
    let min = Infinity;
    let max = -Infinity;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v)) {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
      min = 0;
      max = 255;
    }
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx2d = canvas.getContext('2d');
    const imgData = ctx2d.createImageData(width, height);
    const scale = 255 / (max - min || 1);
    for (let i = 0, j = 0; i < values.length; i++, j += 4) {
      const v = values[i];
      const scaled = Math.max(0, Math.min(255, Math.round((v - min) * scale)));
      imgData.data[j] = scaled;
      imgData.data[j + 1] = scaled;
      imgData.data[j + 2] = scaled;
      imgData.data[j + 3] = 200;
    }
    ctx2d.putImageData(imgData, 0, 0);
    return canvas;
  }

  async function detectLayers() {
    await detectSbsLayer();
    for (const def of layerDefs) {
      let found = null;
      for (const path of def.paths) {
        try {
          const info = await fetchGdalInfo(path);
          if (!info) continue;
          const bounds = computeBoundsFromGdal(info);
          if (!bounds) continue;
          const canvas = await fetchRasterCanvas(path);
          const layer = new deck.BitmapLayer({
            id: `raster-${def.key}-${path}`,
            image: canvas,
            bounds,
            pickable: false,
            opacity: 0.8,
          });
          found = {
            key: def.key,
            label: def.label,
            path,
            bounds,
            bitmapLayer: layer,
            visible: true,
          };
          break;
        } catch (err) {
          // eslint-disable-next-line no-console
          console.warn(`gl-dashboard: failed to load ${def.label} at ${path}`, err);
        }
      }
      if (found) {
        detectedLayers.push(found);
      }
    }
    updateLayerList();
    applyLayers();
    if (detectedLayers.length) {
      zoomToBounds(detectedLayers[0].bounds);
    }
  }

  const deckgl = new deck.Deck({
    parent: target,
    controller: true,
    initialViewState,
    layers: [baseLayer],
    getTooltip: (info) => {
      if (info && info.tile) {
        return `Tile z${info.tile.z}`;
      }
      return null;
    },
    onError: (error) => {
      // Keep the stub resilient; surface issues in console.
      // eslint-disable-next-line no-console
      console.error('gl-dashboard render error', error);
    },
  });

  // Expose for debugging.
  window.glDashboardDeck = deckgl;

  detectLayers().catch((err) => {
    // eslint-disable-next-line no-console
    console.error('gl-dashboard: layer detection failed', err);
  });
})();

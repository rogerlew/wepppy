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

  const controllerOptions = {
    dragPan: true,
    dragRotate: false,
    scrollZoom: true,
    touchZoom: true,
    touchRotate: false,
    doubleClickZoom: true,
    keyboard: true,
  };
  let currentViewState = initialViewState;

  function setViewState(viewState) {
    currentViewState = viewState;
    deckgl.setProps({ viewState: currentViewState });
  }

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
  const landuseLayers = [];
  let landuseSummary = null;
  let subcatchmentsGeoJson = null;
  const layerListEl = document.getElementById('gl-layer-list');
  const layerEmptyEl = document.getElementById('gl-layer-empty');
  let geoTiffLoader = null;
  const NLCD_COLORMAP = {
    11: '#5475A8', // Open water
    12: '#ffffff', // Perennial ice/snow
    21: '#e6d6d6', // Developed, open space
    22: '#ccb1b1', // Developed, low intensity
    23: '#ff0000', // Developed, medium intensity
    24: '#b50000', // Developed, high intensity
    31: '#d2cdc0', // Barren land
    41: '#85c77e', // Deciduous forest
    42: '#38814e', // Evergreen forest
    43: '#d4e7b0', // Mixed forest
    51: '#af963c', // Dwarf scrub
    52: '#dcca8f', // Shrub/scrub
    71: '#fde9aa', // Grassland/herbaceous
    72: '#d1d182', // Sedge/herbaceous
    73: '#a3cc51', // Lichens
    74: '#82ba9e', // Moss
    81: '#fbf65d', // Pasture/hay
    82: '#ca9146', // Cultivated crops
    90: '#c8e6f8', // Woody wetlands
    95: '#64b3d5', // Emergent herbaceous wetlands
  };
  const HEX_RGB_RE = /^#?([0-9a-f]{6})$/i;
  const soilColorCache = new Map();
  const viridisScale =
    typeof createColormap === 'function'
      ? createColormap({ colormap: 'viridis', nshades: 256, format: 'rgba' })
      : null;
  const RGBA_RE = /^rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*(?:,\s*([0-9.]+)\s*)?\)$/i;

  function hslToHex(h, s, l) {
    const sat = s / 100;
    const light = l / 100;
    const a = sat * Math.min(light, 1 - light);
    const f = (n) => {
      const k = (n + h / 30) % 12;
      const color = light - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color)
        .toString(16)
        .padStart(2, '0');
    };
    return `#${f(0)}${f(8)}${f(4)}`;
  }

  function soilColorForValue(value) {
    if (!Number.isFinite(value)) return null;
    if (soilColorCache.has(value)) {
      return soilColorCache.get(value);
    }
    const v = Math.abs(Math.trunc(value));
    const hue = ((v * 2654435761) >>> 0) % 360; // Knuth hash for spread
    const sat = 50 + (((v * 1013904223) >>> 0) % 30); // 50-79
    const light = 45 + (((v * 1664525) >>> 0) % 20); // 45-64
    const hex = hslToHex(hue, sat, light);
    soilColorCache.set(value, hex);
    return hex;
  }

  function resolveGeoTiffGlobal() {
    if (typeof GeoTIFF !== 'undefined' && GeoTIFF && typeof GeoTIFF.fromArrayBuffer === 'function') {
      return GeoTIFF;
    }
    if (typeof geotiff !== 'undefined') {
      if (geotiff.GeoTIFF && typeof geotiff.GeoTIFF.fromArrayBuffer === 'function') {
        return geotiff.GeoTIFF;
      }
      if (geotiff.default && typeof geotiff.default.fromArrayBuffer === 'function') {
        return geotiff.default;
      }
    }
    return null;
  }

  async function ensureGeoTiff() {
    const existing = resolveGeoTiffGlobal();
    if (existing) {
      return existing;
    }
    if (!geoTiffLoader) {
      geoTiffLoader = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = ctx.geoTiffUrl || 'https://unpkg.com/geotiff@2.1.3/dist-browser/geotiff.js';
        script.async = true;
        script.onload = () => {
          const GT = resolveGeoTiffGlobal();
          if (GT) {
            resolve(GT);
          } else {
            reject(new Error('GeoTIFF global missing after script load'));
          }
        };
        script.onerror = () => {
          reject(new Error('GeoTIFF script failed to load'));
        };
        document.head.appendChild(script);
      });
    }
    return geoTiffLoader;
  }

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
      // Fetch the PNG so we can sample pixel values on hover.
      const imgResp = await fetch(imgurl);
      if (!imgResp.ok) {
        throw new Error(`SBS image fetch failed: ${imgResp.status}`);
      }
      const blob = await imgResp.blob();
      const bitmap = await createImageBitmap(blob);
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const ctx2d = canvas.getContext('2d');
      ctx2d.drawImage(bitmap, 0, 0);
      const imgData = ctx2d.getImageData(0, 0, canvas.width, canvas.height);
      detectedLayers.push({
        key: 'sbs',
        label: 'SBS Map',
        path: 'query/baer_wgs_map',
        bounds,
        canvas,
        width: canvas.width,
        height: canvas.height,
        values: imgData.data,
        sampleMode: 'rgba',
        visible: false,
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load SBS map', err);
    }
  }

  function updateLayerList() {
    if (!layerListEl) return;
    layerListEl.innerHTML = '';
    const sections = [];
    if (landuseLayers.length) {
      sections.push({ title: 'Landuse', items: landuseLayers });
    }
    if (detectedLayers.length) {
      sections.push({ title: 'Rasters', items: detectedLayers });
    }
    if (!sections.length) {
      if (layerEmptyEl) {
        layerEmptyEl.hidden = false;
      }
      return;
    }
    if (layerEmptyEl) {
      layerEmptyEl.hidden = true;
    }
    sections.forEach((section) => {
      const heading = document.createElement('li');
      heading.className = 'gl-layer-group';
      heading.textContent = section.title;
      layerListEl.appendChild(heading);
      section.items.forEach((layer) => {
        const li = document.createElement('li');
        li.className = 'gl-layer-item';
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = layer.visible;
        input.id = `layer-${section.title}-${layer.key}`;
        input.addEventListener('change', () => {
          if (section.title === 'Landuse' && input.checked) {
            // Enforce single-selection for landuse overlays
            section.items.forEach((other) => {
              other.visible = other.key === layer.key;
              const otherInput = document.getElementById(`layer-${section.title}-${other.key}`);
              if (otherInput && otherInput !== input) {
                otherInput.checked = other.visible;
              }
            });
          } else {
            layer.visible = input.checked;
          }
          applyLayers();
        });
        const label = document.createElement('label');
        label.setAttribute('for', input.id);
        const name = layer.label || layer.key;
        const path = layer.path || '';
        label.innerHTML = `<span class="gl-layer-name">${name}</span><br><span class="gl-layer-path">${path}</span>`;
        li.appendChild(input);
        li.appendChild(label);
        layerListEl.appendChild(li);
      });
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
    const landuseDeckLayers = buildLanduseLayers();
    deckgl.setProps({
      layers: [baseLayer, ...landuseDeckLayers, ...activeRasterLayers],
    });
  }

  function hexToRgbaArray(hex, alpha = 230) {
    const parsed = HEX_RGB_RE.exec(hex || '');
    if (!parsed) return null;
    const intVal = parseInt(parsed[1], 16);
    return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, alpha];
  }

  function rgbaStringToArray(str, alphaOverride) {
    const match = RGBA_RE.exec(str || '');
    if (!match) return null;
    const r = Number(match[1]);
    const g = Number(match[2]);
    const b = Number(match[3]);
    const aRaw = match[4];
    if (![r, g, b].every(Number.isFinite)) return null;
    const a = Number.isFinite(Number(aRaw)) ? Number(aRaw) * 255 : 255;
    const finalA = Number.isFinite(alphaOverride) ? alphaOverride : a;
    return [Math.round(r), Math.round(g), Math.round(b), Math.round(finalA)];
  }

  function normalizeColorEntry(entry, alpha = 230) {
    if (!entry) return null;
    if (Array.isArray(entry)) {
      if (entry.length === 4 && entry.every((v) => Number.isFinite(Number(v)))) {
        const r = Number(entry[0]);
        const g = Number(entry[1]);
        const b = Number(entry[2]);
        let a = Number(entry[3]);
        // colormap library returns alpha in 0-1 range; convert to 0-255
        if (a <= 1) {
          a = a * 255;
        }
        // Use the passed alpha override if the original alpha was fully opaque
        if (a >= 254) {
          a = alpha;
        }
        return [r, g, b, Math.round(a)];
      }
    } else if (typeof entry === 'string') {
      const hex = hexToRgbaArray(entry, alpha);
      if (hex) return hex;
      const rgba = rgbaStringToArray(entry, alpha);
      if (rgba) return rgba;
    }
    return null;
  }

  function viridisColor(val) {
    const v = Math.min(1, Math.max(0, Number(val)));
    if (viridisScale && typeof viridisScale.map === 'function') {
      const mapped = viridisScale.map(v);
      const rgba = normalizeColorEntry(mapped, 230);
      if (rgba) return rgba;
    }
    if (viridisScale && Array.isArray(viridisScale) && viridisScale.length) {
      const idx = Math.min(viridisScale.length - 1, Math.floor(v * (viridisScale.length - 1)));
      const color = viridisScale[idx];
      const rgba = normalizeColorEntry(color, 230);
      if (rgba) return rgba;
    }
    const start = [68, 1, 84];
    const end = [253, 231, 37];
    return [
      Math.round(start[0] + (end[0] - start[0]) * v),
      Math.round(start[1] + (end[1] - start[1]) * v),
      Math.round(start[2] + (end[2] - start[2]) * v),
      230,
    ];
  }

  function landuseFillColor(mode, row) {
    if (!row) return [120, 120, 120, 120];
    if (mode === 'dominant') {
      const rgba = hexToRgbaArray(row.color, 220);
      return rgba || [120, 120, 120, 180];
    }
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) {
      return [120, 120, 120, 120];
    }
    return viridisColor(Math.min(1, Math.max(0, value)));
  }

  function landuseValue(mode, row) {
    if (!row) return null;
    if (mode === 'dominant') {
      return row.desc || row.key || row._map || 'landuse';
    }
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildLanduseLayers() {
    const activeLayers = landuseLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && landuseSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `landuse-${overlay.key}`,
          data: subcatchmentsGeoJson,
          pickable: true,
          stroked: false,
          filled: true,
          opacity: 0.8,
          getFillColor: (f) => {
            const props = f && f.properties;
            const topaz =
              props &&
              (props.TopazID ||
                props.topaz_id ||
                props.topaz ||
                props.id ||
                props.WeppID ||
                props.wepp_id);
            const row = topaz != null ? landuseSummary[String(topaz)] : null;
            return landuseFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function computeBoundsFromGdal(info) {
    const wgs84 = info && info.wgs84Extent && info.wgs84Extent.coordinates;
    if (Array.isArray(wgs84) && wgs84.length && Array.isArray(wgs84[0])) {
      const ring = wgs84[0];
      let west = Infinity;
      let south = Infinity;
      let east = -Infinity;
      let north = -Infinity;
      for (const pt of ring) {
        if (!Array.isArray(pt) || pt.length < 2) continue;
        const [lon, lat] = pt;
        if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
        if (lon < west) west = lon;
        if (lon > east) east = lon;
        if (lat < south) south = lat;
        if (lat > north) north = lat;
      }
      if ([west, south, east, north].every((v) => Number.isFinite(v))) {
        return [west, south, east, north];
      }
    }
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

  function sampleRaster(layer, lonLat) {
    if (!layer || !layer.values || !layer.width || !layer.height || !layer.bounds) return null;
    const [lon, lat] = lonLat || [];
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
    const [west, south, east, north] = layer.bounds;
    if (lon < west || lon > east || lat < south || lat > north) {
      return null;
    }
    const x = ((lon - west) / (east - west)) * layer.width;
    const y = ((north - lat) / (north - south)) * layer.height;
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    if (xi < 0 || xi >= layer.width || yi < 0 || yi >= layer.height) return null;
    if (layer.sampleMode === 'rgba') {
      const base = (yi * layer.width + xi) * 4;
      const r = layer.values[base];
      const g = layer.values[base + 1];
      const b = layer.values[base + 2];
      const a = layer.values[base + 3];
      return `rgba(${r}, ${g}, ${b}, ${a})`;
    }
    const idx = yi * layer.width + xi;
    const v = layer.values[idx];
    return Number.isFinite(v) ? v : null;
  }

  function pickActiveRaster() {
    for (let i = detectedLayers.length - 1; i >= 0; i--) {
      const layer = detectedLayers[i];
      if (layer.visible && layer.values) {
        return layer;
      }
    }
    return null;
  }

  function pickActiveLanduseLayer() {
    for (let i = landuseLayers.length - 1; i >= 0; i--) {
      const layer = landuseLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function zoomToBounds(bounds) {
    if (!bounds || bounds.length !== 4) return;
    const [west, south, east, north] = bounds;
    const cx = (west + east) / 2;
    const cy = (south + north) / 2;
    const span = Math.max(east - west, north - south);
    const zoom = Math.max(2, Math.min(14, Math.log2(360 / (span || 0.001)) - 1));
    setViewState({
      longitude: cx,
      latitude: cy,
      zoom,
      bearing: 0,
      pitch: 0,
      minZoom: currentViewState.minZoom,
      maxZoom: currentViewState.maxZoom,
    });
  }

  async function fetchGdalInfo(path) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/gdalinfo/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) return null;
    return resp.json();
  }

  function colorize(values, width, height, colorMap) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx2d = canvas.getContext('2d');
    const imgData = ctx2d.createImageData(width, height);
    const mapEntries =
      colorMap &&
      typeof colorMap !== 'function' &&
      Object.entries(colorMap).reduce((acc, [k, hex]) => {
        const v = Number(k);
        if (!Number.isFinite(v)) return acc;
        const parsed = HEX_RGB_RE.exec(hex || '');
        if (!parsed) return acc;
        const intVal = parseInt(parsed[1], 16);
        acc[v] = [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255];
        return acc;
      }, {});
    const fnCache = new Map();

    if (mapEntries && Object.keys(mapEntries).length) {
      for (let i = 0, j = 0; i < values.length; i++, j += 4) {
        const v = values[i];
        const rgb = mapEntries[v];
        if (rgb) {
          imgData.data[j] = rgb[0];
          imgData.data[j + 1] = rgb[1];
          imgData.data[j + 2] = rgb[2];
          imgData.data[j + 3] = 230;
        } else {
          imgData.data[j + 3] = 0; // transparent for unknown codes
        }
      }
      ctx2d.putImageData(imgData, 0, 0);
      return { canvas, values, width, height, sampleMode: 'scalar' };
    }

    if (typeof colorMap === 'function') {
      for (let i = 0, j = 0; i < values.length; i++, j += 4) {
        const v = values[i];
        if (!Number.isFinite(v)) {
          imgData.data[j + 3] = 0;
          continue;
        }
        let rgb = fnCache.get(v);
        if (!rgb) {
          const hex = colorMap(v);
          const parsed = HEX_RGB_RE.exec(hex || '');
          if (parsed) {
            const intVal = parseInt(parsed[1], 16);
            rgb = [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255];
            fnCache.set(v, rgb);
          }
        }
        if (rgb) {
          imgData.data[j] = rgb[0];
          imgData.data[j + 1] = rgb[1];
          imgData.data[j + 2] = rgb[2];
          imgData.data[j + 3] = 230;
        } else {
          imgData.data[j + 3] = 0;
        }
      }
      ctx2d.putImageData(imgData, 0, 0);
      return { canvas, values, width, height, sampleMode: 'scalar' };
    }

    // Fallback grayscale
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
    return { canvas, values, width, height, sampleMode: 'scalar' };
  }

  async function fetchRasterCanvas(path, colorMap) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/download/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Raster fetch failed: ${resp.status}`);
    }
    const GT = await ensureGeoTiff();
    const array = await resp.arrayBuffer();
    const tiff = await GT.fromArrayBuffer(array);
    const image = await tiff.getImage();
    const width = image.getWidth();
    const height = image.getHeight();
    const data = await image.readRasters({ interleave: true, samples: [0] });
    const values = data;
    return colorize(values, width, height, colorMap);
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
          const colorMap = def.key === 'landuse' ? NLCD_COLORMAP : def.key === 'soils' ? soilColorForValue : null;
          const raster = await fetchRasterCanvas(path, colorMap);
          found = {
            key: def.key,
            label: def.label,
            path,
            bounds,
            canvas: raster.canvas,
            width: raster.width,
            height: raster.height,
            values: raster.values,
            sampleMode: raster.sampleMode,
            visible: false,
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

  async function detectLanduseOverlays() {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/landuse/subcatchments`;
    const geoUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/resources/subcatchments.json`;
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      landuseSummary = await subResp.json();
      subcatchmentsGeoJson = await geoResp.json();
      if (!landuseSummary || !subcatchmentsGeoJson) return;
      const basePath = 'landuse/landuse.parquet';
      landuseLayers.length = 0;
      landuseLayers.push(
        { key: 'lu-dominant', label: 'Dominant landuse', path: basePath, mode: 'dominant', visible: true },
        { key: 'lu-cancov', label: 'Canopy cover (cancov)', path: basePath, mode: 'cancov', visible: false },
        { key: 'lu-inrcov', label: 'Interrill cover (inrcov)', path: basePath, mode: 'inrcov', visible: false },
        { key: 'lu-rilcov', label: 'Rill cover (rilcov)', path: basePath, mode: 'rilcov', visible: false },
      );
      updateLayerList();
      applyLayers();
      // Zoom to project extent from subcatchments GeoJSON
      if (subcatchmentsGeoJson && subcatchmentsGeoJson.features && subcatchmentsGeoJson.features.length) {
        let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
        for (const feat of subcatchmentsGeoJson.features) {
          const geom = feat.geometry;
          if (!geom || !geom.coordinates) continue;
          const coords = geom.type === 'Polygon' ? geom.coordinates[0] : 
                         geom.type === 'MultiPolygon' ? geom.coordinates.flat(2) : [];
          for (const pt of coords) {
            if (!Array.isArray(pt) || pt.length < 2) continue;
            const [lon, lat] = pt;
            if (Number.isFinite(lon) && Number.isFinite(lat)) {
              if (lon < west) west = lon;
              if (lon > east) east = lon;
              if (lat < south) south = lat;
              if (lat > north) north = lat;
            }
          }
        }
        if ([west, south, east, north].every(Number.isFinite)) {
          zoomToBounds([west, south, east, north]);
        }
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load landuse overlays', err);
    }
  }

  const deckgl = new deck.Deck({
    parent: target,
    controller: controllerOptions,
    initialViewState,
    onViewStateChange: ({ viewState }) => {
      setViewState({
        ...viewState,
        minZoom: initialViewState.minZoom,
        maxZoom: initialViewState.maxZoom,
      });
    },
    layers: [baseLayer],
    getTooltip: (info) => {
      if (!info) return null;
      const luOverlay = pickActiveLanduseLayer();
      if (info.object && luOverlay && landuseSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? landuseSummary[String(topaz)] : null;
        const val = landuseValue(luOverlay.mode, row);
        if (val !== null) {
          const label =
            luOverlay.mode === 'dominant'
              ? `Landuse: ${val}`
              : `${luOverlay.mode}: ${typeof val === 'number' ? val.toFixed(3) : val}`;
          return `Layer: ${luOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const rasterLayer = pickActiveRaster();
      if (info.coordinate && rasterLayer) {
        const val = sampleRaster(rasterLayer, info.coordinate);
        if (val !== null) {
          return `Layer: ${rasterLayer.path}\nValue: ${val}`;
        }
      }
      if (info.tile) {
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

  Promise.all([detectLayers(), detectLanduseOverlays()]).catch((err) => {
    // eslint-disable-next-line no-console
    console.error('gl-dashboard: layer detection failed', err);
  });
})();

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

  const defaultTileTemplate =
    ctx.tileUrl || 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png';

  // Basemap definitions - Google endpoints match wepppy/weppcloud/controllers_js/map.js
  const GOOGLE_SUBDOMAINS = ['mt0', 'mt1', 'mt2', 'mt3'];
  let subdomainIndex = 0;
  function nextGoogleSubdomain() {
    const sub = GOOGLE_SUBDOMAINS[subdomainIndex % GOOGLE_SUBDOMAINS.length];
    subdomainIndex++;
    return sub;
  }

  const BASEMAP_DEFS = {
    osm: {
      label: 'OpenStreetMap',
      template: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
      getUrl: function (x, y, z) {
        return this.template
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      }
    },
    googleTerrain: {
      label: 'Google Terrain',
      template: 'https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
      getUrl: function (x, y, z) {
        const sub = nextGoogleSubdomain();
        return this.template
          .replace('{s}', sub)
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      }
    },
    googleSatellite: {
      label: 'Google Satellite',
      template: 'https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
      getUrl: function (x, y, z) {
        const sub = nextGoogleSubdomain();
        return this.template
          .replace('{s}', sub)
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      }
    }
  };

  let currentBasemapKey = ctx.basemap || 'googleTerrain';
  if (!BASEMAP_DEFS[currentBasemapKey]) {
    currentBasemapKey = 'googleTerrain';
  }

  // Use map extent/center/zoom from ron.nodb if available
  const mapCenter = ctx.mapCenter; // [longitude, latitude]
  const mapZoom = ctx.mapZoom;

  const initialViewState = {
    longitude: mapCenter && mapCenter[0] != null ? mapCenter[0] : (ctx.longitude || -114.5),
    latitude: mapCenter && mapCenter[1] != null ? mapCenter[1] : (ctx.latitude || 43.8),
    zoom: mapZoom != null ? mapZoom : (ctx.zoom || 5),
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

  function createBaseLayer(basemapKey) {
    const basemapDef = BASEMAP_DEFS[basemapKey] || BASEMAP_DEFS.googleTerrain;
    return new deck.TileLayer({
      id: 'gl-dashboard-base-tiles',
      data: basemapDef.template,
      minZoom: 0,
      maxZoom: 19,
      tileSize: 256,
      maxRequests: 8,
      getTileData: async ({ index, signal }) => {
        const { x, y, z } = index || {};
        if (![x, y, z].every(Number.isFinite)) {
          throw new Error(`Tile coords missing: x=${x} y=${y} z=${z}`);
        }
        const url = basemapDef.getUrl(x, y, z);
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
  }

  let baseLayer = createBaseLayer(currentBasemapKey);

  function setBasemap(basemapKey) {
    if (!BASEMAP_DEFS[basemapKey]) {
      console.warn('gl-dashboard: unknown basemap key', basemapKey);
      return;
    }
    currentBasemapKey = basemapKey;
    baseLayer = createBaseLayer(basemapKey);
    applyLayers();
    // Update selector UI if present
    const selector = document.getElementById('gl-basemap-select');
    if (selector && selector.value !== basemapKey) {
      selector.value = basemapKey;
    }
  }

  function toggleSubcatchmentLabels(visible) {
    subcatchmentLabelsVisible = !!visible;
    applyLayers();
    // Update checkbox UI if present
    const checkbox = document.getElementById('gl-subcatchment-labels-toggle');
    if (checkbox && checkbox.checked !== subcatchmentLabelsVisible) {
      checkbox.checked = subcatchmentLabelsVisible;
    }
  }

  // Expose basemap API for external use
  window.glDashboardSetBasemap = setBasemap;
  window.glDashboardBasemaps = BASEMAP_DEFS;
  window.glDashboardToggleLabels = toggleSubcatchmentLabels;

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
  const soilsLayers = [];
  const hillslopesLayers = [];
  const weppLayers = [];
  const rapLayers = [];
  let landuseSummary = null;
  let soilsSummary = null;
  let hillslopesSummary = null;
  let weppSummary = null;
  let rapSummary = null;
  let rapMetadata = null;
  let rapSelectedYear = null;
  let subcatchmentsGeoJson = null;
  let subcatchmentLabelsVisible = false;
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

  // Helper to deselect all subcatchment overlays across landuse, soils, and hillslopes
  function deselectAllSubcatchmentOverlays() {
    landuseLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-Landuse-${l.key}`);
      if (el) el.checked = false;
    });
    soilsLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-Soils-${l.key}`);
      if (el) el.checked = false;
    });
    hillslopesLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-Watershed-${l.key}`);
      if (el) el.checked = false;
    });
    weppLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-WEPP-${l.key}`);
      if (el) el.checked = false;
    });
    rapLayers.forEach((l) => {
      l.visible = false;
      const el = document.getElementById(`layer-RAP-${l.key}`);
      if (el) el.checked = false;
    });
  }

  function updateLayerList() {
    if (!layerListEl) return;
    layerListEl.innerHTML = '';
    const subcatchmentSections = [];
    const rasterSections = [];
    if (landuseLayers.length) {
      subcatchmentSections.push({ title: 'Landuse', items: landuseLayers, isSubcatchment: true });
    }
    if (soilsLayers.length) {
      subcatchmentSections.push({ title: 'Soils', items: soilsLayers, isSubcatchment: true });
    }
    if (hillslopesLayers.length) {
      subcatchmentSections.push({ title: 'Watershed', items: hillslopesLayers, isSubcatchment: true });
    }
    if (weppLayers.length) {
      subcatchmentSections.push({ title: 'WEPP', items: weppLayers, isSubcatchment: true });
    }
    if (rapLayers.length) {
      subcatchmentSections.push({ title: 'RAP', items: rapLayers, isSubcatchment: true, hasYearPicker: true });
    }
    if (detectedLayers.length) {
      rasterSections.push({ title: 'Rasters', items: detectedLayers, isSubcatchment: false });
    }
    const allSections = [...subcatchmentSections, ...rasterSections];
    if (!allSections.length) {
      if (layerEmptyEl) {
        layerEmptyEl.hidden = false;
      }
      return;
    }
    if (layerEmptyEl) {
      layerEmptyEl.hidden = true;
    }
    // Add subcatchment section header if we have any
    if (subcatchmentSections.length) {
      const groupHeader = document.createElement('li');
      groupHeader.className = 'gl-layer-group-header';
      groupHeader.textContent = 'Subcatchment Overlays';
      layerListEl.appendChild(groupHeader);
    }
    allSections.forEach((section, idx) => {
      // Create collapsible details element
      const details = document.createElement('details');
      details.className = 'gl-layer-details';
      // Open the first section by default, or sections with visible items
      const hasVisibleItem = section.items.some((l) => l.visible);
      details.open = idx === 0 || hasVisibleItem;

      const summary = document.createElement('summary');
      summary.className = 'gl-layer-group';
      summary.textContent = section.title;
      details.appendChild(summary);

      // Add year picker for RAP section (custom dropdown for dark theme)
      if (section.hasYearPicker && rapMetadata && rapMetadata.years && rapMetadata.years.length) {
        const yearPickerDiv = document.createElement('div');
        yearPickerDiv.className = 'gl-year-picker';
        yearPickerDiv.style.cssText = 'padding: 0.5rem; display: flex; align-items: center; gap: 0.5rem;';
        const yearLabel = document.createElement('label');
        yearLabel.textContent = 'Year:';
        yearLabel.style.fontWeight = '500';

        // Custom dropdown container
        const dropdownContainer = document.createElement('div');
        dropdownContainer.className = 'gl-custom-select';
        dropdownContainer.style.cssText = 'flex: 1; position: relative;';

        const selectedDisplay = document.createElement('button');
        selectedDisplay.type = 'button';
        selectedDisplay.className = 'gl-custom-select__trigger';
        selectedDisplay.textContent = rapSelectedYear;
        selectedDisplay.setAttribute('aria-haspopup', 'listbox');
        selectedDisplay.setAttribute('aria-expanded', 'false');

        const optionsList = document.createElement('ul');
        optionsList.className = 'gl-custom-select__options';
        optionsList.setAttribute('role', 'listbox');
        optionsList.style.display = 'none';

        rapMetadata.years.forEach((year) => {
          const li = document.createElement('li');
          li.className = 'gl-custom-select__option';
          li.setAttribute('role', 'option');
          li.setAttribute('data-value', year);
          li.textContent = year;
          if (year === rapSelectedYear) {
            li.classList.add('is-selected');
            li.setAttribute('aria-selected', 'true');
          }
          li.addEventListener('click', async () => {
            rapSelectedYear = year;
            selectedDisplay.textContent = year;
            optionsList.querySelectorAll('.gl-custom-select__option').forEach((o) => {
              o.classList.remove('is-selected');
              o.setAttribute('aria-selected', 'false');
            });
            li.classList.add('is-selected');
            li.setAttribute('aria-selected', 'true');
            optionsList.style.display = 'none';
            selectedDisplay.setAttribute('aria-expanded', 'false');
            await refreshRapData();
            applyLayers();
          });
          optionsList.appendChild(li);
        });

        selectedDisplay.addEventListener('click', (e) => {
          e.stopPropagation();
          const isOpen = optionsList.style.display !== 'none';
          optionsList.style.display = isOpen ? 'none' : 'block';
          selectedDisplay.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', () => {
          optionsList.style.display = 'none';
          selectedDisplay.setAttribute('aria-expanded', 'false');
        });

        dropdownContainer.appendChild(selectedDisplay);
        dropdownContainer.appendChild(optionsList);
        yearPickerDiv.appendChild(yearLabel);
        yearPickerDiv.appendChild(dropdownContainer);
        details.appendChild(yearPickerDiv);
      }

      const itemList = document.createElement('ul');
      itemList.className = 'gl-layer-items';

      section.items.forEach((layer) => {
        const li = document.createElement('li');
        li.className = 'gl-layer-item';
        const input = document.createElement('input');
        // Use radio for subcatchment overlays (landuse/soils), checkbox for rasters
        input.type = section.isSubcatchment ? 'radio' : 'checkbox';
        if (section.isSubcatchment) {
          input.name = 'subcatchment-overlay';
        }
        input.checked = layer.visible;
        input.id = `layer-${section.title}-${layer.key}`;
        input.addEventListener('change', async () => {
          if (section.isSubcatchment) {
            // Radio behavior: deselect all, then select this one
            deselectAllSubcatchmentOverlays();
            layer.visible = true;
            input.checked = true;
            // For RAP layers, refresh data for the selected band via query-engine
            if (layer.bandId && rapSelectedYear) {
              try {
                const dataPayload = {
                  datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
                  columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
                  filters: [
                    { column: 'rap.year', op: '=', value: rapSelectedYear },
                    { column: 'rap.band', op: '=', value: layer.bandId },
                  ],
                };
                const dataResult = await postQueryEngine(dataPayload);
                if (dataResult && dataResult.records) {
                  rapSummary = {};
                  for (const row of dataResult.records) {
                    rapSummary[String(row.topaz_id)] = row.value;
                  }
                }
              } catch (err) {
                // eslint-disable-next-line no-console
                console.warn('gl-dashboard: failed to load RAP band data', err);
              }
            }
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
        itemList.appendChild(li);
      });

      details.appendChild(itemList);
      layerListEl.appendChild(details);
    });
  }

  function buildSubcatchmentLabelsLayer() {
    if (!subcatchmentLabelsVisible || !subcatchmentsGeoJson) {
      return [];
    }
    // Compute centroids for label placement, ensuring unique labels per topaz_id
    const labelData = [];
    const seenIds = new Set();
    const features = subcatchmentsGeoJson.features || [];
    features.forEach((feature) => {
      const props = feature.properties || {};
      const topazId = props.TopazID || props.topaz_id || props.topaz || props.id;
      if (topazId == null) return;
      // Skip if we've already added a label for this topaz_id
      const idKey = String(topazId);
      if (seenIds.has(idKey)) return;
      seenIds.add(idKey);
      // Compute centroid from geometry
      const geom = feature.geometry;
      if (!geom) return;
      let coords = [];
      if (geom.type === 'Polygon' && geom.coordinates && geom.coordinates[0]) {
        coords = geom.coordinates[0];
      } else if (geom.type === 'MultiPolygon' && geom.coordinates && geom.coordinates[0] && geom.coordinates[0][0]) {
        coords = geom.coordinates[0][0];
      }
      if (!coords.length) return;
      let sumX = 0, sumY = 0;
      coords.forEach((pt) => {
        sumX += pt[0];
        sumY += pt[1];
      });
      const centroid = [sumX / coords.length, sumY / coords.length];
      labelData.push({
        position: centroid,
        text: idKey,
      });
    });
    return [
      new deck.TextLayer({
        id: 'subcatchment-labels',
        data: labelData,
        getPosition: (d) => d.position,
        getText: (d) => d.text,
        getSize: 14,
        getColor: [255, 255, 255, 255],
        getTextAnchor: 'middle',
        getAlignmentBaseline: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontWeight: 'bold',
        outlineColor: [0, 0, 0, 200],
        outlineWidth: 2,
        billboard: false,
        sizeUnits: 'pixels',
        pickable: false,
      }),
    ];
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
    const soilsDeckLayers = buildSoilsLayers();
    const hillslopesDeckLayers = buildHillslopesLayers();
    const weppDeckLayers = buildWeppLayers();
    const rapDeckLayers = buildRapLayers();
    const labelLayers = buildSubcatchmentLabelsLayer();
    deckgl.setProps({
      layers: [baseLayer, ...landuseDeckLayers, ...soilsDeckLayers, ...hillslopesDeckLayers, ...weppDeckLayers, ...rapDeckLayers, ...activeRasterLayers, ...labelLayers],
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

  function soilsFillColor(mode, row) {
    if (!row) return [120, 120, 120, 120];
    if (mode === 'dominant') {
      const rgba = hexToRgbaArray(row.color, 220);
      return rgba || [120, 120, 120, 180];
    }
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) {
      return [120, 120, 120, 120];
    }
    // Normalize value ranges for viridis color scale
    let normalized = 0;
    if (mode === 'clay' || mode === 'sand' || mode === 'rock') {
      // These are percentages 0-100
      normalized = Math.min(1, Math.max(0, value / 100));
    } else if (mode === 'bd') {
      // Bulk density typically 0.5-2.0 g/cm3
      normalized = Math.min(1, Math.max(0, (value - 0.5) / 1.5));
    } else {
      normalized = Math.min(1, Math.max(0, value));
    }
    return viridisColor(normalized);
  }

  function soilsValue(mode, row) {
    if (!row) return null;
    if (mode === 'dominant') {
      return row.desc || row.simple_texture || row.mukey || 'soil';
    }
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildSoilsLayers() {
    const activeLayers = soilsLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && soilsSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `soils-${overlay.key}`,
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
            const row = topaz != null ? soilsSummary[String(topaz)] : null;
            return soilsFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  // Hillslopes value ranges for normalization (approximate)
  const HILLSLOPES_RANGES = {
    slope_scalar: { min: 0, max: 1 },     // 0-100% slope as decimal
    length: { min: 0, max: 1000 },         // meters
    aspect: { min: 0, max: 360 },          // degrees
  };

  function hillslopesFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];

    // For aspect, use a circular colormap (HSL hue)
    if (mode === 'aspect') {
      // Convert aspect degrees to hue (0-360)
      const hue = value % 360;
      // Simple HSL to RGB conversion for hue wheel
      const h = hue / 60;
      const c = 200; // chroma
      const x = c * (1 - Math.abs((h % 2) - 1));
      let r, g, b;
      if (h < 1) { r = c; g = x; b = 0; }
      else if (h < 2) { r = x; g = c; b = 0; }
      else if (h < 3) { r = 0; g = c; b = x; }
      else if (h < 4) { r = 0; g = x; b = c; }
      else if (h < 5) { r = x; g = 0; b = c; }
      else { r = c; g = 0; b = x; }
      return [Math.round(r + 55), Math.round(g + 55), Math.round(b + 55), 200];
    }

    // For slope and length, use viridis scale
    const range = HILLSLOPES_RANGES[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    return viridisColor(normalized);
  }

  function hillslopesValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildHillslopesLayers() {
    const activeLayers = hillslopesLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && hillslopesSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `hillslopes-${overlay.key}`,
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
            const row = topaz != null ? hillslopesSummary[String(topaz)] : null;
            return hillslopesFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function pickActiveHillslopesLayer() {
    for (let i = hillslopesLayers.length - 1; i >= 0; i--) {
      const layer = hillslopesLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  // WEPP loss ranges computed dynamically from weppSummary data
  let weppRanges = {};

  function computeWeppRanges() {
    if (!weppSummary) return;
    const modes = ['subrunoff_volume', 'baseflow_volume', 'soil_loss', 'sediment_deposition', 'sediment_yield'];
    weppRanges = {};
    for (const mode of modes) {
      let min = Infinity;
      let max = -Infinity;
      for (const key of Object.keys(weppSummary)) {
        const row = weppSummary[key];
        const v = Number(row[mode]);
        if (Number.isFinite(v)) {
          if (v < min) min = v;
          if (v > max) max = v;
        }
      }
      // Handle edge cases
      if (!Number.isFinite(min)) min = 0;
      if (!Number.isFinite(max)) max = 1;
      if (max <= min) max = min + 1;
      weppRanges[mode] = { min, max };
    }
  }

  function weppFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];

    const range = weppRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    return viridisColor(normalized);
  }

  function weppValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function buildWeppLayers() {
    const activeLayers = weppLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && weppSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `wepp-${overlay.key}`,
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
            const row = topaz != null ? weppSummary[String(topaz)] : null;
            return weppFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function pickActiveWeppLayer() {
    for (let i = weppLayers.length - 1; i >= 0; i--) {
      const layer = weppLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  // RAP band labels for display
  const RAP_BAND_LABELS = {
    annual_forb_grass: 'Annual Forb & Grass',
    bare_ground: 'Bare Ground',
    litter: 'Litter',
    perennial_forb_grass: 'Perennial Forb & Grass',
    shrub: 'Shrub',
    tree: 'Tree',
  };

  function rapFillColor(row) {
    if (!row) return [128, 128, 128, 200];
    const value = Number(row);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    // RAP values are percentages 0-100
    const normalized = Math.min(1, Math.max(0, value / 100));
    return viridisColor(normalized);
  }

  function rapValue(row) {
    if (row == null) return null;
    const v = Number(row);
    return Number.isFinite(v) ? v : null;
  }

  function buildRapLayers() {
    const activeLayers = rapLayers
      .filter((l) => l.visible && subcatchmentsGeoJson && rapSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `rap-${overlay.key}`,
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
            const row = topaz != null ? rapSummary[String(topaz)] : null;
            return rapFillColor(row);
          },
        });
      });
    return activeLayers;
  }

  function pickActiveRapLayer() {
    for (let i = rapLayers.length - 1; i >= 0; i--) {
      const layer = rapLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  async function refreshRapData() {
    const activeLayer = pickActiveRapLayer();
    if (!activeLayer || !rapSelectedYear) return;
    try {
      const dataPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
        filters: [
          { column: 'rap.year', op: '=', value: rapSelectedYear },
          { column: 'rap.band', op: '=', value: activeLayer.bandId },
        ],
      };
      const dataResult = await postQueryEngine(dataPayload);
      if (dataResult && dataResult.records) {
        rapSummary = {};
        for (const row of dataResult.records) {
          rapSummary[String(row.topaz_id)] = row.value;
        }
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to refresh RAP data', err);
    }
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

  function pickActiveSoilsLayer() {
    for (let i = soilsLayers.length - 1; i >= 0; i--) {
      const layer = soilsLayers[i];
      if (layer.visible) {
        return layer;
      }
    }
    return null;
  }

  function zoomToBounds(bounds, explicitZoom) {
    if (!bounds || bounds.length !== 4) return;
    const [west, south, east, north] = bounds;
    const cx = (west + east) / 2;
    const cy = (south + north) / 2;
    // Use explicit zoom if provided, otherwise calculate from bounds span
    let zoom;
    if (explicitZoom != null && Number.isFinite(explicitZoom)) {
      zoom = explicitZoom;
    } else {
      const span = Math.max(east - west, north - south);
      zoom = Math.max(2, Math.min(16, Math.log2(360 / (span || 0.001)) - 1));
    }
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
      // Zoom to project extent from ron.map if available, otherwise compute from subcatchments GeoJSON
      const ronExtent = ctx.mapExtent;
      const ronZoom = ctx.mapZoom;
      if (ronExtent && ronExtent.length === 4 && ronExtent.every(Number.isFinite)) {
        zoomToBounds(ronExtent, ronZoom);
      } else if (subcatchmentsGeoJson && subcatchmentsGeoJson.features && subcatchmentsGeoJson.features.length) {
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

  async function detectSoilsOverlays() {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/soils/subcatchments`;
    const geoUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/resources/subcatchments.json`;
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      soilsSummary = await subResp.json();
      // subcatchmentsGeoJson may already be loaded by detectLanduseOverlays
      if (!subcatchmentsGeoJson) {
        subcatchmentsGeoJson = await geoResp.json();
      }
      if (!soilsSummary || !subcatchmentsGeoJson) return;
      const basePath = 'soils/soils.parquet';
      soilsLayers.length = 0;
      soilsLayers.push(
        { key: 'soil-dominant', label: 'Dominant soil (color)', path: basePath, mode: 'dominant', visible: false },
        { key: 'soil-clay', label: 'Clay content (%)', path: basePath, mode: 'clay', visible: false },
        { key: 'soil-sand', label: 'Sand content (%)', path: basePath, mode: 'sand', visible: false },
        { key: 'soil-bd', label: 'Bulk density (g/cm³)', path: basePath, mode: 'bd', visible: false },
        { key: 'soil-rock', label: 'Rock content (%)', path: basePath, mode: 'rock', visible: false },
      );
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load soils overlays', err);
    }
  }

  async function detectHillslopesOverlays() {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/watershed/subcatchments`;
    const geoUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/resources/subcatchments.json`;
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      hillslopesSummary = await subResp.json();
      // subcatchmentsGeoJson may already be loaded by detectLanduseOverlays or detectSoilsOverlays
      if (!subcatchmentsGeoJson) {
        subcatchmentsGeoJson = await geoResp.json();
      }
      if (!hillslopesSummary || !subcatchmentsGeoJson) return;
      const basePath = 'watershed/hillslopes.parquet';
      hillslopesLayers.length = 0;
      hillslopesLayers.push(
        { key: 'hillslope-slope', label: 'Slope (rise/run)', path: basePath, mode: 'slope_scalar', visible: false },
        { key: 'hillslope-length', label: 'Hillslope length (m)', path: basePath, mode: 'length', visible: false },
        { key: 'hillslope-aspect', label: 'Aspect (degrees)', path: basePath, mode: 'aspect', visible: false },
      );
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load hillslopes overlays', err);
    }
  }

  async function detectWeppOverlays() {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/query/wepp/loss/hillslopes`;
    const geoUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/resources/subcatchments.json`;
    try {
      const [subResp, geoResp] = await Promise.all([fetch(url), fetch(geoUrl)]);
      if (!subResp.ok || !geoResp.ok) return;
      weppSummary = await subResp.json();
      // subcatchmentsGeoJson may already be loaded by other detect functions
      if (!subcatchmentsGeoJson) {
        subcatchmentsGeoJson = await geoResp.json();
      }
      if (!weppSummary || !subcatchmentsGeoJson) return;
      // Compute dynamic ranges from the loaded data
      computeWeppRanges();
      const basePath = 'wepp/output/interchange/loss_pw0.hill.parquet';
      weppLayers.length = 0;
      weppLayers.push(
        { key: 'wepp-subrunoff', label: 'Subrunoff Volume (mm)', path: basePath, mode: 'subrunoff_volume', visible: false },
        { key: 'wepp-baseflow', label: 'Baseflow Volume (mm)', path: basePath, mode: 'baseflow_volume', visible: false },
        { key: 'wepp-soil-loss', label: 'Soil Loss (tonnes/ha)', path: basePath, mode: 'soil_loss', visible: false },
        { key: 'wepp-sed-dep', label: 'Sediment Deposition (tonnes/ha)', path: basePath, mode: 'sediment_deposition', visible: false },
        { key: 'wepp-sed-yield', label: 'Sediment Yield (tonnes/ha)', path: basePath, mode: 'sediment_yield', visible: false },
      );
      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load WEPP overlays', err);
    }
  }

  /**
   * Post a JSON payload to the query-engine and return the parsed response.
   * @param {Object} payload - Query engine request body
   * @returns {Promise<Object|null>} Parsed JSON response or null on failure
   */
  async function postQueryEngine(payload) {
    const origin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
    const targetUrl = `${origin}/query-engine/runs/${ctx.runid}/query`;
    const resp = await fetch(targetUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) return null;
    return resp.json();
  }

  async function detectRapOverlays() {
    const geoUrl = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/resources/subcatchments.json`;
    try {
      // Query for available years
      const yearsPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['DISTINCT rap.year AS year'],
        order_by: ['year'],
      };
      const yearsResult = await postQueryEngine(yearsPayload);
      if (!yearsResult || !yearsResult.records || !yearsResult.records.length) return;

      // Query for available bands
      const bandsPayload = {
        datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
        columns: ['DISTINCT rap.band AS band'],
        order_by: ['band'],
      };
      const bandsResult = await postQueryEngine(bandsPayload);
      if (!bandsResult || !bandsResult.records || !bandsResult.records.length) return;

      const years = yearsResult.records.map((r) => r.year);
      const bands = bandsResult.records.map((r) => r.band);

      // Build rapMetadata from query results
      const RAP_BAND_ID_TO_KEY = {
        1: 'annual_forb_grass',
        2: 'bare_ground',
        3: 'litter',
        4: 'perennial_forb_grass',
        5: 'shrub',
        6: 'tree',
      };
      rapMetadata = {
        available: true,
        years,
        bands: bands.map((id) => ({ id, label: RAP_BAND_ID_TO_KEY[id] || `band_${id}` })),
      };

      // Set default year to most recent
      if (years.length) {
        rapSelectedYear = years[years.length - 1];
      }

      // Ensure subcatchments are loaded
      if (!subcatchmentsGeoJson) {
        const geoResp = await fetch(geoUrl);
        if (geoResp.ok) {
          subcatchmentsGeoJson = await geoResp.json();
        }
      }
      if (!subcatchmentsGeoJson) return;

      // Build layer definitions for each band
      const basePath = 'rap/rap_ts.parquet';
      rapLayers.length = 0;
      for (const band of rapMetadata.bands) {
        const label = RAP_BAND_LABELS[band.label] || band.label;
        rapLayers.push({
          key: `rap-${band.label}`,
          label: `${label} (%)`,
          path: basePath,
          bandId: band.id,
          bandKey: band.label,
          visible: false,
        });
      }

      // Load initial data for the first band via query-engine
      if (rapLayers.length && rapSelectedYear) {
        const firstBand = rapLayers[0];
        const dataPayload = {
          datasets: [{ path: 'rap/rap_ts.parquet', alias: 'rap' }],
          columns: ['rap.topaz_id AS topaz_id', 'rap.value AS value'],
          filters: [
            { column: 'rap.year', op: '=', value: rapSelectedYear },
            { column: 'rap.band', op: '=', value: firstBand.bandId },
          ],
        };
        const dataResult = await postQueryEngine(dataPayload);
        if (dataResult && dataResult.records) {
          rapSummary = {};
          for (const row of dataResult.records) {
            rapSummary[String(row.topaz_id)] = row.value;
          }
        }
      }

      updateLayerList();
      applyLayers();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: failed to load RAP overlays', err);
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
      const soilOverlay = pickActiveSoilsLayer();
      if (info.object && soilOverlay && soilsSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? soilsSummary[String(topaz)] : null;
        const val = soilsValue(soilOverlay.mode, row);
        if (val !== null) {
          let label;
          if (soilOverlay.mode === 'dominant') {
            label = `Soil: ${val}`;
          } else if (soilOverlay.mode === 'bd') {
            label = `Bulk density: ${typeof val === 'number' ? val.toFixed(2) : val} g/cm³`;
          } else {
            label = `${soilOverlay.mode}: ${typeof val === 'number' ? val.toFixed(1) : val}%`;
          }
          return `Layer: ${soilOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const hillslopesOverlay = pickActiveHillslopesLayer();
      if (info.object && hillslopesOverlay && hillslopesSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? hillslopesSummary[String(topaz)] : null;
        const val = hillslopesValue(hillslopesOverlay.mode, row);
        if (val !== null) {
          let label;
          if (hillslopesOverlay.mode === 'slope_scalar') {
            label = `Slope: ${typeof val === 'number' ? (val * 100).toFixed(1) : val}%`;
          } else if (hillslopesOverlay.mode === 'length') {
            label = `Length: ${typeof val === 'number' ? val.toFixed(1) : val} m`;
          } else if (hillslopesOverlay.mode === 'aspect') {
            label = `Aspect: ${typeof val === 'number' ? val.toFixed(0) : val}°`;
          } else {
            label = `${hillslopesOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          }
          return `Layer: ${hillslopesOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const weppOverlay = pickActiveWeppLayer();
      if (info.object && weppOverlay && weppSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? weppSummary[String(topaz)] : null;
        const val = weppValue(weppOverlay.mode, row);
        if (val !== null) {
          let label;
          if (weppOverlay.mode === 'subrunoff_volume') {
            label = `Subrunoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppOverlay.mode === 'baseflow_volume') {
            label = `Baseflow: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
          } else if (weppOverlay.mode === 'soil_loss') {
            label = `Soil Loss: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else if (weppOverlay.mode === 'sediment_deposition') {
            label = `Sed. Deposition: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else if (weppOverlay.mode === 'sediment_yield') {
            label = `Sed. Yield: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
          } else {
            label = `${weppOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
          }
          return `Layer: ${weppOverlay.path}\nTopazID: ${topaz}\n${label}`;
        }
      }
      const rapOverlay = pickActiveRapLayer();
      if (info.object && rapOverlay && rapSummary) {
        const props = info.object && info.object.properties;
        const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
        const row = topaz != null ? rapSummary[String(topaz)] : null;
        const val = rapValue(row);
        if (val !== null) {
          const bandLabel = RAP_BAND_LABELS[rapOverlay.bandKey] || rapOverlay.bandKey;
          const label = `${bandLabel}: ${typeof val === 'number' ? val.toFixed(1) : val}%`;
          return `Layer: ${rapOverlay.path}\nYear: ${rapSelectedYear}\nTopazID: ${topaz}\n${label}`;
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

  Promise.all([detectLayers(), detectLanduseOverlays(), detectSoilsOverlays(), detectHillslopesOverlays(), detectWeppOverlays(), detectRapOverlays()]).catch((err) => {
    // eslint-disable-next-line no-console
    console.error('gl-dashboard: layer detection failed', err);
  });
})();

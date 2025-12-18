/**
 * Basemap + subcatchment toggle wiring for gl-dashboard orchestrator.
 */

export function createBasemapController({ deck, basemapDefs, getState, setValue }) {
  let baseLayer = null;
  let applyLayers = () => {};

  function setApplyLayers(fn) {
    applyLayers = typeof fn === 'function' ? fn : () => {};
  }

  function createBaseLayer(basemapKey) {
    const basemapDef = basemapDefs[basemapKey] || basemapDefs.googleTerrain;
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

  function getBaseLayer() {
    return baseLayer;
  }

  function setBaseLayer(layer) {
    baseLayer = layer;
  }

  function setBasemap(basemapKey) {
    if (!basemapDefs[basemapKey]) {
      // eslint-disable-next-line no-console
      console.warn('gl-dashboard: unknown basemap key', basemapKey);
      return;
    }
    setValue('currentBasemapKey', basemapKey);
    baseLayer = createBaseLayer(basemapKey);
    applyLayers();
    const selector = document.getElementById('gl-basemap-select');
    if (selector && selector.value !== basemapKey) {
      selector.value = basemapKey;
    }
  }

  function toggleSubcatchmentLabels(visible) {
    setValue('subcatchmentLabelsVisible', !!visible);
    applyLayers();
    const checkbox = document.getElementById('gl-subcatchment-labels-toggle');
    if (checkbox && checkbox.checked !== visible) {
      checkbox.checked = !!visible;
    }
  }

  function toggleSubcatchments(visible) {
    setValue('subcatchmentsVisible', !!visible);
    applyLayers();
    const checkbox = document.getElementById('gl-subcatchments-toggle');
    if (checkbox && checkbox.checked !== visible) {
      checkbox.checked = !!visible;
    }
  }

  function bindBasemapControls() {
    const basemapSelect = document.getElementById('gl-basemap-select');
    if (basemapSelect) {
      const initialBasemap = basemapDefs[getState().currentBasemapKey] ? getState().currentBasemapKey : 'googleTerrain';
      basemapSelect.value = initialBasemap;
      basemapSelect.addEventListener('change', (e) => setBasemap(e.target.value));
    }
    const labelsToggle = document.getElementById('gl-subcatchment-labels-toggle');
    if (labelsToggle) {
      labelsToggle.addEventListener('change', (e) => toggleSubcatchmentLabels(e.target.checked));
    }
    const subcatchmentsToggle = document.getElementById('gl-subcatchments-toggle');
    if (subcatchmentsToggle) {
      subcatchmentsToggle.checked = !!getState().subcatchmentsVisible;
      subcatchmentsToggle.addEventListener('change', (e) => toggleSubcatchments(e.target.checked));
    }
  }

  return {
    createBaseLayer,
    getBaseLayer,
    setBaseLayer,
    setBasemap,
    toggleSubcatchmentLabels,
    toggleSubcatchments,
    bindBasemapControls,
    setApplyLayers,
  };
}


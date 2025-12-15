// Layer builders, color/value helpers, and tooltip/legend utilities for gl-dashboard.

import { normalizeModeValue, resolveColormapName } from '../colors.js';

function pickActive(arr) {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i].visible) {
      return arr[i];
    }
  }
  return null;
}

export function createLayerUtils({
  deck,
  getState,
  colorScales,
  constants,
}) {
  const { viridisColor, winterColor, jet2Color, rdbuScale } = colorScales;
  const { WATER_MEASURES, SOIL_MEASURES, NLCD_COLORMAP, NLCD_LABELS, RAP_BAND_LABELS } = constants;

  function colorFromPalette(name, normalized) {
    if (name === 'winter') return winterColor(normalized);
    if (name === 'jet2') return jet2Color(normalized);
    if (name === 'viridis') return viridisColor(normalized);
    // Fallback to viridis to avoid silent gray fills if a palette is added without support.
    return viridisColor(normalized);
  }

  function landuseValue(mode, row) {
    if (!row) return null;
    if (mode === 'dominant') return row.dominant || row.cover_desc || row.key || row._map || null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function landuseFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    if (mode === 'dominant') {
      const key = row.key ?? row._map;
      if (key == null) return [128, 128, 128, 200];
      const parsed = Number.parseInt(key, 10);
      if (!Number.isFinite(parsed)) return [128, 128, 128, 200];
      const hex = NLCD_COLORMAP[parsed];
      if (!hex) return [128, 128, 128, 200];
      const intVal = Number.parseInt(hex.replace('#', ''), 16);
      return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, 220];
    }
    const v = Number(row[mode]);
    const normalized = normalizeModeValue(mode, v);
    if (!Number.isFinite(normalized)) return [128, 128, 128, 200];
    const palette = resolveColormapName(mode, 'Landuse', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function landuseComparisonFillColor(mode, scenarioRow, baseRow) {
    const state = getState();
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const usePercentScale = Math.abs(baseValue) > 1 || Math.abs(scenarioValue) > 1;
    const range = state.comparisonDiffRanges[mode] || { min: usePercentScale ? -50 : -1, max: usePercentScale ? 50 : 1 };
    const normalized = Math.min(1, Math.max(0, (diff - range.min) / (range.max - range.min || 1)));
    return rdbuScale(normalized);
  }

  function soilsValue(mode, row) {
    if (!row) return null;
    if (mode === 'dominant') return row.texture || row.simple_texture || row.desc || row.dom_texture || row.dom_desc || null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function hillslopesValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function watarValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function weppValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function weppYearlyValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function weppEventValue(mode, row) {
    if (!row) return null;
    const v = Number(row[mode]);
    return Number.isFinite(v) ? v : null;
  }

  function rapValue(row) {
    if (row == null) return null;
    const v = Number(row);
    return Number.isFinite(v) ? v : null;
  }

  function landuseColor(mode, row, topazId) {
    const state = getState();
    if (state.comparisonMode && state.currentScenarioPath && state.baseSummaryCache.landuse && ['cancov', 'inrcov', 'rilcov'].includes(mode)) {
      const baseRow = topazId != null ? state.baseSummaryCache.landuse[String(topazId)] : null;
      return landuseComparisonFillColor(mode, row, baseRow);
    }
    return landuseFillColor(mode, row);
  }

  function soilsFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    if (mode === 'dominant') {
      const key = row.mukey;
      if (!key) return [128, 128, 128, 200];
      const hash = [...String(key)].reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) >>> 0, 0);
      const r = (hash & 0xff0000) >> 16;
      const g = (hash & 0x00ff00) >> 8;
      const b = hash & 0x0000ff;
      return [r, g, b, 200];
    }
    const v = Number(row[mode]);
    const normalized = normalizeModeValue(mode, v);
    if (!Number.isFinite(normalized)) return [128, 128, 128, 200];
    const palette = resolveColormapName(mode, 'Soils', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function hillslopesFillColor(mode, row) {
    if (!row) return [128, 128, 128, 200];
    const v = Number(row[mode]);
    if (!Number.isFinite(v)) return [128, 128, 128, 200];
    let normalized = 0.5;
    if (mode === 'slope_scalar') {
      normalized = Math.min(1, Math.max(0, v));
    } else if (mode === 'length') {
      normalized = Math.min(1, Math.max(0, v / 1000));
    } else if (mode === 'aspect') {
      normalized = Math.min(1, Math.max(0, v / 360));
    }
    return viridisColor(normalized);
  }

  function watarFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.watarRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    return jet2Color(normalized);
  }

  function weppFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    }
    if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  function weppComparisonFillColor(mode, scenarioRow, baseRow) {
    const state = getState();
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const range = state.comparisonDiffRanges[mode] || { min: -100, max: 100 };
    const normalized = Math.min(1, Math.max(0, (diff - range.min) / (range.max - range.min || 1)));
    return rdbuScale(normalized);
  }

  function weppYearlyFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppYearlyRanges[mode] || { min: 0, max: 100 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    if (WATER_MEASURES.includes(mode)) {
      return winterColor(normalized);
    }
    if (SOIL_MEASURES.includes(mode)) {
      return jet2Color(normalized);
    }
    return viridisColor(normalized);
  }

  function weppYearlyComparisonFillColor(mode, scenarioRow, baseRow) {
    const state = getState();
    if (!scenarioRow || !baseRow) return [128, 128, 128, 200];
    const scenarioValue = Number(scenarioRow[mode]);
    const baseValue = Number(baseRow[mode]);
    if (!Number.isFinite(scenarioValue) || !Number.isFinite(baseValue)) {
      return [128, 128, 128, 200];
    }
    const diff = baseValue - scenarioValue;
    const range = state.weppYearlyDiffRanges[mode] || { min: -100, max: 100 };
    const normalized = Math.min(1, Math.max(0, (diff - range.min) / (range.max - range.min || 1)));
    return rdbuScale(normalized);
  }

  function weppEventFillColor(mode, row) {
    const state = getState();
    if (!row) return [128, 128, 128, 200];
    const value = Number(row[mode]);
    if (!Number.isFinite(value)) return [128, 128, 128, 200];
    const range = state.weppEventRanges[mode] || { min: 0, max: 1 };
    const normalized = Math.min(1, Math.max(0, (value - range.min) / (range.max - range.min)));
    const palette = resolveColormapName(mode, 'WEPP Event', { WATER_MEASURES, SOIL_MEASURES });
    return colorFromPalette(palette, normalized);
  }

  function rapFillColor(row) {
    const v = rapValue(row);
    if (v === null) return [128, 128, 128, 200];
    const normalized = Math.min(1, Math.max(0, v / 100));
    return winterColor(normalized);
  }

  function buildSubcatchmentLabelsLayer(state) {
    if (!state.subcatchmentLabelsVisible || !state.subcatchmentsVisible || !state.subcatchmentsGeoJson) {
      return [];
    }
    const labelData = [];
    const seenIds = new Set();
    const features = state.subcatchmentsGeoJson.features || [];
    features.forEach((feature) => {
      const props = feature.properties || {};
      const topazId = props.TopazID || props.topaz_id || props.topaz || props.id;
      if (topazId == null) return;
      const idKey = String(topazId);
      if (seenIds.has(idKey)) return;
      seenIds.add(idKey);
      const geom = feature.geometry;
      if (!geom) return;
      let coords = [];
      if (geom.type === 'Polygon' && geom.coordinates && geom.coordinates[0]) {
        coords = geom.coordinates[0];
      } else if (geom.type === 'MultiPolygon' && geom.coordinates && geom.coordinates[0] && geom.coordinates[0][0]) {
        coords = geom.coordinates[0][0];
      }
      if (!coords.length) return;
      let sumX = 0;
      let sumY = 0;
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

  function buildLanduseLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.landuseLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.landuseSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `landuse-${overlay.key}${state.comparisonMode && state.currentScenarioPath && state.baseSummaryCache.landuse && constants.COMPARISON_MEASURES.includes(overlay.mode) ? '-diff' : ''}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.landuseSummary[String(topaz)] : null;
            return landuseColor(overlay.mode, row, topaz);
          },
          updateTriggers: {
            getFillColor: [state.comparisonMode, state.currentScenarioPath, state.comparisonDiffRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildSoilsLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.soilsLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.soilsSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `soils-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.soilsSummary[String(topaz)] : null;
            return soilsFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.graphHighlightedTopazId],
          },
        });
      });
    return activeLayers;
  }

  function buildHillslopesLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.hillslopesLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.hillslopesSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `hillslopes-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.hillslopesSummary[String(topaz)] : null;
            return hillslopesFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function buildWatarLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.watarLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.watarSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `watar-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.watarSummary[String(topaz)] : null;
            return watarFillColor(overlay.mode, row);
          },
        });
      });
    return activeLayers;
  }

  function buildWeppLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.weppLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.weppSummary)
      .map((overlay) => {
        const useComparison =
          state.comparisonMode &&
          state.currentScenarioPath &&
          constants.COMPARISON_MEASURES.includes(overlay.mode) &&
          state.baseSummaryCache.wepp;
        return new deck.GeoJsonLayer({
          id: `wepp-${overlay.key}${useComparison ? '-diff' : ''}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.weppSummary[String(topaz)] : null;
            if (useComparison) {
              const baseRow = topaz != null ? state.baseSummaryCache.wepp[String(topaz)] : null;
              return weppComparisonFillColor(overlay.mode, row, baseRow);
            }
            return weppFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.comparisonMode, state.currentScenarioPath, state.comparisonDiffRanges[overlay.mode], state.weppStatistic],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppYearlyLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.weppYearlyLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.weppYearlySummary)
      .map((overlay) => {
        const useComparison =
          state.comparisonMode &&
          state.currentScenarioPath &&
          constants.COMPARISON_MEASURES.includes(overlay.mode) &&
          state.baseWeppYearlyCache[state.weppYearlySelectedYear];
        return new deck.GeoJsonLayer({
          id: `wepp-yearly-${overlay.key}${useComparison ? '-diff' : ''}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.weppYearlySummary[String(topaz)] : null;
            if (useComparison) {
              const baseSummary = state.baseWeppYearlyCache[state.weppYearlySelectedYear] || {};
              const baseRow = topaz != null ? baseSummary[String(topaz)] : null;
              return weppYearlyComparisonFillColor(overlay.mode, row, baseRow);
            }
            return weppYearlyFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.comparisonMode, state.currentScenarioPath, state.weppYearlySelectedYear, state.weppYearlyRanges[overlay.mode]],
          },
        });
      });
    return activeLayers;
  }

  function buildWeppEventLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    const activeLayers = state.weppEventLayers
      .filter((l) => l.visible && state.subcatchmentsGeoJson && state.weppEventSummary)
      .map((overlay) => {
        return new deck.GeoJsonLayer({
          id: `wepp-event-${overlay.key}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.weppEventSummary[String(topaz)] : null;
            return weppEventFillColor(overlay.mode, row);
          },
          updateTriggers: {
            getFillColor: [state.weppEventSelectedDate],
          },
        });
      });
    return activeLayers;
  }

  function buildRapLayers(state) {
    if (!state.subcatchmentsVisible) return [];
    if (!state.rapSummary) return [];
    if (state.rapCumulativeMode) {
      const selectedBands = state.rapLayers.filter((l) => l.selected !== false);
      const bandIds = selectedBands.map((l) => l.bandId).join(',');
      return [
        new deck.GeoJsonLayer({
          id: `rap-cumulative-${bandIds}`,
          data: state.subcatchmentsGeoJson,
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
            const row = topaz != null ? state.rapSummary[String(topaz)] : null;
            if (state.graphHighlightedTopazId && String(topaz) === String(state.graphHighlightedTopazId)) {
              return [255, 200, 0, 255];
            }
            return rapFillColor(row);
          },
          getLineColor: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (state.graphHighlightedTopazId && String(topaz) === String(state.graphHighlightedTopazId)) {
              return [255, 200, 0, 255];
            }
            return [0, 0, 0, 0];
          },
          getLineWidth: (f) => {
            const props = f && f.properties;
            const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
            if (state.graphHighlightedTopazId && String(topaz) === String(state.graphHighlightedTopazId)) {
              return 3;
            }
            return 0;
          },
          lineWidthUnits: 'pixels',
          updateTriggers: {
            getFillColor: [state.rapSelectedYear, bandIds, state.graphHighlightedTopazId],
            getLineColor: [state.graphHighlightedTopazId],
            getLineWidth: [state.graphHighlightedTopazId],
          },
        }),
      ];
    }

    const activeLayer = pickActive(state.rapLayers);
    if (!activeLayer) return [];
    return [
      new deck.GeoJsonLayer({
        id: `rap-${activeLayer.key}`,
        data: state.subcatchmentsGeoJson,
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
          const row = topaz != null ? state.rapSummary[String(topaz)] : null;
          return rapFillColor(row);
        },
        getLineColor: (f) => {
          const props = f && f.properties;
          const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
          if (state.graphHighlightedTopazId && String(topaz) === String(state.graphHighlightedTopazId)) {
            return [255, 200, 0, 255];
          }
          return [0, 0, 0, 0];
        },
        getLineWidth: (f) => {
          const props = f && f.properties;
          const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
          if (state.graphHighlightedTopazId && String(topaz) === String(state.graphHighlightedTopazId)) {
            return 3;
          }
          return 0;
        },
        lineWidthUnits: 'pixels',
        updateTriggers: {
          getFillColor: [state.rapSelectedYear, activeLayer.bandId],
          getLineColor: [state.graphHighlightedTopazId],
          getLineWidth: [state.graphHighlightedTopazId],
        },
      }),
    ];
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

  function buildRasterLayers(state) {
    return state.detectedLayers
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
  }

  function buildLayerStack(baseLayer) {
    const state = getState();
    const rasterLayers = buildRasterLayers(state);
    const landuseDeckLayers = buildLanduseLayers(state);
    const soilsDeckLayers = buildSoilsLayers(state);
    const hillslopesDeckLayers = buildHillslopesLayers(state);
    const watarDeckLayers = buildWatarLayers(state);
    const weppDeckLayers = buildWeppLayers(state);
    const weppYearlyDeckLayers = buildWeppYearlyLayers(state);
    const weppEventDeckLayers = buildWeppEventLayers(state);
    const rapDeckLayers = buildRapLayers(state);
    const labelLayers = buildSubcatchmentLabelsLayer(state);
    return [
      baseLayer,
      ...landuseDeckLayers,
      ...soilsDeckLayers,
      ...hillslopesDeckLayers,
      ...watarDeckLayers,
      ...weppDeckLayers,
      ...weppYearlyDeckLayers,
      ...weppEventDeckLayers,
      ...rapDeckLayers,
      ...rasterLayers,
      ...labelLayers,
    ];
  }

  function formatTooltip(info) {
    const state = getState();
    if (!info) return null;
    const luOverlay = pickActive(state.landuseLayers);
    if (info.object && luOverlay && state.landuseSummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.landuseSummary[String(topaz)] : null;
      const val = landuseValue(luOverlay.mode, row);
      if (val !== null) {
        const label =
          luOverlay.mode === 'dominant'
            ? `Landuse: ${val}`
            : `${luOverlay.mode}: ${typeof val === 'number' ? val.toFixed(3) : val}`;
        return `Layer: ${luOverlay.path}\nTopazID: ${topaz}\n${label}`;
      }
    }
    const soilOverlay = pickActive(state.soilsLayers);
    if (info.object && soilOverlay && state.soilsSummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.soilsSummary[String(topaz)] : null;
      const val = soilsValue(soilOverlay.mode, row);
      if (val !== null) {
        let label;
        if (soilOverlay.mode === 'dominant') {
          label = `Soil: ${val}`;
        } else if (soilOverlay.mode === 'bd') {
          label = `Bulk density: ${typeof val === 'number' ? val.toFixed(2) : val} g/cm³`;
        } else if (soilOverlay.mode === 'soil_depth') {
          label = `Soil depth: ${typeof val === 'number' ? val.toFixed(0) : val} mm`;
        } else {
          label = `${soilOverlay.mode}: ${typeof val === 'number' ? val.toFixed(1) : val}%`;
        }
        return `Layer: ${soilOverlay.path}\nTopazID: ${topaz}\n${label}`;
      }
    }
    const hillslopesOverlay = pickActive(state.hillslopesLayers);
    if (info.object && hillslopesOverlay && state.hillslopesSummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.hillslopesSummary[String(topaz)] : null;
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
    const watarOverlay = pickActive(state.watarLayers);
    if (info.object && watarOverlay && state.watarSummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.watarSummary[String(topaz)] : null;
      const val = watarValue(watarOverlay.mode, row);
      if (val !== null) {
        const label = `${watarOverlay.label}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
        return `Layer: ${watarOverlay.path}\nTopazID: ${topaz}\n${label}`;
      }
    }
    const weppOverlay = pickActive(state.weppLayers);
    if (info.object && weppOverlay && state.weppSummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.weppSummary[String(topaz)] : null;
      const val = weppValue(weppOverlay.mode, row);
      if (val !== null) {
        let label;
        if (weppOverlay.mode === 'runoff_volume') {
          label = `Runoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
        } else if (weppOverlay.mode === 'subrunoff_volume') {
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
    const weppYearlyOverlay = pickActive(state.weppYearlyLayers);
    if (info.object && weppYearlyOverlay && state.weppYearlySummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.weppYearlySummary[String(topaz)] : null;
      const val = weppYearlyValue(weppYearlyOverlay.mode, row);
      if (val !== null) {
        let label;
        if (weppYearlyOverlay.mode === 'runoff_volume') {
          label = `Runoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
        } else if (weppYearlyOverlay.mode === 'subrunoff_volume') {
          label = `Subrunoff: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
        } else if (weppYearlyOverlay.mode === 'baseflow_volume') {
          label = `Baseflow: ${typeof val === 'number' ? val.toFixed(1) : val} mm`;
        } else if (weppYearlyOverlay.mode === 'soil_loss') {
          label = `Soil Loss: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
        } else if (weppYearlyOverlay.mode === 'sediment_deposition') {
          label = `Sed. Deposition: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
        } else if (weppYearlyOverlay.mode === 'sediment_yield') {
          label = `Sed. Yield: ${typeof val === 'number' ? val.toFixed(2) : val} tonnes/ha`;
        } else {
          label = `${weppYearlyOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
        }
        const yearLine = state.weppYearlySelectedYear != null ? `Year: ${state.weppYearlySelectedYear}\n` : '';
        return `Layer: ${weppYearlyOverlay.path}\n${yearLine}TopazID: ${topaz}\n${label}`;
      }
    }
    const weppEventOverlay = pickActive(state.weppEventLayers);
    if (info.object && weppEventOverlay && state.weppEventSummary) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.weppEventSummary[String(topaz)] : null;
      const val = weppEventValue(weppEventOverlay.mode, row);
      if (val !== null) {
        let label;
        if (weppEventOverlay.mode === 'event_P') {
          label = `Precipitation: ${typeof val === 'number' ? val.toFixed(2) : val} mm`;
        } else if (weppEventOverlay.mode === 'event_Q') {
          label = `Runoff: ${typeof val === 'number' ? val.toFixed(2) : val} mm`;
        } else if (weppEventOverlay.mode === 'event_ET') {
          label = `Total ET: ${typeof val === 'number' ? val.toFixed(2) : val} mm`;
        } else if (weppEventOverlay.mode === 'event_peakro') {
          label = `Peak Runoff Rate: ${typeof val === 'number' ? val.toFixed(4) : val} m³/s`;
        } else if (weppEventOverlay.mode === 'event_tdet') {
          label = `Total Detachment: ${typeof val === 'number' ? val.toFixed(2) : val} kg`;
        } else {
          label = `${weppEventOverlay.mode}: ${typeof val === 'number' ? val.toFixed(2) : val}`;
        }
        return `Layer: ${weppEventOverlay.path}\nDate: ${state.weppEventSelectedDate}\nTopazID: ${topaz}\n${label}`;
      }
    }
    if (info.object && state.rapSummary && (state.rapCumulativeMode || pickActive(state.rapLayers))) {
      const props = info.object && info.object.properties;
      const topaz = props && (props.TopazID || props.topaz_id || props.topaz || props.id);
      const row = topaz != null ? state.rapSummary[String(topaz)] : null;
      const val = rapValue(row);
      if (val !== null) {
        if (state.rapCumulativeMode) {
          const selectedBands = state.rapLayers.filter((l) => l.selected !== false);
          const bandNames = selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join(' + ');
          const label = `Cumulative (${bandNames}): ${typeof val === 'number' ? val.toFixed(1) : val}%`;
          return `Layer: Cumulative Cover\nYear: ${state.rapSelectedYear}\nTopazID: ${topaz}\n${label}`;
        }
        const rapOverlay = pickActive(state.rapLayers);
        const bandLabel = RAP_BAND_LABELS[rapOverlay.bandKey] || rapOverlay.bandKey;
        const label = `${bandLabel}: ${typeof val === 'number' ? val.toFixed(1) : val}%`;
        return `Layer: ${rapOverlay.path}\nYear: ${state.rapSelectedYear}\nTopazID: ${topaz}\n${label}`;
      }
    }
    const rasterLayer = pickActive(state.detectedLayers);
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
  }

  function pickActiveLayerForLegend(category, state) {
    const layersByCategory = {
      Landuse: state.landuseLayers,
      Soils: state.soilsLayers,
      Watershed: state.hillslopesLayers,
      RAP: state.rapLayers,
      WEPP: state.weppLayers,
      'WEPP Yearly': state.weppYearlyLayers,
      'WEPP Event': state.weppEventLayers,
      WATAR: state.watarLayers,
      Raster: state.detectedLayers,
    };
    const layers = layersByCategory[category] || [];
    const layer = pickActive(layers);
    if (!layer) return null;
    return { ...layer, category };
  }

  function getActiveLayersForLegend() {
    const state = getState();
    const active = [];
    if (state.subcatchmentsVisible) {
      const landuse = pickActiveLayerForLegend('Landuse', state);
      if (landuse) active.push(landuse);
      const soils = pickActiveLayerForLegend('Soils', state);
      if (soils) active.push(soils);
      const hills = pickActiveLayerForLegend('Watershed', state);
      if (hills) active.push(hills);
      if (state.rapCumulativeMode) {
        const selectedBands = state.rapLayers.filter((l) => l.selected !== false);
        const bandNames = selectedBands.map((l) => RAP_BAND_LABELS[l.bandKey] || l.bandKey).join(' + ');
        active.push({
          key: 'rap-cumulative',
          label: `Cumulative Cover (${bandNames})`,
          category: 'RAP',
          isCumulative: true,
        });
      } else {
        const rap = pickActiveLayerForLegend('RAP', state);
        if (rap) active.push(rap);
      }
      const wepp = pickActiveLayerForLegend('WEPP', state);
      if (wepp) active.push(wepp);
      const weppYearly = pickActiveLayerForLegend('WEPP Yearly', state);
      if (weppYearly) active.push(weppYearly);
      const weppEvent = pickActiveLayerForLegend('WEPP Event', state);
      if (weppEvent) active.push(weppEvent);
      const watar = pickActiveLayerForLegend('WATAR', state);
      if (watar) active.push(watar);
    }
    state.detectedLayers.forEach((layer) => {
      if (layer.visible) {
        active.push({ ...layer, category: 'Raster' });
      }
    });
    return active;
  }

  return {
    buildLayerStack,
    formatTooltip,
    getActiveLayersForLegend,
    constants: { NLCD_COLORMAP, NLCD_LABELS, RAP_BAND_LABELS },
    helpers: {
      landuseValue,
      soilsValue,
      hillslopesValue,
      watarValue,
      weppValue,
      weppYearlyValue,
      weppEventValue,
      rapValue,
      landuseFillColor: landuseColor,
      soilsFillColor,
      hillslopesFillColor,
      watarFillColor,
      weppFillColor,
      weppYearlyFillColor,
      weppEventFillColor,
      rapFillColor,
      sampleRaster,
    },
  };
}

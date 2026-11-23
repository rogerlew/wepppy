import { DASHBOARD_MODES } from '../batch-keys.js';
import { landuseValue, soilsValue, modeValue, scalarValue, weppEventValue, pickActive, resolveFeatureIdentity } from './layer-values.js';

function buildTooltipTopazLines(identity, state) {
  if (!identity || identity.topazId == null) return '';
  if (state && state.dashboardMode === DASHBOARD_MODES.BATCH) {
    const runLine = identity.runLabel ? `Run: ${identity.runLabel}\n` : '';
    return `${runLine}TOPAZ ID: ${identity.topazId}\n`;
  }
  return `TOPAZ ID: ${identity.topazId}\n`;
}

function landuseLabel(overlay, val) {
  return overlay.mode === 'dominant'
    ? `Landuse: ${val}`
    : `${overlay.mode}: ${val.toFixed(3)}`;
}

function soilsLabel(overlay, val) {
  switch (overlay.mode) {
    case 'dominant':
      return `Soil: ${val}`;
    case 'bd':
      return `Bulk density: ${val.toFixed(2)} g/cm³`;
    case 'soil_depth':
      return `Soil depth: ${val.toFixed(0)} mm`;
    default:
      return `${overlay.mode}: ${val.toFixed(1)}%`;
  }
}

function hillslopesLabel(overlay, val) {
  switch (overlay.mode) {
    case 'slope_scalar':
      return `Slope: ${(val * 100).toFixed(1)}%`;
    case 'length':
      return `Length: ${val.toFixed(1)} m`;
    case 'aspect':
      return `Aspect: ${val.toFixed(0)}°`;
    default:
      return `${overlay.mode}: ${val.toFixed(2)}`;
  }
}

function watarLabel(overlay, val) {
  return `${overlay.label}: ${val.toFixed(2)}`;
}

function weppLabel(overlay, val) {
  switch (overlay.mode) {
    case 'runoff_volume':
      return `Runoff: ${val.toFixed(1)} mm`;
    case 'subrunoff_volume':
      return `Subrunoff: ${val.toFixed(1)} mm`;
    case 'baseflow_volume':
      return `Baseflow: ${val.toFixed(1)} mm`;
    case 'soil_loss':
      return `Soil Loss: ${val.toFixed(2)} tonnes/ha`;
    case 'sediment_deposition':
      return `Sed. Deposition: ${val.toFixed(2)} tonnes/ha`;
    case 'sediment_yield':
      return `Sed. Yield: ${val.toFixed(2)} tonnes/ha`;
    default:
      return `${overlay.mode}: ${val.toFixed(2)}`;
  }
}

function channelLabel(overlay, val) {
  switch (overlay.mode) {
    case 'channel_discharge_volume':
      return `Discharge Volume: ${val.toFixed(2)} m^3`;
    case 'channel_soil_loss':
      return `Soil Loss: ${val.toFixed(2)} kg`;
    default:
      return `${overlay.mode}: ${val.toFixed(2)}`;
  }
}

function eventLabel(overlay, val) {
  switch (overlay.mode) {
    case 'event_P':
      return `Precipitation: ${val.toFixed(2)} mm`;
    case 'event_Q':
      return `Runoff: ${val.toFixed(2)} mm`;
    case 'event_ET':
      return `Total ET: ${val.toFixed(2)} mm`;
    case 'event_Saturation':
      return `Saturation: ${val.toFixed(2)}%`;
    case 'event_peakro':
      return `Peak Runoff Rate: ${val.toFixed(4)} m³/s`;
    case 'event_tdet':
      return `Total Detachment: ${val.toFixed(2)} kg`;
    default:
      return `${overlay.mode}: ${val.toFixed(2)}`;
  }
}

// Earlier entries win when several overlays can describe the same feature.
const featureSources = [
  { key: 'landuse', read: landuseValue, label: landuseLabel },
  { key: 'soils', read: soilsValue, label: soilsLabel },
  { key: 'hillslopes', read: modeValue, label: hillslopesLabel },
  { key: 'watar', read: modeValue, label: watarLabel },
  { key: 'wepp', read: modeValue, label: weppLabel },
  { key: 'weppYearlyChannel', read: modeValue, label: channelLabel, yearly: true },
  { key: 'weppChannel', read: modeValue, label: channelLabel },
  { key: 'weppYearly', read: modeValue, label: weppLabel, yearly: true },
  { key: 'weppEvent', read: weppEventValue, label: eventLabel },
];

function summaryRow(summary, identity) {
  return identity.key != null ? summary[String(identity.key)] : null;
}

function openetTooltip(state, properties) {
  const overlay = pickActive(state.openetLayers);
  if (!overlay || !state.openetSummary) return null;
  const identity = resolveFeatureIdentity(properties, state);
  const value = scalarValue(summaryRow(state.openetSummary, identity));
  if (value === null) return null;
  const topazLines = buildTooltipTopazLines(identity, state);
  const months = state.openetMetadata?.months;
  const index = state.openetSelectedMonthIndex;
  const month = Array.isArray(months) && Number.isFinite(index) ? months[index] : null;
  const monthLine = month?.label ? `Month: ${month.label}\n` : '';
  const dataset = overlay.datasetKey || overlay.label || 'OpenET';
  return `Layer: OpenET (${dataset})\n${monthLine}${topazLines}ET: ${value.toFixed(2)} mm`;
}

function rapTooltip(state, properties, bandLabels) {
  if (!state.rapSummary) return null;
  const overlay = state.rapCumulativeMode ? null : pickActive(state.rapLayers);
  if (!overlay && !state.rapCumulativeMode) return null;
  const identity = resolveFeatureIdentity(properties, state);
  const value = scalarValue(summaryRow(state.rapSummary, identity));
  if (value === null) return null;
  const topazLines = buildTooltipTopazLines(identity, state);
  const bandName = (layer) => bandLabels[layer.bandKey] || layer.bandKey;
  const prefix = `Year: ${state.rapSelectedYear}\n${topazLines}`;
  if (state.rapCumulativeMode) {
    const bands = state.rapLayers.filter((layer) => layer.selected !== false).map(bandName).join(' + ');
    return `Layer: Cumulative Cover\n${prefix}Cumulative (${bands}): ${value.toFixed(1)}%`;
  }
  return `Layer: ${overlay.path}\n${prefix}${bandName(overlay)}: ${value.toFixed(1)}%`;
}

function featureTooltip(state, properties, bandLabels) {
  for (const source of featureSources) {
    const overlay = pickActive(state[`${source.key}Layers`] || []);
    const summary = state[`${source.key}Summary`];
    if (!overlay || !summary) continue;
    const identity = resolveFeatureIdentity(properties, state);
    const row = summaryRow(summary, identity);
    const value = source.read(overlay.mode, row);
    if (value === null) continue;
    const topazLines = buildTooltipTopazLines(identity, state);
    let timeLine = '';
    if (source.yearly && state.weppYearlySelectedYear != null) {
      timeLine = `Year: ${state.weppYearlySelectedYear}\n`;
    } else if (source.key === 'weppEvent') {
      timeLine = `Date: ${state.weppEventSelectedDate}\n`;
    }
    return `Layer: ${overlay.path}\n${timeLine}${topazLines}${source.label(overlay, value)}`;
  }
  return openetTooltip(state, properties) ?? rapTooltip(state, properties, bandLabels);
}

export function formatLayerTooltip(info, state, bandLabels, sampleRaster) {
  if (!info) return null;
  if (info.object) {
    const tooltip = featureTooltip(state, info.object.properties, bandLabels);
    if (tooltip !== null) return tooltip;
  }
  const raster = pickActive(state.detectedLayers);
  if (info.coordinate && raster) {
    const value = sampleRaster(raster, info.coordinate);
    if (value !== null) return `Layer: ${raster.path}\nValue: ${value}`;
  }
  return info.tile ? `Tile z${info.tile.z}` : null;
}

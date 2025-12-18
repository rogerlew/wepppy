/**
 * Configuration and static constants for gl-dashboard.
 * Pure exports: no DOM/deck usage. Safe to import in workers or tests.
 */

/**
 * @typedef {'minimized' | 'split' | 'full'} GraphMode
 */

/**
 * @enum {GraphMode}
 */
export const GRAPH_MODES = Object.freeze({
  MINIMIZED: 'minimized',
  SPLIT: 'split',
  FULL: 'full',
});

/**
 * @typedef {'top' | 'bottom' | 'hide' | 'inherit'} GraphSliderPlacement
 */

/**
 * @enum {GraphSliderPlacement}
 */
export const GRAPH_SLIDER_PLACEMENTS = Object.freeze({
  TOP: 'top',
  BOTTOM: 'bottom',
  HIDE: 'hide',
  INHERIT: 'inherit',
});

/**
 * @enum {'climate_yearly' | 'wepp_yearly' | 'rap' | 'cumulative' | 'omni' | 'default'}
 */
export const GRAPH_CONTEXT_KEYS = Object.freeze({
  CLIMATE_YEARLY: 'climate_yearly',
  WEPP_YEARLY: 'wepp_yearly',
  RAP: 'rap',
  CUMULATIVE: 'cumulative',
  OMNI: 'omni',
  DEFAULT: 'default',
});

/**
 * @typedef {typeof GRAPH_CONTEXT_KEYS[keyof typeof GRAPH_CONTEXT_KEYS]} GraphContextKey
 */

/**
 * @enum {'layer' | 'climate'}
 */
export const YEAR_SLIDER_CONTEXTS = Object.freeze({
  LAYER: 'layer',
  CLIMATE: 'climate',
});

/**
 * @typedef {typeof YEAR_SLIDER_CONTEXTS[keyof typeof YEAR_SLIDER_CONTEXTS]} YearSliderContext
 */

export const COMPARISON_MEASURES = [
  'cancov',
  'inrcov',
  'rilcov',
  'runoff_volume',
  'subrunoff_volume',
  'baseflow_volume',
  'soil_loss',
  'sediment_deposition',
  'sediment_yield',
  'event_P',
  'event_Q',
  'event_ET',
  'event_peakro',
  'event_tdet',
];

export const WATER_MEASURES = [
  'runoff_volume',
  'subrunoff_volume',
  'baseflow_volume',
  'event_P',
  'event_Q',
  'event_ET',
  'event_peakro',
];

export const SOIL_MEASURES = [
  'soil_loss',
  'sediment_deposition',
  'sediment_yield',
  'event_tdet',
];

export const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const DEFAULT_GRAPH_PADDING = { top: 32, right: 160, bottom: 80, left: 100 };

export const CUMULATIVE_MEASURE_OPTIONS = [
  { key: 'runoff_volume', label: 'Runoff (m³)' },
  { key: 'subrunoff_volume', label: 'Lateral Flow (m³)' },
  { key: 'baseflow_volume', label: 'Baseflow (m³)' },
  { key: 'soil_loss', label: 'Soil Loss (t)' },
  { key: 'sediment_deposition', label: 'Sed Deposition (t)' },
  { key: 'sediment_yield', label: 'Sed Yield (t)' },
];

export const NLCD_COLORMAP = {
  11: '#5475A8',
  12: '#ffffff',
  21: '#e6d6d6',
  22: '#ccb1b1',
  23: '#ff0000',
  24: '#b50000',
  31: '#d2cdc0',
  41: '#85c77e',
  42: '#38814e',
  43: '#d4e7b0',
  51: '#af963c',
  52: '#dcca8f',
  71: '#fde9aa',
  72: '#d1d182',
  73: '#a3cc51',
  74: '#82ba9e',
  81: '#fbf65d',
  82: '#ca9146',
  90: '#c8e6f8',
  95: '#64b3d5',
};

export const NLCD_LABELS = {
  11: 'Open Water',
  12: 'Perennial Ice/Snow',
  21: 'Developed, Open Space',
  22: 'Developed, Low Intensity',
  23: 'Developed, Medium Intensity',
  24: 'Developed, High Intensity',
  31: 'Barren Land',
  41: 'Deciduous Forest',
  42: 'Evergreen Forest',
  43: 'Mixed Forest',
  51: 'Dwarf Scrub',
  52: 'Shrub/Scrub',
  71: 'Grassland/Herbaceous',
  72: 'Sedge/Herbaceous',
  73: 'Lichens',
  74: 'Moss',
  81: 'Pasture/Hay',
  82: 'Cultivated Crops',
  90: 'Woody Wetlands',
  95: 'Emergent Herbaceous Wetlands',
};

export const RAP_BAND_LABELS = {
  annual_forb_grass: 'Annual Forb & Grass',
  bare_ground: 'Bare Ground',
  litter: 'Litter',
  perennial_forb_grass: 'Perennial Forb & Grass',
  shrub: 'Shrub',
  tree: 'Tree',
};

export const DEFAULT_CONTROLLER_OPTIONS = {
  dragPan: true,
  dragRotate: false,
  scrollZoom: true,
  touchZoom: true,
  touchRotate: false,
  doubleClickZoom: true,
  keyboard: true,
};

export const BASE_LAYER_DEFS = [
  {
    key: 'landuse',
    label: 'Landuse (nlcd.tif)',
    paths: ['landuse/nlcd.tif'],
  },
  {
    key: 'soils',
    label: 'Soils (ssurgo.tif)',
    paths: ['soils/ssurgo.tif'],
  },
];

export const LAYER_REGISTRY = {
  landuse: { key: 'landuse', label: 'Landuse' },
  soils: { key: 'soils', label: 'Soils' },
  rap: { key: 'rap', label: 'RAP' },
  wepp: { key: 'wepp', label: 'WEPP' },
  wepp_yearly: { key: 'wepp_yearly', label: 'WEPP Yearly' },
  wepp_event: { key: 'wepp_event', label: 'WEPP Event' },
  watar: { key: 'watar', label: 'WATAR' },
};

export const GRAPH_DEFS = [
  {
    key: 'climate',
    title: 'Climate Yearly',
    items: [{ key: 'climate-yearly', label: 'Climate Yearly (precip + temp)', type: 'line' }],
  },
  {
    key: 'cumulative',
    title: 'Cumulative Contribution',
    items: [{ key: 'cumulative-contribution', label: 'Cumulative contribution curve', type: 'line' }],
  },
  {
    key: 'omni',
    title: 'Omni Scenarios',
    items: [
      { key: 'omni-soil-loss-hill', label: 'Soil Loss (hillslopes, tonne/ha)', type: 'boxplot' },
      { key: 'omni-soil-loss-chn', label: 'Soil Loss (channels, tonne)', type: 'boxplot' },
      { key: 'omni-runoff-hill', label: 'Runoff (hillslopes, mm)', type: 'boxplot' },
      { key: 'omni-outlet-sediment', label: 'Sediment discharge (tonne/ha)', type: 'bars' },
      { key: 'omni-outlet-stream', label: 'Stream discharge (mm)', type: 'bars' },
    ],
  },
];

export function createColorScales(colormapFn) {
  const makeScale = (name) => {
    if (typeof colormapFn === 'function') {
      try {
        return colormapFn({ colormap: name, nshades: 256, format: 'rgba' });
      } catch (err) {
        return null;
      }
    }
    return null;
  };

  return {
    viridisScale: makeScale('viridis'),
    rdbuScale: makeScale('rdbu'),
    winterScale: makeScale('winter'),
    jet2Scale: makeScale('jet2'),
  };
}

export function createBasemapDefs() {
  const GOOGLE_SUBDOMAINS = ['mt0', 'mt1', 'mt2', 'mt3'];
  let subdomainIndex = 0;

  function nextGoogleSubdomain() {
    const sub = GOOGLE_SUBDOMAINS[subdomainIndex % GOOGLE_SUBDOMAINS.length];
    subdomainIndex += 1;
    return sub;
  }

  const basemapDefs = {
    osm: {
      label: 'OpenStreetMap',
      template: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
      getUrl(x, y, z) {
        return this.template.replace('{x}', String(x)).replace('{y}', String(y)).replace('{z}', String(z));
      },
    },
    googleTerrain: {
      label: 'Google Terrain',
      template: 'https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
      getUrl(x, y, z) {
        const sub = nextGoogleSubdomain();
        return this.template
          .replace('{s}', sub)
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      },
    },
    googleSatellite: {
      label: 'Google Satellite',
      template: 'https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
      getUrl(x, y, z) {
        const sub = nextGoogleSubdomain();
        return this.template
          .replace('{s}', sub)
          .replace('{x}', String(x))
          .replace('{y}', String(y))
          .replace('{z}', String(z));
      },
    },
  };

  return { basemapDefs, nextGoogleSubdomain };
}

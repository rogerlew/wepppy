// Configuration and static constants for the gl-dashboard bundle.
// Keep this module free of DOM access so it can be imported in workers or tests.

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

export const DEFAULT_GRAPH_PADDING = { top: 32, right: 160, bottom: 80, left: 100 };

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

export function buildLayerSections(state) {
  const {
    landuseLayers = [],
    soilsLayers = [],
    hillslopesLayers = [],
    d8DirectionLayer,
    channelsLayers = [],
    weppLayers = [],
    weppChannelLayers = [],
    weppYearlyLayers = [],
    weppYearlyChannelLayers = [],
    weppEventLayers = [],
    watarLayers = [],
    rapLayers = [],
    openetLayers = [],
    detectedLayers = [],
  } = state;
  const subcatchmentSections = [];

  const landuseRasters = detectedLayers
    .filter((l) => l.key === 'landuse' || l.key === 'sbs')
    .map((r) => ({ ...r, isRaster: true, rasterRef: r }));
  const soilsRasters = detectedLayers
    .filter((l) => l.key === 'soils')
    .map((r) => ({ ...r, isRaster: true, rasterRef: r }));
  const rusleRasters = detectedLayers
    .filter((l) => l && (l.group === 'rusle' || (typeof l.key === 'string' && l.key.startsWith('rusle-'))))
    .map((r) => ({ ...r, isRaster: true, rasterRef: r }));
  const hillslopesItems = Array.isArray(hillslopesLayers) ? [...hillslopesLayers] : [];
  if (d8DirectionLayer) {
    hillslopesItems.push({
      ...d8DirectionLayer,
      isRaster: true,
      rasterRef: d8DirectionLayer,
    });
  }

  if (landuseLayers.length || landuseRasters.length) {
    subcatchmentSections.push({ title: 'Landuse', items: [...landuseLayers, ...landuseRasters], isSubcatchment: true, stateKey: 'landuseLayers' });
  }
  if (soilsLayers.length || soilsRasters.length) {
    subcatchmentSections.push({ title: 'Soils', items: [...soilsLayers, ...soilsRasters], isSubcatchment: true, stateKey: 'soilsLayers' });
  }
  if (hillslopesItems.length) {
    subcatchmentSections.push({ title: 'Hillslopes', items: hillslopesItems, isSubcatchment: true, stateKey: 'hillslopesLayers' });
  }
  if (channelsLayers.length) {
    subcatchmentSections.push({
      title: 'Channels',
      items: channelsLayers,
      isChannels: true,
      radioGroupName: 'wepp-channel-overlay',
      stateKey: 'channelsLayers',
    });
  }
  if (rapLayers.length) {
    subcatchmentSections.push({ title: 'RAP', items: rapLayers, isSubcatchment: true, isRap: true, stateKey: 'rapLayers' });
  }
  if (openetLayers.length) {
    subcatchmentSections.push({
      title: 'OpenET',
      items: openetLayers,
      isSubcatchment: true,
      isOpenet: true,
      stateKey: 'openetLayers',
    });
  }
  if (weppLayers.length || weppChannelLayers.length) {
    subcatchmentSections.push({
      title: 'WEPP',
      items: weppLayers,
      isSubcatchment: true,
      stateKey: 'weppLayers',
      channelItems: weppChannelLayers,
      channelStateKey: 'weppChannelLayers',
    });
  }
  if (rusleRasters.length) {
    subcatchmentSections.push({
      title: 'RUSLE',
      items: rusleRasters,
      isSubcatchment: true,
    });
  }
  if (weppYearlyLayers.length || weppYearlyChannelLayers.length) {
    subcatchmentSections.push({
      title: 'WEPP Yearly',
      idPrefix: 'WEPP-Yearly',
      items: weppYearlyLayers,
      isSubcatchment: true,
      isWeppYearly: true,
      stateKey: 'weppYearlyLayers',
      channelItems: weppYearlyChannelLayers,
      channelStateKey: 'weppYearlyChannelLayers',
    });
  }
  if (weppEventLayers.length) {
    subcatchmentSections.push({ title: 'WEPP Event', items: weppEventLayers, isSubcatchment: true, isWeppEvent: true, stateKey: 'weppEventLayers' });
  }
  if (watarLayers.length) {
    subcatchmentSections.push({ title: 'WATAR', items: watarLayers, isSubcatchment: true, stateKey: 'watarLayers' });
  }
  return subcatchmentSections;
}

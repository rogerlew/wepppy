import { expect, it } from '@jest/globals';
import { createLayerUtils } from '../map/layers.js';

it('falls through overlapping layers in display order, including valid zeroes', () => {
  const channel = { visible: true, mode: 'channel_soil_loss', path: 'channels' };
  const state = {
    landuseLayers: [], soilsLayers: [], hillslopesLayers: [], watarLayers: [], weppLayers: [],
    weppYearlyChannelLayers: [{ ...channel, path: 'yearly' }], weppChannelLayers: [channel],
    weppYearlyLayers: [], weppEventLayers: [{ visible: true, mode: 'event_Q', path: 'event' }],
    openetLayers: [{ visible: true, datasetKey: 'ensemble' }], detectedLayers: [],
    weppYearlyChannelSummary: { 1: { channel_soil_loss: 1.5 } },
    weppChannelSummary: { 1: { channel_soil_loss: 0 } },
    weppEventSummary: { 1: { event_Q: null } },
    openetSummary: { 1: 0 }, openetMetadata: { months: [{ label: 'June' }] }, openetSelectedMonthIndex: 0,
    weppYearlySelectedYear: 2020, weppEventSelectedDate: '2020-06-01',
  };
  const { formatTooltip } = createLayerUtils({ getState: () => state, constants: {}, colorScales: {} });
  const pick = { object: { properties: { TopazID: 1 } }, tile: { z: 7 } };

  expect(formatTooltip(pick)).toBe('Layer: yearly\nYear: 2020\nTOPAZ ID: 1\nSoil Loss: 1.50 kg');
  state.weppYearlyChannelSummary = {};
  expect(formatTooltip(pick)).toBe('Layer: channels\nTOPAZ ID: 1\nSoil Loss: 0.00 kg');
  state.weppChannelLayers = [];
  expect(formatTooltip(pick)).toBe('Layer: OpenET (ensemble)\nMonth: June\nTOPAZ ID: 1\nET: 0.00 mm');
  state.weppEventSummary[1].event_Q = 0;
  expect(formatTooltip(pick)).toBe('Layer: event\nDate: 2020-06-01\nTOPAZ ID: 1\nRunoff: 0.00 mm');
  state.weppEventLayers = [];
  state.openetLayers = [];
  expect(formatTooltip(pick)).toBe('Tile z7');
});

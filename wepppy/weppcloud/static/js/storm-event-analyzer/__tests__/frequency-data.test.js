import { describe, expect, it } from '@jest/globals';
import {
  alignFrequencyToRecurrence,
  filterIntensityRows,
  filterWeppFrequencyRows,
  parseNoaaFrequencyCsv,
  parseWeppFrequencyCsv,
} from '../data/frequency-data.js';

const WEPP_SAMPLE = `By metric for ARI, 1, 2, 5
10-min intensity (mm/hour): 10, 20, 30
15-min intensity (mm/hour): 8, 16, 24
Storm depth (mm): 5, 6, 7
Storm duration (hours): 1.5, 2.0, 2.5
Date/time: end`;

const NOAA_SAMPLE = `By duration for ARI, 1, 2, 5, 10
10-min: 11, 22, 33, 44
15-min: 9, 18, 27, 36
Date/time: end`;

describe('storm-event-analyzer frequency CSV parsing', () => {
  it('parses WEPP frequency rows and filters intensity metrics', () => {
    const parsed = parseWeppFrequencyCsv(WEPP_SAMPLE);
    expect(parsed.recurrence).toEqual([1, 2, 5]);
    expect(parsed.rows).toHaveLength(4);

    const intensity = filterIntensityRows(parsed.rows, { requireIntensityLabel: true });
    expect(intensity).toHaveLength(2);
    expect(intensity[0].durationMinutes).toBe(10);
    expect(intensity[0].displayLabel).toBe('10-min intensity');
    expect(intensity[1].durationMinutes).toBe(15);
  });

  it('includes depth and duration rows in WEPP frequency output', () => {
    const parsed = parseWeppFrequencyCsv(WEPP_SAMPLE);
    const rows = filterWeppFrequencyRows(parsed.rows);

    expect(rows[0].metricKey).toBe('depth');
    expect(rows[0].displayLabel).toBe('Depth');
    expect(rows[1].metricKey).toBe('duration');
    expect(rows[1].displayLabel).toBe('Duration');
    expect(rows[2].metricKey).toBe('intensity');
  });

  it('parses NOAA frequency rows and aligns to WEPP recurrence', () => {
    const noaaParsed = parseNoaaFrequencyCsv(NOAA_SAMPLE);
    const aligned = alignFrequencyToRecurrence(noaaParsed, [1, 5]);

    expect(aligned.recurrence).toEqual([1, 5]);
    expect(aligned.rows[0].values).toEqual([11, 33]);
    expect(aligned.rows[1].values).toEqual([9, 27]);
  });
});

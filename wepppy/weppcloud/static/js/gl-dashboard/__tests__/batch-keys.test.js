import { describe, expect, it } from '@jest/globals';
import {
  BATCH_FEATURE_KEY_SEPARATOR,
  buildBatchFeatureKey,
  DASHBOARD_MODES,
  getFeatureKeyFromProperties,
} from '../batch-keys.js';

describe('gl-dashboard batch key contract', () => {
  it('builds a deterministic string key from runid and topaz_id', () => {
    const key = buildBatchFeatureKey('batch;;spring-2026;;run-001', 12);
    expect(key).toBe(`batch;;spring-2026;;run-001${BATCH_FEATURE_KEY_SEPARATOR}12`);
    expect(typeof key).toBe('string');
  });

  it('preserves string ids and leading zeros', () => {
    const key = buildBatchFeatureKey('run-alpha', '0012');
    expect(key).toBe(`run-alpha${BATCH_FEATURE_KEY_SEPARATOR}0012`);
  });

  it('throws on missing runid or topaz_id', () => {
    expect(() => buildBatchFeatureKey(null, '1')).toThrow('missing runid');
    expect(() => buildBatchFeatureKey('run-1', undefined)).toThrow('missing topaz_id');
    expect(() => buildBatchFeatureKey('   ', '10')).toThrow('empty runid');
    expect(() => buildBatchFeatureKey('run-1', '   ')).toThrow('empty topaz_id');
  });

  it('prefers explicit feature_key from properties', () => {
    const key = getFeatureKeyFromProperties({
      feature_key: 'batch;;spring-2026;;run-001-33',
      runid: 'ignored',
      TopazID: 99,
    });
    expect(key).toBe('batch;;spring-2026;;run-001-33');
  });

  it('builds key from runid + topaz property variants', () => {
    const fromTopazId = getFeatureKeyFromProperties({ runid: 'run-1', TopazID: 20 });
    expect(fromTopazId).toBe('run-1-20');

    const fromSnake = getFeatureKeyFromProperties({ runid: 'run-2', topaz_id: '21' });
    expect(fromSnake).toBe('run-2-21');

    const fromLegacy = getFeatureKeyFromProperties({ run_id: 'run-3', wepp_id: 22 });
    expect(fromLegacy).toBe('run-3-22');
  });

  it('returns null for non-batch properties unless strict mode is enabled', () => {
    expect(getFeatureKeyFromProperties({ TopazID: 12 })).toBeNull();
    expect(getFeatureKeyFromProperties({ runid: 'run-1' })).toBeNull();
    expect(() => getFeatureKeyFromProperties({ TopazID: 12 }, { strict: true })).toThrow('runid/topaz_id unavailable');
  });

  it('exports additive dashboard modes for run and batch', () => {
    expect(DASHBOARD_MODES).toEqual({ RUN: 'run', BATCH: 'batch' });
  });
});

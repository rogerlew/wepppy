/**
 * Batch-mode key helpers.
 * Contract: feature identity is a string "<runid>-<topaz_id>" and must remain string-safe end-to-end.
 */

export const DASHBOARD_MODES = Object.freeze({
  RUN: 'run',
  BATCH: 'batch',
});

export const BATCH_FEATURE_KEY_SEPARATOR = '-';

function normalizeRequiredPart(value, label) {
  if (value == null) {
    throw new TypeError(`gl-dashboard batch key error: missing ${label}`);
  }
  const normalized = String(value).trim();
  if (!normalized) {
    throw new TypeError(`gl-dashboard batch key error: empty ${label}`);
  }
  return normalized;
}

function resolveTopazId(properties) {
  if (!properties || typeof properties !== 'object') return null;
  return (
    properties.TopazID ||
    properties.topaz_id ||
    properties.topaz ||
    properties.id ||
    properties.WeppID ||
    properties.wepp_id ||
    null
  );
}

export function buildBatchFeatureKey(runid, topazId) {
  const normalizedRunId = normalizeRequiredPart(runid, 'runid');
  const normalizedTopazId = normalizeRequiredPart(topazId, 'topaz_id');
  return `${normalizedRunId}${BATCH_FEATURE_KEY_SEPARATOR}${normalizedTopazId}`;
}

export function getFeatureKeyFromProperties(properties, { strict = false } = {}) {
  if (!properties || typeof properties !== 'object') {
    if (strict) throw new TypeError('gl-dashboard batch key error: missing feature properties');
    return null;
  }

  if (properties.feature_key != null) {
    return normalizeRequiredPart(properties.feature_key, 'feature_key');
  }

  const runid = properties.runid || properties.run_id || null;
  const topazId = resolveTopazId(properties);
  if (runid == null || topazId == null) {
    if (strict) {
      throw new TypeError('gl-dashboard batch key error: runid/topaz_id unavailable in feature properties');
    }
    return null;
  }

  return buildBatchFeatureKey(runid, topazId);
}

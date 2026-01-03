/**
 * Utility helpers for control views that keep paired measurement inputs
 * (metric/imperial) in sync via data attributes.
 */
(function (global) {
  'use strict';

  var UNIT_CONVERTERS = {
    m_to_ft: function (value) { return value * 3.28084; },
    ft_to_m: function (value) { return value / 3.28084; },
    ha_to_ac: function (value) { return value * 2.47105; },
    ac_to_ha: function (value) { return value / 2.47105; },
    mm_to_in: function (value) { return value / 25.4; },
    in_to_mm: function (value) { return value * 25.4; }
  };

  var converterState = new WeakMap();

  function toDatasetKey(key) {
    return key.replace(/-([a-z])/g, function (_, chr) { return chr.toUpperCase(); });
  }

  function parseDataValue(value) {
    if (value === undefined) {
      return undefined;
    }
    if (value === null) {
      return null;
    }
    if (value === 'true') {
      return true;
    }
    if (value === 'false') {
      return false;
    }
    if (value === 'null') {
      return null;
    }
    if (value !== '' && !Number.isNaN(Number(value)) && String(Number(value)) === value) {
      return Number(value);
    }
    if (value && value.charAt(0) === '{' && value.charAt(value.length - 1) === '}') {
      try {
        return JSON.parse(value);
      } catch (err) {
        return value;
      }
    }
    return value;
  }

  function getDataValue(element, key) {
    if (!element) {
      return undefined;
    }
    var datasetKey = toDatasetKey(key);
    if (element.dataset && Object.prototype.hasOwnProperty.call(element.dataset, datasetKey)) {
      return parseDataValue(element.dataset[datasetKey]);
    }
    var attrValue = element.getAttribute('data-' + key.replace(/([A-Z])/g, '-$1').toLowerCase());
    if (attrValue === null) {
      return undefined;
    }
    return parseDataValue(attrValue);
  }

  function getInternalState(element) {
    var state = converterState.get(element);
    if (!state) {
      state = {};
      converterState.set(element, state);
    }
    return state;
  }

  function getInternalFlag(element, key) {
    var state = converterState.get(element);
    if (!state) {
      return undefined;
    }
    return state[key];
  }

  function setInternalFlag(element, key, value) {
    var state = getInternalState(element);
    state[key] = value;
  }

  function getRootNode(root) {
    if (root && typeof root.querySelectorAll === 'function') {
      return root;
    }
    return document;
  }

  function initUnitConverters(root) {
    var rootNode = getRootNode(root);
    var sources = rootNode.querySelectorAll('[data-convert-target][data-convert-func]');

    Array.prototype.forEach.call(sources, function (source) {
      if (getInternalFlag(source, 'unitConverterInit')) {
        return;
      }

      var targetSelector = getDataValue(source, 'convertTarget');
      var converterName = getDataValue(source, 'convertFunc');
      var converter = UNIT_CONVERTERS[converterName];

      if (!targetSelector || typeof converter !== 'function') {
        return;
      }

      var targets = document.querySelectorAll(targetSelector);
      if (!targets.length) {
        return;
      }

      var eventsAttr = getDataValue(source, 'convertEvents');
      var events = (eventsAttr ? String(eventsAttr) : 'input').split(/\s+/).filter(Boolean);
      if (events.length === 0) {
        events = ['input'];
      }

      var decimalsData = getDataValue(source, 'convertDecimals');
      var decimals = null;
      if (decimalsData !== undefined && decimalsData !== null && decimalsData !== '') {
        var parsed = Number(decimalsData);
        if (Number.isFinite(parsed)) {
          decimals = Math.max(0, Math.round(parsed));
        }
      }

      var triggerChangeData = getDataValue(source, 'convertTriggerChange');
      var shouldTriggerChange = triggerChangeData === undefined ? true : Boolean(triggerChangeData);

      var handler = function () {
        if (getInternalFlag(source, 'convertLock')) {
          return;
        }

        var rawValue = parseFloat(source.value);
        if (!Number.isFinite(rawValue)) {
          return;
        }

        var converted = converter(rawValue);
        if (!Number.isFinite(converted)) {
          return;
        }

        var formatted = decimals === null ? converted : Number(converted).toFixed(decimals);

        Array.prototype.forEach.call(targets, function (target) {
          setInternalFlag(target, 'convertLock', true);
          try {
            if ('value' in target) {
              target.value = formatted;
            } else if (target.textContent !== undefined) {
              target.textContent = formatted;
            }
            if (shouldTriggerChange) {
              target.dispatchEvent(new Event('change', { bubbles: true }));
            }
          } finally {
            setInternalFlag(target, 'convertLock', false);
          }
        });
      };

      events.forEach(function (eventName) {
        source.addEventListener(eventName, handler);
      });

      setInternalFlag(source, 'unitConverterInit', true);
    });
  }

  global.WEPP_UNIT_CONVERTERS = UNIT_CONVERTERS;
  global.initUnitConverters = initUnitConverters;
})(window);

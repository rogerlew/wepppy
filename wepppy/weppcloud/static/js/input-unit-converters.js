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

  function initUnitConverters(root) {
    var $root = root ? $(root) : $(document);

    $root.find('[data-convert-target][data-convert-func]').each(function () {
      var $source = $(this);
      if ($source.data('unitConverterInit')) {
        return;
      }

      var targetSelector = $source.data('convertTarget');
      var converterName = $source.data('convertFunc');
      var converter = UNIT_CONVERTERS[converterName];

      if (!targetSelector || typeof converter !== 'function') {
        return;
      }

      var $target = $(targetSelector);
      if ($target.length === 0) {
        return;
      }

      var eventsAttr = $source.data('convertEvents');
      var events = (eventsAttr ? String(eventsAttr) : 'input').split(/\s+/).filter(Boolean);
      if (events.length === 0) {
        events = ['input'];
      }

      var decimalsData = $source.data('convertDecimals');
      var decimals = null;
      if (decimalsData !== undefined && decimalsData !== null && decimalsData !== '') {
        var parsed = Number(decimalsData);
        if (Number.isFinite(parsed)) {
          decimals = Math.max(0, Math.round(parsed));
        }
      }

      var triggerChangeData = $source.data('convertTriggerChange');
      var shouldTriggerChange = triggerChangeData === undefined ? true : Boolean(triggerChangeData);

      var handler = function () {
        if ($source.data('convertLock')) {
          return;
        }

        var rawValue = parseFloat($source.val());
        if (!Number.isFinite(rawValue)) {
          return;
        }

        var converted = converter(rawValue);
        if (!Number.isFinite(converted)) {
          return;
        }

        var formatted = decimals === null ? converted : Number(converted).toFixed(decimals);

        $target.data('convertLock', true);
        try {
          $target.val(formatted);
          if (shouldTriggerChange) {
            $target.trigger('change');
          }
        } finally {
          $target.data('convertLock', false);
        }
      };

      events.forEach(function (eventName) {
        $source.on(eventName, handler);
      });

      $source.data('unitConverterInit', true);
    });
  }

  global.WEPP_UNIT_CONVERTERS = UNIT_CONVERTERS;
  global.initUnitConverters = initUnitConverters;
})(window);

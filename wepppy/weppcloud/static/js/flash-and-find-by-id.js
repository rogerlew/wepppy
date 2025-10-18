/**
 * Utility helpers to locate and highlight channel/subcatchment features by id,
 * keeping the map interaction logic out of on_document_ready.
 */
(function (global) {
  'use strict';

  var ID_TYPE = {
    TOPAZ: 'TopazID',
    WEPP: 'WeppID'
  };

  var FEATURE_TYPE = {
    SUBCATCHMENT: 'subcatchment',
    CHANNEL: 'channel'
  };

  function featureMatches(feature, idType, value) {
    return String(feature.properties[idType]) === String(value);
  }

  function flashFeatures(map, features, options) {
    options = options || {};
    var duration = options.duration === undefined ? 1000 : options.duration;
    var fit = Boolean(options.fit);

    if (!map.getPane('markerCustomPane')) {
      map.createPane('markerCustomPane');
      map.getPane('markerCustomPane').style.zIndex = 650;
    }

    var layer = L.geoJSON(
      { type: 'FeatureCollection', features: features },
      {
        style: {
          color: '#ffffff',
          weight: 3,
          opacity: 1,
          fillColor: '#ffffff',
          fillOpacity: 1.0
        },
        pane: 'markerCustomPane',
        interactive: false
      }
    ).addTo(map);

    if (fit) {
      map.fitBounds(layer.getBounds());
    }

    setTimeout(function () {
      map.removeLayer(layer);
    }, duration);
  }

  function findAndFlashById(options) {
    options = options || {};
    var idType = options.idType;
    var value = options.value;
    var map = options.map;
    var layers = options.layers || [];
    var onFlash = options.onFlash;

    if (!idType || value === undefined || value === null) {
      return;
    }

    if (!map) {
      map = global.MapController && typeof global.MapController.getInstance === 'function'
        ? global.MapController.getInstance()
        : null;
    }

    if (!map) {
      console.warn('findAndFlashById: map instance unavailable');
      return;
    }

    if (!Array.isArray(layers) || layers.length === 0) {
      layers = [];
    }

    var hits = [];
    var hitType = null;

    for (var i = 0; i < layers.length; i += 1) {
      var layer = layers[i];
      if (!layer.ctrl || !layer.ctrl.glLayer || !layer.ctrl.glLayer._shapes) {
        continue;
      }

      var features = layer.ctrl.glLayer._shapes.features || [];
      hits = features.filter(function (f) {
        return featureMatches(f, idType, value);
      });

      if (hits.length > 0) {
        hitType = layer.type || null;
        break;
      }
    }

    if (!hits.length) {
      console.warn('findAndFlashById: no feature found matching', idType, value);
      return;
    }

    flashFeatures(map, hits, { duration: 1000, fit: false });

    if (typeof onFlash === 'function') {
      try {
        onFlash({ hits: hits, featureType: hitType, idType: idType, value: value });
      } catch (err) {
        console.error('findAndFlashById onFlash error:', err);
      }
    }
  }

  global.WEPP_FIND_AND_FLASH = {
    ID_TYPE: ID_TYPE,
    FEATURE_TYPE: FEATURE_TYPE,
    findAndFlashById: findAndFlashById,
    flashFeatures: flashFeatures
  };
})(window);

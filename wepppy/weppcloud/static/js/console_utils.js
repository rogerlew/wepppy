(function (global) {
  "use strict";

  function readDataset(node) {
    if (!node || !node.dataset) {
      return {};
    }
    var data = {};
    Object.keys(node.dataset).forEach(function (key) {
      data[key] = node.dataset[key];
    });
    return data;
  }

  function normalizeBoolean(value) {
    if (typeof value !== "string") {
      return value;
    }
    var lowered = value.toLowerCase();
    if (lowered === "true") {
      return true;
    }
    if (lowered === "false") {
      return false;
    }
    return value;
  }

  function mergeConfig(container, selector) {
    if (!container) {
      return {};
    }
    var configNode = selector ? container.querySelector(selector) : null;
    var config = readDataset(configNode);
    var fallback = readDataset(container);

    Object.keys(fallback).forEach(function (key) {
      if (config[key] === undefined) {
        config[key] = fallback[key];
      }
    });

    Object.keys(config).forEach(function (key) {
      config[key] = normalizeBoolean(config[key]);
    });
    return config;
  }

  if (!global.WCConsoleConfig) {
    global.WCConsoleConfig = {};
  }
  global.WCConsoleConfig.readConfig = mergeConfig;
})(typeof window !== "undefined" ? window : this);

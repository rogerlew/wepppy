/* ----------------------------------------------------------------------------
 * Unitizer Client
 * ----------------------------------------------------------------------------
 * Bridges the generated unitizer_map.js module with legacy jQuery-driven
 * controls. Provides helpers to convert values, update DOM labels, and keep
 * preference state in sync with the server.
 */
(function (global) {
    "use strict";

    var modulePromise = null;
    var clientInstance = null;

    function resolveStaticPath(filename) {
        var prefix = (typeof global.site_prefix === "string" && global.site_prefix) ? global.site_prefix : "";
        if (prefix && prefix.charAt(prefix.length - 1) === "/") {
            prefix = prefix.slice(0, -1);
        }
        return prefix + "/static/js/" + filename;
    }

    function loadUnitizerMap() {
        if (global.__unitizerMapModule) {
            return Promise.resolve(global.__unitizerMapModule);
        }

        if (!modulePromise) {
            var inlineMap = global.__unitizerMap;
            if (inlineMap && Array.isArray(inlineMap.categories)) {
                global.__unitizerMapModule = { unitizerMap: inlineMap };
                modulePromise = Promise.resolve(global.__unitizerMapModule);
                return modulePromise;
            }

            var modulePath = resolveStaticPath("unitizer_map.js");
            modulePromise = import(modulePath)
                .then(function (module) {
                    global.__unitizerMapModule = module;
                    return module;
                })
                .catch(function (error) {
                    console.error("Failed to load unitizer_map.js", error);
                    if (global.__unitizerMap && Array.isArray(global.__unitizerMap.categories)) {
                        var fallbackModule = { unitizerMap: global.__unitizerMap };
                        global.__unitizerMapModule = fallbackModule;
                        return fallbackModule;
                    }
                    throw error;
                });
        }
        return modulePromise;
    }

    function createClient(mapModule) {
        var map = mapModule && (mapModule.unitizerMap || mapModule.getUnitizerMap && mapModule.getUnitizerMap());
        if (!map || !Array.isArray(map.categories)) {
            throw new Error("unitizer_map.js did not expose unitizerMap");
        }

    var categoriesByKey = new Map();
    var unitToCategory = new Map();
    var tokenToUnit = new Map();
    var numericInputs = new Map();

        map.categories.forEach(function (category) {
            var units = category.units.map(function (unit, index) {
                var entry = {
                    key: unit.key,
                    token: unit.token,
                    label: unit.label,
                    htmlLabel: unit.htmlLabel,
                    precision: Number(unit.precision),
                    index: index,
                };
                unitToCategory.set(entry.key, category.key);
                tokenToUnit.set(entry.token, entry.key);
                return entry;
            });

            var conversionIndex = new Map();
            category.conversions.forEach(function (conversion) {
                var key = conversion.from + "->" + conversion.to;
                conversionIndex.set(key, {
                    from: conversion.from,
                    to: conversion.to,
                    scale: Number(conversion.scale),
                    offset: Number(conversion.offset),
                });
            });

            categoriesByKey.set(category.key, {
                key: category.key,
                label: category.label,
                defaultIndex: Math.max(0, Math.min(Number(category.defaultIndex) || 0, units.length - 1)),
                units: units,
                conversions: conversionIndex,
                unitByKey: units.reduce(function (acc, unit) {
                    acc.set(unit.key, unit);
                    return acc;
                }, new Map()),
                unitByToken: units.reduce(function (acc, unit) {
                    acc.set(unit.token, unit);
                    return acc;
                }, new Map()),
            });
        });

        var preferences = new Map();
        categoriesByKey.forEach(function (category) {
            var fallback = category.units[category.defaultIndex] || category.units[0];
            preferences.set(category.key, fallback.key);
        });

        function getCategory(categoryKey) {
            return categoriesByKey.get(categoryKey) || null;
        }

        function getUnit(unitKey) {
            var categoryKey = unitToCategory.get(unitKey);
            if (!categoryKey) {
                return null;
            }
            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return null;
            }
            return category.unitByKey.get(unitKey) || null;
        }

        function getToken(unitKey) {
            var unit = getUnit(unitKey);
            return unit ? unit.token : null;
        }

        function getPrecision(unitKey) {
            var unit = getUnit(unitKey);
            return unit ? unit.precision : 3;
        }

        function getConversion(fromUnit, toUnit) {
            if (fromUnit === toUnit) {
                return { scale: 1, offset: 0 };
            }
            var categoryKey = unitToCategory.get(fromUnit);
            if (!categoryKey) {
                throw new Error("Unknown source unit: " + fromUnit);
            }
            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                throw new Error("Unknown category for unit: " + fromUnit);
            }
            var key = fromUnit + "->" + toUnit;
            var conversion = category.conversions.get(key);
            if (!conversion) {
                throw new Error("No conversion available from " + fromUnit + " to " + toUnit);
            }
            return conversion;
        }

        function convert(value, fromUnit, toUnit) {
            if (fromUnit === toUnit) {
                return value;
            }
            var conversion = getConversion(fromUnit, toUnit);
            return conversion.scale * value + conversion.offset;
        }

        function toNumber(value) {
            if (typeof value === "number") {
                return value;
            }
            if (typeof value === "string" && value.trim() !== "") {
                var parsed = Number(value);
                if (!Number.isNaN(parsed)) {
                    return parsed;
                }
            }
            return null;
        }

        function formatNumber(value, precision) {
            if (!Number.isFinite(value)) {
                return String(value);
            }
            var p = precision;
            if (!Number.isFinite(p) || p <= 0) {
                p = 4;
            }
            var formatted = Number.parseFloat(Number(value).toPrecision(p));
            if (Number.isInteger(formatted)) {
                return String(formatted);
            }
            return String(formatted);
        }

        function renderUnitBlock(unit, content, visible, options) {
            var classes = ["unitizer", "units-" + unit.token];
            if (!visible) {
                classes.push("invisible");
            }
            if (options && Array.isArray(options.otherClasses)) {
                classes = classes.concat(options.otherClasses);
            }
            return '<div class="' + classes.join(" ") + '">' + content + "</div>";
        }

        function wrapUnitizer(blocks) {
            return '<div class="unitizer-wrapper">' + blocks.join("") + "</div>";
        }

        function renderValue(value, unitKey, options) {
            options = options || {};

            if (value === null || value === undefined || value === "") {
                return "";
            }

            var canonical = String(unitKey);
            if (canonical === "pct" || canonical === "%") {
                var numeric = toNumber(value);
                if (numeric === null) {
                    return "<i>" + value + "</i>";
                }
                if (numeric < 0.1 && numeric !== 0) {
                    return wrapUnitizer([
                        '<div class="unitizer units-pct">' + Number(numeric).toExponential(0) + "</div>",
                    ]);
                }
                return wrapUnitizer([
                    '<div class="unitizer units-pct">' + Number(numeric).toFixed(1) + "</div>",
                ]);
            }

            if (canonical === "hours") {
                var numericHours = toNumber(value);
                if (numericHours === null) {
                    return "<i>" + value + "</i>";
                }
                var hours = Math.trunc(numericHours);
                var minutes = Math.trunc((numericHours - hours) * 60);
                var padded = String(minutes >= 0 ? minutes : 0).padStart(2, "0");
                return wrapUnitizer([
                    '<div class="unitizer units-hours">' + hours + ":" + padded + "</div>",
                ]);
            }

            var categoryKey = unitToCategory.get(canonical);
            if (!categoryKey) {
                return "<i>" + value + "</i>";
            }

            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return "<i>" + value + "</i>";
            }

            var numericValue = toNumber(value);
            var baseUnit = category.unitByKey.get(canonical);
            if (!baseUnit || numericValue === null) {
                return "<i>" + value + "</i>";
            }

            var includeUnits = options.includeUnits === true;
            var parentheses = options.parentheses === true;
            var preferredUnit = preferences.get(categoryKey) || baseUnit.key;

            var blocks = [];
            category.units.forEach(function (unit) {
                var rendered;
                if (unit.key === baseUnit.key) {
                    rendered = formatNumber(numericValue, options.precision !== undefined ? options.precision : unit.precision);
                } else {
                    try {
                        var converted = convert(numericValue, baseUnit.key, unit.key);
                        rendered = formatNumber(converted, unit.precision);
                    } catch (error) {
                        rendered = "<i>" + value + "</i>";
                    }
                }
                if (includeUnits) {
                    rendered = rendered + " " + unit.htmlLabel;
                }
                if (parentheses) {
                    rendered = "(" + rendered + ")";
                }
                var isPreferred = unit.key === preferredUnit;
                blocks.push(renderUnitBlock(unit, rendered, isPreferred, options));
            });

            return wrapUnitizer(blocks);
        }

        function renderUnits(unitKey, options) {
            options = options || {};
            var canonical = String(unitKey);
            if (canonical === "pct" || canonical === "%") {
                return wrapUnitizer([
                    '<div class="unitizer units-pct">' + (options.parentheses ? "(%)" : "%") + "</div>",
                ]);
            }

            var categoryKey = unitToCategory.get(canonical);
            if (!categoryKey) {
                return canonical;
            }

            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return canonical;
            }

            var preferredUnit = preferences.get(categoryKey) || canonical;
            var blocks = category.units.map(function (unit) {
                var content = options.parentheses ? "(" + unit.htmlLabel + ")" : unit.htmlLabel;
                var isPreferred = unit.key === preferredUnit;
                return renderUnitBlock(unit, content, isPreferred, options);
            });
            return wrapUnitizer(blocks);
        }

        function registerNumericInputs(root) {
            var context = root || document;
            var elements = context.querySelectorAll('[data-unitizer-category][data-unitizer-unit]');
            elements.forEach(function (element) {
                if (numericInputs.has(element)) {
                    return;
                }

                var category = element.getAttribute('data-unitizer-category');
                var canonicalUnit = element.getAttribute('data-unitizer-unit');
                if (!category || !canonicalUnit) {
                    return;
                }

                var precisionAttr = element.getAttribute('data-precision');
                var precisionValue = Number(precisionAttr);
                var meta = {
                    element: element,
                    category: category,
                    canonicalUnit: canonicalUnit,
                    precision: Number.isFinite(precisionValue) ? precisionValue : null,
                };

                element.dataset.unitizerActiveUnit = element.dataset.unitizerActiveUnit || canonicalUnit;
                updateCanonicalValue(element, meta);

                var handler = function () {
                    updateCanonicalValue(element, meta);
                };

                element.addEventListener('input', handler);
                element.addEventListener('change', handler);
                meta.handler = handler;

                numericInputs.set(element, meta);
                if (typeof console !== "undefined" && typeof console.log === "function") {
                    console.log("[UnitizerClient] Registered numeric input", {
                        category: meta.category,
                        canonicalUnit: meta.canonicalUnit,
                        elementId: element.id
                    });
                }
            });
        }

        function updateCanonicalValue(element, meta) {
            var raw = toNumber(element.value);
            if (raw === null) {
                element.dataset.unitizerCanonicalValue = "";
                return;
            }

            var activeUnit = element.dataset.unitizerActiveUnit || meta.canonicalUnit;
            var canonical;
            try {
                canonical = activeUnit === meta.canonicalUnit
                    ? raw
                    : convert(raw, activeUnit, meta.canonicalUnit);
            } catch (error) {
                console.warn("Unitizer: failed to convert numeric field", error);
                return;
            }

            element.dataset.unitizerCanonicalValue = String(canonical);
        }

        function getCanonicalValue(meta) {
            var stored = meta.element.dataset.unitizerCanonicalValue;
            if (stored && stored !== "") {
                var parsed = Number(stored);
                if (Number.isFinite(parsed)) {
                    return parsed;
                }
            }

            updateCanonicalValue(meta.element, meta);
            var canonical = meta.element.dataset.unitizerCanonicalValue;

            if (canonical === undefined || canonical === null || canonical === "") {
                return null;
            }

            var retry = Number(canonical);
            return Number.isFinite(retry) ? retry : null;
        }

        function updateNumericFields(root) {
            var context = root || document;
            var scopeIsDocument = !context || context === document;

            numericInputs.forEach(function (meta, element) {
                if (!scopeIsDocument && !context.contains(element)) {
                    return;
                }

                var canonicalValue = getCanonicalValue(meta);
                if (canonicalValue === null) {
                    return;
                }

                var preferredUnit = preferences.get(meta.category) || meta.canonicalUnit;
                var currentUnit = element.dataset.unitizerActiveUnit || meta.canonicalUnit;
                if (preferredUnit === currentUnit) {
                    return;
                }

                var targetUnit = getUnit(preferredUnit);
                var precision = targetUnit ? targetUnit.precision : meta.precision;
                var converted;
                try {
                    converted = convert(canonicalValue, meta.canonicalUnit, preferredUnit);
                } catch (error) {
                    console.warn("Unitizer: failed to convert numeric field", error);
                    return;
                }

                element.value = formatNumber(converted, precision);
                element.dataset.unitizerActiveUnit = preferredUnit;
            });
        }

        function setPreference(categoryKey, unitKey) {
            if (!categoriesByKey.has(categoryKey)) {
                return false;
            }
            var category = categoriesByKey.get(categoryKey);
            if (!category || !category.unitByKey.has(unitKey)) {
                return false;
            }
            preferences.set(categoryKey, unitKey);
            return true;
        }

        function setPreferenceByToken(categoryKey, token) {
            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return false;
            }
            var unit = category.unitByToken.get(token);
            if (!unit) {
                return false;
            }
            return setPreference(categoryKey, unit.key);
        }

        function setGlobalPreference(index) {
            var idx = Math.max(0, index | 0);
            categoriesByKey.forEach(function (category) {
                var fallback = category.units[idx] || category.units[category.defaultIndex] || category.units[0];
                if (fallback) {
                    preferences.set(category.key, fallback.key);
                }
            });
            if (typeof console !== "undefined" && typeof console.log === "function") {
                console.log("[UnitizerClient] setGlobalPreference", index, getPreferencePayload());
            }
        }

        function getPreferencePayload() {
            var payload = {};
            preferences.forEach(function (unitKey, categoryKey) {
                payload[categoryKey] = unitKey;
            });
            return payload;
        }

        function getPreferenceTokens() {
            var tokens = {};
            preferences.forEach(function (unitKey, categoryKey) {
                var token = getToken(unitKey);
                if (token) {
                    tokens[categoryKey] = token;
                }
            });
            return tokens;
        }

        function syncPreferencesFromDom(root) {
            var context = root || document;
            categoriesByKey.forEach(function (category) {
                var name = "unitizer_" + category.key + "_radio";
                var checked = context.querySelector("input[name='" + name + "']:checked");
                if (checked && checked.value) {
                    setPreferenceByToken(category.key, checked.value);
                }
            });
        }

        function applyPreferenceRadios(root) {
            var context = root || document;
            categoriesByKey.forEach(function (category) {
                var token = getToken(preferences.get(category.key));
                if (!token) {
                    return;
                }
                var selector = "input[name='unitizer_" + category.key + "_radio'][value='" + token + "']";
                var radio = context.querySelector(selector);
                if (radio) {
                    radio.checked = true;
                }
            });
        }

        function applyGlobalRadio(index, root) {
            var context = root || document;
            var selector = "input[name='uni_main_selector'][value='" + index + "']";
            var radios = context.querySelectorAll(selector);
            if (!radios || radios.length === 0) {
                return;
            }
            Array.prototype.forEach.call(radios, function (radio) {
                radio.checked = true;
            });
        }

        function updateUnitLabels(root) {
            var context = root || document;
            var elements = context.querySelectorAll("[data-unitizer-label]");
            elements.forEach(function (element) {
                var categoryKey = element.getAttribute("data-unitizer-category");
                if (!categoryKey) {
                    return;
                }
                var preferredUnitKey = preferences.get(categoryKey);
                if (!preferredUnitKey) {
                    return;
                }
                var unit = getUnit(preferredUnitKey);
                if (!unit) {
                    return;
                }
                element.innerHTML = unit.htmlLabel;
                element.setAttribute("data-unitizer-unit", unit.key);
            });
        }

        function dispatchPreferenceChange() {
            var detail = {
                preferences: getPreferencePayload(),
                tokens: getPreferenceTokens(),
            };
            var event = new CustomEvent("unitizer:preferences-changed", { detail: detail });
            document.dispatchEvent(event);
        }

        return {
            getCategory: getCategory,
            getPreferencePayload: getPreferencePayload,
            getPreferenceTokens: getPreferenceTokens,
            getToken: getToken,
            convert: convert,
            renderValue: renderValue,
            renderUnits: renderUnits,
            setPreference: setPreference,
            setPreferenceByToken: setPreferenceByToken,
            setGlobalPreference: setGlobalPreference,
            syncPreferencesFromDom: syncPreferencesFromDom,
            applyPreferenceRadios: applyPreferenceRadios,
            applyGlobalRadio: applyGlobalRadio,
            updateUnitLabels: updateUnitLabels,
            registerNumericInputs: registerNumericInputs,
            updateNumericFields: updateNumericFields,
            dispatchPreferenceChange: dispatchPreferenceChange,
        };
    }

    function initClient() {
        return loadUnitizerMap().then(function (module) {
            clientInstance = createClient(module);
            return clientInstance;
        });
    }

    global.UnitizerClient = {
        ready: function () {
            if (clientInstance) {
                return Promise.resolve(clientInstance);
            }
            return initClient();
        },
        getClientSync: function () {
            return clientInstance;
        },
        renderValue: function (value, unitKey, options) {
            if (clientInstance) {
                return clientInstance.renderValue(value, unitKey, options);
            }
            return String(value);
        },
        renderUnits: function (unitKey, options) {
            if (clientInstance) {
                return clientInstance.renderUnits(unitKey, options);
            }
            return String(unitKey);
        },
    };
})(window);

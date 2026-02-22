/* ----------------------------------------------------------------------------
 * Map GL Layer Control Helpers
 * ----------------------------------------------------------------------------
 */
var WCMapGlLayerControl = (function () {
    "use strict";

    function ensureLayerControl(options) {
        var layerControl = options.layerControl || null;
        var mapCanvasElement = options.mapCanvasElement || null;

        if (layerControl || !mapCanvasElement || typeof document === "undefined") {
            return layerControl;
        }

        var host = mapCanvasElement.closest ? mapCanvasElement.closest(".wc-map") : null;
        if (!host) {
            host = mapCanvasElement.parentElement;
        }
        if (!host) {
            return null;
        }

        var root = document.createElement("div");
        root.className = "wc-map-layer-control";
        root.setAttribute("data-map-layer-control", "true");

        var toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "wc-map-layer-control__toggle";
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Layers");
        toggle.setAttribute("title", "Layers");
        toggle.innerHTML = '<svg class="wc-map-layer-control__icon" aria-hidden="true" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg" width="26" height="26"><path fill="#b9b9b9" d="m.032 17.056 13-8 13 8-13 8z"/><path fill="#737373" d="m.032 17.056-.032.93 13 8 13-8 .032-.93-13 8z"/><path fill="#cdcdcd" d="m0 13.076 13-8 13 8-13 8z"/><path fill="#737373" d="M0 13.076v.91l13 8 13-8v-.91l-13 8z"/><path fill="#e9e9e9" fill-opacity=".585" stroke="#797979" stroke-width=".1" d="m0 8.986 13-8 13 8-13 8-13-8"/><path fill="#737373" d="M0 8.986v1l13 8 13-8v-1l-13 8z"/></svg><span class="wc-sr-only">Layers</span>';

        var panel = document.createElement("div");
        panel.className = "wc-map-layer-control__panel";
        panel.hidden = true;

        var baseSection = document.createElement("div");
        baseSection.className = "wc-map-layer-control__section";
        var baseTitle = document.createElement("div");
        baseTitle.className = "wc-map-layer-control__title";
        baseTitle.textContent = "Base Layers";
        var baseList = document.createElement("div");
        baseList.className = "wc-map-layer-control__list";
        baseSection.appendChild(baseTitle);
        baseSection.appendChild(baseList);

        var overlaySection = document.createElement("div");
        overlaySection.className = "wc-map-layer-control__section";
        var overlayTitle = document.createElement("div");
        overlayTitle.className = "wc-map-layer-control__title";
        overlayTitle.textContent = "Overlays";
        var overlayList = document.createElement("div");
        overlayList.className = "wc-map-layer-control__list";
        overlaySection.appendChild(overlayTitle);
        overlaySection.appendChild(overlayList);

        panel.appendChild(baseSection);
        panel.appendChild(overlaySection);
        root.appendChild(toggle);
        root.appendChild(panel);
        host.appendChild(root);

        var control = {
            root: root,
            toggle: toggle,
            panel: panel,
            baseSection: baseSection,
            baseList: baseList,
            overlaySection: overlaySection,
            overlayList: overlayList,
            overlayInputs: typeof Map === "function" ? new Map() : null,
            collapse: function () {
                setExpanded(control, false);
            }
        };

        toggle.addEventListener("click", function () {
            var expanded = toggle.getAttribute("aria-expanded") === "true";
            setExpanded(control, !expanded);
        });

        root.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                setExpanded(control, false);
            }
        });

        mapCanvasElement.addEventListener("pointerdown", control.collapse);
        mapCanvasElement.addEventListener("wheel", control.collapse);

        return control;
    }

    function setExpanded(control, expanded) {
        if (!control) {
            return;
        }
        control.toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
        control.root.classList.toggle("is-expanded", expanded);
        control.panel.hidden = !expanded;
    }

    function renderBaseLayerControl(options) {
        var control = options.control;
        var map = options.map;
        var baseLayerKey = options.baseLayerKey;

        if (!control || !map) {
            return;
        }

        var baseMaps = map.baseMaps || {};
        var names = Object.keys(baseMaps);
        control.baseList.textContent = "";
        if (!names.length) {
            control.baseSection.hidden = true;
            return;
        }
        control.baseSection.hidden = false;
        names.forEach(function (name, index) {
            var def = baseMaps[name];
            var key = def && def.key ? def.key : name;
            var label = def && def.label ? def.label : name;
            var inputId = "wc-map-basemap-" + index;
            var wrapper = document.createElement("label");
            wrapper.className = "wc-map-layer-control__item";
            var input = document.createElement("input");
            input.type = "radio";
            input.name = "wc-map-basemap";
            input.value = key;
            input.id = inputId;
            input.checked = key === baseLayerKey;
            input.addEventListener("change", function () {
                if (input.checked) {
                    map.setBaseLayer(key);
                }
            });
            var text = document.createElement("span");
            text.className = "wc-map-layer-control__text";
            text.textContent = label;
            wrapper.appendChild(input);
            wrapper.appendChild(text);
            control.baseList.appendChild(wrapper);
        });
    }

    function syncBaseLayerControlSelection(options) {
        var control = options.control;
        var baseLayerKey = options.baseLayerKey;
        if (!control) {
            return;
        }
        var inputs = control.baseList.querySelectorAll('input[type="radio"][name="wc-map-basemap"]');
        Array.prototype.forEach.call(inputs, function (input) {
            input.checked = input.value === baseLayerKey;
        });
    }

    function overlaySortIndex(name, options) {
        if (!name) {
            return 99;
        }
        if (name.indexOf(options.usgsLayerName) !== -1) {
            return 0;
        }
        if (name.indexOf(options.snotelLayerName) !== -1) {
            return 1;
        }
        if (name.indexOf("NHD") !== -1) {
            return 2;
        }
        if (name.indexOf(options.sbsLayerName) !== -1) {
            return 3;
        }
        return 99;
    }

    function overlayRenderIndex(name, options) {
        if (!name) {
            return 99;
        }
        var label = String(name);
        if (label.indexOf(options.sbsLayerName) !== -1) {
            return 10;
        }
        if (label.indexOf("NHD") !== -1) {
            return 20;
        }
        if (label.indexOf("Subcatchment Labels") !== -1) {
            return 80;
        }
        if (label.indexOf("Contrast ID Labels") !== -1) {
            return 85;
        }
        if (label.indexOf("Channel Labels") !== -1) {
            return 90;
        }
        if (label.indexOf("Subcatchments") !== -1) {
            return 30;
        }
        if (label.indexOf("Contrast IDs") !== -1) {
            return 35;
        }
        if (label.indexOf("Channels") !== -1) {
            return 40;
        }
        if (label.indexOf(options.usgsLayerName) !== -1) {
            return 50;
        }
        if (label.indexOf(options.snotelLayerName) !== -1) {
            return 60;
        }
        if (label.indexOf("Outlet") !== -1) {
            return 70;
        }
        return 99;
    }

    function rebuildOverlayLayer(options) {
        var name = options.name;
        var layer = options.layer;
        var overlayRegistry = options.overlayRegistry;
        var overlayNameRegistry = options.overlayNameRegistry;
        var overlayMaps = options.overlayMaps;

        if (!layer || typeof layer.__wcRebuild !== "function") {
            return layer;
        }
        var nextLayer = layer.__wcRebuild();
        if (!nextLayer || nextLayer === layer) {
            return layer;
        }
        if (overlayRegistry) {
            overlayRegistry.delete(layer);
            overlayRegistry.set(nextLayer, name);
        }
        if (overlayNameRegistry) {
            overlayNameRegistry.set(name, nextLayer);
        }
        if (overlayMaps) {
            overlayMaps[name] = nextLayer;
        }
        return nextLayer;
    }

    function renderOverlayLayerControl(options) {
        var control = options.control;
        var map = options.map;
        var overlayNameRegistry = options.overlayNameRegistry;
        var shouldRenderOverlay = options.shouldRenderOverlay;
        var sortIndex = options.overlaySortIndex;
        var rebuildLayer = options.rebuildOverlayLayer;
        var emit = options.emit;

        if (!control || !overlayNameRegistry) {
            return;
        }

        control.overlayList.textContent = "";
        if (control.overlayInputs && typeof control.overlayInputs.clear === "function") {
            control.overlayInputs.clear();
        }

        var entries = Array.from(overlayNameRegistry.entries())
            .filter(function (entry) {
                return shouldRenderOverlay(entry[0]);
            })
            .map(function (entry, index) {
                return {
                    entry: entry,
                    index: index,
                    order: sortIndex(entry[0])
                };
            });

        if (!entries.length) {
            control.overlaySection.hidden = true;
            return;
        }

        control.overlaySection.hidden = false;
        entries.sort(function (a, b) {
            if (a.order !== b.order) {
                return a.order - b.order;
            }
            return a.index - b.index;
        });

        entries.forEach(function (item, index) {
            var name = item.entry[0];
            var layer = item.entry[1];
            var inputId = "wc-map-overlay-" + index;
            var wrapper = document.createElement("label");
            wrapper.className = "wc-map-layer-control__item";
            var input = document.createElement("input");
            input.type = "checkbox";
            input.name = "wc-map-overlay";
            input.value = name;
            input.id = inputId;
            input.checked = map.hasLayer(layer);
            input.addEventListener("change", function () {
                var activeLayer = overlayNameRegistry && overlayNameRegistry.get(name)
                    ? overlayNameRegistry.get(name)
                    : layer;
                if (input.checked) {
                    activeLayer = rebuildLayer(name, activeLayer);
                    map.addLayer(activeLayer);
                } else {
                    map.removeLayer(activeLayer);
                }
                emit("map:layer:toggled", {
                    name: name,
                    layer: activeLayer,
                    visible: input.checked,
                    type: "overlay"
                });
            });
            var text = document.createElement("span");
            text.className = "wc-map-layer-control__text";
            text.textContent = name;
            wrapper.appendChild(input);
            wrapper.appendChild(text);
            control.overlayList.appendChild(wrapper);
            if (control.overlayInputs && typeof control.overlayInputs.set === "function") {
                control.overlayInputs.set(name, input);
            }
        });
    }

    function syncOverlayLayerControlSelection(options) {
        var control = options.control;
        var overlayNameRegistry = options.overlayNameRegistry;
        var map = options.map;

        if (!control || !overlayNameRegistry || !control.overlayInputs) {
            return;
        }

        control.overlayInputs.forEach(function (input, name) {
            var layer = overlayNameRegistry.get(name);
            if (!layer) {
                input.disabled = true;
                return;
            }
            input.disabled = false;
            input.checked = map.hasLayer(layer);
        });
    }

    return {
        ensureLayerControl: ensureLayerControl,
        renderBaseLayerControl: renderBaseLayerControl,
        syncBaseLayerControlSelection: syncBaseLayerControlSelection,
        overlaySortIndex: overlaySortIndex,
        overlayRenderIndex: overlayRenderIndex,
        rebuildOverlayLayer: rebuildOverlayLayer,
        renderOverlayLayerControl: renderOverlayLayerControl,
        syncOverlayLayerControlSelection: syncOverlayLayerControlSelection
    };
}());

window.WCMapGlLayerControl = WCMapGlLayerControl;

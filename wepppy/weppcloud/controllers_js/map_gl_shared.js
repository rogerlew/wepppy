/* ----------------------------------------------------------------------------
 * Map GL Shared Constants and Utilities
 * ----------------------------------------------------------------------------
 */
var WCMapGlShared = (function () {
    "use strict";

    var EVENT_NAMES = [
        "map:ready",
        "map:center:requested",
        "map:center:changed",
        "map:search:requested",
        "map:elevation:requested",
        "map:elevation:loaded",
        "map:elevation:error",
        "map:drilldown:requested",
        "map:drilldown:loaded",
        "map:drilldown:error",
        "map:layer:toggled",
        "map:layer:refreshed",
        "map:layer:error",
        "baer:map:opacity"
    ];

    var DEFAULT_VIEW = { lat: 44.0, lng: -116.0, zoom: 6 };
    var FLY_TO_DURATION_MS = 4000;
    var FLY_TO_BOUNDS_PADDING_PX = 48;
    var SENSOR_LAYER_MIN_ZOOM = 9;
    var MAP_MIN_ZOOM = 0;
    var MAP_MAX_ZOOM = 19;
    var USGS_LAYER_NAME = "USGS Gage Locations";
    var SNOTEL_LAYER_NAME = "SNOTEL Locations";
    var NHD_LAYER_NAME = "NHD Flowlines";
    var NHD_LAYER_MIN_ZOOM = 11;
    var NHD_LAYER_HR_MIN_ZOOM = 14;
    var NHD_SMALL_SCALE_QUERY_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/4/query";
    var NHD_HR_QUERY_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query";
    var SUBCATCHMENT_LAYER_ENDPOINT = "resources/subcatchments.json";
    var CHANNEL_LAYER_ENDPOINT = "resources/channels.json";
    var SBS_LAYER_NAME = "Burn Severity Map";
    var SBS_QUERY_ENDPOINT = "query/baer_wgs_map/";
    var SBS_DEFAULT_OPACITY = 0.3;
    var SBS_COLOR_MODES = {
        STANDARD: "standard",
        SHIFTED: "shifted"
    };
    var SBS_LEGEND_ITEMS_STANDARD = [
        { key: 130, label: "No Burn", color: "#00734A" },
        { key: 131, label: "Low Severity Burn", color: "#4DE600" },
        { key: 132, label: "Moderate Severity Burn", color: "#FFFF00" },
        { key: 133, label: "High Severity Burn", color: "#FF0000" }
    ];
    var SBS_LEGEND_ITEMS_SHIFTED = [
        { key: 130, label: "No Burn", color: "#009E73" },
        { key: 131, label: "Low Severity Burn", color: "#56B4E9" },
        { key: 132, label: "Moderate Severity Burn", color: "#F0E442" },
        { key: 133, label: "High Severity Burn", color: "#CC79A7" }
    ];
    var SBS_STANDARD_TO_SHIFTED_RGB = {
        "0_115_74": [0, 158, 115],
        "77_230_0": [86, 180, 233],
        "255_255_0": [240, 228, 66],
        "255_0_0": [204, 121, 167]
    };
    var LEGEND_OPACITY_CONTAINER_ID = "baer-opacity-controls";
    var LEGEND_OPACITY_INPUT_ID = "baer-opacity-slider";
    var DEFAULT_ELEVATION_COOLDOWN_MS = 200;
    var MOUSE_ELEVATION_HIDE_DELAY_MS = 2000;
    var FIND_FLASH_LAYER_PREFIX = "wc-find-flash";
    var FIND_FLASH_DURATION_MS = 1200;
    var FIND_FLASH_PULSE_INTERVAL_MS = 200;

    function createLegacyAdapter(element) {
        if (!element) {
            return {
                element: element,
                length: 0,
                show: function () { return this; },
                hide: function () { return this; },
                text: function () { return arguments.length === 0 ? "" : this; },
                html: function () { return arguments.length === 0 ? "" : this; },
                append: function () { return this; },
                empty: function () { return this; }
            };
        }

        return {
            element: element,
            length: 1,
            show: function () {
                element.hidden = false;
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
                return this;
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
                return this;
            },
            text: function (value) {
                if (arguments.length === 0) {
                    return element.textContent;
                }
                element.textContent = value === undefined || value === null ? "" : String(value);
                return this;
            },
            html: function (value) {
                if (arguments.length === 0) {
                    return element.innerHTML;
                }
                element.innerHTML = value === undefined || value === null ? "" : String(value);
                return this;
            },
            append: function (content) {
                if (content === undefined || content === null) {
                    return this;
                }
                if (typeof content === "string") {
                    element.insertAdjacentHTML("beforeend", content);
                    return this;
                }
                if (content instanceof window.Node) {
                    element.appendChild(content);
                }
                return this;
            },
            empty: function () {
                element.textContent = "";
                return this;
            }
        };
    }

    function createTabset(root) {
        if (!root) {
            return null;
        }

        var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
        var panels = Array.prototype.slice.call(root.querySelectorAll('[role="tabpanel"]'));

        if (tabs.length === 0 || panels.length === 0) {
            return null;
        }

        function getTarget(tab) {
            return tab ? tab.getAttribute("data-tab-target") : null;
        }

        function setActive(panelId, focusTab) {
            tabs.forEach(function (tab) {
                var target = getTarget(tab);
                var isActive = target === panelId;
                tab.classList.toggle("is-active", isActive);
                tab.setAttribute("aria-selected", isActive ? "true" : "false");
                tab.setAttribute("tabindex", isActive ? "0" : "-1");
                if (isActive && focusTab) {
                    tab.focus();
                }
            });

            panels.forEach(function (panel) {
                var isActive = panel.id === panelId;
                panel.classList.toggle("is-active", isActive);
                if (isActive) {
                    panel.removeAttribute("hidden");
                } else {
                    panel.setAttribute("hidden", "");
                }
            });

            root.dispatchEvent(new CustomEvent("wc-tabset:change", {
                detail: { panelId: panelId },
                bubbles: true
            }));
        }

        var current = tabs.find(function (tab) {
            return tab.getAttribute("aria-selected") === "true" || tab.classList.contains("is-active");
        });
        var initialPanel = getTarget(current) || getTarget(tabs[0]);
        setActive(initialPanel, false);

        tabs.forEach(function (tab) {
            tab.addEventListener("click", function () {
                setActive(getTarget(tab), false);
            });

            tab.addEventListener("keydown", function (event) {
                var key = event.key;
                if (key !== "ArrowLeft" && key !== "ArrowRight" && key !== "Home" && key !== "End") {
                    return;
                }

                event.preventDefault();
                var currentIndex = tabs.indexOf(tab);
                if (key === "ArrowLeft" || key === "ArrowRight") {
                    var offset = key === "ArrowRight" ? 1 : -1;
                    var nextIndex = (currentIndex + offset + tabs.length) % tabs.length;
                    setActive(getTarget(tabs[nextIndex]), true);
                } else if (key === "Home") {
                    setActive(getTarget(tabs[0]), true);
                } else if (key === "End") {
                    setActive(getTarget(tabs[tabs.length - 1]), true);
                }
            });
        });

        return {
            activate: function (panelId, focusTab) {
                if (!panelId) {
                    return;
                }
                setActive(panelId, focusTab === true);
            }
        };
    }

    function sanitizeLocationInput(value) {
        if (!value) {
            return [];
        }
        var sanitized = String(value).replace(/[a-zA-Z{}\[\]\\|\/<>';:\u00b0]/g, "");
        return sanitized.split(/[\s,]+/).filter(function (item) {
            return item !== "";
        });
    }

    function parseLocationInput(value) {
        var tokens = sanitizeLocationInput(value);
        if (tokens.length < 2) {
            return null;
        }
        var first = Number(tokens[0]);
        var second = Number(tokens[1]);
        if (!Number.isFinite(first) || !Number.isFinite(second)) {
            return null;
        }
        var zoom = null;
        if (tokens.length > 2) {
            var parsedZoom = Number(tokens[2]);
            if (Number.isFinite(parsedZoom)) {
                zoom = parsedZoom;
            }
        }
        var lonLatCandidate = { lat: second, lng: first, zoom: zoom };
        if (isValidLatLng(lonLatCandidate.lat, lonLatCandidate.lng)) {
            return lonLatCandidate;
        }

        var latLonCandidate = { lat: first, lng: second, zoom: zoom };
        if (isValidLatLng(latLonCandidate.lat, latLonCandidate.lng)) {
            return latLonCandidate;
        }

        return lonLatCandidate;
    }

    function normalizeUrlPayload(input) {
        if (!input) {
            return null;
        }
        if (Array.isArray(input)) {
            return input.length ? normalizeUrlPayload(input[0]) : null;
        }
        return String(input);
    }

    function normalizeErrorValue(value) {
        if (value === undefined || value === null) {
            return null;
        }
        if (typeof value === "string") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(function (item) { return item === undefined || item === null ? "" : String(item); }).join("\n");
        }
        if (typeof value === "object") {
            if (typeof value.message === "string") {
                return value.message;
            }
            if (typeof value.detail === "string") {
                return value.detail;
            }
            if (typeof value.details === "string") {
                return value.details;
            }
            if (value.details !== undefined) {
                return normalizeErrorValue(value.details);
            }
            try {
                return JSON.stringify(value);
            } catch (err) {
                return String(value);
            }
        }
        return String(value);
    }

    function formatErrorList(errors) {
        if (!Array.isArray(errors)) {
            return null;
        }
        var parts = [];
        errors.forEach(function (entry) {
            if (entry === undefined || entry === null) {
                return;
            }
            if (typeof entry === "string") {
                parts.push(entry);
                return;
            }
            if (typeof entry.message === "string") {
                parts.push(entry.message);
                return;
            }
            if (typeof entry.detail === "string") {
                parts.push(entry.detail);
                return;
            }
            if (typeof entry.code === "string") {
                parts.push(entry.code);
                return;
            }
            try {
                parts.push(JSON.stringify(entry));
            } catch (err) {
                parts.push(String(entry));
            }
        });
        return parts.length ? parts.join("\n") : null;
    }

    function resolveErrorMessage(payload, fallback) {
        if (!payload) {
            return fallback || null;
        }
        if (payload.error !== undefined) {
            var message = normalizeErrorValue(payload.error);
            if (message) {
                return message;
            }
        }
        if (payload.errors) {
            var errorList = formatErrorList(payload.errors);
            if (errorList) {
                return errorList;
            }
        }
        if (payload.message !== undefined) {
            return normalizeErrorValue(payload.message);
        }
        if (payload.detail !== undefined) {
            return normalizeErrorValue(payload.detail);
        }
        return fallback || null;
    }

    function isValidLatLng(lat, lng) {
        return lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
    }

    function buildNhdFlowlinesUrl(bbox, zoom) {
        if (!bbox) {
            return null;
        }
        var queryUrl = zoom >= NHD_LAYER_HR_MIN_ZOOM ? NHD_HR_QUERY_URL : NHD_SMALL_SCALE_QUERY_URL;
        return queryUrl
            + "?where=1%3D1"
            + "&outFields=OBJECTID"
            + "&geometry=" + encodeURIComponent(bbox)
            + "&geometryType=esriGeometryEnvelope"
            + "&inSR=4326&outSR=4326"
            + "&spatialRel=esriSpatialRelIntersects"
            + "&returnGeometry=true"
            + "&resultRecordCount=2000"
            + "&f=geojson";
    }

    function toOverlayId(name) {
        var base = String(name || "overlay").toLowerCase();
        var slug = base.replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
        return "map-gl-" + (slug || "overlay");
    }

    function hexToRgba(hex, alpha) {
        if (!hex) {
            return [0, 0, 0, Math.round((alpha === undefined ? 1 : alpha) * 255)];
        }
        var normalized = String(hex).trim().replace("#", "");
        if (normalized.length === 3) {
            normalized = normalized[0] + normalized[0] + normalized[1] + normalized[1] + normalized[2] + normalized[2];
        }
        var intVal = parseInt(normalized, 16);
        if (!Number.isFinite(intVal)) {
            return [0, 0, 0, Math.round((alpha === undefined ? 1 : alpha) * 255)];
        }
        var r = (intVal >> 16) & 255;
        var g = (intVal >> 8) & 255;
        var b = intVal & 255;
        var a = Math.round((alpha === undefined ? 1 : alpha) * 255);
        return [r, g, b, a];
    }

    function isAbsoluteUrl(url) {
        return /^([a-z][a-z\d+\-.]*:)?\/\//i.test(String(url || ""));
    }

    function clampOpacity(value) {
        var parsed = parseFloat(value);
        if (!Number.isFinite(parsed)) {
            return SBS_DEFAULT_OPACITY;
        }
        return Math.max(0, Math.min(1, parsed));
    }

    function normalizeSbsColorMode(value) {
        return value === SBS_COLOR_MODES.SHIFTED ? SBS_COLOR_MODES.SHIFTED : SBS_COLOR_MODES.STANDARD;
    }

    function getSbsLegendItemsForMode(mode) {
        return normalizeSbsColorMode(mode) === SBS_COLOR_MODES.SHIFTED
            ? SBS_LEGEND_ITEMS_SHIFTED
            : SBS_LEGEND_ITEMS_STANDARD;
    }

    function getSbsColorShiftKey(r, g, b) {
        return [r, g, b].join("_");
    }

    function mapSbsRgbForMode(r, g, b, mode) {
        if (normalizeSbsColorMode(mode) !== SBS_COLOR_MODES.SHIFTED) {
            return [r, g, b];
        }
        var mapped = SBS_STANDARD_TO_SHIFTED_RGB[getSbsColorShiftKey(r, g, b)];
        return mapped || [r, g, b];
    }

    function drawSbsImageToCanvas(imageSource) {
        if (!imageSource || typeof document === "undefined") {
            return null;
        }
        var width = Number(imageSource.width);
        var height = Number(imageSource.height);
        if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
            return null;
        }
        var canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        var context = canvas.getContext("2d");
        if (!context) {
            return null;
        }
        try {
            context.drawImage(imageSource, 0, 0);
        } catch (error) {
            return null;
        }
        return canvas;
    }

    function buildShiftedSbsImage(imageSource) {
        var baseCanvas = drawSbsImageToCanvas(imageSource);
        if (!baseCanvas) {
            return imageSource;
        }
        var context = baseCanvas.getContext("2d");
        if (!context) {
            return imageSource;
        }
        var imageData = context.getImageData(0, 0, baseCanvas.width, baseCanvas.height);
        var data = imageData.data;
        for (var i = 0; i < data.length; i += 4) {
            var alpha = data[i + 3];
            if (alpha === 0) {
                continue;
            }
            var mapped = mapSbsRgbForMode(data[i], data[i + 1], data[i + 2], SBS_COLOR_MODES.SHIFTED);
            data[i] = mapped[0];
            data[i + 1] = mapped[1];
            data[i + 2] = mapped[2];
        }
        context.putImageData(imageData, 0, 0);
        return baseCanvas;
    }

    function normalizeSbsBounds(bounds) {
        if (!Array.isArray(bounds) || bounds.length < 2) {
            return null;
        }
        var sw = bounds[0];
        var ne = bounds[1];
        if (!Array.isArray(sw) || !Array.isArray(ne) || sw.length < 2 || ne.length < 2) {
            return null;
        }
        var south = Number(sw[0]);
        var west = Number(sw[1]);
        var north = Number(ne[0]);
        var east = Number(ne[1]);
        if (![south, west, north, east].every(Number.isFinite)) {
            return null;
        }
        return [west, south, east, north];
    }

    function normalizeCenter(center) {
        if (Array.isArray(center) && center.length >= 2) {
            var lat = Number(center[0]);
            var lng = Number(center[1]);
            if (Number.isFinite(lat) && Number.isFinite(lng)) {
                return { lat: lat, lng: lng };
            }
        }
        if (center && typeof center === "object") {
            var cLat = Number(center.lat);
            var cLng = Number(center.lng);
            if (Number.isFinite(cLat) && Number.isFinite(cLng)) {
                return { lat: cLat, lng: cLng };
            }
        }
        return null;
    }

    function buildBoundsFallback(center, zoom) {
        var lat = center.lat;
        var lng = center.lng;
        var zoomValue = Number.isFinite(zoom) ? zoom : DEFAULT_VIEW.zoom;
        var delta = Math.max(0.05, 1 / Math.max(zoomValue, 1));
        return {
            getSouthWest: function () { return { lat: lat - delta, lng: lng - delta }; },
            getNorthEast: function () { return { lat: lat + delta, lng: lng + delta }; },
            toBBoxString: function () {
                return [lng - delta, lat - delta, lng + delta, lat + delta].join(",");
            }
        };
    }

    function calculateDistanceMeters(a, b) {
        if (!a || !b) {
            return 0;
        }
        var lat1 = Number(a.lat);
        var lat2 = Number(b.lat);
        var lon1 = Number(a.lng);
        var lon2 = Number(b.lng);
        if (!Number.isFinite(lat1) || !Number.isFinite(lat2) || !Number.isFinite(lon1) || !Number.isFinite(lon2)) {
            return 0;
        }
        var toRad = Math.PI / 180;
        var dLat = (lat2 - lat1) * toRad;
        var dLon = (lon2 - lon1) * toRad;
        var sinLat = Math.sin(dLat / 2);
        var sinLon = Math.sin(dLon / 2);
        var aHarv = sinLat * sinLat + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * sinLon * sinLon;
        var cHarv = 2 * Math.atan2(Math.sqrt(aHarv), Math.sqrt(1 - aHarv));
        return 6371000 * cHarv;
    }

    return {
        EVENT_NAMES: EVENT_NAMES,
        DEFAULT_VIEW: DEFAULT_VIEW,
        FLY_TO_DURATION_MS: FLY_TO_DURATION_MS,
        FLY_TO_BOUNDS_PADDING_PX: FLY_TO_BOUNDS_PADDING_PX,
        SENSOR_LAYER_MIN_ZOOM: SENSOR_LAYER_MIN_ZOOM,
        MAP_MIN_ZOOM: MAP_MIN_ZOOM,
        MAP_MAX_ZOOM: MAP_MAX_ZOOM,
        USGS_LAYER_NAME: USGS_LAYER_NAME,
        SNOTEL_LAYER_NAME: SNOTEL_LAYER_NAME,
        NHD_LAYER_NAME: NHD_LAYER_NAME,
        NHD_LAYER_MIN_ZOOM: NHD_LAYER_MIN_ZOOM,
        NHD_LAYER_HR_MIN_ZOOM: NHD_LAYER_HR_MIN_ZOOM,
        SUBCATCHMENT_LAYER_ENDPOINT: SUBCATCHMENT_LAYER_ENDPOINT,
        CHANNEL_LAYER_ENDPOINT: CHANNEL_LAYER_ENDPOINT,
        SBS_LAYER_NAME: SBS_LAYER_NAME,
        SBS_QUERY_ENDPOINT: SBS_QUERY_ENDPOINT,
        SBS_DEFAULT_OPACITY: SBS_DEFAULT_OPACITY,
        SBS_COLOR_MODES: SBS_COLOR_MODES,
        LEGEND_OPACITY_CONTAINER_ID: LEGEND_OPACITY_CONTAINER_ID,
        LEGEND_OPACITY_INPUT_ID: LEGEND_OPACITY_INPUT_ID,
        DEFAULT_ELEVATION_COOLDOWN_MS: DEFAULT_ELEVATION_COOLDOWN_MS,
        MOUSE_ELEVATION_HIDE_DELAY_MS: MOUSE_ELEVATION_HIDE_DELAY_MS,
        FIND_FLASH_LAYER_PREFIX: FIND_FLASH_LAYER_PREFIX,
        FIND_FLASH_DURATION_MS: FIND_FLASH_DURATION_MS,
        FIND_FLASH_PULSE_INTERVAL_MS: FIND_FLASH_PULSE_INTERVAL_MS,
        createLegacyAdapter: createLegacyAdapter,
        createTabset: createTabset,
        parseLocationInput: parseLocationInput,
        normalizeUrlPayload: normalizeUrlPayload,
        resolveErrorMessage: resolveErrorMessage,
        isValidLatLng: isValidLatLng,
        buildNhdFlowlinesUrl: buildNhdFlowlinesUrl,
        toOverlayId: toOverlayId,
        hexToRgba: hexToRgba,
        isAbsoluteUrl: isAbsoluteUrl,
        clampOpacity: clampOpacity,
        normalizeSbsColorMode: normalizeSbsColorMode,
        getSbsLegendItemsForMode: getSbsLegendItemsForMode,
        drawSbsImageToCanvas: drawSbsImageToCanvas,
        buildShiftedSbsImage: buildShiftedSbsImage,
        normalizeSbsBounds: normalizeSbsBounds,
        normalizeCenter: normalizeCenter,
        buildBoundsFallback: buildBoundsFallback,
        calculateDistanceMeters: calculateDistanceMeters
    };
}());

window.WCMapGlShared = WCMapGlShared;

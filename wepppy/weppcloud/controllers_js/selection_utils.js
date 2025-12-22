/* ----------------------------------------------------------------------------
 * Shared selection helpers for GL modify controllers.
 * ----------------------------------------------------------------------------
 */
(function () {
    "use strict";

    function createLegacyAdapter(element) {
        if (!element) {
            return {
                element: element,
                length: 0,
                show: function () {},
                hide: function () {},
                text: function () {},
                html: function () {},
                append: function () {},
                empty: function () {}
            };
        }

        return {
            element: element,
            length: 1,
            show: function () {
                element.hidden = false;
                if (element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                element.style.display = "none";
            },
            text: function (value) {
                if (value === undefined) {
                    return element.textContent;
                }
                element.textContent = value === null ? "" : String(value);
            },
            html: function (value) {
                if (value === undefined) {
                    return element.innerHTML;
                }
                element.innerHTML = value === null ? "" : String(value);
            },
            append: function (content) {
                if (content === null || content === undefined) {
                    return;
                }
                if (typeof content === "string") {
                    element.insertAdjacentHTML("beforeend", content);
                    return;
                }
                if (content instanceof window.Node) {
                    element.appendChild(content);
                }
            },
            empty: function () {
                element.textContent = "";
            }
        };
    }

    function toResponsePayload(http, error) {
        function coerceBody(raw) {
            if (!raw) {
                return null;
            }
            if (typeof raw === "string") {
                try {
                    return JSON.parse(raw);
                } catch (err) {
                    return raw;
                }
            }
            return raw;
        }

        var body = coerceBody(error && error.body ? error.body : null);

        if (body && typeof body === "object") {
            var payload = body;
            if (payload.Error === undefined) {
                var fallback =
                    payload.detail ||
                    payload.message ||
                    payload.error ||
                    payload.errors;
                if (fallback !== undefined && fallback !== null) {
                    payload = Object.assign({}, payload, { Error: fallback });
                }
            }
            if (payload.StackTrace !== undefined || payload.Error !== undefined) {
                return payload;
            }
        } else if (typeof body === "string" && body) {
            return { Error: body };
        }

        if (error && typeof error === "object" && (error.Error !== undefined || error.StackTrace !== undefined)) {
            return error;
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            return { Error: detail || "Request failed" };
        }

        return { Error: (error && error.message) || "Request failed" };
    }

    function normalizeTopazId(value) {
        if (value === null || value === undefined) {
            return null;
        }
        var token = String(value).trim();
        if (!token) {
            return null;
        }
        var parsed = parseInt(token, 10);
        if (Number.isNaN(parsed)) {
            return null;
        }
        return String(parsed);
    }

    function parseTopazField(value) {
        if (value === null || value === undefined) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.map(normalizeTopazId).filter(Boolean);
        }
        var tokens = String(value).split(/[\s,]+/);
        return tokens.map(normalizeTopazId).filter(Boolean);
    }

    function sortIds(ids) {
        return ids.slice().sort(function (a, b) {
            var left = parseInt(a, 10);
            var right = parseInt(b, 10);
            if (Number.isNaN(left) || Number.isNaN(right)) {
                return a.localeCompare(b);
            }
            return left - right;
        });
    }

    function hexToRgba(hex, alpha) {
        var normalized = String(hex || "").replace("#", "");
        if (normalized.length === 3) {
            normalized = normalized[0] + normalized[0]
                + normalized[1] + normalized[1]
                + normalized[2] + normalized[2];
        }
        var intVal = parseInt(normalized, 16);
        if (!Number.isFinite(intVal)) {
            return [0, 0, 0, Math.round(alpha * 255)];
        }
        var r = (intVal >> 16) & 255;
        var g = (intVal >> 8) & 255;
        var b = intVal & 255;
        return [r, g, b, Math.round(alpha * 255)];
    }

    function resolveMapElement(dom) {
        return dom.qs("#mapid");
    }

    function resolveMapCanvas(mapElement) {
        if (!mapElement) {
            return null;
        }
        var canvas = mapElement.querySelector("canvas");
        return canvas || mapElement;
    }

    function resolveEventLatLng(event, mapElement, map) {
        if (!event || !map || !map._deck) {
            return null;
        }
        var deckInstance = map._deck;
        var canvas = null;
        if (typeof deckInstance.getCanvas === "function") {
            canvas = deckInstance.getCanvas();
        } else if (deckInstance.canvas) {
            canvas = deckInstance.canvas;
        }
        var rectTarget = canvas || mapElement;
        if (!rectTarget || typeof rectTarget.getBoundingClientRect !== "function") {
            return null;
        }
        var rect = rectTarget.getBoundingClientRect();
        var x = event.clientX - rect.left;
        var y = event.clientY - rect.top;
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
            return null;
        }

        var coords = null;
        if (deckInstance.viewManager && typeof deckInstance.viewManager.unproject === "function") {
            coords = deckInstance.viewManager.unproject([x, y]);
        } else if (typeof deckInstance.getViewports === "function") {
            var viewports = deckInstance.getViewports();
            var viewport = viewports && viewports.length ? viewports[0] : null;
            if (viewport && typeof viewport.unproject === "function") {
                coords = viewport.unproject([x - (viewport.x || 0), y - (viewport.y || 0)]);
            }
        } else if (typeof deckInstance.unproject === "function") {
            coords = deckInstance.unproject([x, y]);
        }

        if (!coords || coords.length < 2) {
            return null;
        }
        var lng = Number(coords[0]);
        var lat = Number(coords[1]);
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
            return null;
        }
        return { lat: lat, lng: lng };
    }

    function buildSelectionBounds(sw, ne) {
        if (!sw || !ne) {
            return null;
        }
        return {
            sw: { lat: Math.min(sw.lat, ne.lat), lng: Math.min(sw.lng, ne.lng) },
            ne: { lat: Math.max(sw.lat, ne.lat), lng: Math.max(sw.lng, ne.lng) }
        };
    }

    function buildSelectionPolygon(bounds) {
        if (!bounds) {
            return null;
        }
        var sw = bounds.sw;
        var ne = bounds.ne;
        return [
            [sw.lng, sw.lat],
            [ne.lng, sw.lat],
            [ne.lng, ne.lat],
            [sw.lng, ne.lat],
            [sw.lng, sw.lat]
        ];
    }

    function buildSelectionBoxLayer(deckApi, bounds, layerId) {
        var polygon = buildSelectionPolygon(bounds);
        if (!polygon) {
            return null;
        }
        return new deckApi.GeoJsonLayer({
            id: layerId || "wc-selection-box",
            data: {
                type: "FeatureCollection",
                features: [
                    {
                        type: "Feature",
                        properties: {},
                        geometry: {
                            type: "Polygon",
                            coordinates: [polygon]
                        }
                    }
                ]
            },
            pickable: false,
            stroked: true,
            filled: true,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return 2; },
            getLineColor: function () { return hexToRgba("#1e90ff", 1); },
            getFillColor: function () { return hexToRgba("#1e90ff", 0.08); }
        });
    }

    var utils = {
        createLegacyAdapter: createLegacyAdapter,
        toResponsePayload: toResponsePayload,
        normalizeTopazId: normalizeTopazId,
        parseTopazField: parseTopazField,
        sortIds: sortIds,
        hexToRgba: hexToRgba,
        resolveMapElement: resolveMapElement,
        resolveMapCanvas: resolveMapCanvas,
        resolveEventLatLng: resolveEventLatLng,
        buildSelectionBounds: buildSelectionBounds,
        buildSelectionPolygon: buildSelectionPolygon,
        buildSelectionBoxLayer: buildSelectionBoxLayer
    };

    if (typeof globalThis !== "undefined") {
        globalThis.WCSelectionUtils = utils;
    }
}());

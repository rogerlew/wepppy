/* ----------------------------------------------------------------------------
 * Map GL Scale Control Helpers
 * ----------------------------------------------------------------------------
 */
var WCMapGlScaleControl = (function () {
    "use strict";

    var DEFAULT_MAX_WIDTH_PX = 120;
    var MIN_VISIBLE_WIDTH_PX = 32;
    var ENGLISH_FEET_THRESHOLD = 2640;
    var FEET_PER_METER = 3.28084;
    var METERS_PER_MILE = 1609.344;

    function getHostElement(hostElement) {
        if (hostElement) {
            return hostElement;
        }
        return null;
    }

    function niceFloor(value) {
        if (!Number.isFinite(value) || value <= 0) {
            return 0;
        }
        var exponent = Math.floor(Math.log10(value));
        var base = Math.pow(10, exponent);
        var steps = [5, 2, 1];
        for (var i = 0; i < steps.length; i += 1) {
            var candidate = steps[i] * base;
            if (candidate <= value) {
                return candidate;
            }
        }
        return base;
    }

    function formatDisplayValue(value) {
        if (!Number.isFinite(value)) {
            return "";
        }
        if (Math.abs(value - Math.round(value)) < 1e-6) {
            return String(Math.round(value));
        }
        if (value < 1) {
            return String(Number.parseFloat(value.toFixed(2)));
        }
        return String(Number.parseFloat(value.toFixed(1)));
    }

    function metersToFeet(value) {
        return value * FEET_PER_METER;
    }

    function feetToMeters(value) {
        return value / FEET_PER_METER;
    }

    function metersToMiles(value) {
        return value / METERS_PER_MILE;
    }

    function milesToMeters(value) {
        return value * METERS_PER_MILE;
    }

    function selectScaleDistance(targetMeters, unitSystem) {
        if (!Number.isFinite(targetMeters) || targetMeters <= 0) {
            return null;
        }

        if (unitSystem === "english") {
            var targetFeet = metersToFeet(targetMeters);
            if (targetFeet < ENGLISH_FEET_THRESHOLD) {
                var niceFeet = niceFloor(targetFeet);
                return niceFeet > 0 ? {
                    meters: feetToMeters(niceFeet),
                    label: formatDisplayValue(niceFeet) + " ft"
                } : null;
            }

            var targetMiles = metersToMiles(targetMeters);
            var niceMiles = niceFloor(targetMiles);
            return niceMiles > 0 ? {
                meters: milesToMeters(niceMiles),
                label: formatDisplayValue(niceMiles) + " mi"
            } : null;
        }

        if (targetMeters < 1000) {
            var niceMeters = niceFloor(targetMeters);
            return niceMeters > 0 ? {
                meters: niceMeters,
                label: formatDisplayValue(niceMeters) + " m"
            } : null;
        }

        var targetKilometers = targetMeters / 1000;
        var niceKilometers = niceFloor(targetKilometers);
        return niceKilometers > 0 ? {
            meters: niceKilometers * 1000,
            label: formatDisplayValue(niceKilometers) + " km"
        } : null;
    }

    function toLatLng(coordinate) {
        if (!coordinate || coordinate.length < 2) {
            return null;
        }
        var lng = Number(coordinate[0]);
        var lat = Number(coordinate[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return null;
        }
        return { lat: lat, lng: lng };
    }

    function resolveUnitSystem(preferences) {
        if (preferences && preferences.distance === "mi") {
            return "english";
        }
        return "si";
    }

    function ensureScaleControl(options) {
        var existing = options.scaleControl || null;
        var hostElement = getHostElement(options.hostElement);

        if (existing || !hostElement || typeof document === "undefined") {
            return existing;
        }

        var root = document.createElement("div");
        root.className = "wc-map-scale-control";
        root.setAttribute("data-map-scale-control", "true");
        root.setAttribute("aria-hidden", "true");
        root.hidden = true;

        var label = document.createElement("div");
        label.className = "wc-map-scale-control__label";

        var bar = document.createElement("div");
        bar.className = "wc-map-scale-control__bar";

        var line = document.createElement("span");
        line.className = "wc-map-scale-control__line";

        bar.appendChild(line);
        root.appendChild(label);
        root.appendChild(bar);
        hostElement.appendChild(root);

        var currentUnitSystem = "si";

        function applyPreferences(preferences) {
            currentUnitSystem = resolveUnitSystem(preferences);
        }

        function update() {
            var getCanvasSize = options.getCanvasSize;
            var getBounds = options.getBounds;
            var getCenter = options.getCenter;
            var calculateDistanceMeters = options.calculateDistanceMeters;
            var unproject = options.unproject;

            var size = typeof getCanvasSize === "function" ? getCanvasSize() : null;
            var widthPx = size && Number.isFinite(size.width) ? size.width : 0;
            if (!(widthPx > 0) || typeof getBounds !== "function" || typeof getCenter !== "function" || typeof calculateDistanceMeters !== "function") {
                root.hidden = true;
                return;
            }

            var maxWidthPx = Math.min(
                Number.isFinite(options.maxWidthPx) ? options.maxWidthPx : DEFAULT_MAX_WIDTH_PX,
                Math.max(0, widthPx - 96)
            );
            if (!(maxWidthPx >= MIN_VISIBLE_WIDTH_PX)) {
                root.hidden = true;
                return;
            }

            var targetMeters = 0;
            if (typeof unproject === "function") {
                var screenY = Math.max(0, size.height / 2);
                var startLatLng = toLatLng(unproject([0, screenY]));
                var endLatLng = toLatLng(unproject([maxWidthPx, screenY]));
                if (startLatLng && endLatLng) {
                    targetMeters = calculateDistanceMeters(startLatLng, endLatLng);
                }
            }

            if (!(targetMeters > 0)) {
                var bounds = getBounds();
                var center = getCenter();
                if (!bounds || !center || typeof bounds.getSouthWest !== "function" || typeof bounds.getNorthEast !== "function") {
                    root.hidden = true;
                    return;
                }

                var southWest = bounds.getSouthWest();
                var northEast = bounds.getNorthEast();
                if (!southWest || !northEast) {
                    root.hidden = true;
                    return;
                }

                var fullWidthMeters = calculateDistanceMeters(
                    { lat: center.lat, lng: southWest.lng },
                    { lat: center.lat, lng: northEast.lng }
                );
                if (!(fullWidthMeters > 0)) {
                    root.hidden = true;
                    return;
                }
                targetMeters = fullWidthMeters * (maxWidthPx / widthPx);
            }

            var metersPerPixel = targetMeters / maxWidthPx;
            if (!(metersPerPixel > 0)) {
                root.hidden = true;
                return;
            }

            var scaleDistance = selectScaleDistance(targetMeters, currentUnitSystem);
            if (!scaleDistance || !(scaleDistance.meters > 0)) {
                root.hidden = true;
                return;
            }

            var renderedWidthPx = Math.round(scaleDistance.meters / metersPerPixel);
            if (!(renderedWidthPx >= MIN_VISIBLE_WIDTH_PX)) {
                root.hidden = true;
                return;
            }

            label.textContent = scaleDistance.label;
            line.style.width = renderedWidthPx + "px";
            root.hidden = false;
        }

        function handlePreferenceChange(event) {
            var detail = event && event.detail ? event.detail : {};
            applyPreferences(detail.preferences || null);
            update();
        }

        document.addEventListener("unitizer:preferences-changed", handlePreferenceChange);

        if (options.unitizerClient && typeof options.unitizerClient.getPreferencePayload === "function") {
            applyPreferences(options.unitizerClient.getPreferencePayload());
        } else if (typeof window !== "undefined" && window.UnitizerClient) {
            if (typeof window.UnitizerClient.getClientSync === "function") {
                var syncClient = window.UnitizerClient.getClientSync();
                if (syncClient && typeof syncClient.getPreferencePayload === "function") {
                    applyPreferences(syncClient.getPreferencePayload());
                }
            }
            if (typeof window.UnitizerClient.ready === "function") {
                window.UnitizerClient.ready().then(function (client) {
                    if (client && typeof client.getPreferencePayload === "function") {
                        applyPreferences(client.getPreferencePayload());
                        update();
                    }
                }).catch(function (error) {
                    console.warn("[Map Scale] Failed to read UnitizerClient preferences", error);
                });
            }
        }

        return {
            root: root,
            label: label,
            bar: bar,
            line: line,
            update: update,
            destroy: function () {
                document.removeEventListener("unitizer:preferences-changed", handlePreferenceChange);
                if (root.parentNode) {
                    root.parentNode.removeChild(root);
                }
            },
            getUnitSystem: function () {
                return currentUnitSystem;
            }
        };
    }

    return {
        ensureScaleControl: ensureScaleControl
    };
})();

window.WCMapGlScaleControl = WCMapGlScaleControl;

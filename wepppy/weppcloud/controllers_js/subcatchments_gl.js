/* ----------------------------------------------------------------------------
 * SubcatchmentDelineation (Deck.gl stub)
 * ----------------------------------------------------------------------------
 */
var SubcatchmentDelineation = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "subcatchment:build:started",
        "subcatchment:build:completed",
        "subcatchment:build:error",
        "subcatchment:map:mode",
        "subcatchment:report:loaded",
        "subcatchment:legend:updated"
    ];

    function ensureEvents() {
        var events = window.WCEvents;
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("SubcatchmentDelineation GL stub requires WCEvents helpers.");
        }
        return events;
    }

    function warnNotImplemented(action) {
        console.warn("SubcatchmentDelineation GL stub: " + action + " not implemented.");
    }

    function createInstance() {
        var events = ensureEvents();
        var emitterBase = events.createEmitter();
        var emitter = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var sub = {
            events: emitter,
            _cmapMode: "default",
            bootstrap: function bootstrap() {
                return null;
            },
            enableColorMap: function (mode) {
                if (mode) {
                    sub._cmapMode = mode;
                }
                warnNotImplemented("enableColorMap");
            },
            setColorMap: function (mode) {
                if (mode) {
                    sub._cmapMode = mode;
                }
                warnNotImplemented("setColorMap");
            },
            getCmapMode: function () {
                return sub._cmapMode;
            },
            prefetchLossMetrics: function () {
                warnNotImplemented("prefetchLossMetrics");
            },
            onMapChange: function () {
                return null;
            },
            show: function () {
                return null;
            },
            triggerEvent: function (eventName, payload) {
                if (sub.events && typeof sub.events.emit === "function") {
                    sub.events.emit(eventName, payload || {});
                }
            }
        };

        return sub;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}());

window.SubcatchmentDelineation = SubcatchmentDelineation;

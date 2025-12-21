/* ----------------------------------------------------------------------------
 * ChannelDelineation (Deck.gl stub)
 * ----------------------------------------------------------------------------
 */
var ChannelDelineation = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "channel:build:started",
        "channel:build:completed",
        "channel:build:error",
        "channel:map:updated",
        "channel:extent:mode",
        "channel:report:loaded",
        "channel:layers:loaded"
    ];

    function ensureEvents() {
        var events = window.WCEvents;
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("ChannelDelineation GL stub requires WCEvents helpers.");
        }
        return events;
    }

    function warnNotImplemented(action) {
        console.warn("ChannelDelineation GL stub: " + action + " not implemented.");
    }

    function createInstance() {
        var events = ensureEvents();
        var emitterBase = events.createEmitter();
        var emitter = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var channel = {
            events: emitter,
            bootstrap: function bootstrap() {
                return null;
            },
            onMapChange: function () {
                return null;
            },
            show: function () {
                return null;
            },
            refreshLayers: function () {
                warnNotImplemented("refreshLayers");
            }
        };

        return channel;
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

window.ChannelDelineation = ChannelDelineation;

/* ----------------------------------------------------------------------------
 * LanduseModify (Deck.gl stub)
 * ----------------------------------------------------------------------------
 */
var LanduseModify = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "landuse:modify:started",
        "landuse:modify:completed",
        "landuse:modify:error",
        "landuse:selection:changed",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureEvents() {
        var events = window.WCEvents;
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("LanduseModify GL stub requires WCEvents helpers.");
        }
        return events;
    }

    function warnNotImplemented(action) {
        console.warn("LanduseModify GL stub: " + action + " not implemented.");
    }

    function createInstance() {
        var events = ensureEvents();
        var emitterBase = events.createEmitter();
        var emitter = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var modify = {
            events: emitter,
            bootstrap: function bootstrap() {
                return null;
            },
            enableSelection: function () {
                warnNotImplemented("enableSelection");
            },
            disableSelection: function () {
                warnNotImplemented("disableSelection");
            },
            clearSelection: function () {
                warnNotImplemented("clearSelection");
            },
            triggerEvent: function (eventName, payload) {
                if (modify.events && typeof modify.events.emit === "function") {
                    modify.events.emit(eventName, payload || {});
                }
            }
        };

        return modify;
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

window.LanduseModify = LanduseModify;

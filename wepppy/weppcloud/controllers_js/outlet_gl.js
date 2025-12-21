/* ----------------------------------------------------------------------------
 * Outlet (Deck.gl stub)
 * ----------------------------------------------------------------------------
 */
var Outlet = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "outlet:mode:change",
        "outlet:cursor:toggle",
        "outlet:set:start",
        "outlet:set:queued",
        "outlet:set:success",
        "outlet:set:error",
        "outlet:display:refresh"
    ];

    function ensureEvents() {
        var events = window.WCEvents;
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Outlet GL stub requires WCEvents helpers.");
        }
        return events;
    }

    function warnNotImplemented(action) {
        console.warn("Outlet GL stub: " + action + " not implemented.");
    }

    function createInstance() {
        var events = ensureEvents();
        var emitterBase = events.createEmitter();
        var emitter = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var outlet = {
            events: emitter,
            bootstrap: function bootstrap() {
                return null;
            },
            remove: function () {
                warnNotImplemented("remove");
            },
            triggerEvent: function (eventName, payload) {
                if (outlet.events && typeof outlet.events.emit === "function") {
                    outlet.events.emit(eventName, payload || {});
                }
            }
        };

        return outlet;
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

window.Outlet = Outlet;

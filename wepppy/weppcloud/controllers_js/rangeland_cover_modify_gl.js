/* ----------------------------------------------------------------------------
 * RangelandCoverModify (Deck.gl stub)
 * ----------------------------------------------------------------------------
 */
var RangelandCoverModify = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "rangeland:modify:loaded",
        "rangeland:modify:selection:changed",
        "rangeland:modify:run:started",
        "rangeland:modify:run:completed",
        "rangeland:modify:run:error",
        "rangeland:modify:error",
        "job:started",
        "job:progress",
        "job:completed",
        "job:error",
        "RANGELAND_COVER_MODIFY_TASK_COMPLETED"
    ];

    function ensureEvents() {
        var events = window.WCEvents;
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("RangelandCoverModify GL stub requires WCEvents helpers.");
        }
        return events;
    }

    function warnNotImplemented(action) {
        console.warn("RangelandCoverModify GL stub: " + action + " not implemented.");
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

window.RangelandCoverModify = RangelandCoverModify;

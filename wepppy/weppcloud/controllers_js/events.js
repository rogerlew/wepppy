(function (global) {
    "use strict";

    function createEmitter() {
        var listeners = Object.create(null);

        function getBucket(event) {
            if (!event) {
                throw new Error("Emitter event name is required.");
            }
            if (!listeners[event]) {
                listeners[event] = [];
            }
            return listeners[event];
        }

        function on(event, handler) {
            if (typeof handler !== "function") {
                throw new Error("Emitter.on requires a handler function.");
            }
            var bucket = getBucket(event);
            bucket.push(handler);
            return function unsubscribe() {
                off(event, handler);
            };
        }

        function off(event, handler) {
            var bucket = listeners[event];
            if (!bucket || bucket.length === 0) {
                return;
            }
            if (!handler) {
                listeners[event] = [];
                return;
            }
            listeners[event] = bucket.filter(function (existing) {
                return existing !== handler;
            });
        }

        function once(event, handler) {
            if (typeof handler !== "function") {
                throw new Error("Emitter.once requires a handler function.");
            }
            var unsubscribe;
            function wrapped(payload) {
                if (unsubscribe) {
                    unsubscribe();
                }
                handler(payload);
            }
            unsubscribe = on(event, wrapped);
            return unsubscribe;
        }

        function emit(event, payload) {
            var bucket = listeners[event];
            if (!bucket || bucket.length === 0) {
                return false;
            }
            bucket.slice().forEach(function (handler) {
                try {
                    handler(payload);
                } catch (err) {
                    console.error("Emitter handler error for event '" + event + "':", err);
                }
            });
            return true;
        }

        function listenerCount(event) {
            if (event) {
                var bucket = listeners[event];
                return bucket ? bucket.length : 0;
            }
            return Object.keys(listeners).reduce(function (count, key) {
                return count + (listeners[key] ? listeners[key].length : 0);
            }, 0);
        }

        return {
            on: on,
            off: off,
            once: once,
            emit: emit,
            listenerCount: listenerCount
        };
    }

    function emitDom(target, eventName, detail, options) {
        if (!target) {
            throw new Error("emitDom requires a target element or selector.");
        }
        var element = null;
        if (global.WCDom && typeof global.WCDom.ensureElement === "function") {
            element = global.WCDom.ensureElement(target, "emitDom target not found.");
        } else if (global.document) {
            if (typeof target === "string") {
                element = global.document.querySelector(target);
            } else if (global.Element && target instanceof global.Element) {
                element = target;
            }
        }
        if (!element) {
            throw new Error("emitDom target not found.");
        }
        var opts = options || {};
        var bubbles = opts.bubbles !== undefined ? opts.bubbles : true;
        var cancelable = opts.cancelable !== undefined ? opts.cancelable : true;
        var event;
        try {
            event = new CustomEvent(eventName, {
                detail: detail,
                bubbles: bubbles,
                cancelable: cancelable
            });
        } catch (err) {
            event = global.document.createEvent("CustomEvent");
            event.initCustomEvent(eventName, bubbles, cancelable, detail);
        }
        element.dispatchEvent(event);
        return event;
    }

    function forward(sourceEmitter, sourceEvent, targetEmitter, targetEvent) {
        if (!sourceEmitter || typeof sourceEmitter.on !== "function") {
            throw new Error("forward requires a source emitter.");
        }
        if (!targetEmitter || typeof targetEmitter.emit !== "function") {
            throw new Error("forward requires a target emitter.");
        }
        var eventName = targetEvent || sourceEvent;
        return sourceEmitter.on(sourceEvent, function (payload) {
            targetEmitter.emit(eventName, payload);
        });
    }

    // Wrap an emitter with an allowlist of event names and optional development-time warnings.
    function useEventMap(events, emitter) {
        var allowed = Array.isArray(events)
            ? events.slice()
            : (events && typeof events === "object" ? Object.keys(events) : []);
        var set = new Set(allowed);
        var baseEmitter = emitter && typeof emitter.on === "function" ? emitter : createEmitter();
        var isDev = Boolean(global && (
            global.__WEPPCLOUD_DEV__ ||
            global.__DEV__ ||
            (global.process && global.process.env && global.process.env.NODE_ENV === "development")
        ));

        function guard(event) {
            if (set.size === 0) {
                return;
            }
            if (!set.has(event) && isDev && global.console && typeof global.console.warn === "function") {
                global.console.warn("Attempted to use unknown event '" + event + "'.");
            }
        }

        return {
            on: function (event, handler) {
                guard(event);
                return baseEmitter.on(event, handler);
            },
            once: function (event, handler) {
                guard(event);
                return baseEmitter.once(event, handler);
            },
            off: function (event, handler) {
                guard(event);
                baseEmitter.off(event, handler);
            },
            emit: function (event, payload) {
                guard(event);
                return baseEmitter.emit(event, payload);
            },
            listenerCount: baseEmitter.listenerCount,
            raw: baseEmitter
        };
    }

    global.WCEvents = {
        createEmitter: createEmitter,
        emitDom: emitDom,
        forward: forward,
        useEventMap: useEventMap
    };
})(typeof window !== "undefined" ? window : this);

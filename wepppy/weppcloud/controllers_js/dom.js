(function (global) {
    "use strict";

    var doc = global.document;
    var DISPLAY_DATA_KEY = "wcDisplay";
    var delegateRegistry = new WeakMap();
    var DocumentFragmentCtor = global.DocumentFragment;

    function assertDocument() {
        if (!doc) {
            throw new Error("Document context unavailable.");
        }
        return doc;
    }

    function isElement(value) {
        return Boolean(global.Element && value instanceof global.Element);
    }

    function resolveContext(context) {
        if (!context) {
            return assertDocument();
        }
        if (context === doc || context === global) {
            return assertDocument();
        }
        if (isElement(context) || (DocumentFragmentCtor && context instanceof DocumentFragmentCtor)) {
            return context;
        }
        throw new Error("Invalid context supplied to WCDom.");
    }

    function resolveElement(target, context) {
        if (!target) {
            return null;
        }
        if (isElement(target)) {
            return target;
        }
        if (typeof target === "string") {
            var ctx = resolveContext(context);
            return ctx.querySelector(target);
        }
        return null;
    }

    function ensureElement(target, message) {
        var element = resolveElement(target);
        if (!element) {
            throw new Error(message || "Unable to resolve element.");
        }
        return element;
    }

    function qs(target, context) {
        var element = resolveElement(target, context);
        if (target && !element && typeof target === "string") {
            return null;
        }
        if (!target && !element) {
            return null;
        }
        if (!element) {
            throw new Error("WCDom.qs received an unsupported target.");
        }
        return element;
    }

    function qsa(target, context) {
        if (!target) {
            return [];
        }
        if (Array.isArray(target)) {
            return target.filter(isElement);
        }
        if (typeof target.length === "number" && typeof target.item === "function") {
            return Array.prototype.slice.call(target).filter(isElement);
        }
        if (typeof target === "string") {
            var ctx = resolveContext(context);
            var nodeList = ctx.querySelectorAll(target);
            return Array.prototype.slice.call(nodeList);
        }
        if (isElement(target)) {
            return [target];
        }
        throw new Error("WCDom.qsa expects a selector string or element.");
    }

    function findClosest(element, selector, boundary) {
        if (!element || typeof selector !== "string") {
            return null;
        }
        var current = element;
        while (current && current !== boundary && current.nodeType === 1) {
            if (typeof current.matches === "function" && current.matches(selector)) {
                return current;
            }
            current = current.parentElement;
        }
        if (boundary && boundary !== doc && typeof boundary.matches === "function" && boundary.matches(selector)) {
            return boundary;
        }
        return null;
    }

    // Attach a delegated listener that forwards events whose targets match `selector`.
    function delegate(root, eventName, selector, handler, options) {
        if (typeof eventName !== "string" || !eventName) {
            throw new Error("delegate requires a valid event name.");
        }
        if (typeof selector !== "string" || !selector) {
            throw new Error("delegate requires a selector string.");
        }
        if (typeof handler !== "function") {
            throw new Error("delegate requires a handler function.");
        }

        var element;
        if (root === doc || root === global) {
            element = assertDocument();
        } else if (DocumentFragmentCtor && root instanceof DocumentFragmentCtor) {
            element = root;
        } else {
            element = ensureElement(root, "Delegate root element not found.");
        }
        var listener = function (event) {
            if (!event || !event.target) {
                return;
            }
            var matched = findClosest(event.target, selector, element);
            if (!matched) {
                return;
            }
            handler.call(matched, event, matched);
        };

        element.addEventListener(eventName, listener, options || false);

        var registry = delegateRegistry.get(element);
        if (!registry) {
            registry = [];
            delegateRegistry.set(element, registry);
        }
        registry.push({
            event: eventName,
            selector: selector,
            handler: handler,
            listener: listener,
            options: options || false
        });

        return function unsubscribe() {
            element.removeEventListener(eventName, listener, options || false);
            var entries = delegateRegistry.get(element);
            if (!entries) {
                return;
            }
            delegateRegistry.set(
                element,
                entries.filter(function (entry) {
                    return entry.listener !== listener;
                })
            );
        };
    }

    function setText(target, value) {
        var element = resolveElement(target);
        if (!element) {
            return null;
        }
        element.textContent = value === undefined || value === null ? "" : String(value);
        return element;
    }

    function setHTML(target, html) {
        var element = resolveElement(target);
        if (!element) {
            return null;
        }
        element.innerHTML = html === undefined || html === null ? "" : String(html);
        return element;
    }

    function show(target, options) {
        var element = resolveElement(target);
        if (!element) {
            return null;
        }
        element.hidden = false;
        var desiredDisplay = options && options.display ? String(options.display) : null;
        if (desiredDisplay) {
            element.dataset[DISPLAY_DATA_KEY] = desiredDisplay;
            element.style.display = desiredDisplay;
        } else if (element.dataset[DISPLAY_DATA_KEY]) {
            element.style.display = element.dataset[DISPLAY_DATA_KEY];
        } else if (element.style.display === "none") {
            element.style.removeProperty("display");
        }
        return element;
    }

    function hide(target) {
        var element = resolveElement(target);
        if (!element) {
            return null;
        }
        element.hidden = true;
        if (element.dataset[DISPLAY_DATA_KEY]) {
            element.style.display = "none";
        } else {
            element.style.display = "none";
        }
        return element;
    }

    function toggle(target, force, options) {
        var element = resolveElement(target);
        if (!element) {
            return null;
        }
        var shouldShow = typeof force === "boolean" ? force : element.hidden || element.style.display === "none";
        return shouldShow ? show(element, options) : hide(element);
    }

    function addClass(target, className) {
        var element = resolveElement(target);
        if (!element || !className) {
            return element || null;
        }
        className.split(/\s+/).forEach(function (name) {
            if (name) {
                element.classList.add(name);
            }
        });
        return element;
    }

    function removeClass(target, className) {
        var element = resolveElement(target);
        if (!element || !className) {
            return element || null;
        }
        className.split(/\s+/).forEach(function (name) {
            if (name) {
                element.classList.remove(name);
            }
        });
        return element;
    }

    function toggleClass(target, className, force) {
        var element = resolveElement(target);
        if (!element || !className) {
            return element || null;
        }
        className.split(/\s+/).forEach(function (name) {
            if (!name) {
                return;
            }
            if (typeof force === "boolean") {
                element.classList.toggle(name, force);
            } else {
                element.classList.toggle(name);
            }
        });
        return element;
    }

    function ariaBusy(target, isBusy) {
        var element = resolveElement(target);
        if (!element) {
            return null;
        }
        if (isBusy) {
            element.setAttribute("aria-busy", "true");
        } else {
            element.removeAttribute("aria-busy");
        }
        return element;
    }

    global.WCDom = {
        qs: qs,
        qsa: qsa,
        ensureElement: ensureElement,
        delegate: delegate,
        setText: setText,
        setHTML: setHTML,
        show: show,
        hide: hide,
        toggle: toggle,
        addClass: addClass,
        removeClass: removeClass,
        toggleClass: toggleClass,
        ariaBusy: ariaBusy
    };
})(typeof window !== "undefined" ? window : this);

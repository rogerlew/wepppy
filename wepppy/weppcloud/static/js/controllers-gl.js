/* ----------------------------------------------------------------------------
 * Controllers (controllers-gl.js)
 * NOTE: Generated via build_controllers_js.py from
 *       wepppy/weppcloud/controllers_js/templates/*.js
 * Build date: 2025-12-21T08:42:17Z
 * See developer notes: wepppy/weppcloud/controllers_js/README.md
 * ----------------------------------------------------------------------------
 */
"use strict";
// globals for JSLint: $, L, polylabel, setTimeout, console

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

(function (global) {
    "use strict";

    var doc = global.document;
    var SAFE_CHECKBOX_VALUES = { on: true, true: true, false: true };

    function getDomHelpers() {
        return global.WCDom || null;
    }

    function toFormElement(form) {
        if (!form) {
            throw new Error("WCForms requires a form element or selector.");
        }
        if (global.HTMLFormElement && form instanceof global.HTMLFormElement) {
            return form;
        }
        if (typeof form === "string") {
            var dom = getDomHelpers();
            if (dom && typeof dom.ensureElement === "function") {
                var resolved = dom.ensureElement(form, "Form selector did not match any element.");
                if (resolved instanceof global.HTMLFormElement) {
                    return resolved;
                }
                throw new Error("Selector did not resolve to a form element.");
            }
            if (!doc) {
                throw new Error("Document context unavailable.");
            }
            var el = doc.querySelector(form);
            if (!el) {
                throw new Error("Form selector did not match any element.");
            }
            if (!(el instanceof global.HTMLFormElement)) {
                throw new Error("Selector did not resolve to a form element.");
            }
            return el;
        }
        if (form.nodeType === 1 && form.tagName && form.tagName.toLowerCase() === "form") {
            return form;
        }
        throw new Error("Unsupported form target.");
    }

    function toElementArray(form) {
        if (!form || !form.elements) {
            return [];
        }
        return Array.prototype.slice.call(form.elements);
    }

    function fieldType(field) {
        if (!field || !field.type) {
            return "";
        }
        return String(field.type).toLowerCase();
    }

    function shouldSkipField(field, includeDisabled) {
        if (!field || !field.name) {
            return true;
        }
        if (!includeDisabled && field.disabled) {
            return true;
        }
        var type = fieldType(field);
        if (field.tagName && field.tagName.toLowerCase() === "fieldset") {
            return true;
        }
        if (["submit", "button", "image", "reset"].indexOf(type) !== -1) {
            return true;
        }
        if (type === "file") {
            return true;
        }
        return false;
    }

    function appendValue(target, name, value) {
        if (Object.prototype.hasOwnProperty.call(target, name)) {
            var existing = target[name];
            if (Array.isArray(existing)) {
                if (Array.isArray(value)) {
                    value.forEach(function (item) {
                        existing.push(item);
                    });
                } else {
                    existing.push(value);
                }
            } else {
                if (Array.isArray(value)) {
                    target[name] = [existing].concat(value);
                } else {
                    target[name] = [existing, value];
                }
            }
        } else {
            target[name] = Array.isArray(value) ? value.slice() : value;
        }
    }

    function setValue(target, name, value) {
        target[name] = value;
    }

    function ensureArray(value) {
        if (Array.isArray(value)) {
            return value;
        }
        return [value];
    }

    function serializeFormToParams(form, includeDisabled) {
        var params = new URLSearchParams();
        toElementArray(form).forEach(function (field) {
            if (shouldSkipField(field, includeDisabled)) {
                return;
            }
            var type = fieldType(field);
            if (type === "checkbox" || type === "radio") {
                if (field.checked) {
                    params.append(field.name, field.value || "on");
                }
                return;
            }
            if (field.tagName && field.tagName.toLowerCase() === "select") {
                var options = field.options || [];
                for (var i = 0; i < options.length; i += 1) {
                    var option = options[i];
                    if (option.selected) {
                        params.append(field.name, option.value);
                    }
                }
                return;
            }
            params.append(field.name, field.value);
        });
        return params;
    }

    // Produce a plain object mirroring jQuery's multi-value semantics while normalizing checkboxes.
    function serializeFormToObject(form, includeDisabled) {
        var result = Object.create(null);
        var elements = toElementArray(form);
        var checkboxGroups = Object.create(null);

        elements.forEach(function (field) {
            if (shouldSkipField(field, includeDisabled)) {
                return;
            }
            var type = fieldType(field);
            if (type === "checkbox") {
                if (!checkboxGroups[field.name]) {
                    checkboxGroups[field.name] = [];
                }
                checkboxGroups[field.name].push(field);
                return;
            }
            if (type === "radio") {
                if (field.checked) {
                    setValue(result, field.name, field.value);
                } else if (!Object.prototype.hasOwnProperty.call(result, field.name)) {
                    setValue(result, field.name, null);
                }
                return;
            }
            if (field.tagName && field.tagName.toLowerCase() === "select") {
                var selectValues = [];
                var options = field.options || [];
                for (var i = 0; i < options.length; i += 1) {
                    var option = options[i];
                    if (option.selected) {
                        selectValues.push(option.value);
                    }
                }
                if (field.multiple) {
                    setValue(result, field.name, selectValues);
                } else if (selectValues.length > 0) {
                    setValue(result, field.name, selectValues[0]);
                } else {
                    setValue(result, field.name, null);
                }
                return;
            }
            appendValue(result, field.name, field.value);
        });

        Object.keys(checkboxGroups).forEach(function (name) {
            var group = checkboxGroups[name];
            if (!group || group.length === 0) {
                return;
            }
            if (group.length === 1 && SAFE_CHECKBOX_VALUES[group[0].value || "on"]) {
                setValue(result, name, Boolean(group[0].checked));
                return;
            }
            var values = [];
            group.forEach(function (field) {
                if (field.checked) {
                    values.push(field.value || "on");
                }
            });
            setValue(result, name, values);
        });

        return result;
    }

    function serializeFields(fields, format) {
        if (!Array.isArray(fields)) {
            throw new Error("serializeFields expects an array of field descriptors.");
        }
        var formatType = format || "url";
        if (formatType === "url") {
            var params = new URLSearchParams();
            fields.forEach(function (field) {
                if (!field || !field.name) {
                    return;
                }
                var type = field.type ? String(field.type).toLowerCase() : "";
                if (type === "checkbox") {
                    if (field.checked) {
                        params.append(field.name, field.value || "on");
                    }
                    return;
                }
                if (Array.isArray(field.value)) {
                    field.value.forEach(function (value) {
                        params.append(field.name, value);
                    });
                    return;
                }
                if (field.value !== undefined && field.value !== null) {
                    params.append(field.name, field.value);
                }
            });
            return params;
        }

        var result = Object.create(null);
        fields.forEach(function (field) {
            if (!field || !field.name) {
                return;
            }
            var type = field.type ? String(field.type).toLowerCase() : "";
            if (type === "checkbox") {
                if (field.checked === undefined) {
                    appendValue(result, field.name, Boolean(field.value));
                } else {
                    setValue(result, field.name, Boolean(field.checked));
                }
                return;
            }
            if (Array.isArray(field.value)) {
                appendValue(result, field.name, field.value.slice());
            } else {
                appendValue(result, field.name, field.value);
            }
        });
        return result;
    }

    function serializeForm(form, options) {
        var formElement = toFormElement(form);
        var opts = options || {};
        var format = opts.format || "url";
        var includeDisabled = Boolean(opts.includeDisabled);
        if (format === "url") {
            return serializeFormToParams(formElement, includeDisabled);
        }
        if (format === "object" || format === "json") {
            return serializeFormToObject(formElement, includeDisabled);
        }
        throw new Error("Unsupported serialization format: " + format);
    }

    function formToJSON(form) {
        return serializeForm(form, { format: "json" });
    }

    // Apply an object's values back onto the matching form controls (radios, checkboxes, selects, text).
    function applyValues(form, values) {
        if (!values || typeof values !== "object") {
            return;
        }
        var formElement = toFormElement(form);
        Object.keys(values).forEach(function (name) {
            var fields = formElement.elements.namedItem(name);
            if (!fields) {
                return;
            }
            var value = values[name];
            var isElement = fields instanceof global.Element;
            if (fields instanceof global.RadioNodeList || (fields.length && fields[0] && !isElement)) {
                var list = Array.prototype.slice.call(fields);
                list.forEach(function (field) {
                    var type = fieldType(field);
                    if (type === "checkbox") {
                        if (Array.isArray(value)) {
                            field.checked = value.indexOf(field.value) !== -1;
                        } else {
                            field.checked = Boolean(value);
                        }
                        return;
                    }
                    if (type === "radio") {
                        field.checked = String(field.value) === String(value);
                        return;
                    }
                    if (field.tagName && field.tagName.toLowerCase() === "select" && field.multiple) {
                        var targetValues = ensureArray(value).map(String);
                        Array.prototype.slice.call(field.options).forEach(function (option) {
                            option.selected = targetValues.indexOf(option.value) !== -1;
                        });
                        return;
                    }
                    field.value = value;
                });
                return;
            }
            var singleField = fields;
            if (singleField instanceof global.HTMLSelectElement && singleField.multiple) {
                var multiValues = ensureArray(value).map(String);
                Array.prototype.slice.call(singleField.options).forEach(function (option) {
                    option.selected = multiValues.indexOf(option.value) !== -1;
                });
                return;
            }
            var type = fieldType(singleField);
            if (type === "checkbox") {
                if (Array.isArray(value)) {
                    singleField.checked = value.indexOf(singleField.value) !== -1;
                } else {
                    singleField.checked = Boolean(value);
                }
                return;
            }
            if (type === "radio") {
                singleField.checked = String(singleField.value) === String(value);
                return;
            }
            if (singleField.tagName && singleField.tagName.toLowerCase() === "select" && singleField.multiple) {
                var valuesArray = ensureArray(value).map(String);
                Array.prototype.slice.call(singleField.options).forEach(function (option) {
                    option.selected = valuesArray.indexOf(option.value) !== -1;
                });
                return;
            }
            singleField.value = value === undefined || value === null ? "" : value;
        });
    }

    function readCookie(name) {
        if (!doc || !doc.cookie) {
            return null;
        }
        var escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        var pattern = new RegExp("(?:^|; )" + escapedName + "=([^;]*)");
        var match = doc.cookie.match(pattern);
        return match ? decodeURIComponent(match[1]) : null;
    }

    // Locate a CSRF token from globals, meta tags, the provided form, or well-known cookies.
    function findCsrfToken(form) {
        if (global.__csrfToken) {
            return global.__csrfToken;
        }
        if (global.csrfToken && typeof global.csrfToken === "function") {
            try {
                var token = global.csrfToken();
                if (token) {
                    return token;
                }
            } catch (err) {
                // ignore
            }
        }
        if (global.csrf_token && typeof global.csrf_token === "function") {
            try {
                var tokenFn = global.csrf_token();
                if (tokenFn) {
                    return tokenFn;
                }
            } catch (err) {
                // ignore
            }
        }
        if (doc) {
            var meta = doc.querySelector('meta[name="csrf-token"]');
            if (meta && meta.getAttribute("content")) {
                return meta.getAttribute("content");
            }
        }
        if (form) {
            try {
                var formElement = toFormElement(form);
                var field = formElement.querySelector('input[name="csrf_token"]');
                if (field && field.value) {
                    return field.value;
                }
            } catch (err) {
                // ignore
            }
        }
        var cookieToken = readCookie("csrftoken") || readCookie("csrf_token");
        if (cookieToken) {
            return cookieToken;
        }
        return null;
    }

    global.WCForms = {
        serializeForm: serializeForm,
        serializeFields: serializeFields,
        formToJSON: formToJSON,
        applyValues: applyValues,
        findCsrfToken: findCsrfToken
    };
})(typeof window !== "undefined" ? window : this);

(function (global) {
    "use strict";

    var SAFE_METHODS = ["GET", "HEAD", "OPTIONS", "TRACE"];
    var DEFAULT_ACCEPT = "application/json, text/plain;q=0.9";
    var DEFAULT_TIMEOUT_MS = 0;
    var doc = global.document;
    var http = {};

    function isAbsoluteUrl(url) {
        return /^([a-z][a-z\d+\-.]*:)?\/\//i.test(url);
    }

    function trimTrailingSlash(value) {
        return value ? value.replace(/\/+$/, "") : "";
    }

    function trimLeadingSlash(value) {
        return value ? value.replace(/^\/+/, "") : "";
    }

    function applySitePrefix(url) {
        if (!url) {
            throw new Error("WCHttp.request requires a URL.");
        }
        var prefix = typeof global.site_prefix === "string" ? global.site_prefix : "";
        if (!prefix || isAbsoluteUrl(url)) {
            return url;
        }
        var normalizedPrefix = trimTrailingSlash(prefix);
        var normalizedUrl = url;
        if (normalizedUrl.indexOf(normalizedPrefix) === 0) {
            return normalizedUrl;
        }
        if (normalizedUrl.charAt(0) === "/") {
            return normalizedPrefix + normalizedUrl;
        }
        return normalizedPrefix + "/" + normalizedUrl;
    }

    function createUrl(url, params) {
        var finalUrl = applySitePrefix(url);
        if (!params) {
            return finalUrl;
        }
        var urlObj;
        try {
            urlObj = new URL(finalUrl, global.location ? global.location.href : undefined);
        } catch (err) {
            urlObj = new URL(finalUrl, "http://localhost");
            finalUrl = urlObj.toString();
        }
        var searchParams = params instanceof URLSearchParams ? params : new URLSearchParams();
        if (!(params instanceof URLSearchParams) && typeof params === "object") {
            Object.keys(params).forEach(function (key) {
                var value = params[key];
                if (value === undefined || value === null) {
                    return;
                }
                if (Array.isArray(value)) {
                    value.forEach(function (item) {
                        searchParams.append(key, item);
                    });
                } else {
                    searchParams.append(key, value);
                }
            });
        }
        searchParams.forEach(function (value, key) {
            urlObj.searchParams.append(key, value);
        });
        return urlObj.toString();
    }

    function shouldSendCsrf(method) {
        return SAFE_METHODS.indexOf(method.toUpperCase()) === -1;
    }

    function readCookie(name) {
        if (!doc || !doc.cookie) {
            return null;
        }
        var escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        var pattern = new RegExp("(?:^|; )" + escapedName + "=([^;]*)");
        var match = doc.cookie.match(pattern);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function getCsrfToken(form) {
        if (global.WCForms && typeof global.WCForms.findCsrfToken === "function") {
            return global.WCForms.findCsrfToken(form);
        }
        if (global.__csrfToken) {
            return global.__csrfToken;
        }
        if (doc) {
            var meta = doc.querySelector('meta[name="csrf-token"]');
            if (meta && meta.getAttribute("content")) {
                return meta.getAttribute("content");
            }
        }
        return readCookie("csrftoken") || readCookie("csrf_token");
    }

    function HttpError(message, init) {
        if (!(this instanceof HttpError)) {
            return new HttpError(message, init);
        }
        init = init || {};
        this.name = "HttpError";
        this.message = message || "HTTP request failed";
        this.status = init.status || 0;
        this.statusText = init.statusText || "";
        this.url = init.url || null;
        this.detail = init.detail || null;
        this.body = init.body;
        this.response = init.response || null;
        this.cause = init.cause;
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, HttpError);
        } else {
            this.stack = new Error(this.message).stack;
        }
    }
    HttpError.prototype = Object.create(Error.prototype);
    HttpError.prototype.constructor = HttpError;

    function isHttpError(error) {
        return error instanceof HttpError || (error && error.name === "HttpError");
    }

    // Normalize request bodies, setting content-type as needed and supporting JSON, urlencoded, and FormData payloads.
    function normalizeBody(options, headers) {
        var method = options.method || "GET";
        var body = options.body;
        if (options.json !== undefined) {
            headers.set("Content-Type", "application/json");
            return JSON.stringify(options.json);
        }
        if (body === undefined || body === null) {
            return undefined;
        }
        if (body instanceof URLSearchParams) {
            headers.set("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8");
            return body.toString();
        }
        if (global.FormData && body instanceof global.FormData) {
            return body;
        }
        if (typeof body === "object" && !Array.isArray(body) && method.toUpperCase() !== "GET") {
            headers.set("Content-Type", "application/json");
            return JSON.stringify(body);
        }
        return body;
    }

    function mergeHeaders(headers, overrides) {
        if (!overrides) {
            return headers;
        }
        Object.keys(overrides).forEach(function (key) {
            headers.set(key, overrides[key]);
        });
        return headers;
    }

    // Merge a caller-supplied AbortSignal with an optional timeout so long requests stop cleanly.
    function createAbortController(userSignal, timeoutMs) {
        var controller = typeof AbortController === "function" ? new AbortController() : null;
        var timeoutId = null;
        var signal = null;

        if (controller) {
            signal = controller.signal;
            if (userSignal) {
                if (userSignal.aborted) {
                    controller.abort(userSignal.reason);
                } else {
                    userSignal.addEventListener("abort", function () {
                        if (!controller.signal.aborted) {
                            controller.abort(userSignal.reason);
                        }
                    });
                }
            }
            if (timeoutMs && timeoutMs > 0) {
                timeoutId = setTimeout(function () {
                    if (!controller.signal.aborted) {
                        controller.abort(new Error("Request timed out after " + timeoutMs + "ms"));
                    }
                }, timeoutMs);
            }
        } else {
            signal = userSignal || null;
            if (timeoutMs && timeoutMs > 0) {
                console.warn("AbortController not available; timeout cannot be enforced.");
            }
        }

        return {
            signal: signal,
            cancelTimeout: function () {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
            }
        };
    }

    function isJsonContentType(contentType) {
        if (!contentType) {
            return false;
        }
        return contentType.indexOf("application/json") !== -1 || contentType.indexOf("+json") !== -1;
    }

    function parseBody(response) {
        var contentType = response.headers && response.headers.get ? response.headers.get("content-type") || "" : "";
        if (!contentType) {
            return response.text().then(function (text) {
                return text ? text : null;
            });
        }
        if (isJsonContentType(contentType)) {
            return response.text().then(function (text) {
                if (!text) {
                    return null;
                }
                try {
                    return JSON.parse(text);
                } catch (err) {
                    console.warn("Failed to parse JSON response:", err);
                    return text;
                }
            });
        }
        if (contentType.indexOf("application/octet-stream") !== -1 || contentType.indexOf("image/") === 0) {
            return response.blob();
        }
        if (contentType.indexOf("text/") === 0) {
            return response.text();
        }
        return response.arrayBuffer ? response.arrayBuffer() : response.text();
    }

    function buildError(url, response, body, cause) {
        var message = "HTTP request failed";
        var detail = null;
        if (response) {
            message = "HTTP " + response.status + " " + (response.statusText || "");
            if (body && typeof body === "object") {
                detail = body.detail || body.message || body.error || body;
            } else if (body) {
                detail = body;
            }
        } else if (cause && cause.message) {
            message = cause.message;
        }
        return new HttpError(message, {
            status: response ? response.status : 0,
            statusText: response ? response.statusText : "",
            url: url,
            body: body,
            detail: detail,
            response: response || null,
            cause: cause
        });
    }

    function request(url, options) {
        var opts = options || {};
        var method = (opts.method || "GET").toUpperCase();
        var timeoutMs = typeof opts.timeoutMs === "number" ? opts.timeoutMs : DEFAULT_TIMEOUT_MS;
        var headers = new Headers();
        headers.set("Accept", DEFAULT_ACCEPT);
        mergeHeaders(headers, opts.headers || {});

        var finalUrl = createUrl(url, opts.params);
        var body = normalizeBody({ method: method, body: opts.body, json: opts.json }, headers);

        if (shouldSendCsrf(method) && !headers.has("X-CSRFToken")) {
            var csrfToken = getCsrfToken(opts.form);
            if (csrfToken) {
                headers.set("X-CSRFToken", csrfToken);
            }
        }

        var abort = createAbortController(opts.signal, timeoutMs);

        var fetchOptions = {
            method: method,
            headers: headers,
            credentials: opts.credentials || "same-origin"
        };

        if (abort.signal) {
            fetchOptions.signal = abort.signal;
        }

        if (body !== undefined) {
            fetchOptions.body = body;
        }

        return fetch(finalUrl, fetchOptions)
            .then(function (response) {
                abort.cancelTimeout();
                return parseBody(response).then(function (parsed) {
                    var payload = {
                        ok: response.ok,
                        status: response.status,
                        statusText: response.statusText,
                        headers: response.headers,
                        body: parsed,
                        response: response,
                        url: finalUrl
                    };
                    if (!response.ok) {
                        throw buildError(finalUrl, response, parsed);
                    }
                    return payload;
                });
            })
            .catch(function (error) {
                abort.cancelTimeout();
                if (isHttpError(error)) {
                    throw error;
                }
                if (error && error.name === "AbortError") {
                    throw new HttpError("Request aborted", {
                        url: finalUrl,
                        cause: error
                    });
                }
                throw buildError(finalUrl, null, null, error);
            });
    }

    function getJson(url, options) {
        return http.request(url, options || {}).then(function (result) {
            var body = result.body;
            if (body === null || body === undefined) {
                return body;
            }
            if (typeof body === "string") {
                try {
                    return JSON.parse(body);
                } catch (err) {
                    throw new HttpError("Expected JSON response.", {
                        url: result.url,
                        status: result.status,
                        statusText: result.statusText,
                        body: body,
                        cause: err,
                        response: result.response
                    });
                }
            }
            return body;
        });
    }

    function postJson(url, payload, options) {
        var opts = options ? Object.assign({}, options) : {};
        opts.method = opts.method || "POST";
        opts.json = payload;
        return http.request(url, opts);
    }

    function formDataToParams(formData) {
        var params = new URLSearchParams();
        formData.forEach(function (value, key) {
            params.append(key, value);
        });
        return params;
    }

    // Convert form payload inputs (objects, forms, FormData) into URLSearchParams ready for transport.
    function normalizeFormPayload(payload) {
        if (!payload) {
            return new URLSearchParams();
        }
        if (payload instanceof URLSearchParams) {
            return payload;
        }
        if (global.HTMLFormElement && payload instanceof global.HTMLFormElement) {
            if (global.WCForms && typeof global.WCForms.serializeForm === "function") {
                return global.WCForms.serializeForm(payload, { format: "url" });
            }
            return new URLSearchParams(new FormData(payload));
        }
        if (global.FormData && payload instanceof global.FormData) {
            return formDataToParams(payload);
        }
        if (typeof payload === "string") {
            return new URLSearchParams(payload);
        }
        if (typeof payload === "object") {
            if (global.WCForms && typeof global.WCForms.serializeFields === "function") {
                var fields = Object.keys(payload).map(function (name) {
                    var value = payload[name];
                    return { name: name, value: value };
                });
                return global.WCForms.serializeFields(fields, "url");
            }
            var params = new URLSearchParams();
            Object.keys(payload).forEach(function (key) {
                var value = payload[key];
                if (Array.isArray(value)) {
                    value.forEach(function (item) {
                        params.append(key, item);
                    });
                } else if (value !== undefined && value !== null) {
                    params.append(key, value);
                }
            });
            return params;
        }
        return new URLSearchParams();
    }

    function postForm(url, payload, options) {
        var params = normalizeFormPayload(payload);
        var opts = options ? Object.assign({}, options) : {};
        opts.method = opts.method || "POST";
        opts.body = params;
        return http.request(url, opts);
    }

    http.request = request;
    http.getJson = getJson;
    http.postJson = postJson;
    http.postForm = postForm;
    http.HttpError = HttpError;
    http.isHttpError = isHttpError;
    http.getCsrfToken = getCsrfToken;

    global.WCHttp = http;
})(typeof window !== "undefined" ? window : this);

(function (global) {
    "use strict";

    var http = global.WCHttp;
    if (!http || !http.request || http.request.__wcRecorderWrapped) {
        return;
    }

    var recorderConfig = global.__WEPP_RECORDER_CONFIG || {};
    var recorder = global.WCRecorder || (function () {
        var queue = [];
        var flushTimer = null;
        var DEFAULT_ENDPOINT = "recorder/events";
        var DEFAULT_BATCH_SIZE = 10;
        var DEFAULT_FLUSH_INTERVAL_MS = 200;
        var rand = Math.random().toString(36).slice(2);
        var sessionId = recorderConfig.sessionId || (Date.now().toString(36) + "-" + rand);

        function nowIso() {
            try {
                return new Date().toISOString();
            } catch (err) {
                return null;
            }
        }

        function getConfig() {
            return recorderConfig;
        }

        function setConfig(newConfig) {
            if (!newConfig || typeof newConfig !== "object") {
                return;
            }
            recorderConfig = Object.assign({}, recorderConfig, newConfig);
        }

        function isEnabled() {
            var cfg = getConfig();
            if (cfg.enabled === false) {
                return false;
            }
            return true;
        }

        function resolveSitePrefix() {
            var prefix = typeof global.site_prefix === "string" ? global.site_prefix : "";
            if (!prefix) {
                return "";
            }
            if (prefix.charAt(0) !== "/") {
                prefix = "/" + prefix;
            }
            return prefix.replace(/\/+$/, "");
        }

        function buildRunScopedEndpoint(endpoint) {
            if (typeof endpoint !== "string" || !endpoint) {
                endpoint = DEFAULT_ENDPOINT;
            }

            if (/^https?:\/\//i.test(endpoint) || endpoint.charAt(0) === "/") {
                return endpoint;
            }

            var scoped = endpoint;
            if (typeof global.url_for_run === "function") {
                try {
                    var candidate = global.url_for_run(endpoint);
                    if (candidate) {
                        scoped = candidate;
                    }
                } catch (err) {
                    /* noop */
                }
            }
            if (scoped.charAt(0) !== "/") {
                scoped = "/" + scoped;
            }
            var prefix = resolveSitePrefix();
            if (prefix && scoped.indexOf(prefix + "/") !== 0) {
                scoped = prefix + scoped;
            }
            return scoped;
        }

        function getEndpoint() {
            var endpoint = recorderConfig.endpoint;
            if (typeof endpoint !== "string" || !endpoint) {
                endpoint = DEFAULT_ENDPOINT;
            }
            return buildRunScopedEndpoint(endpoint);
        }

        function normaliseBlob(payload) {
            if (typeof payload !== "string") {
                return payload;
            }
            try {
                return new Blob([payload], { type: "application/json" });
            } catch (err) {
                return payload;
            }
        }

        function send(payload) {
            if (typeof navigator !== "undefined" && navigator.sendBeacon) {
                return navigator.sendBeacon(getEndpoint(), normaliseBlob(payload));
            }

            if (typeof global.fetch === "function") {
                try {
                    global.fetch(getEndpoint(), {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: payload,
                        keepalive: true,
                        __skipRecorder: true
                    }).catch(function () {
                        /* noop */
                    });
                } catch (err) {
                    /* noop */
                }
            }
        }

        function flushQueue() {
            flushTimer = null;
            if (!queue.length) {
                return;
            }
            var events = queue.splice(0, queue.length);
            try {
                send(JSON.stringify({ events: events }));
            } catch (err) {
                /* noop */
            }
        }

        function scheduleFlush() {
            if (flushTimer !== null) {
                return;
            }
            var interval = recorderConfig.flushIntervalMs || DEFAULT_FLUSH_INTERVAL_MS;
            flushTimer = global.setTimeout(flushQueue, interval);
        }

        function enqueue(event) {
            if (!isEnabled()) {
                return;
            }
            queue.push(event);
            var maxBatch = recorderConfig.batchSize || DEFAULT_BATCH_SIZE;
            if (queue.length >= maxBatch) {
                if (flushTimer !== null) {
                    global.clearTimeout(flushTimer);
                    flushTimer = null;
                }
                flushQueue();
            } else {
                scheduleFlush();
            }
        }

        function enrichEvent(stage, payload, base) {
            var event = Object.assign({}, base || {});
            event.stage = stage;
            event.timestamp = nowIso();
            event.sessionId = sessionId;
            event.rootUrl = global.location && global.location.origin ? global.location.origin : null;
            if (typeof global.runId === "string" && global.runId) {
                event.runId = global.runId;
            }
            if (typeof global.config === "string" && global.config) {
                event.config = global.config;
            }
            if (typeof global.pup_relpath === "string" && global.pup_relpath) {
                event.pup = global.pup_relpath;
            }
            if (payload && typeof payload === "object") {
                Object.keys(payload).forEach(function (key) {
                    if (payload[key] !== undefined) {
                        event[key] = payload[key];
                    }
                });
            }
            return event;
        }

        function emit(stage, payload, base) {
            enqueue(enrichEvent(stage, payload, base));
        }

        function handleVisibilityChange() {
            if (queue.length) {
                flushQueue();
            }
        }

        if (typeof global.addEventListener === "function") {
            global.addEventListener("beforeunload", handleVisibilityChange, { capture: true });
            global.addEventListener("pagehide", handleVisibilityChange, { capture: true });
        }

        return {
            emit: emit,
            setConfig: setConfig,
            getConfig: getConfig,
            isEnabled: isEnabled,
            _queueSize: function () {
                return queue.length;
            }
        };
    })();

    global.WCRecorder = recorder;

    function detectCategory(method, options) {
        if (method === "GET") {
            return "http_request";
        }
        if (options && options.body && global.FormData && options.body instanceof global.FormData) {
            return "file_upload";
        }
        return "http_request";
    }

    function isFileLike(value) {
        if (!value || typeof value !== "object") {
            return false;
        }
        if (typeof global.File === "function" && value instanceof global.File) {
            return true;
        }
        if (typeof global.Blob === "function" && value instanceof global.Blob) {
            return true;
        }
        var tag = Object.prototype.toString.call(value);
        if (tag === "[object File]" || tag === "[object Blob]") {
            return true;
        }
        if (typeof value.arrayBuffer === "function" || typeof value.stream === "function") {
            return true;
        }
        return false;
    }

    function serialiseFormValue(value) {
        if (value === undefined || value === null) {
            return "";
        }
        if (typeof value === "string") {
            return value;
        }
        try {
            return String(value);
        } catch (err) {
            return "";
        }
    }

    function summariseBody(options, method) {
        var summary = {
            hasBody: false
        };
        if (!options) {
            return summary;
        }
        var body = options.body;
        if (options.json !== undefined) {
            summary.hasBody = true;
            try {
                var serialised = JSON.stringify(options.json);
                summary.bodyPreview = serialised.slice(0, 256);
                summary.jsonPayload = serialised;
            } catch (err) {
                summary.bodyPreview = "[unserializable json]";
            }
            summary.bodyType = "json";
            return summary;
        }
        if (body === undefined || body === null || method === "GET") {
            return summary;
        }

        summary.hasBody = true;
        if (global.FormData && body instanceof global.FormData) {
            summary.bodyType = "form-data";
            var keys = [];
            var values = {};
            var hasValues = false;
            try {
                body.forEach(function (value, key) {
                    if (keys.indexOf(key) === -1) {
                        keys.push(key);
                    }
                    if (!isFileLike(value)) {
                        var nextValue = serialiseFormValue(value);
                        if (Object.prototype.hasOwnProperty.call(values, key)) {
                            if (!Array.isArray(values[key])) {
                                values[key] = [values[key]];
                            }
                            values[key].push(nextValue);
                        } else {
                            values[key] = nextValue;
                        }
                        hasValues = true;
                    }
                });
            } catch (err) {
                /* noop */
            }
            summary.formKeys = keys;
            if (hasValues) {
                summary.formValues = values;
            }
            return summary;
        }
        if (typeof body === "string") {
            summary.bodyType = "text";
            summary.bodyLength = body.length;
            summary.bodyPreview = body.slice(0, 256);
            return summary;
        }
        summary.bodyType = typeof body;
        return summary;
    }

    function normaliseError(error) {
        if (!error) {
            return null;
        }
        if (typeof error === "string") {
            return error;
        }
        var detail = {
            name: error.name || null,
            message: error.message || null
        };
        if (typeof error.status === "number") {
            detail.status = error.status;
        }
        if (error.detail) {
            detail.detail = error.detail;
        }
        return detail;
    }

    var originalRequest = http.request;
    var counter = 0;

    function nextRequestId() {
        counter += 1;
        return Date.now().toString(36) + "-" + counter.toString(36);
    }

    http.request = function (url, options) {
        var opts = options || {};
        if (opts.__skipRecorder) {
            return originalRequest.call(this, url, opts);
        }

        var method = (opts.method || "GET").toUpperCase();
        var startedAt = (global.performance && typeof global.performance.now === "function")
            ? global.performance.now()
            : Date.now();
        var requestId = nextRequestId();
        var category = detectCategory(method, opts);

        recorder.emit("request", {
            id: requestId,
            method: method,
            endpoint: url,
            category: category,
            requestMeta: summariseBody(opts, method),
            params: opts.params ? Object.keys(opts.params) : undefined
        });

        return originalRequest.call(this, url, opts).then(function (result) {
            var endedAt = (global.performance && typeof global.performance.now === "function")
                ? global.performance.now()
                : Date.now();
            recorder.emit("response", {
                id: requestId,
                method: method,
                endpoint: result && result.url ? result.url : url,
                status: result ? result.status : null,
                ok: result ? !!result.ok : null,
                category: category,
                durationMs: endedAt - startedAt
            });
            return result;
        }).catch(function (error) {
            var endedAt = (global.performance && typeof global.performance.now === "function")
                ? global.performance.now()
                : Date.now();
            recorder.emit("error", {
                id: requestId,
                method: method,
                endpoint: url,
                category: category,
                durationMs: endedAt - startedAt,
                error: normaliseError(error)
            });
            throw error;
        });
    };

    http.request.__wcRecorderWrapped = true;
})(typeof window !== "undefined" ? window : this);

function coordRound(v) {
    var w = Math.floor(v);
    var d = v - w;
    d = Math.round(d * 10000) / 10000;
    return w + d;
}

// utility function to be used by ControlBase subclasses to build URLs for pup runs.
// not to be used elsewhere.
function url_for_run(url) {
    var sitePrefix = "";
    if (typeof window.site_prefix === "string" && window.site_prefix) {
        sitePrefix = window.site_prefix.replace(/\/+$/, "");
    }

    function resolveRunContextFromLocation() {
        var path = window.location && window.location.pathname ? window.location.pathname : "";
        var prefix = sitePrefix;
        if (prefix && prefix !== "/" && prefix.charAt(0) !== "/") {
            prefix = "/" + prefix;
        }
        if (prefix && path.indexOf(prefix) === 0) {
            path = path.slice(prefix.length);
        }

        var parts = path.split("/").filter(function (segment) {
            return segment.length > 0;
        });
        var runsIndex = parts.indexOf("runs");
        if (runsIndex === -1 || parts.length <= runsIndex + 2) {
            return null;
        }
        return {
            runId: decodeURIComponent(parts[runsIndex + 1]),
            config: decodeURIComponent(parts[runsIndex + 2])
        };
    }

    var normalizedUrl = url || "";
    if (normalizedUrl.charAt(0) === "/") {
        normalizedUrl = normalizedUrl.substring(1);
    }

    var resolved = resolveRunContextFromLocation();
    var activeRunId = resolved && resolved.runId ? resolved.runId : (typeof window.runId === "string" ? window.runId : "");
    var activeConfig = resolved && resolved.config ? resolved.config : (typeof window.config === "string" ? window.config : "");

    var runScopedPath = normalizedUrl;
    if (activeRunId && activeConfig) {
        runScopedPath = "runs/" + encodeURIComponent(activeRunId) + "/" + encodeURIComponent(activeConfig) + "/";
        if (normalizedUrl) {
            runScopedPath += normalizedUrl;
        }
    }

    if (runScopedPath.charAt(0) !== "/") {
        runScopedPath = "/" + runScopedPath;
    }

    return sitePrefix + runScopedPath;
}

function pass() {
    return undefined;

} const fromHex = (rgbHex, alpha = 0.5) => {
    // Validate hex input
    if (!rgbHex || typeof rgbHex !== 'string') {
        console.warn(`Invalid hex value: ${rgbHex}. Returning default color.`);
        return { r: 0, g: 0, b: 0, a: 1 };
    }

    // Ensure hex is a valid hex string
    let hex = rgbHex.replace(/^#/, '');
    if (!/^[0-9A-Fa-f]{6}$/.test(hex)) {
        console.warn(`Invalid hex format: ${hex}. Returning default color.`);
        return { r: 0, g: 0, b: 0, a: 1 };
    }

    // Validate alpha
    if (typeof alpha !== 'number' || alpha < 0 || alpha > 1) {
        console.warn(`Invalid alpha value: ${alpha}. Using default alpha: 1.`);
        alpha = 1;
    }

    // Convert hex to RGB and normalize to 0-1 range
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;

    return { r, g, b, a: alpha };
};


function linearToLog(value, minLog, maxLog, maxLinear) {
    if (isNaN(value)) return minLog;
    value = Math.max(0, Math.min(value, maxLinear));

    // Logarithmic mapping: minLog * (maxLog / minLog) ^ (value / maxLinear)
    return minLog * Math.pow(maxLog / minLog, value / maxLinear);
}


function lockButton(buttonId, lockImageId) {
    const button = document.getElementById(buttonId);
    const lockImage = document.getElementById(lockImageId);

    // Disable the button and show the lock image
    button.disabled = true;
    lockImage.style.display = 'inline';
}


function unlockButton(buttonId, lockImageId) {
    const button = document.getElementById(buttonId);
    const lockImage = document.getElementById(lockImageId);

    // Re-enable the button and hide the lock image
    button.disabled = false;
    lockImage.style.display = 'none';
}

// Normalize HTML/text writes across DOM elements, jQuery-style wrappers, and legacy adapters
function applyLabelHtml(label, html) {
    if (!label) {
        return;
    }
    var textFallback = function () {
        try {
            if (label && "textContent" in label) {
                label.textContent = String(html);
            }
        } catch (noop) {
            // ignore
        }
    };

    try {
        var maybeHtml = label && label.html;
        if (typeof maybeHtml === "function") {
            maybeHtml.call(label, html);
            return;
        }
        if ("innerHTML" in label) {
            label.innerHTML = html;
            return;
        }
        if ("textContent" in label) {
            label.textContent = html;
            return;
        }
        textFallback();
    } catch (err) {
        console.warn("applyLabelHtml: failed to write label content, falling back to textContent", err);
        textFallback();
    }
}
if (typeof globalThis !== "undefined") {
    globalThis.applyLabelHtml = applyLabelHtml;
}


const updateRangeMaxLabel_mm = function (r, labelMax) {
    UnitizerClient.ready()
        .then(function (client) {
            var html = client.renderValue(r, 'mm', { includeUnits: true });
            applyLabelHtml(labelMax, html);
        })
        .catch(function (error) {
            console.error("Failed to update unitizer label (mm)", error);
            applyLabelHtml(labelMax, r + ' mm');
        });
};


const updateRangeMaxLabel_kgha = function (r, labelMax) {
    UnitizerClient.ready()
        .then(function (client) {
            var html = client.renderValue(r, 'kg/ha', { includeUnits: true });
            applyLabelHtml(labelMax, html);
        })
        .catch(function (error) {
            console.error("Failed to update unitizer label (kg/ha)", error);
            applyLabelHtml(labelMax, r + ' kg/ha');
        });
};


const updateRangeMaxLabel_tonneha = function (r, labelMax) {
    UnitizerClient.ready()
        .then(function (client) {
            var html = client.renderValue(r, 'tonne/ha', { includeUnits: true });
            applyLabelHtml(labelMax, html);
        })
        .catch(function (error) {
            console.error("Failed to update unitizer label (tonne/ha)", error);
            applyLabelHtml(labelMax, r + ' tonne/ha');
        });
};


function parseBboxText(text) {
    // Keep digits, signs, decimal, scientific notation, commas and spaces
    const toks = text
        .replace(/[^\d\s,.\-+eE]/g, '')
        .split(/[\s,]+/)
        .filter(Boolean)
        .map(Number);

    if (toks.length !== 4 || toks.some(Number.isNaN)) {
        throw new Error("Extent must have exactly 4 numeric values: minLon, minLat, maxLon, maxLat.");
    }

    let [x1, y1, x2, y2] = toks;
    // Normalize (user might give two corners in any order)
    const minLon = Math.min(x1, x2);
    const minLat = Math.min(y1, y2);
    const maxLon = Math.max(x1, x2);
    const maxLat = Math.max(y1, y2);

    // Basic sanity check
    if (minLon >= maxLon || minLat >= maxLat) {
        throw new Error("Invalid extent: ensure minLon < maxLon and minLat < maxLat.");
    }
    return [minLon, minLat, maxLon, maxLat];
}

/* ----------------------------------------------------------------------------
 * Modal Manager
 * ----------------------------------------------------------------------------
 * Lightweight controller for Pure-styled modals triggered via data attributes.
 * Markup requirements:
 *   <div class="wc-modal" id="exampleModal" data-modal hidden>
 *     <div class="wc-modal__overlay" data-modal-dismiss></div>
 *     <div class="wc-modal__dialog" role="dialog" aria-modal="true">
 *       ...
 *       <button type="button" data-modal-dismiss>Close</button>
 *     </div>
 *   </div>
 *   <button type="button" data-modal-open="exampleModal">Open</button>
 */
(function (global) {
    "use strict";

    var ACTIVE_CLASS = "is-visible";
    var BODY_ACTIVE_CLASS = "wc-modal-open";

    var focusableSelectors = [
        "a[href]",
        "button:not([disabled])",
        "input:not([disabled])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "[tabindex]:not([tabindex='-1'])",
    ].join(",");

    var activeModal = null;
    var previouslyFocused = null;

    function toElement(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            return document.getElementById(target);
        }
        return target;
    }

    function getFocusableElements(modal) {
        var dialog = modal.querySelector(".wc-modal__dialog") || modal;
        return Array.prototype.slice.call(dialog.querySelectorAll(focusableSelectors));
    }

    function trapFocus(event) {
        if (!activeModal) {
            return;
        }
        if (event.key !== "Tab") {
            return;
        }

        var focusable = getFocusableElements(activeModal);
        if (focusable.length === 0) {
            event.preventDefault();
            return;
        }

        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        var current = document.activeElement;

        if (event.shiftKey) {
            if (current === first || !activeModal.contains(current)) {
                event.preventDefault();
                last.focus();
            }
        } else if (current === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function onKeyDown(event) {
        if (!activeModal) {
            return;
        }
        if (event.key === "Escape") {
            closeModal(activeModal);
            return;
        }
        trapFocus(event);
    }

    function activateModal(modal) {
        if (activeModal === modal) {
            return;
        }
        if (activeModal) {
            closeModal(activeModal);
        }
        previouslyFocused = document.activeElement;
        activeModal = modal;

        modal.removeAttribute("hidden");
        modal.setAttribute("data-modal-open", "true");
        modal.classList.add(ACTIVE_CLASS);
        document.body.classList.add(BODY_ACTIVE_CLASS);

        var focusable = getFocusableElements(modal);
        if (focusable.length > 0) {
            focusable[0].focus();
        } else {
            modal.focus({ preventScroll: true });
        }

        document.addEventListener("keydown", onKeyDown, true);
    }

    function deactivateModal(modal) {
        modal.classList.remove(ACTIVE_CLASS);
        modal.removeAttribute("data-modal-open");
        modal.setAttribute("hidden", "hidden");
    }

    function closeModal(modal) {
        var element = toElement(modal);
        if (!element) {
            return;
        }
        deactivateModal(element);

        if (activeModal === element) {
            activeModal = null;
            document.body.classList.remove(BODY_ACTIVE_CLASS);
            document.removeEventListener("keydown", onKeyDown, true);

            if (previouslyFocused && typeof previouslyFocused.focus === "function") {
                previouslyFocused.focus({ preventScroll: true });
            }
            previouslyFocused = null;
        }
    }

    function openModal(modal) {
        var element = toElement(modal);
        if (!element) {
            return;
        }
        activateModal(element);
    }

    function toggleModal(modal) {
        var element = toElement(modal);
        if (!element) {
            return;
        }
        if (element.hasAttribute("data-modal-open")) {
            closeModal(element);
        } else {
            openModal(element);
        }
    }

    function handleOpenClick(event) {
        var trigger = event.target.closest("[data-modal-open]");
        if (!trigger) {
            return;
        }
        var targetId = trigger.getAttribute("data-modal-open");
        // Only handle if the value is a modal ID (string), not "true" (open state marker)
        if (!targetId || targetId === "true") {
            return;
        }
        event.preventDefault();
        openModal(targetId);
    }

    function handleDismissClick(event) {
        var dismiss = event.target.closest("[data-modal-dismiss]");
        if (!dismiss) {
            return;
        }
        event.preventDefault();
        var modal = dismiss.closest("[data-modal]");
        if (modal) {
            closeModal(modal);
        }
    }

    function handleOverlayClick(event) {
        if (!activeModal) {
            return;
        }
        if (event.target === activeModal) {
            closeModal(activeModal);
        }
    }

    document.addEventListener("click", handleOpenClick);
    document.addEventListener("click", handleDismissClick);
    document.addEventListener("mousedown", handleOverlayClick);

    global.ModalManager = {
        open: openModal,
        close: closeModal,
        toggle: toggleModal,
        get activeModal() {
            return activeModal;
        },
    };
})(window);

/* ----------------------------------------------------------------------------
 * Unitizer Client
 * ----------------------------------------------------------------------------
 * Bridges the generated unitizer_map.js module with legacy jQuery-driven
 * controls. Provides helpers to convert values, update DOM labels, and keep
 * preference state in sync with the server.
 */
(function (global) {
    "use strict";

    var modulePromise = null;
    var clientInstance = null;

    function resolveStaticPath(filename) {
        var prefix = (typeof global.site_prefix === "string" && global.site_prefix) ? global.site_prefix : "";
        if (prefix && prefix.charAt(prefix.length - 1) === "/") {
            prefix = prefix.slice(0, -1);
        }
        return prefix + "/static/js/" + filename;
    }

    function loadUnitizerMap() {
        if (global.__unitizerMapModule) {
            return Promise.resolve(global.__unitizerMapModule);
        }

        if (!modulePromise) {
            var inlineMap = global.__unitizerMap;
            if (inlineMap && Array.isArray(inlineMap.categories)) {
                global.__unitizerMapModule = { unitizerMap: inlineMap };
                modulePromise = Promise.resolve(global.__unitizerMapModule);
                return modulePromise;
            }

            var modulePath = resolveStaticPath("unitizer_map.js");
            modulePromise = import(modulePath)
                .then(function (module) {
                    global.__unitizerMapModule = module;
                    return module;
                })
                .catch(function (error) {
                    console.error("Failed to load unitizer_map.js", error);
                    if (global.__unitizerMap && Array.isArray(global.__unitizerMap.categories)) {
                        var fallbackModule = { unitizerMap: global.__unitizerMap };
                        global.__unitizerMapModule = fallbackModule;
                        return fallbackModule;
                    }
                    throw error;
                });
        }
        return modulePromise;
    }

    function createClient(mapModule) {
        var map = mapModule && (mapModule.unitizerMap || mapModule.getUnitizerMap && mapModule.getUnitizerMap());
        if (!map || !Array.isArray(map.categories)) {
            throw new Error("unitizer_map.js did not expose unitizerMap");
        }

    var categoriesByKey = new Map();
    var unitToCategory = new Map();
    var tokenToUnit = new Map();
    var numericInputs = new Map();

        map.categories.forEach(function (category) {
            var units = category.units.map(function (unit, index) {
                var entry = {
                    key: unit.key,
                    token: unit.token,
                    label: unit.label,
                    htmlLabel: unit.htmlLabel,
                    precision: Number(unit.precision),
                    index: index,
                };
                unitToCategory.set(entry.key, category.key);
                tokenToUnit.set(entry.token, entry.key);
                return entry;
            });

            var conversionIndex = new Map();
            category.conversions.forEach(function (conversion) {
                var key = conversion.from + "->" + conversion.to;
                conversionIndex.set(key, {
                    from: conversion.from,
                    to: conversion.to,
                    scale: Number(conversion.scale),
                    offset: Number(conversion.offset),
                });
            });

            categoriesByKey.set(category.key, {
                key: category.key,
                label: category.label,
                defaultIndex: Math.max(0, Math.min(Number(category.defaultIndex) || 0, units.length - 1)),
                units: units,
                conversions: conversionIndex,
                unitByKey: units.reduce(function (acc, unit) {
                    acc.set(unit.key, unit);
                    return acc;
                }, new Map()),
                unitByToken: units.reduce(function (acc, unit) {
                    acc.set(unit.token, unit);
                    return acc;
                }, new Map()),
            });
        });

        var preferences = new Map();
        categoriesByKey.forEach(function (category) {
            var fallback = category.units[category.defaultIndex] || category.units[0];
            preferences.set(category.key, fallback.key);
        });

        function getCategory(categoryKey) {
            return categoriesByKey.get(categoryKey) || null;
        }

        function getUnit(unitKey) {
            var categoryKey = unitToCategory.get(unitKey);
            if (!categoryKey) {
                return null;
            }
            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return null;
            }
            return category.unitByKey.get(unitKey) || null;
        }

        function getToken(unitKey) {
            var unit = getUnit(unitKey);
            return unit ? unit.token : null;
        }

        function getPrecision(unitKey) {
            var unit = getUnit(unitKey);
            return unit ? unit.precision : 3;
        }

        function getConversion(fromUnit, toUnit) {
            if (fromUnit === toUnit) {
                return { scale: 1, offset: 0 };
            }
            var categoryKey = unitToCategory.get(fromUnit);
            if (!categoryKey) {
                throw new Error("Unknown source unit: " + fromUnit);
            }
            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                throw new Error("Unknown category for unit: " + fromUnit);
            }
            var key = fromUnit + "->" + toUnit;
            var conversion = category.conversions.get(key);
            if (!conversion) {
                throw new Error("No conversion available from " + fromUnit + " to " + toUnit);
            }
            return conversion;
        }

        function convert(value, fromUnit, toUnit) {
            if (fromUnit === toUnit) {
                return value;
            }
            var conversion = getConversion(fromUnit, toUnit);
            return conversion.scale * value + conversion.offset;
        }

        function toNumber(value) {
            if (typeof value === "number") {
                return value;
            }
            if (typeof value === "string" && value.trim() !== "") {
                var parsed = Number(value);
                if (!Number.isNaN(parsed)) {
                    return parsed;
                }
            }
            return null;
        }

        function formatNumber(value, precision) {
            if (!Number.isFinite(value)) {
                return String(value);
            }
            var p = precision;
            if (!Number.isFinite(p) || p <= 0) {
                p = 4;
            }
            var formatted = Number.parseFloat(Number(value).toPrecision(p));
            if (Number.isInteger(formatted)) {
                return String(formatted);
            }
            return String(formatted);
        }

        function renderUnitBlock(unit, content, visible, options) {
            var classes = ["unitizer", "units-" + unit.token];
            if (!visible) {
                classes.push("invisible");
            }
            if (options && Array.isArray(options.otherClasses)) {
                classes = classes.concat(options.otherClasses);
            }
            return '<div class="' + classes.join(" ") + '">' + content + "</div>";
        }

        function wrapUnitizer(blocks) {
            return '<div class="unitizer-wrapper">' + blocks.join("") + "</div>";
        }

        function renderValue(value, unitKey, options) {
            options = options || {};

            if (value === null || value === undefined || value === "") {
                return "";
            }

            var canonical = String(unitKey);
            if (canonical === "pct" || canonical === "%") {
                var numeric = toNumber(value);
                if (numeric === null) {
                    return "<i>" + value + "</i>";
                }
                if (numeric < 0.1 && numeric !== 0) {
                    return wrapUnitizer([
                        '<div class="unitizer units-pct">' + Number(numeric).toExponential(0) + "</div>",
                    ]);
                }
                return wrapUnitizer([
                    '<div class="unitizer units-pct">' + Number(numeric).toFixed(1) + "</div>",
                ]);
            }

            if (canonical === "hours") {
                var numericHours = toNumber(value);
                if (numericHours === null) {
                    return "<i>" + value + "</i>";
                }
                var hours = Math.trunc(numericHours);
                var minutes = Math.trunc((numericHours - hours) * 60);
                var padded = String(minutes >= 0 ? minutes : 0).padStart(2, "0");
                return wrapUnitizer([
                    '<div class="unitizer units-hours">' + hours + ":" + padded + "</div>",
                ]);
            }

            var categoryKey = unitToCategory.get(canonical);
            if (!categoryKey) {
                return "<i>" + value + "</i>";
            }

            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return "<i>" + value + "</i>";
            }

            var numericValue = toNumber(value);
            var baseUnit = category.unitByKey.get(canonical);
            if (!baseUnit || numericValue === null) {
                return "<i>" + value + "</i>";
            }

            var includeUnits = options.includeUnits === true;
            var parentheses = options.parentheses === true;
            var preferredUnit = preferences.get(categoryKey) || baseUnit.key;

            var blocks = [];
            category.units.forEach(function (unit) {
                var rendered;
                if (unit.key === baseUnit.key) {
                    rendered = formatNumber(numericValue, options.precision !== undefined ? options.precision : unit.precision);
                } else {
                    try {
                        var converted = convert(numericValue, baseUnit.key, unit.key);
                        rendered = formatNumber(converted, unit.precision);
                    } catch (error) {
                        rendered = "<i>" + value + "</i>";
                    }
                }
                if (includeUnits) {
                    rendered = rendered + " " + unit.htmlLabel;
                }
                if (parentheses) {
                    rendered = "(" + rendered + ")";
                }
                var isPreferred = unit.key === preferredUnit;
                blocks.push(renderUnitBlock(unit, rendered, isPreferred, options));
            });

            return wrapUnitizer(blocks);
        }

        function renderUnits(unitKey, options) {
            options = options || {};
            var canonical = String(unitKey);
            if (canonical === "pct" || canonical === "%") {
                return wrapUnitizer([
                    '<div class="unitizer units-pct">' + (options.parentheses ? "(%)" : "%") + "</div>",
                ]);
            }

            var categoryKey = unitToCategory.get(canonical);
            if (!categoryKey) {
                return canonical;
            }

            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return canonical;
            }

            var preferredUnit = preferences.get(categoryKey) || canonical;
            var blocks = category.units.map(function (unit) {
                var content = options.parentheses ? "(" + unit.htmlLabel + ")" : unit.htmlLabel;
                var isPreferred = unit.key === preferredUnit;
                return renderUnitBlock(unit, content, isPreferred, options);
            });
            return wrapUnitizer(blocks);
        }

        function registerNumericInputs(root) {
            var context = root || document;
            var elements = context.querySelectorAll('[data-unitizer-category][data-unitizer-unit]');
            elements.forEach(function (element) {
                if (numericInputs.has(element)) {
                    return;
                }

                var category = element.getAttribute('data-unitizer-category');
                var canonicalUnit = element.getAttribute('data-unitizer-unit');
                if (!category || !canonicalUnit) {
                    return;
                }

                var precisionAttr = element.getAttribute('data-precision');
                var precisionValue = Number(precisionAttr);
                var meta = {
                    element: element,
                    category: category,
                    canonicalUnit: canonicalUnit,
                    precision: Number.isFinite(precisionValue) ? precisionValue : null,
                };

                element.dataset.unitizerActiveUnit = element.dataset.unitizerActiveUnit || canonicalUnit;
                updateCanonicalValue(element, meta);

                var handler = function () {
                    updateCanonicalValue(element, meta);
                };

                element.addEventListener('input', handler);
                element.addEventListener('change', handler);
                meta.handler = handler;

                numericInputs.set(element, meta);
                if (typeof console !== "undefined" && typeof console.log === "function") {
                    console.log("[UnitizerClient] Registered numeric input", {
                        category: meta.category,
                        canonicalUnit: meta.canonicalUnit,
                        elementId: element.id
                    });
                }
            });
        }

        function updateCanonicalValue(element, meta) {
            var raw = toNumber(element.value);
            if (raw === null) {
                element.dataset.unitizerCanonicalValue = "";
                return;
            }

            var activeUnit = element.dataset.unitizerActiveUnit || meta.canonicalUnit;
            var canonical;
            try {
                canonical = activeUnit === meta.canonicalUnit
                    ? raw
                    : convert(raw, activeUnit, meta.canonicalUnit);
            } catch (error) {
                console.warn("Unitizer: failed to convert numeric field", error);
                return;
            }

            element.dataset.unitizerCanonicalValue = String(canonical);
        }

        function getCanonicalValue(meta) {
            var stored = meta.element.dataset.unitizerCanonicalValue;
            if (stored && stored !== "") {
                var parsed = Number(stored);
                if (Number.isFinite(parsed)) {
                    return parsed;
                }
            }

            updateCanonicalValue(meta.element, meta);
            var canonical = meta.element.dataset.unitizerCanonicalValue;

            if (canonical === undefined || canonical === null || canonical === "") {
                return null;
            }

            var retry = Number(canonical);
            return Number.isFinite(retry) ? retry : null;
        }

        function updateNumericFields(root) {
            var context = root || document;
            var scopeIsDocument = !context || context === document;

            numericInputs.forEach(function (meta, element) {
                if (!scopeIsDocument && !context.contains(element)) {
                    return;
                }

                var canonicalValue = getCanonicalValue(meta);
                if (canonicalValue === null) {
                    return;
                }

                var preferredUnit = preferences.get(meta.category) || meta.canonicalUnit;
                var currentUnit = element.dataset.unitizerActiveUnit || meta.canonicalUnit;
                if (preferredUnit === currentUnit) {
                    return;
                }

                var targetUnit = getUnit(preferredUnit);
                var precision = targetUnit ? targetUnit.precision : meta.precision;
                var converted;
                try {
                    converted = convert(canonicalValue, meta.canonicalUnit, preferredUnit);
                } catch (error) {
                    console.warn("Unitizer: failed to convert numeric field", error);
                    return;
                }

                element.value = formatNumber(converted, precision);
                element.dataset.unitizerActiveUnit = preferredUnit;
            });
        }

        function setPreference(categoryKey, unitKey) {
            if (!categoriesByKey.has(categoryKey)) {
                return false;
            }
            var category = categoriesByKey.get(categoryKey);
            if (!category || !category.unitByKey.has(unitKey)) {
                return false;
            }
            preferences.set(categoryKey, unitKey);
            return true;
        }

        function setPreferenceByToken(categoryKey, token) {
            var category = categoriesByKey.get(categoryKey);
            if (!category) {
                return false;
            }
            var unit = category.unitByToken.get(token);
            if (!unit) {
                return false;
            }
            return setPreference(categoryKey, unit.key);
        }

        function setGlobalPreference(index) {
            var idx = Math.max(0, index | 0);
            categoriesByKey.forEach(function (category) {
                var fallback = category.units[idx] || category.units[category.defaultIndex] || category.units[0];
                if (fallback) {
                    preferences.set(category.key, fallback.key);
                }
            });
            if (typeof console !== "undefined" && typeof console.log === "function") {
                console.log("[UnitizerClient] setGlobalPreference", index, getPreferencePayload());
            }
        }

        function getPreferencePayload() {
            var payload = {};
            preferences.forEach(function (unitKey, categoryKey) {
                payload[categoryKey] = unitKey;
            });
            return payload;
        }

        function getPreferenceTokens() {
            var tokens = {};
            preferences.forEach(function (unitKey, categoryKey) {
                var token = getToken(unitKey);
                if (token) {
                    tokens[categoryKey] = token;
                }
            });
            return tokens;
        }

        function syncPreferencesFromDom(root) {
            var context = root || document;
            categoriesByKey.forEach(function (category) {
                var name = "unitizer_" + category.key + "_radio";
                var checked = context.querySelector("input[name='" + name + "']:checked");
                if (checked && checked.value) {
                    setPreferenceByToken(category.key, checked.value);
                }
            });
        }

        function applyPreferenceRadios(root) {
            var context = root || document;
            categoriesByKey.forEach(function (category) {
                var token = getToken(preferences.get(category.key));
                if (!token) {
                    return;
                }
                var selector = "input[name='unitizer_" + category.key + "_radio'][value='" + token + "']";
                var radio = context.querySelector(selector);
                if (radio) {
                    radio.checked = true;
                }
            });
        }

        function applyGlobalRadio(index, root) {
            var context = root || document;
            var selector = "input[name='uni_main_selector'][value='" + index + "']";
            var radios = context.querySelectorAll(selector);
            if (!radios || radios.length === 0) {
                return;
            }
            Array.prototype.forEach.call(radios, function (radio) {
                radio.checked = true;
            });
        }

        function updateUnitLabels(root) {
            var context = root || document;
            var elements = context.querySelectorAll("[data-unitizer-label]");
            elements.forEach(function (element) {
                var categoryKey = element.getAttribute("data-unitizer-category");
                if (!categoryKey) {
                    return;
                }
                var preferredUnitKey = preferences.get(categoryKey);
                if (!preferredUnitKey) {
                    return;
                }
                var unit = getUnit(preferredUnitKey);
                if (!unit) {
                    return;
                }
                element.innerHTML = unit.htmlLabel;
                element.setAttribute("data-unitizer-unit", unit.key);
            });
        }

        function dispatchPreferenceChange() {
            var detail = {
                preferences: getPreferencePayload(),
                tokens: getPreferenceTokens(),
            };
            var event = new CustomEvent("unitizer:preferences-changed", { detail: detail });
            document.dispatchEvent(event);
        }

        return {
            getCategory: getCategory,
            getPreferencePayload: getPreferencePayload,
            getPreferenceTokens: getPreferenceTokens,
            getToken: getToken,
            convert: convert,
            renderValue: renderValue,
            renderUnits: renderUnits,
            setPreference: setPreference,
            setPreferenceByToken: setPreferenceByToken,
            setGlobalPreference: setGlobalPreference,
            syncPreferencesFromDom: syncPreferencesFromDom,
            applyPreferenceRadios: applyPreferenceRadios,
            applyGlobalRadio: applyGlobalRadio,
            updateUnitLabels: updateUnitLabels,
            registerNumericInputs: registerNumericInputs,
            updateNumericFields: updateNumericFields,
            dispatchPreferenceChange: dispatchPreferenceChange,
        };
    }

    function initClient() {
        return loadUnitizerMap().then(function (module) {
            clientInstance = createClient(module);
            return clientInstance;
        });
    }

    global.UnitizerClient = {
        ready: function () {
            if (clientInstance) {
                return Promise.resolve(clientInstance);
            }
            return initClient();
        },
        getClientSync: function () {
            return clientInstance;
        },
        renderValue: function (value, unitKey, options) {
            if (clientInstance) {
                return clientInstance.renderValue(value, unitKey, options);
            }
            return String(value);
        },
        renderUnits: function (unitKey, options) {
            if (clientInstance) {
                return clientInstance.renderUnits(unitKey, options);
            }
            return String(unitKey);
        },
    };
})(window);

/* ----------------------------------------------------------------------------
 * StatusStream
 * ----------------------------------------------------------------------------
 * Shared WebSocket-powered status log helper for console dashboards and run
 * controls. Handles message buffering, auto-scrolling, trigger events, and
 * optional stacktrace enrichment.
 */
(function (global) {
    "use strict";

    var DEFAULT_LOG_LIMIT = 1000;
    var DEFAULT_RECONNECT_BASE_MS = 1500;
    var DEFAULT_RECONNECT_MAX_MS = 15000;
    var streams = new Map();

    function resolveElement(target) {
        if (!target) {
            return null;
        }
        if (global.Element && target instanceof global.Element) {
            return target;
        }
        if (typeof target === "string") {
            return document.querySelector(target);
        }
        return null;
    }

    function createCustomEvent(type, detail) {
        try {
            return new CustomEvent(type, { detail: detail });
        } catch (err) {
            var event = document.createEvent("CustomEvent");
            event.initCustomEvent(type, true, true, detail);
            return event;
        }
    }

    function parseJobIdFromMessage(message) {
        if (!message) {
            return null;
        }
        var text = String(message);
        var parts = text.trim().split(/\s+/);
        if (parts.length === 0) {
            return null;
        }
        var candidate = parts[0];
        if (candidate.startsWith("JID")) {
            return candidate.slice(3);
        }
        // Strip rq: prefix if present (status messages use "rq:<uuid>" format)
        if (candidate.startsWith("rq:")) {
            return candidate.slice(3);
        }
        return candidate;
    }

    function formatMessage(message, formatter) {
        if (formatter && typeof formatter === "function") {
            try {
                return formatter(message);
            } catch (err) {
                console.warn("StatusStream formatter error:", err);
            }
        }
        if (message === null || message === undefined) {
            return "";
        }
        if (typeof message === "string") {
            return message;
        }
        if (typeof message === "object") {
            try {
                return JSON.stringify(message);
            } catch (err) {
                return String(message);
            }
        }
        return String(message);
    }

    function extractStacktrace(payload) {
        if (!payload) {
            return null;
        }
        if (payload.exc_info) {
            return payload.exc_info;
        }
        if (payload.description) {
            return payload.description;
        }
        try {
            return JSON.stringify(payload, null, 2);
        } catch (err) {
            return String(payload);
        }
    }

    function defaultStacktraceFetcher(jobId) {
        if (!jobId) {
            return Promise.resolve(null);
        }

        var http = global.WCHttp;
        if (http && typeof http.getJson === "function") {
            return http.getJson("/weppcloud/rq/api/jobinfo/" + encodeURIComponent(jobId))
                .then(function (payload) {
                    return extractStacktrace(payload);
                })
                .catch(function (error) {
                    if (http.isHttpError && typeof http.isHttpError === "function" && http.isHttpError(error)) {
                        return null;
                    }
                    console.warn("StatusStream stacktrace fetch failed:", error);
                    return null;
                });
        }

        if (typeof fetch !== "function") {
            return Promise.resolve(null);
        }

        var origin = global.location && global.location.origin ? global.location.origin : "";
        var url = origin.replace(/\/$/, "") + "/weppcloud/rq/api/jobinfo/" + encodeURIComponent(jobId);
        return fetch(url, { credentials: "same-origin" })
            .then(function (response) {
                if (!response.ok) {
                    return null;
                }
                return response.json();
            })
            .then(function (payload) {
                return extractStacktrace(payload);
            })
            .catch(function (error) {
                console.warn("StatusStream stacktrace fetch failed:", error);
                return null;
            });
    }

    function StatusStreamInstance(options) {
        var element = resolveElement(options.element || options.root);
        if (!element) {
            throw new Error("StatusStream requires an element or selector.");
        }

        var logElement = options.logElement ? resolveElement(options.logElement) : element.querySelector("[data-status-log]");
        if (!logElement) {
            throw new Error("StatusStream requires a log element with data-status-log.");
        }

        var config = {
            runId: options.runId || global.runid || global.runId || null,
            channel: options.channel || null,
            logLimit: typeof options.logLimit === "number" ? options.logLimit : DEFAULT_LOG_LIMIT,
            formatter: options.formatter,
            onTrigger: typeof options.onTrigger === "function" ? options.onTrigger : null,
            reconnectBaseMs: options.reconnectBaseMs || DEFAULT_RECONNECT_BASE_MS,
            reconnectMaxMs: options.reconnectMaxMs || DEFAULT_RECONNECT_MAX_MS,
            stacktrace: options.stacktrace || null,
            onAppend: typeof options.onAppend === "function" ? options.onAppend : null,
            autoConnect: options.autoConnect === undefined ? true : Boolean(options.autoConnect)
        };

        if (!config.channel) {
            throw new Error("StatusStream requires a channel name.");
        }

        var protocol = (global.location && global.location.protocol === "https:") ? "wss:" : "ws:";
        var host = global.location ? global.location.host : "";
        var runId = config.runId ? String(config.runId) : "";
        var urlRunId = runId || "anonymous";
        var wsUrl = protocol + "//" + host + "/weppcloud-microservices/status/" + encodeURIComponent(urlRunId) + ":" + encodeURIComponent(config.channel);

        var messages = [];
        var reconnectAttempts = 0;
        var ws = null;
        var shouldReconnect = true;
        var api = this;

        if (logElement.textContent) {
            logElement.textContent.split("\n").forEach(function (line) {
                if (line) {
                    messages.push(line);
                }
            });
            if (messages.length > config.logLimit) {
                messages.splice(0, messages.length - config.logLimit);
                logElement.textContent = messages.join("\n") + "\n";
            }
        }

        function dispatch(type, detail) {
            try {
                element.dispatchEvent(createCustomEvent(type, detail));
            } catch (err) {
                console.warn("StatusStream event dispatch error:", err);
            }
        }

        function setLogContent() {
            logElement.textContent = messages.length ? messages.join("\n") + "\n" : "";
        }

        function appendMessage(message, meta) {
            if (!message) {
                return;
            }

            var formatted = formatMessage(message, config.formatter);
            if (!formatted) {
                return;
            }

            var shouldStickToBottom = Math.abs(logElement.scrollHeight - (logElement.scrollTop + logElement.clientHeight)) <= 12;

            messages.push(formatted);
            if (messages.length > config.logLimit) {
                messages.splice(0, messages.length - config.logLimit);
            }

            setLogContent();

            if (shouldStickToBottom) {
                logElement.scrollTop = logElement.scrollHeight;
            }

            dispatch("status:append", { message: formatted, raw: message, meta: meta || null });
            if (config.onAppend) {
                try {
                    config.onAppend({ message: formatted, raw: message, meta: meta || null, stream: api });
                } catch (err) {
                    console.warn("StatusStream onAppend error:", err);
                }
            }
        }

        function resolveStacktraceTargets(stacktraceConfig) {
            if (!stacktraceConfig) {
                return null;
            }
            var panel = resolveElement(stacktraceConfig.element || stacktraceConfig.panel);
            if (!panel) {
                console.warn("StatusStream: stacktrace panel element not found");
                return null;
            }
            var body = stacktraceConfig.body ? resolveElement(stacktraceConfig.body) : panel.querySelector("[data-stacktrace-body]");
            if (!body) {
                console.warn("StatusStream: stacktrace body element not found. Panel:", panel.id || "(no id)", "Expected selector: [data-stacktrace-body]");
                return null;
            }
            return {
                panel: panel,
                body: body,
                fetchJobInfo: typeof stacktraceConfig.fetchJobInfo === "function" ? stacktraceConfig.fetchJobInfo : defaultStacktraceFetcher
            };
        }

        var stacktraceTargets = resolveStacktraceTargets(config.stacktrace);

        function showStacktrace(message) {
            if (!stacktraceTargets) {
                return;
            }

            var panel = stacktraceTargets.panel;
            var body = stacktraceTargets.body;
            if (!panel || !body) {
                return;
            }

            panel.hidden = false;
            if (typeof panel.open !== "undefined") {
                panel.open = true;
            }

            body.textContent = formatMessage(message);

            var jobId = parseJobIdFromMessage(message);
            var fetcher = stacktraceTargets.fetchJobInfo;
            if (!fetcher || !jobId) {
                return;
            }

            fetcher(jobId).then(function (text) {
                if (text) {
                    body.textContent = text;
                }
            }).catch(function (error) {
                console.warn("StatusStream stacktrace enrichment failed:", error);
            });
        }

        function handleTrigger(message) {
            if (typeof message !== "string" || message.indexOf("TRIGGER") === -1) {
                return;
            }
            var tokens = message.trim().split(/\s+/);
            var eventName = tokens.length > 0 ? tokens[tokens.length - 1] : null;
            var controller = tokens.length > 1 ? tokens[tokens.length - 2] : null;
            if (controller && controller !== config.channel) {
                return;
            }
            var detail = { event: eventName, controller: controller, tokens: tokens, raw: message };
            if (config.onTrigger) {
                try {
                    config.onTrigger(detail);
                } catch (err) {
                    console.warn("StatusStream onTrigger error:", err);
                }
            }
            dispatch("status:trigger", detail);
        }

        function handleStatusPayload(payload) {
            if (!payload) {
                return;
            }

            if (payload.type === "ping") {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: "pong" }));
                }
                return;
            }

            if (payload.type === "hangup") {
                disconnect();
                return;
            }

            if (payload.type !== "status") {
                return;
            }

            var data = payload.data;
            appendMessage(data);

            if (typeof data === "string" && data.indexOf("EXCEPTION") !== -1) {
                showStacktrace(data);
            }

            handleTrigger(typeof data === "string" ? data : "");
        }

        function connect() {
            if (ws) {
                return;
            }
            if (typeof WebSocket !== "function") {
                console.warn("StatusStream: WebSocket not supported in this environment.");
                return;
            }

            shouldReconnect = true;
            ws = new WebSocket(wsUrl);

            ws.onopen = function () {
                reconnectAttempts = 0;
                try {
                    ws.send(JSON.stringify({ type: "init" }));
                } catch (err) {
                    console.warn("StatusStream init handshake failed:", err);
                }
                dispatch("status:connected", { url: wsUrl });
            };

            ws.onmessage = function (event) {
                var payload = null;
                try {
                    payload = JSON.parse(event.data);
                } catch (err) {
                    console.warn("StatusStream received non-JSON payload:", err);
                    return;
                }
                handleStatusPayload(payload);
            };

            ws.onerror = function (error) {
                dispatch("status:error", { error: error });
            };

            ws.onclose = function () {
                ws = null;
                dispatch("status:disconnected", { willReconnect: shouldReconnect });

                if (!shouldReconnect) {
                    return;
                }

                reconnectAttempts += 1;
                var delay = Math.min(config.reconnectBaseMs * Math.pow(2, reconnectAttempts - 1), config.reconnectMaxMs);
                setTimeout(connect, delay);
            };
        }

        function disconnect() {
            shouldReconnect = false;
            if (ws) {
                try {
                    ws.close();
                } catch (err) {
                    console.warn("StatusStream close failed:", err);
                }
                ws = null;
            }
        }

        this.element = element;
        this.logElement = logElement;
        this.append = appendMessage;
        this.clear = function () {
            messages = [];
            setLogContent();
        };
        this.connect = connect;
        this.disconnect = disconnect;
        this.setStacktrace = function (stacktraceConfig) {
            stacktraceTargets = resolveStacktraceTargets(stacktraceConfig);
        };
        this.isConnected = function () {
            return ws && ws.readyState === WebSocket.OPEN;
        };

        if (config.autoConnect) {
            connect();
        }
    }

    function attach(options) {
        var instance = new StatusStreamInstance(options || {});
        var element = instance.element;
        if (element && element.id) {
            streams.set(element.id, instance);
        }
        return instance;
    }

    function get(target) {
        if (target instanceof StatusStreamInstance) {
            return target;
        }
        var element = resolveElement(target);
        if (element && element.id && streams.has(element.id)) {
            return streams.get(element.id);
        }
        return null;
    }

    function append(target, message, meta) {
        var instance = get(target);
        if (!instance) {
            console.warn("StatusStream.append: no stream registered for target", target);
            return;
        }
        instance.append(message, meta || null);
    }

    function disconnect(target) {
        var instance = get(target);
        if (instance) {
            instance.disconnect();
        }
    }

    global.StatusStream = {
        attach: attach,
        get: get,
        append: append,
        disconnect: disconnect
    };
})(typeof window !== "undefined" ? window : this);

/* ----------------------------------------------------------------------------
 * Control Base
 * ----------------------------------------------------------------------------
 */
function controlBase() {
    const TERMINAL_JOB_STATUSES = new Set(["finished", "failed", "stopped", "canceled", "not_found"]);
    const SUCCESS_JOB_STATUSES = new Set(["finished"]);
    const FAILURE_JOB_STATUSES = new Set(["failed", "stopped", "canceled", "not_found"]);
    const DEFAULT_POLL_INTERVAL_MS = 800;
    const DEFAULT_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

    function ensureHttp() {
        const http = window.WCHttp;
        if (!http || typeof http.request !== "function") {
            throw new Error("controlBase requires WCHttp helper.");
        }
        return http;
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) {
            return "";
        }
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function formatUtcTimestamp(value) {
        if (value === null || value === undefined) {
            return null;
        }

        const raw = String(value).trim();
        if (!raw) {
            return null;
        }

        const match = raw.match(
            /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?/
        );

        if (!match) {
            return `${raw} UTC`;
        }

        const [, y, m, d, hh, mm, ss, fraction] = match;
        let milliseconds = 0;
        if (fraction) {
            const fractionValue = parseFloat(`0.${fraction}`);
            if (!Number.isNaN(fractionValue)) {
                milliseconds = Math.round(fractionValue * 1000);
            }
        }

        const baseMs = Date.UTC(
            parseInt(y, 10),
            parseInt(m, 10) - 1,
            parseInt(d, 10),
            parseInt(hh, 10),
            parseInt(mm, 10),
            parseInt(ss, 10),
            milliseconds
        );

        const roundedMs = Math.round(baseMs / 1000) * 1000;
        const date = new Date(roundedMs);

        const pad = (num) => String(num).padStart(2, "0");
        const formatted = `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}`;
        return `${formatted} UTC`;
    }

    function normalizeJobId(jobId) {
        if (jobId === undefined || jobId === null) {
            return null;
        }
        const normalized = String(jobId).trim();
        return normalized.length === 0 ? null : normalized;
    }

    function formatStatusLabel(status) {
        if (!status) {
            return "unknown";
        }
        return status.charAt(0).toUpperCase() + status.slice(1);
    }

    function jobDashboardUrl(jobId) {
        return `https://${window.location.host}/weppcloud/rq/job-dashboard/${encodeURIComponent(jobId)}`;
    }

    function splitStacktrace(value) {
        if (value === undefined || value === null) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.map(function (item) { return item === undefined || item === null ? "" : String(item); });
        }
        if (typeof value === "string") {
            return value.split(/\r?\n/);
        }
        return [String(value)];
    }

    function extractJobInfoStacktrace(payload) {
        if (!payload) {
            return null;
        }
        if (payload.exc_info) {
            return payload.exc_info;
        }
        if (payload.children && typeof payload.children === "object") {
            const orders = Object.keys(payload.children);
            for (let i = 0; i < orders.length; i += 1) {
                const entries = payload.children[orders[i]] || [];
                for (let j = 0; j < entries.length; j += 1) {
                    const candidate = extractJobInfoStacktrace(entries[j]);
                    if (candidate) {
                        return candidate;
                    }
                }
            }
        }
        if (payload.description) {
            return payload.description;
        }
        return null;
    }

    function normalizeJobInfoPayload(result) {
        let payload = result && Object.prototype.hasOwnProperty.call(result, "body") ? result.body : result;
        if (typeof payload === "string") {
            try {
                payload = JSON.parse(payload);
            } catch (err) {
                return { exc_info: payload };
            }
        }
        return payload;
    }

    function maybeDispatchCompletion(self, statusObj, source) {
        if (!self || self._job_completion_dispatched) {
            return;
        }
        const status = statusObj && statusObj.status ? String(statusObj.status) : null;
        if (!status || !SUCCESS_JOB_STATUSES.has(status)) {
            return;
        }

        self._job_completion_dispatched = true;

        if (self.poll_completion_event) {
            try {
                self.triggerEvent(self.poll_completion_event, {
                    source: source || "poll",
                    status: statusObj,
                    jobId: self.rq_job_id || null
                });
            } catch (err) {
                console.warn("controlBase poll completion dispatch error:", err);
            }
        }

        try {
            self.triggerEvent("job:completed", {
                jobId: self.rq_job_id || null,
                status: statusObj,
                source: source || "poll"
            });
        } catch (err) {
            console.warn("controlBase job:completed dispatch error:", err);
        }
    }

    function maybeDispatchFailure(self, statusObj, source) {
        if (!self || self._job_failure_dispatched) {
            return;
        }
        const status = statusObj && statusObj.status ? String(statusObj.status).toLowerCase() : null;
        if (!status || !FAILURE_JOB_STATUSES.has(status)) {
            return;
        }

        self._job_failure_dispatched = true;

        const jobId = self.rq_job_id || (statusObj && statusObj.id) || null;
        const errorPayload = { Error: `Job ${status}.` };

        function emitFailure() {
            try {
                self.triggerEvent("job:error", {
                    jobId: jobId,
                    status: status,
                    source: source || "poll"
                });
            } catch (err) {
                console.warn("controlBase job:error dispatch error:", err);
            }
        }

        if (!jobId) {
            self.pushResponseStacktrace(self, errorPayload);
            emitFailure();
            return;
        }

        let http;
        try {
            http = ensureHttp();
        } catch (err) {
            self.pushResponseStacktrace(self, errorPayload);
            emitFailure();
            return;
        }

        const jobInfoUrl = `/weppcloud/rq/api/jobinfo/${encodeURIComponent(jobId)}`;
        const fetchJobInfo = typeof http.getJson === "function"
            ? http.getJson(jobInfoUrl)
            : http.request(jobInfoUrl).then(normalizeJobInfoPayload);

        Promise.resolve(fetchJobInfo)
            .then(function (payload) {
                const stacktrace = extractJobInfoStacktrace(payload);
                if (stacktrace) {
                    errorPayload.StackTrace = splitStacktrace(stacktrace);
                }
                self.pushResponseStacktrace(self, errorPayload);
                emitFailure();
            })
            .catch(function (error) {
                self.pushErrorStacktrace(self, error, status, errorPayload.Error);
                emitFailure();
            });
    }

    function callAdapter(target, method, args) {
        if (!target) {
            return false;
        }
        const fn = target[method];
        if (typeof fn === "function") {
            fn.apply(target, args || []);
            return true;
        }
        return false;
    }

    function unwrapElement(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "object" && target !== null && target.element) {
            const direct = target.element;
            if (typeof window.Node !== "undefined" && direct instanceof window.Node) {
                return direct;
            }
            if (typeof Element !== "undefined" && direct instanceof Element) {
                return direct;
            }
            if (typeof direct === "string") {
                try {
                    return document.querySelector(direct);
                } catch (err) {
                    return null;
                }
            }
        }
        if (typeof window.Node !== "undefined" && target instanceof window.Node) {
            return target;
        }
        if (typeof Element !== "undefined" && target instanceof Element) {
            return target;
        }
        if (target.jquery !== undefined || typeof target.get === "function") {
            try {
                const el = typeof target.get === "function" ? target.get(0) : target[0];
                if (el && typeof window.Node !== "undefined" && el instanceof window.Node) {
                    return el;
                }
            } catch (err) {
                return null;
            }
        }
        if (Array.isArray(target) && target.length > 0) {
            const first = target[0];
            if (typeof window.Node !== "undefined" && first instanceof window.Node) {
                return first;
            }
        }
        return null;
    }

    function showTarget(target) {
        if (callAdapter(target, "show")) {
            return;
        }
        const element = unwrapElement(target);
        if (!element) {
            return;
        }
        element.hidden = false;
        if (element.style && element.style.display === "none") {
            element.style.removeProperty("display");
        }
    }

    function hideTarget(target) {
        if (callAdapter(target, "hide")) {
            return;
        }
        const element = unwrapElement(target);
        if (!element) {
            return;
        }
        element.hidden = true;
        if (element.style) {
            element.style.display = "none";
        }
    }

    function setTextContent(target, value) {
        if (callAdapter(target, "text", [value])) {
            return;
        }
        const element = unwrapElement(target);
        if (!element) {
            return;
        }
        const text = value === undefined || value === null ? "" : String(value);
        element.textContent = text;
    }

    function findStacktracePanel(target) {
        const element = unwrapElement(target);
        if (!element) {
            return null;
        }
        if (typeof element.closest === "function") {
            const closest = element.closest("[data-stacktrace-panel]");
            if (closest) {
                return closest;
            }
        }
        let current = element.parentElement;
        while (current) {
            if (current.hasAttribute && current.hasAttribute("data-stacktrace-panel")) {
                return current;
            }
            current = current.parentElement;
        }
        return null;
    }

    function revealStacktracePanel(target) {
        const panel = findStacktracePanel(target);
        if (!panel) {
            return;
        }
        if (typeof panel.open === "boolean") {
            panel.open = true;
        }
        panel.hidden = false;
        if (panel.style && panel.style.display === "none") {
            panel.style.removeProperty("display");
        }
    }

    function clearStacktrace(target) {
        const element = unwrapElement(target);
        if (!element) {
            return;
        }
        clearContent(element);
        hideTarget(element);
        const panel = findStacktracePanel(element);
        if (panel && panel !== element) {
            if (typeof panel.open === "boolean") {
                panel.open = false;
            }
            hideTarget(panel);
        }
    }

    function clearContent(target) {
        if (callAdapter(target, "empty")) {
            return;
        }
        setHtmlContent(target, "");
    }

    function setHtmlContent(target, value) {
        if (callAdapter(target, "html", [value])) {
            return;
        }
        const element = unwrapElement(target);
        if (!element) {
            return;
        }
        element.innerHTML = value === undefined || value === null ? "" : String(value);
    }

    function appendHtml(target, value) {
        if (callAdapter(target, "append", [value])) {
            return;
        }
        const element = unwrapElement(target);
        if (!element) {
            return;
        }
        if (value instanceof window.Node) {
            element.appendChild(value);
            return;
        }
        const html = value === undefined || value === null ? "" : String(value);
        element.insertAdjacentHTML("beforeend", html);
    }

    function resolveElement(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            try {
                return document.querySelector(target);
            } catch (err) {
                return null;
            }
        }
        return unwrapElement(target);
    }

    function makeTextSetter(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "function") {
            return function (value) {
                target(value === undefined || value === null ? "" : String(value));
            };
        }
        if (typeof target.text === "function") {
            return function (value) {
                target.text(value === undefined || value === null ? "" : String(value));
            };
        }
        if (typeof target.html === "function") {
            return function (value) {
                if (value === undefined || value === null) {
                    target.html("");
                } else {
                    target.html(String(value));
                }
            };
        }
        const element = resolveElement(target);
        if (!element) {
            return null;
        }
        return function (value) {
            element.textContent = value === undefined || value === null ? "" : String(value);
        };
    }

    function extractSummaryText(raw, maxLength) {
        if (raw === undefined || raw === null) {
            return "";
        }
        let text;
        if (typeof raw === "string") {
            text = raw;
        } else if (typeof raw === "object") {
            try {
                text = JSON.stringify(raw);
            } catch (err) {
                text = String(raw);
            }
        } else {
            text = String(raw);
        }
        const firstLine = text.split(/\r?\n/, 1)[0].trim();
        if (!maxLength || maxLength <= 0 || firstLine.length <= maxLength) {
            return firstLine;
        }
        if (maxLength <= 3) {
            return firstLine.slice(0, maxLength);
        }
        return firstLine.slice(0, maxLength - 3) + "...";
    }

    function resolveButtons(self) {
        if (!self || !self.command_btn_id) {
            return [];
        }
        const ids = Array.isArray(self.command_btn_id) ? self.command_btn_id : [self.command_btn_id];
        const resolved = [];
        ids.forEach(function (id) {
            if (!id) {
                return;
            }
            if (typeof id === "string") {
                const element = document.getElementById(id);
                if (element) {
                    resolved.push(element);
                }
                return;
            }
            const element = unwrapElement(id);
            if (element) {
                resolved.push(element);
            }
        });
        return resolved;
    }

    function deriveErrorParts(error, textStatus, errorThrown) {
        let statusCode = "";
        let statusText = "";
        let detail = errorThrown;

        function normalizeDetail(value) {
            if (value === undefined || value === null) {
                return value;
            }
            if (typeof value === "string") {
                return value;
            }
            if (Array.isArray(value)) {
                return value.map(function (item) { return item === undefined || item === null ? "" : String(item); }).join("\n");
            }
            if (typeof value === "object") {
                const maybeError = value.Error || value.error || value.message || value.detail;
                const maybeStack = value.StackTrace || value.stacktrace || value.stack;
                const parts = [];
                if (maybeError) {
                    parts.push(String(maybeError));
                }
                if (maybeStack) {
                    if (Array.isArray(maybeStack)) {
                        parts.push(maybeStack.map(function (item) { return String(item); }).join("\n"));
                    } else {
                        parts.push(String(maybeStack));
                    }
                }
                if (parts.length) {
                    return parts.join("\n");
                }
                try {
                    return JSON.stringify(value);
                } catch (err) {
                    return String(value);
                }
            }
            return String(value);
        }

        if (error) {
            if (typeof error.status === "number" && error.status > 0) {
                statusCode = String(error.status);
            }
            if (typeof error.statusText === "string" && error.statusText) {
                statusText = error.statusText;
            }
            if (error.detail !== undefined) {
                detail = normalizeDetail(error.detail);
            } else if (typeof error.body === "string") {
                detail = error.body;
            } else if (error.body && typeof error.body === "object") {
                detail = normalizeDetail(error.body);
            } else if (error.message && !detail) {
                detail = error.message;
            }
        }

        if (!statusText && textStatus) {
            statusText = textStatus;
        }
        if (detail === undefined && textStatus) {
            detail = textStatus;
        }
        if (detail === undefined && errorThrown) {
            detail = errorThrown;
        }

        return {
            statusCode: statusCode || "ERR",
            statusText: statusText || "Unable to refresh job status",
            detail: detail
        };
    }

    return {
        command_btn_id: null,
        rq_job_id: null,
        rq_job_status: null,
        job_status_poll_interval_ms: DEFAULT_POLL_INTERVAL_MS,
        _job_status_poll_timeout: null,
        _job_status_stacktrace_timeout: null,
        _job_status_fetch_inflight: false,
        _job_status_error: null,
        _job_status_error_parts: null,
        _job_status_stacktrace_from_poll: false,
        _job_failure_dispatched: false,
        statusStream: null,
        _statusStreamHandle: null,

        pushResponseStacktrace: function pushResponseStacktrace(self, response) {
            showTarget(self.stacktrace);
            setTextContent(self.stacktrace, "");

            if (!response) {
                return;
            }

            if (response.Error !== undefined) {
                appendHtml(self.stacktrace, "<h6>" + escapeHtml(response.Error) + "</h6>");
            }

            if (response.StackTrace !== undefined) {
                const lines = Array.isArray(response.StackTrace) ? response.StackTrace : [response.StackTrace];
                const escaped = lines.map(escapeHtml).join("\n");
                appendHtml(self.stacktrace, '<pre><small class="text-muted">' + escaped + "</small></pre>");

                if (lines.some(function (value) { return typeof value === "string" && value.includes("lock() called on an already locked nodb"); })) {
                    appendHtml(
                        self.stacktrace,
                        '<a href="https://doc.wepp.cloud/AdvancedTopics.html#Clearing-Locks">Clearing Locks</a>'
                    );
                }
            }

            if (response.Error === undefined && response.StackTrace === undefined) {
                appendHtml(
                    self.stacktrace,
                    '<pre><small class="text-muted">' + escapeHtml(String(response)) + "</small></pre>"
                );
            }

            revealStacktracePanel(self.stacktrace);
        },

        pushErrorStacktrace: function pushErrorStacktrace(self, error, textStatus, errorThrown) {
            const parts = deriveErrorParts(error, textStatus, errorThrown);
            showTarget(self.stacktrace);
            setTextContent(self.stacktrace, "");
            appendHtml(self.stacktrace, "<h6>" + escapeHtml(parts.statusCode) + "</h6>");
            appendHtml(self.stacktrace, '<pre><small class="text-muted">' + escapeHtml(parts.statusText) + "</small></pre>");
            if (parts.detail !== undefined && parts.detail !== null) {
                appendHtml(
                    self.stacktrace,
                    '<pre><small class="text-muted">' + escapeHtml(String(parts.detail)) + "</small></pre>"
                );
            }

            revealStacktracePanel(self.stacktrace);
        },

        has_stacktrace_content: function has_stacktrace_content(self) {
            const target = self && self.stacktrace ? self.stacktrace : null;
            if (!target) {
                return false;
            }

            const element = unwrapElement(target);
            if (element) {
                const text = (element.textContent || "").trim();
                const html = (element.innerHTML || "").trim();
                if (text || html) {
                    return true;
                }
            }

            if (typeof target.text === "function") {
                const textValue = target.text();
                if (textValue !== undefined && textValue !== null && String(textValue).trim()) {
                    return true;
                }
            }

            if (typeof target.html === "function") {
                const htmlValue = target.html();
                if (htmlValue !== undefined && htmlValue !== null && String(htmlValue).trim()) {
                    return true;
                }
            }

            return false;
        },

        clear_stacktrace_backfill: function clear_stacktrace_backfill(self) {
            if (self._job_status_stacktrace_timeout) {
                clearTimeout(self._job_status_stacktrace_timeout);
                self._job_status_stacktrace_timeout = null;
            }
        },

        schedule_stacktrace_backfill: function schedule_stacktrace_backfill(self, errorParts) {
            if (!self || !self.stacktrace) {
                return;
            }

            self.clear_stacktrace_backfill(self);

            const hasDetail = errorParts && (errorParts.detail !== undefined && errorParts.detail !== null);
            const hasStatus = errorParts && (errorParts.statusCode || errorParts.statusText);
            if (!hasDetail && !hasStatus) {
                return;
            }

            self._job_status_stacktrace_timeout = setTimeout(function () {
                self._job_status_stacktrace_timeout = null;

                if (self.has_stacktrace_content(self)) {
                    return;
                }

                self._job_status_stacktrace_from_poll = true;
                self._job_status_error_parts = errorParts || null;
                self.pushErrorStacktrace(
                    self,
                    errorParts,
                    errorParts ? errorParts.statusText : undefined,
                    errorParts ? errorParts.detail : undefined
                );
            }, 5000);
        },

        should_disable_command_button: function should_disable_command_button(self) {
            if (!self.rq_job_id) {
                return false;
            }

            if (!self.rq_job_status || !self.rq_job_status.status) {
                return true;
            }

            return !TERMINAL_JOB_STATUSES.has(self.rq_job_status.status);
        },

        update_command_button_state: function update_command_button_state(self) {
            const buttons = resolveButtons(self);
            if (buttons.length === 0) {
                return;
            }

            const disable = self.should_disable_command_button(self);

            buttons.forEach(function (button) {
                if (!button) {
                    return;
                }

                const wasDisabledByJob = button.dataset.jobDisabled === "true";

                if (disable) {
                    if (!wasDisabledByJob) {
                        button.dataset.jobDisabledPrev = button.disabled ? "true" : "false";
                    }
                    button.disabled = true;
                    button.dataset.jobDisabled = "true";
                } else if (wasDisabledByJob) {
                    const previous = button.dataset.jobDisabledPrev === "true";
                    button.disabled = previous;
                    button.dataset.jobDisabled = "false";
                }
            });
        },

        set_rq_job_id: function (self, job_id) {
            self.clear_stacktrace_backfill(self);
            const normalizedJobId = normalizeJobId(job_id);

            self._job_completion_dispatched = false;
            self._job_failure_dispatched = false;
            self._job_status_stacktrace_from_poll = false;
            self._job_status_error_parts = null;

            if (normalizedJobId === self.rq_job_id) {
                if (!normalizedJobId) {
                    self.render_job_status(self);
                    self.render_job_hint(self);
                    self.update_command_button_state(self);
                    self.manage_status_stream(self, null);
                    self.reset_status_spinner(self);
                } else if (!self._job_status_fetch_inflight) {
                    self.fetch_job_status(self);
                }
                return;
            }

            self.rq_job_id = normalizedJobId;
            self.rq_job_status = null;
            self._job_status_error = null;

            self.reset_status_spinner(self);
            self.stop_job_status_polling(self);
            self.render_job_status(self);
            self.render_job_hint(self);
            self.update_command_button_state(self);

            if (!self.rq_job_id) {
                self.manage_status_stream(self, null);
                return;
            }

            self.fetch_job_status(self);
        },

        fetch_job_status: function fetch_job_status(self) {
            if (!self.rq_job_id || self._job_status_fetch_inflight) {
                return;
            }

            self._job_status_fetch_inflight = true;
            const http = ensureHttp();
            const url = `/weppcloud/rq/api/jobstatus/${encodeURIComponent(self.rq_job_id)}`;

            http.getJson(url, { params: { _: Date.now() } })
                .then(function (data) {
                    self.handle_job_status_response(self, data);
                })
                .catch(function (error) {
                    self.handle_job_status_error(self, error);
                })
                .finally(function () {
                    self._job_status_fetch_inflight = false;
                });
        },

        handle_job_status_response: function handle_job_status_response(self, data) {
            self.clear_stacktrace_backfill(self);
            if (self._job_status_stacktrace_from_poll) {
                clearStacktrace(self.stacktrace);
                self._job_status_stacktrace_from_poll = false;
                self._job_status_error_parts = null;
            }
            self._job_status_error = null;
            self.rq_job_status = data || {};
            self.render_job_status(self);
            self.manage_status_stream(self, self.rq_job_status && self.rq_job_status.status);

            if (self.should_continue_polling(self, self.rq_job_status && self.rq_job_status.status)) {
                self.schedule_job_status_poll(self);
            } else {
                self.stop_job_status_polling(self);
            }

            maybeDispatchCompletion(self, self.rq_job_status, "poll");
            maybeDispatchFailure(self, self.rq_job_status, "poll");

            self.update_command_button_state(self);
        },

        handle_job_status_error: function handle_job_status_error(self, error) {
            const parts = deriveErrorParts(error);
            self._job_status_error = `${parts.statusCode} ${parts.statusText}`.trim();
            self._job_status_error_parts = parts;
            self.render_job_status(self);
            self.schedule_stacktrace_backfill(self, parts);

            if (self.should_continue_polling(self)) {
                self.schedule_job_status_poll(self);
            } else {
                self.stop_job_status_polling(self);
            }
        },

        render_job_status: function render_job_status(self) {
            if (!self.rq_job) {
                return;
            }

            if (!self.rq_job_id) {
                clearContent(self.rq_job);
                return;
            }

            const statusObj = self.rq_job_status || {};
            const statusLabel = formatStatusLabel(statusObj.status || (self._job_status_error ? "unknown" : "checking"));
            const parts = [];

            parts.push(`<div class="small text-muted">Status: ${escapeHtml(statusLabel)}</div>`);

            const timeline = [];

            const startedAt = formatUtcTimestamp(statusObj.started_at);
            if (startedAt) {
                timeline.push(`<span class="mr-3">Started: ${escapeHtml(startedAt)}</span>`);
            }

            const endedAt = formatUtcTimestamp(statusObj.ended_at);
            if (endedAt) {
                timeline.push(`<span class="mr-3">Ended: ${escapeHtml(endedAt)}</span>`);
            }

            if (timeline.length) {
                parts.push(
                    `<div class="small text-muted d-flex flex-wrap align-items-baseline">${timeline.join(" ")}</div>`
                );
            }

            if (self._job_status_error) {
                parts.push(`<div class="text-danger small">${escapeHtml(self._job_status_error)}</div>`);
            }

            setHtmlContent(self.rq_job, parts.join(""));
        },

        render_job_hint: function render_job_hint(self) {
            if (!self.hint) {
                return;
            }

            if (!self.rq_job_id) {
                self.hint.html("");
                hideTarget(self.hint);
                return;
            }

            showTarget(self.hint);

            const linkHtml = `job_id: <a href="${jobDashboardUrl(self.rq_job_id)}" target="_blank">${escapeHtml(self.rq_job_id)}</a>`;
            self.hint.html(linkHtml);
        },

        schedule_job_status_poll: function schedule_job_status_poll(self) {
            if (!self.rq_job_id) {
                self.stop_job_status_polling(self);
                return;
            }

            const interval = self.job_status_poll_interval_ms || DEFAULT_POLL_INTERVAL_MS;

            self.stop_job_status_polling(self);

            self._job_status_poll_timeout = setTimeout(function () {
                self._job_status_poll_timeout = null;
                self.fetch_job_status(self);
            }, interval);
        },

        stop_job_status_polling: function stop_job_status_polling(self) {
            if (self._job_status_poll_timeout) {
                clearTimeout(self._job_status_poll_timeout);
                self._job_status_poll_timeout = null;
            }
        },

        should_continue_polling: function should_continue_polling(self, status) {
            if (!self.rq_job_id) {
                return false;
            }

            const effectiveStatus = status || (self.rq_job_status && self.rq_job_status.status);
            if (!effectiveStatus) {
                return true;
            }

            return !TERMINAL_JOB_STATUSES.has(effectiveStatus);
        },

        attach_status_stream: function attach_status_stream(self, options) {
            if (typeof window === "undefined" || typeof window.StatusStream === "undefined") {
                console.warn("StatusStream helper unavailable; skipping attachment.");
                return null;
            }

            const config = Object.assign({}, options || {});
            let panelElement = resolveElement(
                config.element || config.panel || config.root || self.statusPanelEl || null
            );
            let createdPanel = false;
            let createdLog = false;
            let injectedElements = null;

            function ensurePanelPlaceholder(formEl) {
                if (typeof document === "undefined" || !formEl || typeof formEl.appendChild !== "function") {
                    return null;
                }
                const container = document.createElement("div");
                const generatedId = (formEl.id || self.formId || "status") + "__status_stream";
                container.id = generatedId;
                container.setAttribute("data-status-panel", "");
                container.style.display = "none";

                const logNode = document.createElement("div");
                logNode.setAttribute("data-status-log", "");
                container.appendChild(logNode);

                formEl.appendChild(container);
                injectedElements = { panel: container, log: logNode };
                return container;
            }

            if (!panelElement) {
                const fallbackForm = resolveElement(config.form || self.form || null);
                const generatedPanel = ensurePanelPlaceholder(fallbackForm);
                if (generatedPanel) {
                    panelElement = generatedPanel;
                    createdPanel = true;
                    config.logElement = config.logElement || injectedElements.log;
                }
            }

            if (!panelElement) {
                // This is normal - controller can be instantiated without its panel on the page
                // For example, batch_runner on a standard run page, or path_ce on pages without that mod
                return null;
            }

            if (!config.logElement) {
                const existingLog = panelElement.querySelector("[data-status-log]");
                if (existingLog) {
                    config.logElement = existingLog;
                } else if (typeof document !== "undefined") {
                    const logNode = document.createElement("div");
                    logNode.setAttribute("data-status-log", "");
                    panelElement.appendChild(logNode);
                    config.logElement = logNode;
                    createdLog = true;
                } else {
                    console.warn("controlBase.attach_status_stream: log element not found.");
                }
            }

            const spinnerSetter = makeTextSetter(
                config.spinner || config.spinnerTarget || config.spinnerAdapter || self.statusSpinnerEl || null
            );
            const hintSetter = makeTextSetter(config.hint || config.hintTarget || self.hint || null);
            const summarySetter = makeTextSetter(
                config.summary ||
                config.summaryTarget ||
                config.statusSummary ||
                self.status ||
                config.statusAdapter ||
                config.statusElement ||
                null
            );
            const summaryMaxLength = typeof config.summaryMaxLength === "number" ? config.summaryMaxLength : 160;
            const spinnerFrames = Array.isArray(config.spinnerFrames) && config.spinnerFrames.length > 0
                ? config.spinnerFrames.slice()
                : DEFAULT_SPINNER_FRAMES.slice();
            let spinnerIndex = 0;

            function resetSpinner() {
                spinnerIndex = 0;
                if (spinnerSetter) {
                    spinnerSetter("");
                }
            }

            function advanceSpinner() {
                if (!spinnerSetter || spinnerFrames.length === 0) {
                    return;
                }
                const frame = spinnerFrames[spinnerIndex];
                spinnerSetter(frame);
                spinnerIndex = (spinnerIndex + 1) % spinnerFrames.length;
            }

            const onStatusCallback = typeof config.onStatus === "function" ? config.onStatus : null;
            const onAppendCallback = typeof config.onAppend === "function" ? config.onAppend : null;
            const onTriggerCallback = typeof config.onTrigger === "function" ? config.onTrigger : null;

            let resolvedStacktrace = null;
            if (config.stacktrace) {
                resolvedStacktrace = Object.assign({}, config.stacktrace);
                if (resolvedStacktrace.element) {
                    resolvedStacktrace.element = resolveElement(resolvedStacktrace.element);
                }
                if (resolvedStacktrace.body) {
                    resolvedStacktrace.body = resolveElement(resolvedStacktrace.body);
                }
            } else if (config.stacktracePanel || self.stacktracePanelEl) {
                const panel = resolveElement(config.stacktracePanel || self.stacktracePanelEl);
                if (panel) {
                    resolvedStacktrace = { element: panel };
                    if (config.stacktraceBody) {
                        resolvedStacktrace.body = resolveElement(config.stacktraceBody);
                    }
                }
            }

            const streamOptions = {
                element: panelElement,
                channel: config.channel || config.topic || null,
                runId: config.runId || self.runId || window.runid || window.runId || null,
                logLimit: typeof config.logLimit === "number" ? config.logLimit : undefined,
                formatter: config.formatter,
                reconnectBaseMs: config.reconnectBaseMs,
                reconnectMaxMs: config.reconnectMaxMs,
                stacktrace: resolvedStacktrace,
                autoConnect: config.autoConnect === undefined ? false : Boolean(config.autoConnect),
                onAppend: function (detail) {
                    advanceSpinner();

                    const rawMessage = detail && detail.raw !== undefined ? detail.raw : detail ? detail.message : "";
                    const summary = extractSummaryText(rawMessage, summaryMaxLength);

                    if (summarySetter) {
                        summarySetter(summary);
                    }
                    // Don't duplicate summary in hint - hints will show job link on completion
                    // (removed hintSetter call to eliminate duplication)
                    
                    if (onStatusCallback) {
                        try {
                            onStatusCallback({ summary: summary, detail: detail });
                        } catch (err) {
                            console.warn("StatusStream onStatus callback error:", err);
                        }
                    }
                    if (onAppendCallback) {
                        try {
                            onAppendCallback(detail);
                        } catch (err) {
                            console.warn("StatusStream onAppend callback error:", err);
                        }
                    }
                },
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        try {
                            self.triggerEvent(detail.event, detail);
                        } catch (err) {
                            console.warn("controlBase triggerEvent error:", err);
                        }
                        const normalized = String(detail.event).toUpperCase();
                        if (
                            normalized.includes("COMPLETE") ||
                            normalized.includes("FINISH") ||
                            normalized.includes("SUCCESS") ||
                            normalized.includes("END_BROADCAST")
                        ) {
                            resetSpinner();
                        }
                    }
                    if (onTriggerCallback) {
                        try {
                            onTriggerCallback(detail);
                        } catch (err) {
                            console.warn("StatusStream onTrigger callback error:", err);
                        }
                    }
                }
            };

            if (!streamOptions.channel) {
                throw new Error("controlBase.attach_status_stream requires a channel name.");
            }

            if (config.logElement || config.logSelector) {
                const logTarget = resolveElement(config.logElement || config.logSelector);
                if (logTarget) {
                    streamOptions.logElement = logTarget;
                }
            }

            const instance = window.StatusStream.attach(streamOptions);

            resetSpinner();

            const handle = {
                instance: instance,
                element: panelElement,
                createdPanel: createdPanel,
                createdLog: createdLog,
                injectedElements: injectedElements,
                connect: function () {
                    if (instance && typeof instance.connect === "function") {
                        instance.connect();
                    }
                },
                disconnect: function () {
                    if (instance && typeof instance.disconnect === "function") {
                        instance.disconnect();
                    }
                },
                resetSpinner: resetSpinner,
                destroy: function () {
                    resetSpinner();
                    if (typeof window.StatusStream !== "undefined") {
                        window.StatusStream.disconnect(instance);
                    }
                    if (this.createdPanel && this.injectedElements && this.injectedElements.panel) {
                        const parent = this.injectedElements.panel.parentNode;
                        if (parent && typeof parent.removeChild === "function") {
                            parent.removeChild(this.injectedElements.panel);
                        }
                    }
                }
            };

            self.statusStream = instance;
            self._statusStreamHandle = handle;

            return instance;
        },

        detach_status_stream: function detach_status_stream(self) {
            if (!self._statusStreamHandle) {
                return;
            }
            try {
                self._statusStreamHandle.destroy();
            } catch (err) {
                console.warn("StatusStream destroy error:", err);
            }
            self._statusStreamHandle = null;
            if (typeof window !== "undefined" && typeof window.StatusStream !== "undefined" && self.statusStream) {
                window.StatusStream.disconnect(self.statusStream);
            }
            self.statusStream = null;
        },

        connect_status_stream: function connect_status_stream(self) {
            if (self._statusStreamHandle && typeof self._statusStreamHandle.connect === "function") {
                self._statusStreamHandle.connect();
            } else if (self.statusStream && typeof self.statusStream.connect === "function") {
                self.statusStream.connect();
            }
        },

        disconnect_status_stream: function disconnect_status_stream(self) {
            if (self._statusStreamHandle && typeof self._statusStreamHandle.disconnect === "function") {
                self._statusStreamHandle.disconnect();
            } else if (self.statusStream && typeof self.statusStream.disconnect === "function") {
                self.statusStream.disconnect();
            }
        },

        reset_status_spinner: function reset_status_spinner(self) {
            if (self._statusStreamHandle && typeof self._statusStreamHandle.resetSpinner === "function") {
                self._statusStreamHandle.resetSpinner();
            } else if (self.statusStream && typeof self.statusStream.resetSpinner === "function") {
                self.statusStream.resetSpinner();
            }
        },

        manage_status_stream: function manage_status_stream(self, status) {
            if (!self._statusStreamHandle && !self.statusStream) {
                return;
            }
            if (self.should_continue_polling(self, status)) {
                self.connect_status_stream(self);
            } else {
                self.disconnect_status_stream(self);
                self.reset_status_spinner(self);
            }
        },

        append_status_message: function append_status_message(self, message, meta) {
            if (!message) {
                return;
            }
            if (self.statusStream && typeof self.statusStream.append === "function") {
                self.statusStream.append(message, meta || null);
                return;
            }
            var adapter = self.status;
            if (adapter && typeof adapter.html === "function") {
                adapter.html(message);
                return;
            }
            if (adapter && typeof adapter.text === "function") {
                adapter.text(message);
                return;
            }
            var element = resolveElement(self.statusElement || null);
            if (!element && self.form) {
                try {
                    element = resolveElement(self.form.querySelector("#status"));
                } catch (err) {
                    element = null;
                }
            }
            if (element) {
                element.innerHTML = message;
            }
        },

        clear_status_messages: function clear_status_messages(self) {
            if (self.statusStream && typeof self.statusStream.clear === "function") {
                self.statusStream.clear();
            }
            var adapter = self.status;
            if (adapter && typeof adapter.html === "function") {
                adapter.html("");
                return;
            }
            if (adapter && typeof adapter.text === "function") {
                adapter.text("");
                return;
            }
            var element = resolveElement(self.statusElement || null);
            if (!element && self.form) {
                try {
                    element = resolveElement(self.form.querySelector("#status"));
                } catch (err) {
                    element = null;
                }
            }
            if (element) {
                element.innerHTML = "";
            }
        },

        reset_panel_state: function reset_panel_state(self, options) {
            var opts = options || {};
            var message = opts.message || opts.taskMessage || null;
            var preserveJobHint = Boolean(self && self.rq_job_id && opts.clearJobHint !== true);

            var summaryTargets = [];
            var stackTargets = [];
            var hintTargets = [];
            var resultsTargets = [];

            function pushUnique(targets, target) {
                if (!target) {
                    return;
                }
                if (targets.indexOf(target) !== -1) {
                    return;
                }
                targets.push(target);
            }

            function collectTargets(targets, candidate) {
                if (!candidate) {
                    return;
                }
                if (Array.isArray(candidate)) {
                    candidate.forEach(function (item) {
                        pushUnique(targets, item);
                    });
                    return;
                }
                pushUnique(targets, candidate);
            }

            collectTargets(summaryTargets, opts.summaryTarget);
            collectTargets(summaryTargets, opts.summaryTargets);
            collectTargets(summaryTargets, self.summary);
            collectTargets(summaryTargets, self.summaryElement);
            collectTargets(summaryTargets, self.info);
            collectTargets(summaryTargets, self.infoElement);
            if (self.form && opts.skipFormLookup !== true) {
                try {
                    var summaryEl = self.form.querySelector("#info");
                    collectTargets(summaryTargets, summaryEl);
                } catch (err) {
                    /* ignore */
                }
            }

            collectTargets(stackTargets, opts.stacktraceTarget);
            collectTargets(stackTargets, opts.stacktraceTargets);
            collectTargets(stackTargets, self.stacktrace);
            collectTargets(stackTargets, self.stacktraceElement);
            collectTargets(stackTargets, self.stacktracePanelEl);

            collectTargets(hintTargets, opts.hintTarget);
            collectTargets(hintTargets, opts.hintTargets);
            collectTargets(hintTargets, self.hint);

            collectTargets(resultsTargets, opts.resultsTarget);
            collectTargets(resultsTargets, opts.resultsTargets);
            collectTargets(resultsTargets, self.results);
            collectTargets(resultsTargets, self.resultsContainer);

            try {
                stackTargets.forEach(function (target) {
                    var resolved = resolveElement(target);
                    if (resolved && resolved.hasAttribute && resolved.hasAttribute("data-stacktrace-panel")) {
                        var body = resolved.querySelector("[data-stacktrace-body]");
                        if (body) {
                            clearContent(body);
                            return;
                        }
                    }
                    clearContent(target);
                });
            } catch (err) {
                /* ignore */
            }

            try {
                summaryTargets.forEach(function (target) {
                    clearContent(target);
                });
            } catch (err) {
                /* ignore */
            }

            if (opts.clearStatus !== false && typeof self.clear_status_messages === "function") {
                self.clear_status_messages(self);
            }

            try {
                resultsTargets.forEach(function (target) {
                    clearContent(target);
                });
            } catch (err) {
                /* ignore */
            }

            try {
                hintTargets.forEach(function (target) {
                    if (preserveJobHint) {
                        return;
                    }
                    setTextContent(target, "");
                });
            } catch (err) {
                /* ignore */
            }

            if (message) {
                self.append_status_message(self, opts.skipEllipsis ? message : message + "...");
            }
        },

        triggerEvent: function triggerEvent(eventName, payload) {
            if (!eventName) {
                return;
            }

            const form = this.form;
            if (!form) {
                return;
            }

            if (typeof form.trigger === "function") {
                if (payload === undefined) {
                    form.trigger(eventName);
                } else {
                    form.trigger(eventName, payload);
                }
                return;
            }

            const element = unwrapElement(form);
            if (!element || typeof window.CustomEvent !== "function") {
                return;
            }

            const event = new CustomEvent(eventName, {
                detail: payload,
                bubbles: true,
                cancelable: true
            });
            element.dispatchEvent(event);
        },

        bootstrap: function bootstrap() {
            return this;
        }
    };
}

if (typeof globalThis !== "undefined") {
    globalThis.controlBase = controlBase;
}

/* ----------------------------------------------------------------------------
 * Controller Bootstrap Helper
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var storedContext = null;

    function isObject(value) {
        return value !== null && typeof value === "object";
    }

    function setContext(context) {
        storedContext = context && typeof context === "object" ? context : {};
        return storedContext;
    }

    function getContext() {
        return storedContext;
    }

    function ensureController(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            var resolved = global[target];
            if (!resolved) {
                throw new Error("Controller not found: " + target);
            }
            target = resolved;
        }
        if (typeof target.getInstance === "function") {
            return target.getInstance();
        }
        return target;
    }

    function bootstrap(target, key, context) {
        var ctx = context && typeof context === "object" ? context : storedContext || {};
        if (context && context !== storedContext) {
            storedContext = ctx;
        }
        var instance = ensureController(target);
        if (!instance) {
            return null;
        }
        if (typeof instance.bootstrap === "function") {
            instance.bootstrap(ctx, { name: key || null });
        }
        return instance;
    }

    function bootstrapMany(entries, context) {
        if (!Array.isArray(entries)) {
            return [];
        }
        return entries.map(function (entry) {
            if (!entry) {
                return null;
            }
            if (Array.isArray(entry)) {
                return bootstrap(entry[0], entry[1], context);
            }
            if (typeof entry === "object" && entry.controller) {
                return bootstrap(entry.controller, entry.name || entry.key, context);
            }
            return bootstrap(entry, null, context);
        });
    }

    function getControllerContext(context, key) {
        var ctx = context || storedContext || {};
        if (!key) {
            return {};
        }
        var controllers = ctx.controllers;
        if (isObject(controllers) && Object.prototype.hasOwnProperty.call(controllers, key)) {
            var value = controllers[key];
            return isObject(value) ? value : {};
        }
        return {};
    }

    function resolveJobId(context, jobKey) {
        if (!jobKey) {
            return null;
        }
        var ctx = context || storedContext || {};
        var jobIds = ctx.jobIds || ctx.jobs;
        if (!isObject(jobIds)) {
            return null;
        }
        if (!Object.prototype.hasOwnProperty.call(jobIds, jobKey)) {
            return null;
        }
        var value = jobIds[jobKey];
        if (value === undefined || value === null) {
            return null;
        }
        return String(value);
    }

    var api = {
        setContext: setContext,
        getContext: getContext,
        bootstrap: bootstrap,
        bootstrapMany: bootstrapMany,
        getControllerContext: getControllerContext,
        resolveJobId: resolveJobId
    };

    global.WCControllerBootstrap = api;
}(typeof globalThis !== "undefined" ? globalThis : window));

/* ----------------------------------------------------------------------------
 * Project
 * ----------------------------------------------------------------------------
 */
var Project = (function () {
    "use strict";

    var instance;

    var NAME_SELECTOR = '[data-project-field="name"]';
    var SCENARIO_SELECTOR = '[data-project-field="scenario"]';
    var READONLY_SELECTOR = '[data-project-toggle="readonly"]';
    var PUBLIC_SELECTOR = '[data-project-toggle="public"]';
    var ACTION_SELECTOR = '[data-project-action]';
    var MOD_SELECTOR = '[data-project-mod]';
    var GLOBAL_UNIT_SELECTOR = '[data-project-unitizer="global"]';
    var CATEGORY_UNIT_SELECTOR = '[data-project-unitizer="category"]';
    var RUN_HEADER_MENU_SELECTOR = ".wc-run-header__menu";
    var RUN_HEADER_MENU_OPEN_SELECTOR = RUN_HEADER_MENU_SELECTOR + "[open]";

    var DEFAULT_DEBOUNCE_MS = 800;
    var runHeaderMenuDismissBound = false;

    var EVENT_NAMES = [
        "project:name:updated",
        "project:name:update:failed",
        "project:scenario:updated",
        "project:scenario:update:failed",
        "project:readonly:changed",
        "project:readonly:update:failed",
        "project:public:changed",
        "project:public:update:failed",
        "project:unitizer:sync:started",
        "project:unitizer:preferences",
        "project:unitizer:sync:completed",
        "project:unitizer:sync:failed"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (
            !dom ||
            typeof dom.qsa !== "function" ||
            typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" ||
            typeof dom.hide !== "function"
        ) {
            throw new Error("Project controller requires WCDom helpers.");
        }
        if (
            !http ||
            typeof http.postJson !== "function" ||
            typeof http.request !== "function" ||
            typeof http.getJson !== "function"
        ) {
            throw new Error("Project controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Project controller requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
    }

    function setupRunHeaderMenuDismiss(dom) {
        if (runHeaderMenuDismissBound || typeof document === "undefined" || !document.addEventListener) {
            return;
        }
        runHeaderMenuDismissBound = true;

        document.addEventListener("click", function handleRunHeaderMenuDismiss(event) {
            var openMenus = dom.qsa(RUN_HEADER_MENU_OPEN_SELECTOR) || [];
            if (!openMenus.length) {
                return;
            }
            openMenus.forEach(function (menu) {
                if (menu && !menu.contains(event.target)) {
                    menu.removeAttribute("open");
                }
            });
        });
    }

    function firstFieldValue(dom, selector, fallback) {
        var elements = dom.qsa(selector);
        if (!elements || elements.length === 0) {
            return fallback || "";
        }
        var value = elements[0].value;
        if (value === undefined || value === null) {
            return fallback || "";
        }
        return String(value);
    }

    function syncFieldValue(dom, selector, value) {
        var elements = dom.qsa(selector);
        if (!elements) {
            return;
        }
        elements.forEach(function (input) {
            if (document.activeElement === input && input.value === value) {
                return;
            }
            input.value = value;
        });
    }

    function readToggleState(dom, selector, fallback) {
        var elements = dom.qsa(selector);
        if (!elements || elements.length === 0) {
            return Boolean(fallback);
        }
        return Boolean(elements[0].checked);
    }

    function syncToggleState(dom, selector, state) {
        var elements = dom.qsa(selector);
        if (!elements) {
            return;
        }
        elements.forEach(function (input) {
            input.checked = Boolean(state);
        });
    }

    function updateTitleWithName(nameValue) {
        try {
            var parts = (document.title || "").split(" - ");
            var baseTitle = parts[0] || document.title || "";
            document.title = baseTitle + " - " + (nameValue || "Untitled");
        } catch (err) {
            console.warn("Failed to update document title with project name", err);
        }
    }

    function updateTitleWithScenario(scenarioValue) {
        try {
            var parts = (document.title || "").split(" - ");
            var baseTitle = parts[0] || document.title || "";
            document.title = baseTitle + " - " + (scenarioValue || "");
        } catch (err) {
            console.warn("Failed to update document title with scenario", err);
        }
    }

    function notifyError(message, error) {
        if (error) {
            if (window.WCHttp && typeof window.WCHttp.isHttpError === "function" && window.WCHttp.isHttpError(error)) {
                console.error(message, error.detail || error.body, error);
            } else {
                console.error(message, error);
            }
        } else {
            console.error(message);
        }
    }

    function unpackResponse(result) {
        if (!result) {
            return null;
        }
        if (result.body !== undefined) {
            return result.body;
        }
        return result;
    }

    function isSuccess(response) {
        return response && response.Success === true;
    }

    function getContent(response) {
        if (!response || typeof response !== "object") {
            return {};
        }
        return response.Content || response.content || {};
    }

    function emitEvent(emitter, name, payload) {
        if (!emitter || typeof emitter.emit !== "function") {
            return;
        }
        emitter.emit(name, payload);
    }

    function applyReadonlyState(dom, readonly) {
        var hideElements = dom.qsa(".hide-readonly");
        hideElements.forEach(function (element) {
            if (readonly) {
                dom.hide(element);
            } else {
                dom.show(element);
            }
        });

        var targets = dom.qsa(".disable-readonly");
        targets.forEach(function (element) {
            var tagName = element.tagName ? element.tagName.toLowerCase() : "";
            if (tagName === "input") {
                var type = (element.getAttribute("type") || "").toLowerCase();
                if (type === "radio" || type === "checkbox" || type === "button" || type === "submit" || type === "reset") {
                    element.disabled = readonly;
                } else {
                    element.readOnly = readonly;
                    if (readonly) {
                        element.setAttribute("readonly", "readonly");
                    } else {
                        element.removeAttribute("readonly");
                    }
                }
            } else if (tagName === "select" || tagName === "button") {
                element.disabled = readonly;
            } else if (tagName === "textarea") {
                element.readOnly = readonly;
                if (readonly) {
                    element.setAttribute("readonly", "readonly");
                } else {
                    element.removeAttribute("readonly");
                }
            } else if (readonly) {
                element.setAttribute("aria-disabled", "true");
            } else {
                element.removeAttribute("aria-disabled");
            }
        });

        if (!readonly) {
            try {
                if (window.Outlet && typeof window.Outlet.getInstance === "function") {
                    var outlet = window.Outlet.getInstance();
                    if (outlet && typeof outlet.setMode === "function") {
                        outlet.setMode(0);
                    }
                }
            } catch (err) {
                console.warn("Failed to reset Outlet mode", err);
            }
        }
    }

    function getRunContext() {
        var runid = typeof window.runid === "string" && window.runid ? window.runid : null;
        var config = typeof window.config === "string" && window.config ? window.config : null;
        if (!runid || !config) {
            return null;
        }
        return { runid: runid, config: config };
    }

    function updateGlobalUnitizerRadios(dom, targetValue) {
        var radios = dom.qsa(GLOBAL_UNIT_SELECTOR);
        if (!radios || radios.length === 0) {
            return;
        }
        var normalized = String(targetValue);
        radios.forEach(function (radio) {
            radio.checked = false;
            radio.removeAttribute("checked");
        });
        radios.forEach(function (radio) {
            if (String(radio.value) === normalized) {
                radio.checked = true;
                radio.setAttribute("checked", "checked");
            }
        });
    }

    function applyUnitizerPreferences(client, root) {
        var scope = root || document;
        if (!scope || !client || typeof client.getPreferenceTokens !== "function") {
            return;
        }

        var tokens = client.getPreferenceTokens();
        Object.keys(tokens).forEach(function (categoryKey) {
            var groupName = "unitizer_" + categoryKey + "_radio";
            var radios = scope.querySelectorAll("input[name='" + groupName + "']");
            Array.prototype.forEach.call(radios, function (radio) {
                var value = radio.value;
                var elements = scope.querySelectorAll(".units-" + value);
                Array.prototype.forEach.call(elements, function (el) {
                    el.classList.add("invisible");
                });
            });

            var preferredToken = tokens[categoryKey];
            if (!preferredToken) {
                return;
            }
            var preferredElements = scope.querySelectorAll(".units-" + preferredToken);
            Array.prototype.forEach.call(preferredElements, function (el) {
                el.classList.remove("invisible");
            });
        });

        if (typeof client.updateUnitLabels === "function") {
            client.updateUnitLabels(scope);
        }
        if (typeof client.registerNumericInputs === "function") {
            client.registerNumericInputs(scope);
        }
        if (typeof client.updateNumericFields === "function") {
            client.updateNumericFields(scope);
        }
        if (typeof client.dispatchPreferenceChange === "function") {
            client.dispatchPreferenceChange();
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;
        setupRunHeaderMenuDismiss(dom);

        var project = controlBase();
        var emitter = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                emitter = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                emitter = emitterBase;
            }
            project.events = emitter;
        }

        var runContext = typeof window !== "undefined" ? window.runContext || {} : {};
        var state = {
            name: firstFieldValue(dom, NAME_SELECTOR, ""),
            scenario: firstFieldValue(dom, SCENARIO_SELECTOR, ""),
            readonly: readToggleState(dom, READONLY_SELECTOR, false),
            public: readToggleState(dom, PUBLIC_SELECTOR, false),
            mods: Array.isArray(runContext.mods && runContext.mods.list)
                ? runContext.mods.list.slice()
                : []
        };

        var MOD_BOOTSTRAP_MAP = {
            rap_ts: function (ctx) {
                bootstrapControllerSymbol(window.RAP_TS, ctx);
            },
            treatments: function (ctx) {
                bootstrapControllerSymbol(window.Treatments, ctx);
            },
            ash: function (ctx) {
                bootstrapControllerSymbol(window.Ash, ctx);
            },
            omni: function (ctx) {
                bootstrapControllerSymbol(window.Omni, ctx, { forceRemount: true });
            },
            dss_export: function (ctx) {
                bootstrapControllerSymbol(window.DssExport, ctx);
            },
            debris_flow: function (ctx) {
                bootstrapControllerSymbol(window.DebrisFlow, ctx);
            },
            path_ce: function (ctx) {
                bootstrapControllerSymbol(window.PathCE, ctx);
            },
            observed: function (ctx) {
                bootstrapControllerSymbol(window.Observed, ctx);
            }
        };

        project.state = state;
        project._currentName = state.name;
        project._currentScenario = state.scenario;
        project._nameDebounceTimer = null;
        project._scenarioDebounceTimer = null;
        project._notifyTimer = null;
        project._unitPreferenceInflight = null;
        project._pendingUnitPreference = null;

        function getModNavElements(modName) {
            var nodes = document.querySelectorAll('[data-mod-nav="' + modName + '"]');
            if (!nodes || nodes.length === 0) {
                return [];
            }
            return Array.prototype.slice.call(nodes);
        }

        function getModSectionContainer(modName) {
            return document.querySelector('[data-mod-section="' + modName + '"]');
        }

        function bootstrapControllerSymbol(symbol, context, options) {
            if (!symbol) {
                return;
            }
            var controller = null;
            var forceRemount = options && options.forceRemount;
            if (forceRemount && typeof symbol.remount === "function") {
                controller = symbol.remount();
            } else if (typeof symbol.getInstance === "function") {
                controller = symbol.getInstance();
            } else if (typeof symbol.remount === "function") {
                controller = symbol.remount();
            }
            if (controller && typeof controller.bootstrap === "function") {
                controller.bootstrap(context || window.runContext || {});
            }
        }

        function toggleModNav(modName, enabled) {
            var navItems = getModNavElements(modName);
            if (!navItems.length) {
                return;
            }
            navItems.forEach(function (nav) {
                if (!nav) {
                    return;
                }
                if (enabled) {
                    nav.removeAttribute("hidden");
                    nav.hidden = false;
                    if (nav.style && nav.style.display === "none") {
                        nav.style.removeProperty("display");
                    }
                } else {
                    nav.setAttribute("hidden", "hidden");
                    nav.hidden = true;
                    if (nav.style) {
                        nav.style.display = "none";
                    }
                }
            });
            var tocElement = document.getElementById("toc");
            if (tocElement && typeof window.registerTocEmojiMetadata === "function" && window.tocTaskEmojis) {
                try {
                    window.registerTocEmojiMetadata(tocElement, window.tocTaskEmojis);
                } catch (err) {
                    console.warn("[Project] Failed to refresh TOC metadata", err);
                }
            }
        }

        function toggleModSection(modName, enabled, html) {
            var container = getModSectionContainer(modName);
            if (!container) {
                return;
            }
            if (enabled) {
                if (html !== undefined && html !== null) {
                    container.innerHTML = html;
                }
                container.removeAttribute("hidden");
                container.hidden = false;
                if (container.style) {
                    container.style.removeProperty("display");
                }
            } else {
                container.innerHTML = "";
                container.setAttribute("hidden", "hidden");
                container.hidden = true;
                if (container.style) {
                    container.style.display = "none";
                }
            }
        }

        function updateRunContextMods(modName, enabled) {
            if (typeof window.runContext !== "object" || !window.runContext) {
                return;
            }
            var ctx = window.runContext.mods || {};
            var list = Array.isArray(ctx.list) ? ctx.list.slice() : [];
            var index = list.indexOf(modName);
            if (enabled && index === -1) {
                list.push(modName);
            } else if (!enabled && index !== -1) {
                list.splice(index, 1);
            }
            ctx.list = list;
            ctx.flags = ctx.flags || {};
            ctx.flags[modName] = enabled;
            window.runContext.mods = ctx;
        }

        function bootstrapModController(modName) {
            var context = window.runContext || {};
            var handler = MOD_BOOTSTRAP_MAP[modName];
            if (typeof handler === "function") {
                handler(context);
            }
        }

        project.notifyCommandBar = function (message, options) {
            options = options || {};
            var duration = options.duration;
            if (duration === undefined) {
                duration = 2500;
            }
            if (typeof window.initializeCommandBar !== "function") {
                return;
            }
            var commandBar = window.initializeCommandBar();
            if (!commandBar || typeof commandBar.showResult !== "function") {
                return;
            }
            commandBar.showResult(message);
            if (project._notifyTimer) {
                clearTimeout(project._notifyTimer);
            }
            if (duration !== null && typeof commandBar.hideResult === "function") {
                project._notifyTimer = setTimeout(function () {
                    commandBar.hideResult();
                }, duration);
            }
        };
        project._notifyCommandBar = project.notifyCommandBar;

        project.setName = function (name, options) {
            options = options || {};
            var trimmed = (name || "").trim();
            if (trimmed === state.name) {
                return Promise.resolve({ Success: true, skipped: true });
            }

            var previous = state.name;
            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = null;

            return http.postJson(url_for_run("tasks/setname/"), { name: trimmed }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    var content = getContent(response);
                    var savedName = typeof content.name === "string" ? content.name : trimmed;
                    state.name = savedName;
                    project._currentName = savedName;
                    syncFieldValue(dom, NAME_SELECTOR, savedName);
                    updateTitleWithName(savedName);
                    if (options.notify !== false) {
                        var displayName = savedName || "Untitled";
                        project.notifyCommandBar('Saved project name to "' + displayName + '"');
                    }
                    emitEvent(emitter, "project:name:updated", {
                        name: state.name,
                        previous: previous,
                        response: response
                    });
                } else {
                    state.name = previous;
                    project._currentName = previous;
                    syncFieldValue(dom, NAME_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error saving project name", { duration: null });
                    }
                    emitEvent(emitter, "project:name:update:failed", {
                        attempted: trimmed,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                state.name = previous;
                project._currentName = previous;
                syncFieldValue(dom, NAME_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error saving project name", { duration: null });
                }
                notifyError("Error saving project name", error);
                emitEvent(emitter, "project:name:update:failed", {
                    attempted: trimmed,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };

        project.setNameFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, NAME_SELECTOR, ""));
            var wait = typeof opts.debounceMs === "number" ? opts.debounceMs : DEFAULT_DEBOUNCE_MS;

            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = setTimeout(function () {
                project.setName(value, opts);
            }, wait);
        };

        project.commitNameFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, NAME_SELECTOR, ""));
            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = null;
            project.setName(value, opts);
        };

        project.setScenario = function (scenario, options) {
            options = options || {};
            var trimmed = (scenario || "").trim();
            if (trimmed === state.scenario) {
                return Promise.resolve({ Success: true, skipped: true });
            }

            var previous = state.scenario;
            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = null;

            return http.postJson(url_for_run("tasks/setscenario/"), { scenario: trimmed }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    var content = getContent(response);
                    var savedScenario = typeof content.scenario === "string" ? content.scenario : trimmed;
                    state.scenario = savedScenario;
                    project._currentScenario = savedScenario;
                    syncFieldValue(dom, SCENARIO_SELECTOR, savedScenario);
                    updateTitleWithScenario(savedScenario);
                    if (options.notify !== false) {
                        var message = savedScenario ? ('Saved scenario to "' + savedScenario + '"') : "Cleared scenario";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:scenario:updated", {
                        scenario: state.scenario,
                        previous: previous,
                        response: response
                    });
                } else {
                    state.scenario = previous;
                    project._currentScenario = previous;
                    syncFieldValue(dom, SCENARIO_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error saving scenario", { duration: null });
                    }
                    emitEvent(emitter, "project:scenario:update:failed", {
                        attempted: trimmed,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                state.scenario = previous;
                project._currentScenario = previous;
                syncFieldValue(dom, SCENARIO_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error saving scenario", { duration: null });
                }
                notifyError("Error saving project scenario", error);
                emitEvent(emitter, "project:scenario:update:failed", {
                    attempted: trimmed,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };

        project.setScenarioFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, SCENARIO_SELECTOR, ""));
            var wait = typeof opts.debounceMs === "number" ? opts.debounceMs : DEFAULT_DEBOUNCE_MS;

            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = setTimeout(function () {
                project.setScenario(value, opts);
            }, wait);
        };

        project.commitScenarioFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, SCENARIO_SELECTOR, ""));
            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = null;
            project.setScenario(value, opts);
        };

        project.set_readonly_controls = function (readonly) {
            applyReadonlyState(dom, Boolean(readonly));
        };

        project.set_readonly = function (stateValue, options) {
            options = options || {};
            var desiredState = Boolean(stateValue);
            var previous = readToggleState(dom, READONLY_SELECTOR, state.readonly);

            return http.postJson(url_for_run("tasks/set_readonly"), { readonly: desiredState }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    syncToggleState(dom, READONLY_SELECTOR, desiredState);
                    state.readonly = desiredState;
                    project.set_readonly_controls(desiredState);
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "READONLY set to True. Project controls disabled."
                            : "READONLY set to False. Project controls enabled.";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:readonly:changed", {
                        readonly: desiredState,
                        previous: previous,
                        response: response
                    });
                } else {
                    syncToggleState(dom, READONLY_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error updating READONLY state.", { duration: null });
                    }
                    emitEvent(emitter, "project:readonly:update:failed", {
                        attempted: desiredState,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                syncToggleState(dom, READONLY_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating READONLY state.", { duration: null });
                }
                notifyError("Error updating READONLY state", error);
                emitEvent(emitter, "project:readonly:update:failed", {
                    attempted: desiredState,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };
        project.setReadonly = project.set_readonly;

        project.set_public = function (stateValue, options) {
            options = options || {};
            var desiredState = Boolean(stateValue);
            var previous = readToggleState(dom, PUBLIC_SELECTOR, state.public);

            return http.postJson(url_for_run("tasks/set_public"), { public: desiredState }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    syncToggleState(dom, PUBLIC_SELECTOR, desiredState);
                    state.public = desiredState;
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "PUBLIC set to True. Project is now publicly accessible."
                            : "PUBLIC set to False. Project access limited to collaborators.";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:public:changed", {
                        isPublic: desiredState,
                        previous: previous,
                        response: response
                    });
                } else {
                    syncToggleState(dom, PUBLIC_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error updating PUBLIC state.", { duration: null });
                    }
                    emitEvent(emitter, "project:public:update:failed", {
                        attempted: desiredState,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                syncToggleState(dom, PUBLIC_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating PUBLIC state.", { duration: null });
                }
                notifyError("Error updating PUBLIC state", error);
                emitEvent(emitter, "project:public:update:failed", {
                    attempted: desiredState,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };
        project.setPublic = project.set_public;

        project.load_mod_section = function (modName) {
            var endpoint = "view/mod/" + encodeURIComponent(modName);
            return http.getJson(url_for_run(endpoint)).then(function (response) {
                if (response && response.Success === true) {
                    return response.Content || response.content || response;
                }
                return Promise.reject(response || { Error: "Failed to load module section" });
            });
        };

        project.set_mod = function (modName, enabled, options) {
            options = options || {};
            var normalized = typeof modName === "string" ? modName.trim() : "";
            if (!normalized) {
                return Promise.resolve(null);
            }
            var desiredState = Boolean(enabled);
            var input = options.input || null;
            if (input) {
                input.disabled = true;
            }

            return http.request(url_for_run("tasks/set_mod"), {
                method: "POST",
                json: { mod: normalized, enabled: desiredState }
            }).then(function (result) {
                var response = unpackResponse(result);
                if (!isSuccess(response)) {
                    var message = response && (response.Error || response.Message || response.message);
                    if (input) {
                        input.disabled = false;
                        input.checked = !desiredState;
                    }
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        if (message) {
                            project.notifyCommandBar(message, { duration: null });
                        } else {
                            project.notifyCommandBar("Unable to update module.", { duration: null });
                        }
                    }
                    return response;
                }

                var label = response.Content && response.Content.label ? response.Content.label : normalized;

                var applyUI = function (html) {
                    toggleModNav(normalized, desiredState);
                    toggleModSection(normalized, desiredState, html);
                    updateRunContextMods(normalized, desiredState);
                    if (options.notify !== false) {
                        var verb = desiredState ? "enabled" : "disabled";
                        project.notifyCommandBar(label + " " + verb + ".");
                    }
                };

                if (desiredState) {
                    return project.load_mod_section(normalized).then(function (payload) {
                        var html = payload && payload.html ? payload.html : "";
                        applyUI(html);
                        // Allow DOM to settle before bootstrapping controller
                        return new Promise(function (resolve) {
                            setTimeout(function () {
                                bootstrapModController(normalized);
                                if (input) {
                                    input.checked = true;
                                    input.disabled = false;
                                }
                                resolve(response);
                            }, 0);
                        });
                    }).catch(function (error) {
                        if (input) {
                            input.disabled = false;
                            input.checked = false;
                        }
                        notifyError("Error rendering module section", error);
                        project.notifyCommandBar("Module enabled but failed to render. Refresh to continue.", { duration: null });
                        return response;
                    });
                }

                applyUI();
                if (input) {
                    input.checked = false;
                    input.disabled = false;
                }
                return response;
            }).catch(function (error) {
                if (input) {
                    input.disabled = false;
                    input.checked = !desiredState;
                }
                notifyError("Error updating module state", error);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating module.", { duration: null });
                }
                return null;
            });
        };

        project.clear_locks = function () {
            return http.request(url_for_run("tasks/clear_locks"), {
                method: "GET",
                params: { _: Date.now() }
            }).then(function (result) {
                var response = unpackResponse(result);
                if (response && response.Success === true) {
                    window.alert("Locks have been cleared");
                } else {
                    window.alert("Error clearing locks");
                }
                return response;
            }).catch(function (error) {
                notifyError("Error clearing locks", error);
                window.alert("Error clearing locks");
                return null;
            });
        };

        project.promote_recorder_profile = function () {
            if (typeof runid === "undefined" || !runid) {
                window.alert("Run ID is not available for promotion.");
                return Promise.resolve(null);
            }

            var defaultSlug = runid;
            var slug = window.prompt("Enter profile slug", defaultSlug);
            if (slug === null) {
                return Promise.resolve(null);
            }

            slug = (slug || "").trim();
            var payload = {};
            if (slug) {
                payload.slug = slug;
            }

            return http.postJson(url_for_run("recorder/promote"), payload).then(function (result) {
                var response = result && result.body ? result.body : result;
                if (response && response.success) {
                    var profileRoot = response.profile && response.profile.profile_root;
                    var message = "Profile draft promoted.";
                    if (profileRoot) {
                        message += "\nSaved to: " + profileRoot;
                    }
                    window.alert(message);
                } else {
                    var errorMessage = response && (response.message || response.error) || "Error promoting profile draft.";
                    window.alert(errorMessage);
                }
                return response;
            }).catch(function (error) {
                notifyError("Error promoting profile draft", error);
                window.alert("Error promoting profile draft.");
                return null;
            });
        };

        project.handleGlobalUnitPreference = function (pref) {
            var numericPref = Number(pref);
            if (Number.isNaN(numericPref)) {
                return Promise.resolve();
            }

            updateGlobalUnitizerRadios(dom, numericPref);

            if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
                console.warn("[Project] UnitizerClient is not available.");
                return Promise.resolve();
            }

            if (project._unitPreferenceInflight) {
                project._pendingUnitPreference = numericPref;
                return project._unitPreferenceInflight;
            }

            project._pendingUnitPreference = null;
            project._unitPreferenceInflight = window.UnitizerClient.ready()
                .then(function (client) {
                    if (typeof client.setGlobalPreference === "function") {
                        client.setGlobalPreference(numericPref);
                    }
                    if (typeof client.applyPreferenceRadios === "function") {
                        client.applyPreferenceRadios(document);
                    }
                    if (typeof client.applyGlobalRadio === "function") {
                        client.applyGlobalRadio(numericPref, document);
                    }
                    applyUnitizerPreferences(client, document);
                    return project.unitChangeEvent({
                        syncFromDom: false,
                        client: client,
                        source: "global"
                    });
                })
                .catch(function (error) {
                    console.error("Error applying global unit preference", error);
                })
                .finally(function () {
                    var nextPref = project._pendingUnitPreference;
                    project._unitPreferenceInflight = null;
                    if (nextPref !== null && nextPref !== undefined) {
                        project._pendingUnitPreference = null;
                        project.handleGlobalUnitPreference(nextPref);
                    }
                });

            return project._unitPreferenceInflight;
        };

        project.handleUnitPreferenceChange = function () {
            if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
                console.warn("[Project] UnitizerClient is not available.");
                return Promise.resolve();
            }
            return project.unitChangeEvent({ source: "category" });
        };

        project.unitChangeEvent = function (options) {
            options = options || {};
            emitEvent(emitter, "project:unitizer:sync:started", { source: options.source || "unknown" });

            var clientPromise = options.client ? Promise.resolve(options.client) : (
                window.UnitizerClient && typeof window.UnitizerClient.ready === "function"
                    ? window.UnitizerClient.ready()
                    : Promise.reject(new Error("UnitizerClient not available"))
            );

            var syncPromise = clientPromise.then(function (client) {
                var root = options.root || document;
                if (options.syncFromDom !== false && typeof client.syncPreferencesFromDom === "function") {
                    client.syncPreferencesFromDom(root);
                }

                applyUnitizerPreferences(client, root);

                var preferences = typeof client.getPreferencePayload === "function"
                    ? client.getPreferencePayload()
                    : {};

                var context = getRunContext();
                if (!context) {
                    console.warn("[Project] Cannot persist unit preferences without run context.");
                    emitEvent(emitter, "project:unitizer:sync:failed", {
                        error: new Error("Missing run context"),
                        preferences: preferences,
                        source: options.source || "unknown"
                    });
                    return null;
                }

                return http.postJson(
                    "runs/" + context.runid + "/" + context.config + "/tasks/set_unit_preferences/",
                    preferences
                ).then(function (result) {
                    var response = unpackResponse(result);
                    if (!isSuccess(response)) {
                        if (response) {
                            project.pushResponseStacktrace(project, response);
                        }
                        emitEvent(emitter, "project:unitizer:sync:failed", {
                            response: response,
                            preferences: preferences,
                            source: options.source || "unknown"
                        });
                        return response;
                    }

                    emitEvent(emitter, "project:unitizer:preferences", {
                        preferences: preferences,
                        response: response,
                        source: options.source || "unknown"
                    });
                    return response;
                }).catch(function (error) {
                    notifyError("Failed to persist unit preferences", error);
                    emitEvent(emitter, "project:unitizer:sync:failed", {
                        error: error,
                        preferences: preferences,
                        source: options.source || "unknown"
                    });
                    return null;
                });
            }).catch(function (error) {
                notifyError("Failed to load unitizer client", error);
                emitEvent(emitter, "project:unitizer:sync:failed", {
                    error: error,
                    source: options.source || "unknown"
                });
                return null;
            });

            return syncPromise.finally(function () {
                emitEvent(emitter, "project:unitizer:sync:completed", { source: options.source || "unknown" });
            });
        };

        project.set_preferred_units = function (root) {
            if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
                console.warn("[Project] UnitizerClient is not available.");
                return Promise.resolve(null);
            }
            return window.UnitizerClient.ready()
                .then(function (client) {
                    var scope = root || document;
                    if (typeof client.syncPreferencesFromDom === "function") {
                        client.syncPreferencesFromDom(scope);
                    }
                    applyUnitizerPreferences(client, scope);
                    return client;
                })
                .catch(function (error) {
                    console.error("Failed to apply unit preferences", error);
                    return null;
                });
        };

        dom.delegate(document, "input", NAME_SELECTOR, function (event, target) {
            project.setNameFromInput({ source: target });
        });

        dom.delegate(document, "focusout", NAME_SELECTOR, function (event, target) {
            project.commitNameFromInput({ source: target });
        });

        dom.delegate(document, "input", SCENARIO_SELECTOR, function (event, target) {
            project.setScenarioFromInput({ source: target });
        });

        dom.delegate(document, "focusout", SCENARIO_SELECTOR, function (event, target) {
            project.commitScenarioFromInput({ source: target });
        });

        dom.delegate(document, "change", READONLY_SELECTOR, function (event, target) {
            project.set_readonly(target.checked);
        });

        dom.delegate(document, "change", PUBLIC_SELECTOR, function (event, target) {
            project.set_public(target.checked);
        });

        dom.delegate(document, "change", MOD_SELECTOR, function (event, target) {
            var modName = target.getAttribute("data-project-mod");
            if (!modName) {
                return;
            }
            project.set_mod(modName, target.checked, { input: target });
        });

        dom.delegate(document, "click", ACTION_SELECTOR, function (event, target) {
            var action = target.getAttribute("data-project-action");
            if (!action) {
                return;
            }
            event.preventDefault();
            if (action === "clear-locks") {
                project.clear_locks();
            } else if (action === "recorder-promote") {
                project.promote_recorder_profile();
            }
        });

        dom.delegate(document, "change", GLOBAL_UNIT_SELECTOR, function (event, target) {
            project.handleGlobalUnitPreference(target.value);
        });

        dom.delegate(document, "change", CATEGORY_UNIT_SELECTOR, function () {
            project.handleUnitPreferenceChange();
        });

        project.set_readonly_controls(state.readonly);

        project.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var controllerContext = ctx.controllers && ctx.controllers.project ? ctx.controllers.project : {};
            var readonly = controllerContext.readonly;
            if (readonly === undefined && ctx.user) {
                readonly = ctx.user.readonly;
            }
            if (readonly !== undefined && typeof project.set_readonly_controls === "function") {
                project.set_readonly_controls(Boolean(readonly));
            }
            return project;
        };

        return project;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.Project = Project;
    globalThis.setGlobalUnitizerPreference = function (pref) {
        var controller = Project.getInstance();
        if (controller && typeof controller.handleGlobalUnitPreference === "function") {
            return controller.handleGlobalUnitPreference(pref);
        }
        return undefined;
    };
}

/* ----------------------------------------------------------------------------
 * Ash
 * Doc: controllers_js/README.md — Ash Controller Modernization (2024 helper-first baseline)
 * ----------------------------------------------------------------------------
 */
var Ash = (function () {
    var instance;

    var DEPTH_MODE_IDS = {
        0: "ash_depth_mode0_controls",
        1: "ash_depth_mode1_controls",
        2: "ash_depth_mode2_controls"
    };

    var EVENT_NAMES = [
        "ash:mode:changed",
        "ash:model:changed",
        "ash:transport:mode",
        "ash:run:started",
        "ash:run:completed",
        "ash:model:values:capture"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Ash controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Ash controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Ash controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Ash controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function parseDepthMode(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function readModelParams(dom) {
        var scriptNode = dom.qs("#ash-model-params-data");
        if (scriptNode && scriptNode.textContent) {
            try {
                return JSON.parse(scriptNode.textContent);
            } catch (err) {
                console.warn("Unable to parse ash model params payload", err);
            }
        }
        if (typeof window.modelParams !== "undefined") {
            return window.modelParams;
        }
        return {};
    }

    function applyReadonlyMarkers(formElement) {
        if (!formElement) {
            return;
        }
        var nodes = formElement.querySelectorAll("[data-disable-readonly]");
        nodes.forEach(function (node) {
            node.classList.add("disable-readonly");
            node.removeAttribute("data-disable-readonly");
        });
    }

    function ensureModelCache(cache, model) {
        if (!cache[model]) {
            cache[model] = {
                white: {},
                black: {}
            };
        }
        return cache[model];
    }

    function mergeModelValues(base, overrides) {
        var result = {};
        Object.keys(base || {}).forEach(function (key) {
            result[key] = base[key];
        });
        Object.keys(overrides || {}).forEach(function (key) {
            if (overrides[key] !== undefined) {
                result[key] = overrides[key];
            }
        });
        return result;
    }

    function storeModelValue(cache, input) {
        if (!input || !input.id) {
            return;
        }
        var separator = input.id.indexOf("_");
        if (separator <= 0) {
            return;
        }
        var color = input.id.slice(0, separator);
        if (color !== "white" && color !== "black") {
            return;
        }
        var key = input.id.slice(separator + 1);
        cache[color][key] = input.value;
    }

    function captureModelValues(formElement, cache, model, transportModeEl) {
        if (!model) {
            return;
        }
        var store = ensureModelCache(cache, model);
        if (transportModeEl && model === "alex") {
            store.transport_mode = transportModeEl.value || "dynamic";
        }
        var inputs = formElement.querySelectorAll("input");
        inputs.forEach(function (input) {
            storeModelValue(store, input);
        });
    }

    function toggleNodes(dom, nodes, shouldShow) {
        nodes.forEach(function (node) {
            if (!node) {
                return;
            }
            if (shouldShow) {
                dom.show(node);
            } else {
                dom.hide(node);
            }
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var ash = controlBase();
        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        var formElement = dom.ensureElement("#ash_form", "Ash form not found.");
        var infoElement = dom.qs("#ash_form #info");
        var statusElement = dom.qs("#ash_form #status");
        var stacktraceElement = dom.qs("#ash_form #stacktrace");
        var rqJobElement = dom.qs("#ash_form #rq_job");
        var hintElement = dom.qs("#hint_run_ash");
        var spinnerElement = dom.qs("#ash_form #braille");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        ash.form = formElement;
        ash.info = infoAdapter;
        ash.status = statusAdapter;
        ash.stacktrace = stacktraceAdapter;
        ash.rq_job = rqJobAdapter;
        ash.command_btn_id = "btn_run_ash";
        ash.hint = hintAdapter;
        ash.events = emitter;
        ash.statusSpinnerEl = spinnerElement;
        ash._completion_seen = false;

        ash.attach_status_stream(ash, {
            form: formElement,
            channel: "ash",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });
        ash.rq_job_id = null;

        var depthModeInputs = dom.qsa('input[name="ash_depth_mode"]', formElement);
        var modelSelectEl = dom.qs('[data-ash-action="model-select"]', formElement) || dom.qs("#ash_model_select", formElement);
        var transportModeEl = dom.qs('[data-ash-action="transport-select"]', formElement) || dom.qs("#ash_transport_mode_select", formElement);
        var windCheckboxEl = dom.qs('[data-ash-action="toggle-wind"]', formElement) || dom.qs("#checkbox_run_wind_transport", formElement);

        var alexOnlyNodes = dom.qsa(".alex-only-param", formElement);
        var anuOnlyNodes = dom.qsa(".anu-only-param", formElement);
        var alexDynamicNodes = dom.qsa(".alex-dynamic-param", formElement);
        var alexStaticNodes = dom.qsa(".alex-static-param", formElement);
        var dynamicDescription = dom.qs("#dynamic_description", formElement);
        var staticDescription = dom.qs("#static_description", formElement);

        var depthModeContainers = {};
        Object.keys(DEPTH_MODE_IDS).forEach(function (key) {
            depthModeContainers[key] = dom.qs("#" + DEPTH_MODE_IDS[key], formElement);
        });

        var modelParams = readModelParams(dom);
        var modelValuesCache = {};

        var initialDepthMode = (function () {
            var checked = depthModeInputs.find(function (input) {
                return input && input.checked;
            });
            return checked ? checked.value : undefined;
        })();

        var state = {
            depthMode: parseDepthMode(initialDepthMode, 0),
            currentModel: modelSelectEl ? modelSelectEl.value || "multi" : "multi"
        };

        ash.ash_depth_mode = state.depthMode;
        ensureModelCache(modelValuesCache, state.currentModel);

        applyReadonlyMarkers(formElement);

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
        }

        function resetCompletionSeen() {
            ash._completion_seen = false;
        }

        function handleError(error, context) {
            var payload = toResponsePayload(http, error);
            ash.pushResponseStacktrace(ash, payload);
            var eventPayload = { jobId: null, error: payload };
            if (context && context.snapshot) {
                eventPayload.payload = context.snapshot;
            }
            emitter.emit("ash:run:completed", eventPayload);
        }

        function updateDepthModeUI(shouldEmit) {
            depthModeInputs.forEach(function (input) {
                if (!input) {
                    return;
                }
                input.checked = parseInt(input.value, 10) === state.depthMode;
            });

            var activeMode = Object.prototype.hasOwnProperty.call(DEPTH_MODE_IDS, state.depthMode)
                ? state.depthMode
                : 0;

            Object.keys(depthModeContainers).forEach(function (key) {
                var container = depthModeContainers[key];
                if (!container) {
                    return;
                }
                if (parseInt(key, 10) === activeMode) {
                    dom.show(container);
                } else {
                    dom.hide(container);
                }
            });

            if (shouldEmit) {
                emitter.emit("ash:mode:changed", { mode: state.depthMode });
            }
        }

        function toggleModelPanels(isAlex) {
            toggleNodes(dom, alexOnlyNodes, isAlex);
            toggleNodes(dom, anuOnlyNodes, !isAlex);
            if (!isAlex) {
                toggleNodes(dom, alexDynamicNodes, false);
                toggleNodes(dom, alexStaticNodes, false);
                if (dynamicDescription) {
                    dom.hide(dynamicDescription);
                }
                if (staticDescription) {
                    dom.hide(staticDescription);
                }
            }
        }

        function updateTransportModeUI(mode, shouldEmit) {
            if (!transportModeEl) {
                return;
            }
            transportModeEl.value = mode;
            if (state.currentModel !== "alex") {
                return;
            }
            var isDynamic = mode === "dynamic";
            toggleNodes(dom, alexDynamicNodes, isDynamic);
            toggleNodes(dom, alexStaticNodes, !isDynamic);
            if (dynamicDescription) {
                if (isDynamic) {
                    dom.show(dynamicDescription);
                } else {
                    dom.hide(dynamicDescription);
                }
            }
            if (staticDescription) {
                if (isDynamic) {
                    dom.hide(staticDescription);
                } else {
                    dom.show(staticDescription);
                }
            }
            if (shouldEmit) {
                emitter.emit("ash:transport:mode", {
                    model: state.currentModel,
                    transportMode: mode
                });
            }
        }

        function storeCurrentModelValue(input) {
            if (!state.currentModel) {
                return;
            }
            var cache = ensureModelCache(modelValuesCache, state.currentModel);
            storeModelValue(cache, input);
        }

        function setDepthMode(mode, emit) {
            var parsed = parseDepthMode(mode, state.depthMode || 0);
            if (state.depthMode === parsed) {
                updateDepthModeUI(false);
                return;
            }
            state.depthMode = parsed;
            ash.ash_depth_mode = parsed;
            ash.clearHint();
            updateDepthModeUI(emit);
        }

        function updateModelFormImpl(options) {
            options = options || {};
            if (!modelSelectEl) {
                return;
            }

            var selectedModel = modelSelectEl.value || "multi";
            var previousModel = state.currentModel;
            var capturePrevious = options.capturePrevious !== false;
            var shouldEmit = options.emit !== false;

            if (capturePrevious && previousModel && previousModel !== selectedModel) {
                captureModelValues(formElement, modelValuesCache, previousModel, transportModeEl);
                emitter.emit("ash:model:values:capture", { model: previousModel });
            }

            state.currentModel = selectedModel;
            ash.currentModel = selectedModel;

            var cache = ensureModelCache(modelValuesCache, selectedModel);
            var paramsForModel = modelParams[selectedModel] || {};
            var isAlex = selectedModel === "alex";

            toggleModelPanels(isAlex);

            if (transportModeEl) {
                if (isAlex) {
                    var mode = cache.transport_mode || transportModeEl.value || "dynamic";
                    transportModeEl.value = mode;
                    updateTransportModeUI(mode, shouldEmit);
                } else {
                    updateTransportModeUI(transportModeEl.value || "dynamic", false);
                }
            }

            ["white", "black"].forEach(function (color) {
                var mergedValues = mergeModelValues(paramsForModel[color] || {}, cache[color] || {});
                Object.keys(mergedValues).forEach(function (key) {
                    var inputId = "#" + color + "_" + key;
                    var input = dom.qs(inputId, formElement);
                    if (input) {
                        input.value = mergedValues[key];
                    }
                });
            });

            if (shouldEmit && previousModel !== selectedModel) {
                emitter.emit("ash:model:changed", {
                    model: selectedModel,
                    previousModel: previousModel
                });
            }
        }

        ash.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        ash.clearHint = function () {
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
        };

        ash.showHint = function (message) {
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text(message || "");
            }
        };

        ash.setAshDepthMode = function (mode) {
            setDepthMode(mode, true);
        };

        ash.handleDepthModeChange = function (mode) {
            ash.setAshDepthMode(mode);
        };

        ash.showHideControls = function () {
            updateDepthModeUI(false);
        };

        ash.updateModelForm = function (options) {
            updateModelFormImpl(options || {});
        };

        ash.validateBeforeRun = function () {
            ash.clearHint();

            if (state.depthMode === undefined) {
                var checked = depthModeInputs.find(function (input) {
                    return input && input.checked;
                });
                state.depthMode = parseDepthMode(checked ? checked.value : undefined, 0);
                ash.ash_depth_mode = state.depthMode;
            }

            if (state.depthMode === 2) {
                var errors = [];
                var allowedExtensions = [".tif", ".tiff", ".img"];
                var maxBytes = 100 * 1024 * 1024;
                var loadInput = dom.qs("#input_upload_ash_load", formElement);
                var typeInput = dom.qs("#input_upload_ash_type_map", formElement);
                [loadInput, typeInput].forEach(function (input) {
                    if (!input || !input.files || !input.files.length) {
                        return;
                    }
                    var file = input.files[0];
                    var name = (file.name || "").toLowerCase();
                    var hasAllowedExt = allowedExtensions.some(function (ext) {
                        return name.endsWith(ext);
                    });
                    if (!hasAllowedExt) {
                        errors.push(file.name + " must be a .tif, .tiff, or .img file.");
                    }
                    if (file.size > maxBytes) {
                        errors.push(file.name + " exceeds the 100 MB upload limit.");
                    }
                });
                if (errors.length) {
                    ash.showHint(errors.join(" "));
                    return false;
                }
            }

            return true;
        };

        ash.run = function () {
            var taskMsg = "Running ash model";
            resetCompletionSeen();
            resetStatus(taskMsg);

            if (!ash.validateBeforeRun()) {
                return;
            }

            ash.connect_status_stream(ash);

            var formData;
            var payloadSnapshot = null;
            try {
                formData = new FormData(formElement);
            } catch (err) {
                handleError(err, { snapshot: payloadSnapshot });
                return;
            }

            if (forms && typeof forms.formToJSON === "function") {
                try {
                    payloadSnapshot = forms.formToJSON(formElement);
                } catch (_err) {
                    payloadSnapshot = null;
                }
            }

            http.request(url_for_run("rq/api/run_ash"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true) {
                    statusAdapter.html("run_ash job submitted: " + payload.job_id);
                    ash.poll_completion_event = "ASH_RUN_TASK_COMPLETED";
                    ash.set_rq_job_id(ash, payload.job_id);
                    ash.rq_job_id = payload.job_id;
                    emitter.emit("ash:run:started", {
                        jobId: payload.job_id,
                        payload: payloadSnapshot
                    });
                } else {
                    ash.pushResponseStacktrace(ash, payload);
                    var failureEvent = { jobId: null, error: payload };
                    if (payloadSnapshot) {
                        failureEvent.payload = payloadSnapshot;
                    }
                    emitter.emit("ash:run:completed", failureEvent);
                }
            }).catch(function (error) {
                handleError(error, { snapshot: payloadSnapshot });
            });
        };

        ash.set_wind_transport = function (state) {
            var taskMsg = "Setting wind_transport(" + state + ")";
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_ash_wind_transport/"), {
                run_wind_transport: Boolean(state)
            }, {
                form: formElement
            }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true || payload.success === true) {
                    statusAdapter.html(taskMsg + "... Success");
                } else {
                    ash.pushResponseStacktrace(ash, payload);
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                ash.pushResponseStacktrace(ash, payload);
            });
        };

        ash.report = function () {
            var taskMsg = "Fetching Summary";
            resetStatus(taskMsg);

            var project = null;
            try {
                if (window.Project && typeof window.Project.getInstance === "function") {
                    project = window.Project.getInstance();
                }
            } catch (err) {
                console.warn("Ash controller unable to load Project instance", err);
            }

            var url = typeof window.url_for_run === "function"
                ? window.url_for_run("report/run_ash/")
                : "report/run_ash/";

            http.request(url, { method: "GET" }).then(function (response) {
                infoAdapter.html(response.body || "");
                statusAdapter.html(taskMsg + "... Success");
                if (project && typeof project.set_preferred_units === "function") {
                    project.set_preferred_units();
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                ash.pushResponseStacktrace(ash, payload);
            });
        };

        var baseTriggerEvent = ash.triggerEvent.bind(ash);
        ash.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "ASH_RUN_TASK_COMPLETED") {
                if (ash._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                ash._completion_seen = true;
                ash.disconnect_status_stream(ash);
                ash.report();
                emitter.emit("ash:run:completed", {
                    jobId: ash.rq_job_id || null,
                    payload: payload || null
                });
            }
            return baseTriggerEvent(eventName, payload);
        };

        dom.delegate(formElement, "change", 'input[name="ash_depth_mode"]', function (event, matched) {
            setDepthMode(matched.value, true);
        });

        dom.delegate(formElement, "click", '[data-ash-action="run"]', function (event) {
            event.preventDefault();
            ash.run();
        });

        dom.delegate(formElement, "change", '[data-ash-action="toggle-wind"]', function (event, checkbox) {
            ash.set_wind_transport(checkbox.checked);
        });

        if (modelSelectEl) {
            dom.delegate(formElement, "change", '[data-ash-action="model-select"]', function () {
                updateModelFormImpl({ capturePrevious: true, emit: true });
            });
        }

        if (transportModeEl) {
            dom.delegate(formElement, "change", '[data-ash-action="transport-select"]', function (event, select) {
                var cache = ensureModelCache(modelValuesCache, state.currentModel);
                cache.transport_mode = select.value || "dynamic";
                updateTransportModeUI(select.value || "dynamic", true);
            });
        }

        dom.delegate(formElement, "change", "input", function (event, input) {
            storeCurrentModelValue(input);
        });

        dom.delegate(formElement, "change", 'input[type="file"][data-ash-upload]', function () {
            ash.clearHint();
        });

        setDepthMode(state.depthMode, false);
        updateModelFormImpl({ capturePrevious: false, emit: false });
        if (transportModeEl && state.currentModel === "alex") {
            updateTransportModeUI(transportModeEl.value || "dynamic", false);
        }

        var bootstrapState = {
            reportTriggered: false,
            depthModeApplied: false,
            controlsShown: false
        };

        ash.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "ash")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_ash_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_ash_rq")) {
                    var value = jobIds.run_ash_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (jobId) {
                resetCompletionSeen();
                ash.poll_completion_event = "ASH_RUN_TASK_COMPLETED";
            }
            if (typeof ash.set_rq_job_id === "function") {
                ash.set_rq_job_id(ash, jobId);
            }

            var ashData = (ctx.data && ctx.data.ash) || {};

            var depthMode = controllerContext.depthMode;
            if (depthMode === undefined || depthMode === null) {
                depthMode = ashData.depthMode !== undefined ? ashData.depthMode : ashData.ashDepthMode;
            }
            if (depthMode === undefined || depthMode === null) {
                depthMode = state.depthMode;
            }

            if (!bootstrapState.depthModeApplied && typeof ash.setAshDepthMode === "function") {
                try {
                    ash.setAshDepthMode(depthMode);
                } catch (err) {
                    console.warn("[Ash] Failed to set depth mode", err);
                }
                bootstrapState.depthModeApplied = true;
            }

            var hasResults = controllerContext.hasResults;
            if (hasResults === undefined) {
                hasResults = ashData.hasResults !== undefined ? ashData.hasResults : ashData.has_results;
            }
            if (hasResults && !bootstrapState.reportTriggered && typeof ash.report === "function") {
                ash.report();
                bootstrapState.reportTriggered = true;
            }

            if (!bootstrapState.controlsShown && typeof ash.showHideControls === "function") {
                try {
                    ash.showHideControls();
                } catch (err) {
                    console.warn("[Ash] Failed to toggle controls", err);
                }
                bootstrapState.controlsShown = true;
            }

            return ash;
        };

        return ash;
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

if (typeof window !== "undefined") {
    window.Ash = Ash;
} else if (typeof globalThis !== "undefined") {
    globalThis.Ash = Ash;
}

/* ----------------------------------------------------------------------------
 * Batch Runner (Modernized)
 * Doc: controllers_js/README.md — Batch Runner Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var BatchRunner = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "batch:upload:started",
        "batch:upload:completed",
        "batch:upload:failed",
        "batch:template:validate-started",
        "batch:template:validate-completed",
        "batch:template:validate-failed",
        "batch:run-directives:updated",
        "batch:run-directives:update-failed",
        "batch:run:started",
        "batch:run:completed",
        "batch:run:failed",
        "batch:sbs-upload:started",
        "batch:sbs-upload:completed",
        "batch:sbs-upload:failed",
        "job:started",
        "job:completed",
        "job:error"
    ];

    var JOB_INFO_TERMINAL_STATUSES = new Set([
        "finished",
        "failed",
        "stopped",
        "canceled",
        "not_found",
        "complete",
        "completed",
        "success",
        "error"
    ]);

    var STATUS_STATE_MAP = {
        success: "success",
        ok: "success",
        completed: "success",
        complete: "success",
        finished: "success",
        error: "critical",
        failed: "critical",
        failure: "critical",
        stopped: "critical",
        canceled: "critical",
        cancelled: "critical",
        not_found: "warning",
        started: "info",
        warning: "warning",
        attention: "warning",
        queued: "warning",
        pending: "warning",
        info: "info",
        running: "info",
        active: "info",
        default: ""
    };

    var SELECTORS = {
        form: "#batch_runner_form",
        statusDisplay: "#batch_runner_form #status",
        stacktrace: "#batch_runner_form #stacktrace",
        infoPanel: "#batch_runner_form #info",
        rqJob: "#batch_runner_form #rq_job",
        container: "#batch-runner-root",
        resourceCard: "#batch-runner-resource-card",
        sbsCard: "#batch-runner-sbs-card",
        templateCard: "#batch-runner-template-card",
        runBatchButton: "#btn_run_batch",
        runBatchHint: "#hint_run_batch",
        runBatchLock: "#run_batch_lock"
    };

    var DATA_ROLES = {
        uploadForm: '[data-role="upload-form"]',
        geojsonInput: '[data-role="geojson-input"]',
        uploadButton: '[data-role="upload-button"]',
        uploadStatus: '[data-role="upload-status"]',
        resourceEmpty: '[data-role="resource-empty"]',
        resourceDetails: '[data-role="resource-details"]',
        resourceMeta: '[data-role="resource-meta"]',
        resourceSchema: '[data-role="resource-schema"]',
        resourceSchemaBody: '[data-role="resource-schema-body"]',
        resourceSamples: '[data-role="resource-samples"]',
        resourceSamplesBody: '[data-role="resource-samples-body"]',
        sbsUploadForm: '[data-role="sbs-upload-form"]',
        sbsInput: '[data-role="sbs-input"]',
        sbsUploadButton: '[data-role="sbs-upload-button"]',
        sbsUploadStatus: '[data-role="sbs-upload-status"]',
        sbsEmpty: '[data-role="sbs-empty"]',
        sbsDetails: '[data-role="sbs-details"]',
        sbsMeta: '[data-role="sbs-meta"]',
        runDirectiveList: '[data-role="run-directive-list"]',
        runDirectiveStatus: '[data-role="run-directive-status"]',
        templateInput: '[data-role="template-input"]',
        validateButton: '[data-role="validate-button"]',
        templateStatus: '[data-role="template-status"]',
        validationSummary: '[data-role="validation-summary"]',
        validationSummaryList: '[data-role="validation-summary-list"]',
        validationIssues: '[data-role="validation-issues"]',
        validationIssuesList: '[data-role="validation-issues-list"]',
        validationPreview: '[data-role="validation-preview"]',
        previewBody: '[data-role="preview-body"]'
    };

    var ACTIONS = {
        upload: '[data-action="batch-upload"]',
        uploadSbs: '[data-action="batch-upload-sbs"]',
        validate: '[data-action="batch-validate"]',
        run: '[data-action="batch-run"]'
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.show !== "function") {
            throw new Error("BatchRunner controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("BatchRunner controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("BatchRunner controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("BatchRunner controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function escapeHtml(value) {
        if (value === undefined || value === null) {
            return "";
        }
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function formatBytes(bytes) {
        if (bytes === undefined || bytes === null || isNaN(bytes)) {
            return "—";
        }
        var size = Number(bytes);
        if (size < 1024) {
            return size + " B";
        }
        if (size < 1024 * 1024) {
            return (size / 1024).toFixed(1) + " KB";
        }
        return (size / (1024 * 1024)).toFixed(1) + " MB";
    }

    function formatBBox(bbox) {
        if (!bbox || bbox.length !== 4) {
            return "—";
        }
        return bbox
            .map(function (val) {
                var num = Number(val);
                return Number.isFinite(num) ? num.toFixed(4) : String(val);
            })
            .join(", ");
    }

    function formatTimestamp(timestamp) {
        if (!timestamp) {
            return "—";
        }
        try {
            var date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                return date.toLocaleString();
            }
        } catch (err) {
            // ignore
        }
        return timestamp || "—";
    }

    function applyDataState(target, state) {
        if (!target) {
            return;
        }
        if (state) {
            target.setAttribute("data-state", state);
        } else {
            target.removeAttribute("data-state");
        }
    }

    function resolveStatusState(status) {
        if (!status) {
            return STATUS_STATE_MAP.default;
        }
        var key = String(status).toLowerCase();
        if (Object.prototype.hasOwnProperty.call(STATUS_STATE_MAP, key)) {
            return STATUS_STATE_MAP[key];
        }
        return STATUS_STATE_MAP.default;
    }

    function buildValidationMessage(summary) {
        if (!summary || typeof summary !== "object") {
            return [];
        }
        var items = [];
        if (summary.feature_count != null) {
            items.push("Features analysed: " + summary.feature_count);
        }
        if (summary.unique_runids != null) {
            items.push("Unique run IDs: " + summary.unique_runids);
        }
        if (summary.duplicate_runids && summary.duplicate_runids.length) {
            items.push("Duplicates: " + summary.duplicate_runids.length);
        }
        if (summary.missing_values && summary.missing_values.length) {
            items.push("Missing values: " + summary.missing_values.length);
        }
        return items;
    }

    function createInstance() {
        var base = controlBase();
        var deps = ensureHelpers();
        var emitter = deps.events.useEventMap(EVENT_NAMES, deps.events.createEmitter());

        var controller = Object.assign(base, {
            dom: deps.dom,
            forms: deps.forms,
            http: deps.http,
            eventsModule: deps.events,
            emitter: emitter
        });

        controller.state = {
            enabled: false,
            batchName: "",
            snapshot: {},
            validation: null,
            geojsonLimitMb: null
        };
        controller.sitePrefix = "";
        controller.baseUrl = "";
        controller.templateInitialised = false;
        controller.command_btn_id = "btn_run_batch";
        controller.statusStream = null;
        controller.statusSpinnerEl = null;
        controller._statusStreamRunId = null;

        controller._delegates = [];
        controller._runDirectivesSaving = false;
        controller._runDirectivesStatus = { message: "", state: "" };

        controller.jobInfo = {
            pollIntervalMs: 3000,
            refreshTimer: null,
            fetchInFlight: false,
            refreshPending: false,
            lastFetchStartedAt: 0,
            forceNextFetch: false,
            trackedIds: new Set(),
            completedIds: new Set(),
            lastPayload: null,
            abortController: null
        };

        controller.container = null;
        controller.resourceCard = null;
        controller.templateCard = null;

        controller.form = null;
        controller.statusDisplay = null;
        controller.stacktrace = null;
        controller.infoPanel = null;
        controller.rq_job = null;
        controller.runBatchButton = null;
        controller.runBatchHint = null;
        controller.runBatchLock = null;

        controller.uploadForm = null;
        controller.uploadInput = null;
        controller.uploadButton = null;
        controller.uploadStatus = null;
        controller.resourceEmpty = null;
        controller.resourceDetails = null;
        controller.resourceMeta = null;
        controller.resourceSchema = null;
        controller.resourceSchemaBody = null;
        controller.resourceSamples = null;
        controller.resourceSamplesBody = null;
        controller.sbsCard = null;
        controller.sbsUploadForm = null;
        controller.sbsUploadInput = null;
        controller.sbsUploadButton = null;
        controller.sbsUploadStatus = null;
        controller.sbsEmpty = null;
        controller.sbsDetails = null;
        controller.sbsMeta = null;
        controller.runDirectiveList = null;
        controller.runDirectiveStatus = null;

        controller.templateInput = null;
        controller.validateButton = null;
        controller.templateStatus = null;
        controller.validationSummary = null;
        controller.validationSummaryList = null;
        controller.validationIssues = null;
        controller.validationIssuesList = null;
        controller.validationPreview = null;
        controller.previewBody = null;

        controller._jobInfoTerminalStatuses = JOB_INFO_TERMINAL_STATUSES;
        controller._jobInfoTrackedIds = controller.jobInfo.trackedIds;
        controller._jobInfoCompletedIds = controller.jobInfo.completedIds;

        controller.init = init;
        controller.initCreate = init;
        controller.initManage = init;
        controller.destroy = destroy;
        controller.refreshJobInfo = refreshJobInfo;
        controller.runBatch = runBatch;
        controller.uploadGeojson = uploadGeojson;
        controller.validateTemplate = validateTemplate;

        controller.render = render;
        controller.renderResource = renderResource;
        controller.renderValidation = renderValidation;

        controller._setRunBatchMessage = setRunBatchMessage;
        controller._renderRunControls = renderRunControls;
        controller._setRunBatchBusy = setRunBatchBusy;
        controller._setUploadBusy = setUploadBusy;
        controller._setUploadStatus = setUploadStatus;
        controller._setValidateBusy = setValidateBusy;
        controller._setRunDirectivesStatus = setRunDirectivesStatus;
        controller._renderRunDirectives = renderRunDirectives;
        controller._applyResourceVisibility = applyResourceVisibility;
        controller._setSbsUploadStatus = setSbsUploadStatus;
        controller._setSbsUploadBusy = setSbsUploadBusy;

        controller._handleRunDirectiveToggle = handleRunDirectiveToggle;
        controller._handleUpload = handleUpload;
        controller._handleSbsUpload = handleSbsUpload;
        controller._handleValidate = handleValidate;

        controller._setRunDirectivesBusy = setRunDirectivesBusy;
        controller._submitRunDirectives = submitRunDirectives;

        controller._renderCoreStatus = renderCoreStatus;
        controller._renderJobInfo = renderJobInfo;
        controller._collectJobNodes = collectJobNodes;
        controller._registerTrackedJobId = registerTrackedJobId;
        controller._registerTrackedJobIds = registerTrackedJobIds;
        controller._unregisterTrackedJobId = unregisterTrackedJobId;
        controller._bootstrapTrackedJobIds = bootstrapTrackedJobIds;
        controller._resolveJobInfoRequestIds = resolveJobInfoRequestIds;
        controller._normalizeJobInfoPayload = normalizeJobInfoPayload;
        controller._registerJobInfoTrees = registerJobInfoTrees;
        controller._dedupeJobNodes = dedupeJobNodes;
        controller._pruneCompletedJobIds = pruneCompletedJobIds;
        controller._cancelJobInfoTimer = cancelJobInfoTimer;
        controller._ensureJobInfoFetchScheduled = ensureJobInfoFetchScheduled;
        controller._performJobInfoFetch = performJobInfoFetch;

        controller._buildBaseUrl = buildBaseUrl;
        controller._apiUrl = apiUrl;

        overrideControlBase(controller);

        return controller;

        function init(bootstrap) {
            bootstrap = bootstrap || {};
            controller.state = {
                enabled: Boolean(bootstrap.enabled),
                batchName: bootstrap.batchName || "",
                snapshot: bootstrap.state || {},
                validation: extractValidation(bootstrap.state || {}),
                geojsonLimitMb: bootstrap.geojsonLimitMb
            };
            controller.sitePrefix = bootstrap.sitePrefix || "";
            controller.baseUrl = buildBaseUrl();
            controller.templateInitialised = false;

            controller.form = deps.dom.qs(SELECTORS.form);
            controller.statusDisplay = deps.dom.qs(SELECTORS.statusDisplay);
            controller.stacktrace = deps.dom.qs(SELECTORS.stacktrace);
            controller.infoPanel = deps.dom.qs(SELECTORS.infoPanel);
            controller.rq_job = deps.dom.qs(SELECTORS.rqJob);

            controller.container = deps.dom.qs(SELECTORS.container);
            controller.resourceCard = deps.dom.qs(SELECTORS.resourceCard);
            controller.templateCard = deps.dom.qs(SELECTORS.templateCard);

            controller.runBatchButton = deps.dom.qs(SELECTORS.runBatchButton);
            controller.runBatchHint = deps.dom.qs(SELECTORS.runBatchHint);
            controller.runBatchLock = deps.dom.qs(SELECTORS.runBatchLock);
            if (!controller.statusSpinnerEl && controller.form) {
                try {
                    controller.statusSpinnerEl = controller.form.querySelector("#braille");
                } catch (err) {
                    controller.statusSpinnerEl = null;
                }
            }

            if (!controller.container) {
                console.warn("BatchRunner container not found");
                return controller;
            }

            cacheElements();
            bindEvents();

            updateStatusStream(controller.state.batchName);

            bootstrapTrackedJobIds(bootstrap);

            renderCoreStatus();
            render();
            refreshJobInfo();
            controller.render_job_status(controller);

            return controller;
        }

        function updateStatusStream(runId) {
            var desiredRunId = runId || window.runid || window.runId || null;
            if (controller._statusStreamRunId === desiredRunId && controller.statusStream) {
                return;
            }
            controller.detach_status_stream(controller);
            controller.attach_status_stream(controller, {
                form: controller.form,
                channel: "batch",
                runId: desiredRunId,
                spinner: controller.statusSpinnerEl,
                logLimit: 400
            });
            controller._statusStreamRunId = desiredRunId;
        }

        function destroy() {
            controller._delegates.forEach(function (unsubscribe) {
                try {
                    if (typeof unsubscribe === "function") {
                        unsubscribe();
                    }
                } catch (err) {
                    console.warn("Failed to remove BatchRunner delegate listener", err);
                }
            });
            controller._delegates = [];
            cancelJobInfoTimer();
            if (controller.jobInfo.abortController && typeof controller.jobInfo.abortController.abort === "function") {
                try {
                    controller.jobInfo.abortController.abort();
                } catch (err) {
                    console.warn("Failed to abort job info request during destroy", err);
                }
            }
        }

        function cacheElements() {
            if (!controller.resourceCard) {
                return;
            }
            controller.uploadForm = controller.resourceCard.querySelector(DATA_ROLES.uploadForm);
            controller.uploadInput = controller.resourceCard.querySelector(DATA_ROLES.geojsonInput);
            controller.uploadButton = controller.resourceCard.querySelector(DATA_ROLES.uploadButton);
            controller.uploadStatus = controller.resourceCard.querySelector(DATA_ROLES.uploadStatus);
            controller.resourceEmpty = controller.resourceCard.querySelector(DATA_ROLES.resourceEmpty);
            controller.resourceDetails = controller.resourceCard.querySelector(DATA_ROLES.resourceDetails);
            controller.resourceMeta = controller.resourceCard.querySelector(DATA_ROLES.resourceMeta);
            controller.resourceSchema = controller.resourceCard.querySelector(DATA_ROLES.resourceSchema);
            controller.resourceSchemaBody = controller.resourceCard.querySelector(DATA_ROLES.resourceSchemaBody);
            controller.resourceSamples = controller.resourceCard.querySelector(DATA_ROLES.resourceSamples);
            controller.resourceSamplesBody = controller.resourceCard.querySelector(DATA_ROLES.resourceSamplesBody);
            controller.sbsCard = deps.dom.qs(SELECTORS.sbsCard);
            if (controller.sbsCard) {
                controller.sbsUploadForm = controller.sbsCard.querySelector(DATA_ROLES.sbsUploadForm);
                controller.sbsUploadInput = controller.sbsCard.querySelector(DATA_ROLES.sbsInput);
                controller.sbsUploadButton = controller.sbsCard.querySelector(DATA_ROLES.sbsUploadButton);
                controller.sbsUploadStatus = controller.sbsCard.querySelector(DATA_ROLES.sbsUploadStatus);
                controller.sbsEmpty = controller.sbsCard.querySelector(DATA_ROLES.sbsEmpty);
                controller.sbsDetails = controller.sbsCard.querySelector(DATA_ROLES.sbsDetails);
                controller.sbsMeta = controller.sbsCard.querySelector(DATA_ROLES.sbsMeta);
            }
            controller.runDirectiveList = controller.container.querySelector(DATA_ROLES.runDirectiveList);
            controller.runDirectiveStatus = controller.container.querySelector(DATA_ROLES.runDirectiveStatus);
            if (controller.runDirectiveList && controller.runDirectiveList.classList) {
                controller.runDirectiveList.classList.add("wc-stack");
            }

            if (controller.templateCard) {
                controller.templateInput = controller.templateCard.querySelector(DATA_ROLES.templateInput);
                controller.validateButton = controller.templateCard.querySelector(DATA_ROLES.validateButton);
                controller.templateStatus = controller.templateCard.querySelector(DATA_ROLES.templateStatus);
                controller.validationSummary = controller.templateCard.querySelector(DATA_ROLES.validationSummary);
                controller.validationSummaryList = controller.templateCard.querySelector(DATA_ROLES.validationSummaryList);
                controller.validationIssues = controller.templateCard.querySelector(DATA_ROLES.validationIssues);
                controller.validationIssuesList = controller.templateCard.querySelector(DATA_ROLES.validationIssuesList);
                controller.validationPreview = controller.templateCard.querySelector(DATA_ROLES.validationPreview);
                controller.previewBody = controller.templateCard.querySelector(DATA_ROLES.previewBody);
            }
        }

        function bindEvents() {
            var delegates = controller._delegates;

            if (
                controller.uploadForm &&
                controller.uploadForm.tagName &&
                controller.uploadForm.tagName.toLowerCase() === "form"
            ) {
                delegates.push(
                    deps.dom.delegate(controller.uploadForm, "submit", function (event) {
                        event.preventDefault();
                        handleUpload();
                    })
                );
            }

            delegates.push(
                deps.dom.delegate(controller.resourceCard || controller.container, "click", ACTIONS.upload, function (event) {
                    event.preventDefault();
                    handleUpload();
                })
            );

            if (
                controller.sbsUploadForm &&
                controller.sbsUploadForm.tagName &&
                controller.sbsUploadForm.tagName.toLowerCase() === "form"
            ) {
                delegates.push(
                    deps.dom.delegate(controller.sbsUploadForm, "submit", function (event) {
                        event.preventDefault();
                        handleSbsUpload();
                    })
                );
            }

            delegates.push(
                deps.dom.delegate(controller.sbsCard || controller.container, "click", ACTIONS.uploadSbs, function (event) {
                    event.preventDefault();
                    handleSbsUpload();
                })
            );

            delegates.push(
                deps.dom.delegate(controller.templateCard || controller.container, "click", ACTIONS.validate, function (event) {
                    event.preventDefault();
                    handleValidate();
                })
            );

            delegates.push(
                deps.dom.delegate(controller.container, "change", "[data-run-directive]", function (event) {
                    handleRunDirectiveToggle(event);
                })
            );

            if (controller.runBatchButton) {
                delegates.push(
                    deps.dom.delegate(controller.runBatchButton, "click", ACTIONS.run, function (event) {
                        event.preventDefault();
                        runBatch();
                    })
                );
            }
        }

        function buildBaseUrl() {
            var prefix = controller.sitePrefix || "";
            if (prefix && prefix.slice(-1) === "/") {
                prefix = prefix.slice(0, -1);
            }
            if (controller.state.batchName) {
                return prefix + "/batch/_/" + encodeURIComponent(controller.state.batchName);
            }
            var pathname = window.location.pathname || "";
            return pathname.replace(/\/$/, "");
        }

        function apiUrl(suffix) {
            var base = controller.baseUrl || "";
            if (!suffix) {
                return base;
            }
            if (suffix.charAt(0) !== "/") {
                suffix = "/" + suffix;
            }
            return base + suffix;
        }

        function extractValidation(snapshot) {
            snapshot = snapshot || {};
            var metadata = snapshot.metadata || {};
            return metadata.template_validation || null;
        }

        function renderCoreStatus() {
            if (!controller.container) {
                return;
            }
            var snapshot = controller.state.snapshot || {};
            setText(controller.container.querySelector('[data-role="enabled-flag"]'), controller.state.enabled ? "True" : "False");
            setText(controller.container.querySelector('[data-role="batch-name"]'), controller.state.batchName || "—");
            setText(controller.container.querySelector('[data-role="manifest-version"]'), snapshot.state_version || "—");
            setText(controller.container.querySelector('[data-role="created-by"]'), snapshot.created_by || "—");
            setText(controller.container.querySelector('[data-role="manifest-json"]'), JSON.stringify(snapshot, null, 2));
        }

        function render() {
            renderResource();
            renderSbsResource();
            renderValidation();
            renderRunDirectives();
            renderRunControls();
        }

        function renderResource() {
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;

            if (!controller.resourceCard) {
                return;
            }

            if (!resource) {
                deps.dom.show(controller.resourceEmpty);
                deps.dom.hide(controller.resourceDetails);
                deps.dom.hide(controller.resourceSchema);
                deps.dom.hide(controller.resourceSamples);
                return;
            }

            deps.dom.hide(controller.resourceEmpty);
            deps.dom.show(controller.resourceDetails);

            var metaRows = [];
            metaRows.push(renderMetaRow("Filename", resource.filename || resource.original_filename || "—"));
            if (resource.uploaded_by) {
                metaRows.push(renderMetaRow("Uploaded by", resource.uploaded_by));
            }
            if (resource.uploaded_at) {
                metaRows.push(renderMetaRow("Uploaded at", formatTimestamp(resource.uploaded_at)));
            }
            if (resource.size_bytes != null) {
                metaRows.push(renderMetaRow("Size", formatBytes(resource.size_bytes)));
            }
            if (resource.feature_count != null) {
                metaRows.push(renderMetaRow("Features", resource.feature_count));
            }
            if (resource.bbox) {
                metaRows.push(renderMetaRow("Bounding Box", formatBBox(resource.bbox)));
            }
            if (resource.epsg) {
                metaRows.push(
                    renderMetaRow(
                        "EPSG",
                        resource.epsg + (resource.epsg_source ? " (" + resource.epsg_source + ")" : "")
                    )
                );
            }
            if (resource.checksum) {
                metaRows.push(renderMetaRow("Checksum", resource.checksum));
            }
            if (resource.relative_path) {
                metaRows.push(renderMetaRow("Path", resource.relative_path));
            }

            if (controller.resourceMeta) {
                controller.resourceMeta.innerHTML = metaRows.join("");
            }

            if (Array.isArray(resource.attribute_schema) && controller.resourceSchemaBody) {
                deps.dom.show(controller.resourceSchema);
                controller.resourceSchemaBody.innerHTML = resource.attribute_schema
                    .map(function (entry) {
                        var name = escapeHtml(entry.name || "—");
                        var type = escapeHtml(entry.type || entry.type_hint || "—");
                        return "<tr><td>" + name + "</td><td>" + type + "</td></tr>";
                    })
                    .join("");
            } else {
                deps.dom.hide(controller.resourceSchema);
            }

            if (Array.isArray(resource.sample_properties) && controller.resourceSamplesBody) {
                deps.dom.show(controller.resourceSamples);
                controller.resourceSamplesBody.innerHTML = resource.sample_properties
                    .map(function (entry, index) {
                        var props = escapeHtml(JSON.stringify(entry.properties || entry, null, 2));
                        var idx = escapeHtml(String(entry.index != null ? entry.index : index));
                        var featureId = escapeHtml(String(entry.feature_id || entry.id || "—"));
                        return (
                            "<tr><td>" +
                            idx +
                            "</td><td><code>" +
                            featureId +
                            '</code></td><td><pre class="wc-pre">' +
                            props +
                            "</pre></td></tr>"
                        );
                    })
                    .join("");
            } else {
                deps.dom.hide(controller.resourceSamples);
            }
        }

        function renderSbsResource() {
            if (!controller.sbsCard) {
                return;
            }
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.sbs_map;
            if (!controller.sbsEmpty || !controller.sbsDetails) {
                return;
            }

            if (!resource) {
                deps.dom.show(controller.sbsEmpty);
                deps.dom.hide(controller.sbsDetails);
                return;
            }

            deps.dom.hide(controller.sbsEmpty);
            deps.dom.show(controller.sbsDetails);

            var metaRows = [];
            metaRows.push(renderMetaRow("Filename", resource.filename || resource.original_filename || "—"));
            if (resource.uploaded_by) {
                metaRows.push(renderMetaRow("Uploaded by", resource.uploaded_by));
            }
            if (resource.uploaded_at) {
                metaRows.push(renderMetaRow("Uploaded at", formatTimestamp(resource.uploaded_at)));
            }
            if (resource.size_bytes != null) {
                metaRows.push(renderMetaRow("Size", formatBytes(resource.size_bytes)));
            }
            if (resource.relative_path) {
                metaRows.push(renderMetaRow("Path", resource.relative_path));
            }
            if (resource.sanity_message) {
                metaRows.push(renderMetaRow("Validation", resource.sanity_message));
            }
            if (resource.replaced) {
                metaRows.push(renderMetaRow("Replaced existing file", resource.replaced ? "Yes" : "No"));
            }
            if (resource.missing) {
                metaRows.push(renderMetaRow("Status", "File missing on disk"));
            }

            if (controller.sbsMeta) {
                controller.sbsMeta.innerHTML = metaRows.join("");
            }
        }

        function renderValidation() {
            var validation = controller.state.validation;
            if (!controller.templateCard) {
                return;
            }

            if (!controller.templateInitialised && controller.templateInput && controller.state.snapshot) {
                var storedTemplate = controller.state.snapshot.runid_template || "";
                controller.templateInput.value = storedTemplate || "";
                controller.templateInitialised = true;
            }

            if (!validation) {
                setText(controller.templateStatus, "");
                applyDataState(controller.templateStatus, "");
                deps.dom.hide(controller.validationSummary);
                deps.dom.hide(controller.validationIssues);
                deps.dom.hide(controller.validationPreview);
                return;
            }

            var status = validation.status || "unknown";
            var summary = validation.summary || {};
            var issues = validation.errors || [];
            var preview = validation.preview || [];

            if ((status === "unknown" || status === undefined || status === null) && summary.is_valid === true) {
                status = "ok";
                validation.status = "ok";
            }

            setText(
                controller.templateStatus,
                status === "ok" ? "Template is valid." : "Template requires attention."
            );
            applyDataState(controller.templateStatus, status === "ok" ? "success" : "warning");

            if (controller.validationSummary && controller.validationSummaryList) {
                var items = buildValidationMessage(summary).map(function (item) {
                    return "<li>" + escapeHtml(item) + "</li>";
                });
                controller.validationSummaryList.innerHTML = items.join("");
                deps.dom.toggle(controller.validationSummary, items.length > 0);
            }

            if (controller.validationIssues && controller.validationIssuesList) {
                if (issues.length) {
                    controller.validationIssuesList.innerHTML = issues
                        .slice(0, 10)
                        .map(function (item) {
                            return escapeHtml(item);
                        })
                        .join("<br>");
                    deps.dom.show(controller.validationIssues);
                } else {
                    controller.validationIssuesList.innerHTML = "";
                    deps.dom.hide(controller.validationIssues);
                }
            }

            if (controller.validationPreview && controller.previewBody) {
                if (Array.isArray(preview) && preview.length) {
                    controller.previewBody.innerHTML = preview
                        .slice(0, 25)
                        .map(function (entry) {
                            var rowIndex = escapeHtml(
                                entry.index != null
                                    ? entry.index
                                    : entry.one_based_index != null
                                    ? entry.one_based_index - 1
                                    : "—"
                            );
                            var featureId = escapeHtml(entry.feature_id || entry.featureId || "—");
                            var runid = escapeHtml(entry.runid || entry.runId || entry.run_id || "—");
                            var error = escapeHtml(entry.error || "");
                            return (
                                "<tr><td>" +
                                rowIndex +
                                "</td><td><code>" +
                                featureId +
                                "</code></td><td><code>" +
                                runid +
                                "</code></td><td>" +
                                error +
                                "</td></tr>"
                            );
                        })
                        .join("");
                    deps.dom.show(controller.validationPreview);
                } else {
                    controller.previewBody.innerHTML = "";
                    deps.dom.hide(controller.validationPreview);
                }
            }
        }

        function renderRunDirectives() {
            if (!controller.runDirectiveList) {
                return;
            }

            var snapshot = controller.state.snapshot || {};
            var directives = snapshot.run_directives || [];

            if (!Array.isArray(directives) || directives.length === 0) {
                controller.runDirectiveList.innerHTML =
                    '<div class="wc-text-muted">No batch tasks configured.</div>';
                setRunDirectivesStatus("No batch tasks configured.", "info");
                return;
            }

            var html = directives
                .map(function (directive, index) {
                    if (!directive || typeof directive !== "object") {
                        return "";
                    }
                    var slug = directive.slug || "directive-" + index;
                    var label = directive.label || slug;
                    var controlId = "batch-runner-directive-" + slug;
                    var checked = directive.enabled ? " checked" : "";
                    var disabled = !controller.state.enabled || controller._runDirectivesSaving ? " disabled" : "";
                    return (
                        '<label class="wc-choice wc-choice--checkbox">' +
                        '<input type="checkbox" id="' +
                        controlId +
                        '" data-run-directive="' +
                        escapeHtml(slug) +
                        '"' +
                        checked +
                        disabled +
                        ">" +
                        '<span class="wc-choice__body"><span class="wc-choice__label">' +
                        escapeHtml(label) +
                        "</span></span>" +
                        "</label>"
                    );
                })
                .join("");

            controller.runDirectiveList.innerHTML = html;
            syncRunDirectiveDisabledState();

            if (controller._runDirectivesStatus && controller._runDirectivesStatus.message) {
                applyStoredRunDirectiveStatus();
            } else if (!controller.state.enabled) {
                setRunDirectivesStatus("Batch runner is disabled; tasks cannot be edited.", "warning");
            }
        }

        function renderRunControls(options) {
            options = options || {};
            var preserveMessage = options.preserveMessage === true;

            if (!controller.runBatchButton) {
                return;
            }

            var jobLocked = controller.should_disable_command_button(controller);
            controller.update_command_button_state(controller);

            if (controller.runBatchLock) {
                if (jobLocked) {
                    deps.dom.show(controller.runBatchLock);
                } else {
                    deps.dom.hide(controller.runBatchLock);
                }
            }

            if (jobLocked) {
                controller.runBatchButton.disabled = true;
                setRunBatchMessage("Batch run in progress…", "info");
                return;
            }

            var enabled = Boolean(controller.state.enabled);
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;
            var templateState =
                controller.state.validation || (snapshot.metadata && snapshot.metadata.template_validation) || null;
            var templateStatus = templateState && (templateState.status || "ok");
            var summary = templateState && templateState.summary;
            var templateIsValid = Boolean(templateState && summary && summary.is_valid && templateStatus === "ok");

            var allowRun = enabled && Boolean(resource) && templateIsValid;
            var message = "";
            var state = "info";

            if (!enabled) {
                message = "Batch runner is disabled.";
                state = "warning";
            } else if (!resource) {
                message = "Upload a watershed GeoJSON before running.";
            } else if (!templateIsValid) {
                message = "Validate and resolve template issues before running.";
                state = "warning";
            } else {
                message = "Ready to run batch.";
                state = "success";
            }

            controller.runBatchButton.disabled = !allowRun;

            if (!preserveMessage || !allowRun) {
                setRunBatchMessage(message, state);
            }
        }

        function syncRunDirectiveDisabledState() {
            if (!controller.runDirectiveList) {
                return;
            }
            var shouldDisable = controller._runDirectivesSaving || !controller.state.enabled;
            var inputs = controller.runDirectiveList.querySelectorAll("input[data-run-directive]");
            inputs.forEach(function (input) {
                input.disabled = shouldDisable;
            });
        }

        function setRunDirectivesBusy(busy) {
            controller._runDirectivesSaving = busy === true;
            syncRunDirectiveDisabledState();
        }

        function setRunBatchBusy(busy, message, state) {
            if (controller.runBatchButton && busy) {
                controller.runBatchButton.disabled = true;
            }
            if (controller.runBatchLock) {
                if (busy) {
                    deps.dom.show(controller.runBatchLock);
                } else if (!controller.should_disable_command_button(controller)) {
                    deps.dom.hide(controller.runBatchLock);
                }
            }
            if (message != null) {
                setRunBatchMessage(message, state || "info");
            }
            if (!busy) {
                renderRunControls({ preserveMessage: true });
            }
        }

        function setRunDirectivesStatus(message, state) {
            controller._runDirectivesStatus = {
                message: message || "",
                state: state || ""
            };
            if (!controller.runDirectiveStatus) {
                return;
            }
            applyDataState(controller.runDirectiveStatus, state);
            setText(controller.runDirectiveStatus, message || "");
        }

        function applyStoredRunDirectiveStatus() {
            if (!controller.runDirectiveStatus) {
                return;
            }
            var status = controller._runDirectivesStatus || {};
            applyDataState(controller.runDirectiveStatus, status.state);
            setText(controller.runDirectiveStatus, status.message || "");
        }

        function setRunBatchMessage(message, state) {
            if (!controller.runBatchHint) {
                return;
            }
            applyDataState(controller.runBatchHint, state);
            setText(controller.runBatchHint, message || "");
        }

        function setUploadBusy(busy, message) {
            if (controller.uploadButton) {
                controller.uploadButton.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setUploadStatus(message, busy ? "info" : "");
            }
        }

        function setValidateBusy(busy, message) {
            if (controller.validateButton) {
                controller.validateButton.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setText(controller.templateStatus, message);
                applyDataState(controller.templateStatus, busy ? "info" : "");
            }
        }

        function setUploadStatus(message, state) {
            if (!controller.uploadStatus) {
                return;
            }
            applyDataState(controller.uploadStatus, state);
            setText(controller.uploadStatus, message || "");
        }

        function setSbsUploadBusy(busy, message) {
            if (controller.sbsUploadButton) {
                controller.sbsUploadButton.disabled = busy || !controller.state.enabled;
            }
            if (controller.sbsUploadInput) {
                controller.sbsUploadInput.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setSbsUploadStatus(message, busy ? "info" : "");
            }
        }

        function setSbsUploadStatus(message, state) {
            if (!controller.sbsUploadStatus) {
                return;
            }
            applyDataState(controller.sbsUploadStatus, state);
            setText(controller.sbsUploadStatus, message || "");
        }

        function collectRunDirectiveValues() {
            var result = {};
            if (!controller.runDirectiveList) {
                return result;
            }
            var inputs = controller.runDirectiveList.querySelectorAll("input[data-run-directive]");
            inputs.forEach(function (input) {
                var slug = input.getAttribute("data-run-directive");
                if (!slug) {
                    return;
                }
                result[String(slug)] = Boolean(input.checked);
            });
            return result;
        }

        function submitRunDirectives(values) {
            if (!values) {
                return;
            }
            setRunDirectivesBusy(true);
            setRunDirectivesStatus("Saving batch task selection…", "info");

            controller.http
                .postJson(apiUrl("run-directives"), { run_directives: values })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload || payload.success !== true) {
                        var errorMsg =
                            (payload && (payload.error || payload.message)) ||
                            "Failed to update batch tasks.";
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot;
                    } else if (Array.isArray(payload.run_directives)) {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.run_directives = payload.run_directives;
                        controller.state.snapshot = snapshot;
                    }

                    setRunDirectivesStatus("Batch tasks updated.", "success");
                    controller.emitter.emit("batch:run-directives:updated", {
                        success: true,
                        batchName: controller.state.batchName,
                        directives: controller.state.snapshot.run_directives || []
                    });
                    renderRunDirectives();
                    renderRunControls();
                })
                .catch(function (error) {
                    var message =
                        error && error.message ? error.message : "Failed to update batch tasks.";
                    setRunDirectivesStatus(message, "critical");
                    controller.emitter.emit("batch:run-directives:update-failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                    renderRunDirectives();
                    renderRunControls();
                })
                .finally(function () {
                    setRunDirectivesBusy(false);
                });
        }

        function handleRunDirectiveToggle(evt) {
            if (controller._runDirectivesSaving) {
                if (evt && typeof evt.preventDefault === "function") {
                    evt.preventDefault();
                }
                return;
            }

            if (!controller.state.enabled) {
                if (evt && typeof evt.preventDefault === "function") {
                    evt.preventDefault();
                }
                renderRunDirectives();
                return;
            }

            var values = collectRunDirectiveValues();
            submitRunDirectives(values);
        }

        function renderJobInfo(payload) {
            var infoPanel = controller.infoPanel;
            if (!infoPanel) {
                return;
            }

            if (!payload) {
                infoPanel.innerHTML = '<div class="wc-text-muted">Job information unavailable.</div>';
                return;
            }

            controller.jobInfo.lastPayload = payload;
            var normalized = normalizeJobInfoPayload(payload);
            var jobInfos = Array.isArray(normalized.jobs) ? normalized.jobs : [];

            if (!jobInfos.length) {
                infoPanel.innerHTML = '<div class="wc-text-muted">Job information unavailable.</div>';
                return;
            }

            registerJobInfoTrees(jobInfos);

            var nodes = [];
            jobInfos.forEach(function (info) {
                collectJobNodes(info, nodes);
            });
            var dedupedNodes = dedupeJobNodes(nodes);
            pruneCompletedJobIds(dedupedNodes);

            var watershedNodes = dedupedNodes.filter(function (node) {
                return node && node.runid;
            });

            var totalWatersheds = watershedNodes.length;
            var completedWatersheds = watershedNodes.filter(function (node) {
                return node.status === "finished";
            }).length;
            var failedWatersheds = watershedNodes.filter(function (node) {
                return (
                    node.status === "failed" ||
                    node.status === "stopped" ||
                    node.status === "canceled"
                );
            });
            var activeWatersheds = watershedNodes.filter(function (node) {
                return (
                    node.status &&
                    node.status !== "finished" &&
                    node.status !== "failed" &&
                    node.status !== "stopped" &&
                    node.status !== "canceled"
                );
            });

            var parts = ['<div class="wc-stack">'];

            if (jobInfos.length === 1) {
                var rootInfo = jobInfos[0] || {};
                parts.push(
                    '<div class="wc-status-chip"' +
                        (resolveStatusState(rootInfo.status) ? ' data-state="' + resolveStatusState(rootInfo.status) + '"' : "") +
                        ">Batch status: " +
                        escapeHtml(rootInfo.status || "unknown") +
                        "</div>"
                );
                if (rootInfo.id) {
                    parts.push(
                        '<div class="wc-text-muted">Job ID: <code>' + escapeHtml(rootInfo.id) + "</code></div>"
                    );
                }
            } else {
                parts.push("<div class=\"wc-text-muted\">Tracked jobs:</div>");
                var maxJobsToShow = 6;
                var jobBadges = jobInfos.slice(0, maxJobsToShow).map(function (info) {
                    var safeStatus = escapeHtml((info && info.status) || "unknown");
                    var safeId = escapeHtml((info && info.id) || "—");
                    var state = resolveStatusState(info && info.status);
                    return (
                        '<span class="wc-status-chip"' +
                        (state ? ' data-state="' + state + '"' : "") +
                        ">" +
                        safeStatus +
                        " · <code>" +
                        safeId +
                        "</code></span>"
                    );
                });
                if (jobInfos.length > maxJobsToShow) {
                    jobBadges.push('<span class="wc-text-muted">…</span>');
                }
                parts.push('<div>' + jobBadges.join(" ") + "</div>");
            }

            var allNotFound = jobInfos.every(function (info) {
                return info && info.status === "not_found";
            });

            if (allNotFound) {
                parts.push(
                    '<div class="wc-text-muted">Requested job IDs were not found in the queue.</div>'
                );
                parts.push("</div>");
                infoPanel.innerHTML = parts.join("");
                return;
            }

            if (totalWatersheds > 0) {
                parts.push(
                    '<div class="wc-text-muted">Watersheds: ' +
                        completedWatersheds +
                        "/" +
                        totalWatersheds +
                        " finished</div>"
                );
            } else {
                parts.push('<div class="wc-text-muted">Watershed tasks have not started yet.</div>');
            }

            if (activeWatersheds.length) {
                var activeList = activeWatersheds.slice(0, 6).map(function (node) {
                    var state = resolveStatusState(node.status || "running");
                    return (
                        '<span class="wc-status-chip"' +
                        (state ? ' data-state="' + state + '"' : "") +
                        ">" +
                        escapeHtml(node.runid) +
                        " · " +
                        escapeHtml(node.status || "pending") +
                        "</span>"
                    );
                });
                if (activeWatersheds.length > activeList.length) {
                    activeList.push('<span class="wc-text-muted">…</span>');
                }
                parts.push(
                    '<div class="wc-stack"><strong>Active</strong><div>' +
                        activeList.join(" ") +
                        "</div></div>"
                );
            }

            if (failedWatersheds.length) {
                var failedList = failedWatersheds.slice(0, 6).map(function (node) {
                    return (
                        '<span class="wc-status-chip" data-state="critical">' +
                        escapeHtml(node.runid) +
                        "</span>"
                    );
                });
                if (failedWatersheds.length > failedList.length) {
                    failedList.push('<span class="wc-text-muted">…</span>');
                }
                parts.push(
                    '<div class="wc-stack"><strong>Failures</strong><div>' +
                        failedList.join(" ") +
                        "</div></div>"
                );
            }

            parts.push("</div>");
            infoPanel.innerHTML = parts.join("");
        }

        function collectJobNodes(jobInfo, acc) {
            if (!jobInfo) {
                return;
            }
            acc.push(jobInfo);
            var children = jobInfo.children || {};
            Object.keys(children).forEach(function (orderKey) {
                var bucket = children[orderKey] || [];
                bucket.forEach(function (child) {
                    if (child) {
                        collectJobNodes(child, acc);
                    }
                });
            });
        }

        function registerTrackedJobId(jobId) {
            if (jobId === undefined || jobId === null) {
                return false;
            }
            var normalized = String(jobId).trim();
            if (!normalized) {
                return false;
            }
            if (controller.jobInfo.completedIds.has(normalized)) {
                return false;
            }
            if (!controller.jobInfo.trackedIds.has(normalized)) {
                controller.jobInfo.trackedIds.add(normalized);
                return true;
            }
            return false;
        }

        function unregisterTrackedJobId(jobId) {
            if (jobId === undefined || jobId === null) {
                return false;
            }
            var normalized = String(jobId).trim();
            if (!normalized) {
                return false;
            }
            if (controller.jobInfo.trackedIds.has(normalized)) {
                controller.jobInfo.trackedIds.delete(normalized);
                return true;
            }
            return false;
        }

        function registerTrackedJobIds(collection) {
            if (!collection) {
                return;
            }
            if (Array.isArray(collection)) {
                collection.forEach(registerTrackedJobId);
                return;
            }
            if (typeof collection === "object") {
                Object.keys(collection).forEach(function (key) {
                    registerTrackedJobId(collection[key]);
                });
                return;
            }
            registerTrackedJobId(collection);
        }

        function bootstrapTrackedJobIds(bootstrap) {
            if (!bootstrap || typeof bootstrap !== "object") {
                return;
            }

            if (Array.isArray(bootstrap.jobIds)) {
                registerTrackedJobIds(bootstrap.jobIds);
            }

            if (bootstrap.rqJobIds && typeof bootstrap.rqJobIds === "object") {
                registerTrackedJobIds(bootstrap.rqJobIds);
            }

            var snapshot = bootstrap.state || {};
            var metadata =
                snapshot && typeof snapshot === "object" ? snapshot.metadata || {} : {};

            registerTrackedJobIds(snapshot.job_ids);
            registerTrackedJobIds(metadata.job_ids);
            registerTrackedJobIds(metadata.rq_job_ids);
            registerTrackedJobIds(metadata.tracked_job_ids);
        }

        function resolveJobInfoRequestIds() {
            var ids = new Set();

            if (controller.rq_job_id) {
                var rootId = String(controller.rq_job_id).trim();
                if (rootId && !controller.jobInfo.completedIds.has(rootId)) {
                    ids.add(rootId);
                }
            }

            controller.jobInfo.trackedIds.forEach(function (value) {
                if (!value) {
                    return;
                }
                var normalizedTracked = String(value).trim();
                if (normalizedTracked && !controller.jobInfo.completedIds.has(normalizedTracked)) {
                    ids.add(normalizedTracked);
                }
            });

            return Array.from(ids);
        }

        function normalizeJobInfoPayload(payload) {
            if (!payload || typeof payload !== "object") {
                return { jobs: [] };
            }
            if (Array.isArray(payload.jobs)) {
                return payload;
            }
            if (Array.isArray(payload.job_info)) {
                return { jobs: payload.job_info };
            }
            if (payload.jobs && typeof payload.jobs === "object") {
                return { jobs: Object.values(payload.jobs) };
            }
            return { jobs: [] };
        }

        function registerJobInfoTrees(jobInfos) {
            if (!Array.isArray(jobInfos)) {
                return;
            }
            jobInfos.forEach(function (info) {
                if (info && info.id) {
                    registerTrackedJobId(info.id);
                    if (controller._jobInfoTerminalStatuses.has(info.status)) {
                        controller.jobInfo.completedIds.add(String(info.id).trim());
                    }
                }
            });
        }

        function dedupeJobNodes(nodes) {
            var seen = new Set();
            var result = [];
            nodes.forEach(function (node) {
                if (!node || !node.id) {
                    return;
                }
                var normalized = String(node.id).trim();
                if (seen.has(normalized)) {
                    return;
                }
                seen.add(normalized);
                result.push(node);
            });
            return result;
        }

        function pruneCompletedJobIds(nodes) {
            if (!Array.isArray(nodes)) {
                return;
            }
            nodes.forEach(function (node) {
                if (!node || !node.id) {
                    return;
                }
                var id = String(node.id).trim();
                if (!id) {
                    return;
                }
                if (controller._jobInfoTerminalStatuses.has(node.status)) {
                    controller.jobInfo.completedIds.add(id);
                    controller.jobInfo.trackedIds.delete(id);
                }
            });
        }

        function cancelJobInfoTimer() {
            if (controller.jobInfo.refreshTimer) {
                clearTimeout(controller.jobInfo.refreshTimer);
                controller.jobInfo.refreshTimer = null;
            }
        }

        function ensureJobInfoFetchScheduled() {
            if (controller.jobInfo.fetchInFlight) {
                return;
            }

            var now = Date.now();
            var interval = controller.jobInfo.pollIntervalMs || 0;
            var lastStarted = controller.jobInfo.lastFetchStartedAt || 0;
            var elapsed = now - lastStarted;
            var forceNext = controller.jobInfo.forceNextFetch === true;

            if (!forceNext && interval > 0 && elapsed < interval) {
                if (controller.jobInfo.refreshTimer) {
                    return;
                }
                controller.jobInfo.refreshTimer = setTimeout(function () {
                    controller.jobInfo.refreshTimer = null;
                    performJobInfoFetch();
                }, interval - elapsed);
                return;
            }

            controller.jobInfo.forceNextFetch = false;
            performJobInfoFetch();
        }

        function performJobInfoFetch() {
            if (!controller.infoPanel) {
                return;
            }

            if (controller.jobInfo.fetchInFlight) {
                return;
            }

            cancelJobInfoTimer();
            controller.jobInfo.forceNextFetch = false;

            var jobIds = resolveJobInfoRequestIds();
            if (!jobIds.length) {
                controller.jobInfo.refreshPending = false;
                if (!controller.jobInfo.lastPayload) {
                    controller.infoPanel.innerHTML =
                        '<div class="wc-text-muted">No batch job submitted yet.</div>';
                }
                return;
            }

            jobIds.forEach(registerTrackedJobId);

            controller.jobInfo.refreshPending = false;
            controller.jobInfo.fetchInFlight = true;
            controller.jobInfo.lastFetchStartedAt = Date.now();

            if (typeof AbortController !== "undefined") {
                if (controller.jobInfo.abortController) {
                    controller.jobInfo.abortController.abort();
                }
                controller.jobInfo.abortController = new AbortController();
            }

            var signal = controller.jobInfo.abortController
                ? controller.jobInfo.abortController.signal
                : undefined;

            controller.http
                .postJson("/weppcloud/rq/api/jobinfo", { job_ids: jobIds }, { signal: signal })
                .then(function (response) {
                    var payload = normalizeJobInfoPayload(response.body);
                    registerTrackedJobIds(payload.job_ids);
                    renderJobInfo(payload);
                })
                .catch(function (error) {
                    if (
                        error &&
                        error.name === "HttpError" &&
                        error.cause &&
                        error.cause.name === "AbortError"
                    ) {
                        return;
                    }
                    console.warn("Unable to refresh batch job info:", error);
                    if (controller.infoPanel) {
                        controller.infoPanel.innerHTML =
                            '<div class="wc-text-muted">Unable to refresh batch job details.</div>';
                    }
                })
                .finally(function () {
                    if (controller.jobInfo.abortController) {
                        controller.jobInfo.abortController = null;
                    }
                    controller.jobInfo.fetchInFlight = false;
                    if (controller.jobInfo.refreshPending) {
                        ensureJobInfoFetchScheduled();
                    }
                });
        }

        function refreshJobInfo(options) {
            options = options || {};
            if (!controller.infoPanel) {
                return;
            }

            if (options.force === true) {
                controller.jobInfo.forceNextFetch = true;
                controller.jobInfo.refreshPending = true;
                cancelJobInfoTimer();
                if (!controller.jobInfo.fetchInFlight) {
                    performJobInfoFetch();
                }
                return;
            }

            controller.jobInfo.refreshPending = true;
            ensureJobInfoFetchScheduled();
        }

        function applyResourceVisibility() {
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;

            if (!controller.resourceCard) {
                return;
            }

            if (!resource) {
                deps.dom.show(controller.resourceEmpty);
                deps.dom.hide(controller.resourceDetails);
                deps.dom.hide(controller.resourceSchema);
                deps.dom.hide(controller.resourceSamples);
            } else {
                deps.dom.hide(controller.resourceEmpty);
                deps.dom.show(controller.resourceDetails);
            }
        }

        function renderMetaRow(label, value) {
            return (
                '<div class="wc-summary-pane__item">' +
                '<dt class="wc-summary-pane__term">' +
                escapeHtml(label) +
                "</dt>" +
                '<dd class="wc-summary-pane__definition">' +
                escapeHtml(value) +
                "</dd>" +
                "</div>"
            );
        }

        function setText(node, value) {
            if (!node) {
                return;
            }
            node.textContent = value === undefined || value === null ? "" : String(value);
        }

        function handleUpload(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            if (!controller.state.enabled) {
                return;
            }
            var fileInput = controller.uploadInput;
            if (!fileInput || !fileInput.files || !fileInput.files.length) {
                setUploadStatus("Choose a GeoJSON file before uploading.", "warning");
                return;
            }

            var formData = new FormData();
            formData.append("geojson_file", fileInput.files[0]);

            setUploadBusy(true, "Uploading GeoJSON…");
            controller.emitter.emit("batch:upload:started", {
                batchName: controller.state.batchName,
                filename: fileInput.files[0].name,
                size: fileInput.files[0].size
            });

            controller.http
                .request(apiUrl("upload-geojson"), {
                    method: "POST",
                    body: formData
                })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.success) {
                        var errorMsg = payload.error || payload.message || "Upload failed.";
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot || {};
                        controller.state.validation = extractValidation(controller.state.snapshot);
                    } else {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.resources = snapshot.resources || {};
                        var resource = payload.resource;
                        if (!resource && payload.resource_metadata) {
                            resource = Object.assign({}, payload.resource_metadata);
                            var analysis = payload.template_validation || {};
                            if (analysis && typeof analysis === "object") {
                                if (analysis.feature_count != null) {
                                    resource.feature_count = analysis.feature_count;
                                }
                                if (analysis.bbox) {
                                    resource.bbox = analysis.bbox;
                                }
                                if (analysis.epsg) {
                                    resource.epsg = analysis.epsg;
                                }
                                if (analysis.epsg_source) {
                                    resource.epsg_source = analysis.epsg_source;
                                }
                                if (analysis.checksum) {
                                    resource.checksum = analysis.checksum;
                                }
                                if (analysis.size_bytes != null) {
                                    resource.size_bytes = analysis.size_bytes;
                                }
                                if (analysis.attribute_schema) {
                                    resource.attribute_schema = analysis.attribute_schema;
                                }
                                if (Array.isArray(analysis.properties)) {
                                    resource.properties = analysis.properties;
                                }
                                if (Array.isArray(analysis.sample_properties)) {
                                    resource.sample_properties = analysis.sample_properties;
                                }
                            }
                        }
                        if (resource) {
                            snapshot.resources.watershed_geojson = resource;
                        }
                        snapshot.metadata = snapshot.metadata || {};
                        if (payload.template_validation && payload.template_validation.summary) {
                            snapshot.metadata.template_validation = payload.template_validation;
                            controller.state.validation = payload.template_validation;
                        } else if (snapshot.metadata.template_validation) {
                            snapshot.metadata.template_validation.status = "stale";
                            controller.state.validation = snapshot.metadata.template_validation;
                        } else {
                            controller.state.validation = null;
                        }
                        controller.state.snapshot = snapshot;
                    }

                    setUploadStatus(payload.message || "Upload complete.", "success");
                    if (fileInput) {
                        fileInput.value = "";
                    }
                    controller.templateInitialised = false;
                    applyResourceVisibility();
                    render();

                    controller.emitter.emit("batch:upload:completed", {
                        success: true,
                        batchName: controller.state.batchName,
                        snapshot: controller.state.snapshot
                    });
                })
                .catch(function (error) {
                    var message = error && error.message ? error.message : "Upload failed.";
                    setUploadStatus(message, "critical");
                    controller.emitter.emit("batch:upload:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setUploadBusy(false);
                });
        }

        function handleSbsUpload(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            if (!controller.state.enabled) {
                return;
            }
            var fileInput = controller.sbsUploadInput;
            if (!fileInput || !fileInput.files || !fileInput.files.length) {
                setSbsUploadStatus("Choose an SBS map before uploading.", "warning");
                return;
            }

            var formData = new FormData();
            formData.append("sbs_map", fileInput.files[0]);

            setSbsUploadBusy(true, "Uploading SBS map…");
            controller.emitter.emit("batch:sbs-upload:started", {
                batchName: controller.state.batchName,
                filename: fileInput.files[0].name,
                size: fileInput.files[0].size
            });

            controller.http
                .request(apiUrl("upload-sbs-map"), {
                    method: "POST",
                    body: formData
                })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.success) {
                        var errorMsg = payload.error || payload.message || "Upload failed.";
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot || {};
                    } else {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.resources = snapshot.resources || {};
                        if (payload.resource) {
                            snapshot.resources.sbs_map = payload.resource;
                        }
                        controller.state.snapshot = snapshot;
                    }

                    setSbsUploadStatus(payload.message || "Upload complete.", "success");
                    if (fileInput) {
                        fileInput.value = "";
                    }
                    renderSbsResource();

                    controller.emitter.emit("batch:sbs-upload:completed", {
                        success: true,
                        batchName: controller.state.batchName,
                        snapshot: controller.state.snapshot
                    });
                })
                .catch(function (error) {
                    var message = error && error.message ? error.message : "Upload failed.";
                    setSbsUploadStatus(message, "critical");
                    controller.emitter.emit("batch:sbs-upload:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setSbsUploadBusy(false);
                });
        }

        function handleValidate(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            if (!controller.state.enabled) {
                return;
            }
            var template = (controller.templateInput && controller.templateInput.value || "").trim();
            if (!template) {
                setText(controller.templateStatus, "Enter a template before validating.");
                applyDataState(controller.templateStatus, "warning");
                return;
            }

            setValidateBusy(true, "Validating template…");
            controller.emitter.emit("batch:template:validate-started", {
                batchName: controller.state.batchName,
                template: template
            });

            controller.http
                .postJson(apiUrl("validate-template"), { template: template })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.validation) {
                        var errorMsg =
                            payload.error || payload.message || "Template validation failed.";
                        throw new Error(errorMsg);
                    }

                    controller.state.validation = payload.validation;
                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot || {};
                    } else {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.metadata = snapshot.metadata || {};
                        snapshot.metadata.template_validation = payload.stored;
                        snapshot.runid_template = template;
                        controller.state.snapshot = snapshot;
                    }
                    controller.templateInitialised = false;
                    render();

                    controller.emitter.emit("batch:template:validate-completed", {
                        success: true,
                        batchName: controller.state.batchName,
                        validation: payload.validation
                    });
                })
                .catch(function (error) {
                    var message =
                        error && error.message ? error.message : "Template validation failed.";
                    setText(controller.templateStatus, message);
                    applyDataState(controller.templateStatus, "critical");
                    controller.emitter.emit("batch:template:validate-failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setValidateBusy(false);
                });
        }

        function runBatch() {
            if (!controller.state.enabled) {
                setRunBatchMessage("Batch runner is disabled.", "warning");
                return;
            }

            if (controller.should_disable_command_button(controller)) {
                return;
            }

            if (
                controller.jobInfo.abortController &&
                typeof controller.jobInfo.abortController.abort === "function"
            ) {
                try {
                    controller.jobInfo.abortController.abort();
                } catch (abortError) {
                    console.warn(
                        "Failed to abort in-flight job info request before submitting batch:",
                        abortError
                    );
                }
                controller.jobInfo.abortController = null;
            }
            cancelJobInfoTimer();
            controller.jobInfo.fetchInFlight = false;
            controller.jobInfo.refreshPending = false;
            controller.jobInfo.forceNextFetch = false;
            controller.jobInfo.lastFetchStartedAt = 0;
            controller.jobInfo.trackedIds.clear();
            controller.jobInfo.completedIds.clear();
            controller.jobInfo.lastPayload = null;

            setRunBatchBusy(true, "Submitting batch run…", "info");

            controller.connect_status_stream(controller);

            if (controller.infoPanel) {
                controller.infoPanel.innerHTML =
                    '<div class="wc-status-chip" data-state="info">Submitting batch job…</div>';
            }

            controller.http
                .postJson(apiUrl(url_for_run("rq/api/run-batch")), {})
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.success) {
                        var errorMsg = payload.error || payload.message || "Failed to submit batch run.";
                        throw new Error(errorMsg);
                    }

                    if (payload.job_id) {
                        controller.set_rq_job_id(controller, payload.job_id);
                    } else {
                        controller.update_command_button_state(controller);
                    }

                    var successMessage = payload.message || "Batch run submitted.";
                    setRunBatchMessage(successMessage, "success");

                    controller.emitter.emit("batch:run:started", {
                        batchName: controller.state.batchName,
                        jobId: payload.job_id || null
                    });
                    controller.emitter.emit("job:started", {
                        batchName: controller.state.batchName,
                        jobId: payload.job_id || null
                    });
                })
                .catch(function (error) {
                    var message =
                        error && error.message ? error.message : "Failed to submit batch run.";
                    setRunBatchMessage(message, "critical");
                    if (controller.infoPanel) {
                        controller.infoPanel.innerHTML =
                            '<div class="wc-status-chip" data-state="critical">' +
                            escapeHtml(message) +
                            "</div>";
                    }
                    controller.disconnect_status_stream(controller);
                    controller.emitter.emit("batch:run:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                    controller.emitter.emit("job:error", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setRunBatchBusy(false);
                });
        }

        function uploadGeojson(event) {
            handleUpload(event);
            return false;
        }

        function validateTemplate(event) {
            handleValidate(event);
            return false;
        }

        function overrideControlBase(ctrl) {
            var baseSetRqJobId = ctrl.set_rq_job_id;
            ctrl.set_rq_job_id = function (self, jobId) {
                baseSetRqJobId.call(ctrl, self, jobId);
                if (self === ctrl) {
                    if (jobId) {
                        var normalizedJobId = String(jobId).trim();
                        if (ctrl.jobInfo.completedIds) {
                            ctrl.jobInfo.completedIds.delete(normalizedJobId);
                        }
                        registerTrackedJobId(normalizedJobId);
                    }
                    if (jobId) {
                        refreshJobInfo({ force: true });
                    } else if (ctrl.infoPanel) {
                        ctrl.infoPanel.innerHTML =
                            '<div class="wc-text-muted">No batch job submitted yet.</div>';
                    }
                }
            };

            var baseHandleJobStatusResponse = ctrl.handle_job_status_response;
            ctrl.handle_job_status_response = function (self, data) {
                baseHandleJobStatusResponse.call(ctrl, self, data);
                if (self === ctrl) {
                    refreshJobInfo();
                }
            };

            var baseTriggerEvent = ctrl.triggerEvent;
            ctrl.triggerEvent = function (eventName, payload) {
                if (eventName === "BATCH_RUN_COMPLETED" || eventName === "END_BROADCAST") {
                    ctrl.disconnect_status_stream(ctrl);
                    ctrl.reset_status_spinner(ctrl);
                    refreshJobInfo({ force: true });
                    if (eventName === "BATCH_RUN_COMPLETED") {
                        ctrl.emitter.emit("batch:run:completed", {
                            success: true,
                            batchName: ctrl.state.batchName,
                            jobId: ctrl.rq_job_id || null,
                            payload: payload || null
                        });
                        ctrl.emitter.emit("job:completed", {
                            success: true,
                            batchName: ctrl.state.batchName,
                            jobId: ctrl.rq_job_id || null,
                            payload: payload || null
                        });
                    }
                } else if (eventName === "BATCH_RUN_FAILED") {
                    ctrl.emitter.emit("batch:run:failed", {
                        error: payload && payload.error ? payload.error : "Batch run failed.",
                        batchName: ctrl.state.batchName
                    });
                    ctrl.emitter.emit("job:error", {
                        error: payload && payload.error ? payload.error : "Batch run failed.",
                        batchName: ctrl.state.batchName
                    });
                } else if (eventName === "BATCH_WATERSHED_TASK_COMPLETED") {
                    refreshJobInfo();
                }

                baseTriggerEvent.call(ctrl, eventName, payload);
            };
        }
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

window.BatchRunner = BatchRunner;

/* ----------------------------------------------------------------------------
 * Climate (Pure UI + Legacy Console)
 * Doc: controllers_js/README.md — Climate Controller Reference (2024 helper migration)
 * ----------------------------------------------------------------------------
 */
var Climate = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "climate:dataset:changed",
        "climate:dataset:mode",
        "climate:station:mode",
        "climate:station:selected",
        "climate:station:list:loading",
        "climate:station:list:loaded",
        "climate:build:started",
        "climate:build:completed",
        "climate:build:failed",
        "climate:precip:mode",
        "climate:upload:completed",
        "climate:upload:failed",
        "climate:gridmet:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (
            !dom ||
            typeof dom.ensureElement !== "function" ||
            typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" ||
            typeof dom.hide !== "function"
        ) {
            throw new Error("Climate controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Climate controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Climate controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Climate controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function parseJsonScript(id) {
        if (!id) {
            return null;
        }
        var element = document.getElementById(id);
        if (!element) {
            return null;
        }
        var raw = element.textContent || element.innerText || "";
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch (err) {
            console.error("[Climate] Failed to parse JSON from #" + id, err);
            return null;
        }
    }

    function ensureArray(value) {
        if (Array.isArray(value)) {
            return value.slice();
        }
        if (value === undefined || value === null) {
            return [];
        }
        return [value];
    }

    function parseInteger(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function toggleChoiceDisabled(input, disabled) {
        if (!input) {
            return;
        }
        var isDisabled = Boolean(disabled);
        input.disabled = isDisabled;
        if (isDisabled) {
            input.setAttribute("aria-disabled", "true");
        } else {
            input.removeAttribute("aria-disabled");
        }
        if (typeof input.closest === "function") {
            var wrapper = input.closest(".wc-choice");
            if (wrapper) {
                if (isDisabled) {
                    wrapper.classList.add("is-disabled");
                } else {
                    wrapper.classList.remove("is-disabled");
                }
            }
        }
    }

    function getRadioValue(radios) {
        if (!radios || radios.length === 0) {
            return null;
        }
        for (var i = 0; i < radios.length; i += 1) {
            if (radios[i] && radios[i].checked) {
                return radios[i].value;
            }
        }
        return null;
    }

    function setRadioValue(radios, targetValue) {
        if (!radios || radios.length === 0) {
            return;
        }
        var normalized = targetValue !== undefined && targetValue !== null ? String(targetValue) : null;
        for (var i = 0; i < radios.length; i += 1) {
            var radio = radios[i];
            if (!radio) {
                continue;
            }
            radio.checked = normalized !== null && String(radio.value) === normalized;
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var climate = controlBase();
        var climateEvents = events.useEventMap(EVENT_NAMES, events.createEmitter());

        var formElement = dom.ensureElement("#climate_form", "Climate form not found.");
        var infoElement = dom.qs("#climate_form #info");
        var statusElement = dom.qs("#climate_form #status");
        var stacktraceElement = dom.qs("#climate_form #stacktrace");
        var rqJobElement = dom.qs("#climate_form #rq_job");
        var hintUploadElement = dom.qs("#hint_upload_cli");
        var hintBuildElement = dom.qs("#hint_build_climate");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var uploadHintAdapter = createLegacyAdapter(hintUploadElement);
        var buildHintAdapter = createLegacyAdapter(hintBuildElement);

        climate.form = formElement;
        climate.info = infoAdapter;
        climate.status = statusAdapter;
        climate.stacktrace = stacktraceAdapter;
        climate.rq_job = rqJobAdapter;
        climate.command_btn_id = "btn_build_climate";
        climate.events = climateEvents;

        climate.statusPanelEl = dom.qs("#climate_status_panel");
        climate.stacktracePanelEl = dom.qs("#climate_stacktrace_panel");
        climate.statusSpinnerEl = climate.statusPanelEl ? climate.statusPanelEl.querySelector("#braille") : null;
        climate.statusStream = null;

        climate.datasetMessages = dom.qsa("[data-climate-group-message]");
        climate.stationSelect = dom.qs("#climate_station_selection");
        climate.monthliesContainer = dom.qs("#climate_monthlies");
        climate.catalogHiddenInput = dom.qs("#climate_catalog_id");
        climate.modeHiddenInput = dom.qs("#climate_mode");
        climate.userDefinedSection = dom.qs("#climate_userdefined");
        climate.cligenSection = dom.qs("#climate_cligen");
        climate.hintUpload = uploadHintAdapter;
        climate.hintBuild = buildHintAdapter;
        climate.hint = buildHintAdapter;

        climate.datasetRadios = dom.qsa("input[name=\"climate_dataset_choice\"]", formElement);
        climate.stationModeRadios = dom.qsa("input[name=\"climatestation_mode\"]", formElement);
        climate.spatialModeRadios = dom.qsa("input[name=\"climate_spatialmode\"]", formElement);
        climate.spatialModeHelpEl = dom.qs("#climate_spatialmode_help", formElement) || document.getElementById("climate_spatialmode_help");
        climate.precipModeRadios = dom.qsa("input[name=\"precip_scaling_mode\"]", formElement);
        climate.buildModeRadios = dom.qsa("input[name=\"climate_build_mode\"]", formElement);
        climate.gridmetCheckbox = dom.qs("#checkbox_use_gridmet_wind_when_applicable");

        climate.sectionNodes = dom.qsa("[data-climate-section]", formElement);
        climate.precipSections = dom.qsa("[data-precip-section]", formElement);

        climate.parDetails = dom.qs("[data-climate-par]", formElement);
        climate.parBody = climate.parDetails ? climate.parDetails.querySelector("[data-climate-par-body]") : null;
        climate._parLoaded = false;

        climate.catalogData = ensureArray(parseJsonScript("climate_catalog_data"));
        climate.datasetMap = {};
        climate.catalogData.forEach(function (dataset) {
            if (dataset && dataset.catalog_id) {
                climate.datasetMap[dataset.catalog_id] = dataset;
            }
        });

        climate.datasetId = null;
        climate._previousStationMode = null;
        climate._delegates = [];
        climate.spatialModeFieldEl = formElement
            ? formElement.querySelector("#climate_spatialmode_controls .wc-field")
            : document.querySelector("#climate_spatialmode_controls .wc-field");

        function handleError(error) {
            climate.pushResponseStacktrace(climate, toResponsePayload(http, error));
        }

        function resetCompletionSeen() {
            climate._completion_seen = false;
        }

        resetCompletionSeen();

        climate.updateSpatialModeHelp = function (mode) {
            if (!climate.spatialModeHelpEl) {
                return;
            }
            var normalized = mode !== null && mode !== undefined ? String(mode) : null;
            var radios = climate.spatialModeRadios || [];
            var targetRadio = null;
            for (var i = 0; i < radios.length; i += 1) {
                var radio = radios[i];
                if (!radio) {
                    continue;
                }
                if (normalized !== null && String(radio.value) === normalized) {
                    targetRadio = radio;
                    break;
                }
            }
            if (!targetRadio && radios.length > 0) {
                targetRadio = radios[0];
            }
            if (!targetRadio) {
                climate.spatialModeHelpEl.textContent = "";
                climate.spatialModeHelpEl.style.display = "none";
                return;
            }
            var title = targetRadio.getAttribute("data-spatial-help-title") || "";
            var body = targetRadio.getAttribute("data-spatial-help-body") || "";
            var small = document.createElement("small");
            if (title) {
                var strong = document.createElement("strong");
                strong.textContent = title + ":";
                small.appendChild(strong);
                if (body) {
                    small.appendChild(document.createTextNode(" " + body));
                }
            } else if (body) {
                small.textContent = body;
            }
            climate.spatialModeHelpEl.textContent = "";
            if (small.childNodes.length > 0) {
                climate.spatialModeHelpEl.appendChild(small);
                climate.spatialModeHelpEl.style.removeProperty("display");
            } else {
                climate.spatialModeHelpEl.style.display = "none";
            }
        };
        climate.adjustSpatialModeFieldSpacing = function () {
            if (climate.spatialModeFieldEl) {
                climate.spatialModeFieldEl.style.marginBottom = "0";
            }
        };
        climate.updateSpatialModeHelp(parseInteger(getRadioValue(climate.spatialModeRadios), 0));
        climate.adjustSpatialModeFieldSpacing();
        climate.updateSpatialModeHelp(parseInteger(getRadioValue(climate.spatialModeRadios), 0));

        climate.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (climate.statusStream && typeof climate.statusStream.append === "function") {
                climate.statusStream.append(message, meta || null);
                return;
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
                return;
            }
            if (statusElement) {
                statusElement.innerHTML = message;
            }
        };

        climate.resetParPreview = function () {
            climate._parLoaded = false;
            if (climate.parBody) {
                climate.parBody.innerHTML = '<p class="wc-text-muted">Expand to load the active station PAR file.</p>';
            }
            if (climate.parDetails) {
                climate.parDetails.removeAttribute("open");
            }
        };

        climate.loadParPreview = function () {
            if (!climate.parBody) {
                return;
            }
            climate.parBody.innerHTML = '<p class="wc-text-muted">Loading station PAR…</p>';
            http.request(url_for_run("view/par/"), { method: "GET" })
                .then(function (response) {
                    var text = response && response.body ? String(response.body) : "";
                    var pre = document.createElement("pre");
                    pre.className = "wc-pre";
                    pre.textContent = text || "No PAR contents available for the active station.";
                    climate.parBody.innerHTML = "";
                    climate.parBody.appendChild(pre);
                    climate._parLoaded = true;
                })
                .catch(function (error) {
                    console.error("[Climate] Failed to load PAR contents:", error);
                    climate.parBody.innerHTML = '<p class="wc-text-critical">Failed to load PAR contents.</p>';
                });
        };

        if (climate.parDetails && climate.parBody) {
            climate.parDetails.addEventListener("toggle", function () {
                if (climate.parDetails.open && !climate._parLoaded) {
                    climate.loadParPreview();
                }
            });
        }

        climate.resetParPreview();

        climate.attachStatusStream = function (options) {
            var opts = options ? Object.assign({}, options) : {};

            climate.detach_status_stream(climate);

            if (!climate.statusSpinnerEl && climate.statusPanelEl) {
                climate.statusSpinnerEl = climate.statusPanelEl.querySelector("#braille");
            }

            var stacktraceConfig;
            if (Object.prototype.hasOwnProperty.call(opts, "stacktrace")) {
                stacktraceConfig = opts.stacktrace;
                delete opts.stacktrace;
            } else if (climate.stacktracePanelEl) {
                stacktraceConfig = { element: climate.stacktracePanelEl };
            } else {
                stacktraceConfig = null;
            }

            var autoConnect = Object.prototype.hasOwnProperty.call(opts, "autoConnect")
                ? Boolean(opts.autoConnect)
                : false;
            if (Object.prototype.hasOwnProperty.call(opts, "autoConnect")) {
                delete opts.autoConnect;
            }

            var streamConfig = Object.assign({
                element: climate.statusPanelEl,
                form: formElement,
                channel: "climate",
                runId: window.runid || window.runId || null,
                logLimit: 400,
                stacktrace: stacktraceConfig,
                spinner: climate.statusSpinnerEl,
                autoConnect: autoConnect
            }, opts);

            climate.attach_status_stream(climate, streamConfig);

            return climate.statusStream;
        };

        function formatDatasetMessage(dataset) {
            var lines = [];
            if (!dataset) {
                return lines;
            }
            if (dataset.help_text) {
                lines.push(dataset.help_text);
            } else if (dataset.description) {
                lines.push(dataset.description);
            } else {
                lines.push("Configure the dataset-specific options below.");
            }
            if (dataset.rap_compatible) {
                lines.push("Compatible with RAP time-series workflows.");
            }
            if (dataset.ui_exposed === false) {
                lines.push("This dataset is read-only in the Pure UI and managed through catalog metadata.");
            }
            if (dataset.metadata && dataset.metadata.year_bounds) {
                var bounds = dataset.metadata.year_bounds;
                var minYear = bounds.min || bounds.min_start || bounds.start;
                var maxYear = bounds.max || bounds.max_end || bounds.end;
                if (minYear || maxYear) {
                    var rangeText = "Available years";
                    if (minYear && maxYear) {
                        rangeText += ": " + minYear + "–" + maxYear + ".";
                    } else if (minYear) {
                        rangeText += " from " + minYear + ".";
                    } else if (maxYear) {
                        rangeText += " through " + maxYear + ".";
                    }
                    lines.push(rangeText);
                }
            }
            return lines;
        }

        climate.getDataset = function (catalogId) {
            if (catalogId && climate.datasetMap[catalogId]) {
                return climate.datasetMap[catalogId];
            }
            if (climate.catalogData.length > 0) {
                return climate.catalogData[0];
            }
            return null;
        };

        climate.updateDatasetMessage = function (dataset) {
            if (!climate.datasetMessages || climate.datasetMessages.length === 0) {
                return;
            }
            var targetGroup = dataset && dataset.group ? dataset.group : null;
            var messages = formatDatasetMessage(dataset);

            climate.datasetMessages.forEach(function (msgEl) {
                var groupName = msgEl.getAttribute("data-climate-group-message");
                if (groupName === targetGroup && messages.length > 0) {
                    msgEl.innerHTML = "";
                    messages.forEach(function (line, index) {
                        var paragraph = document.createElement("p");
                        paragraph.className = index === 0 ? "wc-dataset-hint__text" : "wc-dataset-hint__meta";
                        paragraph.textContent = line;
                        msgEl.appendChild(paragraph);
                    });
                    msgEl.hidden = false;
                } else {
                    msgEl.innerHTML = "";
                    msgEl.hidden = true;
                }
            });
        };

        climate.updateSectionVisibility = function (dataset) {
            if (!climate.sectionNodes || climate.sectionNodes.length === 0) {
                return;
            }
            var inputs = ensureArray(dataset && dataset.inputs).map(function (value) {
                return String(value || "");
            });
            var spatialDefined = ensureArray(dataset && dataset.spatial_modes).length > 1;
            climate.sectionNodes.forEach(function (node) {
                if (!node || !node.getAttribute) {
                    return;
                }
                var key = node.getAttribute("data-climate-section");
                if (!key) {
                    return;
                }
                var shouldShow = inputs.indexOf(key) !== -1;
                if (key === "spatial_mode") {
                    shouldShow = shouldShow && spatialDefined;
                }
                node.hidden = !shouldShow;
            });
        };

        climate.updateSpatialModes = function (dataset, options) {
            var opts = options || {};
            if (!climate.spatialModeRadios || climate.spatialModeRadios.length === 0) {
                return;
            }
            var allowed = ensureArray(dataset && dataset.spatial_modes)
                .map(function (value) {
                    return parseInteger(value, null);
                })
                .filter(function (value) {
                    return value !== null && !Number.isNaN(value);
                });
            if (!allowed.length) {
                allowed = [0];
            }
            var defaultMode = dataset && dataset.default_spatial_mode !== undefined && dataset.default_spatial_mode !== null
                ? parseInteger(dataset.default_spatial_mode, allowed[0])
                : allowed[0];
            var currentValue = parseInteger(getRadioValue(climate.spatialModeRadios), defaultMode);
            var nextValue = currentValue;

            climate.spatialModeRadios.forEach(function (radio) {
                if (!radio) {
                    return;
                }
                var value = parseInteger(radio.value, null);
                var enabled = value !== null && allowed.indexOf(value) !== -1;
                toggleChoiceDisabled(radio, !enabled);
                if (!enabled && value === currentValue) {
                    nextValue = defaultMode;
                }
            });

            if (Number.isNaN(currentValue) || nextValue !== currentValue) {
                climate.setSpatialMode(nextValue, { silent: true });
            } else if (opts.silent) {
                climate.setSpatialMode(currentValue, { silent: true });
            }
        };

        climate.updateStationVisibility = function (dataset) {
            var section = document.getElementById("climate_station_section");
            if (!section) {
                return;
            }
            var stationModes = ensureArray(dataset && dataset.station_modes)
                .map(function (value) {
                    return parseInteger(value, null);
                })
                .filter(function (value) {
                    return value !== null && !Number.isNaN(value);
                });
            if (!stationModes.length) {
                stationModes = [-1, 0];
            }
            var shouldShow = stationModes.some(function (value) {
                return value !== 4;
            });
            section.hidden = !shouldShow;
        };

        climate.updateStationModes = function (dataset, options) {
            var opts = options || {};
            if (!climate.stationModeRadios || climate.stationModeRadios.length === 0) {
                return;
            }
            var allowed = ensureArray(dataset && dataset.station_modes)
                .map(function (value) {
                    return parseInteger(value, null);
                })
                .filter(function (value) {
                    return value !== null && !Number.isNaN(value);
                });
            if (!allowed.length) {
                allowed = [-1, 0];
            }
            var currentValue = parseInteger(getRadioValue(climate.stationModeRadios), allowed[0]);
            var nextValue = currentValue;

            climate.stationModeRadios.forEach(function (radio) {
                if (!radio) {
                    return;
                }
                var value = parseInteger(radio.value, null);
                var enabled = value !== null && allowed.indexOf(value) !== -1;
                toggleChoiceDisabled(radio, !enabled);
                if (!enabled && value === currentValue) {
                    nextValue = allowed[0];
                }
            });

            if (Number.isNaN(currentValue) || nextValue !== currentValue) {
                climate.setStationMode(nextValue, { silent: true, skipRefresh: true });
            } else if (opts.silent) {
                climate.setStationMode(currentValue, { silent: true, skipRefresh: true });
            }

            if (!(opts.skipStationRefresh || (allowed.length === 1 && allowed[0] === 4))) {
                climate.refreshStationSelection();
            } else if (allowed.length === 1 && allowed[0] === 4 && climate.stationSelect) {
                climate.stationSelect.innerHTML = "";
            }
        };

        climate.applyDataset = function (catalogId, options) {
            var dataset = climate.getDataset(catalogId);
            if (!dataset) {
                return null;
            }
            climate.datasetId = dataset.catalog_id || null;
            if (climate.catalogHiddenInput) {
                climate.catalogHiddenInput.value = dataset.catalog_id || "";
            }
            if (climate.modeHiddenInput) {
                climate.modeHiddenInput.value = dataset.climate_mode !== undefined && dataset.climate_mode !== null
                    ? String(dataset.climate_mode)
                    : "";
            }
            if (climate.datasetRadios && climate.datasetRadios.length > 0) {
                setRadioValue(climate.datasetRadios, dataset.catalog_id);
            }
            climate.updateDatasetMessage(dataset);
            climate.updateSectionVisibility(dataset);
            climate.updateSpatialModes(dataset, options || {});
            climate.updateStationModes(dataset, options || {});
            climate.updateStationVisibility(dataset);
            climate.resetParPreview();
            climate.events.emit("climate:dataset:mode", {
                catalogId: dataset.catalog_id,
                climateMode: dataset.climate_mode
            });
            return dataset;
        };

        climate.handleDatasetChange = function (catalogId) {
            infoAdapter.text("");
            stacktraceAdapter.text("");

            var dataset = climate.applyDataset(catalogId, { skipPersist: true, skipStationRefresh: true });
            if (!dataset) {
                return;
            }
            climate.events.emit("climate:dataset:changed", {
                catalogId: dataset.catalog_id,
                dataset: dataset
            });

            climate.setCatalogMode(dataset.catalog_id, dataset.climate_mode)
                .then(function () {
                    var stationModes = ensureArray(dataset.station_modes)
                        .map(function (value) {
                            return parseInteger(value, null);
                        })
                        .filter(function (value) {
                            return value !== null && !Number.isNaN(value);
                        });
                    if (stationModes.length === 1 && stationModes[0] === 4 && climate.stationSelect) {
                        climate.stationSelect.innerHTML = "";
                    } else {
                        climate.refreshStationSelection();
                    }
                    climate.viewStationMonthlies();
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.setCatalogMode = function (catalogId, mode) {
            infoAdapter.text("");
            stacktraceAdapter.text("");

            var payload = {};
            var normalizedMode = parseInteger(mode, null);
            if (normalizedMode !== null && !Number.isNaN(normalizedMode)) {
                payload.mode = normalizedMode;
            }
            if (catalogId !== undefined && catalogId !== null && catalogId !== "") {
                payload.catalog_id = catalogId;
            }
            return http.postJson(url_for_run("tasks/set_climate_mode/"), payload, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETMODE_TASK_COMPLETED", body);
                        return body;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    return Promise.reject(body);
                })
                .catch(function (error) {
                    handleError(error);
                    return Promise.reject(error);
                });
        };

        climate.setStationMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = parseInteger(mode, -1);
            setRadioValue(climate.stationModeRadios, parsedMode);

            if (parsedMode !== 4) {
                climate._previousStationMode = parsedMode;
            }

            if (opts.silent) {
                if (!opts.skipRefresh) {
                    climate.refreshStationSelection();
                }
                climate.events.emit("climate:station:mode", { mode: parsedMode, silent: true });
                return Promise.resolve(null);
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            climate.events.emit("climate:station:mode", { mode: parsedMode, silent: false });

            return http.postJson(url_for_run("tasks/set_climatestation_mode/"), { mode: parsedMode }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        var eventPayload = Object.assign({}, body, {
                            mode: parsedMode,
                            skipRefresh: Boolean(opts.skipRefresh),
                            skipMonthlies: Boolean(opts.skipMonthlies)
                        });
                        climate.triggerEvent("CLIMATE_SETSTATIONMODE_TASK_COMPLETED", eventPayload);
                        return body;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    return Promise.reject(body);
                })
                .catch(function (error) {
                    handleError(error);
                    return Promise.reject(error);
                });
        };

        climate.setSpatialMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = parseInteger(mode, 0);
            setRadioValue(climate.spatialModeRadios, parsedMode);
            climate.updateSpatialModeHelp(parsedMode);
            climate.adjustSpatialModeFieldSpacing();

            if (opts.silent) {
                return Promise.resolve(null);
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            return http.postJson(url_for_run("tasks/set_climate_spatialmode/"), { spatialmode: parsedMode }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETSPATIALMODE_TASK_COMPLETED", body);
                        return body;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    return Promise.reject(body);
                })
                .catch(function (error) {
                    handleError(error);
                    return Promise.reject(error);
                });
        };

        climate.refreshStationSelection = function () {
            if (!climate.stationSelect) {
                return;
            }
            var mode = parseInteger(getRadioValue(climate.stationModeRadios), -1);
            if (mode === -1 || mode === 4) {
                return;
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");
            climate.resetParPreview();

            var endpoint = null;
            if (mode === 0) {
                endpoint = url_for_run("view/closest_stations/");
            } else if (mode === 1) {
                endpoint = url_for_run("view/heuristic_stations/");
            } else if (mode === 2) {
                endpoint = url_for_run("view/eu_heuristic_stations/");
            } else if (mode === 3) {
                endpoint = url_for_run("view/au_heuristic_stations/");
            }
            if (!endpoint) {
                return;
            }

            climate.events.emit("climate:station:list:loading", { mode: mode });

            http.request(endpoint, { params: { mode: mode } })
                .then(function (response) {
                    var body = response.body;
                    climate.stationSelect.innerHTML = typeof body === "string" ? body : "";
                    climate.triggerEvent("CLIMATE_SETSTATION_TASK_COMPLETED", { mode: mode });
                    climate.events.emit("climate:station:list:loaded", { mode: mode });
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.setStation = function (station) {
            var selectedStation = station;
            if (selectedStation === undefined || selectedStation === null) {
                selectedStation = climate.stationSelect ? climate.stationSelect.value : null;
            }
            if (!selectedStation) {
                return;
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            climate.events.emit("climate:station:selected", { station: selectedStation });

            http.postJson(url_for_run("tasks/set_climatestation/"), { station: selectedStation }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETSTATION_TASK_COMPLETED", body);
                        climate.resetParPreview();
                        return;
                    }
                    climate.pushResponseStacktrace(climate, body);
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.viewStationMonthlies = function () {
            if (!climate.monthliesContainer) {
                return;
            }
            var project = window.Project && typeof window.Project.getInstance === "function" ? window.Project.getInstance() : null;
            http.request(url_for_run("view/climate_monthlies/"), { params: {} })
                .then(function (response) {
                    var body = response.body;
                    climate.monthliesContainer.innerHTML = typeof body === "string" ? body : "";
                    if (project && typeof project.set_preferred_units === "function") {
                        project.set_preferred_units();
                    }
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.handlePrecipScalingModeChange = function (mode) {
            var parsedMode = parseInteger(mode, -1);
            if (climate.precipModeRadios && climate.precipModeRadios.length > 0) {
                setRadioValue(climate.precipModeRadios, parsedMode);
            }
            if (climate.precipSections) {
                climate.precipSections.forEach(function (section) {
                    if (!section || !section.getAttribute) {
                        return;
                    }
                    var key = parseInteger(section.getAttribute("data-precip-section"), -1);
                    section.hidden = key !== parsedMode;
                });
            }
            climate.events.emit("climate:precip:mode", { mode: parsedMode });
        };

        climate.report = function () {
            var project = window.Project && typeof window.Project.getInstance === "function" ? window.Project.getInstance() : null;
            http.request(url_for_run("report/climate/"), { params: {}, method: "GET" })
                .then(function (response) {
                    var body = response.body;
                    if (infoAdapter && typeof infoAdapter.html === "function") {
                        infoAdapter.html(typeof body === "string" ? body : "");
                    } else if (infoElement) {
                        infoElement.innerHTML = typeof body === "string" ? body : "";
                    }
                    if (project && typeof project.set_preferred_units === "function") {
                        project.set_preferred_units();
                    }
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.build = function () {
            if (!climate._statusStreamHandle) {
                climate.attachStatusStream({ autoConnect: false });
            }
            resetCompletionSeen();
            climate.connect_status_stream(climate);

            var taskMsg = "Building climate";
            climate.reset_panel_state(climate, { taskMessage: taskMsg });

            var payload = forms.serializeForm(formElement, { format: "json" });
            climate.events.emit("climate:build:started", { payload: payload });

            http.postJson(url_for_run("rq/api/build_climate"), payload, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        var message = "build_climate job submitted: " + body.job_id;
                        statusAdapter.html(message);
                        climate.appendStatus(message);
                        climate.poll_completion_event = "CLIMATE_BUILD_TASK_COMPLETED";
                        climate.set_rq_job_id(climate, body.job_id);
                        climate.events.emit("climate:build:completed", { jobId: body.job_id, payload: payload });
                        return;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    climate.events.emit("climate:build:failed", { payload: payload, response: body });
                })
                .catch(function (error) {
                    handleError(error);
                    climate.events.emit("climate:build:failed", { payload: payload, error: error });
                });
        };

        climate.upload_cli = function () {
            infoAdapter.text("");
            stacktraceAdapter.text("");

            var formData = new FormData(formElement);
            http.request(url_for_run("tasks/upload_cli/"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (response) {
                var body = response.body || {};
                if (body.Success === true) {
                    climate.appendStatus("User-defined climate uploaded successfully.");
                    resetCompletionSeen();
                    climate.triggerEvent("CLIMATE_BUILD_TASK_COMPLETED", body);
                    climate.events.emit("climate:upload:completed", body);
                    return;
                }
                climate.pushResponseStacktrace(climate, body);
                climate.events.emit("climate:upload:failed", body);
            }).catch(function (error) {
                handleError(error);
                climate.events.emit("climate:upload:failed", { error: error });
            });
        };

        climate.set_use_gridmet_wind_when_applicable = function (state) {
            var normalizedState = Boolean(state);
            statusAdapter.html("Setting use_gridmet_wind_when_applicable (" + normalizedState + ")...");
            stacktraceAdapter.text("");

            http.postJson(url_for_run("tasks/set_use_gridmet_wind_when_applicable/"), { state: normalizedState }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        var message = "use_gridmet_wind_when_applicable updated.";
                        statusAdapter.html(message);
                        climate.appendStatus(message);
                        climate.events.emit("climate:gridmet:updated", { state: normalizedState });
                        return;
                    }
                    climate.pushResponseStacktrace(climate, body);
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.setBuildMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = parseInteger(mode, 0);
            if (climate.buildModeRadios && climate.buildModeRadios.length > 0) {
                setRadioValue(climate.buildModeRadios, parsedMode);
            }
            if (parsedMode === 1) {
                if (climate.userDefinedSection) {
                    dom.show(climate.userDefinedSection);
                }
                if (climate.cligenSection) {
                    dom.hide(climate.cligenSection);
                }
                if (!opts.skipStationMode) {
                    climate.setStationMode(4, { silent: false, skipRefresh: true });
                    if (climate.stationSelect) {
                        climate.stationSelect.innerHTML = "";
                    }
                }
            } else {
                if (climate.userDefinedSection) {
                    dom.hide(climate.userDefinedSection);
                }
                if (climate.cligenSection) {
                    dom.show(climate.cligenSection);
                }
                if (!opts.skipStationMode) {
                    var restoreMode = climate._previousStationMode;
                    if (restoreMode === null || restoreMode === undefined || restoreMode === 4) {
                        restoreMode = 0;
                    }
                    climate.setStationMode(restoreMode, { silent: false });
                }
            }
        };

        climate.handleBuildModeChange = function (value) {
            climate.setBuildMode(value, { skipStationMode: false });
        };

        climate.handleModeChange = function (value) {
            var parsedMode = parseInteger(value, null);
            if (climate.modeHiddenInput) {
                climate.modeHiddenInput.value = parsedMode !== null && !Number.isNaN(parsedMode) ? String(parsedMode) : "";
            }
            climate.setCatalogMode(climate.datasetId, parsedMode)
                .then(function () {
                    climate.viewStationMonthlies();
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        var baseTriggerEvent = climate.triggerEvent.bind(climate);
        climate.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "CLIMATE_SETSTATIONMODE_TASK_COMPLETED") {
                var skipRefresh = payload && payload.skipRefresh;
                var skipMonthlies = payload && payload.skipMonthlies;
                if (!skipRefresh) {
                    climate.refreshStationSelection();
                }
                if (!skipMonthlies) {
                    climate.viewStationMonthlies();
                }
            } else if (normalized === "CLIMATE_SETSTATION_TASK_COMPLETED") {
                climate.viewStationMonthlies();
            } else if (normalized === "CLIMATE_BUILD_TASK_COMPLETED" || normalized === "CLIMATE_BUILD_COMPLETE") {
                if (climate._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                climate._completion_seen = true;
                climate.report();
            }
            return baseTriggerEvent(eventName, payload);
        };

        if (typeof dom.delegate === "function") {
            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"dataset\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handleDatasetChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"station-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.setStationMode(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"spatial-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.setSpatialMode(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handleModeChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"station-select\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.setStation(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"precip-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handlePrecipScalingModeChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"gridmet-wind\"]", function (event, matched) {
                event.preventDefault();
                var checked = matched ? matched.checked : false;
                climate.set_use_gridmet_wind_when_applicable(checked);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"build-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handleBuildModeChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "click", "[data-climate-action=\"upload-cli\"]", function (event) {
                event.preventDefault();
                climate.upload_cli();
            }));

            climate._delegates.push(dom.delegate(formElement, "click", "[data-climate-action=\"build\"]", function (event) {
                event.preventDefault();
                climate.build();
            }));
        }

        var initialDatasetId = null;
        if (climate.catalogHiddenInput && climate.catalogHiddenInput.value) {
            initialDatasetId = climate.catalogHiddenInput.value;
        }
        if (!initialDatasetId && climate.datasetRadios && climate.datasetRadios.length > 0) {
            var radioValue = getRadioValue(climate.datasetRadios);
            if (radioValue !== null) {
                initialDatasetId = radioValue;
            }
        }
        if (initialDatasetId) {
            climate.applyDataset(initialDatasetId, { skipPersist: true, skipStationRefresh: true });
        }

        var initialPrecip = dom.qs("input[name=\"precip_scaling_mode\"]:checked", formElement);
        if (initialPrecip) {
            climate.handlePrecipScalingModeChange(initialPrecip.value);
        } else {
            climate.handlePrecipScalingModeChange(null);
        }

        if (climate.buildModeRadios && climate.buildModeRadios.length > 0) {
            var initialBuildMode = getRadioValue(climate.buildModeRadios);
            climate.setBuildMode(initialBuildMode, { skipStationMode: true });
        }

        climate.attachStatusStream({ autoConnect: false });
        climate.refreshStationSelection();
        climate.viewStationMonthlies();

        var bootstrapState = {
            reportTriggered: false,
            stationRefreshed: false
        };

        climate.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "climate")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_climate_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_climate_rq")) {
                    var value = jobIds.build_climate_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof climate.set_rq_job_id === "function") {
                if (jobId) {
                    climate.poll_completion_event = "CLIMATE_BUILD_TASK_COMPLETED";
                }
                climate.set_rq_job_id(climate, jobId);
            }

            var precipMode = controllerContext.precipScalingMode;
            if (precipMode === undefined && ctx.data && ctx.data.climate) {
                precipMode = ctx.data.climate.precipScalingMode;
            }
            if (precipMode === undefined && climate.form) {
                var selected = climate.form.querySelector('input[name="precip_scaling_mode"]:checked');
                if (selected) {
                    precipMode = selected.value;
                }
            }
            if (typeof climate.handlePrecipScalingModeChange === "function") {
                climate.handlePrecipScalingModeChange(precipMode);
            }

            var climateData = (ctx.data && ctx.data.climate) || {};
            var hasStation = controllerContext.hasStation;
            if (hasStation === undefined) {
                hasStation = climateData.hasStation;
            }

            if (hasStation) {
                if (typeof climate.refreshStationSelection === "function") {
                    climate.refreshStationSelection();
                }
                if (typeof climate.viewStationMonthlies === "function") {
                    climate.viewStationMonthlies();
                }
                bootstrapState.stationRefreshed = true;
            } else if (!bootstrapState.stationRefreshed && climateData.hasStation) {
                if (typeof climate.refreshStationSelection === "function") {
                    climate.refreshStationSelection();
                }
                if (typeof climate.viewStationMonthlies === "function") {
                    climate.viewStationMonthlies();
                }
                bootstrapState.stationRefreshed = true;
            }

            var hasClimate = controllerContext.hasClimate;
            if (hasClimate === undefined) {
                hasClimate = climateData.hasClimate;
            }
            if (hasClimate && !bootstrapState.reportTriggered && typeof climate.report === "function") {
                climate.report();
                bootstrapState.reportTriggered = true;
            }

            return climate;
        };

        return climate;
    }

    function initialise() {
        if (!instance) {
            instance = createInstance();
        }
        return instance;
    }

    if (typeof document !== "undefined") {
        var bootstrapClimate = function () {
            if (!document.getElementById("climate_form")) {
                return;
            }
            try {
                Climate.getInstance();
            } catch (err) {
                console.error("[Climate] Initialisation failed:", err);
            }
        };
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", bootstrapClimate, { once: true });
        } else {
            setTimeout(bootstrapClimate, 0);
        }
    }

    return {
        getInstance: function () {
            return initialise();
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.Climate = Climate;
}

/* ----------------------------------------------------------------------------
 * DebrisFlow
 * Doc: controllers_js/README.md — Debris Flow Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var DebrisFlow = (function () {
    var instance;

    var EVENT_NAMES = [
        "debris:run:started",
        "debris:run:completed",
        "debris:run:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("DebrisFlow controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("DebrisFlow controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("DebrisFlow controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("DebrisFlow controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        var formElement = dom.qs("#debris_flow_form");
        if (!formElement) {
            var placeholder = controlBase();
            placeholder.form = null;
            placeholder.events = emitter;
            placeholder.command_btn_id = "btn_run_debris_flow";
            placeholder.run = function () {
                return null;
            };
            placeholder.report = function () {};
            placeholder.bootstrap = function () {
                return placeholder;
            };
            return placeholder;
        }

        var debris = controlBase();

        var infoElement = dom.qs("#debris_flow_form #info");
        var statusElement = dom.qs("#debris_flow_form #status");
        var stacktraceElement = dom.qs("#debris_flow_form #stacktrace");
        var rqJobElement = dom.qs("#debris_flow_form #rq_job");
        var hintElement = dom.qs("#hint_run_debris_flow");
        var statusPanelElement = dom.qs("#debris_flow_status_panel");
        var stacktracePanelElement = dom.qs("#debris_flow_stacktrace_panel");
        var spinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        debris.form = formElement;
        debris.info = infoAdapter;
        debris.status = statusAdapter;
        debris.stacktrace = stacktraceAdapter;
        debris.rq_job = rqJobAdapter;
        debris.hint = hintAdapter;
        debris.command_btn_id = "btn_run_debris_flow";
        debris.statusPanelEl = statusPanelElement || null;
        debris.stacktracePanelEl = stacktracePanelElement || null;
        debris.statusSpinnerEl = spinnerElement || null;
        debris._completion_seen = false;
        debris.attach_status_stream(debris, {
            element: statusPanelElement,
            form: formElement,
            channel: "debris_flow",
            runId: window.runid || window.runId || null,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: spinnerElement
        });
        debris.events = emitter;

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
            debris.hideStacktrace();
        }

        function resetCompletionSeen() {
            debris._completion_seen = false;
        }

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            debris.pushResponseStacktrace(debris, payload);
            emitter.emit("debris:run:error", { error: payload });
            debris.triggerEvent("job:error", { task: "debris:run", error: payload });
            debris.disconnect_status_stream(debris);
        }

        debris.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        debris.run = function () {
            var taskMsg = "Running debris flow model fit";
            resetStatus(taskMsg);
            resetCompletionSeen();

            var payload = forms.serializeForm(formElement, { format: "object" }) || {};
            var cleanPayload = {};
            Object.keys(payload).forEach(function (key) {
                var value = payload[key];
                if (value === null || value === undefined) {
                    return;
                }
                if (typeof value === "string" && value.trim() === "") {
                    return;
                }
                cleanPayload[key] = value;
            });

            debris.triggerEvent("job:started", { task: "debris:run" });
            emitter.emit("debris:run:started", { jobId: null, task: "debris:run" });

            debris.connect_status_stream(debris);

            http.postJson(url_for_run("rq/api/run_debris_flow"), cleanPayload, { form: formElement }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true || payload.success === true) {
                    statusAdapter.html("run_debris_flow_rq job submitted: " + payload.job_id);
                    debris.poll_completion_event = "DEBRIS_FLOW_RUN_TASK_COMPLETED";
                    debris.set_rq_job_id(debris, payload.job_id);
                    emitter.emit("debris:run:started", {
                        jobId: payload.job_id,
                        task: "debris:run",
                        status: "queued"
                    });
                } else {
                    debris.pushResponseStacktrace(debris, payload);
                    emitter.emit("debris:run:error", { error: payload });
                    debris.triggerEvent("job:error", { task: "debris:run", error: payload });
                }
            }).catch(function (error) {
                handleError(error);
            });
        };

        debris.report = function () {
            infoAdapter.html("<a href='" + url_for_run("report/debris_flow/") + "' target='_blank'>View Debris Flow Model Results</a>");
            emitter.emit("debris:run:completed", {
                jobId: debris.rq_job_id || null,
                task: "debris:run"
            });
            if (!debris._job_completion_dispatched) {
                debris._job_completion_dispatched = true;
                debris.triggerEvent("job:completed", {
                    task: "debris:run",
                    jobId: debris.rq_job_id || null
                });
            }
        };

        function handleCompletion() {
            if (debris._completion_seen) {
                return;
            }
            debris._completion_seen = true;
            debris.disconnect_status_stream(debris);
            debris.report();
        }

        var baseTriggerEvent = debris.triggerEvent.bind(debris);
        debris.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "DEBRIS_FLOW_RUN_TASK_COMPLETED") {
                handleCompletion();
            }
            return baseTriggerEvent(eventName, payload);
        };

        formElement.addEventListener("DEBRIS_FLOW_RUN_TASK_COMPLETED", function () {
            handleCompletion();
        });

        dom.delegate(formElement, "click", "[data-debris-action='run']", function (event) {
            event.preventDefault();
            debris.run();
        });

        debris.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_debris_flow_rq")
                : null;
            if (!jobId && ctx.controllers && ctx.controllers.debrisFlow && ctx.controllers.debrisFlow.jobId) {
                jobId = ctx.controllers.debrisFlow.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_debris_flow_rq")) {
                    var value = jobIds.run_debris_flow_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }
            if (typeof debris.set_rq_job_id === "function") {
                if (jobId) {
                    debris.poll_completion_event = "DEBRIS_FLOW_RUN_TASK_COMPLETED";
                    resetCompletionSeen();
                }
                debris.set_rq_job_id(debris, jobId);
            }
            if (!jobId) {
                var hasResultsAttr = formElement.getAttribute("data-debris-has-results");
                if (hasResultsAttr === "true" && typeof debris.report === "function") {
                    debris.report();
                }
            }
            return debris;
        };

        return debris;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.DebrisFlow = DebrisFlow;
}

(function (global) {
    "use strict";

    var doc = global.document;
    var SELECTORS = [".wc-run-header__menu", ".wc-nav__menu"];
    var bound = false;

    function closeMenus(target) {
        if (!doc || !doc.querySelectorAll) {
            return;
        }
        SELECTORS.forEach(function (selector) {
            var openMenus = doc.querySelectorAll(selector + "[open]");
            Array.prototype.forEach.call(openMenus, function (menu) {
                if (!menu || (target && menu.contains(target))) {
                    return;
                }
                menu.removeAttribute("open");
            });
        });
    }

    function bind() {
        if (bound || !doc || !doc.addEventListener) {
            return;
        }
        bound = true;

        doc.addEventListener("click", function handleClick(event) {
            closeMenus(event && event.target);
        });

        doc.addEventListener("keyup", function handleKeyup(event) {
            var key = event && (event.key || event.keyCode);
            if (key === "Escape" || key === "Esc" || key === 27) {
                closeMenus();
            }
        });
    }

    bind();

    var api = global.WCDetailsMenu || {};
    api.closeAll = function () {
        closeMenus();
    };
    global.WCDetailsMenu = api;
}(typeof window !== "undefined" ? window : this));

/* ----------------------------------------------------------------------------
 * Disturbed Controller - Soil Burn Severity (SBS) Management
 * 
 * Handles two modes: Upload (mode 0) and Uniform (mode 1)
 * Communicates with Baer controller for dual-control scenarios
 * 
 * Documentation:
 * - Architecture: controllers_js/README.md — Disturbed Controller Reference
 * - Behavior: docs/ui-docs/control-ui-styling/sbs_controls_behavior.md
 * ----------------------------------------------------------------------------
 */
var Disturbed = (function () {
    var instance;

    var MODE_PANELS = {
        0: "#sbs_mode0_controls",
        1: "#sbs_mode1_controls"
    };

    var UNIFORM_HINT_IDS = {
        1: "#hint_low_sbs",
        2: "#hint_moderate_sbs",
        3: "#hint_high_sbs"
    };

    var UNIFORM_LABELS = {
        1: "Uniform Low SBS",
        2: "Uniform Moderate SBS",
        3: "Uniform High SBS"
    };

    var EVENT_NAMES = [
        "disturbed:mode:changed",
        "disturbed:sbs:state",
        "disturbed:lookup:reset",
        "disturbed:lookup:extended",
        "disturbed:lookup:error",
        "disturbed:upload:started",
        "disturbed:upload:completed",
        "disturbed:upload:error",
        "disturbed:remove:started",
        "disturbed:remove:completed",
        "disturbed:remove:error",
        "disturbed:uniform:started",
        "disturbed:uniform:completed",
        "disturbed:uniform:error",
        "disturbed:firedate:updated",
        "disturbed:firedate:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Disturbed controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Disturbed controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Disturbed controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Disturbed controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function parseInteger(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function setAdapterText(adapter, text) {
        if (!adapter || typeof adapter.text !== "function") {
            return;
        }
        adapter.text(text === undefined || text === null ? "" : String(text));
    }

    function dispatchDomEvent(name, detail) {
        if (typeof CustomEvent !== "function") {
            return;
        }
        try {
            document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
        } catch (err) {
            console.warn("[Disturbed] Failed to dispatch " + name, err);
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var disturbed = controlBase();
        var disturbedEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                disturbedEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                disturbedEvents = emitterBase;
            }
        }

        if (disturbedEvents) {
            disturbed.events = disturbedEvents;
        }

        var formElement = dom.qs("#sbs_upload_form") || null;
        var infoElement = formElement ? dom.qs("#info", formElement) : null;
        var statusElement = formElement ? dom.qs("#status", formElement) : null;
        var stacktraceElement = formElement ? dom.qs("#stacktrace", formElement) : null;
        var rqJobElement = formElement ? dom.qs("#rq_job", formElement) : null;
        var spinnerElement = formElement ? dom.qs("#braille", formElement) : null;

        var uploadHintElement = formElement ? dom.qs("#hint_upload_sbs", formElement) : null;
        var removeHintElement = formElement ? dom.qs("#hint_remove_sbs", formElement) : null;

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var uploadHintAdapter = createLegacyAdapter(uploadHintElement);
        var removeHintAdapter = createLegacyAdapter(removeHintElement);

        var uniformHintAdapters = {};
        Object.keys(UNIFORM_HINT_IDS).forEach(function (key) {
            var selector = UNIFORM_HINT_IDS[key];
            var node = formElement ? dom.qs(selector, formElement) : null;
            uniformHintAdapters[key] = createLegacyAdapter(node);
        });

        disturbed.form = formElement;
        disturbed.info = infoAdapter;
        disturbed.status = statusAdapter;
        disturbed.stacktrace = stacktraceAdapter;
        disturbed.rq_job = rqJobAdapter;
        disturbed.infoElement = infoElement;
        disturbed.statusSpinnerEl = spinnerElement;

        var commandButtons = [];
        [
            "#btn_upload_sbs",
            "#btn_remove_sbs",
            "#btn_remove_sbs_uniform",
            "#btn_uniform_low_sbs",
            "#btn_uniform_moderate_sbs",
            "#btn_uniform_high_sbs",
            "#btn_set_firedate"
        ].forEach(function (selector) {
            var button = formElement ? dom.qs(selector, formElement) : dom.qs(selector);
            if (button) {
                commandButtons.push(button);
            }
        });

        if (commandButtons.length > 0) {
            disturbed.command_btn_id = commandButtons;
        }

        disturbed.attach_status_stream(disturbed, {
            form: formElement,
            channel: "disturbed",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        var modePanels = {};
        Object.keys(MODE_PANELS).forEach(function (key) {
            modePanels[key] = formElement ? dom.qs(MODE_PANELS[key], formElement) : null;
        });

        var initialMode = 0;
        var initialUniform = null;
        if (formElement) {
            if (formElement.dataset) {
                if (formElement.dataset.initialMode !== undefined) {
                    initialMode = parseInteger(formElement.dataset.initialMode, 0);
                }
                if (formElement.dataset.initialUniform !== undefined) {
                    var uniformValue = formElement.dataset.initialUniform;
                    if (uniformValue === "" || uniformValue === null || uniformValue === undefined) {
                        initialUniform = null;
                    } else {
                        initialUniform = parseInteger(uniformValue, null);
                    }
                }
            }
            if (!formElement.dataset || formElement.dataset.initialMode === undefined) {
                var checked = formElement.querySelector("input[name='sbs_mode']:checked");
                initialMode = parseInteger(checked ? checked.value : initialMode, initialMode);
            }
        }

        var state = {
            mode: initialMode,
            hasSbs: undefined,
            hasSbsRequest: null,
            uniformSeverity: initialUniform
        };

        function emit(name, payload) {
            if (!disturbedEvents || typeof disturbedEvents.emit !== "function") {
                return;
            }
            disturbedEvents.emit(name, payload || {});
        }

        function startTask(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
        }

        function completeTask(taskMsg) {
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "... Success");
            }
        }

        function failTask(taskMsg) {
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "... Failed");
            }
        }

        function setMode(mode, shouldEmit) {
            var normalized = parseInteger(mode, state.mode);
            if (!Object.prototype.hasOwnProperty.call(modePanels, String(normalized))) {
                normalized = 0;
            }
            state.mode = normalized;
            Object.keys(modePanels).forEach(function (key) {
                var panel = modePanels[key];
                if (!panel) {
                    return;
                }
                if (String(key) === String(normalized)) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
            if (formElement) {
                var modeInput = formElement.querySelector("input[name='sbs_mode'][value='" + normalized + "']");
                if (modeInput && !modeInput.checked) {
                    modeInput.checked = true;
                }
            }
            if (shouldEmit) {
                emit("disturbed:mode:changed", { mode: normalized });
            }
        }

        function clearUploadHint() {
            setAdapterText(uploadHintAdapter, "");
        }

        function clearRemoveHint() {
            setAdapterText(removeHintAdapter, "");
        }

        function updateCurrentFilename(filename) {
            if (!filename) {
                return;
            }
            // Find the text display showing current SBS map filename
            var displays = formElement ? formElement.querySelectorAll(".wc-field--display .wc-text-display") : [];
            for (var i = 0; i < displays.length; i++) {
                var display = displays[i];
                var label = display.parentElement ? display.parentElement.querySelector(".wc-field__label") : null;
                if (label && label.textContent && label.textContent.indexOf("Current SBS map") !== -1) {
                    display.innerHTML = "<code>" + filename + "</code>";
                    break;
                }
            }
        }

        function clearUniformHints() {
            Object.keys(uniformHintAdapters).forEach(function (key) {
                setAdapterText(uniformHintAdapters[key], "");
            });
        }

        function setUniformHint(value, text) {
            var key = String(value);
            if (!Object.prototype.hasOwnProperty.call(uniformHintAdapters, key)) {
                return;
            }
            setAdapterText(uniformHintAdapters[key], text);
        }

        function updateUniformSummary(severity) {
            var display = formElement ? formElement.querySelector('[data-uniform-summary]') : null;
            var nextSeverity;
            if (severity === undefined) {
                nextSeverity = state.uniformSeverity;
            } else if (severity === null) {
                nextSeverity = null;
            } else {
                nextSeverity = parseInteger(severity, null);
            }
            state.uniformSeverity = nextSeverity;
            if (!display) {
                return;
            }
            var summaryHtml;
            if (nextSeverity === null || nextSeverity === undefined) {
                summaryHtml = '<span class="wc-text-muted">Not set</span>';
            } else {
                summaryHtml = UNIFORM_LABELS[nextSeverity] || "Uniform " + nextSeverity + " SBS";
            }
            display.innerHTML = summaryHtml;
        }

        function syncModeFromServer(mode, severity, options) {
            var opts = options || {};
            if (mode !== undefined && mode !== null) {
                setMode(mode, opts.emit !== false);
            }
            if (severity !== undefined) {
                updateUniformSummary(severity);
            }
        }

        updateUniformSummary(state.uniformSeverity);

        function updateHasSbs(value, source) {
            var next;
            if (value === undefined || value === null) {
                next = undefined;
            } else {
                next = value === true;
            }
            var previous = state.hasSbs;
            state.hasSbs = next;
            if (previous !== next) {
                emit("disturbed:sbs:state", { hasSbs: next, source: source || null });
                dispatchDomEvent("disturbed:has_sbs_changed", { hasSbs: next, source: source || null });
            }
            return state.hasSbs;
        }

        function refreshHasSbs(reason) {
            if (state.hasSbsRequest) {
                return state.hasSbsRequest;
            }
            var request = http
                .request(url_for_run("api/disturbed/has_sbs/"), {
                    method: "GET",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var body = result.body || {};
                    var hasSbs = body.has_sbs === true;
                    updateHasSbs(hasSbs, reason || "api");
                    return hasSbs;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    emit("disturbed:sbs:state", { error: payload, source: reason || "api" });
                    return false;
                })
                .finally(function () {
                    state.hasSbsRequest = null;
                });
            state.hasSbsRequest = request;
            return request;
        }

        function handleResponseError(taskMsg, payload, errorEvent, taskName) {
            disturbed.pushResponseStacktrace(disturbed, payload);
            failTask(taskMsg);
            emit(errorEvent, { error: payload });
            disturbed.triggerEvent("job:error", { task: taskName, error: payload });
        }

        function resetLandSoilLookup() {
            var taskMsg = "Resetting disturbed lookup";
            startTask(taskMsg);
            emit("disturbed:lookup:reset", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:lookup:reset" });
            return http
                .request(url_for_run("tasks/reset_disturbed"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, "Disturbed lookup reset to defaults.");
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:lookup:reset",
                            response: data
                        });
                        return data;
                    }
                    handleResponseError(taskMsg, data, "disturbed:lookup:error", "disturbed:lookup:reset");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    handleResponseError(taskMsg, payload, "disturbed:lookup:error", "disturbed:lookup:reset");
                    return payload;
                });
        }

        function loadExtendedLandSoilLookup() {
            var taskMsg = "Loading extended disturbed lookup";
            startTask(taskMsg);
            emit("disturbed:lookup:extended", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:lookup:extended" });
            return http
                .request(url_for_run("tasks/load_extended_land_soil_lookup"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, "Extended disturbed lookup loaded.");
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:lookup:extended",
                            response: data
                        });
                        return data;
                    }
                    handleResponseError(taskMsg, data, "disturbed:lookup:error", "disturbed:lookup:extended");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    handleResponseError(taskMsg, payload, "disturbed:lookup:error", "disturbed:lookup:extended");
                    return payload;
                });
        }

        function uploadSbs() {
            if (!formElement) {
                return Promise.resolve(null);
            }
            var taskMsg = "Uploading SBS";
            clearUploadHint();
            startTask(taskMsg);
            emit("disturbed:upload:started", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:upload" });
            var formData = new window.FormData(formElement);
            return http
                .request(url_for_run("tasks/upload_sbs/"), {
                    method: "POST",
                    body: formData,
                    form: formElement
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        setAdapterText(uploadHintAdapter, "SBS raster uploaded successfully.");
                        updateHasSbs(true, "upload");
                        
                        // Update filename display if provided
                        var content = data.Content || {};
                        if (content.disturbed_fn) {
                            updateCurrentFilename(content.disturbed_fn);
                        }

                        syncModeFromServer(0, null);

                        emit("disturbed:upload:completed", { response: data });
                        disturbed.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                        // Sync with baer controller
                        try {
                            var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                            if (baer) {
                                // Trigger event on baer form
                                if (typeof baer.triggerEvent === "function") {
                                    baer.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                                }
                                // Call methods directly since forms are separate
                                setTimeout(function () {
                                    if (typeof baer.show_sbs === "function") {
                                        baer.show_sbs();
                                    }
                                    if (typeof baer.load_modify_class === "function") {
                                        baer.load_modify_class();
                                    }
                                }, 100);
                            }
                        } catch (e) {
                            console.warn("[Disturbed] Failed to sync Baer controller", e);
                        }
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:upload",
                            response: data
                        });
                        refreshHasSbs("upload");
                        return data;
                    }
                    setAdapterText(uploadHintAdapter, data.Error || "Upload failed.");
                    handleResponseError(taskMsg, data, "disturbed:upload:error", "disturbed:upload");
                    refreshHasSbs("upload");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setAdapterText(uploadHintAdapter, payload.Error || "Upload failed.");
                    handleResponseError(taskMsg, payload, "disturbed:upload:error", "disturbed:upload");
                    refreshHasSbs("upload");
                    return payload;
                });
        }

        function removeSbs() {
            var taskMsg = "Removing SBS";
            clearUploadHint();
            clearRemoveHint();
            startTask(taskMsg);
            emit("disturbed:remove:started", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:remove" });
            return http
                .request(url_for_run("tasks/remove_sbs"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        setAdapterText(removeHintAdapter, "SBS raster removed.");
                        updateHasSbs(false, "remove");
                        emit("disturbed:remove:completed", { response: data });
                        disturbed.triggerEvent("SBS_REMOVE_TASK_COMPLETE", data);
                        
                        // Remove map layer via baer controller
                        try {
                            var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                            if (baer) {
                                // Trigger event on baer form
                                if (typeof baer.triggerEvent === "function") {
                                    baer.triggerEvent("SBS_REMOVE_TASK_COMPLETE", data);
                                }
                                // Remove the map layer directly
                                try {
                                    var map = typeof MapController !== "undefined" ? MapController.getInstance() : null;
                                    if (map && baer.baer_map) {
                                        if (typeof map.removeLayer === "function") {
                                            map.removeLayer(baer.baer_map);
                                        }
                                        if (map.ctrls && typeof map.ctrls.removeLayer === "function") {
                                            map.ctrls.removeLayer(baer.baer_map);
                                        }
                                        baer.baer_map = null;
                                    }
                                    // Clear the SBS legend
                                    var legend = document.getElementById("sbs_legend");
                                    if (legend) {
                                        legend.innerHTML = "";
                                    }
                                } catch (mapErr) {
                                    console.warn("[Disturbed] Failed to remove map layer", mapErr);
                                }
                            }
                        } catch (e) {
                            console.warn("[Disturbed] Failed to sync Baer controller", e);
                        }
                        
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:remove",
                            response: data
                        });
                        refreshHasSbs("remove");
                        return data;
                    }
                    setAdapterText(removeHintAdapter, data.Error || "Failed to remove SBS.");
                    handleResponseError(taskMsg, data, "disturbed:remove:error", "disturbed:remove");
                    refreshHasSbs("remove");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setAdapterText(removeHintAdapter, payload.Error || "Failed to remove SBS.");
                    handleResponseError(taskMsg, payload, "disturbed:remove:error", "disturbed:remove");
                    refreshHasSbs("remove");
                    return payload;
                });
        }

        function buildUniformSbs(value) {
            var severity = parseInteger(value, NaN);
            if (Number.isNaN(severity)) {
                return Promise.resolve(null);
            }
            var taskMsg = "Building uniform SBS";
            clearUniformHints();
            startTask(taskMsg);
            emit("disturbed:uniform:started", { severity: severity });
            disturbed.triggerEvent("job:started", { task: "disturbed:uniform", severity: severity });
            return http
                .request(url_for_run("tasks/build_uniform_sbs"), {
                    method: "POST",
                    json: { value: severity },
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        updateHasSbs(true, "uniform");
                        
                        // Update filename display if provided
                        var content = data.Content || {};
                        if (content.disturbed_fn) {
                            updateCurrentFilename(content.disturbed_fn);
                        }

                        syncModeFromServer(1, severity);

                        emit("disturbed:uniform:completed", {
                            response: data,
                            severity: severity
                        });
                        disturbed.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                        // Sync with baer controller
                        try {
                            var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                            if (baer) {
                                // Trigger event on baer form
                                if (typeof baer.triggerEvent === "function") {
                                    baer.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                                }
                                // Call methods directly since forms are separate
                                setTimeout(function () {
                                    if (typeof baer.show_sbs === "function") {
                                        baer.show_sbs();
                                    }
                                    if (typeof baer.load_modify_class === "function") {
                                        baer.load_modify_class();
                                    }
                                }, 100);
                            }
                        } catch (e) {
                            console.warn("[Disturbed] Failed to sync Baer controller", e);
                        }
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:uniform",
                            severity: severity,
                            response: data
                        });
                        refreshHasSbs("uniform");
                        return data;
                    }
                    setUniformHint(severity, data.Error || "Failed to generate uniform SBS.");
                    handleResponseError(taskMsg, data, "disturbed:uniform:error", "disturbed:uniform");
                    refreshHasSbs("uniform");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setUniformHint(severity, payload.Error || "Failed to generate uniform SBS.");
                    handleResponseError(taskMsg, payload, "disturbed:uniform:error", "disturbed:uniform");
                    refreshHasSbs("uniform");
                    return payload;
                });
        }

        function setFireDate(value) {
            var taskMsg = "Setting fire date";
            startTask(taskMsg);
            emit("disturbed:firedate:updated", { pending: true });
            disturbed.triggerEvent("job:started", { task: "disturbed:firedate" });

            var fireDate = value;
            if ((fireDate === undefined || fireDate === null) && formElement) {
                var formValues = forms.serializeForm(formElement, { format: "object" }) || {};
                if (Object.prototype.hasOwnProperty.call(formValues, "firedate")) {
                    fireDate = formValues.firedate;
                }
            }

            return http
                .request(url_for_run("tasks/set_firedate/"), {
                    method: "POST",
                    json: { fire_date: fireDate || null },
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, fireDate ? "Fire date set to " + fireDate + "." : "Fire date cleared.");
                        emit("disturbed:firedate:updated", { fireDate: fireDate || null });
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:firedate",
                            response: data
                        });
                        return data;
                    }
                    handleResponseError(taskMsg, data, "disturbed:firedate:error", "disturbed:firedate");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    handleResponseError(taskMsg, payload, "disturbed:firedate:error", "disturbed:firedate");
                    return payload;
                });
        }

        function bindHandlers() {
            if (formElement) {
                if (formElement.dataset && formElement.dataset.disturbedHandlersBound === "true") {
                    return;
                }
                if (formElement.dataset) {
                    formElement.dataset.disturbedHandlersBound = "true";
                }

                dom.delegate(formElement, "change", "input[name='sbs_mode']", function (event, target) {
                    var nextMode = target ? target.value : state.mode;
                    setMode(nextMode, true);
                });

                dom.delegate(formElement, "click", "[data-sbs-action]", function (event, target) {
                    event.preventDefault();
                    var action = target.getAttribute("data-sbs-action");
                    if (!action) {
                        return;
                    }
                    if (action === "upload") {
                        uploadSbs();
                        return;
                    }
                    if (action === "remove") {
                        removeSbs();
                        return;
                    }
                    if (action === "set-firedate") {
                        var selector = target.getAttribute("data-sbs-target") || "#firedate";
                        var input = selector ? dom.qs(selector) : null;
                        var value = input ? input.value : null;
                        setFireDate(value);
                    }
                });

                dom.delegate(formElement, "change", "input[type='file'][data-auto-upload]", function (event, target) {
                    if (target.files && target.files.length > 0) {
                        uploadSbs();
                    }
                });

                dom.delegate(formElement, "click", "[data-sbs-uniform]", function (event, target) {
                    event.preventDefault();
                    var uniformValue = target.getAttribute("data-sbs-uniform");
                    buildUniformSbs(uniformValue);
                });
            }

            dom.delegate(document, "click", "[data-disturbed-action]", function (event, target) {
                event.preventDefault();
                var action = target.getAttribute("data-disturbed-action");
                if (action === "reset-lookup") {
                    resetLandSoilLookup();
                    return;
                }
                if (action === "load-extended-lookup") {
                    loadExtendedLandSoilLookup();
                }
            });
        }

        setMode(state.mode, false);
        bindHandlers();

        disturbed.reset_land_soil_lookup = resetLandSoilLookup;
        disturbed.load_extended_land_soil_lookup = loadExtendedLandSoilLookup;
        disturbed.upload_sbs = uploadSbs;
        disturbed.remove_sbs = removeSbs;
        disturbed.build_uniform_sbs = buildUniformSbs;
        disturbed.set_firedate = setFireDate;
        disturbed.refresh_has_sbs = refreshHasSbs;

        disturbed.set_has_sbs_cached = function (value) {
            return updateHasSbs(value, "manual");
        };

        disturbed.get_has_sbs_cached = function () {
            return state.hasSbs;
        };

        disturbed.clear_has_sbs_cache = function () {
            return updateHasSbs(undefined, "clear");
        };

        disturbed.has_sbs = function (options) {
            var opts = options || {};
            if (opts.forceRefresh || state.hasSbs === undefined) {
                refreshHasSbs(opts.forceRefresh ? "force" : "lazy");
            }
            return state.hasSbs === true;
        };

        disturbed.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var flags = ctx.flags || {};
            var controllerContext = ctx.controllers && ctx.controllers.disturbed ? ctx.controllers.disturbed : {};
            if (flags.initialHasSbs !== undefined && typeof disturbed.set_has_sbs_cached === "function") {
                disturbed.set_has_sbs_cached(Boolean(flags.initialHasSbs));
            }

            if (controllerContext.mode !== undefined || controllerContext.uniformSeverity !== undefined) {
                syncModeFromServer(controllerContext.mode, controllerContext.uniformSeverity, { emit: false });
            }
            
            // Always bootstrap the Baer controller so task events are wired even before SBS exists.
            try {
                var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                if (baer && typeof baer.bootstrap === "function") {
                    baer.bootstrap(context);
                }
            } catch (e) {
                console.warn("[Disturbed] Failed to bootstrap Baer controller", e);
            }
            
            return disturbed;
        };

        return disturbed;
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

if (typeof window !== "undefined") {
    window.Disturbed = Disturbed;
} else if (typeof globalThis !== "undefined") {
    globalThis.Disturbed = Disturbed;
}

/* ----------------------------------------------------------------------------
 * DSS Export
 * Doc: controllers_js/README.md — DSS Export Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var DssExport = (function () {
    "use strict";

    var instance;

    var FORM_ID = "dss_export_form";
    var DSS_CHANNEL = "dss_export";
    var EXPORT_TASK = "dss:export";
    var EXPORT_MESSAGE = "Submitting DSS export request";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        hint: "#hint_export_dss",
        mode1: "#dss_export_mode1_controls",
        mode2: "#dss_export_mode2_controls"
    };

    var ACTIONS = {
        modeToggle: '[data-action="dss-export-mode"]',
        runExport: '[data-action="dss-export-run"]'
    };

    var NAV_LINK_SELECTORS = [
        'a[href="#partitioned-dss-export-for-hec"]',
        'a[href="#dss-export"]'
    ];

    var EVENT_NAMES = [
        "dss:mode:changed",
        "dss:export:started",
        "dss:export:completed",
        "dss:export:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("DssExport controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("DssExport controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function") {
            throw new Error("DssExport controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("DssExport controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
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

    function parseMode(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback === undefined ? null : fallback;
        }
        var parsed = parseInt(String(value), 10);
        if (parsed === 1 || parsed === 2) {
            return parsed;
        }
        return fallback === undefined ? null : fallback;
    }

    function parseChannelIds(value) {
        if (value === undefined || value === null) {
            return [];
        }

        var tokens = [];
        if (Array.isArray(value)) {
            tokens = value.slice();
        } else if (typeof value === "string") {
            tokens = value.split(/[,;\s]+/);
        } else {
            tokens = [value];
        }

        var seen = new Set();
        var ids = [];
        tokens.forEach(function (token) {
            if (token === undefined || token === null || token === "") {
                return;
            }
            var parsed = parseInt(String(token).trim(), 10);
            if (!Number.isNaN(parsed) && parsed > 0 && !seen.has(parsed)) {
                seen.add(parsed);
                ids.push(parsed);
            }
        });
        return ids;
    }

    function normalizeDateInput(value) {
        if (value === undefined || value === null) {
            return null;
        }
        var candidate = value;
        if (Array.isArray(candidate)) {
            candidate = candidate.find(function (entry) {
                return entry !== undefined && entry !== null && entry !== "";
            });
        }
        if (candidate === undefined || candidate === null) {
            return null;
        }
        if (typeof candidate === "string") {
            var trimmed = candidate.trim();
            return trimmed === "" ? null : trimmed;
        }
        return String(candidate);
    }

    function collectExcludeOrders(payload) {
        var orders = [];
        if (!payload) {
            return orders;
        }

        for (var i = 1; i <= 5; i += 1) {
            var key = "dss_export_exclude_order_" + i;
            var raw = payload[key];
            var selected = false;

            if (Array.isArray(raw)) {
                selected = raw.some(function (value) {
                    return Boolean(value);
                });
            } else if (typeof raw === "string") {
                var lowered = raw.toLowerCase();
                selected = lowered === "true" || lowered === "on" || lowered === "1";
            } else {
                selected = Boolean(raw);
            }

            if (selected) {
                orders.push(i);
            }
        }

        if (orders.length === 0 && payload.dss_export_exclude_orders !== undefined) {
            var direct = payload.dss_export_exclude_orders;
            var values = Array.isArray(direct) ? direct : [direct];
            values.forEach(function (value) {
                var parsed = parseInt(String(value), 10);
                if (!Number.isNaN(parsed) && parsed >= 1 && parsed <= 5 && orders.indexOf(parsed) === -1) {
                    orders.push(parsed);
                }
            });
        }

        return orders;
    }

    function toggleNavEntries(dom, shouldShow) {
        NAV_LINK_SELECTORS.forEach(function (selector) {
            var links = [];
            try {
                links = dom.qsa(selector);
            } catch (err) {
                // ignore selector failures
            }
            if (!links || links.length === 0) {
                return;
            }
            links.forEach(function (link) {
                if (!link) {
                    return;
                }
                var target = link.parentElement || link;
                if (!target) {
                    return;
                }
                if (shouldShow) {
                    dom.show(target);
                } else {
                    dom.hide(target);
                }
            });
        });
    }

    function buildDownloadUrl(path) {
        if (typeof url_for_run === "function") {
            return url_for_run(path);
        }
        var prefix = typeof window.site_prefix === "string" ? window.site_prefix : "";
        var normalizedPrefix = prefix.replace(/\/+$/, "");
        var normalizedPath = (path || "").replace(/^\/+/, "");
        if (!normalizedPrefix) {
            return normalizedPath || "/";
        }
        if (!normalizedPath) {
            return normalizedPrefix;
        }
        return normalizedPrefix + "/" + normalizedPath;
    }

    function applyMode(controller, mode, options) {
        if (!controller) {
            return null;
        }
        var fallback = options && options.fallback !== undefined ? options.fallback : controller.state.mode || 1;
        var parsed = parseMode(mode, null);
        if (parsed === null) {
            parsed = parseMode(fallback, 1);
        }
        if (parsed !== 1 && parsed !== 2) {
            throw new Error("ValueError: unknown mode");
        }

        controller.state.mode = parsed;

        var panel1 = controller.modePanels ? controller.modePanels[1] : null;
        var panel2 = controller.modePanels ? controller.modePanels[2] : null;

        if (parsed === 1) {
            if (panel1 && typeof panel1.show === "function") {
                panel1.show();
            }
            if (panel2 && typeof panel2.hide === "function") {
                panel2.hide();
            }
        } else {
            if (panel1 && typeof panel1.hide === "function") {
                panel1.hide();
            }
            if (panel2 && typeof panel2.show === "function") {
                panel2.show();
            }
        }

        if (controller.form && (options ? options.updateRadios !== false : true)) {
            var radios = controller.form.querySelectorAll("input[name='dss_export_mode']");
            radios.forEach(function (radio) {
                if (!radio) {
                    return;
                }
                radio.checked = String(radio.value) === String(parsed);
            });
        }

        if (!options || options.emit !== false) {
            var detail = { mode: parsed };
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("dss:mode:changed", detail);
            }
            controller.triggerEvent("dss:mode:changed", detail);
        }

        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = null;

        if (eventsApi && typeof eventsApi.createEmitter === "function") {
            var baseEmitter = eventsApi.createEmitter();
            emitter = typeof eventsApi.useEventMap === "function"
                ? eventsApi.useEventMap(EVENT_NAMES, baseEmitter)
                : baseEmitter;
        }

        var formElement = null;
        try {
            formElement = dom.qs(SELECTORS.form);
        } catch (err) {
            console.warn("DssExport controller could not locate form:", err);
        }

        var containerElement = null;
        if (formElement && typeof formElement.closest === "function") {
            containerElement = formElement.closest(".controller-section");
        }
        if (!containerElement) {
            containerElement = formElement || null;
        }

        var infoElement = formElement ? dom.qs(SELECTORS.info, formElement) : null;
        var statusElement = formElement ? dom.qs(SELECTORS.status, formElement) : null;
        var stacktraceElement = formElement ? dom.qs(SELECTORS.stacktrace, formElement) : null;
        var rqJobElement = formElement ? dom.qs(SELECTORS.rqJob, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var mode1Element = formElement ? dom.qs(SELECTORS.mode1, formElement) : null;
        var mode2Element = formElement ? dom.qs(SELECTORS.mode2, formElement) : null;

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: formElement,
            container: containerElement,
            info: createLegacyAdapter(infoElement),
            status: createLegacyAdapter(statusElement),
            stacktrace: createLegacyAdapter(stacktraceElement),
            rq_job: createLegacyAdapter(rqJobElement),
            hint: createLegacyAdapter(hintElement),
            modePanels: {
                1: createLegacyAdapter(mode1Element),
                2: createLegacyAdapter(mode2Element)
            },
            command_btn_id: "btn_export_dss",
            state: {
                mode: 1
            },
            _delegates: []
        });

        controller.statusPanelEl = formElement ? dom.qs("#dss_export_status_panel") : null;
        controller.stacktracePanelEl = formElement ? dom.qs("#dss_export_stacktrace_panel") : null;
        controller.statusSpinnerEl = controller.statusPanelEl ? controller.statusPanelEl.querySelector("#braille") : null;
        controller._completion_seen = false;

        controller.attach_status_stream(controller, {
            element: controller.statusPanelEl,
            channel: DSS_CHANNEL,
            stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
            spinner: controller.statusSpinnerEl
        });

        controller.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (controller.statusStream && typeof controller.statusStream.append === "function") {
                controller.statusStream.append(message, meta || null);
                return;
            }
            if (controller.status && typeof controller.status.html === "function") {
                controller.status.html(message);
                return;
            }
            if (statusElement) {
                statusElement.innerHTML = message;
            }
        };

        controller.hideStacktrace = function () {
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function resetCompletionSeen() {
            controller._completion_seen = false;
        }

        function rebindDomReferences() {
            if (!controller.form) {
                return;
            }

            formElement = controller.form;

            var nextInfoElement = dom.qs(SELECTORS.info, formElement);
            if (nextInfoElement !== infoElement) {
                infoElement = nextInfoElement;
                controller.info = createLegacyAdapter(infoElement);
            }

            var nextStatusElement = dom.qs(SELECTORS.status, formElement);
            if (nextStatusElement !== statusElement) {
                statusElement = nextStatusElement;
                controller.status = createLegacyAdapter(statusElement);
            }

            var nextStacktraceElement = dom.qs(SELECTORS.stacktrace, formElement);
            if (nextStacktraceElement !== stacktraceElement) {
                stacktraceElement = nextStacktraceElement;
                controller.stacktrace = createLegacyAdapter(stacktraceElement);
            }

            var nextRqJobElement = dom.qs(SELECTORS.rqJob, formElement);
            if (nextRqJobElement !== rqJobElement) {
                rqJobElement = nextRqJobElement;
                controller.rq_job = createLegacyAdapter(rqJobElement);
            }

            var nextHintElement = dom.qs(SELECTORS.hint, formElement);
            if (nextHintElement !== hintElement) {
                hintElement = nextHintElement;
                controller.hint = createLegacyAdapter(hintElement);
            }

            var nextStatusPanel = dom.qs("#dss_export_status_panel");
            var nextStacktracePanel = dom.qs("#dss_export_stacktrace_panel");
            var nextSpinnerElement = nextStatusPanel ? nextStatusPanel.querySelector("#braille") : null;
            var shouldReattachStream = false;

            if (nextStatusPanel !== controller.statusPanelEl) {
                controller.statusPanelEl = nextStatusPanel;
                shouldReattachStream = true;
            }
            if (nextStacktracePanel !== controller.stacktracePanelEl) {
                controller.stacktracePanelEl = nextStacktracePanel;
                shouldReattachStream = true;
            }
            if (nextSpinnerElement !== controller.statusSpinnerEl) {
                controller.statusSpinnerEl = nextSpinnerElement;
                shouldReattachStream = true;
            }

            if ((shouldReattachStream || (!controller.statusStream && controller.statusPanelEl)) && typeof controller.attach_status_stream === "function") {
                controller.detach_status_stream(controller);
                controller.attach_status_stream(controller, {
                    element: controller.statusPanelEl,
                    channel: DSS_CHANNEL,
                    stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
                    spinner: controller.statusSpinnerEl
                });
            }
        }

        controller.setMode = function (mode) {
            return applyMode(controller, mode, { emit: true, updateRadios: true });
        };

        controller.buildRequestPayload = function () {
            if (!controller.form) {
                return {};
            }
            var payload = forms.serializeForm(controller.form, { format: "json" }) || {};
            var currentMode = parseMode(payload.dss_export_mode, controller.state.mode || 1);
            var channelIds = parseChannelIds(payload.dss_export_channel_ids);
            var excludeOrders = collectExcludeOrders(payload);
            var startDate = normalizeDateInput(payload.dss_start_date);
            var endDate = normalizeDateInput(payload.dss_end_date);

            return {
                dss_export_mode: currentMode,
                dss_export_channel_ids: channelIds,
                dss_export_exclude_orders: excludeOrders,
                dss_start_date: startDate,
                dss_end_date: endDate
            };
        };

        controller.export = function () {
            if (!controller.form) {
                return;
            }

            if (typeof controller.clear_status_messages === "function") {
                controller.clear_status_messages(controller);
            }
            if (typeof controller.reset_status_spinner === "function") {
                controller.reset_status_spinner(controller);
            }
            controller.info.html("");
            controller.appendStatus(EXPORT_MESSAGE + "…");
            controller.stacktrace.text("");
            controller.hideStacktrace();
            resetCompletionSeen();

            var payload = controller.buildRequestPayload();
            controller.state.mode = payload.dss_export_mode || controller.state.mode || 1;

            controller.triggerEvent("job:started", {
                task: EXPORT_TASK,
                payload: payload
            });
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("dss:export:started", {
                    task: EXPORT_TASK,
                    payload: payload
                });
            }

            controller.connect_status_stream(controller);

            http.postJson(url_for_run("rq/api/post_dss_export_rq"), payload, { form: controller.form }).then(function (response) {
                var body = response && response.body ? response.body : response;
                var normalized = body || {};

                if (normalized.Success === true || normalized.success === true) {
                    var jobId = normalized.job_id || normalized.jobId || null;
                    controller.appendStatus("post_dss_export_rq job submitted: " + jobId);
                    controller.poll_completion_event = "DSS_EXPORT_TASK_COMPLETED";
                    controller.set_rq_job_id(controller, jobId);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("dss:export:started", {
                            task: EXPORT_TASK,
                            payload: payload,
                            jobId: jobId,
                            status: "queued"
                        });
                    }
                    return;
                }

                controller.pushResponseStacktrace(controller, normalized);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("dss:export:error", {
                        task: EXPORT_TASK,
                        error: normalized
                    });
                }
                controller.triggerEvent("job:error", {
                    task: EXPORT_TASK,
                    error: normalized
                });
                controller.disconnect_status_stream(controller);
            }).catch(function (error) {
                var handled = false;
                if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
                    var payload = error && Object.prototype.hasOwnProperty.call(error, "body") ? error.body : null;
                    if (typeof payload === "string" && payload.trim() !== "") {
                        try {
                            payload = JSON.parse(payload);
                        } catch (err) {
                            payload = {
                                Error: error.statusText || "Request failed",
                                StackTrace: [payload]
                            };
                        }
                    }
                    if (!payload && error && error.status) {
                        payload = {
                            Error: error.statusText || "Request failed",
                            StackTrace: [error.message || ("HTTP " + error.status)]
                        };
                    }
                    if (payload) {
                        controller.pushResponseStacktrace(controller, payload);
                        handled = true;
                    }
                }
                if (!handled) {
                    controller.pushErrorStacktrace(controller, error);
                }
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("dss:export:error", {
                        task: EXPORT_TASK,
                        error: error
                    });
                }
                controller.triggerEvent("job:error", {
                    task: EXPORT_TASK,
                    error: error
                });
                controller.disconnect_status_stream(controller);
            });
        };

        controller.report = function () {
            var href = buildDownloadUrl("browse/export/dss.zip");
            controller.info.html("<a class='wc-link wc-link--file' href='" + href + "' target='_blank'>Download DSS Export Results (.zip)</a>");
        };

        controller.handleExportTaskCompleted = function (detail) {
            controller.disconnect_status_stream(controller);
            controller.report();
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("dss:export:completed", {
                    task: EXPORT_TASK,
                    jobId: controller.rq_job_id || null,
                    detail: detail || null
                });
            }
            if (!controller._job_completion_dispatched) {
                controller._job_completion_dispatched = true;
                controller.triggerEvent("job:completed", {
                    task: EXPORT_TASK,
                    jobId: controller.rq_job_id || null,
                    detail: detail || null
                });
            }
        };

        function handleCompletion(detail) {
            if (controller._completion_seen) {
                return;
            }
            controller._completion_seen = true;
            controller.handleExportTaskCompleted(detail);
        }

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "DSS_EXPORT_TASK_COMPLETED") {
                var detail = payload && payload.detail ? payload.detail : payload || null;
                handleCompletion(detail);
            }
            return baseTriggerEvent(eventName, payload);
        };

        controller.show = function () {
            if (controller.container) {
                dom.show(controller.container);
            }
            toggleNavEntries(dom, true);
        };

        controller.hide = function () {
            if (controller.container) {
                dom.hide(controller.container);
            }
            toggleNavEntries(dom, false);
        };

        controller.dispose = function () {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            controller.detach_status_stream(controller);
        };

        if (formElement) {
            controller._delegates.push(dom.delegate(formElement, "change", ACTIONS.modeToggle, function (event, target) {
                event.preventDefault();
                var datasetMode = target && target.getAttribute("data-dss-export-mode");
                var nextMode = parseMode(datasetMode || (target ? target.value : undefined), null);
                try {
                    controller.setMode(nextMode);
                } catch (err) {
                    console.error("[DssExport] Unable to set mode:", err);
                }
            }));

            controller._delegates.push(dom.delegate(formElement, "click", ACTIONS.runExport, function (event) {
                event.preventDefault();
                controller.export();
            }));

            formElement.addEventListener("DSS_EXPORT_TASK_COMPLETED", function (event) {
                handleCompletion(event && event.detail ? event.detail : null);
            });
        }

        var initialModeElement = formElement ? formElement.querySelector("input[name='dss_export_mode']:checked") : null;
        var initialMode = parseMode(initialModeElement ? initialModeElement.value : null, 1);
        controller.state.mode = initialMode;
        try {
            applyMode(controller, initialMode, { emit: false, updateRadios: true, fallback: 1 });
        } catch (err) {
            console.warn("[DssExport] Failed to apply initial mode:", err);
        }

        controller.hideStacktrace();

        var bootstrapState = {
            reportDisplayed: false
        };

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "dssExport")
                : {};

            // DYNAMIC MOD LOADING SUPPORT (Nov 2025)
            // When DSS Export is enabled via Mods checkbox, DOM elements don't exist during createInstance().
            // This bootstrap logic re-queries elements and re-attaches event delegates to support dynamic loading.
            // See docs/dev-notes/dynamic-mod-loading-patterns.md for full context.
            
            // Re-query critical elements if they weren't found during initial creation (dynamic loading)
            var needsReApply = false;
            var needsDelegates = false;
            
            if (!controller.form || !controller.form.isConnected) {
                controller.form = dom.qs(SELECTORS.form);
                needsDelegates = Boolean(controller.form);
            }
            
            if (controller.form) {
                formElement = controller.form;
                if (!controller.container || !controller.container.isConnected) {
                    controller.container = typeof controller.form.closest === "function"
                        ? controller.form.closest(".controller-section") || controller.form
                        : controller.form;
                }
                rebindDomReferences();
            }
            
            var modePanelOneMissing = !controller.modePanels[1] ||
                !controller.modePanels[1].element ||
                (controller.modePanels[1].element && controller.modePanels[1].element.isConnected === false);
            if (modePanelOneMissing && controller.form) {
                var mode1El = dom.qs(SELECTORS.mode1, controller.form);
                if (mode1El) {
                    controller.modePanels[1] = createLegacyAdapter(mode1El);
                    needsReApply = true;
                }
            }
            var modePanelTwoMissing = !controller.modePanels[2] ||
                !controller.modePanels[2].element ||
                (controller.modePanels[2].element && controller.modePanels[2].element.isConnected === false);
            if (modePanelTwoMissing && controller.form) {
                var mode2El = dom.qs(SELECTORS.mode2, controller.form);
                if (mode2El) {
                    controller.modePanels[2] = createLegacyAdapter(mode2El);
                    needsReApply = true;
                }
            }
            
            // Set up event delegates if form was just found (dynamic loading)
            if (needsDelegates && controller.form) {
                controller._delegates.push(dom.delegate(controller.form, "change", ACTIONS.modeToggle, function (event, target) {
                    event.preventDefault();
                    var datasetMode = target && target.getAttribute("data-dss-export-mode");
                    var nextMode = parseMode(datasetMode || (target ? target.value : undefined), null);
                    try {
                        controller.setMode(nextMode);
                    } catch (err) {
                        console.error("[DssExport] Unable to set mode:", err);
                    }
                }));

                controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.runExport, function (event) {
                    event.preventDefault();
                    controller.export();
                }));

                controller.form.addEventListener("DSS_EXPORT_TASK_COMPLETED", function (event) {
                    handleCompletion(event && event.detail ? event.detail : null);
                });
            }
            
            // Re-apply initial mode if we just re-queried the panels
            if (needsReApply && controller.form) {
                var checkedModeEl = controller.form.querySelector("input[name='dss_export_mode']:checked");
                var initialMode = parseMode(checkedModeEl ? checkedModeEl.value : null, controller.state.mode || 1);
                controller.state.mode = initialMode;
                try {
                    applyMode(controller, initialMode, { emit: false, updateRadios: true, fallback: 1 });
                } catch (err) {
                    console.warn("[DssExport] Failed to apply mode during bootstrap:", err);
                }
            }

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "post_dss_export_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "post_dss_export_rq")) {
                    var value = jobIds.post_dss_export_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }
            if (jobId && typeof controller.set_rq_job_id === "function") {
                controller.poll_completion_event = "DSS_EXPORT_TASK_COMPLETED";
                resetCompletionSeen();
                controller.set_rq_job_id(controller, jobId);
            }

            var exportData = (ctx.data && ctx.data.wepp) || {};
            var nextMode = controllerContext.mode;
            if (nextMode === undefined || nextMode === null) {
                nextMode = exportData.dssExportMode !== undefined ? exportData.dssExportMode : exportData.dss_export_mode;
            }
            if (nextMode !== undefined && nextMode !== null) {
                try {
                    controller.setMode(nextMode);
                } catch (err) {
                    console.warn("[DssExport] Failed to apply bootstrap mode:", err);
                }
            }

            var hasZip = controllerContext.hasZip;
            if (hasZip === undefined) {
                hasZip = exportData.hasDssZip !== undefined ? exportData.hasDssZip : exportData.has_dss_zip;
            }
            if (hasZip && !bootstrapState.reportDisplayed && typeof controller.report === "function") {
                controller.report();
                bootstrapState.reportDisplayed = true;
            }

            return controller;
        };

        return controller;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.DssExport = DssExport;
}

/* ----------------------------------------------------------------------------
 * Landuse
 * ----------------------------------------------------------------------------
 */
var Landuse = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Landuse controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Landuse controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Landuse controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Landuse controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function parseInteger(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var landuse = controlBase();
        var landuseEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                landuseEvents = events.useEventMap([
                    "landuse:build:started",
                    "landuse:build:completed",
                    "landuse:report:loaded",
                    "landuse:mode:change",
                    "landuse:db:change"
                ], emitterBase);
            } else {
                landuseEvents = emitterBase;
            }
        }

        if (landuseEvents) {
            landuse.events = landuseEvents;
        }

        var formElement = dom.ensureElement("#landuse_form", "Landuse form not found.");
        var infoElement = dom.qs("#landuse_form #info");
        var statusElement = dom.qs("#landuse_form #status");
        var stacktraceElement = dom.qs("#landuse_form #stacktrace");
        var rqJobElement = dom.qs("#landuse_form #rq_job");
        var hintElement = dom.qs("#hint_build_landuse");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        landuse.form = formElement;
        landuse.info = infoAdapter;
        landuse.status = statusAdapter;
        landuse.stacktrace = stacktraceAdapter;
        landuse.rq_job = rqJobAdapter;
        landuse.command_btn_id = "btn_build_landuse";
        landuse.hint = hintAdapter;
        landuse.infoElement = infoElement;
        landuse.statusPanelEl = dom.qs("#landuse_status_panel");
        landuse.stacktracePanelEl = dom.qs("#landuse_stacktrace_panel");
        landuse.statusStream = null;
        var spinnerElement = landuse.statusPanelEl ? landuse.statusPanelEl.querySelector("#braille") : null;

        landuse.attach_status_stream(landuse, {
            element: landuse.statusPanelEl,
            channel: "landuse",
            stacktrace: landuse.stacktracePanelEl ? { element: landuse.stacktracePanelEl } : null,
            spinner: spinnerElement
        });

        function resetCompletionSeen() {
            landuse._completion_seen = false;
        }

        landuse.poll_completion_event = "LANDUSE_BUILD_TASK_COMPLETED";
        resetCompletionSeen();

        var modePanels = [
            dom.qs("#landuse_mode0_controls"),
            dom.qs("#landuse_mode1_controls"),
            dom.qs("#landuse_mode2_controls"),
            dom.qs("#landuse_mode3_controls"),
            dom.qs("#landuse_mode4_controls")
        ];

        var baseTriggerEvent = landuse.triggerEvent.bind(landuse);
        landuse.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "LANDUSE_BUILD_TASK_COMPLETED") {
                if (landuse._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                landuse._completion_seen = true;
                landuse.disconnect_status_stream(landuse);
                landuse.report();
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("dom_lc");
                } catch (err) {
                    console.warn("[Landuse] Failed to enable Subcatchment color map", err);
                }
                if (landuseEvents && typeof landuseEvents.emit === "function") {
                    landuseEvents.emit("landuse:build:completed", payload || {});
                }
            }

            return baseTriggerEvent(eventName, payload);
        };

        landuse.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function resetStatus(taskMsg) {
            landuse.reset_panel_state(landuse, { taskMessage: taskMsg });
        }

        function handleError(error) {
            landuse.pushResponseStacktrace(landuse, toResponsePayload(http, error));
        }

        function ensureReportDelegates() {
            if (!landuse.infoElement) {
                return;
            }

            if (landuse._reportDelegates) {
                return;
            }

            landuse._reportDelegates = [];

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "click", "[data-landuse-toggle]", function (event) {
                event.preventDefault();
                var toggle = this;
                var targetId = toggle.getAttribute("data-landuse-toggle");
                if (!targetId) {
                    return;
                }
                var panel = document.getElementById(targetId);
                if (!panel) {
                    return;
                }
                if (panel.tagName && panel.tagName.toLowerCase() === "details") {
                    var willOpen = !panel.open;
                    panel.open = willOpen;
                    toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
                    if (typeof panel.closest === "function") {
                        var row = panel.closest("tr");
                        if (row) {
                            if (willOpen) {
                                row.classList.add("is-open");
                            } else {
                                row.classList.remove("is-open");
                            }
                        }
                    }
                    if (willOpen && typeof panel.scrollIntoView === "function") {
                        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    }
                }
            }));

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "change", "[data-landuse-role=\"mapping-select\"]", function () {
                var domId = this.getAttribute("data-landuse-dom");
                var value = this.value;
                if (domId === undefined || domId === null || value === undefined) {
                    return;
                }
                landuse.modify_mapping(String(domId), value);
            }));

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "change", "[data-landuse-role=\"coverage-select\"]", function () {
                var domId = this.getAttribute("data-landuse-dom");
                var cover = this.getAttribute("data-landuse-cover");
                var value = this.value;
                if (domId === undefined || domId === null || cover === undefined || cover === null) {
                    return;
                }
                landuse.modify_coverage(String(domId), String(cover), value);
            }));
        }

        landuse.bindReportEvents = function () {
            ensureReportDelegates();
        };

        function ensureFormDelegates() {
            if (landuse._formDelegates) {
                return;
            }

            landuse._formDelegates = [];

            landuse._formDelegates.push(dom.delegate(formElement, "change", "[data-landuse-role=\"mode\"]", function () {
                var modeAttr = this.getAttribute("data-landuse-mode");
                var nextMode = modeAttr !== null ? modeAttr : this.value;
                landuse.handleModeChange(nextMode);
            }));

            landuse._formDelegates.push(dom.delegate(formElement, "change", "[data-landuse-role=\"single-selection\"]", function () {
                landuse.handleSingleSelectionChange();
            }));

            landuse._formDelegates.push(dom.delegate(formElement, "change", "[data-landuse-role=\"db\"]", function () {
                landuse.setLanduseDb(this.value);
            }));

            landuse._formDelegates.push(dom.delegate(formElement, "click", "[data-landuse-action=\"build\"]", function (event) {
                event.preventDefault();
                landuse.build();
            }));
        }

        landuse.build = function () {
            var taskMsg = "Building landuse";
            resetStatus(taskMsg);
            resetCompletionSeen();

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:build:started", {
                    mode: landuse.mode
                });
            }

            landuse.connect_status_stream(landuse);

            var formData = new FormData(formElement);

            http.request(url_for_run("rq/api/build_landuse"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    landuse.append_status_message(landuse, "build_landuse job submitted: " + response.job_id);
                    landuse.poll_completion_event = "LANDUSE_BUILD_TASK_COMPLETED";
                    landuse.set_rq_job_id(landuse, response.job_id);
                } else if (response) {
                    landuse.pushResponseStacktrace(landuse, response);
                }
            }).catch(handleError);
        };

        landuse.modify_coverage = function (domId, cover, value) {
            var payload = {
                dom: domId,
                cover: cover,
                value: value
            };

            http.postJson(url_for_run("tasks/modify_landuse_coverage/"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === false) {
                        landuse.pushResponseStacktrace(landuse, response);
                    }
                })
                .catch(handleError);
        };

        landuse.modify_mapping = function (domId, newDom) {
            var payload = {
                dom: domId,
                newdom: newDom
            };

            http.postJson(url_for_run("tasks/modify_landuse_mapping/"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === false) {
                        landuse.pushResponseStacktrace(landuse, response);
                        return;
                    }
                    landuse.report();
                })
                .catch(handleError);
        };

        landuse.report = function () {
            http.request(url_for_run("report/landuse/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                landuse.bindReportEvents();
                if (landuseEvents && typeof landuseEvents.emit === "function") {
                    landuseEvents.emit("landuse:report:loaded", { html: html });
                }
                if (window.UnitizerClient && typeof window.UnitizerClient.ready === "function") {
                    window.UnitizerClient.ready().then(function (client) {
                        if (client && typeof client.updateNumericFields === "function" && infoElement) {
                            client.updateNumericFields(infoElement);
                        }
                    }).catch(function (error) {
                        console.warn("[Landuse] Failed to update unitizer fields", error);
                    });
                }
            }).catch(handleError);
        };

        landuse.restore = function (mode, singleSelection) {
            var modeValue = parseInteger(mode, 0);
            var singleValue = singleSelection === undefined || singleSelection === null ? null : String(singleSelection);

            var radio = document.getElementById("landuse_mode" + modeValue);
            if (radio) {
                radio.checked = true;
            }

            var singleSelect = document.getElementById("landuse_single_selection");
            if (singleSelect && singleValue !== null && singleValue !== "") {
                singleSelect.value = singleValue;
            }

            landuse.showHideControls(modeValue);
        };

        landuse.handleModeChange = function (mode) {
            if (mode === undefined) {
                landuse.setMode();
                return;
            }
            landuse.setMode(parseInteger(mode, 0));
        };

        landuse.handleSingleSelectionChange = function () {
            landuse.setMode();
        };

        landuse.setMode = function (mode) {
            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (mode === undefined || mode === null) {
                mode = parseInteger(payload.landuse_mode, 0);
            }

            var singleSelection = payload.landuse_single_selection;
            landuse.mode = mode;

            var taskMsg = "Setting Mode to " + mode + " (" + (singleSelection || "") + ")";
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_landuse_mode/"), {
                mode: mode,
                landuse_single_selection: singleSelection
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    landuse.append_status_message(landuse, taskMsg + "... Success");
                } else if (response) {
                    landuse.pushResponseStacktrace(landuse, response);
                }
            }).catch(handleError);

            landuse.showHideControls(mode);

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:mode:change", {
                    mode: mode,
                    singleSelection: singleSelection !== undefined && singleSelection !== null ? String(singleSelection) : null
                });
            }
        };

        landuse.setLanduseDb = function (db) {
            var value = db;
            if (value === undefined) {
                var select = document.getElementById("landuse_db");
                if (select && select.value !== undefined) {
                    value = select.value;
                } else {
                    var checked = formElement.querySelector("input[name='landuse_db']:checked");
                    value = checked ? checked.value : null;
                }
            }

            if (value === undefined || value === null) {
                return;
            }

            var taskMsg = "Setting Landuse Db to " + value;
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_landuse_db/"), { landuse_db: value }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        landuse.append_status_message(landuse, taskMsg + "... Success");
                    } else if (response) {
                        landuse.pushResponseStacktrace(landuse, response);
                    }
                })
                .catch(handleError);

            if (landuse.mode !== undefined) {
                landuse.showHideControls(landuse.mode);
            }

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:db:change", { db: value });
            }
        };

        landuse.showHideControls = function (mode) {
            var numericMode = parseInteger(mode, -1);

            modePanels.forEach(function (panel, index) {
                if (!panel) {
                    return;
                }
                if (numericMode === index) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });

            if (numericMode < 0 || numericMode > modePanels.length - 1) {
                if (numericMode === -1) {
                    modePanels.forEach(function (panel) {
                        if (panel) {
                            dom.hide(panel);
                        }
                    });
                    return;
                }
                throw new Error("ValueError: unknown mode");
            }
        };

        ensureFormDelegates();
        ensureReportDelegates();

        var bootstrapState = {
            buildTriggered: false
        };

        landuse.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "landuse")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_landuse_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_landuse_rq")) {
                    var value = jobIds.build_landuse_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof landuse.set_rq_job_id === "function") {
                landuse.set_rq_job_id(landuse, jobId);
            }

            var settings = (ctx.data && ctx.data.landuse) || {};
            var restoreMode = controllerContext.mode !== undefined && controllerContext.mode !== null
                ? controllerContext.mode
                : settings.mode;
            var restoreSelection = controllerContext.singleSelection !== undefined && controllerContext.singleSelection !== null
                ? controllerContext.singleSelection
                : settings.singleSelection;

            if (typeof landuse.restore === "function") {
                landuse.restore(restoreMode, restoreSelection);
            }

            var hasLanduse = controllerContext.hasLanduse;
            if (hasLanduse === undefined) {
                hasLanduse = settings.hasLanduse;
            }

            if (hasLanduse && !bootstrapState.buildTriggered && typeof landuse.triggerEvent === "function") {
                landuse.triggerEvent("LANDUSE_BUILD_TASK_COMPLETED");
                bootstrapState.buildTriggered = true;
            }

            return landuse;
        };

        return landuse;
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

if (typeof globalThis !== "undefined") {
    globalThis.Landuse = Landuse;
}

/* ----------------------------------------------------------------------------
 * Observed
 * Doc: controllers_js/README.md — Observed Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Observed = (function () {
    "use strict";

    var instance;

    var FORM_ID = "observed_form";
    var WS_CHANNEL = "observed";
    var TASK_NAME = "observed:model-fit";
    var RUN_MESSAGE = "Running observed model fit";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        textarea: "#observed_text",
        hint: "#hint_run_observed"
    };

    var ACTIONS = {
        run: '[data-action="observed-run"]'
    };

    var EVENT_NAMES = [
        "observed:data:loaded",
        "observed:model:fit",
        "observed:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.hide !== "function" || typeof dom.show !== "function") {
            throw new Error("Observed controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Observed controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.getJson !== "function") {
            throw new Error("Observed controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Observed controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
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

    function normalizeError(http, error) {
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error.detail || error.message || "Request failed";
            var stacktrace = [];
            if (error.body && typeof error.body === "object") {
                if (Array.isArray(error.body.StackTrace)) {
                    stacktrace = error.body.StackTrace;
                } else if (typeof error.body.StackTrace === "string") {
                    stacktrace = [error.body.StackTrace];
                }
                if (error.body.Error) {
                    detail = error.body.Error;
                }
            }
            return {
                Success: false,
                Error: detail,
                StackTrace: stacktrace
            };
        }
        return {
            Success: false,
            Error: (error && error.message) || "Request failed"
        };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = null;

        if (eventsApi && typeof eventsApi.createEmitter === "function") {
            var baseEmitter = eventsApi.createEmitter();
            emitter = typeof eventsApi.useEventMap === "function"
                ? eventsApi.useEventMap(EVENT_NAMES, baseEmitter)
                : baseEmitter;
        }

        var formElement = null;
        try {
            formElement = dom.qs(SELECTORS.form);
        } catch (err) {
            console.warn("[Observed] Unable to locate form element:", err);
        }

        var containerElement = null;
        if (formElement && typeof formElement.closest === "function") {
            containerElement = formElement.closest(".controller-section");
        }
        if (!containerElement) {
            containerElement = formElement || null;
        }

        var infoElement = formElement ? dom.qs(SELECTORS.info, formElement) : null;
        var statusElement = formElement ? dom.qs(SELECTORS.status, formElement) : null;
        var stacktraceElement = formElement ? dom.qs(SELECTORS.stacktrace, formElement) : null;
        var rqJobElement = formElement ? dom.qs(SELECTORS.rqJob, formElement) : null;
        var textAreaElement = formElement ? dom.qs(SELECTORS.textarea, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var statusPanelElement = dom.qs("#observed_status_panel");
        var stacktracePanelElement = dom.qs("#observed_stacktrace_panel");
        var spinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: formElement,
            container: containerElement,
            info: createLegacyAdapter(infoElement),
            status: createLegacyAdapter(statusElement),
            stacktrace: createLegacyAdapter(stacktraceElement),
            rq_job: createLegacyAdapter(rqJobElement),
            hint: createLegacyAdapter(hintElement),
            textarea: textAreaElement,
            statusPanelEl: statusPanelElement,
            stacktracePanelEl: stacktracePanelElement,
            statusSpinnerEl: spinnerElement,
            statusStream: null,
            command_btn_id: "btn_run_observed",
            state: {
                visible: false
            },
            _delegates: []
        });

        controller.attach_status_stream(controller, {
            element: statusPanelElement,
            form: formElement,
            channel: WS_CHANNEL,
            runId: window.runid || window.runId || null,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: spinnerElement
        });

        controller.hideStacktrace = function () {
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        controller.showControl = function () {
            controller.state.visible = true;
            if (controller.container) {
                dom.show(controller.container);
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("observed:data:loaded", { available: true });
            }
        };

        controller.hideControl = function () {
            controller.state.visible = false;
            if (controller.container) {
                dom.hide(controller.container);
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("observed:data:loaded", { available: false });
            }
        };

        controller.onWeppRunCompleted = function () {
            http.getJson(url_for_run("query/climate_has_observed/")).then(function (hasObserved) {
                var available = false;
                if (typeof hasObserved === "boolean") {
                    available = hasObserved;
                } else if (hasObserved && typeof hasObserved === "object" && typeof hasObserved.available === "boolean") {
                    available = hasObserved.available;
                }

                if (available) {
                    controller.showControl();
                } else {
                    controller.hideControl();
                }
            }).catch(function (error) {
                controller.pushErrorStacktrace(controller, error);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("observed:error", {
                        context: "climate_has_observed",
                        error: error
                    });
                }
            });
        };

        controller.report = function () {
            if (!controller.info || typeof controller.info.html !== "function") {
                return;
            }
            var href = url_for_run("report/observed/");
            controller.info.html("<a href='" + href + "' target='_blank'>View Model Fit Results</a>");
        };

        controller.run_model_fit = function () {
            if (!controller.form) {
                return;
            }

            controller.info.html("");
            controller.status.html(RUN_MESSAGE + "…");
            controller.stacktrace.text("");
            controller.hideStacktrace();
            if (controller.hint && typeof controller.hint.text === "function") {
                controller.hint.text("");
            }

            var payload = forms.serializeForm(controller.form, { format: "json" }) || {};
            var text = "";
            if (typeof payload.data === "string" && payload.data) {
                text = payload.data;
            } else if (typeof payload.observed_text === "string") {
                text = payload.observed_text;
            } else if (controller.textarea && typeof controller.textarea.value === "string") {
                text = controller.textarea.value;
            }

            var submission = { data: text };

            controller.triggerEvent("job:started", {
                task: TASK_NAME,
                payload: submission
            });
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("observed:model:fit", {
                    status: "started",
                    task: TASK_NAME,
                    payload: submission
                });
            }

            controller.connect_status_stream(controller);

            http.postJson(url_for_run("tasks/run_model_fit/"), submission, { form: controller.form }).then(function (response) {
                var body = response && response.body !== undefined ? response.body : response;
                var normalized = body || {};

                if (normalized.Success === true || normalized.success === true) {
                    controller.status.html(RUN_MESSAGE + "… done.");
                    controller.report();
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("observed:model:fit", {
                            status: "completed",
                            task: TASK_NAME,
                            payload: submission,
                            response: normalized
                        });
                    }
                    controller.triggerEvent("job:completed", {
                        task: TASK_NAME,
                        payload: submission,
                        response: normalized
                    });
                } else {
                    controller.pushResponseStacktrace(controller, normalized);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("observed:error", {
                            task: TASK_NAME,
                            payload: submission,
                            error: normalized
                        });
                    }
                    controller.triggerEvent("job:error", {
                        task: TASK_NAME,
                        payload: submission,
                        error: normalized
                    });
                }
            }).catch(function (error) {
                var normalizedError = normalizeError(http, error);
                controller.pushResponseStacktrace(controller, normalizedError);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("observed:error", {
                        task: TASK_NAME,
                        payload: submission,
                        error: normalizedError
                    });
                }
                controller.triggerEvent("job:error", {
                    task: TASK_NAME,
                    payload: submission,
                    error: normalizedError
                });
            }).finally(function () {
                controller.disconnect_status_stream(controller);
            });
        };

        controller.runModelFit = controller.run_model_fit;

        controller.dispose = function () {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            controller.disconnect_status_stream(controller);
        };

        if (formElement) {
            controller._delegates.push(dom.delegate(formElement, "click", ACTIONS.run, function (event) {
                event.preventDefault();
                controller.run_model_fit();
            }));
        }

        controller.hideStacktrace();

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var climateData = (ctx.data && ctx.data.climate) || {};
            var observedData = (ctx.data && ctx.data.observed) || {};
            var shouldShow = Boolean(climateData.hasObserved || observedData.hasResults || observedData.resultsAvailable);
            var forceVisible = Boolean(ctx.flags && ctx.flags.playwrightLoadAll);

            if (forceVisible) {
                shouldShow = true;
            }

            if (typeof controller.hideControl === "function") {
                controller.hideControl();
            }
            if (shouldShow && typeof controller.showControl === "function") {
                controller.showControl();
            }
            if (observedData.hasResults && typeof controller.report === "function") {
                controller.report();
            }
            return controller;
        };

        return controller;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.Observed = Observed;
}

/* ----------------------------------------------------------------------------
 * Omni
 * Doc: controllers_js/README.md — Omni Controller Reference (2024 helper migration)
 * ----------------------------------------------------------------------------
 */
var Omni = (function () {
    var instance;

    var MAX_SBS_FILE_BYTES = 100 * 1024 * 1024;
    var ALLOWED_SBS_FILE_EXTENSIONS = new Set(["tif", "tiff", "img"]);
    var SCENARIO_ORDER = [
        "sbs_map",
        "uniform_low",
        "uniform_moderate",
        "uniform_high",
        "undisturbed",
        "prescribed_fire",
        "thinning",
        "mulch"
    ];
    var EVENT_NAMES = [
        "omni:scenarios:loaded",
        "omni:scenario:added",
        "omni:scenario:removed",
        "omni:scenario:updated",
        "omni:run:started",
        "omni:run:completed",
        "omni:run:error"
    ];

    var SCENARIO_CATALOG = {
        uniform_low: {
            label: "Uniform Low Severity Fire",
            controls: []
        },
        uniform_moderate: {
            label: "Uniform Moderate Severity Fire",
            controls: []
        },
        uniform_high: {
            label: "Uniform High Severity Fire",
            controls: []
        },
        sbs_map: {
            label: "SBS Map",
            controls: [
                {
                    type: "file",
                    name: "sbs_file",
                    label: "Upload SBS File",
                    help: "GeoTIFF/IMG, 100 MB maximum."
                }
            ]
        },
        undisturbed: {
            label: "Undisturbed",
            controls: [],
            condition: function (ctx) {
                var disturbed = resolveDisturbed();
                if (!disturbed) {
                    return false;
                }
                if (typeof disturbed.get_has_sbs_cached === "function") {
                    var cached = disturbed.get_has_sbs_cached();
                    if (cached !== undefined) {
                        return cached === true;
                    }
                }
                if (typeof disturbed.has_sbs === "function") {
                    try {
                        return disturbed.has_sbs({ forceRefresh: false }) === true;
                    } catch (err) {
                        console.warn("[Omni] Disturbed.has_sbs failed", err);
                    }
                }
                return false;
            }
        },
        prescribed_fire: {
            label: "Prescribed Fire",
            controls: [],
            condition: function (ctx) {
                var disturbed = resolveDisturbed();
                var hasSbs = false;
                if (disturbed) {
                    if (typeof disturbed.get_has_sbs_cached === "function") {
                        var cached = disturbed.get_has_sbs_cached();
                        if (cached !== undefined) {
                            hasSbs = cached === true;
                        }
                    } else if (typeof disturbed.has_sbs === "function") {
                        try {
                            hasSbs = disturbed.has_sbs({ forceRefresh: false }) === true;
                        } catch (err) {
                            console.warn("[Omni] Disturbed.has_sbs failed", err);
                        }
                    }
                }
                if (!hasSbs) {
                    return true;
                }
                if (ctx && typeof ctx.hasUndisturbed === "function") {
                    return ctx.hasUndisturbed();
                }
                return false;
            }
        },
        thinning: {
            label: "Thinning",
            controls: [
                {
                    type: "select",
                    name: "canopy_cover",
                    label: "Canopy cover reduction to",
                    options: [
                        { value: "40%", label: "40%" },
                        { value: "65%", label: "65%" }
                    ]
                },
                {
                    type: "select",
                    name: "ground_cover",
                    label: "Ground cover",
                    options: [
                        { value: "93%", label: "93% – Cable" },
                        { value: "90%", label: "90% – Forward" },
                        { value: "85%", label: "85% – Skidder" },
                        { value: "75%", label: "75%" }
                    ]
                }
            ]
        },
        mulch: {
            label: "Mulching",
            controls: [
                {
                    type: "select",
                    name: "ground_cover_increase",
                    label: "Ground cover increase",
                    options: [
                        { value: "15%", label: "15% – ½ tons/acre" },
                        { value: "30%", label: "30% – 1 ton/acre" },
                        { value: "60%", label: "60% – 2 tons/acre" }
                    ]
                },
                {
                    type: "select",
                    name: "base_scenario",
                    label: "Base scenario",
                    options: [
                        { value: "uniform_low", label: "Uniform Low Severity Fire" },
                        { value: "uniform_moderate", label: "Uniform Moderate Severity Fire" },
                        { value: "uniform_high", label: "Uniform High Severity Fire" },
                        { value: "sbs_map", label: "SBS Map" }
                    ]
                }
            ]
        }
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Omni controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Omni controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Omni controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Omni controller requires WCEvents helpers.");
        }
        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function resolveDisturbed() {
        if (!window.Disturbed || typeof window.Disturbed.getInstance !== "function") {
            return null;
        }
        try {
            return window.Disturbed.getInstance();
        } catch (err) {
            console.warn("[Omni] Unable to resolve Disturbed controller", err);
        }
        return null;
    }

    function hasUndisturbedScenario(container) {
        if (!container) {
            return false;
        }
        var selects = container.querySelectorAll("[data-omni-role='scenario-select']");
        for (var i = 0; i < selects.length; i += 1) {
            if (selects[i].value === "undisturbed") {
                return true;
            }
        }
        return false;
    }

    function scenarioIsAvailable(key, container) {
        var config = SCENARIO_CATALOG[key];
        if (!config) {
            return false;
        }
        if (typeof config.condition === "function") {
            try {
                return !!config.condition({
                    hasUndisturbed: function () {
                        return hasUndisturbedScenario(container);
                    }
                });
            } catch (err) {
                console.warn("[Omni] Scenario condition failed for " + key, err);
                return false;
            }
        }
        return true;
    }

    function ensureOption(parent, value, label) {
        var option = parent.ownerDocument.createElement("option");
        option.value = value;
        option.textContent = label === undefined ? value : label;
        parent.appendChild(option);
        return option;
    }

    function populateScenarioSelect(select, container) {
        if (!select) {
            return;
        }
        var currentValue = select.value;
        while (select.firstChild) {
            select.removeChild(select.firstChild);
        }

        ensureOption(select, "", "Select scenario");
        SCENARIO_ORDER.forEach(function (key) {
            if (!scenarioIsAvailable(key, container)) {
                return;
            }
            var config = SCENARIO_CATALOG[key];
            ensureOption(select, key, config.label);
        });

        if (currentValue && select.querySelector('option[value="' + currentValue + '"]')) {
            select.value = currentValue;
        } else {
            select.value = "";
        }
    }

    function extractFileName(path) {
        if (!path) {
            return "";
        }
        var normalized = String(path);
        var parts = normalized.split(/[\\/]/);
        return parts.length ? parts[parts.length - 1] : normalized;
    }

    function createFieldWrapper(document, control) {
        var field = document.createElement("div");
        field.className = "wc-field";

        var label = document.createElement("label");
        label.className = "wc-field__label";
        label.textContent = control.label || control.name || "";

        var inputRow = document.createElement("div");
        inputRow.className = "wc-field__input-row";

        field.appendChild(label);
        field.appendChild(inputRow);

        return { field: field, row: inputRow };
    }

    function createControlElement(document, control, scenarioIndex, values) {
        var name = control.name;
        var fieldWrap = createFieldWrapper(document, control);
        var row = fieldWrap.row;
        var value = values && values[name] !== undefined ? values[name] : null;

        if (control.type === "select") {
            var select = document.createElement("select");
            select.className = "wc-field__control";
            select.name = name;
            select.id = name + "_" + scenarioIndex;
            select.dataset.omniField = name;

            (control.options || []).forEach(function (option) {
                var optValue = option && typeof option === "object" ? option.value : option;
            var optLabel = option && typeof option === "object" ? option.label : option;
                ensureOption(select, optValue, optLabel);
            });

            if (value !== null && value !== undefined) {
                select.value = value;
            }

            row.appendChild(select);
        } else if (control.type === "file") {
            var input = document.createElement("input");
            input.type = "file";
            input.className = "wc-field__control";
            input.name = name;
            input.id = name + "_" + scenarioIndex;
            input.accept = ".tif,.tiff,.img";
            input.dataset.omniField = name;
            input.dataset.omniRole = "scenario-file";
            row.appendChild(input);

            var hint = document.createElement("p");
            hint.className = "wc-field__help";
            hint.textContent = control.help || "GeoTIFF/IMG, 100 MB maximum.";
            fieldWrap.field.appendChild(hint);

            if (values && values.sbs_file_path) {
                var existing = document.createElement("p");
                existing.className = "wc-field__help";
                existing.textContent = "Current file: " + extractFileName(values.sbs_file_path);
                fieldWrap.field.appendChild(existing);
            }
        }

        return fieldWrap.field;
    }

    function readScenarioDefinition(scenarioItem) {
        if (!scenarioItem) {
            return null;
        }
        var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
        if (!select || !select.value) {
            return null;
        }
        var definition = { type: select.value };
        var inputs = scenarioItem.querySelectorAll("[data-omni-field]");
        inputs.forEach(function (input) {
            var fieldName = input.dataset.omniField;
            if (!fieldName) {
                return;
            }
            if (input.type === "file") {
                if (input.files && input.files.length > 0) {
                    definition[fieldName] = input.files[0].name;
                }
                return;
            }
            definition[fieldName] = input.value;
        });
        return definition;
    }

    function scenarioNameFromDefinition(definition) {
        if (!definition || !definition.type) {
            return null;
        }
        var type = String(definition.type);
        var normalizedType = type.toLowerCase();
        var typeAlias = {
            "1": "uniform_low",
            "2": "uniform_moderate",
            "3": "uniform_high",
            "4": "thinning",
            "5": "mulch",
            "8": "sbs_map",
            "9": "undisturbed",
            "10": "prescribed_fire"
        };
        if (typeAlias[normalizedType]) {
            normalizedType = typeAlias[normalizedType];
        }

        if (normalizedType === "thinning") {
            var canopy = String(definition.canopy_cover || "").replace(/%/g, "");
            var ground = String(definition.ground_cover || "").replace(/%/g, "");
            if (!canopy || !ground) {
                return null;
            }
            return normalizedType + "_" + canopy + "_" + ground;
        }

        if (normalizedType === "mulch") {
            var increase = String(definition.ground_cover_increase || "").replace(/%/g, "");
            var base = String(definition.base_scenario || "").trim();
            if (!increase || !base) {
                return null;
            }
            return normalizedType + "_" + increase + "_" + base;
        }

        if (normalizedType === "sbs_map") {
            var rawPath = String(definition.sbs_file_path || definition.sbs_map || definition.sbs_file || "");
            var fileName = rawPath.split(/[/\\\\]/).pop() || "";
            if (!fileName) {
                return normalizedType;
            }
            try {
                return normalizedType + "_" + btoa(fileName).replace(/=+$/g, "");
            } catch (err) {
                return normalizedType;
            }
        }

        return normalizedType;
    }

    function validateSbsFile(file) {
        if (!file) {
            return;
        }
        var name = file.name || "";
        var dot = name.lastIndexOf(".");
        var ext = dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
        if (!ALLOWED_SBS_FILE_EXTENSIONS.has(ext)) {
            throw new Error("SBS maps must be .tif, .tiff, or .img files.");
        }
        if (file.size > MAX_SBS_FILE_BYTES) {
            throw new Error("SBS maps must be 100 MB or smaller.");
        }
    }

    function formatJobHint(jobId) {
        if (!jobId) {
            return "";
        }
        var host = "";
        if (typeof window !== "undefined" && window.location && window.location.host) {
            host = window.location.host;
        }
        var dashboardUrl = host
            ? "https://" + host + "/weppcloud/rq/job-dashboard/" + encodeURIComponent(jobId)
            : "/weppcloud/rq/job-dashboard/" + encodeURIComponent(jobId);
        return 'job_id: <a href="' + dashboardUrl + '" target="_blank" rel="noopener noreferrer">' + jobId + "</a>";
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;

        var omni = controlBase();
        var omniEvents = null;
        var scenarioCounter = 0;
        var deleteButton = null;
        var deleteModal = null;
        var deleteModalList = null;
        var deleteModalConfirm = null;
        var pendingDeleteSelections = [];

        if (events && typeof events.createEmitter === "function") {
            var baseEmitter = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                omniEvents = events.useEventMap(EVENT_NAMES, baseEmitter);
            } else {
                omniEvents = baseEmitter;
            }
        }

        if (omniEvents) {
            omni.events = omniEvents;
        }

        var formElement = dom.ensureElement("#omni_form", "Omni form not found.");
        var infoElement = dom.qs("#omni_form #info");
        var statusElement = dom.qs("#omni_form #status");
        var stacktraceElement = dom.qs("#omni_form #stacktrace");
        var rqJobElement = dom.qs("#omni_form #rq_job");
        var spinnerElement = dom.qs("#omni_form #braille");
        var hintElement = dom.qs("#hint_run_omni");
        deleteButton = dom.qs("#omni_form [data-omni-action='delete-selected']");
        deleteModal = dom.qs("#omni-delete-modal");
        deleteModalList = deleteModal ? deleteModal.querySelector("[data-omni-role='delete-list']") : null;
        deleteModalConfirm = deleteModal ? deleteModal.querySelector("[data-omni-action='confirm-delete']") : null;
        var scenarioContainer = dom.ensureElement("#scenario-container", "Omni scenario container not found.");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        omni.form = formElement;
        omni.info = infoAdapter;
        omni.status = statusAdapter;
        omni.stacktrace = stacktraceAdapter;
        omni.rq_job = rqJobAdapter;
        omni.statusSpinnerEl = spinnerElement;
        omni.command_btn_id = "btn_run_omni";
        omni.hint = hintAdapter;
        omni._completion_seen = false;

        omni.attach_status_stream(omni, {
            form: formElement,
            channel: "omni",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        function resetCompletionSeen() {
            omni._completion_seen = false;
        }

        var baseTriggerEvent = omni.triggerEvent.bind(omni);
        omni.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "OMNI_SCENARIO_RUN_TASK_COMPLETED") {
                if (omni._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                omni._completion_seen = true;
                omni.report_scenarios();
                omni.disconnect_status_stream(omni);
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:completed", payload || {});
                }
            } else if (normalized === "END_BROADCAST") {
                omni.disconnect_status_stream(omni);
            }

            return baseTriggerEvent(eventName, payload);
        };

        function emitScenarioUpdate(scenarioItem) {
            if (!omniEvents || typeof omniEvents.emit !== "function") {
                return;
            }
            var definition = readScenarioDefinition(scenarioItem);
            syncScenarioSelectionState(scenarioItem, definition);
            updateDeleteButtonState();
            omniEvents.emit("omni:scenario:updated", {
                scenario: definition,
                element: scenarioItem
            });
        }

        function syncScenarioSelectionState(scenarioItem, definition) {
            if (!scenarioItem) {
                return;
            }
            var checkbox = scenarioItem.querySelector("[data-omni-role='scenario-select-toggle']");
            var scenarioName = scenarioNameFromDefinition(definition || readScenarioDefinition(scenarioItem));
            scenarioItem.dataset.omniScenarioName = scenarioName || "";
            if (!checkbox) {
                return;
            }
            var enabled = Boolean(scenarioName);
            checkbox.disabled = !enabled;
            if (!enabled) {
                checkbox.checked = false;
            }
        }

        function collectSelectedScenarios() {
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            var selections = [];
            items.forEach(function (item) {
                var checkbox = item.querySelector("[data-omni-role='scenario-select-toggle']");
                if (!checkbox || checkbox.disabled || !checkbox.checked) {
                    return;
                }
                var definition = readScenarioDefinition(item);
                var scenarioName = scenarioNameFromDefinition(definition);
                if (scenarioName) {
                    selections.push({
                        item: item,
                        name: scenarioName,
                        definition: definition
                    });
                }
            });
            return selections;
        }

        function updateDeleteButtonState() {
            if (!deleteButton) {
                return;
            }
            var selections = collectSelectedScenarios();
            deleteButton.disabled = selections.length === 0;
        }

        function openDeleteModal() {
            var selections = collectSelectedScenarios();
            if (selections.length === 0) {
                setStatus("Select at least one scenario to delete.");
                return;
            }
            if (!deleteModal || !deleteModalList) {
                setStatus("Delete dialog unavailable.");
                return;
            }
            deleteModalList.innerHTML = "";
            selections.forEach(function (selection) {
                var li = deleteModal.ownerDocument.createElement("li");
                li.textContent = selection.name || "Scenario";
                deleteModalList.appendChild(li);
            });
            pendingDeleteSelections = selections;
            openModal(deleteModal);
        }

        function pruneDeletedScenarios(removedNames) {
            if (!removedNames || removedNames.length === 0) {
                return;
            }
            var removedSet = new Set(removedNames.map(function (name) {
                return String(name);
            }));
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            items.forEach(function (item) {
                var scenarioName = item.dataset.omniScenarioName;
                if (scenarioName && removedSet.has(scenarioName)) {
                    item.remove();
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:scenario:removed", {
                            scenario: scenarioName,
                            element: item
                        });
                    }
                }
            });
        }

        function confirmDeleteSelected() {
            if (!pendingDeleteSelections.length) {
                closeModal(deleteModal);
                return;
            }
            var names = pendingDeleteSelections
                .map(function (entry) { return entry.name; })
                .filter(Boolean);
            if (!names.length) {
                closeModal(deleteModal);
                return;
            }

            setStatus("Deleting selected scenarios...");
            if (deleteModalConfirm) {
                deleteModalConfirm.disabled = true;
            }

            http.postJson(url_for_run("api/omni/delete_scenarios"), { scenario_names: names }, { form: formElement })
                .then(function (response) {
                    var body = response && response.body ? response.body : {};
                    var content = body && body.Content ? body.Content : {};
                    var removed = Array.isArray(content.removed) ? content.removed : [];
                    var missing = Array.isArray(content.missing) ? content.missing : [];

                    if (removed.length) {
                        pruneDeletedScenarios(removed);
                    }

                    refreshScenarioOptions();
                    updateDeleteButtonState();

                    var parts = [];
                    if (removed.length) {
                        parts.push("Removed " + removed.length + " scenario(s).");
                    }
                    if (missing.length) {
                        parts.push("Missing: " + missing.join(", "));
                    }
                    setStatus(parts.join(" ") || "No scenarios deleted.");
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    omni.pushResponseStacktrace(omni, payload);
                    setStatus(payload && payload.Error ? payload.Error : "Failed to delete scenarios.");
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:error", { error: error });
                    }
                })
                .finally(function () {
                    pendingDeleteSelections = [];
                    if (deleteModalConfirm) {
                        deleteModalConfirm.disabled = false;
                    }
                    closeModal(deleteModal);
                });
        }

        function refreshScenarioOptions() {
            var selects = scenarioContainer.querySelectorAll("[data-omni-role='scenario-select']");
            selects.forEach(function (select) {
                var previous = select.value;
                populateScenarioSelect(select, scenarioContainer);
                if (previous && select.value === previous) {
                    emitScenarioUpdate(select.closest("[data-omni-scenario-item='true']"));
                }
            });
        }

        function updateScenarioControls(scenarioItem, values) {
            if (!scenarioItem) {
                return;
            }
            var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
            var controlsHost = scenarioItem.querySelector("[data-omni-scenario-controls]");
            if (!controlsHost) {
                return;
            }
            controlsHost.innerHTML = "";

            if (!select || !select.value) {
                return;
            }

            var config = SCENARIO_CATALOG[select.value];
            if (!config) {
                return;
            }

            (config.controls || []).forEach(function (control) {
                var controlField = createControlElement(
                    scenarioItem.ownerDocument,
                    control,
                    scenarioItem.dataset.index || "0",
                    values
                );
                controlsHost.appendChild(controlField);
            });

            syncScenarioSelectionState(scenarioItem, values || readScenarioDefinition(scenarioItem));
        }

        function addScenario(prefill, options) {
            var opts = options || {};
            var scenarioItem = formElement.ownerDocument.createElement("div");
            scenarioItem.className = "scenario-item wc-card wc-card--subtle";
            scenarioItem.dataset.index = String(scenarioCounter++);
            scenarioItem.dataset.omniScenarioItem = "true";
            scenarioItem.innerHTML = [
                '<div class="wc-card__body scenario-item__body">',
                '  <div class="scenario-item__inputs">',
                '    <label class="scenario-item__selector" aria-label="Select scenario for deletion">',
                '      <input type="checkbox"',
                '             class="disable-readonly"',
                '             data-omni-role="scenario-select-toggle"',
                '             title="Select scenario for deletion" />',
                '    </label>',
                '    <div class="wc-field scenario-item__field">',
                '      <label class="wc-field__label" for="omni_scenario_' + scenarioItem.dataset.index + '">Scenario</label>',
                '      <select class="wc-field__control"',
                '              id="omni_scenario_' + scenarioItem.dataset.index + '"',
                '              name="scenario"',
                '              data-omni-role="scenario-select">',
                '        <option value="">Select scenario</option>',
                '      </select>',
                '    </div>',
                '    <div class="scenario-controls scenario-item__controls" data-omni-scenario-controls></div>',
                '  </div>',
                '  <div class="scenario-item__actions">',
                '    <button type="button" class="pure-button button-error disable-readonly" data-omni-action="remove-scenario">',
                '      Remove',
                '    </button>',
                '  </div>',
                '</div>'
            ].join("\n");

            scenarioContainer.appendChild(scenarioItem);

            var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
            populateScenarioSelect(select, scenarioContainer);

            if (prefill && prefill.type) {
                select.value = prefill.type;
            }
            updateScenarioControls(scenarioItem, prefill || null);
            syncScenarioSelectionState(scenarioItem, prefill || readScenarioDefinition(scenarioItem));
            updateDeleteButtonState();

            if (!opts.deferRefresh) {
                refreshScenarioOptions();
            }

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:scenario:added", {
                    scenario: readScenarioDefinition(scenarioItem),
                    element: scenarioItem
                });
            }

            return scenarioItem;
        }

        function removeScenario(target) {
            var scenarioItem = target.closest("[data-omni-scenario-item='true']");
            if (!scenarioItem) {
                return;
            }

            scenarioItem.remove();
            refreshScenarioOptions();
            updateDeleteButtonState();

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:scenario:removed", { element: scenarioItem });
            }
        }

        function serializeScenarios() {
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            var scenarios = [];
            var formData = new FormData(formElement);
            if (typeof formData.delete === "function") {
                formData.delete("scenarios");
            }

            items.forEach(function (item, index) {
                var select = item.querySelector("[data-omni-role='scenario-select']");
                if (!select || !select.value) {
                    return;
                }

                var scenarioDef = { type: select.value };
                var config = SCENARIO_CATALOG[select.value] || {};
                var controls = item.querySelectorAll("[data-omni-field]");

                controls.forEach(function (input) {
                    var name = input.dataset.omniField;
                    if (!name) {
                        return;
                    }

                    if (input.type === "file") {
                        if (input.files && input.files.length > 0) {
                            var file = input.files[0];
                            if (select.value === "sbs_map") {
                                validateSbsFile(file);
                            }
                            formData.append("scenarios[" + index + "][" + name + "]", file);
                            scenarioDef[name] = file.name;
                        }
                        return;
                    }

                    if (input.value !== undefined && input.value !== null && input.value !== "") {
                        scenarioDef[name] = input.value;
                    }
                });

                scenarios.push(scenarioDef);
            });

            formData.append("scenarios", JSON.stringify(scenarios));
            return { formData: formData, scenarios: scenarios };
        }

        function clearStatus() {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html("");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.html === "function") {
                stacktraceAdapter.html("");
            }
        }

        function setStatus(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message || "");
            }
        }

        function openModal(modal) {
            if (!modal) {
                return;
            }
            var manager = typeof window !== "undefined" ? window.ModalManager : null;
            if (manager && typeof manager.open === "function") {
                manager.open(modal);
                return;
            }
            modal.removeAttribute("hidden");
            modal.style.display = "flex";
            modal.classList.add("is-visible");
            if (typeof document !== "undefined") {
                document.body.classList.add("wc-modal-open");
            }
        }

        function closeModal(modal) {
            if (!modal) {
                return;
            }
            var manager = typeof window !== "undefined" ? window.ModalManager : null;
            if (manager && typeof manager.close === "function") {
                manager.close(modal);
                return;
            }
            modal.classList.remove("is-visible");
            modal.setAttribute("hidden", "hidden");
            modal.style.display = "";
            if (typeof document !== "undefined") {
                document.body.classList.remove("wc-modal-open");
            }
        }

        function bindModalDismiss(modal) {
            if (!modal) {
                return;
            }
            var dismissers = modal.querySelectorAll("[data-modal-dismiss]");
            dismissers.forEach(function (btn) {
                btn.addEventListener("click", function (event) {
                    event.preventDefault();
                    closeModal(modal);
                });
            });
        }

        bindModalDismiss(deleteModal);

        omni.serializeScenarios = serializeScenarios;

        omni.run_omni_scenarios = function () {
            clearStatus();

            var payload;
            try {
                payload = serializeScenarios();
            } catch (err) {
                var message = err && err.message ? err.message : "Validation failed. Check SBS uploads.";
                setStatus(message);
                if (hintAdapter && typeof hintAdapter.text === "function") {
                    hintAdapter.text(message);
                }
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: err });
                }
                return;
            }

            resetCompletionSeen();
            setStatus("Submitting omni run...");
            omni.connect_status_stream(omni);

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:run:started", { scenarios: payload.scenarios });
            }

            http.request(url_for_run("rq/api/run_omni"), {
                method: "POST",
                body: payload.formData,
                form: formElement
            }).then(function (response) {
                var body = response && response.body ? response.body : null;
                if (body && body.Success === true) {
                    setStatus("run_omni_rq job submitted: " + body.job_id);
                    omni.poll_completion_event = "OMNI_SCENARIO_RUN_TASK_COMPLETED";
                    omni.set_rq_job_id(omni, body.job_id);
                    if (hintAdapter && typeof hintAdapter.html === "function") {
                        hintAdapter.html(formatJobHint(body.job_id));
                        if (typeof hintAdapter.show === "function") {
                            hintAdapter.show();
                        }
                    }
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:completed", {
                            jobId: body.job_id,
                            scenarios: payload.scenarios
                        });
                    }
                } else if (body) {
                    omni.pushResponseStacktrace(omni, body);
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:error", { response: body });
                    }
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                omni.pushResponseStacktrace(omni, payload);
                setStatus(payload && payload.Error ? payload.Error : "Omni run failed.");
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: error });
                }
            });
        };

        omni.runOmniScenarios = omni.run_omni_scenarios;

        omni.load_scenarios_from_backend = function () {
            clearStatus();
            var endpoint = url_for_run("api/omni/get_scenarios");
            return http.getJson(endpoint).then(function (data) {
                if (!Array.isArray(data)) {
                    throw new Error("Invalid scenario format");
                }

                scenarioContainer.innerHTML = "";
                scenarioCounter = 0;

                data.forEach(function (scenario) {
                    var item = addScenario(scenario, { deferRefresh: true });
                    var select = item.querySelector("[data-omni-role='scenario-select']");
                    if (select && scenario.type) {
                        select.value = scenario.type;
                    }
                    updateScenarioControls(item, scenario);
                    syncScenarioSelectionState(item, scenario);
                });

                refreshScenarioOptions();
                updateDeleteButtonState();

                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:scenarios:loaded", { scenarios: data });
                }
            }).catch(function (error) {
                console.error("Error loading scenarios:", error);
                setStatus("Unable to load saved scenarios.");
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: error });
                }
            });
        };

        omni.report_scenarios = function () {
            if (infoAdapter && typeof infoAdapter.html === "function") {
                infoAdapter.html("");
            }

            http.request(url_for_run("report/omni_scenarios/"), {
                method: "GET",
                headers: { Accept: "text/html" }
            }).then(function (response) {
                var body = response && response.body ? response.body : "";
                omni.info.html(body);
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                omni.pushResponseStacktrace(omni, payload);
            });
        };

        dom.delegate(formElement, "click", "[data-omni-action='add-scenario']", function (event) {
            event.preventDefault();
            addScenario();
        });

        dom.delegate(formElement, "click", "[data-omni-action='delete-selected']", function (event) {
            event.preventDefault();
            openDeleteModal();
        });

        dom.delegate(formElement, "click", "[data-omni-action='remove-scenario']", function (event) {
            event.preventDefault();
            removeScenario(event.target);
        });

        dom.delegate(formElement, "click", "[data-omni-action='run-scenarios']", function (event) {
            event.preventDefault();
            omni.run_omni_scenarios();
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-role='scenario-select']", function (event, matched) {
            var item = matched.closest("[data-omni-scenario-item='true']");
            updateScenarioControls(item);
            refreshScenarioOptions();
            emitScenarioUpdate(item);
            syncScenarioSelectionState(item);
            updateDeleteButtonState();
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-field]", function (event, matched) {
            var item = matched.closest("[data-omni-scenario-item='true']");
            emitScenarioUpdate(item);
            syncScenarioSelectionState(item);
            updateDeleteButtonState();
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-role='scenario-select-toggle']", function () {
            updateDeleteButtonState();
        });

        document.addEventListener("disturbed:has_sbs_changed", function () {
            refreshScenarioOptions();
        });

        if (deleteModalConfirm) {
            deleteModalConfirm.addEventListener("click", function (event) {
                event.preventDefault();
                confirmDeleteSelected();
            });
        }

        var bootstrapState = {
            scenariosLoaded: false,
            reportDisplayed: false
        };

        omni.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "omni")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_omni_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_omni_rq")) {
                    var value = jobIds.run_omni_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (jobId) {
                resetCompletionSeen();
                omni.poll_completion_event = "OMNI_SCENARIO_RUN_TASK_COMPLETED";
            }
            if (typeof omni.set_rq_job_id === "function") {
                omni.set_rq_job_id(omni, jobId);
            }

            if (!bootstrapState.scenariosLoaded && typeof omni.load_scenarios_from_backend === "function") {
                omni.load_scenarios_from_backend();
                bootstrapState.scenariosLoaded = true;
            }

            var omniData = (ctx.data && ctx.data.omni) || {};
            var hasRanScenarios = controllerContext.hasRanScenarios;
            if (hasRanScenarios === undefined) {
                hasRanScenarios = omniData.hasRanScenarios;
            }

            if (hasRanScenarios && !bootstrapState.reportDisplayed && typeof omni.report_scenarios === "function") {
                omni.report_scenarios();
                bootstrapState.reportDisplayed = true;
            }

            return omni;
        };

        return omni;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        },
        remount: function remount() {
            instance = null;
            return this.getInstance();
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.Omni = Omni;
}

/* ----------------------------------------------------------------------------
 * PATH Cost-Effective Control
 * Doc: controllers_js/README.md — Path CE Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var PathCE = (function () {
    var instance;

    function endpoint(path) {
        if (typeof url_for_run === "function") {
            return url_for_run(path);
        }
        if (path.charAt(0) !== "/") {
            return "/" + path;
        }
        return path;
    }

    var ENDPOINTS = {
        config: function () { return endpoint("api/path_ce/config"); },
        status: function () { return endpoint("api/path_ce/status"); },
        results: function () { return endpoint("api/path_ce/results"); },
        run: function () { return endpoint("tasks/path_cost_effective_run"); }
    };

    var TREATMENT_FIELDS = ["label", "scenario", "quantity", "unit_cost", "fixed_cost"];
    var EVENT_NAMES = [
        "pathce:config:loaded",
        "pathce:config:saved",
        "pathce:config:error",
        "pathce:treatment:added",
        "pathce:treatment:removed",
        "pathce:treatment:updated",
        "pathce:status:update",
        "pathce:results:update",
        "pathce:run:started",
        "pathce:run:completed",
        "pathce:run:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    var POLL_INTERVAL_MS = 5000;
    var TERMINAL_STATUSES = { completed: true, failed: true };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("PathCE controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("PathCE controller requires WCForms helpers.");
        }
        if (!http || typeof http.getJson !== "function" || typeof http.postJson !== "function") {
            throw new Error("PathCE controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("PathCE controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function toNumber(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        var num = Number(value);
        return Number.isFinite(num) ? num : null;
    }

    function normalizeSeverity(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        var values = Array.isArray(value) ? value : [value];
        var filtered = values
            .map(function (item) {
                if (item === undefined || item === null) {
                    return "";
                }
                return String(item).trim();
            })
            .filter(function (item) {
                return item.length > 0;
            });
        return filtered.length ? filtered : null;
    }

    function buildFormValues(config) {
        var slopeRange = Array.isArray(config && config.slope_range) ? config.slope_range : [null, null];
        return {
            sddc_threshold: config && config.sddc_threshold !== undefined && config.sddc_threshold !== null ? config.sddc_threshold : "",
            sdyd_threshold: config && config.sdyd_threshold !== undefined && config.sdyd_threshold !== null ? config.sdyd_threshold : "",
            slope_min: slopeRange[0] !== undefined && slopeRange[0] !== null ? slopeRange[0] : "",
            slope_max: slopeRange[1] !== undefined && slopeRange[1] !== null ? slopeRange[1] : "",
            severity_filter: config && config.severity_filter ? config.severity_filter : []
        };
    }

    function applyFormValues(forms, formElement, values) {
        if (forms && typeof forms.applyValues === "function") {
            forms.applyValues(formElement, values);
            return;
        }
        if (!formElement || !values) {
            return;
        }
        Object.keys(values).forEach(function (name) {
            var field = formElement.elements.namedItem(name);
            if (!field) {
                return;
            }
            var value = values[name];
            if (field instanceof window.HTMLSelectElement && field.multiple) {
                var selectedValues = normalizeSeverity(value) || [];
                Array.prototype.slice.call(field.options).forEach(function (option) {
                    option.selected = selectedValues.indexOf(option.value) !== -1;
                });
                return;
            }
            if (field instanceof window.RadioNodeList) {
                Array.prototype.slice.call(field).forEach(function (input) {
                    input.checked = String(input.value) === String(value);
                });
                return;
            }
            if (field instanceof window.HTMLInputElement && field.type === "checkbox") {
                field.checked = Boolean(value);
                return;
            }
            if (value === null || value === undefined) {
                field.value = "";
            } else {
                field.value = value;
            }
        });
    }

    function setMessage(controller, message, isError) {
        if (controller.message && typeof controller.message.text === "function") {
            controller.message.text(message || "");
        }
        if (controller.messageElement) {
            if (isError) {
                controller.messageElement.classList.add("wc-field__help--error");
            } else {
                controller.messageElement.classList.remove("wc-field__help--error");
            }
        }
    }

    function updateBraille(controller, progress) {
        var text = "";
        if (typeof progress === "number" && !Number.isNaN(progress)) {
            var clamped = Math.max(0, Math.min(1, progress));
            text = "Progress: " + Math.round(clamped * 100) + "%";
        }
        if (controller.braille && typeof controller.braille.text === "function") {
            controller.braille.text(text);
        }
    }

    function formatNumber(value) {
        if (value === undefined || value === null) {
            return "—";
        }
        var num = Number(value);
        if (!Number.isFinite(num)) {
            return "—";
        }
        return num.toFixed(2);
    }

    function renderSummary(controller, results) {
        var summaryElement = controller.summaryElement;
        if (!summaryElement) {
            return;
        }
        summaryElement.textContent = "";
        var doc = window.document;
        var data = results && typeof results === "object" ? results : {};
        if (Object.keys(data).length === 0) {
            var emptyItem = doc.createElement("div");
            emptyItem.className = "wc-summary-pane__item";
            var emptyTerm = doc.createElement("dt");
            emptyTerm.className = "wc-summary-pane__term";
            emptyTerm.textContent = "Summary";
            var emptyDef = doc.createElement("dd");
            emptyDef.className = "wc-summary-pane__definition";
            emptyDef.textContent = "No results yet.";
            emptyItem.appendChild(emptyTerm);
            emptyItem.appendChild(emptyDef);
            summaryElement.appendChild(emptyItem);
            return;
        }
        var rows = [
            ["Status", data.status || "unknown"],
            ["Used Secondary Solver", data.used_secondary ? "Yes" : "No"],
            ["Total Cost (variable)", formatNumber(data.total_cost)],
            ["Total Fixed Cost", formatNumber(data.total_fixed_cost)],
            ["Total Sddc Reduction", formatNumber(data.total_sddc_reduction)],
            ["Final Sddc", formatNumber(data.final_sddc)]
        ];
        var fragment = doc.createDocumentFragment();
        rows.forEach(function (entry) {
            var item = doc.createElement("div");
            item.className = "wc-summary-pane__item";
            var dt = doc.createElement("dt");
            dt.className = "wc-summary-pane__term";
            dt.textContent = entry[0];
            var dd = doc.createElement("dd");
            dd.className = "wc-summary-pane__definition";
            dd.textContent = entry[1];
            item.appendChild(dt);
            item.appendChild(dd);
            fragment.appendChild(item);
        });
        summaryElement.appendChild(fragment);
    }

    function readMulchCosts(costInputs) {
        var costs = {};
        var list = Array.isArray(costInputs) ? costInputs : [];
        list.forEach(function (input) {
            if (!input || typeof input.getAttribute !== "function") {
                return;
            }
            var scenario = input.getAttribute("data-pathce-cost");
            if (!scenario) {
                return;
            }
            var canonicalAttr = input.dataset ? input.dataset.unitizerCanonicalValue : null;
            var sourceValue = canonicalAttr && canonicalAttr !== "" ? canonicalAttr : input.value;
            var value = toNumber(sourceValue);
            costs[scenario] = value === null ? 0 : value;
        });
        return costs;
    }

    function createTreatmentRow(option) {
        var doc = window.document;
        var row = doc.createElement("tr");
        TREATMENT_FIELDS.forEach(function (field) {
            var cell = doc.createElement("td");
            var input = doc.createElement("input");
            input.setAttribute("data-pathce-field", field);
            if (field === "label" || field === "scenario") {
                input.type = "text";
            } else {
                input.type = "number";
                input.step = "any";
                input.min = "0";
            }
            var value = option && Object.prototype.hasOwnProperty.call(option, field) ? option[field] : "";
            input.value = value === null || value === undefined ? "" : String(value);
            cell.appendChild(input);
            row.appendChild(cell);
        });
        var actionCell = doc.createElement("td");
        var removeButton = doc.createElement("button");
        removeButton.type = "button";
        removeButton.setAttribute("data-pathce-action", "remove-treatment");
        removeButton.textContent = "Remove";
        actionCell.appendChild(removeButton);
        row.appendChild(actionCell);
        return row;
    }

    function renderTreatmentOptions(controller, options) {
        var body = controller.treatmentsBody;
        var list = Array.isArray(options) ? options : [];
        if (!body) {
            if (controller.state && controller.state.config) {
                controller.state.config.treatment_options = list.slice();
            }
            return;
        }
        body.textContent = "";
        list.forEach(function (option) {
            body.appendChild(createTreatmentRow(option));
        });
    }

    function appendTreatmentRow(controller, option) {
        var body = controller.treatmentsBody;
        if (!body) {
            return null;
        }
        var row = createTreatmentRow(option || {});
        body.appendChild(row);
        emitEvent(controller, "pathce:treatment:added", { option: option || {}, row: row });
        return row;
    }

    function removeTreatmentRow(controller, row) {
        var body = controller.treatmentsBody;
        if (!body || !row || !row.parentNode) {
            return;
        }
        if (row.parentNode === body) {
            body.removeChild(row);
            emitEvent(controller, "pathce:treatment:removed", { row: row });
        }
    }

    function harvestTreatmentOptions(controller) {
        var body = controller.treatmentsBody;
        if (!body) {
            if (controller.state && controller.state.config && Array.isArray(controller.state.config.treatment_options)) {
                return controller.state.config.treatment_options.slice();
            }
            return [];
        }
        var rows = body.querySelectorAll("tr");
        var options = [];
        Array.prototype.slice.call(rows).forEach(function (row) {
            var getField = function (name) {
                var input = row.querySelector('[data-pathce-field="' + name + '"]');
                return input ? input.value : "";
            };
            var label = String(getField("label") || "").trim();
            var scenario = String(getField("scenario") || "").trim();
            if (!label && !scenario) {
                return;
            }
            var quantity = toNumber(getField("quantity"));
            var unitCost = toNumber(getField("unit_cost"));
            var fixedCost = toNumber(getField("fixed_cost"));
            options.push({
                label: label,
                scenario: scenario,
                quantity: quantity === null ? 0 : quantity,
                unit_cost: unitCost === null ? 0 : unitCost,
                fixed_cost: fixedCost === null ? 0 : fixedCost
            });
        });
        emitEvent(controller, "pathce:treatment:updated", { options: options });
        return options;
    }

    function applyMulchCosts(costInputs, costMap) {
        var list = Array.isArray(costInputs) ? costInputs : [];
        var formScope = null;
        list.forEach(function (input) {
            if (!input || typeof input.getAttribute !== "function") {
                return;
            }
            var scenario = input.getAttribute("data-pathce-cost");
            if (!scenario) {
                return;
            }
            var value = costMap && Object.prototype.hasOwnProperty.call(costMap, scenario)
                ? costMap[scenario]
                : null;
            var hasValue = value !== null && value !== undefined && value !== "";
            input.value = hasValue ? String(value) : "";
            if (input.dataset) {
                input.dataset.unitizerCanonicalValue = hasValue ? String(value) : "";
                if (!input.dataset.unitizerActiveUnit) {
                    var canonicalUnit = input.getAttribute("data-unitizer-unit");
                    if (canonicalUnit) {
                        input.dataset.unitizerActiveUnit = canonicalUnit;
                    }
                }
            }
            if (!formScope && typeof input.closest === "function") {
                formScope = input.closest("form");
            }
        });

        if (typeof window !== "undefined" && window.UnitizerClient && typeof window.UnitizerClient.ready === "function") {
            window.UnitizerClient.ready()
                .then(function (client) {
                    if (client && typeof client.updateNumericFields === "function") {
                        client.updateNumericFields(formScope || undefined);
                    }
                })
                .catch(function () {
                    /* noop */
                });
        }
    }

    function buildPayload(forms, controller) {
        var formElement = controller.form;
        var values = forms.serializeForm(formElement, { format: "json" }) || {};
        var severity = normalizeSeverity(values.severity_filter);
        var slopeMin = toNumber(values.slope_min);
        var slopeMax = toNumber(values.slope_max);
        var sddc = toNumber(values.sddc_threshold);
        var sdyd = toNumber(values.sdyd_threshold);
        return {
            sddc_threshold: sddc === null ? 0 : sddc,
            sdyd_threshold: sdyd === null ? 0 : sdyd,
            slope_range: [slopeMin, slopeMax],
            severity_filter: severity,
            mulch_costs: readMulchCosts(controller.mulchCostInputs),
            treatment_options: harvestTreatmentOptions(controller)
        };
    }

    function updateStatusMessage(controller, message) {
        if (controller.status && typeof controller.status.text === "function") {
            controller.status.text(message || "");
        }
    }

    function emitEvent(controller, name, payload) {
        if (!controller || !name) {
            return;
        }
        var emitter = controller.events;
        if (emitter && typeof emitter.emit === "function") {
            emitter.emit(name, payload || {});
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var controller = controlBase();
        var state = {
            config: {},
            pollTimer: null,
            statusFetchInFlight: false,
            resultsFetchInFlight: false,
            lastStatusValue: null,
            lastEmittedStatus: null,
            lastJobId: null,
            statusStartedAt: null
        };
        controller.state = state;
        controller.job_status_poll_interval_ms = 1200;

        var emitter = events.useEventMap(EVENT_NAMES, events.createEmitter());
        controller.events = emitter;

        var formElement = dom.ensureElement("#path_ce_form", "PATH Cost-Effective form not found.");
        var messageElement = dom.ensureElement("#path_ce_message", "PATH Cost-Effective message element missing.");
        var hintElement = dom.ensureElement("#path_ce_hint", "PATH Cost-Effective hint element missing.");
        var summaryElement = dom.ensureElement("#path_ce_summary", "PATH Cost-Effective summary element missing.");
        var jobElement = dom.ensureElement("#path_ce_rq_job", "PATH Cost-Effective job element missing.");
        var brailleElement = dom.ensureElement("#path_ce_braille", "PATH Cost-Effective braille element missing.");
        var stacktraceElement = dom.ensureElement("#path_ce_stacktrace", "PATH Cost-Effective stacktrace element missing.");
        var statusElement = dom.qs("#path_ce_form #status");
        var infoElement = dom.qs("#path_ce_form #info");
        var treatmentsBody = dom.qs("#path_ce_treatments_table tbody") || dom.qs("#path_ce_treatments_table");

        var hintAdapter = createLegacyAdapter(hintElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var jobAdapter = createLegacyAdapter(jobElement);
        var brailleAdapter = createLegacyAdapter(brailleElement);
        var infoAdapter = createLegacyAdapter(infoElement);
        var messageAdapter = createLegacyAdapter(messageElement);

        controller.form = formElement;
        controller.message = messageAdapter;
        controller.hint = hintAdapter;
        controller.stacktrace = stacktraceAdapter;
        controller.status = statusAdapter;
        controller.rq_job = jobAdapter;
        controller.braille = brailleAdapter;
        controller.info = infoAdapter;
        controller.summaryElement = summaryElement;
        controller.hintElement = hintElement;
        controller.messageElement = messageElement;
        controller.brailleElement = brailleElement;
        controller.command_btn_id = ["path_ce_run"];
        controller.mulchCostInputs = Array.prototype.slice.call(
            formElement.querySelectorAll("[data-pathce-cost]")
        );
        controller.treatmentsBody = treatmentsBody || null;

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function (eventName, payload) {
            if (eventName && eventName.indexOf("job:") === 0) {
                emitEvent(controller, eventName, payload);
            }
            baseTriggerEvent(eventName, payload);
        };

        function applyConfig(config) {
            state.config = Object.assign({}, config || {});
            var values = buildFormValues(state.config);
            applyFormValues(forms, formElement, values);
            applyMulchCosts(controller.mulchCostInputs, state.config.mulch_costs || {});
            renderTreatmentOptions(controller, state.config.treatment_options || []);
            emitEvent(controller, "pathce:config:loaded", { config: state.config });
        }

        function stopPolling() {
            if (state.pollTimer) {
                window.clearInterval(state.pollTimer);
                state.pollTimer = null;
            }
        }

        function startPolling() {
            if (!state.pollTimer) {
                state.pollTimer = window.setInterval(function () {
                    refreshStatus();
                    refreshResults();
                }, POLL_INTERVAL_MS);
            }
            refreshStatus();
            refreshResults();
        }

        function applyStatus(payload) {
            var data = payload || {};
            var statusName = typeof data.status === "string" ? data.status.toLowerCase() : "";
            var previousStatus = state.lastStatusValue;
            var recentRun = state.statusStartedAt && Date.now() - state.statusStartedAt < 3000;
            if (state.lastJobId && previousStatus === "running" && recentRun) {
                // Ignore stale responses immediately after a new run kicks off
                if (statusName && statusName !== "running") {
                    return;
                }
            }

            state.lastStatusValue = statusName || null;

            if (state.lastStatusValue === "running") {
                state.statusStartedAt = Date.now();
            }

            updateStatusMessage(controller, data.status || "");
            setMessage(controller, data.status_message || "", statusName === "failed");
            updateBraille(controller, data.progress);

            emitEvent(controller, "pathce:status:update", { status: data });

            if (statusName === "running") {
                startPolling();
                if (state.lastEmittedStatus !== "running") {
                    state.lastEmittedStatus = "running";
                    controller.triggerEvent("job:started", { task: "pathce:run", job_id: state.lastJobId, status: data });
                }
                return;
            }

            if (!statusName) {
                return;
            }

            if (TERMINAL_STATUSES[statusName]) {
                stopPolling();
                if (state.lastEmittedStatus !== statusName) {
                    state.lastEmittedStatus = statusName;
                    var eventPayload = { task: "pathce:run", job_id: state.lastJobId, status: data };
                    if (statusName === "completed") {
                        controller.triggerEvent("job:completed", eventPayload);
                        emitEvent(controller, "pathce:run:completed", { job_id: state.lastJobId, status: data });
                    } else {
                        controller.triggerEvent("job:error", eventPayload);
                        emitEvent(controller, "pathce:run:error", { job_id: state.lastJobId, status: data });
                    }
                }
            }
        }

        function applyResults(payload) {
            var results = payload && payload.results ? payload.results : {};
            renderSummary(controller, results);
            emitEvent(controller, "pathce:results:update", { results: results });
        }

        function refreshStatus() {
            if (state.statusFetchInFlight) {
                return Promise.resolve(null);
            }
            state.statusFetchInFlight = true;
            return http.getJson(ENDPOINTS.status(), { params: { _: Date.now() } })
                .then(function (data) {
                    applyStatus(data);
                    return data;
                })
                .catch(function (error) {
                    console.warn("[PathCE] status poll failed", error);
                    return null;
                })
                .finally(function () {
                    state.statusFetchInFlight = false;
                });
        }

        function refreshResults() {
            if (state.resultsFetchInFlight) {
                return Promise.resolve(null);
            }
            state.resultsFetchInFlight = true;
            return http.getJson(ENDPOINTS.results(), { params: { _: Date.now() } })
                .then(function (data) {
                    applyResults(data);
                    return data;
                })
                .catch(function (error) {
                    console.warn("[PathCE] result poll failed", error);
                    return null;
                })
                .finally(function () {
                    state.resultsFetchInFlight = false;
                });
        }

        function handleSave(event) {
            event.preventDefault();
            controller.saveConfig();
        }

        function handleRun(event) {
            event.preventDefault();
            controller.run();
        }

        dom.delegate(formElement, "click", "[data-pathce-action='save-config']", handleSave);
        dom.delegate(formElement, "click", "[data-pathce-action='run']", handleRun);
        dom.delegate(formElement, "click", "[data-pathce-action='add-treatment']", function (event) {
            event.preventDefault();
            appendTreatmentRow(controller, {});
        });
        dom.delegate(formElement, "click", "[data-pathce-action='remove-treatment']", function (event) {
            event.preventDefault();
            var row = event && event.target && typeof event.target.closest === "function"
                ? event.target.closest("tr")
                : null;
            removeTreatmentRow(controller, row);
        });

        controller.fetchConfig = function () {
            setMessage(controller, "Loading PATH Cost-Effective configuration…");
            return http.getJson(ENDPOINTS.config(), { params: { _: Date.now() } })
                .then(function (response) {
                    var config = response && response.config ? response.config : {};
                    applyConfig(config);
                    setMessage(controller, "");
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    return config;
                })
                .catch(function (error) {
                    setMessage(controller, "Failed to load configuration.", true);
                    controller.pushErrorStacktrace(controller, error);
                    emitEvent(controller, "pathce:config:error", { error: error });
                    throw error;
                });
        };

        controller.saveConfig = function () {
            var payload = buildPayload(forms, controller);
            setMessage(controller, "Saving configuration…");
            return http.postJson(ENDPOINTS.config(), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    var nextConfig = response && response.config ? response.config : payload;
                    applyConfig(nextConfig);
                    setMessage(controller, "Configuration saved.");
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    emitEvent(controller, "pathce:config:saved", { config: state.config, response: response });
                    return response;
                })
                .catch(function (error) {
                    setMessage(controller, "Failed to save configuration.", true);
                    controller.pushErrorStacktrace(controller, error);
                    emitEvent(controller, "pathce:config:error", { error: error });
                    throw error;
                });
        };

        controller.run = function () {
            if (typeof controller.reset_panel_state === "function") {
                controller.reset_panel_state(controller, {
                    clearJobHint: false,
                    clearStacktrace: true
                });
            }
            setMessage(controller, "Starting PATH Cost-Effective run…");
            if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                controller.stacktrace.empty();
            }
            if (controller.status && typeof controller.status.text === "function") {
                controller.status.text("");
            }
            var statusLog = dom.qs("#path_ce_status_panel [data-status-log]");
            if (statusLog) {
                statusLog.textContent = "";
            }
            state.statusStartedAt = Date.now();
            var payload = buildPayload(forms, controller);
            stopPolling();
            return http.postJson(ENDPOINTS.run(), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    var jobId = response && (response.job_id || response.jobId);
                    state.lastJobId = jobId || null;
                    state.lastEmittedStatus = "running";
                    state.lastStatusValue = "running";
                    if (jobId) {
                        controller.set_rq_job_id(controller, jobId);
                    } else {
                        controller.set_rq_job_id(controller, null);
                    }
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    controller.triggerEvent("job:started", { task: "pathce:run", job_id: state.lastJobId, response: response });
                    emitEvent(controller, "pathce:run:started", { job_id: state.lastJobId, response: response });
                    setMessage(controller, "PATH Cost-Effective job submitted. Monitoring status…");
                    startPolling();
                    refreshResults();
                    return response;
                })
                .catch(function (error) {
                    setMessage(controller, "Failed to enqueue PATH Cost-Effective run.", true);
                    controller.pushErrorStacktrace(controller, error);
                    // Preserve the last job_id hint so users can still inspect the previous attempt.
                    controller.stop_job_status_polling(controller);
                    controller.reset_status_spinner(controller);
                    state.lastEmittedStatus = "error";
                    emitEvent(controller, "pathce:run:error", { error: error });
                    controller.triggerEvent("job:error", { task: "pathce:run", error: error });
                    throw error;
                });
        };

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "pathCe")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_path_ce")
                : null;

            if (!jobId && controllerContext && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }

            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_path_ce")) {
                    var value = jobIds.run_path_ce;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            state.lastJobId = jobId || null;

            if (typeof controller.set_rq_job_id === "function") {
                controller.set_rq_job_id(controller, jobId || null);
            }
        };

        controller.init = function () {
            controller.fetchConfig()
                .catch(function () {
                    return null;
                })
                .finally(function () {
                    refreshStatus();
                    refreshResults();
                });
        };

        return controller;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
                instance.init();
            }
            return instance;
        }
    };
})();

window.PathCE = PathCE;

/* ----------------------------------------------------------------------------
 * Rangeland Cover
 * Doc: controllers_js/README.md — Rangeland Cover Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var RangelandCover = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "rangeland:config:loaded",
        "rangeland:mode:changed",
        "rangeland:rap-year:changed",
        "rangeland:run:started",
        "rangeland:run:completed",
        "rangeland:run:failed",
        "rangeland:report:loaded",
        "rangeland:report:failed"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("Rangeland cover controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Rangeland cover controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.request !== "function") {
            throw new Error("Rangeland cover controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Rangeland cover controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function parseInteger(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function parseOptionalInteger(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return value;
        }
        return parsed;
    }

    function parseCoverValue(value) {
        if (value === undefined || value === null || value === "") {
            return value;
        }
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        if (typeof value === "string") {
            var trimmed = value.trim();
            if (trimmed === "") {
                return "";
            }
            var parsed = parseFloat(trimmed);
            if (!Number.isNaN(parsed)) {
                return parsed;
            }
        }
        return value;
    }

    function resolveFieldValue(values, keys) {
        if (!values) {
            return undefined;
        }
        for (var i = 0; i < keys.length; i += 1) {
            var key = keys[i];
            if (Object.prototype.hasOwnProperty.call(values, key)) {
                return values[key];
            }
        }
        return undefined;
    }

    function readFormState(forms, formElement) {
        var values = forms.serializeForm(formElement, { format: "json" }) || {};
        var defaults = {
            bunchgrass: parseCoverValue(resolveFieldValue(values, ["input_bunchgrass_cover", "bunchgrass_cover"])),
            forbs: parseCoverValue(resolveFieldValue(values, ["input_forbs_cover", "forbs_cover"])),
            sodgrass: parseCoverValue(resolveFieldValue(values, ["input_sodgrass_cover", "sodgrass_cover"])),
            shrub: parseCoverValue(resolveFieldValue(values, ["input_shrub_cover", "shrub_cover"])),
            basal: parseCoverValue(resolveFieldValue(values, ["input_basal_cover", "basal_cover"])),
            rock: parseCoverValue(resolveFieldValue(values, ["input_rock_cover", "rock_cover"])),
            litter: parseCoverValue(resolveFieldValue(values, ["input_litter_cover", "litter_cover"])),
            cryptogams: parseCoverValue(resolveFieldValue(values, ["input_cryptogams_cover", "cryptogams_cover"]))
        };

        return {
            mode: parseInteger(values.rangeland_cover_mode, 0),
            rapYear: parseOptionalInteger(values.rap_year),
            defaults: defaults
        };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var rangeland = controlBase();
        var rangelandEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                rangelandEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                rangelandEvents = emitterBase;
            }
        }

        if (rangelandEvents) {
            rangeland.events = rangelandEvents;
        }

        var formElement = dom.ensureElement("#rangeland_cover_form", "Rangeland cover form not found.");
        var infoElement = dom.qs("#rangeland_cover_form #info");
        var statusElement = dom.qs("#rangeland_cover_form #status");
        var stacktraceElement = dom.qs("#rangeland_cover_form #stacktrace");
        var rqJobElement = dom.qs("#rangeland_cover_form #rq_job");
        var hintElement = dom.qs("#hint_build_rangeland_cover");
        var statusPanelElement = dom.qs("#rangeland_status_panel");
        var stacktracePanelElement = dom.qs("#rangeland_stacktrace_panel");
        var spinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;
        var rapSectionElement = dom.qs("[data-rangeland-rap-section]", formElement);

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        rangeland.form = formElement;
        rangeland.info = infoAdapter;
        rangeland.status = statusAdapter;
        rangeland.stacktrace = stacktraceAdapter;
        rangeland.rq_job = rqJobAdapter;
        rangeland.hint = hintAdapter;
        rangeland.statusPanelEl = statusPanelElement || null;
        rangeland.stacktracePanelEl = stacktracePanelElement || null;
        rangeland.statusSpinnerEl = spinnerElement || null;
        rangeland.infoElement = infoElement;
        rangeland.command_btn_id = "btn_build_rangeland_cover";

        rangeland.attach_status_stream(rangeland, {
            element: statusPanelElement,
            form: formElement,
            channel: "rangeland_cover",
            runId: window.runid || window.runId || null,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: spinnerElement
        });

        function resetCompletionSeen() {
            rangeland._completion_seen = false;
        }

        rangeland.poll_completion_event = "RANGELAND_COVER_BUILD_TASK_COMPLETED";
        resetCompletionSeen();

        function emit(eventName, payload) {
            if (!rangelandEvents || typeof rangelandEvents.emit !== "function") {
                return;
            }
            rangelandEvents.emit(eventName, payload || {});
        }

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg ? taskMsg + "..." : "");
            }
            rangeland.hideStacktrace();
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else if (stacktraceElement) {
                stacktraceElement.textContent = "";
            }
        }

        function setStatusMessage(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message || "");
            } else if (statusElement) {
                statusElement.textContent = message || "";
            }
        }

        function handleError(error, contextMessage) {
            var payload = toResponsePayload(http, error);
            rangeland.pushResponseStacktrace(rangeland, payload);
            setStatusMessage(contextMessage || payload.Error || "Request failed.");
        }

        rangeland.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        rangeland.showStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.show === "function") {
                stacktraceAdapter.show();
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = false;
                if (stacktraceElement.style.display === "none") {
                    stacktraceElement.style.removeProperty("display");
                }
            }
        };

        rangeland.showHideControls = function (mode) {
            if (!rapSectionElement) {
                return;
            }
            if (parseInteger(mode, 0) === 2) {
                dom.show(rapSectionElement);
            } else {
                dom.hide(rapSectionElement);
            }
        };

        rangeland.setMode = function (mode) {
            var state = readFormState(forms, formElement);
            var nextMode = parseInteger(mode, state.mode);
            var rapYearValue = state.rapYear;

            var previousMode = rangeland.mode;
            var previousRapYear = rangeland.rap_year;

            rangeland.mode = nextMode;
            rangeland.rap_year = rapYearValue;

            var rapYearLabel = rapYearValue === null || rapYearValue === undefined ? "" : String(rapYearValue);
            var taskMsg = "Setting Mode to " + nextMode + (rapYearLabel ? " (" + rapYearLabel + ")" : "");
            resetStatus(taskMsg);

            rangeland.showHideControls(nextMode);

            http.postJson(url_for_run("tasks/set_rangeland_cover_mode/"), {
                mode: nextMode,
                rap_year: rapYearValue
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    setStatusMessage(taskMsg + "... Success");
                } else if (response) {
                    rangeland.pushResponseStacktrace(rangeland, response);
                }
            }).catch(function (error) {
                handleError(error, "Failed to set rangeland cover mode.");
            });

            if (nextMode !== previousMode) {
                emit("rangeland:mode:changed", { mode: nextMode });
            }
            if (rapYearValue !== previousRapYear) {
                emit("rangeland:rap-year:changed", { year: rapYearValue });
            }
        };

        rangeland.handleModeChange = function (mode) {
            if (mode === undefined || mode === null) {
                rangeland.setMode();
                return;
            }
            rangeland.setMode(parseInteger(mode, 0));
        };

        rangeland.handleRapYearChange = function () {
            rangeland.setMode();
        };

        rangeland.build = function () {
            var state = readFormState(forms, formElement);
            var taskMsg = "Building rangeland cover";

            resetStatus(taskMsg);
            resetCompletionSeen();
            emit("rangeland:run:started", {
                mode: state.mode,
                defaults: state.defaults
            });

            if (typeof rangeland.connect_status_stream === "function") {
                rangeland.connect_status_stream(rangeland);
            }

            http.postJson(url_for_run("tasks/build_rangeland_cover/"), {
                rap_year: state.rapYear,
                defaults: state.defaults
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    var jobId = response.job_id || response.jobId || null;
                    var submittedMessage = jobId ? taskMsg + "... Submitted (job " + jobId + ")" : taskMsg + "... Submitted";
                    setStatusMessage(submittedMessage);
                    if (typeof rangeland.append_status_message === "function" && jobId) {
                        rangeland.append_status_message(rangeland, "build_rangeland_cover job submitted: " + jobId);
                    }
                    if (typeof rangeland.set_rq_job_id === "function") {
                        rangeland.poll_completion_event = "RANGELAND_COVER_BUILD_TASK_COMPLETED";
                        rangeland.set_rq_job_id(rangeland, jobId);
                    }
                } else if (response) {
                    rangeland.pushResponseStacktrace(rangeland, response);
                    emit("rangeland:run:failed", { error: response, mode: state.mode });
                    if (typeof rangeland.set_rq_job_id === "function") {
                        rangeland.set_rq_job_id(rangeland, null);
                    }
                    if (typeof rangeland.disconnect_status_stream === "function") {
                        rangeland.disconnect_status_stream(rangeland);
                    }
                    if (typeof rangeland.reset_status_spinner === "function") {
                        rangeland.reset_status_spinner(rangeland);
                    }
                }
            }).catch(function (error) {
                handleError(error, "Failed to build rangeland cover.");
                emit("rangeland:run:failed", { error: error, mode: state.mode });
                if (typeof rangeland.set_rq_job_id === "function") {
                    rangeland.set_rq_job_id(rangeland, null);
                }
                if (typeof rangeland.disconnect_status_stream === "function") {
                    rangeland.disconnect_status_stream(rangeland);
                }
                if (typeof rangeland.reset_status_spinner === "function") {
                    rangeland.reset_status_spinner(rangeland);
                }
            });
        };

        rangeland.report = function () {
            http.request(url_for_run("report/rangeland_cover/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                emit("rangeland:report:loaded", { html: html });
            }).catch(function (error) {
                handleError(error, "Failed to load rangeland cover report.");
                emit("rangeland:report:failed", { error: error });
            });
        };

        var baseTriggerEvent = rangeland.triggerEvent.bind(rangeland);
        rangeland.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "RANGELAND_COVER_BUILD_TASK_COMPLETED") {
                if (rangeland._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                rangeland._completion_seen = true;
                rangeland.disconnect_status_stream(rangeland);
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("rangeland_cover");
                } catch (err) {
                    console.warn("[RangelandCover] Failed to enable Subcatchment color map", err);
                }
                rangeland.report();
                emit("rangeland:run:completed", payload || {});
            }

            return baseTriggerEvent(eventName, payload);
        };

        function ensureDelegates() {
            if (rangeland._delegates) {
                return;
            }

            rangeland._delegates = [];

            rangeland._delegates.push(dom.delegate(formElement, "change", "[data-rangeland-role=\"mode\"]", function (event) {
                event.preventDefault();
                var modeAttr = this.getAttribute("data-rangeland-mode");
                var nextMode = modeAttr !== null ? modeAttr : this.value;
                rangeland.handleModeChange(nextMode);
            }));

            rangeland._delegates.push(dom.delegate(formElement, "change", "[data-rangeland-input=\"rap-year\"]", function () {
                rangeland.handleRapYearChange();
            }));

            rangeland._delegates.push(dom.delegate(formElement, "click", "[data-rangeland-action=\"build\"]", function (event) {
                event.preventDefault();
                rangeland.build();
            }));
        }

        ensureDelegates();

        var initialState = readFormState(forms, formElement);
        rangeland.mode = initialState.mode;
        rangeland.rap_year = initialState.rapYear;
        rangeland.showHideControls(initialState.mode);
        emit("rangeland:config:loaded", {
            mode: initialState.mode,
            rapYear: initialState.rapYear,
            defaults: initialState.defaults
        });

        var bootstrapState = {
            reportTriggered: false,
            modeApplied: false
        };

        rangeland.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "rangelandCover")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_rangeland_cover_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_rangeland_cover_rq")) {
                    var jobIdValue = jobIds.build_rangeland_cover_rq;
                    if (jobIdValue !== undefined && jobIdValue !== null) {
                        jobId = String(jobIdValue);
                    }
                }
            }
            if (typeof rangeland.set_rq_job_id === "function") {
                rangeland.set_rq_job_id(rangeland, jobId);
            }

            var mode = controllerContext.mode;
            if (mode === undefined && ctx.data && ctx.data.rangelandCover) {
                mode = ctx.data.rangelandCover.mode;
            }
            if (!bootstrapState.modeApplied && typeof rangeland.setMode === "function") {
                try {
                    rangeland.setMode(mode);
                } catch (err) {
                    console.warn("[RangelandCover] Failed to apply bootstrap mode", err);
                }
                bootstrapState.modeApplied = true;
            }

            var hasCovers = controllerContext.hasCovers;
            if (hasCovers === undefined && ctx.data && ctx.data.rangelandCover) {
                hasCovers = ctx.data.rangelandCover.hasCovers;
            }

            if (hasCovers && !bootstrapState.reportTriggered && typeof rangeland.report === "function") {
                rangeland.report();
                bootstrapState.reportTriggered = true;
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("rangeland_cover");
                } catch (err) {
                    console.warn("[RangelandCover] Failed to enable Subcatchment color map", err);
                }
            }

            return rangeland;
        };

        return rangeland;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.RangelandCover = RangelandCover;
}

/* ----------------------------------------------------------------------------
 * RAP Time Series
 * Doc: controllers_js/README.md — RAP Time Series Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var RAP_TS = (function () {
    "use strict";

    var instance;

    var FORM_ID = "rap_ts_form";
    var WS_CHANNEL = "rap_ts";
    var TASK_NAME = "rap:timeseries:run";
    var RUN_MESSAGE = "Acquiring RAP time series";
    var COMPLETE_MESSAGE = "RAP time series fetched and analyzed";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        hint: "#hint_build_rap_ts"
    };

    var ACTIONS = {
        run: '[data-rap-action="run"]'
    };

    var EVENT_NAMES = [
        "rap:schedule:loaded",
        "rap:timeseries:run:started",
        "rap:timeseries:run:completed",
        "rap:timeseries:run:error",
        "rap:timeseries:status",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.qs !== "function" || typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("RAP_TS controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("RAP_TS controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.isHttpError !== "function") {
            throw new Error("RAP_TS controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("RAP_TS controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
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
        function normalizeErrorValue(value) {
            if (!value) {
                return value;
            }
            if (typeof value === "object") {
                if (typeof value.Error === "string") {
                    return value.Error;
                }
                if (typeof value.message === "string") {
                    return value.message;
                }
                if (typeof value.detail === "string") {
                    return value.detail;
                }
                try {
                    return JSON.stringify(value);
                } catch (err) {
                    return String(value);
                }
            }
            return value;
        }

        function finalizePayload(payload) {
            if (!payload) {
                return { Success: false, Error: "Request failed" };
            }
            if (payload.Success === undefined) {
                payload = Object.assign({}, payload, { Success: false });
            }
            if (payload.Error && typeof payload.Error === "object") {
                payload = Object.assign({}, payload, { Error: normalizeErrorValue(payload.Error) });
            }
            return payload;
        }

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
                    payload = Object.assign({}, payload, { Error: normalizeErrorValue(fallback) });
                }
            }
            if (payload.StackTrace !== undefined || payload.Error !== undefined) {
                return finalizePayload(payload);
            }
        } else if (typeof body === "string" && body) {
            return finalizePayload({ Error: body });
        }

        if (error && typeof error === "object" && (error.Error !== undefined || error.StackTrace !== undefined)) {
            return finalizePayload(error);
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            return finalizePayload({ Error: normalizeErrorValue(detail) || "Request failed" });
        }

        return finalizePayload({ Error: normalizeErrorValue(error && error.message) || "Request failed" });
    }

    function parseSchedule(dom) {
        try {
            var node = dom.qs("[data-rap-schedule]");
            if (!node) {
                return [];
            }
            var raw = node.textContent || node.value || node.getAttribute("data-rap-schedule") || "";
            if (!raw) {
                return [];
            }
            var trimmed = raw.trim();
            if (!trimmed) {
                return [];
            }
            var parsed = JSON.parse(trimmed);
            return parsed;
        } catch (err) {
            console.warn("[RAP_TS] Unable to parse schedule payload", err);
            return [];
        }
    }

    function createInstance() {
        if (typeof controlBase !== "function") {
            throw new Error("RAP_TS controller requires controlBase helper.");
        }

        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = null;

        if (eventsApi && typeof eventsApi.createEmitter === "function") {
            var baseEmitter = eventsApi.createEmitter();
            emitter = typeof eventsApi.useEventMap === "function"
                ? eventsApi.useEventMap(EVENT_NAMES, baseEmitter)
                : baseEmitter;
        }

        var formElement = null;
        try {
            formElement = dom.qs(SELECTORS.form);
        } catch (err) {
            console.warn("[RAP_TS] Unable to resolve RAP time series form:", err);
        }

        var containerElement = null;
        if (formElement && typeof formElement.closest === "function") {
            containerElement = formElement.closest(".controller-section");
        }
        if (!containerElement) {
            containerElement = formElement || null;
        }

        var infoElement = formElement ? dom.qs(SELECTORS.info, formElement) : null;
        var statusElement = formElement ? dom.qs(SELECTORS.status, formElement) : null;
        var stacktraceElement = formElement ? dom.qs(SELECTORS.stacktrace, formElement) : null;
        var rqJobElement = formElement ? dom.qs(SELECTORS.rqJob, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var statusPanelElement = dom.qs("#rap_ts_status_panel");
        var stacktracePanelElement = dom.qs("#rap_ts_stacktrace_panel");
        var statusSpinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: formElement,
            container: containerElement,
            info: createLegacyAdapter(infoElement),
            status: createLegacyAdapter(statusElement),
            stacktrace: createLegacyAdapter(stacktraceElement),
            rq_job: createLegacyAdapter(rqJobElement),
            hint: createLegacyAdapter(hintElement),
            statusPanelEl: statusPanelElement,
            stacktracePanelEl: stacktracePanelElement,
            statusStream: null,
            statusSpinnerEl: statusSpinnerElement,
            command_btn_id: "btn_build_rap_ts",
            _delegates: [],
            _completion_seen: false,
            state: {
                schedule: [],
                lastSubmission: null
            }
        });
        var delegateRoot = controller.form || null;

        function detachDelegates() {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            delegateRoot = null;
        }

        function attachDelegates(force) {
            if (!controller.form) {
                detachDelegates();
                return;
            }
            if (!force && delegateRoot === controller.form && controller._delegates.length) {
                return;
            }
            detachDelegates();
            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.run, function (event) {
                event.preventDefault();
                controller.acquire();
            }));
            delegateRoot = controller.form;
        }

        function rebindDomReferences() {
            var updated = { formChanged: false };

            var nextForm = dom.qs(SELECTORS.form);
            if (nextForm !== controller.form) {
                controller.form = nextForm || null;
                formElement = controller.form || null;
                updated.formChanged = true;
            }

            if (controller.form) {
                if (!controller.container || !controller.container.isConnected) {
                    controller.container = typeof controller.form.closest === "function"
                        ? controller.form.closest(".controller-section") || controller.form
                        : controller.form;
                }
            } else {
                controller.container = null;
            }

            function syncAdapter(selector, current, assign) {
                var next = controller.form ? dom.qs(selector, controller.form) : null;
                if (next !== current) {
                    assign(next);
                }
            }

            syncAdapter(SELECTORS.info, infoElement, function (next) {
                infoElement = next;
                controller.info = createLegacyAdapter(infoElement);
            });
            syncAdapter(SELECTORS.status, statusElement, function (next) {
                statusElement = next;
                controller.status = createLegacyAdapter(statusElement);
            });
            syncAdapter(SELECTORS.stacktrace, stacktraceElement, function (next) {
                stacktraceElement = next;
                controller.stacktrace = createLegacyAdapter(stacktraceElement);
            });
            syncAdapter(SELECTORS.rqJob, rqJobElement, function (next) {
                rqJobElement = next;
                controller.rq_job = createLegacyAdapter(rqJobElement);
            });
            syncAdapter(SELECTORS.hint, hintElement, function (next) {
                hintElement = next;
                controller.hint = createLegacyAdapter(hintElement);
            });

            var nextStatusPanel = dom.qs("#rap_ts_status_panel");
            var nextStacktracePanel = dom.qs("#rap_ts_stacktrace_panel");
            var nextSpinner = nextStatusPanel ? nextStatusPanel.querySelector("#braille") : null;
            var shouldReattachStream = false;
            if (nextStatusPanel !== controller.statusPanelEl) {
                controller.statusPanelEl = nextStatusPanel;
                shouldReattachStream = true;
            }
            if (nextStacktracePanel !== controller.stacktracePanelEl) {
                controller.stacktracePanelEl = nextStacktracePanel;
                shouldReattachStream = true;
            }
            if (nextSpinner !== controller.statusSpinnerEl) {
                controller.statusSpinnerEl = nextSpinner;
                shouldReattachStream = true;
            }
            if (shouldReattachStream && typeof controller.attach_status_stream === "function") {
                controller.detach_status_stream(controller);
                controller.attach_status_stream(controller, {
                    element: controller.statusPanelEl,
                    channel: WS_CHANNEL,
                    runId: window.runid || window.runId || null,
                    stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
                    spinner: controller.statusSpinnerEl,
                    logLimit: 200
                });
            }

            return updated;
        }

        var baseTriggerEvent = controller.triggerEvent.bind(controller);

        function resetCompletionSeen() {
            controller._completion_seen = false;
        }

        function dispatchControlEvent(eventName, payload) {
            baseTriggerEvent(eventName, payload);
        }

        controller.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (controller.statusStream && typeof controller.statusStream.append === "function") {
                controller.statusStream.append(message, meta || null);
            }
            if (controller.status && typeof controller.status.html === "function") {
                controller.status.html(message);
            }
        };

        controller.setStatusMessage = controller.appendStatus;

        controller.attach_status_stream(controller, {
            element: controller.statusPanelEl,
            channel: WS_CHANNEL,
            runId: window.runid || window.runId || null,
            stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
            spinner: controller.statusSpinnerEl,
            logLimit: 200
        });

        controller.hideStacktrace = function () {
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        controller.report = function () {
            controller.setStatusMessage(COMPLETE_MESSAGE);
        };

        controller.handleRunCompletion = function (detail) {
            controller.report();
            controller.disconnect_status_stream(controller);
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rap:timeseries:run:completed", {
                    task: TASK_NAME,
                    jobId: controller.rq_job_id || null,
                    submission: controller.state.lastSubmission,
                    detail: detail || null
                });
                controller.events.emit("rap:timeseries:status", {
                    status: "completed",
                    task: TASK_NAME,
                    jobId: controller.rq_job_id || null,
                    submission: controller.state.lastSubmission,
                    detail: detail || null
                });
            }
            dispatchControlEvent("job:completed", {
                task: TASK_NAME,
                jobId: controller.rq_job_id || null,
                detail: detail || null,
                submission: controller.state.lastSubmission
            });
        };

        controller.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "RAP_TS_TASK_COMPLETED") {
                if (controller._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                controller._completion_seen = true;
                controller.handleRunCompletion(payload || null);
            }
            return baseTriggerEvent(eventName, payload);
        };

        controller.acquire = function (overridePayload) {
            if (!controller.form) {
                return;
            }

            resetCompletionSeen();
            controller.info.html("");
            controller.stacktrace.empty();
            controller.hideStacktrace();

            var submission = forms.serializeForm(controller.form, { format: "json" }) || {};
            if (overridePayload && typeof overridePayload === "object") {
                Object.keys(overridePayload).forEach(function (key) {
                    submission[key] = overridePayload[key];
                });
            }
            controller.state.lastSubmission = submission;

            controller.setStatusMessage(RUN_MESSAGE + "…");
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rap:timeseries:run:started", {
                    task: TASK_NAME,
                    payload: submission
                });
                controller.events.emit("rap:timeseries:status", {
                    status: "started",
                    task: TASK_NAME,
                    payload: submission
                });
            }
            dispatchControlEvent("job:started", {
                task: TASK_NAME,
                payload: submission
            });

            controller.connect_status_stream(controller);

            function handleError(result) {
                controller.pushResponseStacktrace(controller, result);
                controller.setStatusMessage("Failed to acquire RAP time series");
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("rap:timeseries:run:error", {
                        task: TASK_NAME,
                        payload: submission,
                        error: result
                    });
                    controller.events.emit("rap:timeseries:status", {
                        status: "error",
                        task: TASK_NAME,
                        payload: submission,
                        error: result
                    });
                }
                dispatchControlEvent("job:error", {
                    task: TASK_NAME,
                    payload: submission,
                    error: result
                });
                controller.disconnect_status_stream(controller);
            }

            http.postJson(url_for_run("rq/api/acquire_rap_ts"), submission, { form: controller.form }).then(function (response) {
                var body = response && response.body !== undefined ? response.body : response;
                var normalized = body || {};
                if (normalized.Success === true || normalized.success === true) {
                    var jobId = normalized.job_id || normalized.jobId || null;
                    var message = "fetch_and_analyze_rap_ts_rq job submitted";
                    if (jobId) {
                        message += ": " + jobId;
                    }
                    controller.setStatusMessage(message, { status: "queued", jobId: jobId });
                    controller.poll_completion_event = "RAP_TS_TASK_COMPLETED";
                    controller.set_rq_job_id(controller, jobId);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("rap:timeseries:status", {
                            status: "queued",
                            task: TASK_NAME,
                            payload: submission,
                            jobId: jobId,
                            response: normalized
                        });
                    }
                    return;
                }

                handleError(normalized);
            }).catch(function (error) {
                handleError(toResponsePayload(http, error));
            });
        };

        controller.dispose = function () {
            detachDelegates();
            controller.disconnect_status_stream(controller);
        };

        controller.hideStacktrace();

        controller.state.schedule = parseSchedule(dom);
        if (controller.events && typeof controller.events.emit === "function") {
            controller.events.emit("rap:schedule:loaded", {
                schedule: controller.state.schedule
            });
        }
        dispatchControlEvent("rap:schedule:loaded", {
            schedule: controller.state.schedule
        });

        attachDelegates();

        controller._rebindDomReferences = rebindDomReferences;
        controller._attachDelegates = attachDelegates;
        controller._detachDelegates = detachDelegates;

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var rebindResult = controller._rebindDomReferences();
            if (controller.form) {
                controller._attachDelegates(Boolean(rebindResult && rebindResult.formChanged));
            } else {
                controller._detachDelegates();
            }

            var nextSchedule = parseSchedule(dom) || [];
            var prevSchedule = controller.state && Array.isArray(controller.state.schedule)
                ? controller.state.schedule
                : [];
            var prevSerialized = JSON.stringify(prevSchedule);
            var nextSerialized = JSON.stringify(nextSchedule);
            if (nextSerialized !== prevSerialized) {
                controller.state.schedule = nextSchedule;
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("rap:schedule:loaded", { schedule: controller.state.schedule });
                }
                dispatchControlEvent("rap:schedule:loaded", { schedule: controller.state.schedule });
            }

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "fetch_and_analyze_rap_ts_rq")
                : null;
            if (!jobId && ctx.controllers && ctx.controllers.rapTs && ctx.controllers.rapTs.jobId) {
                jobId = ctx.controllers.rapTs.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "fetch_and_analyze_rap_ts_rq")) {
                    var value = jobIds.fetch_and_analyze_rap_ts_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }
            if (jobId) {
                resetCompletionSeen();
                controller.poll_completion_event = "RAP_TS_TASK_COMPLETED";
            }
            if (typeof controller.set_rq_job_id === "function") {
                controller.set_rq_job_id(controller, jobId);
            }
            return controller;
        };

        return controller;
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

if (typeof globalThis !== "undefined") {
    globalThis.RAP_TS = RAP_TS;
}

/* ----------------------------------------------------------------------------
 * Rhem
 * Doc: controllers_js/README.md — RHEM Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Rhem = (function () {
    var instance;

    var EVENT_NAMES = [
        "rhem:config:loaded",
        "rhem:run:started",
        "rhem:run:queued",
        "rhem:run:completed",
        "rhem:run:failed",
        "rhem:status:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Rhem controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Rhem controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Rhem controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Rhem controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function getActiveRunId() {
        return window.runid || window.runId || null;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var rhem = controlBase();

        var formElement = dom.ensureElement("#rhem_form", "RHEM form not found.");
        var infoElement = dom.qs("#rhem_form #info");
        var statusElement = dom.qs("#rhem_form #status");
        var stacktraceElement = dom.qs("#rhem_form #stacktrace");
        var rqJobElement = dom.qs("#rhem_form #rq_job");
        var hintElement = dom.qs("#hint_run_rhem");
        var statusPanelElement = dom.qs("#rhem_status_panel");
        var stacktracePanelElement = dom.qs("#rhem_stacktrace_panel");
        var statusSpinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;
        var resultsElement = dom.qs("#rhem-results");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        rhem.form = formElement;
        rhem.info = infoAdapter;
        rhem.status = statusAdapter;
        rhem.stacktrace = stacktraceAdapter;
        rhem.rq_job = rqJobAdapter;
        rhem.hint = hintAdapter;
        rhem.statusPanelEl = statusPanelElement || null;
        rhem.stacktracePanelEl = stacktracePanelElement || null;
        rhem.statusSpinnerEl = statusSpinnerElement || null;
        rhem.command_btn_id = "btn_run_rhem";
        rhem.statusStream = null;
        rhem.events = emitter;
        rhem._completion_seen = false;

        function renderStatus(message, meta) {
            if (!message) {
                return;
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.innerHTML = message;
            }
            emitter.emit("rhem:status:updated", {
                message: message,
                meta: meta || null
            });
        }

        function appendStatus(message, meta) {
            if (!message) {
                return;
            }
            if (rhem.statusStream && typeof rhem.statusStream.append === "function") {
                rhem.statusStream.append(message, meta || null);
                return;
            }
            renderStatus(message, meta);
        }
        rhem.appendStatus = appendStatus;

        function clearStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            rhem.clear_status_messages(rhem);
            if (taskMsg) {
                appendStatus(taskMsg + "...", { phase: "pending" });
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else if (stacktraceElement) {
                stacktraceElement.textContent = "";
            }
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
            rhem.hideStacktrace();
        }

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            rhem.pushResponseStacktrace(rhem, payload);
            emitter.emit("rhem:run:failed", {
                runId: getActiveRunId(),
                error: payload
            });
            rhem.triggerEvent("job:error", {
                task: "rhem:run",
                error: payload
            });
            rhem.disconnect_status_stream(rhem);
        }
        rhem.attach_status_stream(rhem, {
            element: rhem.statusPanelEl,
            channel: "rhem",
            runId: getActiveRunId(),
            stacktrace: rhem.stacktracePanelEl ? { element: rhem.stacktracePanelEl } : null,
            spinner: rhem.statusSpinnerEl,
            logLimit: 200,
            onAppend: function (detail) {
                renderStatus(detail ? detail.message : "", detail ? detail.meta : null);
                emitter.emit("rhem:status:updated", detail || {});
            },
            onTrigger: function (detail) {
                emitter.emit("rhem:status:updated", detail || {});
            }
        });

        emitter.emit("rhem:config:loaded", {
            hasStatusStream: Boolean(rhem.statusStream),
            runId: getActiveRunId()
        });

        function resetCompletionSeen() {
            rhem._completion_seen = false;
        }

        rhem.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function submitRunRequest() {
            var payload = forms.serializeForm(formElement, { format: "object" }) || {};
            http.postJson(url_for_run("rq/api/run_rhem_rq"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.Success === true || response.success === true)) {
                        var jobId = response.job_id || response.jobId || null;
                        appendStatus("run_rhem_rq job submitted: " + jobId, {
                            status: "queued"
                        });
                        rhem.poll_completion_event = "RHEM_RUN_TASK_COMPLETED";
                        rhem.set_rq_job_id(rhem, jobId);
                        emitter.emit("rhem:run:queued", {
                            runId: getActiveRunId(),
                            jobId: jobId
                        });
                        return;
                    }
                    var errorPayload = response || { Error: "RHEM job submission failed." };
                    rhem.pushResponseStacktrace(rhem, errorPayload);
                    emitter.emit("rhem:run:failed", {
                        runId: getActiveRunId(),
                        error: errorPayload
                    });
                    rhem.triggerEvent("job:error", {
                        task: "rhem:run",
                        error: errorPayload
                    });
                    rhem.disconnect_status_stream(rhem);
                })
                .catch(handleError);
        }

        rhem.run = function () {
            var taskMsg = "Submitting RHEM run";
            clearStatus(taskMsg);
            resetCompletionSeen();

            rhem.triggerEvent("job:started", {
                task: "rhem:run",
                runId: getActiveRunId()
            });
            emitter.emit("rhem:run:started", {
                runId: getActiveRunId(),
                jobId: null
            });

            rhem.connect_status_stream(rhem);

            submitRunRequest();
        };

        rhem.report = function () {
            var taskMsg = "Fetching Summary";
            clearStatus(taskMsg);

            http.request(url_for_run("report/rhem/results/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (resultsElement) {
                    resultsElement.innerHTML = html;
                }
            }).catch(handleError);

            http.request(url_for_run("report/rhem/run_summary/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                appendStatus(taskMsg + "... Success", { status: "completed" });

                if (window.Project && typeof window.Project.getInstance === "function") {
                    try {
                        var project = window.Project.getInstance();
                        if (project && typeof project.set_preferred_units === "function") {
                            project.set_preferred_units();
                        }
                    } catch (err) {
                        console.warn("[Rhem] Failed to set preferred units", err);
                    }
                }

                emitter.emit("rhem:run:completed", {
                    runId: getActiveRunId(),
                    jobId: rhem.rq_job_id || null
                });
                rhem.triggerEvent("job:completed", {
                    task: "rhem:run",
                    jobId: rhem.rq_job_id || null
                });
            }).catch(handleError);
        };

        var baseTriggerEvent = rhem.triggerEvent.bind(rhem);
        rhem.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "RHEM_RUN_TASK_COMPLETED") {
                if (rhem._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                rhem._completion_seen = true;
                rhem.disconnect_status_stream(rhem);
                rhem.report();
            }
            return baseTriggerEvent(eventName, payload);
        };

        dom.delegate(formElement, "click", "[data-rhem-action='run']", function (event) {
            event.preventDefault();
            rhem.run();
        });

        var bootstrapState = {
            reportLoaded: false
        };

        rhem.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "rhem")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_rhem_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_rhem_rq")) {
                    var value = jobIds.run_rhem_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof rhem.set_rq_job_id === "function") {
                if (jobId) {
                    rhem.poll_completion_event = "RHEM_RUN_TASK_COMPLETED";
                    resetCompletionSeen();
                }
                rhem.set_rq_job_id(rhem, jobId);
            }

            var rhemData = (ctx.data && ctx.data.rhem) || {};
            var hasRun = controllerContext.hasRun;
            if (hasRun === undefined) {
                hasRun = rhemData.hasRun;
            }

            if (hasRun && !bootstrapState.reportLoaded && typeof rhem.report === "function") {
                rhem.report();
                bootstrapState.reportLoaded = true;
            }

            return rhem;
        };

        return rhem;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.Rhem = Rhem;
}

/* ----------------------------------------------------------------------------
 * Run Sync Dashboard Controller
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var instance;

    function ensureHelpers() {
        var http = global.WCHttp;
        var dom = global.WCDom;
        var forms = global.WCForms;
        if (!http || typeof http.request !== "function") {
            throw new Error("RunSyncDashboard requires WCHttp helpers.");
        }
        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("RunSyncDashboard requires WCDom helpers.");
        }
        if (!forms || typeof forms.formToJSON !== "function") {
            throw new Error("RunSyncDashboard requires WCForms helpers.");
        }
        return { http: http, dom: dom, forms: forms };
    }

    function formatDate(value) {
        if (!value) {
            return "";
        }
        try {
            var date = typeof value === "string" ? new Date(value) : value;
            return date.toISOString();
        } catch (err) {
            return String(value);
        }
    }

    function createRow(cells) {
        var tr = document.createElement("tr");
        cells.forEach(function (cell) {
            var td = document.createElement("td");
            td.textContent = cell || "";
            tr.appendChild(td);
        });
        return tr;
    }

    function createEmptyRow(colspan, message) {
        var tr = document.createElement("tr");
        var td = document.createElement("td");
        td.colSpan = colspan;
        td.textContent = message || "No data.";
        tr.appendChild(td);
        return tr;
    }

    function setTableBody(tbody, rows) {
        tbody.innerHTML = "";
        rows.forEach(function (row) {
            tbody.appendChild(row);
        });
    }

    function normalizeRunLabel(runid) {
        return runid || "";
    }

    function escapeHtml(text) {
        if (!text) return "";
        var div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function showStacktrace(container, errorPayload) {
        var stacktraceEl = container.querySelector("#stacktrace");
        if (!stacktraceEl) {
            return;
        }
        stacktraceEl.innerHTML = "";
        stacktraceEl.style.display = "block";
        stacktraceEl.hidden = false;

        if (errorPayload.Error) {
            var heading = document.createElement("h6");
            heading.textContent = errorPayload.Error;
            stacktraceEl.appendChild(heading);
        }

        if (errorPayload.StackTrace) {
            var lines = Array.isArray(errorPayload.StackTrace) ? errorPayload.StackTrace : [errorPayload.StackTrace];
            var pre = document.createElement("pre");
            var small = document.createElement("small");
            small.className = "text-muted";
            small.textContent = lines.join("");
            pre.appendChild(small);
            stacktraceEl.appendChild(pre);
        }

        // Make sure the stacktrace panel is visible
        var panel = stacktraceEl.closest(".wc-card, .wc-panel, [class*=\"stacktrace\"]");
        if (panel) {
            panel.style.display = "block";
            panel.hidden = false;
        }
    }

    function createController() {
        var helpers = ensureHelpers();
        var http = helpers.http;
        var dom = helpers.dom;
        var forms = helpers.forms;
        var statusStream = null;

        function startStream(container, runId, channel) {
            if (!global.StatusStream || typeof global.StatusStream.attach !== "function") {
                return;
            }
            if (statusStream) {
                try {
                    statusStream.disconnect();
                } catch (err) {
                    // ignore
                }
            }
            var logElement = container.querySelector("#run_sync_status_log");
            var summaryElement = container.querySelector("#run_sync_summary");
            if (!runId || !channel || !logElement) {
                return;
            }
            statusStream = global.StatusStream.attach({
                element: container,
                logElement: logElement,
                runId: runId,
                channel: channel,
                onAppend: function (detail) {
                    var message = detail.message || "";

                    // Detect EXCEPTION_JSON message and display stacktrace
                    var exceptionMatch = message.match(/EXCEPTION_JSON\s+(.+)$/);
                    if (exceptionMatch) {
                        try {
                            var payload = JSON.parse(exceptionMatch[1]);
                            showStacktrace(container, payload);
                            if (summaryElement) {
                                summaryElement.innerHTML = '<div style="padding: 0.5em 0;"><strong style="color: var(--wc-error-fg, #721c24);">✗ Sync failed</strong></div>' +
                                    '<p>' + escapeHtml(payload.Error || 'Unknown error') + '</p>';
                            }
                        } catch (e) {
                            // JSON parse failed, ignore
                        }
                        return;
                    }

                    // Detect COMPLETE message and show link in summary panel
                    // Format: rq:<job_id> COMPLETE run_sync_rq(<runid>, <config>)
                    var completeMatch = message.match(/COMPLETE run_sync_rq\(([^,]+),\s*([^)]+)\)/);
                    if (completeMatch && summaryElement) {
                        var syncedRunId = completeMatch[1].trim();
                        var syncedConfig = completeMatch[2].trim();
                        var runUrl = "/weppcloud/runs/" + encodeURIComponent(syncedRunId) + "/" + encodeURIComponent(syncedConfig) + "/";
                        summaryElement.innerHTML = '<div style="padding: 0.5em 0;"><strong style="color: var(--wc-success-fg, #155724);">✓ Sync complete!</strong></div>' +
                            '<a href="' + runUrl + '" class="pure-button pure-button-primary">Open run →</a>';
                    }
                }
            });
        }

        function renderJobs(container, jobs) {
            var tbody = container.querySelector("#run_sync_jobs_table tbody");
            if (!tbody) {
                return;
            }
            if (!jobs || jobs.length === 0) {
                setTableBody(tbody, [createEmptyRow(7, "No run sync jobs found.")]);
                return;
            }
            var rows = jobs.map(function (job) {
                return createRow([
                    job.id || "",
                    normalizeRunLabel(job.runid),
                    job.source_host || "",
                    job.status || "",
                    job.job_status || "",
                    formatDate(job.started_at || job.enqueued_at),
                    formatDate(job.ended_at),
                ]);
            });
            setTableBody(tbody, rows);
        }

        function renderMigrations(container, records) {
            var tbody = container.querySelector("#run_sync_migrations_table tbody");
            if (!tbody) {
                return;
            }
            if (!records || records.length === 0) {
                setTableBody(tbody, [createEmptyRow(7, "No recorded imports yet.")]);
                return;
            }
            var rows = records.map(function (record) {
                return createRow([
                    normalizeRunLabel(record.runid),
                    record.source_host || "",
                    record.owner_email || "",
                    record.last_status || "",
                    record.version_at_pull !== undefined && record.version_at_pull !== null ? String(record.version_at_pull) : "",
                    formatDate(record.pulled_at || record.updated_at),
                    record.local_path || "",
                ]);
            });
            setTableBody(tbody, rows);
        }

        function buildPayload(form, defaults) {
            var payload = forms.formToJSON(form);
            return {
                source_host: payload.source_host || defaults.defaultHost,
                runid: payload.runid ? String(payload.runid).trim() : "",
                target_root: payload.target_root || defaults.defaultRoot,
                owner_email: payload.owner_email || null,
                run_migrations: payload.run_migrations !== false,
                archive_before: payload.archive_before === true
            };
        }

        function bootstrap() {
            var container = dom.qs("[data-controller=\"run-sync-dashboard\"]");
            if (!container) {
                return;
            }
            if (container.__runSyncDashboardInit) {
                return;
            }
            container.__runSyncDashboardInit = true;

            var configEl = container.querySelector("#run_sync_config");
            var dataset = (configEl && configEl.dataset) || {};
            var apiUrl = dataset.apiUrl || "/rq/api/run-sync";
            var statusUrl = dataset.statusUrl || "/rq/api/run-sync/status";
            var defaults = {
                defaultHost: dataset.defaultHost || "wepp.cloud",
                defaultRoot: dataset.defaultRoot || "",
            };
            var statusChannel = dataset.statusChannel || "run_sync";

            var form = container.querySelector("#run_sync_form");
            var refreshButton = container.querySelector("#run_sync_refresh");
            var statusLog = container.querySelector("#run_sync_status_log");

            function setStatusMessage(message) {
                if (!statusLog) {
                    return;
                }
                statusLog.textContent = (message || "") + "\n";
            }

            function refreshStatus() {
                http.getJson(statusUrl)
                    .then(function (payload) {
                        renderJobs(container, payload.jobs || []);
                        renderMigrations(container, payload.migrations || []);
                    })
                    .catch(function (error) {
                        setStatusMessage("Status refresh failed: " + (error.message || error));
                    });
            }

            function handleSubmit(event) {
                event.preventDefault();
                if (!form) {
                    return;
                }
                var payload = buildPayload(form, defaults);
                if (!payload.runid) {
                    setStatusMessage("runid is required.");
                    return;
                }
                setStatusMessage("Enqueueing run sync job...");
                http.postJson(apiUrl, payload)
                    .then(function (response) {
                        setStatusMessage("Job enqueued: " + (response.job_id || ""));
                        startStream(container, payload.runid, statusChannel);
                        refreshStatus();
                    })
                    .catch(function (error) {
                        setStatusMessage("Run sync submit failed: " + (error.message || error));
                        if (global.console && console.error) {
                            console.error(error);
                        }
                    });
            }

            if (form) {
                form.addEventListener("submit", handleSubmit);
            }
            if (refreshButton) {
                refreshButton.addEventListener("click", function (event) {
                    event.preventDefault();
                    refreshStatus();
                });
            }

            refreshStatus();
        }

        return {
            bootstrap: bootstrap,
        };
    }

    var api = {
        getInstance: function () {
            if (!instance) {
                instance = createController();
            }
            return instance;
        },
        bootstrap: function () {
            return api.getInstance().bootstrap();
        },
    };

    global.RunSyncDashboard = api;

    document.addEventListener("DOMContentLoaded", function () {
        try {
            api.bootstrap();
        } catch (err) {
            if (global.console && console.error) {
                console.error("RunSyncDashboard bootstrap failed:", err);
            }
        }
    });
}(typeof window !== "undefined" ? window : this));

/* ----------------------------------------------------------------------------
 * Soil
 * ----------------------------------------------------------------------------
 */
var Soil = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Soil controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Soil controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Soil controller requires WCHttp helpers.");
        }

        return { dom: dom, forms: forms, http: http };
    }

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

    function parseInteger(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;

        var soil = controlBase();

        var formElement = dom.ensureElement("#soil_form", "Soil form not found.");
        var infoElement = dom.qs("#soil_form #info");
        var statusElement = dom.qs("#soil_form #status");
        var stacktraceElement = dom.qs("#soil_form #stacktrace");
        var rqJobElement = dom.qs("#soil_form #rq_job");
        var hintElement = dom.qs("#soil_form #hint_build_soil");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        soil.form = formElement;
        soil.info = infoAdapter;
        soil.status = statusAdapter;
        soil.stacktrace = stacktraceAdapter;
        soil.rq_job = rqJobAdapter;
        soil.command_btn_id = "btn_build_soil";
        soil.hint = hintAdapter;
        soil.statusPanelEl = dom.qs("#soil_status_panel");
        soil.stacktracePanelEl = dom.qs("#soil_stacktrace_panel");
        var spinnerElement = soil.statusPanelEl ? soil.statusPanelEl.querySelector("#braille") : null;

        soil.attach_status_stream(soil, {
            element: soil.statusPanelEl,
            channel: "soils",
            stacktrace: soil.stacktracePanelEl ? { element: soil.stacktracePanelEl } : null,
            spinner: spinnerElement
        });

        function resetCompletionSeen() {
            soil._completion_seen = false;
        }

        soil.poll_completion_event = "SOILS_BUILD_TASK_COMPLETED";
        resetCompletionSeen();

        var modePanels = [
            dom.qs("#soil_mode0_controls"),
            dom.qs("#soil_mode1_controls"),
            dom.qs("#soil_mode2_controls"),
            dom.qs("#soil_mode3_controls"),
            dom.qs("#soil_mode4_controls")
        ];

        var baseTriggerEvent = soil.triggerEvent.bind(soil);
        soil.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "SOILS_BUILD_TASK_COMPLETED") {
                if (soil._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                soil._completion_seen = true;
                soil.disconnect_status_stream(soil);
                soil.report();
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("dom_soil");
                } catch (err) {
                    console.warn("[Soil] Failed to enable Subcatchment color map", err);
                }
            }

            return baseTriggerEvent(eventName, payload);
        };

        soil.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function resetStatus(taskMsg) {
            soil.reset_panel_state(soil, { taskMessage: taskMsg });
        }

        function handleError(error) {
            soil.pushResponseStacktrace(soil, toResponsePayload(http, error));
        }

        soil.handleModeChange = function (mode) {
            if (mode === undefined) {
                soil.setMode();
                return;
            }
            soil.setMode(parseInteger(mode, 0));
        };

        soil.handleSingleSelectionInput = function () {
            soil.setMode();
        };

        soil.handleDbSelectionChange = function () {
            soil.setMode();
        };

        soil.build = function () {
            var taskMsg = "Building soil";
            resetStatus(taskMsg);
            resetCompletionSeen();

            soil.connect_status_stream(soil);

            var params = forms.serializeForm(formElement, { format: "url" });

            http.postForm(url_for_run("rq/api/build_soils"), params, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        soil.append_status_message(soil, "build_soils_rq job submitted: " + response.job_id);
                        soil.poll_completion_event = "SOILS_BUILD_TASK_COMPLETED";
                        soil.set_rq_job_id(soil, response.job_id);
                    } else if (response) {
                        soil.pushResponseStacktrace(soil, response);
                    }
                })
                .catch(handleError);
        };

        soil.report = function () {
            http.request(url_for_run("report/soils/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
            }).catch(handleError);
        };

        soil.restore = function (mode) {
            var modeValue = parseInteger(mode, 0);
            var radio = document.getElementById("soil_mode" + modeValue);
            if (radio) {
                radio.checked = true;
            }
            soil.showHideControls(modeValue);
        };

        soil.set_ksflag = function (state) {
            var taskMsg = "Setting ksflag (" + state + ")";
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_soils_ksflag/"), { ksflag: Boolean(state) }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        soil.append_status_message(soil, taskMsg + "... Success");
                    } else if (response) {
                        soil.pushResponseStacktrace(soil, response);
                    }
                })
                .catch(handleError);
        };

        soil.set_disturbed_sol_ver = function (value) {
            if (value === undefined || value === null || value === "") {
                return;
            }

            var taskMsg = "Setting disturbed sol_ver to " + value;
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_disturbed_sol_ver/"), { sol_ver: value }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        soil.append_status_message(soil, taskMsg + "... Success");
                    } else if (response) {
                        soil.pushResponseStacktrace(soil, response);
                    }
                })
                .catch(handleError);
        };

        soil.setMode = function (mode) {
            var payload = forms.serializeForm(formElement, { format: "json" }) || {};
            var resolvedMode = mode;
            if (resolvedMode === undefined || resolvedMode === null) {
                resolvedMode = parseInteger(payload.soil_mode, 0);
            }
            resolvedMode = parseInteger(resolvedMode, 0);

            var singleSelectionRaw = payload.soil_single_selection;
            var singleDbSelection = payload.soil_single_dbselection || null;
            var singleSelection = singleSelectionRaw === undefined || singleSelectionRaw === null || singleSelectionRaw === ""
                ? null
                : parseInteger(singleSelectionRaw, null);

            soil.mode = resolvedMode;

            var taskMsg = "Setting Mode to " + resolvedMode;
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_soil_mode/"), {
                mode: resolvedMode,
                soil_single_selection: singleSelection,
                soil_single_dbselection: singleDbSelection
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    soil.append_status_message(soil, taskMsg + "... Success");
                } else if (response) {
                    soil.pushResponseStacktrace(soil, response);
                }
            }).catch(handleError);

            soil.showHideControls(resolvedMode);
        };

        soil.showHideControls = function (mode) {
            var numericMode = parseInteger(mode, -1);

            if (numericMode === -1) {
                modePanels.forEach(function (panel) {
                    if (panel) {
                        dom.hide(panel);
                    }
                });
                return;
            }

            if (numericMode < 0 || numericMode >= modePanels.length) {
                throw new Error("ValueError: unknown mode");
            }

            modePanels.forEach(function (panel, index) {
                if (!panel) {
                    return;
                }
                if (index === numericMode) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
        };

        var modeInputs = formElement.querySelectorAll('input[name="soil_mode"]');
        Array.prototype.forEach.call(modeInputs, function (input) {
            input.addEventListener("change", function (event) {
                soil.handleModeChange(event.target.value);
            });
        });

        var singleSelectionInput = document.getElementById("soil_single_selection");
        if (singleSelectionInput) {
            singleSelectionInput.addEventListener("input", soil.handleSingleSelectionInput);
            singleSelectionInput.addEventListener("change", soil.handleSingleSelectionInput);
        }

        var dbSelectionInput = document.getElementById("soil_single_dbselection");
        if (dbSelectionInput) {
            dbSelectionInput.addEventListener("change", soil.handleDbSelectionChange);
        }

        var ksflagCheckbox = document.getElementById("checkbox_run_flowpaths");
        if (ksflagCheckbox) {
            ksflagCheckbox.addEventListener("change", function (event) {
                soil.set_ksflag(event.target.checked);
            });
        }

        var solVerSelect = document.getElementById("sol_ver");
        if (solVerSelect) {
            solVerSelect.addEventListener("change", function (event) {
                soil.set_disturbed_sol_ver(event.target.value);
            });
        }

        var buildButton = document.getElementById("btn_build_soil");
        if (buildButton) {
            buildButton.addEventListener("click", function (event) {
                event.preventDefault();
                soil.build();
            });
        }

        var bootstrapState = {
            buildTriggered: false
        };

        soil.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "soil")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_soils_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_soils_rq")) {
                    var value = jobIds.build_soils_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof soil.set_rq_job_id === "function") {
                soil.set_rq_job_id(soil, jobId);
            }

            var settings = (ctx.data && ctx.data.soils) || {};
            var restoreMode = controllerContext.mode !== undefined && controllerContext.mode !== null
                ? controllerContext.mode
                : settings.mode;

            if (typeof soil.restore === "function") {
                soil.restore(restoreMode);
            }

            var dbSelection = controllerContext.singleDbSelection;
            if (dbSelection === undefined) {
                dbSelection = settings.singleDbSelection;
            }
            if (dbSelection === undefined) {
                dbSelection = settings.single_dbselection;
            }

            if (dbSelection !== undefined && dbSelection !== null) {
                var dbSelectElement = document.getElementById("soil_single_dbselection");
                if (dbSelectElement) {
                    dbSelectElement.value = String(dbSelection);
                }
            }

            var hasSoils = controllerContext.hasSoils;
            if (hasSoils === undefined) {
                hasSoils = settings.hasSoils;
            }
            if (hasSoils && !bootstrapState.buildTriggered && typeof soil.triggerEvent === "function") {
                soil.triggerEvent("SOILS_BUILD_TASK_COMPLETED");
                bootstrapState.buildTriggered = true;
            }

            return soil;
        };

        return soil;
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

if (typeof globalThis !== "undefined") {
    globalThis.Soil = Soil;
}

/* ----------------------------------------------------------------------------
 * Team
 * Doc: controllers_js/README.md — Team Controller Reference (2026 helper migration)
 * ----------------------------------------------------------------------------
 */
var Team = (function () {
    "use strict";

    var instance;

    var FORM_SELECTOR = "#team_form";
    var MEMBERS_CONTAINER_SELECTOR = "#team-info";
    var EMAIL_FIELD_SELECTOR = '[data-team-field="email"]';
    var ACTION_SELECTOR = "[data-team-action]";
    var STATUS_PANEL_SELECTOR = "#team_status_panel";
    var STACKTRACE_PANEL_SELECTOR = "#team_stacktrace_panel";
    var HINT_SELECTOR = "#hint_run_team";

    var EVENT_NAMES = [
        "team:list:loading",
        "team:list:loaded",
        "team:list:failed",
        "team:invite:started",
        "team:invite:sent",
        "team:invite:failed",
        "team:member:remove:started",
        "team:member:removed",
        "team:member:remove:failed",
        "team:status:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" || typeof dom.ensureElement !== "function") {
            throw new Error("Team controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Team controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.request !== "function") {
            throw new Error("Team controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("Team controller requires WCEvents helpers.");
        }

        return {
            dom: dom,
            forms: forms,
            http: http,
            events: events
        };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return null;
        }
        return {
            text: function (value) {
                element.textContent = value === undefined || value === null ? "" : String(value);
            },
            html: function (html) {
                element.innerHTML = html === undefined || html === null ? "" : String(html);
            },
            append: function (html) {
                if (html === undefined || html === null) {
                    return;
                }
                if (typeof html === "string") {
                    element.insertAdjacentHTML("beforeend", html);
                    return;
                }
                if (typeof window.Node !== "undefined" && html instanceof window.Node) {
                    element.appendChild(html);
                }
            },
            show: function () {
                element.hidden = false;
                element.style.removeProperty("display");
            },
            hide: function () {
                element.hidden = true;
                element.style.display = "none";
            },
            empty: function () {
                element.textContent = "";
            }
        };
    }

    function toResponsePayload(http, error) {
        function normalizeErrorValue(value) {
            if (!value) {
                return value;
            }
            if (typeof value === "object") {
                if (typeof value.Error === "string") {
                    return value.Error;
                }
                if (typeof value.message === "string") {
                    return value.message;
                }
                if (typeof value.detail === "string") {
                    return value.detail;
                }
                try {
                    return JSON.stringify(value);
                } catch (err) {
                    return String(value);
                }
            }
            return value;
        }

        function finalizePayload(payload) {
            if (!payload) {
                return { Success: false, Error: "Request failed" };
            }
            if (payload.Success === undefined) {
                payload = Object.assign({}, payload, { Success: false });
            }
            if (payload.Error && typeof payload.Error === "object") {
                payload = Object.assign({}, payload, { Error: normalizeErrorValue(payload.Error) });
            }
            return payload;
        }

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
                    payload = Object.assign({}, payload, { Error: normalizeErrorValue(fallback) });
                }
            }
            if (payload.StackTrace !== undefined || payload.Error !== undefined) {
                return finalizePayload(payload);
            }
        } else if (typeof body === "string" && body) {
            return finalizePayload({ Error: body });
        }

        if (error && typeof error === "object" && (error.Error !== undefined || error.StackTrace !== undefined)) {
            return finalizePayload(error);
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            return finalizePayload({ Error: normalizeErrorValue(detail) || "Request failed" });
        }

        return finalizePayload({ Error: normalizeErrorValue(error && error.message) || "Request failed" });
    }

    function getActiveRunId() {
        return window.runid || window.runId || null;
    }

    function setButtonPending(button, isPending) {
        if (!button) {
            return;
        }
        if (isPending) {
            button.dataset.teamPrevDisabled = button.disabled ? "true" : "false";
            button.dataset.teamPending = "true";
            button.disabled = true;
            return;
        }
        delete button.dataset.teamPending;
        if (button.dataset.jobDisabled === "true") {
            return;
        }
        if (button.dataset.teamPrevDisabled !== "true") {
            button.disabled = false;
        }
        delete button.dataset.teamPrevDisabled;
    }

    function readEmailValue(forms, form) {
        var payload = {};
        try {
            payload = forms.serializeForm(form, { format: "object" }) || {};
        } catch (err) {
            payload = {};
        }
        var raw = Object.prototype.hasOwnProperty.call(payload, "email") ? payload.email : payload["adduser-email"];
        if (Array.isArray(raw)) {
            raw = raw[0];
        }
        if (raw === undefined || raw === null) {
            return "";
        }
        return String(raw).trim();
    }

    function normaliseHtmlContent(content) {
        if (content === undefined || content === null) {
            return "";
        }
        if (typeof content === "string") {
            return content;
        }
        if (typeof content === "object" && content !== null && content.html !== undefined) {
            return String(content.html);
        }
        return String(content);
    }

    function normaliseUserId(value) {
        if (value === undefined || value === null) {
            return null;
        }
        var candidate = value;
        if (Array.isArray(candidate)) {
            candidate = candidate[0];
        }
        if (typeof candidate === "string") {
            candidate = candidate.trim();
            if (candidate.length === 0) {
                return null;
            }
        }
        var parsed = parseInt(candidate, 10);
        if (Number.isNaN(parsed)) {
            return null;
        }
        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var team = controlBase();

        var formElement = dom.ensureElement(FORM_SELECTOR, "Team form not found.");
        var infoElement = dom.qs("#team_form #info");
        var statusElement = dom.qs("#team_form #status");
        var stacktraceElement = dom.qs("#team_form #stacktrace");
        var hintElement = dom.qs(HINT_SELECTOR);
        var statusPanelElement = dom.qs(STATUS_PANEL_SELECTOR);
        var stacktracePanelElement = dom.qs(STACKTRACE_PANEL_SELECTOR);
        var membersElement = dom.qs(MEMBERS_CONTAINER_SELECTOR, formElement);
        if (!membersElement) {
            throw new Error("Team members container not found.");
        }
        var emailInput = dom.qs(EMAIL_FIELD_SELECTOR, formElement);

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        team.form = formElement;
        team.info = infoAdapter;
        team.status = statusAdapter;
        team.stacktrace = stacktraceAdapter;
        team.hint = hintAdapter;
        team.statusPanelEl = statusPanelElement || null;
        team.stacktracePanelEl = stacktracePanelElement || null;
        team.statusSpinnerEl = team.statusPanelEl ? team.statusPanelEl.querySelector("#braille") : null;
        team.command_btn_id = "btn_adduser";
        team.events = emitter;
        team.membersElement = membersElement;
        team.emailInput = emailInput || null;
        team._delegates = [];

        team.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (team.statusStream && typeof team.statusStream.append === "function") {
                team.statusStream.append(message, meta || null);
            } else if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.innerHTML = message;
            }
            emitter.emit("team:status:updated", {
                message: message,
                meta: meta || null
            });
        };

        team.hideStacktrace = function () {
            if (team.stacktrace && typeof team.stacktrace.hide === "function") {
                team.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                if (typeof dom.hide === "function") {
                    dom.hide(stacktraceElement);
                } else {
                    stacktraceElement.hidden = true;
                    stacktraceElement.style.display = "none";
                }
            }
        };

        function attachStatusChannel() {
            team.attach_status_stream(team, {
                element: team.statusPanelEl,
                form: formElement,
                channel: "team",
                runId: getActiveRunId(),
                stacktrace: team.stacktracePanelEl ? { element: team.stacktracePanelEl } : null,
                spinner: team.statusSpinnerEl,
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        team.triggerEvent(detail.event, detail);
                    }
                    emitter.emit("team:status:updated", detail || {});
                }
            });
        }

        function refreshMembers(options) {
            var opts = options || {};
            if (team.isAuthenticated === false) {
                if (!opts.silentStatus) {
                    team.appendStatus("Sign in to view collaborators.");
                }
                return Promise.resolve("");
            }
            emitter.emit("team:list:loading");
            return http.request(url_for_run("report/users/"), {
                method: "GET",
                params: { _: Date.now() }
            }).then(function (result) {
                var body = result && result.body !== undefined ? result.body : result;
                var html = normaliseHtmlContent(body);
                membersElement.innerHTML = html;
                emitter.emit("team:list:loaded", {
                    html: html,
                    response: body
                });
                if (!opts.silentStatus) {
                    team.appendStatus("Team roster updated.");
                }
                return html;
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                if (!payload.Error) {
                    payload.Error = "Unable to load collaborator list.";
                }
                team.appendStatus(payload.Error);
                team.pushResponseStacktrace(team, payload);
                emitter.emit("team:list:failed", {
                    error: payload
                });
                throw payload;
            });
        }

        function inviteCollaborator(email, options) {
            var opts = options || {};
            var button = opts.button || null;
            var trimmed = (email || "").trim();

            if (!trimmed) {
                var validationError = { Error: "Email address is required." };
                team.appendStatus(validationError.Error);
                emitter.emit("team:invite:failed", {
                    email: "",
                    error: validationError
                });
                return Promise.resolve(null);
            }

            team.hideStacktrace();
            setButtonPending(button, true);
            emitter.emit("team:invite:started", { email: trimmed });
            team.triggerEvent("job:started", { task: "team:adduser", email: trimmed });

            return http.postJson(url_for_run("tasks/adduser/"), { email: trimmed }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    if (!response || response.Success !== true) {
                        throw response || { Error: "Collaborator invite failed." };
                    }
                    var content = response.Content || response.content || {};
                    var alreadyMember = Boolean(content.already_member);
                    var statusMessage = alreadyMember ? "Collaborator already has access." : "Collaborator invited.";
                    team.appendStatus(statusMessage, { alreadyMember: alreadyMember });
                    if (team.emailInput) {
                        team.emailInput.value = "";
                    }
                    emitter.emit("team:invite:sent", {
                        email: trimmed,
                        response: response,
                        alreadyMember: alreadyMember
                    });
                    team.triggerEvent("TEAM_ADDUSER_TASK_COMPLETED", {
                        email: trimmed,
                        response: response,
                        alreadyMember: alreadyMember
                    });
                    team.triggerEvent("job:completed", {
                        task: "team:adduser",
                        email: trimmed,
                        response: response
                    });
                    return refreshMembers({ silentStatus: true }).then(function () {
                        return response;
                    });
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    if (!payload.Error) {
                        payload.Error = "Collaborator invite failed.";
                    }
                    team.appendStatus(payload.Error);
                    team.pushResponseStacktrace(team, payload);
                    emitter.emit("team:invite:failed", {
                        email: trimmed,
                        error: payload
                    });
                    team.triggerEvent("job:error", {
                        task: "team:adduser",
                        email: trimmed,
                        error: payload
                    });
                    throw payload;
                })
                .finally(function () {
                    setButtonPending(button, false);
                });
        }

        function removeMemberById(userId, options) {
            var opts = options || {};
            var button = opts.button || null;
            var normalisedId = normaliseUserId(userId);

            if (normalisedId === null) {
                var validationError = { Error: "user_id is required." };
                team.appendStatus(validationError.Error);
                emitter.emit("team:member:remove:failed", {
                    userId: userId,
                    error: validationError
                });
                return Promise.resolve(null);
            }

            team.hideStacktrace();
            setButtonPending(button, true);
            emitter.emit("team:member:remove:started", { userId: normalisedId });
            team.triggerEvent("job:started", { task: "team:removeuser", userId: normalisedId });

            return http.postJson(url_for_run("tasks/removeuser/"), { user_id: normalisedId }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    if (!response || response.Success !== true) {
                        throw response || { Error: "Collaborator removal failed." };
                    }
                    var content = response.Content || response.content || {};
                    var alreadyRemoved = Boolean(content.already_removed);
                    var statusMessage = alreadyRemoved ? "Collaborator already removed." : "Collaborator removed.";
                    team.appendStatus(statusMessage, { alreadyRemoved: alreadyRemoved });
                    emitter.emit("team:member:removed", {
                        userId: normalisedId,
                        response: response,
                        alreadyRemoved: alreadyRemoved
                    });
                    team.triggerEvent("TEAM_REMOVEUSER_TASK_COMPLETED", {
                        user_id: normalisedId,
                        response: response,
                        alreadyRemoved: alreadyRemoved
                    });
                    team.triggerEvent("job:completed", {
                        task: "team:removeuser",
                        userId: normalisedId,
                        response: response
                    });
                    return refreshMembers({ silentStatus: true }).then(function () {
                        return response;
                    });
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    if (!payload.Error) {
                        payload.Error = "Collaborator removal failed.";
                    }
                    team.appendStatus(payload.Error);
                    team.pushResponseStacktrace(team, payload);
                    emitter.emit("team:member:remove:failed", {
                        userId: normalisedId,
                        error: payload
                    });
                    team.triggerEvent("job:error", {
                        task: "team:removeuser",
                        userId: normalisedId,
                        error: payload
                    });
                    throw payload;
                })
                .finally(function () {
                    setButtonPending(button, false);
                });
        }

        function handleAction(event, target) {
            if (!target || !target.dataset) {
                return;
            }
            var action = target.dataset.teamAction;
            if (!action) {
                return;
            }
            if (action === "invite") {
                event.preventDefault();
                team.inviteFromForm({ button: target });
                return;
            }
            if (action === "remove") {
                event.preventDefault();
                var userIdValue = target.getAttribute("data-team-user-id") || target.dataset.teamUserId;
                team.removeMemberById(userIdValue, { button: target });
            }
        }

        team._delegates.push(dom.delegate(formElement, "click", ACTION_SELECTOR, handleAction));

        team.refreshMembers = refreshMembers;
        team.inviteCollaborator = function (email, options) {
            return inviteCollaborator(email, options || {});
        };
        team.inviteFromForm = function (options) {
            var btn = options && options.button ? options.button : null;
            var email = readEmailValue(forms, formElement);
            return inviteCollaborator(email, { button: btn });
        };
        team.adduser = function (email) {
            return inviteCollaborator(email || "", {});
        };
        team.adduser_click = function () {
            var button = dom.qs('[data-team-action="invite"]', formElement) || null;
            return team.inviteFromForm({ button: button });
        };
        team.removeMemberById = function (userId, options) {
            return removeMemberById(userId, options || {});
        };
        team.removeuser = function (userId) {
            return removeMemberById(userId, {});
        };
        team.report = function () {
            return refreshMembers({});
        };

        attachStatusChannel();

        var bootstrapState = {
            listenersBound: false,
            initialReport: false
        };

        team.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var user = ctx.user || {};
            var form = team.form;
            team.isAuthenticated = Boolean(user.isAuthenticated);

            if (form && !bootstrapState.listenersBound && typeof form.addEventListener === "function") {
                form.addEventListener("TEAM_ADDUSER_TASK_COMPLETED", function () {
                    team.report();
                });
                form.addEventListener("TEAM_REMOVEUSER_TASK_COMPLETED", function () {
                    team.report();
                });
                bootstrapState.listenersBound = true;
            }

            if (user.isAuthenticated && !bootstrapState.initialReport) {
                team.report();
                bootstrapState.initialReport = true;
            }

            return team;
        };

        return team;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.Team = Team;
}

/* ----------------------------------------------------------------------------
 * Theme Switcher
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var STORAGE_KEY = "wc-theme";
    var SELECTOR = "[data-theme-select]";
    var root = global.document ? global.document.documentElement : null;

    function emitThemeChange(theme) {
        if (!global.document) {
            return;
        }
        var detail = { theme: theme && theme !== "" ? theme : "default" };
        global.document.dispatchEvent(new CustomEvent("wc-theme:change", { detail: detail }));
    }

    function getStoredTheme() {
        try {
            return global.localStorage.getItem(STORAGE_KEY);
        } catch (err) {
            return null;
        }
    }

    function storeTheme(theme) {
        try {
            if (!theme || theme === "default") {
                global.localStorage.removeItem(STORAGE_KEY);
            } else {
                global.localStorage.setItem(STORAGE_KEY, theme);
            }
        } catch (err) {
            // ignore storage errors (private mode, etc.)
        }
    }

    function applyTheme(theme) {
        if (!root) {
            return;
        }
        if (!theme || theme === "default") {
            root.removeAttribute("data-theme");
        } else {
            root.setAttribute("data-theme", theme);
        }
    }

    function syncSelects(theme) {
        var value = theme && theme !== "" ? theme : "default";
        var selects = global.document.querySelectorAll(SELECTOR);
        selects.forEach(function (select) {
            if (select.value !== value) {
                select.value = value;
            }
        });
    }

    function listAvailableThemes(selects) {
        var values = ["default"];
        if (!selects || !selects.length) {
            return values;
        }
        selects.forEach(function (select) {
            var options = select && select.options ? select.options : [];
            for (var i = 0; i < options.length; i += 1) {
                var value = options[i].value || "default";
                if (values.indexOf(value) === -1) {
                    values.push(value);
                }
            }
        });
        return values;
    }

    function handleChange(event) {
        var select = event.target;
        if (!select || select.matches(SELECTOR) === false) {
            return;
        }
        var theme = select.value;
        applyTheme(theme);
        storeTheme(theme);
        syncSelects(theme);
        emitThemeChange(theme);
    }

    function init() {
        if (!root || !global.document) {
            return;
        }
        var selects = global.document.querySelectorAll(SELECTOR);
        if (!selects.length) {
            return;
        }

        var availableThemes = listAvailableThemes(selects);
        var stored = getStoredTheme();
        var initial = stored || root.getAttribute("data-theme") || "default";
        if (availableThemes.indexOf(initial) === -1) {
            initial = "default";
            storeTheme(initial);
        }
        applyTheme(initial);
        syncSelects(initial);
        emitThemeChange(initial);

        global.document.addEventListener("change", handleChange, { passive: true });
    }

    if (typeof global.document !== "undefined") {
        if (global.document.readyState === "loading") {
            global.document.addEventListener("DOMContentLoaded", init, { once: true });
        } else {
            init();
        }
    }
}(typeof globalThis !== "undefined" ? globalThis : window));

/* ----------------------------------------------------------------------------
 * Treatments
 * Doc: controllers_js/README.md — Treatments Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Treatments = (function () {
    var instance;

    var MODE_PANEL_MAP = {
        1: "#treatments_mode1_controls",
        4: "#treatments_mode4_controls"
    };

    var EVENT_NAMES = [
        "treatments:list:loaded",
        "treatments:scenario:updated",
        "treatments:mode:changed",
        "treatments:mode:error",
        "treatments:selection:changed",
        "treatments:run:started",
        "treatments:run:submitted",
        "treatments:run:error",
        "treatments:job:started",
        "treatments:job:completed",
        "treatments:job:failed",
        "treatments:status:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Treatments controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Treatments controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Treatments controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Treatments controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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

    function parseMode(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function getOptionSnapshot(selectElement) {
        if (!selectElement || !selectElement.options) {
            return [];
        }
        return Array.prototype.slice.call(selectElement.options).map(function (option) {
            return {
                value: option.value,
                label: option.textContent,
                selected: Boolean(option.selected)
            };
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var treatments = controlBase();
        var treatmentsEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                treatmentsEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                treatmentsEvents = emitterBase;
            }
        }

        if (treatmentsEvents) {
            treatments.events = treatmentsEvents;
        }

        var formElement = dom.ensureElement("#treatments_form", "Treatments form not found.");
        var infoElement = dom.qs("[data-treatments-role=\"info\"]", formElement) || dom.qs("#info", formElement);
        var statusElement = dom.qs("[data-treatments-role=\"status\"]", formElement) || dom.qs("#status", formElement);
        var stacktraceElement = dom.qs("[data-treatments-role=\"stacktrace\"]", formElement) || dom.qs("#stacktrace", formElement);
        var statusPanelEl = dom.qs("#treatments_status_panel");
        var stacktracePanelEl = dom.qs("#treatments_stacktrace_panel");
        var hintElement = dom.qs("[data-treatments-role=\"hint\"]") || dom.qs("#hint_build_treatments");
        var rqJobElement = dom.qs("[data-treatments-role=\"job\"]", formElement) || dom.qs("#rq_job", formElement);
        var selectionElement = dom.qs("[data-treatments-role=\"selection\"]", formElement) || dom.qs("#treatments_single_selection", formElement);

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var hintAdapter = createLegacyAdapter(hintElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);

        treatments.form = formElement;
        treatments.info = infoAdapter;
        treatments.status = statusAdapter;
        treatments.stacktrace = stacktraceAdapter;
        treatments.statusPanelEl = statusPanelEl || null;
        treatments.stacktracePanelEl = stacktracePanelEl || null;
        treatments.statusStream = null;
        treatments.command_btn_id = "btn_build_treatments";
        treatments.hint = hintAdapter;
        treatments.rq_job = rqJobAdapter;
        treatments._completion_seen = false;

        var spinnerElement = statusPanelEl ? statusPanelEl.querySelector("#braille") : null;
        treatments.statusSpinnerEl = spinnerElement;

        function snapshotForm() {
            try {
                return forms.serializeForm(formElement, { format: "json" }) || {};
            } catch (err) {
                return {};
            }
        }

        function getSelectionValue() {
            if (!selectionElement) {
                return null;
            }
            var value = selectionElement.value;
            if (value === undefined || value === null || value === "") {
                return null;
            }
            return String(value);
        }

        function applyModeToRadios(modeValue) {
            var radios = formElement.querySelectorAll("input[name=\"treatments_mode\"]");
            if (!radios) {
                return;
            }
            Array.prototype.slice.call(radios).forEach(function (radio) {
                radio.checked = String(radio.value) === String(modeValue);
            });
        }

        function updateScenarioEmit(source) {
            if (!treatmentsEvents) {
                return;
            }
            treatmentsEvents.emit("treatments:scenario:updated", {
                mode: treatments.mode,
                selection: getSelectionValue(),
                source: source || "controller"
            });
        }

        function emitStatus(message, meta) {
            if (!message) {
                return;
            }
            if (treatments.statusStream && typeof treatments.statusStream.append === "function") {
                treatments.statusStream.append(message, meta || null);
            } else if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.innerHTML = message;
            }
            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:status:updated", {
                    message: message,
                    meta: meta || null
                });
            }
        }

        treatments.appendStatus = emitStatus;

        treatments.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function resetBeforeRun(taskMessage) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            } else if (infoElement) {
                infoElement.textContent = "";
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else if (stacktraceElement) {
                stacktraceElement.textContent = "";
            }
            treatments.hideStacktrace();
            if (rqJobAdapter && typeof rqJobAdapter.text === "function") {
                rqJobAdapter.text("");
            }
            if (taskMessage) {
                emitStatus(taskMessage + "...");
            }
        }

        function resetCompletionSeen() {
            treatments._completion_seen = false;
        }

        function handleModeError(error, normalized, selectionValue) {
            var payload = toResponsePayload(http, error);
            treatments.pushResponseStacktrace(treatments, payload);
            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:mode:error", {
                    mode: normalized,
                    selection: selectionValue,
                    error: payload,
                    cause: error
                });
            }
        }

        function postModeUpdate(normalized, selectionValue) {
            return http.postJson(url_for_run("tasks/set_treatments_mode/"), {
                mode: normalized,
                single_selection: selectionValue
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === false) {
                    treatments.pushResponseStacktrace(treatments, response);
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:mode:error", {
                            mode: normalized,
                            selection: selectionValue,
                            response: response
                        });
                    }
                    return response;
                }
                updateScenarioEmit("server");
                return response;
            }).catch(function (error) {
                handleModeError(error, normalized, selectionValue);
                throw error;
            });
        }

        treatments.updateModeUI = function (mode) {
            var normalized = parseMode(mode, treatments.mode);
            Object.keys(MODE_PANEL_MAP).forEach(function (key) {
                var selector = MODE_PANEL_MAP[key];
                if (!selector) {
                    return;
                }
                var panel = dom.qs(selector);
                if (!panel) {
                    return;
                }
                if (parseInt(key, 10) === normalized) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
            applyModeToRadios(normalized);
        };

        treatments.setMode = function (mode, options) {
            var normalized = parseMode(
                mode !== undefined ? mode : (snapshotForm().treatments_mode),
                treatments.mode !== undefined ? treatments.mode : -1
            );
            var selectionValue = getSelectionValue();

            treatments.mode = normalized;
            treatments.updateModeUI(normalized);

            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:mode:changed", {
                    mode: normalized,
                    selection: selectionValue,
                    source: options && options.source ? options.source : "controller"
                });
            }

            if (options && options.skipRequest) {
                updateScenarioEmit(options.source || "controller");
                return Promise.resolve({ skipped: true });
            }

            return postModeUpdate(normalized, selectionValue);
        };

        treatments.build = function () {
            var taskMessage = "Building treatments";
            resetCompletionSeen();
            resetBeforeRun(taskMessage);

            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:run:started", {
                    mode: treatments.mode,
                    selection: getSelectionValue()
                });
            }

            treatments.connect_status_stream(treatments);

            var formData = new FormData(formElement);

            http.request(url_for_run("rq/api/build_treatments"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    var message = "build_treatments job submitted: " + response.job_id;
                    emitStatus(message);
                    treatments.poll_completion_event = "TREATMENTS_BUILD_TASK_COMPLETED";
                    treatments.set_rq_job_id(treatments, response.job_id);
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:run:submitted", {
                            jobId: response.job_id,
                            mode: treatments.mode,
                            selection: getSelectionValue()
                        });
                    }
                    return;
                }
                if (response) {
                    treatments.pushResponseStacktrace(treatments, response);
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:run:error", {
                            mode: treatments.mode,
                            selection: getSelectionValue(),
                            response: response
                        });
                    }
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                treatments.pushResponseStacktrace(treatments, payload);
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:run:error", {
                        mode: treatments.mode,
                        selection: getSelectionValue(),
                        error: payload,
                        cause: error
                    });
                }
            });
        };

        treatments.report = function () {
            http.request(url_for_run("report/treatments/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:list:loaded", {
                        html: html,
                        mode: treatments.mode,
                        selection: getSelectionValue()
                    });
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                treatments.pushResponseStacktrace(treatments, payload);
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:run:error", {
                        error: payload,
                        cause: error,
                        action: "report"
                    });
                }
            });
        };

        treatments.restore = function (mode, singleSelection) {
            var normalized = parseMode(mode, treatments.mode !== undefined ? treatments.mode : -1);
            var selectionValue = singleSelection === undefined || singleSelection === null ? null : String(singleSelection);

            treatments.mode = normalized;
            applyModeToRadios(normalized);
            if (selectionElement && selectionValue !== null) {
                selectionElement.value = selectionValue;
            }
            treatments.updateModeUI(normalized);
            updateScenarioEmit("restore");
        };

        var baseTriggerEvent = treatments.triggerEvent.bind(treatments);
        treatments.triggerEvent = function (eventName, detail) {
            if (eventName) {
                var normalized = String(eventName).toUpperCase();
                var isCompleted = normalized.indexOf("COMPLETED") >= 0 ||
                    normalized.indexOf("FINISHED") >= 0 ||
                    normalized.indexOf("SUCCESS") >= 0;
                if (isCompleted) {
                    if (treatments._completion_seen) {
                        return baseTriggerEvent(eventName, detail);
                    }
                    treatments._completion_seen = true;
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:job:completed", detail || {});
                    }
                    treatments.disconnect_status_stream(treatments);
                }
                if (treatmentsEvents) {
                    if (normalized.indexOf("STARTED") >= 0 || normalized.indexOf("QUEUED") >= 0) {
                        treatmentsEvents.emit("treatments:job:started", detail || {});
                    }
                    if (normalized.indexOf("FAILED") >= 0 || normalized.indexOf("ERROR") >= 0) {
                        treatmentsEvents.emit("treatments:job:failed", detail || {});
                    }
                }
            }
            return baseTriggerEvent(eventName, detail);
        };

        function setupStatusStream() {
            treatments.detach_status_stream(treatments);
            var spinnerEl = treatments.statusSpinnerEl;
            if (!spinnerEl && treatments.statusPanelEl) {
                spinnerEl = treatments.statusPanelEl.querySelector("#braille");
                treatments.statusSpinnerEl = spinnerEl;
            }
            treatments.attach_status_stream(treatments, {
                element: treatments.statusPanelEl,
                form: formElement,
                channel: "treatments",
                stacktrace: treatments.stacktracePanelEl ? { element: treatments.stacktracePanelEl } : null,
                spinner: spinnerEl,
                logLimit: 200
            });
        }

        setupStatusStream();

        var delegates = [];

        delegates.push(dom.delegate(formElement, "change", "[data-treatments-role=\"mode\"]", function () {
            var modeAttr = this.getAttribute("data-treatments-mode");
            var normalized = parseMode(modeAttr, snapshotForm().treatments_mode);
            treatments.setMode(normalized, { source: "mode-change" });
        }));

        if (selectionElement) {
            delegates.push(dom.delegate(formElement, "change", "[data-treatments-role=\"selection\"]", function () {
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:selection:changed", {
                        selection: getSelectionValue(),
                        mode: treatments.mode
                    });
                }
                treatments.setMode(treatments.mode, { source: "selection-change" });
            }));
        }

        delegates.push(dom.delegate(formElement, "click", "[data-treatments-action=\"build\"]", function (event) {
            event.preventDefault();
            treatments.build();
        }));

        treatments._delegates = delegates;

        var initialSnapshot = snapshotForm();
        var initialMode = parseMode(initialSnapshot.treatments_mode, -1);
        var initialSelection = initialSnapshot.treatments_single_selection;
        if (initialSelection === undefined && selectionElement) {
            initialSelection = selectionElement.value;
        }

        treatments.mode = initialMode;
        applyModeToRadios(initialMode);
        if (selectionElement && initialSelection !== undefined && initialSelection !== null) {
            selectionElement.value = String(initialSelection);
        }
        treatments.updateModeUI(initialMode);

        var optionSnapshot = getOptionSnapshot(selectionElement);
        if (treatmentsEvents && optionSnapshot.length > 0) {
            treatmentsEvents.emit("treatments:list:loaded", {
                options: optionSnapshot,
                mode: treatments.mode,
                selection: getSelectionValue()
            });
        }
        updateScenarioEmit("init");

        treatments.destroy = function () {
            if (delegates && delegates.length) {
                delegates.forEach(function (unsubscribe) {
                    if (typeof unsubscribe === "function") {
                        try {
                            unsubscribe();
                        } catch (err) {
                            // ignore
                        }
                    }
                });
                delegates = [];
            }
            treatments.detach_status_stream(treatments);
        };

        return treatments;
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

if (typeof globalThis !== "undefined") {
    globalThis.Treatments = Treatments;
}

/* ----------------------------------------------------------------------------
 * Wepp
 * ----------------------------------------------------------------------------
 */
var Wepp = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("Wepp controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Wepp controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Wepp controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Wepp controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

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
                } else if (content instanceof window.Node) {
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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var wepp = controlBase();
        var weppEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                weppEvents = events.useEventMap([
                    "wepp:run:started",
                    "wepp:run:queued",
                    "wepp:run:completed",
                    "wepp:run:error",
                    "wepp:report:loaded"
                ], emitterBase);
            } else {
                weppEvents = emitterBase;
            }
        }

        var formElement = dom.ensureElement("#wepp_form", "WEPP form not found.");
        var infoElement = dom.qs("#wepp_form #info");
        var statusElement = dom.qs("#wepp_form #status");
        var stacktraceElement = dom.qs("#wepp_form #stacktrace");
        var rqJobElement = dom.qs("#wepp_form #rq_job");
        var hintElement = dom.qs("#hint_run_wepp");
        var resultsContainer = dom.qs("#wepp-results");
        var revegSelect = dom.qs("#reveg_scenario");
        var coverTransformContainer = dom.qs("#user_defined_cover_transform_container");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        wepp.form = formElement;
        wepp.info = infoAdapter;
        wepp.status = statusAdapter;
        wepp.stacktrace = stacktraceAdapter;
        wepp.rq_job = rqJobAdapter;
        wepp.hint = hintAdapter;
        wepp.command_btn_id = "btn_run_wepp";
        wepp.resultsContainer = resultsContainer;

        wepp.statusPanelEl = dom.qs("#wepp_status_panel");
        wepp.stacktracePanelEl = dom.qs("#wepp_stacktrace_panel");
        wepp.statusSpinnerEl = wepp.statusPanelEl ? wepp.statusPanelEl.querySelector("#braille") : null;
        wepp.statusStream = null;
        wepp._delegates = [];

        if (weppEvents) {
            wepp.events = weppEvents;
        }

        wepp.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (wepp.statusStream && typeof wepp.statusStream.append === "function") {
                wepp.statusStream.append(message, meta || null);
            } else if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(message);
            } else if (statusElement) {
                statusElement.textContent = message;
            }
        };

        wepp.attach_status_stream(wepp, {
            element: wepp.statusPanelEl,
            channel: "wepp",
            runId: window.runid || window.runId || null,
            stacktrace: wepp.stacktracePanelEl ? { element: wepp.stacktracePanelEl } : null,
            spinner: wepp.statusSpinnerEl,
            logLimit: 400
        });

        wepp._completion_seen = false;

        function resetCompletionSeen() {
            wepp._completion_seen = false;
        }

        var baseTriggerEvent = wepp.triggerEvent.bind(wepp);
        wepp.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "WEPP_RUN_TASK_COMPLETED") {
                if (wepp._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                wepp._completion_seen = true;
                wepp.disconnect_status_stream(wepp);
                wepp.report();
                try {
                    Observed.getInstance().onWeppRunCompleted();
                } catch (err) {
                    console.warn("[WEPP] Observed controller notification failed", err);
                }
                if (weppEvents && typeof weppEvents.emit === "function") {
                    weppEvents.emit("wepp:run:completed", payload || {});
                }
            }

            return baseTriggerEvent(eventName, payload);
        };

        wepp.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
            } else if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        wepp.surf_runoff = dom.qs("#wepp_form #surf_runoff");
        wepp.lateral_flow = dom.qs("#wepp_form #lateral_flow");
        wepp.baseflow = dom.qs("#wepp_form #baseflow");
        wepp.sediment = dom.qs("#wepp_form #sediment");
        wepp.channel_critical_shear = dom.qs("#wepp_form #channel_critical_shear");

        wepp.addChannelCriticalShear = function (value) {
            if (!wepp.channel_critical_shear) {
                return;
            }
            var option = new Option("User Defined: CS = " + value, value, true, true);
            wepp.channel_critical_shear.appendChild(option);
        };

        wepp.updatePhosphorus = function () {
            http.getJson(url_for_run("query/wepp/phosphorus_opts/"))
                .then(function (response) {
                    if (!response) {
                        return;
                    }
                    if (response.surf_runoff !== null && wepp.surf_runoff) {
                        wepp.surf_runoff.value = Number(response.surf_runoff).toFixed(4);
                    }
                    if (response.lateral_flow !== null && wepp.lateral_flow) {
                        wepp.lateral_flow.value = Number(response.lateral_flow).toFixed(4);
                    }
                    if (response.baseflow !== null && wepp.baseflow) {
                        wepp.baseflow.value = Number(response.baseflow).toFixed(4);
                    }
                    if (response.sediment !== null && wepp.sediment) {
                        wepp.sediment.value = Number(response.sediment).toFixed(0);
                    }
                    wepp.appendStatus("Phosphorus defaults loaded from configuration.");
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.set_run_wepp_routine = function (routine, state) {
            var taskMsg = "Setting " + routine + " (" + state + ")";
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
            wepp.appendStatus(taskMsg + "...");

            return http.postJson(url_for_run("tasks/set_run_wepp_routine/"), { routine: routine, state: state }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        var message = taskMsg + "... Success";
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html(message);
                        }
                        wepp.appendStatus(message);
                    } else if (response) {
                        wepp.pushResponseStacktrace(wepp, response);
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.handleCoverTransformUpload = function (input) {
            if (!input || !input.files || input.files.length === 0) {
                return false;
            }

            var file = input.files[0];
            var formData = new FormData();
            formData.append("input_upload_cover_transform", file);

            http.request(url_for_run("tasks/upload_cover_transform"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function () {
                console.log("[WEPP] Cover transform uploaded");
            }).catch(function (error) {
                wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
            });

            return true;
        };

        wepp.handleRevegetationScenarioChange = function (value) {
            if (!coverTransformContainer) {
                return;
            }
            if (value === "user_cover_transform") {
                if (dom.show) {
                    dom.show(coverTransformContainer);
                } else {
                    coverTransformContainer.hidden = false;
                    coverTransformContainer.style.removeProperty("display");
                }
            } else {
                if (dom.hide) {
                    dom.hide(coverTransformContainer);
                } else {
                    coverTransformContainer.hidden = true;
                    coverTransformContainer.style.display = "none";
                }
            }
        };

        wepp.run = function () {
            var taskMsg = "Submitting wepp run";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            wepp.connect_status_stream(wepp);

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run:started", { payload: payload });
            }

            http.postJson(url_for_run("rq/api/run_wepp"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        var message = "run_wepp_rq job submitted: " + response.job_id;
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html(message);
                        }
                        wepp.appendStatus(message, { job_id: response.job_id });
                        wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, response.job_id);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run:queued", { jobId: response.job_id, payload: payload });
                        }
                    } else if (response) {
                        wepp.pushResponseStacktrace(wepp, response);
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:run:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.report = function () {
            var taskMsg = "Fetching Summary";
            var resultsHtml = "";

            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }

            try {
                SubcatchmentDelineation.getInstance().prefetchLossMetrics();
            } catch (error) {
                console.warn("[WEPP] Unable to prefetch loss metrics", error);
            }

            http.request(url_for_run("report/wepp/results/"))
                .then(function (result) {
                    var body = result && result.body;
                    if (typeof body === "string" && resultsContainer) {
                        resultsContainer.innerHTML = body;
                        resultsHtml = body;
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });

            http.request(url_for_run("report/wepp/run_summary/"))
                .then(function (result) {
                    var body = result && result.body;
                    if (typeof body === "string") {
                        if (infoAdapter && typeof infoAdapter.html === "function") {
                            infoAdapter.html(body);
                        } else if (infoElement) {
                            infoElement.innerHTML = body;
                        }
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(taskMsg + "... Success");
                    }
                    wepp.appendStatus(taskMsg + "... Success");
                    try {
                        Project.getInstance().set_preferred_units();
                    } catch (error) {
                        console.warn("[WEPP] Failed to apply preferred units", error);
                    }
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:report:loaded", {
                            summary: typeof body === "string" ? body : "",
                            results: resultsHtml
                        });
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.runWatershed = function () {
            var taskMsg = "Submitting WEPP watershed run";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            wepp.connect_status_stream(wepp);

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run_watershed:started", { payload: payload });
            }

            http.postJson(url_for_run("rq/api/run_wepp_watershed"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        var message = "run_wepp_watershed_rq job submitted: " + response.job_id;
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html(message);
                        }
                        wepp.appendStatus(message, { job_id: response.job_id });
                        wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, response.job_id);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run_watershed:queued", { jobId: response.job_id, payload: payload });
                        }
                    } else if (response) {
                        wepp.pushResponseStacktrace(wepp, response);
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:run_watershed:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        function ensureDelegates() {
            if (wepp._delegates && wepp._delegates.length) {
                return;
            }

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.run();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run-watershed"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.runWatershed();
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", "[data-wepp-routine]", function () {
                var routine = this.getAttribute("data-wepp-routine");
                if (!routine) {
                    return;
                }
                wepp.set_run_wepp_routine(routine, Boolean(this.checked));
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", '[data-wepp-action="upload-cover-transform"]', function () {
                wepp.handleCoverTransformUpload(this);
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", '[data-wepp-role="reveg-scenario"]', function () {
                wepp.handleRevegetationScenarioChange(this.value);
            }));
        }

        ensureDelegates();
        wepp.handleRevegetationScenarioChange(revegSelect ? revegSelect.value : "");

        var bootstrapState = {
            modeListenersBound: false,
            reportTriggered: false
        };

        wepp.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "wepp")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_wepp_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_wepp_rq")) {
                    var value = jobIds.run_wepp_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_wepp_watershed_rq")) {
                    var watershedValue = jobIds.run_wepp_watershed_rq;
                    if (watershedValue !== undefined && watershedValue !== null) {
                        jobId = String(watershedValue);
                    }
                }
            }

            if (typeof wepp.set_rq_job_id === "function") {
                if (jobId) {
                    wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                    resetCompletionSeen();
                }
                wepp.set_rq_job_id(wepp, jobId);
            }

            if (!bootstrapState.modeListenersBound && typeof wepp.setMode === "function") {
                var modeInputs = document.querySelectorAll("input[name='wepp_mode']");
                modeInputs.forEach(function (input) {
                    input.addEventListener("change", function () {
                        wepp.setMode();
                    });
                });
                var singleSelectionInput = document.getElementById("wepp_single_selection");
                if (singleSelectionInput) {
                    singleSelectionInput.addEventListener("change", function () {
                        wepp.setMode();
                    });
                }
                bootstrapState.modeListenersBound = modeInputs.length > 0 || Boolean(singleSelectionInput);
                if (bootstrapState.modeListenersBound) {
                    try {
                        wepp.setMode();
                    } catch (err) {
                        console.warn("[WEPP] Failed to apply initial mode", err);
                    }
                }
            }

            var weppData = (ctx.data && ctx.data.wepp) || {};
            var hasRun = controllerContext.hasRun;
            if (hasRun === undefined) {
                hasRun = weppData.hasRun;
            }
            if (hasRun && !bootstrapState.reportTriggered && typeof wepp.report === "function") {
                wepp.report();
                bootstrapState.reportTriggered = true;
            }

            return wepp;
        };

        return wepp;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.Wepp = Wepp;
}

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

/* ----------------------------------------------------------------------------
 * Map (Deck.gl scaffolding)
 * Doc: controllers_js/README.md - Map Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var MapController = (function () {
    "use strict";

    var instance;

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
        "map:layer:error"
    ];

    var DEFAULT_VIEW = { lat: 44.0, lng: -116.0, zoom: 6 };

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" || typeof dom.hide !== "function" || typeof dom.setText !== "function") {
            throw new Error("Map GL controller requires WCDom helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.getJson !== "function" || typeof http.request !== "function") {
            throw new Error("Map GL controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Map GL controller requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
    }

    function ensureDeck() {
        if (typeof window === "undefined" || !window.deck || !window.deck.Deck) {
            throw new Error("Map GL controller requires deck.gl (window.deck.Deck).");
        }
    }

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
        var sanitized = String(value).replace(/[a-zA-Z{}\[\]\\|\/<>';:]/g, "");
        return sanitized.split(/[\s,]+/).filter(function (item) {
            return item !== "";
        });
    }

    function parseLocationInput(value) {
        var tokens = sanitizeLocationInput(value);
        if (tokens.length < 2) {
            return null;
        }
        var lng = Number(tokens[0]);
        var lat = Number(tokens[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return null;
        }
        var zoom = null;
        if (tokens.length > 2) {
            var parsedZoom = Number(tokens[2]);
            if (Number.isFinite(parsedZoom)) {
                zoom = parsedZoom;
            }
        }
        return { lat: lat, lng: lng, zoom: zoom };
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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var events = helpers.events;
        var deckApi = window.deck;
        var coordRound = (typeof window.coordRound === "function")
            ? window.coordRound
            : function (value) { return Math.round(value * 1000) / 1000; };

        ensureDeck();

        var state = {
            center: { lat: DEFAULT_VIEW.lat, lng: DEFAULT_VIEW.lng },
            zoom: DEFAULT_VIEW.zoom,
            readyEmitted: false
        };

        var emitterBase = events.createEmitter();
        var mapEvents = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var basemapDefs = {
            googleTerrain: {
                key: "googleTerrain",
                label: "Terrain",
                template: "https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
                subdomains: ["mt0", "mt1", "mt2", "mt3"]
            },
            googleSatellite: {
                key: "googleSatellite",
                label: "Satellite",
                template: "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                subdomains: ["mt0", "mt1", "mt2", "mt3"]
            }
        };

        var formElement = dom.qs("#setloc_form");
        var centerInput = dom.qs("#input_centerloc", formElement);
        var mapCanvasElement = dom.qs("#mapid");
        var drilldownElement = dom.qs("#drilldown");
        var subLegendElement = dom.qs("#sub_legend");
        var sbsLegendElement = dom.qs("#sbs_legend");
        var mapStatusElement = dom.qs("#mapstatus");
        var mouseElevationElement = dom.qs("#mouseelev");
        var tabsetRoot = dom.qs("#setloc_form [data-tabset]");

        var overlayRegistry = typeof Map === "function" ? new Map() : null;
        var overlayNameRegistry = typeof Map === "function" ? new Map() : null;
        var layerRegistry = typeof Set === "function" ? new Set() : null;
        var drilldownSuppressionTokens = typeof Set === "function" ? new Set() : null;
        var panes = {};
        var mapHandlers = {};
        var deckgl = null;
        var isApplyingViewState = false;
        var baseLayer = null;
        var baseLayerKey = basemapDefs.googleTerrain.key;
        var layerControl = null;

        function emit(eventName, payload) {
            if (mapEvents && typeof mapEvents.emit === "function") {
                mapEvents.emit(eventName, payload || {});
            }
        }

        function warnNotImplemented(action) {
            console.warn("Map GL stub: " + action + " not implemented.");
        }

        function getCanvasSize() {
            if (!mapCanvasElement) {
                return { width: 0, height: 0 };
            }
            var rect = mapCanvasElement.getBoundingClientRect();
            var width = Math.round(rect.width || mapCanvasElement.offsetWidth || mapCanvasElement.clientWidth || 0);
            var height = Math.round(rect.height || mapCanvasElement.offsetHeight || mapCanvasElement.clientHeight || 0);
            return { width: width, height: height };
        }

        function updateMapStatus() {
            if (!mapStatusElement) {
                return;
            }
            var center = state.center;
            var zoom = state.zoom;
            var width = mapCanvasElement ? Math.round(mapCanvasElement.offsetWidth || 0) : 0;
            var lng = coordRound(center.lng);
            var lat = coordRound(center.lat);
            dom.setText(mapStatusElement, "Center: " + lng + ", " + lat + " | Zoom: " + zoom + " ( Map Width:" + width + "px )");
        }

        function buildBounds() {
            var center = state.center;
            var zoom = state.zoom;
            if (deckApi && typeof deckApi.WebMercatorViewport === "function") {
                var size = getCanvasSize();
                if (size.width > 0 && size.height > 0) {
                    var viewport = new deckApi.WebMercatorViewport({
                        width: size.width,
                        height: size.height,
                        longitude: center.lng,
                        latitude: center.lat,
                        zoom: zoom,
                        pitch: 0,
                        bearing: 0
                    });
                    var bounds = viewport.getBounds();
                    if (bounds && bounds.length === 4) {
                        return {
                            getSouthWest: function () { return { lat: bounds[1], lng: bounds[0] }; },
                            getNorthEast: function () { return { lat: bounds[3], lng: bounds[2] }; },
                            toBBoxString: function () {
                                return [bounds[0], bounds[1], bounds[2], bounds[3]].join(",");
                            }
                        };
                    }
                }
            }
            return buildBoundsFallback(center, zoom);
        }

        function buildViewportPayload() {
            var center = state.center;
            var bounds = buildBounds();
            return {
                center: { lat: center.lat, lng: center.lng },
                zoom: state.zoom,
                bounds: bounds,
                bbox: bounds.toBBoxString()
            };
        }

        function addDrilldownSuppression(token) {
            if (!drilldownSuppressionTokens) {
                return;
            }
            drilldownSuppressionTokens.add(token || "default");
        }

        function removeDrilldownSuppression(token) {
            if (!drilldownSuppressionTokens) {
                return;
            }
            drilldownSuppressionTokens.delete(token || "default");
        }

        function isDrilldownSuppressed() {
            return drilldownSuppressionTokens ? drilldownSuppressionTokens.size > 0 : false;
        }

        function normalizeViewState(viewState) {
            if (!viewState || typeof viewState !== "object") {
                return null;
            }
            var longitude = Number(viewState.longitude);
            var latitude = Number(viewState.latitude);
            var zoom = Number.isFinite(viewState.zoom) ? Number(viewState.zoom) : state.zoom;
            if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
                return null;
            }
            var bearing = Number.isFinite(viewState.bearing) ? Number(viewState.bearing) : 0;
            var pitch = Number.isFinite(viewState.pitch) ? Number(viewState.pitch) : 0;
            return {
                longitude: longitude,
                latitude: latitude,
                zoom: zoom,
                bearing: bearing,
                pitch: pitch
            };
        }

        function toViewState(center, zoom) {
            return normalizeViewState({
                longitude: center.lng,
                latitude: center.lat,
                zoom: Number.isFinite(zoom) ? zoom : state.zoom
            });
        }

        function updateStateFromViewState(viewState) {
            state.center = { lat: viewState.latitude, lng: viewState.longitude };
            state.zoom = viewState.zoom;
        }

        function fireMapHandlers(eventName) {
            if (!eventName || !mapHandlers[eventName]) {
                return;
            }
            mapHandlers[eventName].forEach(function (handler) {
                try {
                    handler({ target: map });
                } catch (err) {
                    console.warn("Map GL handler failed for " + eventName, err);
                }
            });
        }

        function notifyViewChange(isFinal) {
            updateMapStatus();
            fireMapHandlers("move");
            fireMapHandlers("zoom");
            if (isFinal) {
                fireMapHandlers("moveend");
                fireMapHandlers("zoomend");
                emit("map:center:changed", buildViewportPayload());
            }
        }

        function applyViewState(nextViewState, options) {
            var normalized = normalizeViewState(nextViewState);
            if (!normalized) {
                return;
            }
            updateStateFromViewState(normalized);
            if (deckgl && !(options && options.skipDeck)) {
                var size = getCanvasSize();
                if (!isApplyingViewState) {
                    isApplyingViewState = true;
                    deckgl.setProps({
                        viewState: normalized,
                        width: size.width || undefined,
                        height: size.height || undefined
                    });
                    isApplyingViewState = false;
                }
            }
            notifyViewChange(Boolean(options && options.final));
        }

        function resolveBasemap(key) {
            if (!key) {
                return basemapDefs.googleTerrain;
            }
            if (basemapDefs[key]) {
                return basemapDefs[key];
            }
            var lower = String(key).toLowerCase();
            if (lower.indexOf("sat") !== -1) {
                return basemapDefs.googleSatellite;
            }
            if (lower.indexOf("terrain") !== -1) {
                return basemapDefs.googleTerrain;
            }
            return basemapDefs.googleTerrain;
        }

        function buildBasemapUrl(def, x, y, z) {
            var template = def.template;
            var subdomains = def.subdomains || [];
            var subdomain = subdomains.length
                ? subdomains[(x + y + z) % subdomains.length]
                : "";
            return template
                .replace("{s}", subdomain)
                .replace("{x}", x)
                .replace("{y}", y)
                .replace("{z}", z);
        }

        function createBaseLayer(definition) {
            var def = definition || basemapDefs.googleTerrain;
            if (!deckApi || typeof deckApi.TileLayer !== "function" || typeof deckApi.BitmapLayer !== "function") {
                warnNotImplemented("TileLayer/BitmapLayer unavailable");
                return null;
            }
            return new deckApi.TileLayer({
                id: "map-gl-base-" + def.key,
                data: def.template,
                minZoom: 0,
                maxZoom: 19,
                tileSize: 256,
                maxRequests: 8,
                getTileData: async function (params) {
                    var index = params && params.index ? params.index : {};
                    var x = index.x;
                    var y = index.y;
                    var z = index.z;
                    if (![x, y, z].every(Number.isFinite)) {
                        throw new Error("Tile coords missing: x=" + x + " y=" + y + " z=" + z);
                    }
                    var url = buildBasemapUrl(def, x, y, z);
                    var response = await fetch(url, { signal: params.signal, mode: "cors" });
                    if (!response.ok) {
                        throw new Error("Tile fetch failed " + response.status + ": " + url);
                    }
                    var blob = await response.blob();
                    return await createImageBitmap(blob);
                },
                onTileError: function (error) {
                    console.warn("Map GL tile error", error);
                },
                renderSubLayers: function (props) {
                    var tile = props.tile;
                    if (!tile || !props.data || !tile.bbox) {
                        return null;
                    }
                    var west = tile.bbox.west;
                    var south = tile.bbox.south;
                    var east = tile.bbox.east;
                    var north = tile.bbox.north;
                    return new deckApi.BitmapLayer(props, {
                        id: props.id + "-" + tile.id,
                        data: null,
                        image: props.data,
                        bounds: [west, south, east, north],
                        pickable: false,
                        opacity: 1.0
                    });
                }
            });
        }

        function applyLayers() {
            if (!deckgl) {
                return;
            }
            var nextLayers = [];
            if (baseLayer) {
                nextLayers.push(baseLayer);
            }
            if (layerRegistry) {
                layerRegistry.forEach(function (layer) {
                    nextLayers.push(layer);
                });
            }
            deckgl.setProps({ layers: nextLayers });
        }

        function ensureLayerControl() {
            if (layerControl || !mapCanvasElement || typeof document === "undefined") {
                return layerControl;
            }
            var host = mapCanvasElement.closest ? mapCanvasElement.closest(".wc-map") : null;
            if (!host) {
                host = mapCanvasElement.parentElement;
            }
            if (!host) {
                return null;
            }

            var root = document.createElement("div");
            root.className = "wc-map-layer-control";
            root.setAttribute("data-map-layer-control", "true");

            var toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "wc-map-layer-control__toggle";
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Layers");
            toggle.setAttribute("title", "Layers");
            toggle.innerHTML = '<svg class="wc-map-layer-control__icon" aria-hidden="true" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg" width="26" height="26"><path fill="#b9b9b9" d="m.032 17.056 13-8 13 8-13 8z"/><path fill="#737373" d="m.032 17.056-.032.93 13 8 13-8 .032-.93-13 8z"/><path fill="#cdcdcd" d="m0 13.076 13-8 13 8-13 8z"/><path fill="#737373" d="M0 13.076v.91l13 8 13-8v-.91l-13 8z"/><path fill="#e9e9e9" fill-opacity=".585" stroke="#797979" stroke-width=".1" d="m0 8.986 13-8 13 8-13 8-13-8"/><path fill="#737373" d="M0 8.986v1l13 8 13-8v-1l-13 8z"/></svg><span class="wc-sr-only">Layers</span>';

            var panel = document.createElement("div");
            panel.className = "wc-map-layer-control__panel";
            panel.hidden = true;

            var baseSection = document.createElement("div");
            baseSection.className = "wc-map-layer-control__section";
            var baseTitle = document.createElement("div");
            baseTitle.className = "wc-map-layer-control__title";
            baseTitle.textContent = "Base Layers";
            var baseList = document.createElement("div");
            baseList.className = "wc-map-layer-control__list";
            baseSection.appendChild(baseTitle);
            baseSection.appendChild(baseList);

            var overlaySection = document.createElement("div");
            overlaySection.className = "wc-map-layer-control__section";
            var overlayTitle = document.createElement("div");
            overlayTitle.className = "wc-map-layer-control__title";
            overlayTitle.textContent = "Overlays";
            var overlayList = document.createElement("div");
            overlayList.className = "wc-map-layer-control__list";
            overlaySection.appendChild(overlayTitle);
            overlaySection.appendChild(overlayList);

            panel.appendChild(baseSection);
            panel.appendChild(overlaySection);
            root.appendChild(toggle);
            root.appendChild(panel);
            host.appendChild(root);

            function setExpanded(expanded) {
                if (!layerControl) {
                    return;
                }
                layerControl.toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
                layerControl.root.classList.toggle("is-expanded", expanded);
                layerControl.panel.hidden = !expanded;
            }

            toggle.addEventListener("click", function () {
                var expanded = toggle.getAttribute("aria-expanded") === "true";
                setExpanded(!expanded);
            });

            root.addEventListener("keydown", function (event) {
                if (event.key === "Escape") {
                    setExpanded(false);
                }
            });

            layerControl = {
                root: root,
                toggle: toggle,
                panel: panel,
                baseSection: baseSection,
                baseList: baseList,
                overlaySection: overlaySection,
                overlayList: overlayList,
                overlayInputs: typeof Map === "function" ? new Map() : null
            };

            return layerControl;
        }

        function renderBaseLayerControl() {
            var control = ensureLayerControl();
            if (!control) {
                return;
            }
            var baseMaps = map.baseMaps || {};
            var names = Object.keys(baseMaps);
            control.baseList.textContent = "";
            if (!names.length) {
                control.baseSection.hidden = true;
                return;
            }
            control.baseSection.hidden = false;
            names.forEach(function (name, index) {
                var def = baseMaps[name];
                var key = def && def.key ? def.key : name;
                var label = def && def.label ? def.label : name;
                var inputId = "wc-map-basemap-" + index;
                var wrapper = document.createElement("label");
                wrapper.className = "wc-map-layer-control__item";
                var input = document.createElement("input");
                input.type = "radio";
                input.name = "wc-map-basemap";
                input.value = key;
                input.id = inputId;
                input.checked = key === baseLayerKey;
                input.addEventListener("change", function () {
                    if (input.checked) {
                        map.setBaseLayer(key);
                    }
                });
                var text = document.createElement("span");
                text.className = "wc-map-layer-control__text";
                text.textContent = label;
                wrapper.appendChild(input);
                wrapper.appendChild(text);
                control.baseList.appendChild(wrapper);
            });
        }

        function syncBaseLayerControlSelection() {
            if (!layerControl) {
                return;
            }
            var inputs = layerControl.baseList.querySelectorAll('input[type="radio"][name="wc-map-basemap"]');
            Array.prototype.forEach.call(inputs, function (input) {
                input.checked = input.value === baseLayerKey;
            });
        }

        function renderOverlayLayerControl() {
            var control = ensureLayerControl();
            if (!control || !overlayNameRegistry) {
                return;
            }
            control.overlayList.textContent = "";
            if (control.overlayInputs && typeof control.overlayInputs.clear === "function") {
                control.overlayInputs.clear();
            }
            var entries = Array.from(overlayNameRegistry.entries());
            if (!entries.length) {
                control.overlaySection.hidden = true;
                return;
            }
            control.overlaySection.hidden = false;
            entries.forEach(function (entry, index) {
                var name = entry[0];
                var layer = entry[1];
                var inputId = "wc-map-overlay-" + index;
                var wrapper = document.createElement("label");
                wrapper.className = "wc-map-layer-control__item";
                var input = document.createElement("input");
                input.type = "checkbox";
                input.name = "wc-map-overlay";
                input.value = name;
                input.id = inputId;
                input.checked = map.hasLayer(layer);
                input.addEventListener("change", function () {
                    if (input.checked) {
                        map.addLayer(layer);
                    } else {
                        map.removeLayer(layer);
                    }
                    emit("map:layer:toggled", {
                        name: name,
                        layer: layer,
                        visible: input.checked,
                        type: "overlay"
                    });
                });
                var text = document.createElement("span");
                text.className = "wc-map-layer-control__text";
                text.textContent = name;
                wrapper.appendChild(input);
                wrapper.appendChild(text);
                control.overlayList.appendChild(wrapper);
                if (control.overlayInputs && typeof control.overlayInputs.set === "function") {
                    control.overlayInputs.set(name, input);
                }
            });
        }

        function syncOverlayLayerControlSelection() {
            if (!layerControl || !overlayNameRegistry || !layerControl.overlayInputs) {
                return;
            }
            layerControl.overlayInputs.forEach(function (input, name) {
                var layer = overlayNameRegistry.get(name);
                if (!layer) {
                    input.disabled = true;
                    return;
                }
                input.disabled = false;
                input.checked = map.hasLayer(layer);
            });
        }

        var map = {
            events: mapEvents,
            drilldown: createLegacyAdapter(drilldownElement),
            sub_legend: createLegacyAdapter(subLegendElement),
            sbs_legend: createLegacyAdapter(sbsLegendElement),
            mouseelev: createLegacyAdapter(mouseElevationElement),
            centerInput: centerInput || null,
            tabset: createTabset(tabsetRoot),
            ctrls: {
                addOverlay: function (layer, name) {
                    if (!layer || !name || !overlayRegistry || !overlayNameRegistry) {
                        return;
                    }
                    var existing = overlayNameRegistry.get(name);
                    if (existing && existing !== layer) {
                        map.removeLayer(existing);
                        overlayRegistry.delete(existing);
                        overlayNameRegistry.delete(name);
                        if (map.overlayMaps) {
                            delete map.overlayMaps[name];
                        }
                    }
                    overlayRegistry.set(layer, name);
                    overlayNameRegistry.set(name, layer);
                    if (map.overlayMaps) {
                        map.overlayMaps[name] = layer;
                    }
                    renderOverlayLayerControl();
                },
                removeLayer: function (layer) {
                    if (!layer || !overlayRegistry || !overlayNameRegistry) {
                        return;
                    }
                    var name = overlayRegistry.get(layer);
                    if (name) {
                        overlayRegistry.delete(layer);
                        overlayNameRegistry.delete(name);
                        if (map.overlayMaps) {
                            delete map.overlayMaps[name];
                        }
                    }
                    renderOverlayLayerControl();
                }
            },
            boxZoom: {
                disable: function () { return null; },
                enable: function () { return null; }
            },
            on: function (eventName, handler) {
                if (!eventName || typeof handler !== "function") {
                    return;
                }
                mapHandlers[eventName] = mapHandlers[eventName] || [];
                mapHandlers[eventName].push(handler);
            },
            off: function (eventName, handler) {
                if (!eventName || !mapHandlers[eventName]) {
                    return;
                }
                if (!handler) {
                    delete mapHandlers[eventName];
                    return;
                }
                mapHandlers[eventName] = mapHandlers[eventName].filter(function (item) {
                    return item !== handler;
                });
            },
            createPane: function (name) {
                panes[name] = panes[name] || { style: {} };
                return panes[name];
            },
            getPane: function (name) {
                return panes[name] || null;
            },
            getCenter: function () {
                return { lat: state.center.lat, lng: state.center.lng };
            },
            getZoom: function () {
                return state.zoom;
            },
            getBounds: function () {
                return buildBounds();
            },
            distance: function (a, b) {
                return calculateDistanceMeters(a, b);
            },
            setView: function (center, zoom) {
                var normalized = normalizeCenter(center);
                if (!normalized) {
                    return;
                }
                var nextViewState = toViewState(normalized, Number.isFinite(zoom) ? zoom : state.zoom);
                applyViewState(nextViewState, { final: true });
            },
            flyTo: function (center, zoom) {
                map.setView(center, zoom);
            },
            flyToBounds: function (bounds) {
                if (!bounds) {
                    return;
                }
                var sw = bounds.getSouthWest ? bounds.getSouthWest() : null;
                var ne = bounds.getNorthEast ? bounds.getNorthEast() : null;
                if (!sw || !ne) {
                    return;
                }
                var center = {
                    lat: (sw.lat + ne.lat) / 2,
                    lng: (sw.lng + ne.lng) / 2
                };
                map.setView([center.lat, center.lng], state.zoom);
            },
            invalidateSize: function () {
                if (!deckgl) {
                    return null;
                }
                var size = getCanvasSize();
                deckgl.setProps({
                    width: size.width || undefined,
                    height: size.height || undefined
                });
                updateMapStatus();
                return null;
            },
            addLayer: function (layer) {
                if (layerRegistry && layer) {
                    layerRegistry.add(layer);
                    applyLayers();
                }
                syncOverlayLayerControlSelection();
                return layer;
            },
            removeLayer: function (layer) {
                if (layerRegistry && layer) {
                    layerRegistry.delete(layer);
                    applyLayers();
                }
                syncOverlayLayerControlSelection();
                return null;
            },
            hasLayer: function (layer) {
                if (!layerRegistry || !layer) {
                    return false;
                }
                return layerRegistry.has(layer);
            },
            registerOverlay: function (layer, name) {
                map.ctrls.addOverlay(layer, name);
                return layer;
            },
            unregisterOverlay: function (layer) {
                map.ctrls.removeLayer(layer);
            },
            suppressDrilldown: function (token) {
                addDrilldownSuppression(token);
            },
            releaseDrilldown: function (token) {
                removeDrilldownSuppression(token);
            },
            isDrilldownSuppressed: function () {
                return isDrilldownSuppressed();
            },
            addGeoJsonOverlay: function () {
                warnNotImplemented("addGeoJsonOverlay");
                return null;
            },
            subQuery: function () {
                warnNotImplemented("subQuery");
            },
            chnQuery: function () {
                warnNotImplemented("chnQuery");
            },
            findByTopazId: function () {
                warnNotImplemented("findByTopazId");
            },
            findByWeppId: function () {
                warnNotImplemented("findByWeppId");
            },
            goToEnteredLocation: function (value) {
                var inputValue = value;
                if (!inputValue && map.centerInput) {
                    inputValue = map.centerInput.value;
                }
                var parsed = parseLocationInput(inputValue);
                if (!parsed) {
                    warnNotImplemented("goToEnteredLocation: unable to parse input");
                    return;
                }
                if (parsed.zoom === null) {
                    map.flyTo([parsed.lat, parsed.lng]);
                } else {
                    map.flyTo([parsed.lat, parsed.lng], parsed.zoom);
                }
            },
            onMapChange: function () {
                updateMapStatus();
            },
            bootstrap: function (context) {
                var mapContext = context && context.map ? context.map : context || {};
                var center = Array.isArray(mapContext.center) ? mapContext.center : null;
                var zoom = Number.isFinite(mapContext.zoom) ? mapContext.zoom : null;

                if (center && zoom !== null) {
                    map.setView(center, zoom);
                } else if (center) {
                    map.setView(center, state.zoom);
                } else {
                    map.setView([DEFAULT_VIEW.lat, DEFAULT_VIEW.lng], zoom !== null ? zoom : state.zoom);
                }

                if (mapContext && mapContext.boundary) {
                    warnNotImplemented("boundary overlay");
                }

                if (!state.readyEmitted) {
                    emit("map:ready", buildViewportPayload());
                    state.readyEmitted = true;
                }

                updateMapStatus();
            }
        };

        map.baseMaps = {
            Terrain: basemapDefs.googleTerrain,
            Satellite: basemapDefs.googleSatellite
        };
        map.overlayMaps = {};
        map.setBaseLayer = function (key) {
            var def = resolveBasemap(key);
            baseLayerKey = def.key;
            baseLayer = createBaseLayer(def);
            applyLayers();
            syncBaseLayerControlSelection();
            emit("map:layer:toggled", {
                name: def.label,
                layer: baseLayer,
                visible: true,
                type: "base"
            });
        };
        renderBaseLayerControl();
        renderOverlayLayerControl();

        if (centerInput && typeof centerInput.addEventListener === "function") {
            centerInput.addEventListener("keydown", function (event) {
                var key = event.key || event.keyCode;
                if (key === "Enter" || key === 13) {
                    event.preventDefault();
                    emit("map:center:requested", {
                        source: "input",
                        query: centerInput.value || ""
                    });
                    map.goToEnteredLocation();
                }
            });
        }

        if (formElement) {
            dom.delegate(formElement, "click", "[data-map-action]", function (event) {
                var action = this.getAttribute("data-map-action");
                if (!action) {
                    return;
                }
                event.preventDefault();
                switch (action) {
                    case "go":
                        emit("map:center:requested", {
                            source: "button",
                            query: centerInput ? centerInput.value : ""
                        });
                        map.goToEnteredLocation();
                        break;
                    case "find-topaz":
                        emit("map:search:requested", {
                            type: "topaz",
                            query: centerInput ? centerInput.value : ""
                        });
                        map.findByTopazId();
                        break;
                    case "find-wepp":
                        emit("map:search:requested", {
                            type: "wepp",
                            query: centerInput ? centerInput.value : ""
                        });
                        map.findByWeppId();
                        break;
                    default:
                        break;
                }
            });
        }

        var initialViewState = normalizeViewState({
            longitude: state.center.lng,
            latitude: state.center.lat,
            zoom: state.zoom
        });

        var size = getCanvasSize();
        baseLayer = createBaseLayer(resolveBasemap(baseLayerKey));
        var widgets = [];
        if (deckApi && typeof deckApi.ZoomWidget === "function") {
            widgets.push(new deckApi.ZoomWidget({
                placement: "top-left",
                orientation: "vertical",
                transitionDuration: 200
            }));
        }
        deckgl = new deckApi.Deck({
            parent: mapCanvasElement,
            controller: true,
            views: deckApi.MapView ? [new deckApi.MapView({ repeat: true })] : undefined,
            initialViewState: initialViewState,
            width: size.width || undefined,
            height: size.height || undefined,
            layers: baseLayer ? [baseLayer] : [],
            widgets: widgets,
            onViewStateChange: function (params) {
                var viewState = params && params.viewState ? params.viewState : null;
                if (!viewState) {
                    return;
                }
                if (isApplyingViewState) {
                    return;
                }
                var interaction = params && params.interactionState ? params.interactionState : null;
                var isFinal = !interaction || (!interaction.isDragging && !interaction.isZooming && !interaction.isPanning && !interaction.inTransition);
                applyViewState(viewState, { final: isFinal });
            },
            onError: function (error) {
                console.warn("Map GL deck error", error);
            }
        });
        map._deck = deckgl;

        updateMapStatus();
        return map;
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

window.MapController = MapController;
window.WeppMap = MapController;

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

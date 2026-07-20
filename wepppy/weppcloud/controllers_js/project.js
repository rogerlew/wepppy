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
    var TTL_DISABLED_SELECTOR = '[data-project-toggle="ttl_disabled"]';
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
        "project:ttl-disabled:changed",
        "project:ttl-disabled:update:failed",
        "project:mod:updated",
        "project:mod:update:failed",
        "project:unitizer:sync:started",
        "project:unitizer:preferences",
        "project:unitizer:sync:completed",
        "project:unitizer:sync:failed"
    ];
    var MOD_DIAGNOSTIC_SECRET_KEYS_ALT = [
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "key",
        "api_key",
        "apikey",
        "api-key",
        "x-api-key",
        "authorization",
        "set-cookie",
        "cookie",
        "session",
        "email",
        "auth",
        "x-auth-token",
        "x-csrf-token"
    ].join("|");
    var MOD_DIAGNOSTIC_SECRET_HEADER_KEYS_ALT = [
        "authorization",
        "set-cookie",
        "cookie",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-csrf-token"
    ].join("|");
    var MOD_ENABLE_PROPAGATION = {
        geneva: ["roads"]
    };
    var MOD_STICKY_FALSE_FLAGS = {
        openet_ts: true,
        rusle: true,
        debris_flow: true,
        omni_contrasts: true
    };
    var MOD_DIAGNOSTIC_SECRET_KEY_PATTERN = new RegExp(
        "^(?:" + MOD_DIAGNOSTIC_SECRET_KEYS_ALT + ")$",
        "i"
    );

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
        var safeMessage = sanitizeModDiagnosticLine(message || "Error");
        if (error) {
            var safeError = sanitizeModDiagnosticPayload(error);
            if (window.WCHttp && typeof window.WCHttp.isHttpError === "function" && window.WCHttp.isHttpError(error)) {
                var safeDetail = sanitizeModDiagnosticPayload(error.detail || error.body || null);
                if (safeDetail !== undefined && safeDetail !== null) {
                    console.error(safeMessage, safeDetail, safeError);
                } else {
                    console.error(safeMessage, safeError);
                }
            } else {
                console.error(safeMessage, safeError);
            }
        } else {
            console.error(safeMessage);
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

    function normalizeErrorValue(value) {
        if (value === undefined || value === null) {
            return null;
        }
        if (typeof value === "string") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(function (item) { return item === undefined || item === null ? "" : String(item); }).join("\n");
        }
        if (typeof value === "object") {
            if (typeof value.message === "string") {
                return value.message;
            }
            if (typeof value.detail === "string") {
                return value.detail;
            }
            if (typeof value.details === "string") {
                return value.details;
            }
            if (value.details !== undefined) {
                return normalizeErrorValue(value.details);
            }
            try {
                return JSON.stringify(value);
            } catch (err) {
                return String(value);
            }
        }
        return String(value);
    }

    function sanitizeModDiagnosticLine(line) {
        var helper = window.WCBootstrapObservability || null;
        if (helper && typeof helper.sanitizeDiagnosticLine === "function") {
            return helper.sanitizeDiagnosticLine(line);
        }
        var text = String(line === undefined || line === null ? "" : line);
        text = text.replace(new RegExp(
            "\\b(" + MOD_DIAGNOSTIC_SECRET_HEADER_KEYS_ALT + ")\\b\\s*:\\s*[^\\r\\n]*",
            "gi"
        ), "$1: [redacted]");
        text = text.replace(/\bauthorization\b\s*=\s*[^\r\n]*/gi, "authorization=[redacted]");
        text = text.replace(/\b(set-cookie|cookie)\b\s*=\s*[^\r\n]*/gi, "$1=[redacted]");
        text = text.replace(
            new RegExp(
                "([?&](?:" + MOD_DIAGNOSTIC_SECRET_KEYS_ALT + ")=)([^&\\s#]+)",
                "gi"
            ),
            "$1[redacted]"
        );
        text = text.replace(
            new RegExp(
                "(\\b(?:" + MOD_DIAGNOSTIC_SECRET_KEYS_ALT + ")\\b\\s*=\\s*)([^\\s,;&]+)",
                "gi"
            ),
            "$1[redacted]"
        );
        text = text.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[redacted-email]");
        return text;
    }

    function sanitizeModDiagnosticLines(lines) {
        return (Array.isArray(lines) ? lines : []).map(function (line) {
            return sanitizeModDiagnosticLine(line);
        });
    }

    function sanitizeModDiagnosticPayload(value, depth) {
        var level = typeof depth === "number" ? depth : 0;
        if (level > 5) {
            return "[truncated]";
        }
        if (value === undefined || value === null) {
            return value;
        }
        if (typeof value === "string") {
            return sanitizeModDiagnosticLine(value);
        }
        if (
            typeof value === "number"
            || typeof value === "boolean"
            || typeof value === "bigint"
        ) {
            return value;
        }
        if (Array.isArray(value)) {
            var arrayLimit = 40;
            var sanitizedArray = value.slice(0, arrayLimit).map(function (entry) {
                return sanitizeModDiagnosticPayload(entry, level + 1);
            });
            if (value.length > arrayLimit) {
                sanitizedArray.push("... [truncated]");
            }
            return sanitizedArray;
        }
        if (typeof value === "object") {
            var sanitizedObject = {};
            if (value instanceof Error) {
                sanitizedObject.name = value.name || "Error";
                sanitizedObject.message = sanitizeModDiagnosticLine(value.message || "");
                if (value.stack) {
                    sanitizedObject.stack = sanitizeModDiagnosticLine(value.stack);
                }
            }
            Object.keys(value).forEach(function (key) {
                if (MOD_DIAGNOSTIC_SECRET_KEY_PATTERN.test(String(key))) {
                    sanitizedObject[key] = "[redacted]";
                    return;
                }
                sanitizedObject[key] = sanitizeModDiagnosticPayload(value[key], level + 1);
            });
            return sanitizedObject;
        }
        return sanitizeModDiagnosticLine(String(value));
    }

    function formatErrorList(errors) {
        if (!Array.isArray(errors)) {
            return null;
        }
        var parts = [];
        errors.forEach(function (entry) {
            if (entry === undefined || entry === null) {
                return;
            }
            if (typeof entry === "string") {
                parts.push(entry);
                return;
            }
            if (typeof entry.message === "string") {
                parts.push(entry.message);
                return;
            }
            if (typeof entry.detail === "string") {
                parts.push(entry.detail);
                return;
            }
            if (typeof entry.code === "string") {
                parts.push(entry.code);
                return;
            }
            try {
                parts.push(JSON.stringify(entry));
            } catch (err) {
                parts.push(String(entry));
            }
        });
        return parts.length ? parts.join("\n") : null;
    }

    function resolveErrorMessage(response, fallback) {
        if (!response) {
            return fallback || null;
        }
        if (response.error !== undefined) {
            var message = normalizeErrorValue(response.error);
            if (message) {
                return message;
            }
        }
        if (response.errors) {
            var errorList = formatErrorList(response.errors);
            if (errorList) {
                return errorList;
            }
        }
        if (response.message !== undefined) {
            return normalizeErrorValue(response.message);
        }
        if (response.detail !== undefined) {
            return normalizeErrorValue(response.detail);
        }
        return fallback || null;
    }

    function splitStackLines(value) {
        if (value === undefined || value === null) {
            return [];
        }
        if (Array.isArray(value)) {
            var arrayLines = [];
            value.forEach(function (entry) {
                if (entry === undefined || entry === null) {
                    return;
                }
                String(entry).split(/\r?\n/).forEach(function (line) {
                    if (line !== "") {
                        arrayLines.push(line);
                    }
                });
            });
            return arrayLines;
        }
        if (typeof value === "string") {
            return value.split(/\r?\n/).filter(function (line) {
                return line !== "";
            });
        }
        if (typeof value === "object") {
            var objectLines = [];
            if (value.stacktrace !== undefined) {
                objectLines = objectLines.concat(splitStackLines(value.stacktrace));
            }
            if (value.details !== undefined) {
                objectLines = objectLines.concat(splitStackLines(value.details));
            }
            if (value.detail !== undefined) {
                objectLines = objectLines.concat(splitStackLines(value.detail));
            }
            if (value.stack !== undefined) {
                objectLines = objectLines.concat(splitStackLines(value.stack));
            }
            if (value.message !== undefined) {
                objectLines = objectLines.concat(splitStackLines(value.message));
            }
            if (objectLines.length) {
                return objectLines;
            }
        }
        return splitStackLines(normalizeErrorValue(value));
    }

    function truncateLines(lines, maxLines) {
        var list = Array.isArray(lines) ? lines : [];
        var max = typeof maxLines === "number" && maxLines > 0 ? maxLines : 40;
        if (list.length <= max) {
            return list.slice();
        }
        var trimmed = list.slice(0, max);
        trimmed.push("... [truncated]");
        return trimmed;
    }

    function collectModErrorStackLines(response, error) {
        var lines = [];
        var seen = {};

        function appendUnique(source) {
            splitStackLines(source).forEach(function (line) {
                var key = String(line);
                if (seen[key]) {
                    return;
                }
                seen[key] = true;
                lines.push(key);
            });
        }

        if (response && typeof response === "object") {
            appendUnique(response.stacktrace);
            if (response.error && typeof response.error === "object") {
                appendUnique(response.error.details);
                appendUnique(response.error.detail);
            }
            appendUnique(response.detail);
            appendUnique(response.details);
        }

        if (error && typeof error === "object") {
            appendUnique(error.stack);
            appendUnique(error.detail);
            appendUnique(error.stacktrace);
            if (error.body && typeof error.body === "object") {
                appendUnique(error.body.stacktrace);
                appendUnique(error.body.details);
                appendUnique(error.body.detail);
                if (error.body.error && typeof error.body.error === "object") {
                    appendUnique(error.body.error.details);
                    appendUnique(error.body.error.detail);
                }
            }
            if (error.error && typeof error.error === "object") {
                appendUnique(error.error.details);
                appendUnique(error.error.detail);
            }
            appendUnique(error.details);
            if (!error.detail && !error.body) {
                appendUnique(error.message);
            }
        }

        return truncateLines(lines, 80);
    }

    function resolveNestedErrorDetail(error) {
        if (!error || typeof error !== "object") {
            return null;
        }
        if (error.body && typeof error.body === "object") {
            if (error.body.error && typeof error.body.error === "object") {
                if (error.body.error.details !== undefined) {
                    return normalizeErrorValue(error.body.error.details);
                }
                if (error.body.error.detail !== undefined) {
                    return normalizeErrorValue(error.body.error.detail);
                }
            }
            if (error.body.stacktrace !== undefined) {
                return normalizeErrorValue(error.body.stacktrace);
            }
            if (error.body.details !== undefined) {
                return normalizeErrorValue(error.body.details);
            }
            if (error.body.detail !== undefined) {
                return normalizeErrorValue(error.body.detail);
            }
        }
        return null;
    }

    function resolveDiagnosticPayload(error) {
        if (!error || typeof error !== "object") {
            return null;
        }
        if (error.body && typeof error.body === "object") {
            return error.body;
        }
        if (error.detail && typeof error.detail === "object") {
            return error.detail;
        }
        if (
            Object.prototype.hasOwnProperty.call(error, "error")
            || Object.prototype.hasOwnProperty.call(error, "errors")
            || Object.prototype.hasOwnProperty.call(error, "message")
            || Object.prototype.hasOwnProperty.call(error, "detail")
            || Object.prototype.hasOwnProperty.call(error, "details")
            || Object.prototype.hasOwnProperty.call(error, "stacktrace")
        ) {
            return error;
        }
        return null;
    }

    function buildModErrorDiagnostic(modName, desiredState, phase, response, error, fallbackMessage) {
        var status = null;
        var statusText = null;
        if (error && error.status !== undefined && error.status !== null) {
            status = error.status;
        } else if (response && response.status !== undefined && response.status !== null) {
            status = response.status;
        }
        if (error && error.statusText) {
            statusText = error.statusText;
        } else if (response && response.statusText) {
            statusText = response.statusText;
        }
        var errorPayload = resolveDiagnosticPayload(error);
        var url = (error && error.url) || (response && response.url) || null;
        var detail = null;
        var nestedDetail = resolveNestedErrorDetail(error);
        if (nestedDetail) {
            detail = nestedDetail;
        }
        if (error && error.detail !== undefined) {
            if (!detail && error.detail && typeof error.detail === "object") {
                if (error.detail.details !== undefined) {
                    detail = normalizeErrorValue(error.detail.details);
                } else if (error.detail.detail !== undefined) {
                    detail = normalizeErrorValue(error.detail.detail);
                }
            }
            if (!detail || (typeof detail === "string" && detail.trim() === "")) {
                detail = normalizeErrorValue(error.detail);
            }
        }
        if (!detail && error && error.body !== undefined) {
            detail = normalizeErrorValue(error.body);
        }
        if (!detail && errorPayload) {
            detail = resolveErrorMessage(errorPayload, null);
        }
        if (!detail && response && typeof response === "object" && response.error && typeof response.error === "object") {
            if (response.error.details !== undefined) {
                detail = normalizeErrorValue(response.error.details);
            } else if (response.error.detail !== undefined) {
                detail = normalizeErrorValue(response.error.detail);
            }
        }
        if (!detail) {
            detail = resolveErrorMessage(response, null);
        }
        var message = resolveErrorMessage(response, null);
        if (!message && errorPayload) {
            message = resolveErrorMessage(errorPayload, null);
        }
        if (!message && error && error.message) {
            message = error.message;
        }
        if (nestedDetail && message && detail === message) {
            detail = nestedDetail;
        }
        if (!message) {
            message = fallbackMessage || "Unable to update module.";
        }
        var sanitizedMessage = sanitizeModDiagnosticLine(message);
        var sanitizedDetail = detail ? sanitizeModDiagnosticLine(detail) : null;
        var sanitizedUrl = url ? sanitizeModDiagnosticLine(url) : null;
        var sanitizedStack = sanitizeModDiagnosticLines(collectModErrorStackLines(response, error));
        return {
            mod: modName,
            enabled: Boolean(desiredState),
            phase: phase || "unknown",
            message: sanitizedMessage,
            detail: sanitizedDetail,
            status: status,
            statusText: statusText,
            url: sanitizedUrl,
            stack: sanitizedStack
        };
    }

    function formatModErrorDiagnosticMessage(diagnostic) {
        var lines = [];
        lines.push("project.set_mod failed");
        lines.push(
            "mod="
            + diagnostic.mod
            + " enabled="
            + String(Boolean(diagnostic.enabled))
            + " phase="
            + diagnostic.phase
        );
        if (diagnostic.status !== null && diagnostic.status !== undefined) {
            var statusLine = "status=" + String(diagnostic.status);
            if (diagnostic.statusText) {
                statusLine += " " + diagnostic.statusText;
            }
            lines.push(statusLine);
        }
        if (diagnostic.url) {
            lines.push("url=" + diagnostic.url);
        }
        if (diagnostic.message) {
            lines.push("message=" + diagnostic.message);
        }
        if (diagnostic.detail) {
            lines.push("detail=" + diagnostic.detail);
        }
        if (diagnostic.stack && diagnostic.stack.length) {
            lines.push("stacktrace:");
            diagnostic.stack.forEach(function (line) {
                lines.push(line);
            });
        }
        return lines.join("\n");
    }

    function emitRecorderEvent(stage, payload) {
        if (!window.WCRecorder || typeof window.WCRecorder.emit !== "function") {
            return;
        }
        try {
            window.WCRecorder.emit(stage, payload);
        } catch (err) {
            console.warn("Failed to emit recorder event", err);
        }
    }

    function isSuccess(response) {
        return response && !response.error && !response.errors;
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
            ttlDisabled: readToggleState(dom, TTL_DISABLED_SELECTOR, false),
            mods: Array.isArray(runContext.mods && runContext.mods.list)
                ? runContext.mods.list.slice()
                : []
        };

        var MOD_BOOTSTRAP_MAP = {
            rap_ts: function (ctx) {
                bootstrapControllerSymbol(window.RAP_TS, ctx);
            },
            openet_ts: function (ctx) {
                bootstrapControllerSymbol(window.OPENET_TS, ctx);
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
            omni_contrasts: function (ctx) {
                bootstrapControllerSymbol(window.Omni, ctx, { forceRemount: true });
                bootstrapControllerSymbol(window.OmniContrastOverlays, ctx, { forceRemount: true });
            },
            dss_export: function (ctx) {
                bootstrapControllerSymbol(window.DssExport, ctx);
            },
            debris_flow: function (ctx) {
                bootstrapControllerSymbol(window.DebrisFlow, ctx);
            },
            roads: function (ctx) {
                bootstrapControllerSymbol(window.Roads, ctx);
                bootstrapControllerSymbol(window.RoadsMapOverlay, ctx);
            },
            geneva: function (ctx) {
                bootstrapControllerSymbol(window.Geneva, ctx);
            },
            features_export: function (ctx) {
                bootstrapControllerSymbol(window.FeaturesExport, ctx);
            },
            path_ce: function (ctx) {
                bootstrapControllerSymbol(window.PathCE, ctx);
            },
            observed: function (ctx) {
                bootstrapControllerSymbol(window.Observed, ctx);
            },
            ag_fields: function (ctx) {
                bootstrapControllerSymbol(window.AgFields, ctx);
            },
            rusle: function (ctx) {
                bootstrapControllerSymbol(window.Rusle, ctx, { forceRemount: true });
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

        function normalizeModList(mods) {
            var seen = {};
            var normalized = [];
            if (!Array.isArray(mods)) {
                return normalized;
            }
            mods.forEach(function (entry) {
                var modName = typeof entry === "string" ? entry.trim() : "";
                if (!modName || seen[modName]) {
                    return;
                }
                seen[modName] = true;
                normalized.push(modName);
            });
            return normalized;
        }

        function collectDomModNames() {
            var seen = {};
            function track(name) {
                if (!name || seen[name]) {
                    return;
                }
                seen[name] = true;
            }
            Array.prototype.forEach.call(document.querySelectorAll(MOD_SELECTOR), function (input) {
                track(input.getAttribute("data-project-mod"));
            });
            Array.prototype.forEach.call(document.querySelectorAll("[data-mod-nav]"), function (node) {
                track(node.getAttribute("data-mod-nav"));
            });
            Array.prototype.forEach.call(document.querySelectorAll("[data-mod-section]"), function (node) {
                track(node.getAttribute("data-mod-section"));
            });
            return Object.keys(seen);
        }

        function collectKnownModNames() {
            var seen = {};
            function track(name) {
                if (!name || seen[name]) {
                    return;
                }
                seen[name] = true;
            }
            collectDomModNames().forEach(track);
            if (window.runContext && window.runContext.mods) {
                normalizeModList(window.runContext.mods.list || []).forEach(track);
                if (window.runContext.mods.flags && typeof window.runContext.mods.flags === "object") {
                    Object.keys(window.runContext.mods.flags).forEach(track);
                }
            }
            return Object.keys(seen);
        }

        function resolveAllowEnableMods(modName, enabled) {
            if (!enabled || !modName) {
                return [];
            }
            var allowed = [modName];
            if (Object.prototype.hasOwnProperty.call(MOD_ENABLE_PROPAGATION, modName)) {
                allowed = allowed.concat(MOD_ENABLE_PROPAGATION[modName] || []);
            }
            return normalizeModList(allowed);
        }

        function setRunContextModsList(mods, options) {
            var normalizedMods = normalizeModList(mods);
            if (typeof window.runContext !== "object" || !window.runContext) {
                return normalizedMods;
            }
            var opts = options || {};
            var ctx = window.runContext.mods || {};
            var allowEnableMods = normalizeModList(opts.allowEnableMods || []);
            var allowEnableMap = {};
            allowEnableMods.forEach(function (modName) {
                allowEnableMap[modName] = true;
            });
            var existingFlags = ctx.flags && typeof ctx.flags === "object" ? ctx.flags : {};
            var domMods = collectDomModNames();
            var domModMap = {};
            domMods.forEach(function (modName) {
                domModMap[modName] = true;
            });
            var flags = {};
            Object.keys(existingFlags).forEach(function (key) {
                flags[key] = false;
            });
            domMods.forEach(function (modName) {
                if (!Object.prototype.hasOwnProperty.call(flags, modName)) {
                    flags[modName] = false;
                }
            });
            normalizedMods.forEach(function (modName) {
                var hasExisting = Object.prototype.hasOwnProperty.call(existingFlags, modName);
                if (hasExisting) {
                    if (existingFlags[modName]) {
                        flags[modName] = true;
                        return;
                    }
                    if (allowEnableMap[modName]) {
                        flags[modName] = true;
                        return;
                    }
                    if (Object.prototype.hasOwnProperty.call(MOD_STICKY_FALSE_FLAGS, modName)) {
                        flags[modName] = false;
                        return;
                    }
                    flags[modName] = true;
                    return;
                }
                if (
                    Object.prototype.hasOwnProperty.call(MOD_STICKY_FALSE_FLAGS, modName)
                    && !allowEnableMap[modName]
                ) {
                    flags[modName] = false;
                    return;
                }
                if (domModMap[modName]) {
                    flags[modName] = true;
                    return;
                }
                flags[modName] = true;
            });
            ctx.list = normalizedMods;
            ctx.flags = flags;
            window.runContext.mods = ctx;
            return normalizedMods;
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
            setRunContextModsList(list, {
                allowEnableMods: resolveAllowEnableMods(modName, enabled)
            });
        }

        function reconcileRunContextModsFromResponse(response, modName, enabled) {
            var content = response && typeof response === "object" ? (response.Content || response.content || null) : null;
            if (content && Array.isArray(content.mods)) {
                return setRunContextModsList(content.mods, {
                    allowEnableMods: resolveAllowEnableMods(modName, enabled)
                });
            }
            updateRunContextMods(modName, enabled);
            if (window.runContext && window.runContext.mods && Array.isArray(window.runContext.mods.list)) {
                return window.runContext.mods.list.slice();
            }
            return normalizeModList(enabled ? [modName] : []);
        }

        function syncModInputsAndNav(modList) {
            var enabledMods = {};
            var flags = (window.runContext && window.runContext.mods && window.runContext.mods.flags)
                ? window.runContext.mods.flags
                : {};
            normalizeModList(modList).forEach(function (modName) {
                enabledMods[modName] = true;
            });

            function isModActiveVisible(modName) {
                if (!enabledMods[modName]) {
                    return false;
                }
                if (Object.prototype.hasOwnProperty.call(flags, modName)) {
                    return Boolean(flags[modName]);
                }
                if (Object.prototype.hasOwnProperty.call(MOD_STICKY_FALSE_FLAGS, modName)) {
                    return false;
                }
                return true;
            }

            function syncModAvailability(modInput, modName) {
                var authorized = modInput.getAttribute("data-project-mod-authorized") !== "false";
                var required = (modInput.getAttribute("data-project-mod-requires") || "")
                    .split(",")
                    .map(function (token) { return token.trim(); })
                    .filter(Boolean);
                var active = Boolean(enabledMods[modName]);
                var missing = required.filter(function (requiredMod) {
                    return !enabledMods[requiredMod];
                });
                var reason = "";
                if (!authorized) {
                    reason = "Not Authorized";
                } else if (!active && missing.length) {
                    reason = "Enable " + missing.map(function (requiredMod) {
                        var requiredInput = document.querySelector(
                            '[data-project-mod="' + requiredMod + '"]'
                        );
                        if (requiredInput && requiredInput.parentElement) {
                            var label = requiredInput.parentElement.querySelector("span span");
                            if (label && label.textContent) {
                                return label.textContent.trim();
                            }
                        }
                        return requiredMod.replace(/_/g, " ").replace(/\b\w/g, function (char) {
                            return char.toUpperCase();
                        });
                    }).join(", ") + " first";
                }
                modInput.disabled = !authorized || (!active && missing.length > 0);
                var reasonNode = document.querySelector(
                    '[data-project-mod-reason="' + modName + '"]'
                );
                if (reasonNode) {
                    reasonNode.textContent = reason;
                    reasonNode.hidden = !reason;
                }
            }

            Array.prototype.forEach.call(document.querySelectorAll(MOD_SELECTOR), function (modInput) {
                var modName = modInput.getAttribute("data-project-mod");
                if (!modName) {
                    return;
                }
                modInput.checked = Boolean(enabledMods[modName]);
                syncModAvailability(modInput, modName);
            });
            collectKnownModNames().forEach(function (modName) {
                toggleModNav(modName, isModActiveVisible(modName));
            });
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
                return Promise.resolve({ skipped: true });
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
                return Promise.resolve({ skipped: true });
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

        project.set_ttl_disabled = function (stateValue, options) {
            options = options || {};
            var desiredState = Boolean(stateValue);
            var previous = readToggleState(dom, TTL_DISABLED_SELECTOR, state.ttlDisabled);

            return http.postJson(url_for_run("tasks/set_ttl_disabled"), { ttl_disabled: desiredState }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    syncToggleState(dom, TTL_DISABLED_SELECTOR, desiredState);
                    state.ttlDisabled = desiredState;
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "TTL deletion disabled for this project."
                            : "TTL deletion re-enabled for this project.";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:ttl-disabled:changed", {
                        ttlDisabled: desiredState,
                        previous: previous,
                        response: response
                    });
                } else {
                    syncToggleState(dom, TTL_DISABLED_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error updating TTL deletion state.", { duration: null });
                    }
                    emitEvent(emitter, "project:ttl-disabled:update:failed", {
                        attempted: desiredState,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                syncToggleState(dom, TTL_DISABLED_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating TTL deletion state.", { duration: null });
                }
                notifyError("Error updating TTL deletion state", error);
                emitEvent(emitter, "project:ttl-disabled:update:failed", {
                    attempted: desiredState,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };
        project.setTtlDisabled = project.set_ttl_disabled;

        project.load_mod_section = function (modName) {
            var endpoint = "view/mod/" + encodeURIComponent(modName);
            return http.getJson(url_for_run(endpoint)).then(function (response) {
                if (response && !response.error && !response.errors) {
                    return response.Content || response.content || response;
                }
                return Promise.reject(response || { error: { message: "Failed to load module section" } });
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
            var reconciledMods = [];
            var effectiveEnabled = desiredState;
            var priorMods = normalizeModList(
                (window.runContext && window.runContext.mods && window.runContext.mods.list) || []
            );
            var priorEnabled = priorMods.indexOf(normalized) !== -1;

            function restoreInput() {
                syncModInputsAndNav(priorMods);
                if (input) {
                    input.checked = Boolean(priorEnabled);
                }
            }

            function reportFailure(phase, response, error, fallbackMessage, context) {
                var failureContext = context || {};
                var failedMod = failureContext.mod || normalized;
                var failedEnabled = typeof failureContext.enabled === "boolean"
                    ? failureContext.enabled
                    : desiredState;
                var diagnostic = buildModErrorDiagnostic(
                    failedMod,
                    failedEnabled,
                    phase,
                    response,
                    error,
                    fallbackMessage
                );
                var stackPayload = { error: { message: diagnostic.message } };
                if (diagnostic.detail) {
                    stackPayload.detail = diagnostic.detail;
                }
                if (diagnostic.stack && diagnostic.stack.length) {
                    stackPayload.stacktrace = diagnostic.stack;
                }
                project.pushResponseStacktrace(project, stackPayload);
                if (options.notify !== false) {
                    project.notifyCommandBar(formatModErrorDiagnosticMessage(diagnostic), { duration: null });
                }
                emitRecorderEvent("project_mod_toggle_error", {
                    category: "mod-toggle",
                    mod: diagnostic.mod,
                    enabled: diagnostic.enabled,
                    phase: diagnostic.phase,
                    status: diagnostic.status,
                    statusText: diagnostic.statusText,
                    url: diagnostic.url,
                    message: diagnostic.message,
                    detail: diagnostic.detail,
                    stacktrace: diagnostic.stack
                });
                emitEvent(emitter, "project:mod:update:failed", {
                    mod: diagnostic.mod,
                    enabled: diagnostic.enabled,
                    phase: phase,
                    response: response ? sanitizeModDiagnosticPayload(response) : null,
                    error: error ? sanitizeModDiagnosticPayload(error) : null,
                    diagnostic: diagnostic
                });
                return diagnostic;
            }

            function resolveAdditionalEnabledMods() {
                var priorMap = {};
                priorMods.forEach(function (modKey) {
                    priorMap[modKey] = true;
                });
                return normalizeModList(reconciledMods).filter(function (modKey) {
                    return modKey !== normalized && !priorMap[modKey];
                });
            }

            function hasModSectionContainer(modKey) {
                return Boolean(document.querySelector('[data-mod-section="' + modKey + '"]'));
            }

            function loadAndBootstrapAdditionalMods(modKeys, response) {
                var queue = normalizeModList(modKeys).filter(function (modKey) {
                    return modKey !== normalized && hasModSectionContainer(modKey);
                });
                var dependencyStatus = { failed: false, diagnostic: null };
                var sequence = Promise.resolve();
                queue.forEach(function (modKey) {
                    sequence = sequence.then(function () {
                        return project.load_mod_section(modKey).then(function (payload) {
                            var html = payload && payload.html ? payload.html : "";
                            toggleModSection(modKey, true, html);
                            try {
                                bootstrapModController(modKey);
                            } catch (dependencyBootstrapError) {
                                notifyError("Error bootstrapping dependent module section", dependencyBootstrapError);
                                var bootstrapDiagnostic = reportFailure(
                                    "bootstrap",
                                    response,
                                    dependencyBootstrapError,
                                    "Dependent module enabled but failed to initialize.",
                                    { mod: modKey, enabled: true }
                                );
                                if (!dependencyStatus.failed) {
                                    dependencyStatus.failed = true;
                                    dependencyStatus.diagnostic = bootstrapDiagnostic;
                                }
                            }
                        }).catch(function (dependencyRenderError) {
                            notifyError("Error rendering dependent module section", dependencyRenderError);
                            var renderDiagnostic = reportFailure(
                                "render",
                                response,
                                dependencyRenderError,
                                "Dependent module enabled but failed to render.",
                                { mod: modKey, enabled: true }
                            );
                            if (!dependencyStatus.failed) {
                                dependencyStatus.failed = true;
                                dependencyStatus.diagnostic = renderDiagnostic;
                            }
                        });
                    });
                });
                return sequence.then(function () {
                    return dependencyStatus;
                });
            }

            if (input) {
                input.disabled = true;
            }

            return http.request(url_for_run("tasks/set_mod"), {
                method: "POST",
                json: { mod: normalized, enabled: desiredState }
            }).then(function (result) {
                var response = unpackResponse(result);
                if (!isSuccess(response)) {
                    restoreInput();
                    reportFailure("response", response, null, "Unable to update module.");
                    return response;
                }

                var label = response.Content && response.Content.label ? response.Content.label : normalized;
                reconciledMods = reconcileRunContextModsFromResponse(response, normalized, desiredState);
                effectiveEnabled = reconciledMods.indexOf(normalized) !== -1;

                var applyUI = function (html, applyOptions) {
                    var opts = applyOptions || {};
                    syncModInputsAndNav(reconciledMods);
                    toggleModSection(normalized, effectiveEnabled, html);
                    if (opts.emitUpdated !== false) {
                        emitEvent(emitter, "project:mod:updated", {
                            mod: normalized,
                            enabled: effectiveEnabled,
                            desired: desiredState,
                            label: label,
                            response: response
                        });
                    }
                };

                if (desiredState && effectiveEnabled) {
                    return project.load_mod_section(normalized).then(function (payload) {
                        var html = payload && payload.html ? payload.html : "";
                        applyUI(html, { emitUpdated: false });
                        // Allow DOM to settle before bootstrapping controller
                        return new Promise(function (resolve) {
                            setTimeout(function () {
                                try {
                                    bootstrapModController(normalized);
                                } catch (bootstrapError) {
                                    if (input) {
                                        input.disabled = false;
                                        input.checked = Boolean(effectiveEnabled);
                                    }
                                    notifyError("Error bootstrapping module section", bootstrapError);
                                    var bootstrapDiagnostic = reportFailure(
                                        "bootstrap",
                                        response,
                                        bootstrapError,
                                        "Module enabled but failed to initialize."
                                    );
                                    resolve({
                                        error: {
                                            message: bootstrapDiagnostic.message,
                                            detail: bootstrapDiagnostic.detail,
                                            details: bootstrapDiagnostic.detail,
                                            phase: "bootstrap"
                                        },
                                        Content: response && response.Content ? response.Content : null,
                                        response: response || null,
                                        diagnostic: bootstrapDiagnostic
                                    });
                                    return;
                                }
                                var dependentMods = resolveAdditionalEnabledMods();
                                loadAndBootstrapAdditionalMods(dependentMods, response).then(function (dependencyStatus) {
                                    if (input) {
                                        input.checked = Boolean(effectiveEnabled);
                                        input.disabled = false;
                                    }
                                    if (dependencyStatus && dependencyStatus.failed && dependencyStatus.diagnostic) {
                                        var dependencyDiagnostic = dependencyStatus.diagnostic;
                                        resolve({
                                            error: {
                                                message: dependencyDiagnostic.message,
                                                detail: dependencyDiagnostic.detail,
                                                details: dependencyDiagnostic.detail,
                                                phase: "dependency"
                                            },
                                            Content: response && response.Content ? response.Content : null,
                                            response: response || null,
                                            dependency_error: {
                                                mod: dependencyDiagnostic.mod,
                                                phase: dependencyDiagnostic.phase,
                                                message: dependencyDiagnostic.message,
                                                detail: dependencyDiagnostic.detail,
                                                details: dependencyDiagnostic.detail
                                            },
                                            diagnostic: dependencyDiagnostic
                                        });
                                        return;
                                    }
                                    if (options.notify !== false) {
                                        var enabledVerb = effectiveEnabled ? "enabled" : "disabled";
                                        project.notifyCommandBar(label + " " + enabledVerb + ".");
                                    }
                                    emitEvent(emitter, "project:mod:updated", {
                                        mod: normalized,
                                        enabled: effectiveEnabled,
                                        desired: desiredState,
                                        label: label,
                                        response: response
                                    });
                                    resolve(response);
                                });
                            }, 0);
                        });
                    }).catch(function (error) {
                        syncModInputsAndNav(reconciledMods);
                        if (input) {
                            input.disabled = false;
                            input.checked = Boolean(effectiveEnabled);
                        }
                        notifyError("Error rendering module section", error);
                        var diagnostic = reportFailure(
                            "render",
                            response,
                            error,
                            "Module enabled but failed to render. Refresh to continue."
                        );
                        return {
                            error: {
                                message: diagnostic.message,
                                detail: diagnostic.detail,
                                details: diagnostic.detail,
                                phase: "render"
                            },
                            Content: response && response.Content ? response.Content : null,
                            response: response || null,
                            render_error: {
                                message: diagnostic.message,
                                detail: diagnostic.detail,
                                details: diagnostic.detail,
                                phase: "render"
                            },
                            diagnostic: diagnostic
                        };
                    });
                }

                applyUI(undefined, { emitUpdated: true });
                if (options.notify !== false) {
                    var verb = effectiveEnabled ? "enabled" : "disabled";
                    project.notifyCommandBar(label + " " + verb + ".");
                }
                return response;
            }).catch(function (error) {
                restoreInput();
                notifyError("Error updating module state", error);
                reportFailure("request", null, error, "Error updating module.");
                return null;
            });
        };

        project.clear_locks = function () {
            return http.request(url_for_run("tasks/clear_locks"), {
                method: "GET",
                params: { _: Date.now() }
            }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
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
                if (response && !response.error && !response.errors) {
                    var profileRoot = response.profile && response.profile.profile_root;
                    var message = "Profile draft promoted.";
                    if (profileRoot) {
                        message += "\nSaved to: " + profileRoot;
                    }
                    window.alert(message);
                } else {
                    var errorMessage = resolveErrorMessage(response, "Error promoting profile draft.");
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

        dom.delegate(document, "change", TTL_DISABLED_SELECTOR, function (event, target) {
            project.set_ttl_disabled(target.checked);
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

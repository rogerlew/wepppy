/* ----------------------------------------------------------------------------
 * StatusStream standalone bundle
 * NOTE: Generated via build_controllers_js.py from
 *       wepppy/weppcloud/controllers_js/status_stream.js
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    if (global.WCHttp) { return; }

    var SAFE_METHODS = ["GET", "HEAD", "OPTIONS", "TRACE"];
    var DEFAULT_ACCEPT = "application/json, text/plain;q=0.9";
    var DEFAULT_TIMEOUT_MS = 0;
    var doc = global.document;
    var http = {};
    var sessionTokenCache = {};
    var rqEngineTokenEntry = null;

    function isAbsoluteUrl(url) {
        return /^([a-z][a-z\d+\-.]*:)?\/\//i.test(url);
    }

    function trimTrailingSlash(value) {
        return value ? value.replace(/\/+$/, "") : "";
    }

    function trimLeadingSlash(value) {
        return value ? value.replace(/^\/+/, "") : "";
    }

    function normalizeSitePrefix(value) {
        if (!value) {
            return "";
        }
        var text = String(value).trim();
        if (!text || text === "/") {
            return "";
        }
        if (text.charAt(0) !== "/") {
            text = "/" + text;
        }
        return text.replace(/\/+$/, "");
    }

    function deriveSitePrefix(pathname) {
        var path = typeof pathname === "string" ? pathname : "";
        if (!path) {
            return "";
        }
        var runsIndex = path.indexOf("/runs/");
        if (runsIndex !== -1) {
            return normalizeSitePrefix(path.slice(0, runsIndex));
        }
        if (path.indexOf("/weppcloud/") === 0 || path === "/weppcloud") {
            return "/weppcloud";
        }
        return "";
    }

    function resolveSitePrefix() {
        var configured = normalizeSitePrefix(typeof global.site_prefix === "string" ? global.site_prefix : "");
        if (configured) {
            return configured;
        }
        if (doc && doc.body && doc.body.dataset) {
            var bodyPrefix = normalizeSitePrefix(doc.body.dataset.sitePrefix);
            if (bodyPrefix) {
                return bodyPrefix;
            }
        }
        if (global.location && typeof global.location.pathname === "string") {
            return deriveSitePrefix(global.location.pathname);
        }
        return "";
    }

    function applySitePrefix(url) {
        if (!url) {
            throw new Error("WCHttp.request requires a URL.");
        }
        var prefix = resolveSitePrefix();
        if (url === "/rq-engine" || url.indexOf("/rq-engine/") === 0) {
            return url;
        }
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

    function _sessionCacheKey(runId, config) {
        return String(runId || "") + "::" + String(config || "");
    }

    function _isSessionTokenValid(entry) {
        if (!entry || !entry.token || !entry.expiresAt) {
            return false;
        }
        return (Date.now() / 1000) < (entry.expiresAt - 30);
    }

    function _isRqEngineTokenValid(entry) {
        if (!entry || !entry.token || !entry.expiresAt) {
            return false;
        }
        return (Date.now() / 1000) < (entry.expiresAt - 30);
    }

    function getRqEngineToken(options) {
        if (_isRqEngineTokenValid(rqEngineTokenEntry)) {
            return Promise.resolve(rqEngineTokenEntry.token);
        }
        if (rqEngineTokenEntry && rqEngineTokenEntry.promise) {
            return rqEngineTokenEntry.promise;
        }

        var opts = options ? Object.assign({}, options) : {};
        rqEngineTokenEntry = rqEngineTokenEntry || {};
        rqEngineTokenEntry.promise = http.request("/api/auth/rq-engine-token", {
            method: "POST",
            credentials: "same-origin",
            timeoutMs: opts.timeoutMs
        })
            .then(function (result) {
                var body = result.body || {};
                if (!body || !body.token) {
                    throw new HttpError("RQ-engine token missing from response", {
                        url: result.url,
                        status: result.status,
                        statusText: result.statusText,
                        body: body,
                        response: result.response
                    });
                }
                rqEngineTokenEntry.token = body.token;
                rqEngineTokenEntry.expiresAt = Number(body.expires_at || 0);
                if (!rqEngineTokenEntry.expiresAt) {
                    rqEngineTokenEntry.expiresAt = (Date.now() / 1000) + 600;
                }
                rqEngineTokenEntry.promise = null;
                return rqEngineTokenEntry.token;
            })
            .catch(function (error) {
                if (rqEngineTokenEntry) {
                    rqEngineTokenEntry.promise = null;
                }
                throw error;
            });

        return rqEngineTokenEntry.promise;
    }

    function getSessionToken(runId, config, options) {
        if (!runId || !config) {
            return Promise.reject(new HttpError("Run ID and config are required for session tokens"));
        }
        var key = _sessionCacheKey(runId, config);
        var entry = sessionTokenCache[key];
        if (_isSessionTokenValid(entry)) {
            return Promise.resolve(entry.token);
        }
        if (entry && entry.promise) {
            return entry.promise;
        }

        var opts = options ? Object.assign({}, options) : {};
        var urlForRun = global.url_for_run;
        if (typeof urlForRun !== "function") {
            throw new Error("url_for_run is required to build session token URLs");
        }
        var url = urlForRun("session-token", {
            prefix: "/rq-engine/api",
            runId: runId,
            config: config
        });

        entry = entry || {};
        entry.promise = http.request(url, { method: "POST", credentials: "same-origin", timeoutMs: opts.timeoutMs })
            .then(function (result) {
                var body = result.body || {};
                if (!body || !body.token) {
                    throw new HttpError("Session token missing from response", {
                        url: result.url,
                        status: result.status,
                        statusText: result.statusText,
                        body: body,
                        response: result.response
                    });
                }
                entry.token = body.token;
                entry.expiresAt = Number(body.expires_at || 0);
                entry.scopes = body.scopes || null;
                entry.promise = null;
                sessionTokenCache[key] = entry;
                return entry.token;
            })
            .catch(function (error) {
                entry.promise = null;
                sessionTokenCache[key] = entry;
                if (!isHttpError(error) || (error.status !== 401 && error.status !== 403)) {
                    throw error;
                }
                return getRqEngineToken(opts).then(function (fallbackToken) {
                    entry.token = fallbackToken;
                    entry.expiresAt = (Date.now() / 1000) + 600;
                    entry.scopes = null;
                    sessionTokenCache[key] = entry;
                    return fallbackToken;
                }).catch(function (fallbackError) {
                    fallbackError.rqEngineFallbackTried = true;
                    throw fallbackError;
                });
            });

        sessionTokenCache[key] = entry;
        return entry.promise;
    }

    function clearSessionToken(runId, config) {
        if (!runId && !config) {
            sessionTokenCache = {};
            return;
        }
        delete sessionTokenCache[_sessionCacheKey(runId, config)];
    }

    function clearRqEngineToken() {
        rqEngineTokenEntry = null;
    }

    function resolveRunContext(options) {
        var runId = options && options.runId ? String(options.runId) : "";
        var config = options && options.config ? String(options.config) : "";

        if (!runId) {
            if (typeof global.runid === "string" && global.runid) {
                runId = global.runid;
            } else if (typeof global.runId === "string" && global.runId) {
                runId = global.runId;
            }
        }

        if (!config) {
            if (typeof global.config === "string" && global.config) {
                config = global.config;
            }
        }

        if (!runId || !config) {
            var path = global.location && typeof global.location.pathname === "string" ? global.location.pathname : "";
            var prefix = typeof global.site_prefix === "string" ? global.site_prefix : "";
            if (prefix) {
                var normalizedPrefix = prefix.charAt(0) === "/" ? prefix : "/" + prefix;
                normalizedPrefix = normalizedPrefix.replace(/\/+$/, "");
                if (normalizedPrefix && path.indexOf(normalizedPrefix) === 0) {
                    path = path.slice(normalizedPrefix.length);
                }
            }

            var parts = path.split("/").filter(function (segment) {
                return segment.length > 0;
            });
            var runsIndex = parts.indexOf("runs");
            if (runsIndex !== -1 && parts.length > runsIndex + 2) {
                if (!runId) {
                    runId = decodeURIComponent(parts[runsIndex + 1]);
                }
                if (!config) {
                    config = decodeURIComponent(parts[runsIndex + 2]);
                }
            }
        }

        return { runId: runId, config: config };
    }

    function requestWithSessionToken(url, options) {
        var opts = options ? Object.assign({}, options) : {};
        var context = resolveRunContext(opts);
        if (!context.runId || !context.config) {
            return Promise.reject(new HttpError("Run ID and config are required for session tokens"));
        }

        var tokenOptions = {};
        if (opts.tokenTimeoutMs !== undefined) {
            tokenOptions.timeoutMs = opts.tokenTimeoutMs;
        } else if (opts.timeoutMs !== undefined) {
            tokenOptions.timeoutMs = opts.timeoutMs;
        }

        delete opts.runId;
        delete opts.config;
        delete opts.tokenTimeoutMs;

        function requestWithBearer(token) {
            var headers = opts.headers ? Object.assign({}, opts.headers) : {};
            headers.Authorization = "Bearer " + token;
            opts.headers = headers;
            return request(url, opts);
        }

        return getSessionToken(context.runId, context.config, tokenOptions)
            .then(requestWithBearer)
            .catch(function (error) {
                if (error && error.rqEngineFallbackTried) {
                    throw error;
                }
                if (!isHttpError(error) || (error.status !== 401 && error.status !== 403)) {
                    throw error;
                }
                clearSessionToken(context.runId, context.config);
                clearRqEngineToken();
                return getRqEngineToken(tokenOptions).then(requestWithBearer).catch(function (fallbackError) {
                    fallbackError.rqEngineFallbackTried = true;
                    throw fallbackError;
                });
            });
    }

    function requestWithUserToken(url, options) {
        var opts = options ? Object.assign({}, options) : {};
        return getRqEngineToken().then(function (token) {
            var headers = opts.headers ? Object.assign({}, opts.headers) : {};
            headers.Authorization = "Bearer " + token;
            opts.headers = headers;
            return request(url, opts);
        });
    }

    function postJsonWithSessionToken(url, payload, options) {
        var opts = options ? Object.assign({}, options) : {};
        opts.method = opts.method || "POST";
        opts.json = payload;
        return requestWithSessionToken(url, opts);
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

    function isPlainObject(value) {
        return Object.prototype.toString.call(value) === "[object Object]";
    }

    function normalizeErrorValue(value) {
        if (value === undefined || value === null) {
            return value;
        }
        if (typeof value === "string") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(function (item) {
                return item === undefined || item === null ? "" : String(item);
            }).join("\n");
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

    function normalizeResponsePayload(payload) {
        if (!payload || typeof payload !== "object") {
            return payload;
        }
        if (Array.isArray(payload) || !isPlainObject(payload)) {
            return payload;
        }

        if (!Object.prototype.hasOwnProperty.call(payload, "job_id")) {
            if (Array.isArray(payload.job_ids) && payload.job_ids.length > 0) {
                payload.job_id = payload.job_ids[0];
            }
        }

        if (!Object.prototype.hasOwnProperty.call(payload, "error_message")) {
            var errorValue = Object.prototype.hasOwnProperty.call(payload, "error") ? payload.error : undefined;
            var errorMessage = normalizeErrorValue(errorValue);
            if (!errorMessage) {
                errorMessage = formatErrorList(payload.errors);
            }
            if (errorMessage !== undefined && errorMessage !== null) {
                payload.error_message = errorMessage;
            }
        }
        if (!Object.prototype.hasOwnProperty.call(payload, "message") &&
            Object.prototype.hasOwnProperty.call(payload, "error_message")) {
            payload.message = payload.error_message;
        }

        return payload;
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

    function resolveErrorDetail(body) {
        if (!body || typeof body !== "object") {
            return null;
        }
        if (body.error) {
            if (typeof body.error === "string") {
                return body.error;
            }
            if (body.error && typeof body.error.message === "string") {
                return body.error.message;
            }
            if (body.error && typeof body.error.detail === "string") {
                return body.error.detail;
            }
            if (body.error && Object.prototype.hasOwnProperty.call(body.error, "details")) {
                return body.error.details;
            }
        }
        if (body.errors) {
            var errorList = formatErrorList(body.errors);
            if (errorList) {
                return errorList;
            }
        }
        if (typeof body.message === "string") {
            return body.message;
        }
        if (typeof body.detail === "string") {
            return body.detail;
        }
        return null;
    }

    function buildError(url, response, body, cause) {
        var message = "HTTP request failed";
        var detail = null;
        if (response) {
            message = "HTTP " + response.status + " " + (response.statusText || "");
            if (body && typeof body === "object") {
                var resolved = resolveErrorDetail(body);
                detail = resolved !== null ? resolved : body;
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
                    parsed = normalizeResponsePayload(parsed);
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
                    return normalizeResponsePayload(JSON.parse(body));
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
            return normalizeResponsePayload(body);
        });
    }

    function postJson(url, payload, options) {
        var opts = options ? Object.assign({}, options) : {};
        opts.method = opts.method || "POST";
        opts.json = payload;
        return http.request(url, opts);
    }

    function requestWithFallback(primaryUrl, fallbackUrl, options) {
        return http.request(primaryUrl, options || {}).catch(function (primaryError) {
            return http.request(fallbackUrl, options || {}).catch(function (fallbackError) {
                fallbackError.primaryError = primaryError;
                throw fallbackError;
            });
        });
    }

    function getJsonWithFallback(primaryUrl, fallbackUrl, options) {
        var opts = options || {};

        function parseResult(result) {
            var body = result.body;
            if (body === null || body === undefined) {
                return body;
            }
            if (typeof body === "string") {
                try {
                    return normalizeResponsePayload(JSON.parse(body));
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
            return normalizeResponsePayload(body);
        }

        return http.request(primaryUrl, opts)
            .then(parseResult)
            .catch(function (primaryError) {
                return http.request(fallbackUrl, opts)
                    .then(parseResult)
                    .catch(function (fallbackError) {
                        fallbackError.primaryError = primaryError;
                        throw fallbackError;
                    });
            });
    }

    function postJsonWithFallback(primaryUrl, fallbackUrl, payload, options) {
        var opts = options ? Object.assign({}, options) : {};
        opts.method = opts.method || "POST";
        opts.json = payload;
        return requestWithFallback(primaryUrl, fallbackUrl, opts);
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

    var streamTokenCache = new Map();

    function streamContext(options) {
        return resolveRunContext(options || {});
    }

    function getStreamToken(runId, config, service, options) {
        var opts = options || {};
        var key = JSON.stringify([runId, config, service, opts.jobId || null]);
        var entry = streamTokenCache.get(key);
        if (entry && entry.promise) { return entry.promise; }
        if (!opts.forceRefresh && entry && entry.expiresAt > Date.now() + 30000) {
            return Promise.resolve(entry);
        }
        var url = "/rq-engine/api/runs/" + encodeURIComponent(runId) + "/" + encodeURIComponent(config) + "/stream-token";
        var payload = { service: service };
        if (opts.jobId) { payload.job_id = opts.jobId; }
        entry = {};
        entry.promise = http.postJson(url, payload, { credentials: "same-origin", timeoutMs: 15000 })
            .then(function (response) {
                var body = response.body;
                if (!body || typeof body.token !== "string" || !body.token ||
                    typeof body.config !== "string" || !body.config || body.service !== service ||
                    !Number.isFinite(body.expires_at) || body.expires_at * 1000 <= Date.now() + 30000) {
                    throw new Error("Invalid stream authorization response");
                }
                var credential = { token: body.token, config: body.config, expiresAt: body.expires_at * 1000 };
                streamTokenCache.set(key, credential);
                return credential;
            }).catch(function (error) {
                streamTokenCache.delete(key);
                // Never propagate response objects/bodies containing credentials to loggable callers.
                throw new HttpError("Stream authorization unavailable", { status: error.status || 0 });
            });
        streamTokenCache.set(key, entry);
        return entry.promise;
    }

    // WebSocket-compatible facade owning mint, refresh, bounded retry and cancellation.
    // Only final closure is emitted; transient renewal stays inside this connection.
    function createStreamConnection(options) {
        var opts = options || {};
        var context = streamContext(opts);
        var socket = null;
        var timer = null;
        var generation = 0;
        var stopped = false;
        var failures = 0;
        var state = 0;
        var events = new global.EventTarget();
        var facade = {
            onopen: null, onmessage: null, onclose: null, onerror: null,
            addEventListener: events.addEventListener.bind(events),
            removeEventListener: events.removeEventListener.bind(events),
            send: function (data) { if (socket && socket.readyState === 1) { socket.send(data); } },
            close: function () {
                if (stopped) { return; }
                stopped = true;
                generation += 1;
                global.clearTimeout(timer);
                state = 3;
                if (socket) { socket.close(1000, "client disconnected"); socket = null; }
                emit("close", { code: 1000, reason: "client disconnected", wasClean: true });
            }
        };
        Object.defineProperty(facade, "readyState", { get: function () { return state; } });
        function emit(type, data) {
            var event = new global.Event(type);
            Object.keys(data || {}).forEach(function (key) { Object.defineProperty(event, key, { value: data[key] }); });
            if (typeof facade["on" + type] === "function") { facade["on" + type](event); }
            events.dispatchEvent(event);
        }
        function finish() {
            if (stopped) { return; }
            stopped = true;
            state = 3;
            global.clearTimeout(timer);
            emit("error", {});
            emit("close", { code: 1008, reason: "Stream authorization unavailable", wasClean: false });
        }
        function retry() {
            if (stopped) { return; }
            failures += 1;
            if (failures > 1) { finish(); return; }
            timer = global.setTimeout(function () { connect(true); }, 1000);
        }
        function connect(force) {
            if (stopped) { return; }
            if (!context.runId || !context.config || !opts.service) { finish(); return; }
            var attempt = ++generation;
            state = 0;
            getStreamToken(context.runId, context.config, opts.service, { jobId: opts.jobId, forceRefresh: force })
                .then(function (credential) {
                    if (stopped || attempt !== generation) { return; }
                    var scheme = global.location.protocol === "https:" ? "wss:" : "ws:";
                    var path = "/weppcloud-microservices/" + opts.service + "/" + encodeURIComponent(context.runId);
                    if (opts.service === "status") { path += ":" + encodeURIComponent(opts.channel); }
                    var url = scheme + "//" + global.location.host + path + "?config=" + encodeURIComponent(credential.config);
                    socket = new global.WebSocket(url, ["wepp-stream.v1", "bearer." + credential.token]);
                    var current = socket;
                    current.onopen = function () {
                        if (stopped || attempt !== generation) { current.close(); return; }
                        failures = 0;
                        state = 1;
                        timer = global.setTimeout(function () { current.close(4001, "renew authorization"); },
                            Math.max(1, credential.expiresAt - Date.now() - 30000));
                        emit("open", {});
                    };
                    current.onmessage = function (event) { if (!stopped && attempt === generation) { emit("message", { data: event.data }); } };
                    current.onerror = function () { /* onclose owns bounded retry; never expose handshake details. */ };
                    current.onclose = function (event) {
                        if (stopped || attempt !== generation) { return; }
                        global.clearTimeout(timer);
                        socket = null;
                        state = 0;
                        if (event.code === 4001) {
                            timer = global.setTimeout(function () { connect(true); }, 1000);
                        } else { retry(); }
                    };
                }).catch(function (error) {
                    if (stopped || attempt !== generation) { return; }
                    if (error.status === 401 || error.status === 403 || error.status === 400 || error.status === 404) { finish(); }
                    else { retry(); }
                });
        }
        // Defer so callers install event handlers before synchronous validation failures.
        Promise.resolve().then(function () { connect(false); });
        return facade;
    }

    http.getStreamToken = getStreamToken;
    http.createStreamConnection = createStreamConnection;
    http.streamContext = streamContext;

    http.request = request;
    http.getJson = getJson;
    http.postJson = postJson;
    http.postForm = postForm;
    http.requestWithFallback = requestWithFallback;
    http.getJsonWithFallback = getJsonWithFallback;
    http.postJsonWithFallback = postJsonWithFallback;
    http.requestWithSessionToken = requestWithSessionToken;
    http.requestWithUserToken = requestWithUserToken;
    http.postJsonWithSessionToken = postJsonWithSessionToken;
    http.HttpError = HttpError;
    http.isHttpError = isHttpError;
    http.getCsrfToken = getCsrfToken;
    http.getSessionToken = getSessionToken;
    http.clearSessionToken = clearSessionToken;
    http.getRqEngineToken = getRqEngineToken;
    http.clearRqEngineToken = clearRqEngineToken;

    global.WCHttp = http;
})(typeof window !== "undefined" ? window : this);

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
    var DEFAULT_RENDER_BATCH_MS = 100;
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
        if (payload.error && typeof payload.error === "object" && payload.error.message) {
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

    function defaultIsImportantMessage(message) {
        if (!message) {
            return false;
        }
        return /(?:\bSTARTED\b|\bCOMPLETED\b|\bTRIGGER\b|\bEXCEPTION\b|\bERROR\b|\bFAILED\b|\bWARNING\b|\bWARN\b|Copying project files|rsync summary)/i.test(String(message));
    }

    function defaultStacktraceFetcher(jobId) {
        if (!jobId) {
            return Promise.resolve(null);
        }

        var http = global.WCHttp;
        var primaryUrl = "/rq-engine/api/jobinfo/" + encodeURIComponent(jobId);
        if (http && typeof http.getJson === "function") {
            return http.getJson(primaryUrl)
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
        var primaryFetchUrl = origin.replace(/\/$/, "") + primaryUrl;
        return fetch(primaryFetchUrl, { credentials: "same-origin" })
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
            logLimit: typeof options.logLimit === "number" ? Math.max(1, Math.floor(options.logLimit)) : DEFAULT_LOG_LIMIT,
            renderBatchMs: typeof options.renderBatchMs === "number" ? Math.max(0, options.renderBatchMs) : DEFAULT_RENDER_BATCH_MS,
            formatter: options.formatter,
            isImportant: typeof options.isImportant === "function" ? options.isImportant : defaultIsImportantMessage,
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
        var ws = null;
        var shouldReconnect = true;
        var renderTimeout = null;
        var renderPending = false;
        var stickToBottomPending = false;
        var api = this;

        if (logElement.textContent) {
            logElement.textContent.split("\n").forEach(function (line) {
                if (line) {
                    messages.push({ text: line, important: config.isImportant(line) });
                }
            });
            if (messages.length > config.logLimit) {
                trimMessages();
                logElement.textContent = messages.map(function (entry) { return entry.text; }).join("\n") + "\n";
            }
        }

        function dispatch(type, detail) {
            try {
                element.dispatchEvent(createCustomEvent(type, detail));
            } catch (err) {
                console.warn("StatusStream event dispatch error:", err);
            }
        }

        function documentIsHidden() {
            return typeof document !== "undefined" && document.hidden === true;
        }

        function trimMessages() {
            while (messages.length > config.logLimit) {
                var ordinaryIndex = messages.findIndex(function (entry) {
                    return !entry.important;
                });
                messages.splice(ordinaryIndex === -1 ? 0 : ordinaryIndex, 1);
            }
        }

        function setLogContent() {
            renderPending = false;
            logElement.textContent = messages.length
                ? messages.map(function (entry) { return entry.text; }).join("\n") + "\n"
                : "";
            if (stickToBottomPending) {
                logElement.scrollTop = logElement.scrollHeight;
            }
            stickToBottomPending = false;
        }

        function flushLogContent() {
            if (renderTimeout !== null) {
                clearTimeout(renderTimeout);
                renderTimeout = null;
            }
            if (documentIsHidden()) {
                renderPending = true;
                return;
            }
            setLogContent();
        }

        function scheduleLogContent() {
            renderPending = true;
            if (documentIsHidden() || renderTimeout !== null) {
                return;
            }
            if (config.renderBatchMs <= 0) {
                setLogContent();
                return;
            }
            renderTimeout = setTimeout(function () {
                renderTimeout = null;
                if (documentIsHidden()) {
                    return;
                }
                setLogContent();
            }, config.renderBatchMs);
        }

        function handleVisibilityChange() {
            if (!documentIsHidden() && renderPending) {
                flushLogContent();
            }
        }

        if (typeof document !== "undefined" && typeof document.addEventListener === "function") {
            document.addEventListener("visibilitychange", handleVisibilityChange);
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

            if (shouldStickToBottom) {
                stickToBottomPending = true;
            }

            messages.push({ text: formatted, important: config.isImportant(formatted, message, meta || null) });
            trimMessages();
            scheduleLogContent();

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
            fetchJobInfo: typeof stacktraceConfig.fetchJobInfo === "function" ? stacktraceConfig.fetchJobInfo : defaultStacktraceFetcher,
            allowHtml: stacktraceConfig.allowHtml === true
        };
    }

    var stacktraceTargets = resolveStacktraceTargets(config.stacktrace);

    function decodeHtmlEntities(message) {
        if (typeof message !== "string") {
            return message;
        }
        if (message.indexOf("&") === -1) {
            return message;
        }
        var needsDecode = (
            message.indexOf("&lt;") !== -1 ||
            message.indexOf("&gt;") !== -1 ||
            message.indexOf("&#") !== -1 ||
            message.indexOf("&amp;") !== -1 ||
            message.indexOf("&quot;") !== -1
        );
        if (!needsDecode || typeof document === "undefined") {
            return message;
        }
        var textarea = document.createElement("textarea");
        textarea.innerHTML = message;
        return textarea.value;
    }

    function shouldRenderStacktraceHtml(message, allowHtml) {
        if (!allowHtml || typeof message !== "string") {
            return false;
        }
        var lowered = message.toLowerCase();
        return (
            lowered.indexOf("<h6") !== -1 ||
            lowered.indexOf("<pre") !== -1 ||
            lowered.indexOf("<small") !== -1
        );
    }

    function renderStacktraceBody(body, message, allowHtml) {
        if (!body) {
            return;
        }
        var formatted = formatMessage(message);
        var isString = typeof formatted === "string";
        var decoded = isString ? decodeHtmlEntities(formatted) : formatted;
        if (isString && shouldRenderStacktraceHtml(decoded, true)) {
            body.innerHTML = decoded;
            return;
        }
        if (allowHtml && isString && shouldRenderStacktraceHtml(formatted, true)) {
            body.innerHTML = formatted;
            return;
        }
        body.textContent = formatted;
    }

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

        renderStacktraceBody(body, message, stacktraceTargets.allowHtml);

        var jobId = parseJobIdFromMessage(message);
        var fetcher = stacktraceTargets.fetchJobInfo;
        if (!fetcher || !jobId) {
            return;
        }

        fetcher(jobId).then(function (text) {
            if (text) {
                renderStacktraceBody(body, text, stacktraceTargets.allowHtml);
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
            ws = global.WCHttp.createStreamConnection({ runId: runId, config: options.config,
                service: "status", channel: config.channel, jobId: options.jobId });

            ws.onopen = function () {
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
                dispatch("status:disconnected", { willReconnect: false });

                if (!shouldReconnect) {
                    return;
                }

                shouldReconnect = false;
                appendMessage("Live updates unavailable. Reload the page to reconnect.");
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
            flushLogContent();
        }

        this.element = element;
        this.logElement = logElement;
        this.append = appendMessage;
        this.clear = function () {
            messages = [];
            stickToBottomPending = false;
            flushLogContent();
        };
        this.flush = flushLogContent;
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

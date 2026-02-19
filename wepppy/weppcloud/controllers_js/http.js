(function (global) {
    "use strict";

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

    http.request = request;
    http.getJson = getJson;
    http.postJson = postJson;
    http.postForm = postForm;
    http.requestWithFallback = requestWithFallback;
    http.getJsonWithFallback = getJsonWithFallback;
    http.postJsonWithFallback = postJsonWithFallback;
    http.requestWithSessionToken = requestWithSessionToken;
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

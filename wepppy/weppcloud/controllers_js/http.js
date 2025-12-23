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
        if (url === "/upload" || url.indexOf("/upload/") === 0) {
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

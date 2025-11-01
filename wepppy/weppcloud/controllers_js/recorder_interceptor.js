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
                summary.bodyPreview = JSON.stringify(options.json).slice(0, 256);
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
            try {
                body.forEach(function (value, key) {
                    if (keys.indexOf(key) === -1) {
                        keys.push(key);
                    }
                });
            } catch (err) {
                /* noop */
            }
            summary.formKeys = keys;
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

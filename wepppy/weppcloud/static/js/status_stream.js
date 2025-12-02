/* ----------------------------------------------------------------------------
 * StatusStream standalone bundle
 * NOTE: Generated via build_controllers_js.py from
 *       wepppy/weppcloud/controllers_js/status_stream.js
 * ----------------------------------------------------------------------------
 */
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

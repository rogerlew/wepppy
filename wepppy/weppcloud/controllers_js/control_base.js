/* ----------------------------------------------------------------------------
 * Control Base
 * ----------------------------------------------------------------------------
 */
function controlBase() {
    const TERMINAL_JOB_STATUSES = new Set(["finished", "failed", "stopped", "canceled", "not_found"]);
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

        if (error) {
            if (typeof error.status === "number" && error.status > 0) {
                statusCode = String(error.status);
            }
            if (typeof error.statusText === "string" && error.statusText) {
                statusText = error.statusText;
            }
            if (error.detail !== undefined) {
                detail = error.detail;
            } else if (typeof error.body === "string") {
                detail = error.body;
            } else if (error.body && typeof error.body === "object") {
                try {
                    detail = JSON.stringify(error.body);
                } catch (err) {
                    detail = String(error.body);
                }
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
        _job_status_fetch_inflight: false,
        _job_status_error: null,
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
            const normalizedJobId = normalizeJobId(job_id);

            if (normalizedJobId === self.rq_job_id) {
                if (!normalizedJobId) {
                    self.render_job_status(self);
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
            self._job_status_error = null;
            self.rq_job_status = data || {};
            self.render_job_status(self);

            if (self.should_continue_polling(self, self.rq_job_status && self.rq_job_status.status)) {
                self.schedule_job_status_poll(self);
            } else {
                self.stop_job_status_polling(self);
            }

            self.update_command_button_state(self);
        },

        handle_job_status_error: function handle_job_status_error(self, error) {
            const parts = deriveErrorParts(error);
            self._job_status_error = `${parts.statusCode} ${parts.statusText}`.trim();
            self.render_job_status(self);

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

            parts.push(
                `<div>job_id: <a href="${jobDashboardUrl(self.rq_job_id)}" target="_blank">${escapeHtml(self.rq_job_id)}</a></div>`
            );
            parts.push(`<div class="small text-muted">Status: ${escapeHtml(statusLabel)}</div>`);

            const timeline = [];

            if (statusObj.started_at) {
                timeline.push(`<span class="mr-3">Started: ${escapeHtml(statusObj.started_at)}</span>`);
            }

            if (statusObj.ended_at) {
                timeline.push(`<span class="mr-3">Ended: ${escapeHtml(statusObj.ended_at)}</span>`);
            }

            if (timeline.length) {
                parts.push(
                    `<div class="small text-muted d-flex flex-wrap align-items-baseline">${timeline.join("")}</div>`
                );
            }

            if (self._job_status_error) {
                parts.push(`<div class="text-danger small">${escapeHtml(self._job_status_error)}</div>`);
            }

            setHtmlContent(self.rq_job, parts.join(""));
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
                    if (hintSetter) {
                        hintSetter(summary);
                    }
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

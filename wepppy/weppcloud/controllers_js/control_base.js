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

        const jobInfoPrimaryUrl = `/rq-engine/api/jobinfo/${encodeURIComponent(jobId)}`;
        const jobInfoFallbackUrl = `/weppcloud/rq/api/jobinfo/${encodeURIComponent(jobId)}`;
        const fetchJobInfo = typeof http.getJsonWithFallback === "function"
            ? http.getJsonWithFallback(jobInfoPrimaryUrl, jobInfoFallbackUrl)
            : typeof http.getJson === "function"
                ? http.getJson(jobInfoFallbackUrl)
                : http.request(jobInfoFallbackUrl).then(normalizeJobInfoPayload);

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
            const primaryUrl = `/rq-engine/api/jobstatus/${encodeURIComponent(self.rq_job_id)}`;
            const fallbackUrl = `/weppcloud/rq/api/jobstatus/${encodeURIComponent(self.rq_job_id)}`;
            const fetchJobStatus = typeof http.getJsonWithFallback === "function"
                ? http.getJsonWithFallback(primaryUrl, fallbackUrl, { params: { _: Date.now() } })
                : typeof http.getJson === "function"
                    ? http.getJson(fallbackUrl, { params: { _: Date.now() } })
                    : http.request(fallbackUrl, { params: { _: Date.now() } }).then(normalizeJobInfoPayload);

            fetchJobStatus
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

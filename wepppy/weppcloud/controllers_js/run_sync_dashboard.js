/* ----------------------------------------------------------------------------
 * Run Sync Dashboard Controller
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var instance;
    var MAX_STATUS_MESSAGES = 3000;

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

    function resolveErrorMessage(payload, fallback) {
        if (!payload) {
            return fallback || null;
        }
        if (payload.error !== undefined) {
            if (typeof payload.error === "string") {
                return payload.error;
            }
            if (payload.error) {
                return payload.error.message || payload.error.detail || payload.error.details || fallback || null;
            }
        }
        if (payload.errors && Array.isArray(payload.errors) && payload.errors.length) {
            return payload.errors.map(function (entry) {
                if (!entry) {
                    return "";
                }
                if (typeof entry === "string") {
                    return entry;
                }
                if (typeof entry.message === "string") {
                    return entry.message;
                }
                if (typeof entry.detail === "string") {
                    return entry.detail;
                }
                if (typeof entry.code === "string") {
                    return entry.code;
                }
                return JSON.stringify(entry);
            }).filter(Boolean).join("\n");
        }
        if (payload.message) {
            return payload.message;
        }
        return fallback || null;
    }

    function showStacktrace(container, errorPayload) {
        var stacktraceEl = container.querySelector("#stacktrace");
        if (!stacktraceEl) {
            return;
        }
        stacktraceEl.innerHTML = "";
        stacktraceEl.style.display = "block";
        stacktraceEl.hidden = false;

        var errorMessage = resolveErrorMessage(errorPayload, null);
        if (errorMessage) {
            var heading = document.createElement("h6");
            heading.textContent = errorMessage;
            stacktraceEl.appendChild(heading);
        }

        var rawStack = errorPayload ? (errorPayload.stacktrace || (errorPayload.error && errorPayload.error.details)) : null;
        if (rawStack) {
            var lines = Array.isArray(rawStack) ? rawStack : [rawStack];
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
        var poller = null;
        var completionState = { completed: false, failed: false };
        var activeRunId = null;
        var activeConfig = null;
        var activeJobId = null;
        var summaryElement = null;
        var refreshStatusFn = null;
        var statusPanel = null;
        var statusLog = null;
        var stacktracePanel = null;
        var stacktraceBody = null;
        var statusMessages = [];
        var statusPollTimer = null;
        var statusPollIntervalMs = 10000;
        var lastStatusRefreshError = null;

        function ensureSummaryElement(container) {
            if (!summaryElement && container) {
                summaryElement = container.querySelector("#run_sync_summary");
            }
            return summaryElement;
        }

        function normalizeConfig(value) {
            if (value === null || value === undefined) {
                return "cfg";
            }
            var trimmed = String(value).trim();
            return trimmed ? trimmed : "cfg";
        }

        function clearSummary() {
            if (summaryElement) {
                summaryElement.innerHTML = "";
            }
        }

        function appendStatus(message) {
            if (message === undefined || message === null) {
                return;
            }
            var text = typeof message === "string" ? message : String(message);
            statusMessages.push(text);
            if (statusMessages.length > MAX_STATUS_MESSAGES) {
                statusMessages.splice(0, statusMessages.length - MAX_STATUS_MESSAGES);
            }
            if (statusStream && typeof statusStream.append === "function") {
                statusStream.append(text);
                return;
            }
            if (!statusLog) {
                return;
            }
            statusLog.textContent = statusMessages.join("\n") + "\n";
            statusLog.scrollTop = statusLog.scrollHeight;
        }

        function resetStatusLog() {
            statusMessages.length = 0;
            if (statusStream && typeof statusStream.clear === "function") {
                statusStream.clear();
                return;
            }
            if (statusLog) {
                statusLog.textContent = "";
            }
        }

        function resetCompletionState() {
            completionState.completed = false;
            completionState.failed = false;
        }

        function updateSummarySuccess(runId, config) {
            var summaryEl = summaryElement;
            if (!summaryEl) {
                return;
            }
            var normalizedRunId = runId ? String(runId).trim() : "";
            if (!normalizedRunId) {
                summaryEl.innerHTML = '<div style="padding: 0.5em 0;"><strong style="color: var(--wc-success-fg, #155724);">✓ Sync complete!</strong></div>';
                return;
            }
            var normalizedConfig = normalizeConfig(config);
            var runUrl = "/weppcloud/runs/" + encodeURIComponent(normalizedRunId) + "/" + encodeURIComponent(normalizedConfig) + "/";
            summaryEl.innerHTML = '<div style="padding: 0.5em 0;"><strong style="color: var(--wc-success-fg, #155724);">✓ Sync complete!</strong></div>' +
                '<a href="' + runUrl + '" class="pure-button pure-button-primary">Open run →</a>';
        }

        function updateSummaryFailure(message) {
            var summaryEl = summaryElement;
            if (!summaryEl) {
                return;
            }
            var detail = message ? escapeHtml(message) : "Unknown error";
            summaryEl.innerHTML = '<div style="padding: 0.5em 0;"><strong style="color: var(--wc-error-fg, #721c24);">✗ Sync failed</strong></div>' +
                '<p>' + detail + '</p>';
        }

        function markCompleted(runId, config) {
            if (completionState.completed) {
                return;
            }
            completionState.completed = true;
            completionState.failed = false;
            updateSummarySuccess(runId, config);
            appendStatus("Sync job completed.");
            if (typeof refreshStatusFn === "function") {
                refreshStatusFn();
            }
        }

        function markFailed(message) {
            if (completionState.failed) {
                return;
            }
            completionState.failed = true;
            completionState.completed = false;
            updateSummaryFailure(message);
            if (message) {
                appendStatus("Sync job failed: " + message);
            } else {
                appendStatus("Sync job failed.");
            }
            if (typeof refreshStatusFn === "function") {
                refreshStatusFn();
            }
        }

        function handleTrigger(eventOrDetail, payload) {
            var eventName = null;
            if (typeof eventOrDetail === "string") {
                eventName = eventOrDetail;
            } else if (eventOrDetail && eventOrDetail.event) {
                eventName = eventOrDetail.event;
            }
            if (!eventName) {
                return;
            }
            var normalized = String(eventName).toUpperCase();
            if (normalized === "RUN_SYNC_COMPLETE" || normalized === "JOB:COMPLETED") {
                markCompleted(activeRunId, activeConfig);
            } else if (normalized === "RUN_SYNC_FAILED" || normalized === "JOB:ERROR") {
                markFailed("Sync failed. Review the status log for details.");
            }
        }

        function handleStreamAppend(container, detail) {
            var message = detail && detail.message ? detail.message : "";

            // Detect EXCEPTION_JSON message and display stacktrace
            var exceptionMatch = message.match(/EXCEPTION_JSON\s+(.+)$/);
            if (exceptionMatch) {
                try {
                    var payload = JSON.parse(exceptionMatch[1]);
                    showStacktrace(container, payload);
                    markFailed(resolveErrorMessage(payload, "Unknown error"));
                } catch (e) {
                    // JSON parse failed, ignore
                }
                return;
            }

            // Detect COMPLETE message and show link in summary panel
            // Format: rq:<job_id> COMPLETE run_sync_rq(<runid>, <config>)
            var completeMatch = message.match(/COMPLETE run_sync_rq\(([^,]+),\s*([^)]+)\)/);
            if (completeMatch) {
                var syncedRunId = completeMatch[1].trim();
                var syncedConfig = completeMatch[2].trim();
                activeRunId = syncedRunId;
                activeConfig = syncedConfig;
                markCompleted(syncedRunId, syncedConfig);
            }
        }

        function detachStatusStream() {
            if (poller && typeof poller.detach_status_stream === "function") {
                poller.detach_status_stream(poller);
            } else if (statusStream && typeof statusStream.disconnect === "function") {
                try {
                    statusStream.disconnect();
                } catch (err) {
                    // ignore
                }
            }
            statusStream = null;
        }

        function startStream(container, runId, channel) {
            ensureSummaryElement(container);
            if (!runId || !channel) {
                return;
            }

            detachStatusStream();

            if (poller && typeof poller.attach_status_stream === "function") {
                statusStream = poller.attach_status_stream(poller, {
                    element: statusPanel || container,
                    form: poller.form,
                    channel: channel,
                    runId: runId,
                    logElement: statusLog,
                    stacktrace: stacktracePanel ? { element: stacktracePanel, body: stacktraceBody } : null,
                    autoConnect: false,
                    onAppend: function (detail) {
                        handleStreamAppend(container, detail);
                    },
                    onTrigger: handleTrigger
                });
                return;
            }

            if (!global.StatusStream || typeof global.StatusStream.attach !== "function") {
                return;
            }
            if (!statusLog) {
                return;
            }

            statusStream = global.StatusStream.attach({
                element: statusPanel || container,
                logElement: statusLog,
                runId: runId,
                channel: channel,
                onTrigger: handleTrigger,
                onAppend: function (detail) {
                    handleStreamAppend(container, detail);
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
                config: payload.config ? String(payload.config).trim() : null,
                target_root: payload.target_root || defaults.defaultRoot,
                owner_email: payload.owner_email || null,
                run_migrations: payload.run_migrations !== false,
                archive_before: payload.archive_before === true
            };
        }

        function initPoller(container, form) {
            if (typeof controlBase !== "function") {
                if (global.console && console.warn) {
                    console.warn("RunSyncDashboard polling disabled; controlBase missing.");
                }
                return;
            }
            poller = controlBase();
            poller.form = form;
            poller.rq_job = statusPanel ? statusPanel.querySelector("#rq_job") : container.querySelector("#rq_job");
            poller.stacktrace = stacktraceBody;
            poller.statusSpinnerEl = statusPanel ? statusPanel.querySelector("#braille") : container.querySelector("#braille");
            poller.statusPanelEl = statusPanel;
            poller.stacktracePanelEl = stacktracePanel;
            poller.poll_completion_event = "RUN_SYNC_COMPLETE";
            poller.triggerEvent = function (eventName, detail) {
                handleTrigger(eventName, detail);
            };
        }

        function startPolling(jobId) {
            if (!poller) {
                return;
            }
            var normalized = jobId ? String(jobId).trim() : "";
            if (!normalized) {
                return;
            }
            if (activeJobId === normalized) {
                return;
            }
            activeJobId = normalized;
            resetCompletionState();
            poller.poll_completion_event = "RUN_SYNC_COMPLETE";
            poller.set_rq_job_id(poller, normalized);
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
            statusPanel = container.querySelector("#run_sync_status_panel");
            statusLog = container.querySelector("#run_sync_status_log");
            stacktracePanel = container.querySelector("[data-stacktrace-panel]");
            stacktraceBody = container.querySelector("[data-stacktrace-body]") || container.querySelector("#stacktrace");
            summaryElement = container.querySelector("#run_sync_summary");

            function refreshStatus() {
                http.getJson(statusUrl)
                    .then(function (payload) {
                        renderJobs(container, payload.jobs || []);
                        renderMigrations(container, payload.migrations || []);
                        lastStatusRefreshError = null;
                    })
                    .catch(function (error) {
                        var message = "Status refresh failed: " + (error.message || error);
                        if (message !== lastStatusRefreshError) {
                            appendStatus(message);
                            lastStatusRefreshError = message;
                        }
                    });
            }
            refreshStatusFn = refreshStatus;

            function startStatusPolling() {
                if (statusPollTimer) {
                    return;
                }
                statusPollTimer = setInterval(refreshStatus, statusPollIntervalMs);
            }

            function handleSubmit(event) {
                event.preventDefault();
                if (!form) {
                    return;
                }
                var payload = buildPayload(form, defaults);
                if (!payload.runid) {
                    appendStatus("runid is required.");
                    return;
                }
                resetCompletionState();
                activeRunId = payload.runid;
                activeConfig = normalizeConfig(payload.config);
                clearSummary();
                resetStatusLog();
                appendStatus("Enqueueing run sync job...");
                http.postJson(apiUrl, payload)
                    .then(function (response) {
                        var body = response && response.body ? response.body : response;
                        if (body && (body.error || body.errors)) {
                            throw new Error(body.message || "Run sync submit failed.");
                        }
                        var syncJobId = body && (body.sync_job_id || body.job_id) ? (body.sync_job_id || body.job_id) : "";
                        appendStatus("Job enqueued: " + syncJobId);
                        startStream(container, payload.runid, statusChannel);
                        if (poller && typeof poller.connect_status_stream === "function") {
                            poller.connect_status_stream(poller);
                        }
                        startPolling(syncJobId);
                        refreshStatus();
                    })
                    .catch(function (error) {
                        appendStatus("Run sync submit failed: " + (error.message || error));
                        if (global.console && console.error) {
                            console.error(error);
                        }
                    });
            }

            if (form) {
                form.addEventListener("submit", handleSubmit);
            }

            startStatusPolling();
            initPoller(container, form);
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

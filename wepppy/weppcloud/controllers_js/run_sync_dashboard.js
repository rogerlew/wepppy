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

    function normalizeRunLabel(runid, config) {
        if (!runid && !config) {
            return "";
        }
        if (!config) {
            return runid || "";
        }
        return runid + " / " + config;
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
            if (!runId || !channel || !logElement) {
                return;
            }
            statusStream = global.StatusStream.attach({
                element: container,
                logElement: logElement,
                runId: runId,
                channel: channel,
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
                    normalizeRunLabel(job.runid, job.config),
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
                    normalizeRunLabel(record.runid, record.config),
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
            var result = {
                source_host: payload.source_host || defaults.defaultHost,
                runid: payload.runid ? String(payload.runid).trim() : "",
                config: payload.config ? String(payload.config).trim() : "",
                target_root: payload.target_root || defaults.defaultRoot,
                owner_email: payload.owner_email || null,
                auth_token: payload.auth_token || null,
                allow_push: Boolean(payload.allow_push),
                overwrite: Boolean(payload.overwrite),
                expected_sha256: payload.expected_sha256 || null,
            };
            if (payload.expected_size !== undefined && payload.expected_size !== null && String(payload.expected_size).trim() !== "") {
                result.expected_size = Number(payload.expected_size);
            }

            Object.keys(result).forEach(function (key) {
                if (result[key] === "" || result[key] === null) {
                    delete result[key];
                }
            });

            return result;
        }

        function bootstrap() {
            var container = dom.ensureElement("[data-controller=\"run-sync-dashboard\"]");
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
                if (!payload.runid || !payload.config) {
                    setStatusMessage("runid and config are required.");
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

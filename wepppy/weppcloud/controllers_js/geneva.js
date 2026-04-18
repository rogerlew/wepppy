/* ----------------------------------------------------------------------------
 * Geneva
 * ----------------------------------------------------------------------------
 */
var Geneva = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "geneva:state:loaded",
        "geneva:config:saved",
        "geneva:workflow:queued",
        "geneva:state:error"
    ];

    var FORM_ID = "geneva_form";
    var STATUS_CHANNEL = "geneva";
    var COMPLETION_EVENT = "GENEVA_STATE_SYNC_REQUESTED";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        hintRunWorkflow: "#hint_run_geneva_run_workflow",
        hintRunBatch: "#hint_run_geneva_run_batch",
        hintLegacy: "#hint_run_geneva",
        results: "#geneva-results",
        configMessage: "#geneva_config_message",
        configNode: "#geneva_controller_data",
        statusPanel: "#geneva_status_panel",
        stacktracePanel: "#geneva_stacktrace_panel"
    };

    var ACTIONS = {
        runWorkflow: '[data-geneva-action="run-workflow"]'
    };
    var CONFIG_FIELD_MAP = {
        lambda_mode: "geneva_lambda_mode",
        uh_method: "geneva_uh_method",
        default_hsg_code: "geneva_default_hsg_code",
        unresolved_hsg_policy: "geneva_unresolved_hsg_policy",
        strict_burn_nodata: "geneva_strict_burn_nodata",
        allow_cross_hsg_merge: "geneva_allow_cross_hsg_merge",
        hydrophobic_forest_high: "geneva_hydrophobic_forest_high",
        hydrophobic_forest_moderate: "geneva_hydrophobic_forest_moderate",
        hydrophobic_shrub_high: "geneva_hydrophobic_shrub_high",
        hydrophobic_shrub_moderate: "geneva_hydrophobic_shrub_moderate",
        min_hru_area_ha: "geneva_min_hru_area_ha"
    };
    var UNSAVED_CONFIG_MESSAGE = "Unsaved Geneva settings detected. Settings will be auto-saved when you submit a Geneva job.";
    var LINK_FIELDS = {
        "cn-table": "cn_table_url",
        "query-summary": "query_summary_url",
        "report-summary": "report_summary_url"
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function") {
            throw new Error("Geneva controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Geneva controller requires WCForms.serializeForm.");
        }
        if (!http || typeof http.postJson !== "function") {
            throw new Error("Geneva controller requires WCHttp.postJson.");
        }
        if (typeof http.postJsonWithSessionToken !== "function") {
            throw new Error("Geneva controller requires WCHttp.postJsonWithSessionToken.");
        }
        if (typeof http.requestWithSessionToken !== "function") {
            throw new Error("Geneva controller requires WCHttp.requestWithSessionToken.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Geneva controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return {
                element: element,
                length: 0,
                show: function () {},
                hide: function () {},
                text: function () {},
                html: function () {},
                append: function () {},
                empty: function () {}
            };
        }

        return {
            element: element,
            length: 1,
            show: function () {
                element.hidden = false;
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
            },
            text: function (value) {
                if (value === undefined) {
                    return element.textContent;
                }
                element.textContent = value === null ? "" : String(value);
            },
            html: function (value) {
                if (value === undefined) {
                    return element.innerHTML;
                }
                element.innerHTML = value === null ? "" : String(value);
            },
            append: function (content) {
                if (content === null || content === undefined) {
                    return;
                }
                if (typeof content === "string") {
                    element.insertAdjacentHTML("beforeend", content);
                    return;
                }
                if (content instanceof window.Node) {
                    element.appendChild(content);
                }
            },
            empty: function () {
                element.textContent = "";
            }
        };
    }

    function normalizeResponseBody(response) {
        if (!response) {
            return {};
        }
        if (Object.prototype.hasOwnProperty.call(response, "body")) {
            return response.body || {};
        }
        return response;
    }

    function parseJsonNode(element) {
        if (!element) {
            return {};
        }
        try {
            return JSON.parse(element.textContent || "{}");
        } catch (error) {
            console.warn("[Geneva] Failed to parse config node:", error);
            return {};
        }
    }

    function escapeHtml(value) {
        return String(value === undefined || value === null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function hasValidRunContext(candidate) {
        if (!candidate) {
            return false;
        }

        var pathname;
        try {
            pathname = new URL(String(candidate), window.location.origin).pathname || "";
        } catch (_error) {
            pathname = String(candidate);
        }

        if (pathname.indexOf("/runs/") === -1) {
            return true;
        }
        return /\/runs\/[^/]+\/[^/]+(?:\/|$)/.test(pathname);
    }

    function normalizeUrlCandidate(candidate, fallback) {
        var text = typeof candidate === "string" ? candidate.trim() : "";
        if (!text) {
            return fallback || "";
        }
        if (!hasValidRunContext(text) && fallback) {
            return fallback;
        }
        return text;
    }

    function jobStatusUrl(jobId) {
        if (!jobId) {
            return "";
        }
        return "/rq-engine/api/jobstatus/" + encodeURIComponent(String(jobId));
    }

    function jobIdAnchor(jobId) {
        if (!jobId) {
            return "none";
        }
        var normalized = String(jobId);
        return (
            '<a href="' +
            jobStatusUrl(normalized) +
            '" target="_blank" rel="noopener">' +
            escapeHtml(normalized) +
            "</a>"
        );
    }

    function fallbackUrls() {
        if (typeof url_for_run === "function") {
            return {
                config_url: url_for_run("api/geneva/config"),
                state_url: url_for_run("geneva/state", { prefix: "/rq-engine/api" }),
                run_workflow_url: url_for_run("geneva/run-workflow", { prefix: "/rq-engine/api" }),
                results_url: url_for_run("api/geneva/results"),
                frequency_panel_url: url_for_run("api/geneva/frequency_panel"),
                query_summary_url: url_for_run("query/geneva/summary"),
                report_summary_url: url_for_run("report/geneva/summary"),
                cn_table_url: url_for_run("modify_geneva_cn_table")
            };
        }
        return {};
    }

    function normalizeConfig(controller) {
        var fallback = fallbackUrls();
        var merged = Object.assign({}, fallback, controller.configNodeData || {});
        Object.keys(fallback).forEach(function (key) {
            merged[key] = normalizeUrlCandidate(merged[key], fallback[key]);
        });
        return merged;
    }

    function parseList(value, parser) {
        if (value === undefined || value === null) {
            return [];
        }

        var tokens;
        if (Array.isArray(value)) {
            tokens = value.slice();
        } else {
            tokens = String(value).split(",");
        }

        var values = [];
        tokens.forEach(function (token) {
            var text = token === undefined || token === null ? "" : String(token).trim();
            if (!text) {
                return;
            }
            values.push(parser(text));
        });
        return values;
    }

    function parsePositiveIntegers(value) {
        return parseList(value, function (token) {
            var parsed = parseInt(token, 10);
            if (Number.isNaN(parsed) || parsed <= 0) {
                throw new Error("Expected a comma-separated list of positive integers.");
            }
            return parsed;
        });
    }

    function parseDatasourceIds(value) {
        return parseList(value, function (token) {
            return token;
        });
    }

    function parseOptionalFloat(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        var parsed = parseFloat(String(value));
        if (Number.isNaN(parsed)) {
            throw new Error("Expected a numeric value.");
        }
        return parsed;
    }

    function setFieldValue(form, name, value) {
        if (!form || !name) {
            return;
        }

        var field = form.elements ? form.elements.namedItem(name) : null;
        if (!field) {
            return;
        }

        if (typeof RadioNodeList !== "undefined" && field instanceof RadioNodeList) {
            Array.prototype.forEach.call(field, function (item) {
                if (!item) {
                    return;
                }
                item.checked = String(item.value) === String(value);
            });
            return;
        }

        if (field.type === "checkbox") {
            field.checked = Boolean(value);
            return;
        }

        if (value === null || value === undefined) {
            field.value = "";
            return;
        }
        field.value = String(value);
    }

    function readFormSnapshot(controller) {
        return controller.forms.serializeForm(controller.form, { format: "json" }) || {};
    }

    function toResponsePayload(http, error) {
        var payload = error && Object.prototype.hasOwnProperty.call(error, "body") ? error.body : null;
        if (typeof payload === "string" && payload.trim() !== "") {
            try {
                payload = JSON.parse(payload);
            } catch (parseError) {
                payload = { error: { message: payload } };
            }
        }
        if (payload && (payload.error || payload.errors)) {
            return payload;
        }
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            return { error: { message: error.message || "Request failed" } };
        }
        return { error: { message: (error && error.message) || "Request failed" } };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = eventsApi.useEventMap
            ? eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter())
            : eventsApi.createEmitter();

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: null,
            info: createLegacyAdapter(null),
            status: createLegacyAdapter(null),
            stacktrace: createLegacyAdapter(null),
            rq_job: createLegacyAdapter(null),
            hint: createLegacyAdapter(null),
            hintTargets: {},
            activeHintKey: "run",
            resultsEl: null,
            configMessageEl: null,
            statusPanelEl: null,
            stacktracePanelEl: null,
            statusSpinnerEl: null,
            configNodeEl: null,
            configNodeData: {},
            command_btn_id: ["geneva_run_batch"],
            state: {
                snapshot: null
            },
            savedConfigComparable: null,
            _delegates: []
        });

        controller.resolveHintKeyForSnapshot = function () {
            return "run";
        };

        controller.setActiveHint = function (hintKey) {
            var key = String(hintKey || "").trim().toLowerCase();
            if (key !== "run") {
                key = "run";
            }

            var targets = controller.hintTargets || {};
            var nextTarget = targets[key] || targets.run || createLegacyAdapter(null);
            controller.activeHintKey = key;
            controller.hint = nextTarget;

            Object.keys(targets).forEach(function (targetKey) {
                if (targetKey === key) {
                    return;
                }
                var target = targets[targetKey];
                if (!target) {
                    return;
                }
                if (typeof target.html === "function") {
                    target.html("");
                }
                if (typeof target.hide === "function") {
                    target.hide();
                }
            });
        };

        controller.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (controller.statusStream && typeof controller.statusStream.append === "function") {
                controller.statusStream.append(message, meta || null);
                return;
            }
            controller.status.html(message);
        };

        controller.setMessage = function (message, kind) {
            if (!controller.configMessageEl) {
                return;
            }
            controller.configMessageEl.textContent = message || "";
            controller.configMessageEl.dataset.messageKind = kind || "";
        };

        controller.clearTransientUi = function () {
            controller.setMessage("");
            if (typeof controller.clear_status_messages === "function") {
                controller.clear_status_messages(controller);
            }
            if (typeof controller.reset_status_spinner === "function") {
                controller.reset_status_spinner(controller);
            }
            if (controller.stacktrace && typeof controller.stacktrace.text === "function") {
                controller.stacktrace.text("");
            }
        };

        controller.hasFormField = function (name) {
            if (!controller.form || !controller.form.elements || !name) {
                return false;
            }
            return Boolean(controller.form.elements.namedItem(name));
        };

        controller.normalizeConfigComparable = function (payload) {
            var source = payload || {};
            var defaultHsgRaw = source.default_hsg_code;
            var minAreaRaw = source.min_hru_area_ha;
            var defaultHsg = null;
            var minArea = parseFloat(minAreaRaw);

            if (!(defaultHsgRaw === "" || defaultHsgRaw === null || defaultHsgRaw === undefined)) {
                defaultHsg = parseInt(String(defaultHsgRaw), 10);
                if (Number.isNaN(defaultHsg)) {
                    defaultHsg = null;
                }
            }
            if (Number.isNaN(minArea)) {
                minArea = 2.0;
            }

            return {
                lambda_mode: source.lambda_mode || "0.20",
                uh_method: source.uh_method || "scs_triangular",
                default_hsg_code: defaultHsg,
                unresolved_hsg_policy: source.unresolved_hsg_policy || "assume_d",
                strict_burn_nodata: Boolean(source.strict_burn_nodata),
                allow_cross_hsg_merge: Boolean(source.allow_cross_hsg_merge),
                hydrophobic_forest_high: Boolean(source.hydrophobic_forest_high),
                hydrophobic_forest_moderate: Boolean(source.hydrophobic_forest_moderate),
                hydrophobic_shrub_high: Boolean(source.hydrophobic_shrub_high),
                hydrophobic_shrub_moderate: Boolean(source.hydrophobic_shrub_moderate),
                min_hru_area_ha: minArea
            };
        };

        controller.currentConfigComparable = function () {
            var payload = controller.buildConfigPayload();
            delete payload.schema_version;
            return controller.normalizeConfigComparable(payload);
        };

        controller.hasUnsavedConfigChanges = function () {
            if (!controller.savedConfigComparable) {
                return false;
            }
            var current = controller.currentConfigComparable();
            var keys = Object.keys(CONFIG_FIELD_MAP);

            for (var idx = 0; idx < keys.length; idx += 1) {
                var key = keys[idx];
                var formFieldName = CONFIG_FIELD_MAP[key];
                if (!controller.hasFormField(formFieldName)) {
                    continue;
                }
                if (current[key] !== controller.savedConfigComparable[key]) {
                    return true;
                }
            }
            return false;
        };

        controller.updateUnsavedConfigMessage = function () {
            if (!controller.configMessageEl) {
                return;
            }

            var dirty = controller.hasUnsavedConfigChanges();
            var kind = controller.configMessageEl.dataset.messageKind || "";

            if (dirty) {
                if (kind !== "pending") {
                    controller.setMessage(UNSAVED_CONFIG_MESSAGE, "warning");
                }
                return;
            }

            if (kind === "warning") {
                controller.setMessage("", "");
            }
        };

        controller.renderSummary = function (snapshot) {
            var config = normalizeConfig(controller);
            if (!snapshot) {
                controller.info.html("");
                if (controller.resultsEl) {
                    controller.resultsEl.innerHTML = "";
                }
                return;
            }

            var progress = snapshot.progress || {};
            var lastRun = snapshot.last_run_summary || {};
            var artifacts = snapshot.artifacts || {};
            var warnings = Array.isArray(snapshot.warnings) ? snapshot.warnings.length : 0;
            var errors = Array.isArray(snapshot.errors) ? snapshot.errors.length : 0;
            var lines = [
                "<div class='wc-stack-sm'>",
                "<p><strong>Status:</strong> " + String(snapshot.status || "idle") + "</p>",
                "<p><strong>Message:</strong> " + String(snapshot.status_message || "") + "</p>",
                "<p><strong>Active job:</strong> " + jobIdAnchor(snapshot.active_job_id) + "</p>",
                "<p><strong>Last job:</strong> " + jobIdAnchor(snapshot.last_job_id) + "</p>",
                "<p><strong>Progress:</strong> " + String(progress.completed || 0) + " / " + String(progress.total || 0) + " " + String(progress.unit || "storms") + "</p>",
                "<p><strong>Artifacts:</strong> HRUs " + (artifacts.hru_table_ready ? "ready" : "missing") + ", panel " + (artifacts.frequency_panel_ready ? "ready" : "missing") + ", batch " + (artifacts.batch_summary_ready ? "ready" : "missing") + "</p>",
                "<p><strong>Warnings:</strong> " + String(warnings) + " | <strong>Errors:</strong> " + String(errors) + "</p>",
                "</div>"
            ];
            controller.info.html(lines.join(""));

            if (!controller.resultsEl) {
                return;
            }

            var resultLines = [];
            if (lastRun && lastRun.storm_count_total !== undefined) {
                resultLines.push(
                    "<p><strong>Last batch:</strong> " +
                    String(lastRun.storm_count_completed || 0) +
                    " completed / " +
                    String(lastRun.storm_count_total || 0) +
                    " total storms.</p>"
                );
                if (config.query_summary_url && config.report_summary_url) {
                    resultLines.push(
                        "<p><strong>Links:</strong> " +
                        '<a href="' + escapeHtml(config.query_summary_url) + '" target="_blank" rel="noopener">Query summary</a>' +
                        " · " +
                        '<a href="' + escapeHtml(config.report_summary_url) + '" target="_blank" rel="noopener">Report summary</a>' +
                        "</p>"
                    );
                }
            } else {
                resultLines.push("<p class='wc-field__help'>No Geneva batch summary is available yet.</p>");
            }
            controller.resultsEl.innerHTML = resultLines.join("");
        };

        controller.syncPanelLinks = function () {
            if (!controller.form) {
                return;
            }
            var config = normalizeConfig(controller);
            var anchors = controller.form.querySelectorAll("[data-geneva-link]");
            Array.prototype.forEach.call(anchors, function (anchor) {
                if (!anchor || typeof anchor.getAttribute !== "function") {
                    return;
                }
                var key = String(anchor.getAttribute("data-geneva-link") || "").trim();
                var configField = LINK_FIELDS[key];
                if (!configField) {
                    return;
                }
                var href = config[configField];
                if (!href) {
                    return;
                }
                anchor.setAttribute("href", href);
            });
        };

        controller.updateActionAvailability = function (snapshot) {
            if (!controller.form) {
                return;
            }

            var runButton = controller.form.querySelector("#geneva_run_batch");
            var disabled = !snapshot || snapshot.enabled === false;
            if (runButton) {
                runButton.disabled = Boolean(disabled);
            }
        };

        controller.hydrateConfigFields = function (configSnapshot) {
            if (!controller.form || !configSnapshot) {
                return;
            }
            setFieldValue(controller.form, "geneva_lambda_mode", configSnapshot.lambda_mode);
            setFieldValue(controller.form, "geneva_uh_method", configSnapshot.uh_method);
            setFieldValue(controller.form, "geneva_default_hsg_code", configSnapshot.default_hsg_code);
            setFieldValue(controller.form, "geneva_unresolved_hsg_policy", configSnapshot.unresolved_hsg_policy);
            setFieldValue(controller.form, "geneva_min_hru_area_ha", configSnapshot.min_hru_area_ha);
            setFieldValue(controller.form, "geneva_strict_burn_nodata", configSnapshot.strict_burn_nodata);
            setFieldValue(controller.form, "geneva_allow_cross_hsg_merge", configSnapshot.allow_cross_hsg_merge);
            setFieldValue(controller.form, "geneva_hydrophobic_forest_high", configSnapshot.hydrophobic_forest_high);
            setFieldValue(controller.form, "geneva_hydrophobic_forest_moderate", configSnapshot.hydrophobic_forest_moderate);
            setFieldValue(controller.form, "geneva_hydrophobic_shrub_high", configSnapshot.hydrophobic_shrub_high);
            setFieldValue(controller.form, "geneva_hydrophobic_shrub_moderate", configSnapshot.hydrophobic_shrub_moderate);

            if (controller.state.snapshot && controller.state.snapshot.enabled === false) {
                setFieldValue(controller.form, "geneva_run_lambda_mode", "");
                setFieldValue(controller.form, "geneva_run_uh_method", "");
            }
        };

        controller.applyState = function (payload) {
            controller.state.snapshot = payload || null;
            if (!payload) {
                controller.renderSummary(null);
                controller.updateActionAvailability(null);
                controller.setActiveHint("run");
                controller.set_rq_job_id(controller, null);
                return;
            }

            controller.hydrateConfigFields(payload.config_snapshot || {});
            controller.savedConfigComparable = controller.normalizeConfigComparable(payload.config_snapshot || {});
            controller.syncPanelLinks();
            controller.renderSummary(payload);
            controller.updateActionAvailability(payload);
            controller.updateUnsavedConfigMessage();
            controller.poll_completion_event = COMPLETION_EVENT;
            controller.setActiveHint(controller.resolveHintKeyForSnapshot(payload));
            controller.set_rq_job_id(controller, payload.active_job_id || payload.last_job_id || null);
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("geneva:state:loaded", {
                    revision: payload.run_state_revision || null,
                    status: payload.status || null
                });
            }
        };

        controller.handleFailure = function (error, eventName) {
            var payload = toResponsePayload(controller.http, error);
            controller.pushResponseStacktrace(controller, payload);
            if (controller.events && typeof controller.events.emit === "function" && eventName) {
                controller.events.emit(eventName, { error: payload });
            }
            controller.disconnect_status_stream(controller);
        };

        controller.refreshState = function (options) {
            if (!controller.form) {
                return Promise.resolve(null);
            }

            var opts = options || {};
            var config = normalizeConfig(controller);
            if (!config.state_url) {
                return Promise.resolve(null);
            }

            if (!opts.silent) {
                controller.appendStatus("Refreshing Geneva state…", { phase: "sync" });
            }

            return controller.http.requestWithSessionToken(
                config.state_url,
                { method: "GET", form: controller.form }
            ).then(function (response) {
                var payload = normalizeResponseBody(response);
                controller.applyState(payload);
                return payload;
            }).catch(function (error) {
                controller.handleFailure(error, "geneva:state:error");
                throw error;
            });
        };

        controller.buildConfigPayload = function () {
            var raw = readFormSnapshot(controller);
            var defaultHsg = raw.geneva_default_hsg_code;
            var stateConfig = controller.state.snapshot && controller.state.snapshot.config_snapshot
                ? controller.state.snapshot.config_snapshot
                : {};
            var strictBurnNodata = controller.hasFormField("geneva_strict_burn_nodata")
                ? Boolean(raw.geneva_strict_burn_nodata)
                : Boolean(stateConfig.strict_burn_nodata);
            return {
                schema_version: 1,
                lambda_mode: raw.geneva_lambda_mode || "0.20",
                uh_method: raw.geneva_uh_method || "scs_triangular",
                default_hsg_code: defaultHsg === "" || defaultHsg === null ? null : parseInt(defaultHsg, 10),
                unresolved_hsg_policy: raw.geneva_unresolved_hsg_policy || "assume_d",
                strict_burn_nodata: strictBurnNodata,
                allow_cross_hsg_merge: Boolean(raw.geneva_allow_cross_hsg_merge),
                hydrophobic_forest_high: Boolean(raw.geneva_hydrophobic_forest_high),
                hydrophobic_forest_moderate: Boolean(raw.geneva_hydrophobic_forest_moderate),
                hydrophobic_shrub_high: Boolean(raw.geneva_hydrophobic_shrub_high),
                hydrophobic_shrub_moderate: Boolean(raw.geneva_hydrophobic_shrub_moderate),
                min_hru_area_ha: parseFloat(raw.geneva_min_hru_area_ha || "2.0")
            };
        };

        controller.saveConfig = function (options) {
            var opts = options || {};
            var config = normalizeConfig(controller);
            if (!config.config_url || !controller.form) {
                return Promise.resolve(null);
            }

            controller.clearTransientUi();
            controller.setMessage(
                opts.autosave ? "Auto-saving Geneva settings…" : "Saving Geneva settings…",
                "pending",
            );
            return controller.http.postJson(config.config_url, controller.buildConfigPayload(), { form: controller.form })
                .then(function (response) {
                    normalizeResponseBody(response);
                    controller.setMessage(
                        opts.autosave ? "Geneva settings auto-saved." : "Geneva settings saved.",
                        "success",
                    );
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("geneva:config:saved", {});
                    }
                    return controller.refreshState({ silent: true });
                }).catch(function (error) {
                    controller.handleFailure(error, "geneva:state:error");
                    throw error;
                });
        };

        controller.ensureConfigSyncedBeforeQueue = function () {
            if (!controller.hasUnsavedConfigChanges()) {
                return Promise.resolve(null);
            }
            return controller.saveConfig({ autosave: true });
        };

        controller.buildPreparePayload = function () {
            return {
                schema_version: 1,
                force_rebuild: true
            };
        };

        controller.buildPanelPayload = function () {
            var raw = readFormSnapshot(controller);
            var payload = {
                schema_version: 1,
                durations_minutes: parsePositiveIntegers(raw.geneva_panel_durations_minutes),
                ari_years: parsePositiveIntegers(raw.geneva_panel_ari_years),
                rebuild: true
            };
            var sources = {};
            if (raw.geneva_panel_source_cligen) {
                sources.cligen_freq = String(raw.geneva_panel_source_cligen).trim();
            }
            if (raw.geneva_panel_source_noaa14) {
                sources.noaa14_pds = String(raw.geneva_panel_source_noaa14).trim();
            }
            if (Object.keys(sources).length > 0) {
                payload.sources = sources;
            }
            return payload;
        };

        controller.buildRunPayload = function () {
            var raw = readFormSnapshot(controller);
            var runoffModel = {};
            var tcHours = parseOptionalFloat(raw.geneva_run_tc_hours);

            if (raw.geneva_run_lambda_mode) {
                runoffModel.lambda_mode = raw.geneva_run_lambda_mode;
            }
            if (raw.geneva_run_uh_method) {
                runoffModel.uh_method = raw.geneva_run_uh_method;
            }
            if (tcHours !== null) {
                runoffModel.tc_hours = tcHours;
            } else if (raw.geneva_run_timing_method) {
                runoffModel.timing_method = raw.geneva_run_timing_method;
            }

            return {
                schema_version: 1,
                batch_id: raw.geneva_run_batch_id ? String(raw.geneva_run_batch_id).trim() : null,
                event_filter: {
                    datasource_ids: parseDatasourceIds(raw.geneva_run_datasource_ids),
                    durations_minutes: parsePositiveIntegers(raw.geneva_run_durations_minutes),
                    ari_years: parsePositiveIntegers(raw.geneva_run_ari_years)
                },
                hyetograph: {
                    distribution_type: "neh4_type_b",
                    time_step_minutes: parseFloat(raw.geneva_run_time_step_minutes || "1.0")
                },
                runoff_model: runoffModel
            };
        };

        controller.buildWorkflowPayload = function () {
            return {
                schema_version: 1,
                prepare: controller.buildPreparePayload(),
                panel: controller.buildPanelPayload(),
                run_batch: controller.buildRunPayload()
            };
        };

        controller.handleQueuedSubmission = function (taskLabel, eventName, response) {
            var payload = normalizeResponseBody(response);
            if (!payload || !payload.job_id) {
                controller.pushResponseStacktrace(controller, payload);
                controller.disconnect_status_stream(controller);
                return payload;
            }

            controller.appendStatus(taskLabel + " queued: " + payload.job_id, { phase: "queued" });
            controller.poll_completion_event = COMPLETION_EVENT;
            controller.connect_status_stream(controller);
            controller.set_rq_job_id(controller, payload.job_id);
            if (controller.events && typeof controller.events.emit === "function" && eventName) {
                controller.events.emit(eventName, {
                    job_id: payload.job_id,
                    response: payload
                });
            }
            controller.refreshState({ silent: true });
            return payload;
        };

        controller.submitRunWorkflow = function () {
            var config = normalizeConfig(controller);
            if (!config.run_workflow_url || !controller.form) {
                return Promise.resolve(null);
            }
            controller.setActiveHint("run");
            return controller.ensureConfigSyncedBeforeQueue().then(function () {
                controller.clearTransientUi();
                controller.appendStatus("Submitting Geneva workflow…", { phase: "pending" });
                return controller.http.postJsonWithSessionToken(
                    config.run_workflow_url,
                    controller.buildWorkflowPayload(),
                    { form: controller.form }
                ).then(function (response) {
                    return controller.handleQueuedSubmission("Geneva workflow", "geneva:workflow:queued", response);
                }).catch(function (error) {
                    controller.handleFailure(error, "geneva:state:error");
                    throw error;
                });
            });
        };

        controller.rebindDom = function () {
            controller.form = dom.qs(SELECTORS.form);
            if (!controller.form) {
                return false;
            }

            controller.info = createLegacyAdapter(dom.qs(SELECTORS.info, controller.form));
            controller.status = createLegacyAdapter(dom.qs(SELECTORS.status, controller.form));
            controller.stacktrace = createLegacyAdapter(dom.qs(SELECTORS.stacktrace, controller.form));
            controller.rq_job = createLegacyAdapter(dom.qs(SELECTORS.rqJob, controller.form));
            var workflowHintElement = dom.qs(SELECTORS.hintRunWorkflow, controller.form) || dom.qs(SELECTORS.hintRunWorkflow);
            var runHintElement = dom.qs(SELECTORS.hintRunBatch, controller.form) || dom.qs(SELECTORS.hintRunBatch);
            var legacyHintElement = dom.qs(SELECTORS.hintLegacy, controller.form) || dom.qs(SELECTORS.hintLegacy);
            controller.hintTargets = {
                run: createLegacyAdapter(workflowHintElement || runHintElement || legacyHintElement)
            };
            controller.setActiveHint(controller.activeHintKey || "run");
            controller.resultsEl = dom.qs(SELECTORS.results);
            controller.configMessageEl = dom.qs(SELECTORS.configMessage, controller.form);
            controller.configNodeEl = dom.qs(SELECTORS.configNode, controller.form) || dom.qs(SELECTORS.configNode);
            controller.configNodeData = parseJsonNode(controller.configNodeEl);
            controller.statusPanelEl = dom.qs(SELECTORS.statusPanel);
            controller.stacktracePanelEl = dom.qs(SELECTORS.stacktracePanel);
            controller.statusSpinnerEl = controller.statusPanelEl ? controller.statusPanelEl.querySelector("#braille") : null;
            controller.syncPanelLinks();

            controller.detach_status_stream(controller);
            controller.attach_status_stream(controller, {
                element: controller.statusPanelEl,
                channel: STATUS_CHANNEL,
                stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
                spinner: controller.statusSpinnerEl
            });
            return true;
        };

        controller.bindDelegates = function () {
            if (!controller.form || controller._delegates.length > 0) {
                return;
            }

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.runWorkflow, function (event) {
                event.preventDefault();
                controller.submitRunWorkflow();
            }));
            controller._delegates.push(dom.delegate(controller.form, "change", "[data-geneva-field]", function (event) {
                if (!event || !event.target || !event.target.name) {
                    return;
                }
                if (!Object.values(CONFIG_FIELD_MAP).includes(String(event.target.name))) {
                    return;
                }
                controller.updateUnsavedConfigMessage();
            }));
        };

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function (eventName, payload) {
            if (String(eventName || "").toUpperCase() === COMPLETION_EVENT) {
                controller.refreshState({ silent: true });
            }
            return baseTriggerEvent(eventName, payload);
        };

        controller.bootstrap = function (context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            if (helper && typeof helper.getControllerContext === "function") {
                helper.getControllerContext(ctx, "geneva");
            }

            if (!controller.rebindDom()) {
                return;
            }
            controller.bindDelegates();
            controller.refreshState({ silent: true });
        };

        return controller;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}());

if (typeof window !== "undefined") {
    window.Geneva = Geneva;
}

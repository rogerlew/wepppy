/* ----------------------------------------------------------------------------
 * DSS Export
 * ----------------------------------------------------------------------------
 */
var DssExport = (function () {
    "use strict";

    var instance;

    var FORM_ID = "dss_export_form";
    var DSS_CHANNEL = "dss_export";
    var EXPORT_TASK = "dss:export";
    var EXPORT_MESSAGE = "Exporting to DSS";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        hint: "#hint_export_dss",
        mode1: "#dss_export_mode1_controls",
        mode2: "#dss_export_mode2_controls"
    };

    var ACTIONS = {
        modeToggle: '[data-action="dss-export-mode"]',
        runExport: '[data-action="dss-export-run"]'
    };

    var NAV_LINK_SELECTORS = [
        'a[href="#partitioned-dss-export-for-hec"]',
        'a[href="#dss-export"]'
    ];

    var EVENT_NAMES = [
        "dss:mode:changed",
        "dss:export:started",
        "dss:export:completed",
        "dss:export:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("DssExport controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("DssExport controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function") {
            throw new Error("DssExport controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("DssExport controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return {
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

    function parseMode(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback === undefined ? null : fallback;
        }
        var parsed = parseInt(String(value), 10);
        if (parsed === 1 || parsed === 2) {
            return parsed;
        }
        return fallback === undefined ? null : fallback;
    }

    function parseChannelIds(value) {
        if (value === undefined || value === null) {
            return [];
        }

        var tokens = [];
        if (Array.isArray(value)) {
            tokens = value.slice();
        } else if (typeof value === "string") {
            tokens = value.split(/[,;\s]+/);
        } else {
            tokens = [value];
        }

        var seen = new Set();
        var ids = [];
        tokens.forEach(function (token) {
            if (token === undefined || token === null || token === "") {
                return;
            }
            var parsed = parseInt(String(token).trim(), 10);
            if (!Number.isNaN(parsed) && parsed > 0 && !seen.has(parsed)) {
                seen.add(parsed);
                ids.push(parsed);
            }
        });
        return ids;
    }

    function collectExcludeOrders(payload) {
        var orders = [];
        if (!payload) {
            return orders;
        }

        for (var i = 1; i <= 5; i += 1) {
            var key = "dss_export_exclude_order_" + i;
            var raw = payload[key];
            var selected = false;

            if (Array.isArray(raw)) {
                selected = raw.some(function (value) {
                    return Boolean(value);
                });
            } else if (typeof raw === "string") {
                var lowered = raw.toLowerCase();
                selected = lowered === "true" || lowered === "on" || lowered === "1";
            } else {
                selected = Boolean(raw);
            }

            if (selected) {
                orders.push(i);
            }
        }

        if (orders.length === 0 && payload.dss_export_exclude_orders !== undefined) {
            var direct = payload.dss_export_exclude_orders;
            var values = Array.isArray(direct) ? direct : [direct];
            values.forEach(function (value) {
                var parsed = parseInt(String(value), 10);
                if (!Number.isNaN(parsed) && parsed >= 1 && parsed <= 5 && orders.indexOf(parsed) === -1) {
                    orders.push(parsed);
                }
            });
        }

        return orders;
    }

    function toggleNavEntries(dom, shouldShow) {
        NAV_LINK_SELECTORS.forEach(function (selector) {
            var links = [];
            try {
                links = dom.qsa(selector);
            } catch (err) {
                // ignore selector failures
            }
            if (!links || links.length === 0) {
                return;
            }
            links.forEach(function (link) {
                if (!link) {
                    return;
                }
                var target = link.parentElement || link;
                if (!target) {
                    return;
                }
                if (shouldShow) {
                    dom.show(target);
                } else {
                    dom.hide(target);
                }
            });
        });
    }

    function buildDownloadUrl(path) {
        var prefix = typeof window.site_prefix === "string" ? window.site_prefix : "";
        var normalizedPrefix = prefix.replace(/\/+$/, "");
        var normalizedPath = (path || "").replace(/^\/+/, "");
        if (!normalizedPrefix) {
            return normalizedPath || "/";
        }
        if (!normalizedPath) {
            return normalizedPrefix;
        }
        return normalizedPrefix + "/" + normalizedPath;
    }

    function applyMode(controller, mode, options) {
        if (!controller) {
            return null;
        }
        var fallback = options && options.fallback !== undefined ? options.fallback : controller.state.mode || 1;
        var parsed = parseMode(mode, null);
        if (parsed === null) {
            parsed = parseMode(fallback, 1);
        }
        if (parsed !== 1 && parsed !== 2) {
            throw new Error("ValueError: unknown mode");
        }

        controller.state.mode = parsed;

        var panel1 = controller.modePanels ? controller.modePanels[1] : null;
        var panel2 = controller.modePanels ? controller.modePanels[2] : null;

        if (parsed === 1) {
            if (panel1 && typeof panel1.show === "function") {
                panel1.show();
            }
            if (panel2 && typeof panel2.hide === "function") {
                panel2.hide();
            }
        } else {
            if (panel1 && typeof panel1.hide === "function") {
                panel1.hide();
            }
            if (panel2 && typeof panel2.show === "function") {
                panel2.show();
            }
        }

        if (controller.form && (options ? options.updateRadios !== false : true)) {
            var radios = controller.form.querySelectorAll("input[name='dss_export_mode']");
            radios.forEach(function (radio) {
                if (!radio) {
                    return;
                }
                radio.checked = String(radio.value) === String(parsed);
            });
        }

        if (!options || options.emit !== false) {
            var detail = { mode: parsed };
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("dss:mode:changed", detail);
            }
            controller.triggerEvent("dss:mode:changed", detail);
        }

        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = null;

        if (eventsApi && typeof eventsApi.createEmitter === "function") {
            var baseEmitter = eventsApi.createEmitter();
            emitter = typeof eventsApi.useEventMap === "function"
                ? eventsApi.useEventMap(EVENT_NAMES, baseEmitter)
                : baseEmitter;
        }

        var formElement = null;
        try {
            formElement = dom.qs(SELECTORS.form);
        } catch (err) {
            console.warn("DssExport controller could not locate form:", err);
        }

        var containerElement = null;
        if (formElement && typeof formElement.closest === "function") {
            containerElement = formElement.closest(".controller-section");
        }
        if (!containerElement) {
            containerElement = formElement || null;
        }

        var infoElement = formElement ? dom.qs(SELECTORS.info, formElement) : null;
        var statusElement = formElement ? dom.qs(SELECTORS.status, formElement) : null;
        var stacktraceElement = formElement ? dom.qs(SELECTORS.stacktrace, formElement) : null;
        var rqJobElement = formElement ? dom.qs(SELECTORS.rqJob, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var mode1Element = formElement ? dom.qs(SELECTORS.mode1, formElement) : null;
        var mode2Element = formElement ? dom.qs(SELECTORS.mode2, formElement) : null;

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: formElement,
            container: containerElement,
            info: createLegacyAdapter(infoElement),
            status: createLegacyAdapter(statusElement),
            stacktrace: createLegacyAdapter(stacktraceElement),
            rq_job: createLegacyAdapter(rqJobElement),
            hint: createLegacyAdapter(hintElement),
            modePanels: {
                1: createLegacyAdapter(mode1Element),
                2: createLegacyAdapter(mode2Element)
            },
            command_btn_id: "btn_export_dss",
            state: {
                mode: 1
            },
            _delegates: []
        });

        controller.statusPanelEl = formElement ? dom.qs("#dss_export_status_panel") : null;
        controller.stacktracePanelEl = formElement ? dom.qs("#dss_export_stacktrace_panel") : null;
        var spinnerElement = controller.statusPanelEl ? controller.statusPanelEl.querySelector("#braille") : null;

        controller.attach_status_stream(controller, {
            element: controller.statusPanelEl,
            channel: DSS_CHANNEL,
            stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
            spinner: spinnerElement
        });

        controller.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (controller.statusStream && typeof controller.statusStream.append === "function") {
                controller.statusStream.append(message, meta || null);
                return;
            }
            if (controller.status && typeof controller.status.html === "function") {
                controller.status.html(message);
                return;
            }
            if (statusElement) {
                statusElement.innerHTML = message;
            }
        };

        controller.hideStacktrace = function () {
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        controller.setMode = function (mode) {
            return applyMode(controller, mode, { emit: true, updateRadios: true });
        };

        controller.buildRequestPayload = function () {
            if (!controller.form) {
                return {};
            }
            var payload = forms.serializeForm(controller.form, { format: "json" }) || {};
            var currentMode = parseMode(payload.dss_export_mode, controller.state.mode || 1);
            var channelIds = parseChannelIds(payload.dss_export_channel_ids);
            var excludeOrders = collectExcludeOrders(payload);

            return {
                dss_export_mode: currentMode,
                dss_export_channel_ids: channelIds,
                dss_export_exclude_orders: excludeOrders
            };
        };

        controller.export = function () {
            if (!controller.form) {
                return;
            }

            controller.info.html("");
            controller.appendStatus(EXPORT_MESSAGE + "…");
            controller.stacktrace.text("");
            controller.hideStacktrace();
            if (controller.hint && typeof controller.hint.text === "function") {
                controller.hint.text("");
            }

            var payload = controller.buildRequestPayload();
            controller.state.mode = payload.dss_export_mode || controller.state.mode || 1;

            controller.triggerEvent("job:started", {
                task: EXPORT_TASK,
                payload: payload
            });
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("dss:export:started", {
                    task: EXPORT_TASK,
                    payload: payload
                });
            }

            controller.connect_status_stream(controller);

            http.postJson("rq/api/post_dss_export_rq", payload, { form: controller.form }).then(function (response) {
                var body = response && response.body ? response.body : response;
                var normalized = body || {};

                if (normalized.Success === true || normalized.success === true) {
                    var jobId = normalized.job_id || normalized.jobId || null;
                    controller.appendStatus("post_dss_export_rq job submitted: " + jobId);
                    controller.set_rq_job_id(controller, jobId);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("dss:export:started", {
                            task: EXPORT_TASK,
                            payload: payload,
                            jobId: jobId,
                            status: "queued"
                        });
                    }
                    return;
                }

                controller.pushResponseStacktrace(controller, normalized);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("dss:export:error", {
                        task: EXPORT_TASK,
                        error: normalized
                    });
                }
                controller.triggerEvent("job:error", {
                    task: EXPORT_TASK,
                    error: normalized
                });
                controller.disconnect_status_stream(controller);
            }).catch(function (error) {
                controller.pushErrorStacktrace(controller, error);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("dss:export:error", {
                        task: EXPORT_TASK,
                        error: error
                    });
                }
                controller.triggerEvent("job:error", {
                    task: EXPORT_TASK,
                    error: error
                });
                controller.disconnect_status_stream(controller);
            });
        };

        controller.report = function () {
            var href = buildDownloadUrl("browse/export/dss.zip");
            controller.info.html("<a href='" + href + "' target='_blank'>Download DSS Export Results (.zip)</a>");
        };

        controller.handleExportTaskCompleted = function (detail) {
            controller.disconnect_status_stream(controller);
            controller.report();
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("dss:export:completed", {
                    task: EXPORT_TASK,
                    jobId: controller.rq_job_id || null,
                    detail: detail || null
                });
            }
            controller.triggerEvent("job:completed", {
                task: EXPORT_TASK,
                jobId: controller.rq_job_id || null,
                detail: detail || null
            });
        };

        controller.show = function () {
            if (controller.container) {
                dom.show(controller.container);
            }
            toggleNavEntries(dom, true);
        };

        controller.hide = function () {
            if (controller.container) {
                dom.hide(controller.container);
            }
            toggleNavEntries(dom, false);
        };

        controller.dispose = function () {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            controller.detach_status_stream(controller);
        };

        if (formElement) {
            controller._delegates.push(dom.delegate(formElement, "change", ACTIONS.modeToggle, function (event, target) {
                event.preventDefault();
                var datasetMode = target && target.getAttribute("data-dss-export-mode");
                var nextMode = parseMode(datasetMode || (target ? target.value : undefined), null);
                try {
                    controller.setMode(nextMode);
                } catch (err) {
                    console.error("[DssExport] Unable to set mode:", err);
                }
            }));

            controller._delegates.push(dom.delegate(formElement, "click", ACTIONS.runExport, function (event) {
                event.preventDefault();
                controller.export();
            }));

            formElement.addEventListener("DSS_EXPORT_TASK_COMPLETED", function (event) {
                controller.handleExportTaskCompleted(event && event.detail ? event.detail : null);
            });
        }

        var initialModeElement = formElement ? formElement.querySelector("input[name='dss_export_mode']:checked") : null;
        var initialMode = parseMode(initialModeElement ? initialModeElement.value : null, 1);
        controller.state.mode = initialMode;
        try {
            applyMode(controller, initialMode, { emit: false, updateRadios: true, fallback: 1 });
        } catch (err) {
            console.warn("[DssExport] Failed to apply initial mode:", err);
        }

        controller.hideStacktrace();

        return controller;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.DssExport = DssExport;
}

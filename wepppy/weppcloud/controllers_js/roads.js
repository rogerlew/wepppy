/* ----------------------------------------------------------------------------
 * Roads
 * Doc: controllers_js/README.md — Roads Controller Reference (2026 helper migration)
 * ----------------------------------------------------------------------------
 */
var Roads = (function () {
    "use strict";

    var instance;

    var FORM_ID = "roads_form";
    var STATUS_CHANNEL = "roads";

    var TASKS = {
        upload: {
            eventPrefix: "roads:upload",
            label: "Uploading roads GeoJSON",
            successMessage: "Roads GeoJSON uploaded successfully."
        },
        prepare: {
            eventPrefix: "roads:prepare",
            label: "Submitting Roads segment preparation and lowpoint mapping",
            queueName: "run_roads_prepare_rq",
            completionEvent: "ROADS_PREPARE_TASK_COMPLETED",
            requestPath: "tasks/roads/prepare_segments"
        },
        run: {
            eventPrefix: "roads:run",
            label: "Submitting Roads run",
            queueName: "run_roads_rq",
            completionEvent: "ROADS_RUN_TASK_COMPLETED",
            requestPath: "tasks/roads/run"
        }
    };

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#roads_info",
        results: "#roads-results",
        status: "#roads_status",
        stacktrace: "#roads_stacktrace",
        rqJob: "#rq_job",
        hint: "#hint_run_roads",
        uploadInput: "#roads_geojson_file",
        uploadProgress: "#roads_geojson_file-progress",
        uploadProgressFill: ".wc-upload-progress__fill",
        uploadProgressStatus: ".wc-upload-progress__status",
        uploadMessage: "#roads_upload_message",
        mappingSection: "#roads_attribute_mapping_section",
        mappingPreview: "#roads_attribute_catalog_preview",
        mappingMessage: "#roads_mapping_message",
        mappingSelects: "[data-roads-map-field]",
        defaultSelects: "[data-roads-default-field]"
    };

    var ACTIONS = {
        upload: "[data-roads-action='upload']",
        prepare: "[data-roads-action='prepare-segments']",
        run: "[data-roads-action='run']",
        applyMapping: "[data-roads-action='apply-attribute-mapping']"
    };

    var EVENT_NAMES = [
        "roads:upload:started",
        "roads:upload:completed",
        "roads:upload:error",
        "roads:mapping:started",
        "roads:mapping:completed",
        "roads:mapping:error",
        "roads:prepare:started",
        "roads:prepare:completed",
        "roads:prepare:error",
        "roads:run:started",
        "roads:run:completed",
        "roads:run:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    var SURFACE_DEFAULT_OPTIONS = ["gravel", "paved"];
    var TRAFFIC_DEFAULT_OPTIONS = ["high", "low", "none"];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" || typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("Roads controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Roads controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function" || typeof http.getJson !== "function") {
            throw new Error("Roads controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Roads controller requires WCEvents helpers.");
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

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function resolveRunUrl(path, options) {
        if (typeof url_for_run === "function") {
            return url_for_run(path, options || {});
        }
        return path;
    }

    function toResponsePayload(http, error) {
        function coerceBody(raw) {
            if (!raw) {
                return null;
            }
            if (typeof raw === "string") {
                try {
                    return JSON.parse(raw);
                } catch (err) {
                    return raw;
                }
            }
            return raw;
        }

        var body = coerceBody(error && error.body ? error.body : null);

        if (body && typeof body === "object") {
            if (body.error || body.errors) {
                return body;
            }
            if (body.message || body.detail) {
                return { error: { message: body.message || body.detail, details: body.details } };
            }
            return body;
        } else if (typeof body === "string" && body) {
            return { error: { message: body } };
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            if (detail && typeof detail === "object" && (detail.error || detail.errors)) {
                return detail;
            }
            return { error: { message: detail || "Request failed" } };
        }

        return { error: { message: (error && error.message) || "Request failed" } };
    }

    function extractErrorMessage(payload, fallback) {
        if (payload && payload.error) {
            if (typeof payload.error === "string") {
                return payload.error;
            }
            if (payload.error && typeof payload.error.message === "string") {
                return payload.error.message;
            }
            if (payload.error && typeof payload.error.detail === "string") {
                return payload.error.detail;
            }
        }
        if (payload && typeof payload.message === "string") {
            return payload.message;
        }
        if (payload && typeof payload.detail === "string") {
            return payload.detail;
        }
        return fallback;
    }

    function parseJsonOrNull(text) {
        if (!text || typeof text !== "string") {
            return null;
        }
        try {
            return JSON.parse(text);
        } catch (err) {
            return null;
        }
    }

    function createInstance() {
        if (typeof controlBase !== "function") {
            throw new Error("Roads controller requires controlBase helper.");
        }

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
        var infoElement = null;
        var resultsElement = null;
        var statusElement = null;
        var stacktraceElement = null;
        var rqJobElement = null;
        var hintElement = null;
        var uploadInputElement = null;
        var uploadProgressElement = null;
        var uploadProgressFillElement = null;
        var uploadProgressStatusElement = null;
        var uploadMessageElement = null;
        var mappingSectionElement = null;
        var mappingPreviewElement = null;
        var mappingMessageElement = null;
        var mappingSelectElements = [];
        var defaultSelectElements = [];

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: null,
            info: createLegacyAdapter(null),
            resultsContainer: null,
            status: createLegacyAdapter(null),
            stacktrace: createLegacyAdapter(null),
            rq_job: createLegacyAdapter(null),
            hint: createLegacyAdapter(null),
            uploadMessage: createLegacyAdapter(null),
            mappingMessage: createLegacyAdapter(null),
            statusPanelEl: null,
            stacktracePanelEl: null,
            statusSpinnerEl: null,
            statusStream: null,
            command_btn_id: "run_roads_wepp",
            _delegates: [],
            _completionSeen: {
                prepare: false,
                run: false
            },
            _lastQueuedTask: null,
            _activeTaskKey: null,
            _activeJobId: null,
            _taskRequestInFlight: false
        });

        function detachDelegates() {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
        }

        function updateUploadProgress(percent, statusText, visible) {
            if (!uploadProgressElement) {
                return;
            }
            var resolvedPercent = Number.isFinite(percent) ? Math.max(0, Math.min(100, Math.round(percent))) : null;
            var text = statusText || "";

            if (resolvedPercent !== null && uploadProgressFillElement && uploadProgressFillElement.style) {
                uploadProgressFillElement.style.width = String(resolvedPercent) + "%";
            }
            if (uploadProgressStatusElement) {
                if (!text && resolvedPercent !== null) {
                    text = "Uploading: " + String(resolvedPercent) + "%";
                }
                uploadProgressStatusElement.textContent = text;
            }
            if (visible === true) {
                dom.show(uploadProgressElement);
            } else if (visible === false) {
                dom.hide(uploadProgressElement);
            }
        }

        function resetUploadProgress() {
            updateUploadProgress(0, "Uploading: 0%", false);
        }

        function setUploadMessage(text) {
            if (controller.uploadMessage && typeof controller.uploadMessage.text === "function") {
                controller.uploadMessage.text(text || "");
            }
        }

        function setMappingMessage(text) {
            if (controller.mappingMessage && typeof controller.mappingMessage.text === "function") {
                controller.mappingMessage.text(text || "");
            }
        }

        function hideStacktrace() {
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
                return;
            }
            if (!stacktraceElement) {
                return;
            }
            stacktraceElement.hidden = true;
            if (stacktraceElement.style) {
                stacktraceElement.style.display = "none";
            }
        }

        function ensureStatusStreamAttached(reattach) {
            if (!controller.statusPanelEl) {
                return;
            }
            if (reattach && typeof controller.detach_status_stream === "function") {
                controller.detach_status_stream(controller);
            }
            if (!controller.statusStream && typeof controller.attach_status_stream === "function") {
                controller.attach_status_stream(controller, {
                    element: controller.statusPanelEl,
                    form: controller.form || null,
                    channel: STATUS_CHANNEL,
                    runId: window.runid || window.runId || null,
                    stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
                    spinner: controller.statusSpinnerEl || null
                });
            }
        }

        function rebindDomReferences(forceReattachStream) {
            var nextForm = null;
            try {
                nextForm = dom.qs(SELECTORS.form);
            } catch (err) {
                nextForm = null;
            }

            var formChanged = nextForm !== controller.form;
            if (formChanged) {
                controller.form = nextForm || null;
                formElement = controller.form || null;
            }

            function syncAdapter(selector, currentElement, assign) {
                var next = controller.form ? dom.qs(selector, controller.form) : null;
                if (next !== currentElement) {
                    assign(next);
                }
            }

            syncAdapter(SELECTORS.info, infoElement, function (next) {
                infoElement = next;
                controller.info = createLegacyAdapter(infoElement);
            });
            var nextResults = null;
            try {
                nextResults = dom.qs(SELECTORS.results);
            } catch (errResults) {
                nextResults = null;
            }
            if (nextResults !== resultsElement) {
                resultsElement = nextResults;
                controller.resultsContainer = resultsElement;
            }
            syncAdapter(SELECTORS.status, statusElement, function (next) {
                statusElement = next;
                controller.status = createLegacyAdapter(statusElement);
            });
            syncAdapter(SELECTORS.stacktrace, stacktraceElement, function (next) {
                stacktraceElement = next;
                controller.stacktrace = createLegacyAdapter(stacktraceElement);
            });
            syncAdapter(SELECTORS.rqJob, rqJobElement, function (next) {
                rqJobElement = next;
                controller.rq_job = createLegacyAdapter(rqJobElement);
            });
            syncAdapter(SELECTORS.hint, hintElement, function (next) {
                hintElement = next;
                controller.hint = createLegacyAdapter(hintElement);
            });
            syncAdapter(SELECTORS.uploadInput, uploadInputElement, function (next) {
                uploadInputElement = next;
            });
            syncAdapter(SELECTORS.uploadProgress, uploadProgressElement, function (next) {
                uploadProgressElement = next;
                uploadProgressFillElement = uploadProgressElement ? uploadProgressElement.querySelector(SELECTORS.uploadProgressFill) : null;
                uploadProgressStatusElement = uploadProgressElement ? uploadProgressElement.querySelector(SELECTORS.uploadProgressStatus) : null;
            });
            syncAdapter(SELECTORS.uploadMessage, uploadMessageElement, function (next) {
                uploadMessageElement = next;
                controller.uploadMessage = createLegacyAdapter(uploadMessageElement);
            });
            syncAdapter(SELECTORS.mappingSection, mappingSectionElement, function (next) {
                mappingSectionElement = next;
            });
            syncAdapter(SELECTORS.mappingPreview, mappingPreviewElement, function (next) {
                mappingPreviewElement = next;
            });
            syncAdapter(SELECTORS.mappingMessage, mappingMessageElement, function (next) {
                mappingMessageElement = next;
                controller.mappingMessage = createLegacyAdapter(mappingMessageElement);
            });
            mappingSelectElements = controller.form
                ? Array.prototype.slice.call(controller.form.querySelectorAll(SELECTORS.mappingSelects))
                : [];
            defaultSelectElements = controller.form
                ? Array.prototype.slice.call(controller.form.querySelectorAll(SELECTORS.defaultSelects))
                : [];

            var nextStatusPanel = null;
            var nextStacktracePanel = null;
            try {
                nextStatusPanel = dom.qs("#roads_status_panel");
            } catch (err) {
                nextStatusPanel = null;
            }
            try {
                nextStacktracePanel = dom.qs("#roads_stacktrace_panel");
            } catch (err2) {
                nextStacktracePanel = null;
            }
            var nextSpinner = nextStatusPanel ? nextStatusPanel.querySelector("#braille") : null;
            var panelChanged = (
                nextStatusPanel !== controller.statusPanelEl
                || nextStacktracePanel !== controller.stacktracePanelEl
                || nextSpinner !== controller.statusSpinnerEl
            );

            controller.statusPanelEl = nextStatusPanel || null;
            controller.stacktracePanelEl = nextStacktracePanel || null;
            controller.statusSpinnerEl = nextSpinner || null;

            if (panelChanged || forceReattachStream === true) {
                ensureStatusStreamAttached(true);
            } else {
                ensureStatusStreamAttached(false);
            }

            if (formChanged) {
                resetUploadProgress();
            }
        }

        function attachDelegates(force) {
            if (!controller.form) {
                detachDelegates();
                return;
            }
            if (!force && controller._delegates.length > 0) {
                return;
            }
            detachDelegates();

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.upload, function (event) {
                event.preventDefault();
                controller.uploadGeojson();
            }));
            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.prepare, function (event) {
                event.preventDefault();
                controller.prepareSegments();
            }));
            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.run, function (event) {
                event.preventDefault();
                controller.runRoads();
            }));
            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.applyMapping, function (event) {
                event.preventDefault();
                controller.applyAttributeMapping();
            }));
        }

        function resolveMaxUploadBytes() {
            var fallbackMb = 50;
            if (!controller.form || !controller.form.dataset) {
                return fallbackMb * 1024 * 1024;
            }
            var raw = controller.form.dataset.roadsMaxUploadMb;
            var parsed = parseInt(raw, 10);
            if (!Number.isFinite(parsed) || parsed <= 0) {
                parsed = fallbackMb;
            }
            return parsed * 1024 * 1024;
        }

        function renderUploadSummary(payload) {
            if (!controller.info || typeof controller.info.html !== "function") {
                return;
            }
            var summary = payload && payload.Content ? payload.Content : payload;
            if (!summary || typeof summary !== "object") {
                controller.info.html("");
                return;
            }
            var relpath = summary.uploaded_geojson_relpath ? String(summary.uploaded_geojson_relpath) : null;
            var featureCount = summary.feature_count;
            var pieces = [];
            if (relpath) {
                pieces.push("<div><strong>Uploaded:</strong> <code>" + escapeHtml(relpath) + "</code></div>");
            }
            if (featureCount !== undefined && featureCount !== null && !Number.isNaN(Number(featureCount))) {
                pieces.push("<div><strong>Feature count:</strong> " + escapeHtml(String(featureCount)) + "</div>");
            }
            if (pieces.length > 0) {
                controller.info.html("<div class=\"wc-stack-sm\">" + pieces.join("") + "</div>");
            }
        }

        function extractPayload(rawPayload) {
            if (!rawPayload || typeof rawPayload !== "object") {
                return {};
            }
            if (rawPayload.Content && typeof rawPayload.Content === "object") {
                return rawPayload.Content;
            }
            return rawPayload;
        }

        function normalizeFieldNames(catalog) {
            if (!catalog || typeof catalog !== "object" || !Array.isArray(catalog.field_names)) {
                return [];
            }
            return catalog.field_names.filter(function (fieldName) {
                return typeof fieldName === "string" && fieldName.length > 0;
            });
        }

        function normalizeMappingState(summary) {
            var roadsParams = summary && typeof summary === "object" && summary.roads_params && typeof summary.roads_params === "object"
                ? summary.roads_params
                : {};
            var map = summary && typeof summary === "object" && summary.attribute_field_map && typeof summary.attribute_field_map === "object"
                ? summary.attribute_field_map
                : (roadsParams.attribute_field_map && typeof roadsParams.attribute_field_map === "object"
                    ? roadsParams.attribute_field_map
                    : {});
            return {
                design: typeof map.design === "string" ? map.design : "",
                surface: typeof map.surface === "string" ? map.surface : "",
                traffic: typeof map.traffic === "string" ? map.traffic : ""
            };
        }

        function normalizeFallbackDefaults(summary) {
            var roadsParams = summary && typeof summary === "object" && summary.roads_params && typeof summary.roads_params === "object"
                ? summary.roads_params
                : null;
            var hasRoadsParams = !!roadsParams;
            var rawSurface = roadsParams && typeof roadsParams.surface_default === "string"
                ? roadsParams.surface_default.toLowerCase()
                : "";
            var rawTraffic = roadsParams && typeof roadsParams.traffic_default === "string"
                ? roadsParams.traffic_default.toLowerCase()
                : "";

            return {
                hasRoadsParams: hasRoadsParams,
                surface_default: SURFACE_DEFAULT_OPTIONS.indexOf(rawSurface) !== -1 ? rawSurface : "gravel",
                traffic_default: TRAFFIC_DEFAULT_OPTIONS.indexOf(rawTraffic) !== -1 ? rawTraffic : "low"
            };
        }

        function applySelectOptions(selectElement, fieldNames, selectedValue) {
            if (!selectElement) {
                return;
            }
            while (selectElement.firstChild) {
                selectElement.removeChild(selectElement.firstChild);
            }

            function addOption(value, text) {
                var option = document.createElement("option");
                option.value = value;
                option.textContent = text;
                selectElement.appendChild(option);
            }

            addOption("", "Auto / Unset");
            fieldNames.forEach(function (fieldName) {
                addOption(fieldName, fieldName);
            });
            if (selectedValue && fieldNames.indexOf(selectedValue) === -1) {
                addOption(selectedValue, selectedValue + " (not in current upload)");
            }
            selectElement.value = selectedValue || "";
        }

        function applyDefaultValueOptions(selectElement, options, selectedValue) {
            if (!selectElement) {
                return;
            }
            while (selectElement.firstChild) {
                selectElement.removeChild(selectElement.firstChild);
            }

            options.forEach(function (value) {
                var option = document.createElement("option");
                option.value = value;
                option.textContent = value;
                selectElement.appendChild(option);
            });

            var resolved = options.indexOf(selectedValue) !== -1 ? selectedValue : options[0];
            selectElement.value = resolved;
        }

        function renderAttributeCatalogPreview(catalog) {
            if (!mappingPreviewElement) {
                return;
            }
            if (!catalog || typeof catalog !== "object") {
                mappingPreviewElement.innerHTML = "<p class=\"wc-field__help\">Upload a GeoJSON file to discover attributes.</p>";
                return;
            }

            var fieldNames = normalizeFieldNames(catalog);
            var fieldCount = Number(catalog.field_count || fieldNames.length || 0);
            var totalFeatures = Number(catalog.total_feature_count || 0);
            var profiledFeatures = Number(catalog.profiled_feature_count || totalFeatures);
            var profileRows = Array.isArray(catalog.field_profiles) ? catalog.field_profiles : [];
            var previewRows = profileRows.slice(0, 8).map(function (row) {
                var samples = Array.isArray(row.sample_values) && row.sample_values.length
                    ? row.sample_values.map(function (sample) { return "<code>" + escapeHtml(String(sample)) + "</code>"; }).join(", ")
                    : "<span class=\"wc-text-muted\">(none)</span>";
                return "<li><strong>" + escapeHtml(String(row.name || "")) + "</strong>: " + samples + "</li>";
            }).join("");

            var summary = [
                "<div><strong>Discovered fields:</strong> " + escapeHtml(String(fieldCount)) + "</div>",
                "<div><strong>Features profiled:</strong> " + escapeHtml(String(profiledFeatures)) + " / " + escapeHtml(String(totalFeatures)) + "</div>"
            ];
            if (previewRows) {
                summary.push("<div><strong>Sample values:</strong><ul class=\"wc-list\">" + previewRows + "</ul></div>");
            }
            if (profileRows.length > 8) {
                summary.push("<p class=\"wc-field__help\">Showing first 8 fields by name.</p>");
            }

            mappingPreviewElement.innerHTML = "<div class=\"wc-stack-sm\">" + summary.join("") + "</div>";
        }

        function renderAttributeMappingState(rawPayload) {
            var summary = extractPayload(rawPayload);
            var catalog = summary.discovered_attribute_catalog && typeof summary.discovered_attribute_catalog === "object"
                ? summary.discovered_attribute_catalog
                : null;
            var fieldNames = normalizeFieldNames(catalog);
            var mappingState = normalizeMappingState(summary);
            var fallbackState = normalizeFallbackDefaults(summary);

            if (mappingSectionElement) {
                mappingSectionElement.dataset.roadsHasAttributeCatalog = fieldNames.length ? "1" : "0";
            }
            mappingSelectElements.forEach(function (selectElement) {
                var mapField = selectElement.dataset ? selectElement.dataset.roadsMapField : "";
                var selectedValue = mapField && Object.prototype.hasOwnProperty.call(mappingState, mapField)
                    ? mappingState[mapField]
                    : "";
                applySelectOptions(selectElement, fieldNames, selectedValue);
            });
            defaultSelectElements.forEach(function (selectElement) {
                var defaultField = selectElement.dataset ? selectElement.dataset.roadsDefaultField : "";
                var fallbackOptions = defaultField === "traffic_default" ? TRAFFIC_DEFAULT_OPTIONS : SURFACE_DEFAULT_OPTIONS;
                var fallbackValue = "";
                if (defaultField && Object.prototype.hasOwnProperty.call(fallbackState, defaultField)) {
                    fallbackValue = fallbackState[defaultField];
                }
                if (!fallbackState.hasRoadsParams && selectElement.value) {
                    fallbackValue = selectElement.value;
                }
                applyDefaultValueOptions(selectElement, fallbackOptions, fallbackValue);
            });
            renderAttributeCatalogPreview(catalog);
        }

        function readAttributeMappingFromForm() {
            var payload = {};
            mappingSelectElements.forEach(function (selectElement) {
                var mapField = selectElement.dataset ? selectElement.dataset.roadsMapField : "";
                if (!mapField) {
                    return;
                }
                var value = selectElement.value || "";
                payload[mapField] = value ? value : null;
            });
            return payload;
        }

        function readFallbackDefaultsFromForm() {
            var payload = {};
            defaultSelectElements.forEach(function (selectElement) {
                var defaultField = selectElement.dataset ? selectElement.dataset.roadsDefaultField : "";
                if (!defaultField) {
                    return;
                }
                var value = selectElement.value || "";
                payload[defaultField] = value;
            });
            return payload;
        }

        function renderDecisionCounts(decisionCounts) {
            if (!decisionCounts || typeof decisionCounts !== "object") {
                return "";
            }
            var keys = Object.keys(decisionCounts).sort();
            if (!keys.length) {
                return "";
            }
            var items = keys.map(function (key) {
                return "<li><code>" + escapeHtml(key) + "</code>: " + escapeHtml(String(decisionCounts[key])) + "</li>";
            });
            return "<ul class=\"wc-list\">" + items.join("") + "</ul>";
        }

        function renderPrepareSummary(summary) {
            if (!controller.info || typeof controller.info.html !== "function") {
                return;
            }
            if (!summary || typeof summary !== "object") {
                return;
            }
            var decisionHtml = renderDecisionCounts(summary.eligible_lowpoint_decision_counts);
            var details = [
                "<div><strong>Eligible segments:</strong> " + escapeHtml(String(summary.eligible_segment_count || 0)) + "</div>",
                "<div><strong>Mapped lowpoints:</strong> " + escapeHtml(String(summary.eligible_with_lowpoint_ids || 0)) + "</div>"
            ];
            if (decisionHtml) {
                details.push("<div><strong>Lowpoint decisions:</strong>" + decisionHtml + "</div>");
            }
            controller.info.html("<div class=\"wc-stack-sm\">" + details.join("") + "</div>");
        }

        function renderRunSummary(summary) {
            if (!controller.info || typeof controller.info.html !== "function") {
                return;
            }
            if (!summary || typeof summary !== "object") {
                controller.info.html("");
                return;
            }

            var skippedReasonHtml = renderDecisionCounts(summary.skipped_segment_reason_counts);
            var details = [
                "<div><strong>Mapped segments:</strong> " + escapeHtml(String(summary.mapped_segment_count || 0)) + "</div>",
                "<div><strong>Targeted hillslopes:</strong> " + escapeHtml(String(summary.targeted_hillslope_count || 0)) + "</div>"
            ];
            if (skippedReasonHtml) {
                details.push("<div><strong>Skipped reasons:</strong>" + skippedReasonHtml + "</div>");
            }
            controller.info.html("<div class=\"wc-stack-sm\">" + details.join("") + "</div>");
        }

        function renderRoadsResultsPanel() {
            if (!controller.resultsContainer || !http || typeof http.request !== "function") {
                return Promise.resolve(null);
            }
            return http.request(resolveRunUrl("report/roads/results/")).then(function (result) {
                var body = result && result.body;
                if (typeof body === "string" && controller.resultsContainer) {
                    controller.resultsContainer.innerHTML = body;
                }
                return body;
            }).catch(function (error) {
                controller.pushResponseStacktrace(controller, toResponsePayload(http, error));
                return null;
            });
        }

        function renderLatestRoadsSummary(payload) {
            if (!payload || typeof payload !== "object") {
                return;
            }
            if (payload.last_run_summary && typeof payload.last_run_summary === "object") {
                renderRunSummary(payload.last_run_summary);
                return;
            }
            if (payload.last_prepare_summary && typeof payload.last_prepare_summary === "object") {
                renderPrepareSummary(payload.last_prepare_summary);
                return;
            }
            if (controller.info && typeof controller.info.html === "function") {
                controller.info.html("");
            }
        }

        function refreshRoadsResults(taskKey) {
            if (!http || typeof http.getJson !== "function") {
                return Promise.resolve(null);
            }
            return http.getJson(resolveRunUrl("api/roads/results")).then(function (result) {
                var payload = result && result.body ? result.body : {};
                if (taskKey === "prepare") {
                    renderPrepareSummary(payload.last_prepare_summary || null);
                } else if (taskKey === "run") {
                    renderRunSummary(payload.last_run_summary || null);
                }
                return payload;
            }).catch(function () {
                return null;
            });
        }

        function refreshRoadsSummary() {
            if (!http || typeof http.getJson !== "function") {
                return Promise.resolve(null);
            }
            return http.getJson(resolveRunUrl("api/roads/results")).then(function (result) {
                var payload = result && result.body ? result.body : {};
                renderLatestRoadsSummary(payload);
                return payload;
            }).catch(function () {
                return null;
            });
        }

        function refreshRoadsConfig() {
            if (!http || typeof http.getJson !== "function") {
                return Promise.resolve(null);
            }
            return http.getJson(resolveRunUrl("api/roads/config")).then(function (result) {
                var payload = result && result.body ? result.body : {};
                renderAttributeMappingState(payload);
                return payload;
            }).catch(function () {
                return null;
            });
        }

        function resolvePayloadJobId(payload) {
            if (!payload || typeof payload !== "object") {
                return null;
            }
            if (payload.job_id) {
                return String(payload.job_id);
            }
            if (payload.status && payload.status.job_id) {
                return String(payload.status.job_id);
            }
            return null;
        }

        function clearActiveTaskState() {
            controller._taskRequestInFlight = false;
            controller._activeTaskKey = null;
            controller._activeJobId = null;
            controller._lastQueuedTask = null;
        }

        function markTaskCompleted(taskKey, source, payload) {
            if (!TASKS[taskKey] || !controller.form) {
                return;
            }
            if (controller._activeTaskKey && controller._activeTaskKey !== taskKey) {
                return;
            }
            if (!controller._activeTaskKey && controller._lastQueuedTask && controller._lastQueuedTask !== taskKey) {
                return;
            }
            var payloadJobId = resolvePayloadJobId(payload);
            if (controller._activeJobId && payloadJobId && payloadJobId !== controller._activeJobId) {
                return;
            }
            if (source === "dom" && controller._activeJobId && !payloadJobId) {
                return;
            }
            if (controller._completionSeen[taskKey]) {
                return;
            }
            controller._completionSeen[taskKey] = true;
            var completedJobId = controller._activeJobId || controller.rq_job_id || payloadJobId || null;
            controller.disconnect_status_stream(controller);
            clearActiveTaskState();
            controller.set_rq_job_id(controller, null);

            if (taskKey === "prepare") {
                controller.append_status_message(controller, "Road segment candidates prepared.");
                refreshRoadsResults("prepare");
                renderRoadsResultsPanel();
            }
            if (taskKey === "run") {
                controller.append_status_message(controller, "Roads run completed.");
                refreshRoadsResults("run");
                renderRoadsResultsPanel();
            }

            if (emitter && typeof emitter.emit === "function") {
                emitter.emit(TASKS[taskKey].eventPrefix + ":completed", {
                    job_id: completedJobId,
                    source: source || "trigger",
                    task: taskKey
                });
            }
            if (!controller._job_completion_dispatched) {
                controller._job_completion_dispatched = true;
                controller.triggerEvent("job:completed", {
                    task: "roads:" + taskKey,
                    job_id: completedJobId,
                    source: source || "trigger"
                });
            }
        }

        function handleTaskError(taskKey, error) {
            var payload = toResponsePayload(http, error);
            controller.pushResponseStacktrace(controller, payload);
            controller.disconnect_status_stream(controller);
            if (emitter && typeof emitter.emit === "function") {
                emitter.emit(TASKS[taskKey].eventPrefix + ":error", {
                    error: payload,
                    task: taskKey
                });
            }
            controller.triggerEvent("job:error", {
                task: "roads:" + taskKey,
                error: payload
            });
            controller.set_rq_job_id(controller, null);
            clearActiveTaskState();
        }

        function queueTask(taskKey) {
            if (!TASKS[taskKey]) {
                return Promise.resolve(null);
            }
            rebindDomReferences(false);
            if (!controller.form) {
                return Promise.resolve(null);
            }
            if (controller._taskRequestInFlight || controller._activeTaskKey) {
                var activeTask = controller._activeTaskKey || controller._lastQueuedTask || "task";
                var conflictPayload = {
                    error: {
                        message: "Roads " + activeTask + " is already active. Wait for completion before starting another task."
                    }
                };
                controller.append_status_message(
                    controller,
                    "Roads " + activeTask + " is already active. Wait for completion before starting another task."
                );
                if (emitter && typeof emitter.emit === "function") {
                    emitter.emit(TASKS[taskKey].eventPrefix + ":error", {
                        error: conflictPayload,
                        task: taskKey
                    });
                }
                controller.triggerEvent("job:error", { task: "roads:" + taskKey, error: conflictPayload });
                return Promise.resolve(null);
            }

            var task = TASKS[taskKey];
            controller._completionSeen[taskKey] = false;
            controller._taskRequestInFlight = true;
            controller._activeTaskKey = taskKey;
            controller._activeJobId = null;
            controller._lastQueuedTask = taskKey;
            controller.poll_completion_event = task.completionEvent;

            setUploadMessage("");
            resetUploadProgress();
            controller.reset_panel_state(controller, {
                message: task.label,
                summaryTarget: [controller.info],
                stacktraceTarget: [controller.stacktrace, controller.stacktracePanelEl]
            });
            hideStacktrace();

            return http.request(resolveRunUrl(task.requestPath), {
                method: "POST",
                form: controller.form
            }).then(function (response) {
                var payload = response && response.body ? response.body : {};
                var jobId = payload && payload.job_id ? String(payload.job_id) : null;
                controller._taskRequestInFlight = false;
                if (!jobId) {
                    var missingJobPayload = {
                        error: {
                            message: "Queue response did not include a job_id."
                        }
                    };
                    controller.pushResponseStacktrace(controller, missingJobPayload);
                    controller.disconnect_status_stream(controller);
                    controller.set_rq_job_id(controller, null);
                    clearActiveTaskState();
                    if (emitter && typeof emitter.emit === "function") {
                        emitter.emit(task.eventPrefix + ":error", { error: missingJobPayload, task: taskKey });
                    }
                    controller.triggerEvent("job:error", { task: "roads:" + taskKey, error: missingJobPayload });
                    return null;
                }

                controller.poll_completion_event = task.completionEvent;
                controller.set_rq_job_id(controller, jobId);
                controller._activeJobId = jobId;
                controller.connect_status_stream(controller);
                controller.append_status_message(controller, task.queueName + " job submitted: " + jobId);
                if (emitter && typeof emitter.emit === "function") {
                    emitter.emit(task.eventPrefix + ":started", {
                        job_id: jobId,
                        task: taskKey,
                        status: "queued"
                    });
                }
                controller.triggerEvent("job:started", { task: "roads:" + taskKey, job_id: jobId });
                return payload;
            }).catch(function (error) {
                handleTaskError(taskKey, error);
                return null;
            });
        }

        controller.uploadGeojson = function uploadGeojson() {
            rebindDomReferences(false);
            if (!controller.form || !uploadInputElement) {
                return Promise.resolve(null);
            }

            var file = uploadInputElement.files && uploadInputElement.files.length > 0 ? uploadInputElement.files[0] : null;
            if (!file) {
                setUploadMessage("Select a .geojson file before uploading.");
                return Promise.resolve(null);
            }

            var filename = String(file.name || "");
            if (!/\.geojson$/i.test(filename)) {
                setUploadMessage("Roads upload must be a .geojson file.");
                uploadInputElement.value = "";
                return Promise.resolve(null);
            }

            var maxUploadBytes = resolveMaxUploadBytes();
            if (Number.isFinite(file.size) && file.size > maxUploadBytes) {
                var maxMb = Math.round(maxUploadBytes / (1024 * 1024));
                setUploadMessage("File exceeds maximum size of " + String(maxMb) + " MB.");
                uploadInputElement.value = "";
                return Promise.resolve(null);
            }

            controller.reset_panel_state(controller, {
                message: TASKS.upload.label,
                summaryTarget: [controller.info],
                stacktraceTarget: [controller.stacktrace, controller.stacktracePanelEl]
            });
            hideStacktrace();
            setUploadMessage("");
            updateUploadProgress(0, "Uploading: 0%", true);

            if (emitter && typeof emitter.emit === "function") {
                emitter.emit(TASKS.upload.eventPrefix + ":started", {
                    file_name: filename,
                    size_bytes: file.size
                });
            }
            controller.triggerEvent("job:started", { task: "roads:upload" });

            return new Promise(function (resolve) {
                var formData = new window.FormData();
                formData.append("file", file);

                var xhr = new window.XMLHttpRequest();
                xhr.open("POST", resolveRunUrl("tasks/roads/upload_geojson"));
                xhr.withCredentials = true;

                if (http && typeof http.getCsrfToken === "function") {
                    var csrfToken = http.getCsrfToken(controller.form);
                    if (csrfToken) {
                        xhr.setRequestHeader("X-CSRFToken", csrfToken);
                    }
                }

                xhr.upload.addEventListener("progress", function (event) {
                    if (!event.lengthComputable) {
                        return;
                    }
                    var percent = Math.round((event.loaded / event.total) * 100);
                    updateUploadProgress(percent, "Uploading: " + String(percent) + "%", true);
                });

                xhr.addEventListener("load", function () {
                    var parsed = parseJsonOrNull(xhr.responseText);
                    if (xhr.status >= 200 && xhr.status < 300) {
                        updateUploadProgress(100, "Upload complete.", true);
                        setUploadMessage(TASKS.upload.successMessage);
                        setMappingMessage("");
                        controller.append_status_message(controller, TASKS.upload.successMessage);
                        renderUploadSummary(parsed || {});
                        renderAttributeMappingState(parsed || {});
                        if (emitter && typeof emitter.emit === "function") {
                            emitter.emit(TASKS.upload.eventPrefix + ":completed", {
                                response: parsed || {},
                                file_name: filename
                            });
                        }
                        controller.triggerEvent("job:completed", {
                            task: "roads:upload",
                            response: parsed || {}
                        });
                        uploadInputElement.value = "";
                        resolve(parsed || {});
                        return;
                    }

                    var payload = parsed || { error: { message: xhr.statusText || "Upload failed." } };
                    setUploadMessage(extractErrorMessage(payload, "Upload failed."));
                    setMappingMessage("");
                    updateUploadProgress(0, "Upload failed.", true);
                    controller.pushResponseStacktrace(controller, payload);
                    if (emitter && typeof emitter.emit === "function") {
                        emitter.emit(TASKS.upload.eventPrefix + ":error", { error: payload });
                    }
                    controller.triggerEvent("job:error", { task: "roads:upload", error: payload });
                    resolve(null);
                });

                xhr.addEventListener("error", function () {
                    var payload = { error: { message: "Network error during upload." } };
                    setUploadMessage(payload.error.message);
                    setMappingMessage("");
                    updateUploadProgress(0, "Upload failed.", true);
                    controller.pushResponseStacktrace(controller, payload);
                    if (emitter && typeof emitter.emit === "function") {
                        emitter.emit(TASKS.upload.eventPrefix + ":error", { error: payload });
                    }
                    controller.triggerEvent("job:error", { task: "roads:upload", error: payload });
                    resolve(null);
                });

                xhr.send(formData);
            });
        };

        controller.prepareSegments = function prepareSegments() {
            return queueTask("prepare");
        };

        controller.runRoads = function runRoads() {
            return queueTask("run");
        };

        controller.applyAttributeMapping = function applyAttributeMapping() {
            rebindDomReferences(false);
            if (!controller.form || !http || typeof http.request !== "function") {
                return Promise.resolve(null);
            }

            var payload = {
                attribute_field_map: readAttributeMappingFromForm()
            };
            Object.assign(payload, readFallbackDefaultsFromForm());
            setUploadMessage("");
            setMappingMessage("");
            hideStacktrace();
            controller.append_status_message(controller, "Applying Roads attribute mapping and defaults.");

            if (emitter && typeof emitter.emit === "function") {
                emitter.emit("roads:mapping:started", { payload: payload });
            }

            return http.request(resolveRunUrl("tasks/roads/set_params"), {
                method: "POST",
                form: controller.form,
                json: payload
            }).then(function (response) {
                var body = response && response.body ? response.body : {};
                renderAttributeMappingState(body);
                setMappingMessage("Attribute mapping and fallback defaults applied.");
                controller.append_status_message(controller, "Roads attribute mapping and defaults applied.");
                refreshRoadsSummary();
                if (emitter && typeof emitter.emit === "function") {
                    emitter.emit("roads:mapping:completed", { response: body });
                }
                return body;
            }).catch(function (error) {
                var responsePayload = toResponsePayload(http, error);
                controller.pushResponseStacktrace(controller, responsePayload);
                setMappingMessage(extractErrorMessage(responsePayload, "Failed to apply attribute mapping."));
                if (emitter && typeof emitter.emit === "function") {
                    emitter.emit("roads:mapping:error", { error: responsePayload });
                }
                return null;
            });
        };

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            rebindDomReferences(false);
            attachDelegates(true);

            var helper = window.WCControllerBootstrap || null;
            var runJobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, TASKS.run.queueName)
                : null;
            var prepareJobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, TASKS.prepare.queueName)
                : null;

            var candidateJobId = runJobId || prepareJobId;
            var candidateTask = runJobId ? "run" : (prepareJobId ? "prepare" : null);

            if (!candidateJobId && ctx && ctx.jobIds && typeof ctx.jobIds === "object") {
                if (ctx.jobIds[TASKS.run.queueName]) {
                    candidateJobId = String(ctx.jobIds[TASKS.run.queueName]);
                    candidateTask = "run";
                } else if (ctx.jobIds[TASKS.prepare.queueName]) {
                    candidateJobId = String(ctx.jobIds[TASKS.prepare.queueName]);
                    candidateTask = "prepare";
                }
            }

            if (candidateJobId && candidateTask) {
                controller._completionSeen[candidateTask] = false;
                controller._lastQueuedTask = candidateTask;
                controller._activeTaskKey = candidateTask;
                controller._activeJobId = candidateJobId;
                controller._taskRequestInFlight = false;
                controller.poll_completion_event = TASKS[candidateTask].completionEvent;
                controller.set_rq_job_id(controller, candidateJobId);
            }

            refreshRoadsConfig();
            refreshRoadsSummary();
            renderRoadsResultsPanel();

            return controller;
        };

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function triggerEvent(eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === TASKS.prepare.completionEvent) {
                markTaskCompleted("prepare", payload && payload.source ? payload.source : "trigger", payload || null);
            } else if (normalized === TASKS.run.completionEvent) {
                markTaskCompleted("run", payload && payload.source ? payload.source : "trigger", payload || null);
            }
            return baseTriggerEvent(eventName, payload);
        };

        rebindDomReferences(true);
        attachDelegates(true);
        if (controller.form) {
            controller.form.addEventListener(TASKS.prepare.completionEvent, function (event) {
                markTaskCompleted("prepare", "dom", event && event.detail ? event.detail : null);
            });
            controller.form.addEventListener(TASKS.run.completionEvent, function (event) {
                markTaskCompleted("run", "dom", event && event.detail ? event.detail : null);
            });
        }

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
    globalThis.Roads = Roads;
}

/* ----------------------------------------------------------------------------
 * Batch Runner (Modernized)
 * Doc: controllers_js/README.md — Batch Runner Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var BatchRunner = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "batch:upload:started",
        "batch:upload:completed",
        "batch:upload:failed",
        "batch:template:validate-started",
        "batch:template:validate-completed",
        "batch:template:validate-failed",
        "batch:run-directives:updated",
        "batch:run-directives:update-failed",
        "batch:run:started",
        "batch:run:completed",
        "batch:run:failed",
        "batch:delete:started",
        "batch:delete:completed",
        "batch:delete:failed",
        "batch:sbs-upload:started",
        "batch:sbs-upload:completed",
        "batch:sbs-upload:failed",
        "job:started",
        "job:completed",
        "job:error"
    ];


    var SELECTORS = {
        form: "#batch_runner_form",
        statusDisplay: "#batch_runner_form #status",
        stacktrace: "#batch_runner_form #stacktrace",
        runstatePanel: "#batch_runner_form #batch_runstate",
        runstateInterval: "#batch_runner_form #batch_runstate_interval",
        rqJob: "#batch_runner_form #rq_job",
        container: "#batch-runner-root",
        resourceCard: "#batch-runner-resource-card",
        sbsCard: "#batch-runner-sbs-card",
        templateCard: "#batch-runner-template-card",
        runBatchButton: "#btn_run_batch",
        runBatchStatus: "#batch_run_message",
        deleteBatchButton: "#btn_delete_batch",
        deleteBatchStatus: "#batch_delete_message",
        runBatchHint: "#hint_run_batch",
        runBatchLock: "#run_batch_lock"
    };

    var DATA_ROLES = {
        uploadForm: '[data-role="upload-form"]',
        geojsonInput: '[data-role="geojson-input"]',
        uploadButton: '[data-role="upload-button"]',
        uploadStatus: '[data-role="upload-status"]',
        resourceEmpty: '[data-role="resource-empty"]',
        resourceDetails: '[data-role="resource-details"]',
        resourceMeta: '[data-role="resource-meta"]',
        resourceSchema: '[data-role="resource-schema"]',
        resourceSchemaBody: '[data-role="resource-schema-body"]',
        resourceSamples: '[data-role="resource-samples"]',
        resourceSamplesBody: '[data-role="resource-samples-body"]',
        sbsUploadForm: '[data-role="sbs-upload-form"]',
        sbsInput: '[data-role="sbs-input"]',
        sbsUploadButton: '[data-role="sbs-upload-button"]',
        sbsUploadStatus: '[data-role="sbs-upload-status"]',
        sbsEmpty: '[data-role="sbs-empty"]',
        sbsDetails: '[data-role="sbs-details"]',
        sbsMeta: '[data-role="sbs-meta"]',
        runDirectiveList: '[data-role="run-directive-list"]',
        runDirectiveStatus: '[data-role="run-directive-status"]',
        templateInput: '[data-role="template-input"]',
        validateButton: '[data-role="validate-button"]',
        templateStatus: '[data-role="template-status"]',
        validationSummary: '[data-role="validation-summary"]',
        validationSummaryList: '[data-role="validation-summary-list"]',
        validationIssues: '[data-role="validation-issues"]',
        validationIssuesList: '[data-role="validation-issues-list"]',
        validationPreview: '[data-role="validation-preview"]',
        previewBody: '[data-role="preview-body"]'
    };

    var ACTIONS = {
        upload: '[data-action="batch-upload"]',
        uploadSbs: '[data-action="batch-upload-sbs"]',
        validate: '[data-action="batch-validate"]',
        run: '[data-action="batch-run"]',
        deleteConfirm: '[data-action="batch-delete-confirm"]'
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.show !== "function") {
            throw new Error("BatchRunner controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("BatchRunner controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function" || typeof http.getJson !== "function") {
            throw new Error("BatchRunner controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("BatchRunner controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function escapeHtml(value) {
        if (value === undefined || value === null) {
            return "";
        }
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return null;
        }
        return {
            element: element,
            html: function (value) {
                element.innerHTML = value === undefined || value === null ? "" : String(value);
            },
            text: function (value) {
                element.textContent = value === undefined || value === null ? "" : String(value);
            },
            show: function () {
                element.hidden = false;
                if (element.style) {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
            }
        };
    }

    function formatBytes(bytes) {
        if (bytes === undefined || bytes === null || isNaN(bytes)) {
            return "—";
        }
        var size = Number(bytes);
        if (size < 1024) {
            return size + " B";
        }
        if (size < 1024 * 1024) {
            return (size / 1024).toFixed(1) + " KB";
        }
        return (size / (1024 * 1024)).toFixed(1) + " MB";
    }

    function formatCount(value) {
        if (value === undefined || value === null || isNaN(value)) {
            return "—";
        }
        var num = Number(value);
        if (!isFinite(num)) {
            return "—";
        }
        return Math.round(num).toLocaleString();
    }

    function formatBBox(bbox) {
        if (!bbox || bbox.length !== 4) {
            return "—";
        }
        return bbox
            .map(function (val) {
                var num = Number(val);
                return Number.isFinite(num) ? num.toFixed(4) : String(val);
            })
            .join(", ");
    }

    function formatTimestamp(timestamp) {
        if (!timestamp) {
            return "—";
        }
        try {
            var date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                return date.toLocaleString();
            }
        } catch (err) {
            // ignore
        }
        return timestamp || "—";
    }

    function applyDataState(target, state) {
        if (!target) {
            return;
        }
        if (state) {
            target.setAttribute("data-state", state);
        } else {
            target.removeAttribute("data-state");
        }
    }


    function resolveErrorMessage(error, fallback) {
        if (error && typeof error === "object") {
            if (error.error !== undefined) {
                if (typeof error.error === "string") {
                    return error.error;
                }
                if (error.error && typeof error.error.message === "string") {
                    return error.error.message;
                }
            }
            if (Array.isArray(error.errors) && error.errors.length) {
                return error.errors.map(function (entry) {
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
            if (typeof error.detail === "string" && error.detail) {
                return error.detail;
            }
            if (typeof error.message === "string" && error.message) {
                return error.message;
            }
        }
        return fallback;
    }

    function buildValidationMessage(summary) {
        if (!summary || typeof summary !== "object") {
            return [];
        }
        var items = [];
        if (summary.feature_count != null) {
            items.push("Features analyzed: " + summary.feature_count);
        }
        if (summary.unique_runids != null) {
            items.push("Unique run IDs: " + summary.unique_runids);
        }
        if (summary.duplicate_runids && summary.duplicate_runids.length) {
            items.push("Duplicates: " + summary.duplicate_runids.length);
        }
        if (summary.missing_values && summary.missing_values.length) {
            items.push("Missing values: " + summary.missing_values.length);
        }
        return items;
    }

    function createInstance() {
        var base = controlBase();
        var deps = ensureHelpers();
        var emitter = deps.events.useEventMap(EVENT_NAMES, deps.events.createEmitter());

        var controller = Object.assign(base, {
            dom: deps.dom,
            forms: deps.forms,
            http: deps.http,
            eventsModule: deps.events,
            emitter: emitter
        });

        controller.state = {
            enabled: false,
            batchName: "",
            snapshot: {},
            validation: null,
            geojsonLimitMb: null
        };
        controller.sitePrefix = "";
        controller.baseUrl = "";
        controller.uploadBaseUrl = "";
        controller.templateInitialised = false;
        controller.command_btn_id = "btn_run_batch";
        controller.statusStream = null;
        controller.statusSpinnerEl = null;
        controller.statusPanelEl = null;
        controller.stacktracePanelEl = null;
        controller._statusStreamRunId = null;

        controller._delegates = [];
        controller._runDirectivesSaving = false;
        controller._runDirectivesStatus = { message: "", state: "" };

        controller.runstate = {
            pollIntervalMs: 10000,
            refreshTimer: null,
            fetchInFlight: false,
            refreshPending: false,
            lastFetchStartedAt: 0,
            forceNextFetch: false,
            lastReport: null,
            abortController: null
        };

        controller.container = null;
        controller.resourceCard = null;
        controller.templateCard = null;

        controller.form = null;
        controller.statusDisplay = null;
        controller.stacktrace = null;
        controller.runstatePanel = null;
        controller.runstateInterval = null;
        controller.rq_job = null;
        controller.runBatchButton = null;
        controller.runBatchStatus = null;
        controller.deleteBatchButton = null;
        controller.deleteBatchStatus = null;
        controller.runBatchHint = null;
        controller.runBatchLock = null;

        controller.uploadForm = null;
        controller.uploadInput = null;
        controller.uploadButton = null;
        controller.uploadStatus = null;
        controller.resourceEmpty = null;
        controller.resourceDetails = null;
        controller.resourceMeta = null;
        controller.resourceSchema = null;
        controller.resourceSchemaBody = null;
        controller.resourceSamples = null;
        controller.resourceSamplesBody = null;
        controller.sbsCard = null;
        controller.sbsUploadForm = null;
        controller.sbsUploadInput = null;
        controller.sbsUploadButton = null;
        controller.sbsUploadStatus = null;
        controller.sbsEmpty = null;
        controller.sbsDetails = null;
        controller.sbsMeta = null;
        controller.runDirectiveList = null;
        controller.runDirectiveStatus = null;

        controller.templateInput = null;
        controller.validateButton = null;
        controller.templateStatus = null;
        controller.validationSummary = null;
        controller.validationSummaryList = null;
        controller.validationIssues = null;
        controller.validationIssuesList = null;
        controller.validationPreview = null;
        controller.previewBody = null;

        controller.init = init;
        controller.initCreate = init;
        controller.initManage = init;
        controller.destroy = destroy;
        controller.refreshRunstate = refreshRunstate;
        controller.runBatch = runBatch;
        controller.deleteBatch = deleteBatch;
        controller.uploadGeojson = uploadGeojson;
        controller.validateTemplate = validateTemplate;

        controller.render = render;
        controller.renderResource = renderResource;
        controller.renderValidation = renderValidation;

        controller._setRunBatchMessage = setRunBatchMessage;
        controller._setDeleteBatchMessage = setDeleteBatchMessage;
        controller._renderRunControls = renderRunControls;
        controller._setRunBatchBusy = setRunBatchBusy;
        controller._setDeleteBatchBusy = setDeleteBatchBusy;
        controller._setUploadBusy = setUploadBusy;
        controller._setUploadStatus = setUploadStatus;
        controller._setValidateBusy = setValidateBusy;
        controller._setRunDirectivesStatus = setRunDirectivesStatus;
        controller._renderRunDirectives = renderRunDirectives;
        controller._applyResourceVisibility = applyResourceVisibility;
        controller._setSbsUploadStatus = setSbsUploadStatus;
        controller._setSbsUploadBusy = setSbsUploadBusy;

        controller._handleRunDirectiveToggle = handleRunDirectiveToggle;
        controller._handleUpload = handleUpload;
        controller._handleSbsUpload = handleSbsUpload;
        controller._handleValidate = handleValidate;
        controller._handleDeleteBatch = handleDeleteBatch;

        controller._setRunDirectivesBusy = setRunDirectivesBusy;
        controller._submitRunDirectives = submitRunDirectives;

        controller._renderCoreStatus = renderCoreStatus;
        controller._renderRunstate = renderRunstate;
        controller._renderRunstateInterval = renderRunstateInterval;
        controller._cancelRunstateTimer = cancelRunstateTimer;
        controller._ensureRunstateFetchScheduled = ensureRunstateFetchScheduled;
        controller._performRunstateFetch = performRunstateFetch;

        controller._buildBaseUrl = buildBaseUrl;
        controller._apiUrl = apiUrl;
        controller._uploadApiUrl = uploadApiUrl;

        overrideControlBase(controller);

        return controller;

        function init(bootstrap) {
            bootstrap = bootstrap || {};
            controller.state = {
                enabled: Boolean(bootstrap.enabled),
                batchName: bootstrap.batchName || "",
                snapshot: bootstrap.state || {},
                validation: extractValidation(bootstrap.state || {}),
                geojsonLimitMb: bootstrap.geojsonLimitMb
            };
            controller.rqEngineToken = bootstrap.rqEngineToken || "";
            controller.sitePrefix = bootstrap.sitePrefix || "";
            controller.baseUrl = buildBaseUrl();
            controller.uploadBaseUrl = buildBaseUrl("/rq-engine/api");
            controller.templateInitialised = false;

            controller.form = deps.dom.qs(SELECTORS.form);
            controller.statusDisplay = deps.dom.qs(SELECTORS.statusDisplay);
            controller.stacktrace = deps.dom.qs(SELECTORS.stacktrace);
            controller.runstatePanel = deps.dom.qs(SELECTORS.runstatePanel);
            controller.runstateInterval = deps.dom.qs(SELECTORS.runstateInterval);
            controller.rq_job = deps.dom.qs(SELECTORS.rqJob);
            controller.statusPanelEl = controller.form
                ? controller.form.querySelector("[data-status-panel]")
                : null;
            controller.stacktracePanelEl = controller.form
                ? controller.form.querySelector("[data-stacktrace-panel]")
                : null;

            controller.container = deps.dom.qs(SELECTORS.container);
            controller.resourceCard = deps.dom.qs(SELECTORS.resourceCard);
            controller.templateCard = deps.dom.qs(SELECTORS.templateCard);

            controller.runBatchButton = deps.dom.qs(SELECTORS.runBatchButton);
            controller.runBatchStatus = deps.dom.qs(SELECTORS.runBatchStatus);
            controller.deleteBatchButton = deps.dom.qs(SELECTORS.deleteBatchButton);
            controller.deleteBatchStatus = deps.dom.qs(SELECTORS.deleteBatchStatus);
            controller.runBatchHint = deps.dom.qs(SELECTORS.runBatchHint);
            controller.runBatchLock = deps.dom.qs(SELECTORS.runBatchLock);
            controller.hint = createLegacyAdapter(controller.runBatchHint);
            controller.summaryElement = controller.runstatePanel;
            if (!controller.statusSpinnerEl && controller.form) {
                try {
                    controller.statusSpinnerEl = controller.form.querySelector("#braille");
                } catch (err) {
                    controller.statusSpinnerEl = null;
                }
            }

            if (!controller.container) {
                console.warn("BatchRunner container not found");
                return controller;
            }

            cacheElements();
            bindEvents();

            updateStatusStream(controller.state.batchName);

            hydrateJobId(bootstrap);

            renderCoreStatus();
            render();
            renderRunstateInterval();
            refreshRunstate({ force: true });
            controller.render_job_status(controller);

            return controller;
        }

        function updateStatusStream(runId) {
            var desiredRunId = runId || window.runid || window.runId || null;
            if (controller._statusStreamRunId === desiredRunId && controller.statusStream) {
                return;
            }
            controller.detach_status_stream(controller);
            controller.attach_status_stream(controller, {
                form: controller.form,
                channel: "batch",
                runId: desiredRunId,
                spinner: controller.statusSpinnerEl,
                logLimit: 400,
                stacktrace: {
                    element: controller.stacktracePanelEl,
                    body: controller.stacktrace,
                    allowHtml: true
                }
            });
            controller._statusStreamRunId = desiredRunId;
        }

        function destroy() {
            controller._delegates.forEach(function (unsubscribe) {
                try {
                    if (typeof unsubscribe === "function") {
                        unsubscribe();
                    }
                } catch (err) {
                    console.warn("Failed to remove BatchRunner delegate listener", err);
                }
            });
            controller._delegates = [];
            cancelRunstateTimer();
            controller.runstate.refreshPending = false;
            if (controller.runstate.abortController && typeof controller.runstate.abortController.abort === "function") {
                try {
                    controller.runstate.abortController.abort();
                } catch (err) {
                    console.warn("Failed to abort runstate request during destroy", err);
                }
            }
        }

        function cacheElements() {
            if (!controller.resourceCard) {
                return;
            }
            controller.uploadForm = controller.resourceCard.querySelector(DATA_ROLES.uploadForm);
            controller.uploadInput = controller.resourceCard.querySelector(DATA_ROLES.geojsonInput);
            controller.uploadButton = controller.resourceCard.querySelector(DATA_ROLES.uploadButton);
            controller.uploadStatus = controller.resourceCard.querySelector(DATA_ROLES.uploadStatus);
            controller.resourceEmpty = controller.resourceCard.querySelector(DATA_ROLES.resourceEmpty);
            controller.resourceDetails = controller.resourceCard.querySelector(DATA_ROLES.resourceDetails);
            controller.resourceMeta = controller.resourceCard.querySelector(DATA_ROLES.resourceMeta);
            controller.resourceSchema = controller.resourceCard.querySelector(DATA_ROLES.resourceSchema);
            controller.resourceSchemaBody = controller.resourceCard.querySelector(DATA_ROLES.resourceSchemaBody);
            controller.resourceSamples = controller.resourceCard.querySelector(DATA_ROLES.resourceSamples);
            controller.resourceSamplesBody = controller.resourceCard.querySelector(DATA_ROLES.resourceSamplesBody);
            controller.sbsCard = deps.dom.qs(SELECTORS.sbsCard);
            if (controller.sbsCard) {
                controller.sbsUploadForm = controller.sbsCard.querySelector(DATA_ROLES.sbsUploadForm);
                controller.sbsUploadInput = controller.sbsCard.querySelector(DATA_ROLES.sbsInput);
                controller.sbsUploadButton = controller.sbsCard.querySelector(DATA_ROLES.sbsUploadButton);
                controller.sbsUploadStatus = controller.sbsCard.querySelector(DATA_ROLES.sbsUploadStatus);
                controller.sbsEmpty = controller.sbsCard.querySelector(DATA_ROLES.sbsEmpty);
                controller.sbsDetails = controller.sbsCard.querySelector(DATA_ROLES.sbsDetails);
                controller.sbsMeta = controller.sbsCard.querySelector(DATA_ROLES.sbsMeta);
            }
            controller.runDirectiveList = controller.container.querySelector(DATA_ROLES.runDirectiveList);
            controller.runDirectiveStatus = controller.container.querySelector(DATA_ROLES.runDirectiveStatus);
            if (controller.runDirectiveList && controller.runDirectiveList.classList) {
                controller.runDirectiveList.classList.add("wc-stack");
            }

            if (controller.templateCard) {
                controller.templateInput = controller.templateCard.querySelector(DATA_ROLES.templateInput);
                controller.validateButton = controller.templateCard.querySelector(DATA_ROLES.validateButton);
                controller.templateStatus = controller.templateCard.querySelector(DATA_ROLES.templateStatus);
                controller.validationSummary = controller.templateCard.querySelector(DATA_ROLES.validationSummary);
                controller.validationSummaryList = controller.templateCard.querySelector(DATA_ROLES.validationSummaryList);
                controller.validationIssues = controller.templateCard.querySelector(DATA_ROLES.validationIssues);
                controller.validationIssuesList = controller.templateCard.querySelector(DATA_ROLES.validationIssuesList);
                controller.validationPreview = controller.templateCard.querySelector(DATA_ROLES.validationPreview);
                controller.previewBody = controller.templateCard.querySelector(DATA_ROLES.previewBody);
            }
        }

        function bindEvents() {
            var delegates = controller._delegates;

            if (
                controller.uploadForm &&
                controller.uploadForm.tagName &&
                controller.uploadForm.tagName.toLowerCase() === "form"
            ) {
                delegates.push(
                    deps.dom.delegate(controller.uploadForm, "submit", function (event) {
                        event.preventDefault();
                        handleUpload();
                    })
                );
            }

            delegates.push(
                deps.dom.delegate(controller.resourceCard || controller.container, "click", ACTIONS.upload, function (event) {
                    event.preventDefault();
                    handleUpload();
                })
            );

            if (
                controller.sbsUploadForm &&
                controller.sbsUploadForm.tagName &&
                controller.sbsUploadForm.tagName.toLowerCase() === "form"
            ) {
                delegates.push(
                    deps.dom.delegate(controller.sbsUploadForm, "submit", function (event) {
                        event.preventDefault();
                        handleSbsUpload();
                    })
                );
            }

            delegates.push(
                deps.dom.delegate(controller.sbsCard || controller.container, "click", ACTIONS.uploadSbs, function (event) {
                    event.preventDefault();
                    handleSbsUpload();
                })
            );

            delegates.push(
                deps.dom.delegate(controller.templateCard || controller.container, "click", ACTIONS.validate, function (event) {
                    event.preventDefault();
                    handleValidate();
                })
            );

            delegates.push(
                deps.dom.delegate(controller.container, "change", "[data-run-directive]", function (event) {
                    handleRunDirectiveToggle(event);
                })
            );

            if (controller.runBatchButton) {
                delegates.push(
                    deps.dom.delegate(controller.runBatchButton, "click", ACTIONS.run, function (event) {
                        event.preventDefault();
                        runBatch();
                    })
                );
            }

            delegates.push(
                deps.dom.delegate(controller.container, "click", ACTIONS.deleteConfirm, function (event) {
                    event.preventDefault();
                    handleDeleteBatch();
                })
            );
        }

        function buildBaseUrl(prefixOverride) {
            var prefix = "";
            if (typeof prefixOverride === "string" && prefixOverride.length) {
                prefix = prefixOverride;
            } else {
                prefix = controller.sitePrefix || "";
            }
            if (prefix && prefix.slice(-1) === "/") {
                prefix = prefix.slice(0, -1);
            }
            if (controller.state.batchName) {
                return prefix + "/batch/_/" + encodeURIComponent(controller.state.batchName);
            }
            var pathname = window.location.pathname || "";
            return pathname.replace(/\/$/, "");
        }

        function apiUrl(suffix) {
            var base = controller.baseUrl || "";
            if (!suffix) {
                return base;
            }
            if (suffix.charAt(0) !== "/") {
                suffix = "/" + suffix;
            }
            return base + suffix;
        }

        function uploadApiUrl(suffix) {
            var base = controller.uploadBaseUrl || "";
            if (!suffix) {
                return base;
            }
            if (suffix.charAt(0) !== "/") {
                suffix = "/" + suffix;
            }
            return base + suffix;
        }

        function buildAuthHeaders() {
            if (!controller.rqEngineToken) {
                return undefined;
            }
            return { Authorization: "Bearer " + controller.rqEngineToken };
        }

        function extractValidation(snapshot) {
            snapshot = snapshot || {};
            var metadata = snapshot.metadata || {};
            return metadata.template_validation || null;
        }

        function renderCoreStatus() {
            if (!controller.container) {
                return;
            }
            var snapshot = controller.state.snapshot || {};
            setText(controller.container.querySelector('[data-role="enabled-flag"]'), controller.state.enabled ? "True" : "False");
            setText(controller.container.querySelector('[data-role="batch-name"]'), controller.state.batchName || "—");
            setText(controller.container.querySelector('[data-role="manifest-version"]'), snapshot.state_version || "—");
            setText(controller.container.querySelector('[data-role="created-by"]'), snapshot.created_by || "—");
            setText(controller.container.querySelector('[data-role="manifest-json"]'), JSON.stringify(snapshot, null, 2));
        }

        function render() {
            renderResource();
            renderSbsResource();
            renderValidation();
            renderRunDirectives();
            renderRunControls();
        }

        function renderResource() {
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;

            if (!controller.resourceCard) {
                return;
            }

            if (!resource) {
                deps.dom.show(controller.resourceEmpty);
                deps.dom.hide(controller.resourceDetails);
                deps.dom.hide(controller.resourceSchema);
                deps.dom.hide(controller.resourceSamples);
                return;
            }

            deps.dom.hide(controller.resourceEmpty);
            deps.dom.show(controller.resourceDetails);

            var metaRows = [];
            metaRows.push(renderMetaRow("Filename", resource.filename || resource.original_filename || "—"));
            if (resource.uploaded_by) {
                metaRows.push(renderMetaRow("Uploaded by", resource.uploaded_by));
            }
            if (resource.uploaded_at) {
                metaRows.push(renderMetaRow("Uploaded at", formatTimestamp(resource.uploaded_at)));
            }
            if (resource.size_bytes != null) {
                metaRows.push(renderMetaRow("Size", formatBytes(resource.size_bytes)));
            }
            if (resource.feature_count != null) {
                metaRows.push(renderMetaRow("Features", resource.feature_count));
            }
            if (resource.bbox) {
                metaRows.push(renderMetaRow("Bounding Box", formatBBox(resource.bbox)));
            }
            if (resource.epsg) {
                metaRows.push(
                    renderMetaRow(
                        "EPSG",
                        resource.epsg + (resource.epsg_source ? " (" + resource.epsg_source + ")" : "")
                    )
                );
            }
            if (resource.checksum) {
                metaRows.push(renderMetaRow("Checksum", resource.checksum));
            }
            if (resource.relative_path) {
                metaRows.push(renderMetaRow("Path", resource.relative_path));
            }

            if (controller.resourceMeta) {
                controller.resourceMeta.innerHTML = metaRows.join("");
            }

            if (Array.isArray(resource.attribute_schema) && controller.resourceSchemaBody) {
                deps.dom.show(controller.resourceSchema);
                controller.resourceSchemaBody.innerHTML = resource.attribute_schema
                    .map(function (entry) {
                        var name = escapeHtml(entry.name || "—");
                        var type = escapeHtml(entry.type || entry.type_hint || "—");
                        return "<tr><td>" + name + "</td><td>" + type + "</td></tr>";
                    })
                    .join("");
            } else {
                deps.dom.hide(controller.resourceSchema);
            }

            if (Array.isArray(resource.sample_properties) && controller.resourceSamplesBody) {
                deps.dom.show(controller.resourceSamples);
                controller.resourceSamplesBody.innerHTML = resource.sample_properties
                    .map(function (entry, index) {
                        var props = escapeHtml(JSON.stringify(entry.properties || entry, null, 2));
                        var idx = escapeHtml(String(entry.index != null ? entry.index : index));
                        var featureId = escapeHtml(String(entry.feature_id || entry.id || "—"));
                        return (
                            "<tr><td>" +
                            idx +
                            "</td><td><code>" +
                            featureId +
                            '</code></td><td><pre class="wc-pre">' +
                            props +
                            "</pre></td></tr>"
                        );
                    })
                    .join("");
            } else {
                deps.dom.hide(controller.resourceSamples);
            }
        }

        function renderSbsResource() {
            if (!controller.sbsCard) {
                return;
            }
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.sbs_map;
            if (!controller.sbsEmpty || !controller.sbsDetails) {
                return;
            }

            if (!resource) {
                deps.dom.show(controller.sbsEmpty);
                deps.dom.hide(controller.sbsDetails);
                return;
            }

            deps.dom.hide(controller.sbsEmpty);
            deps.dom.show(controller.sbsDetails);

            var metaRows = [];
            metaRows.push(renderMetaRow("Filename", resource.filename || resource.original_filename || "—"));
            if (resource.uploaded_by) {
                metaRows.push(renderMetaRow("Uploaded by", resource.uploaded_by));
            }
            if (resource.uploaded_at) {
                metaRows.push(renderMetaRow("Uploaded at", formatTimestamp(resource.uploaded_at)));
            }
            if (resource.size_bytes != null) {
                metaRows.push(renderMetaRow("Size", formatBytes(resource.size_bytes)));
            }
            if (resource.relative_path) {
                metaRows.push(renderMetaRow("Path", resource.relative_path));
            }
            if (resource.sanity_message) {
                metaRows.push(renderMetaRow("Validation", resource.sanity_message));
            }
            if (resource.burn_class_counts && typeof resource.burn_class_counts === "object") {
                var burnCounts = resource.burn_class_counts;
                [
                    { key: "No Burn", label: "Pixels: No Burn" },
                    { key: "Low Severity Burn", label: "Pixels: Low Severity" },
                    { key: "Moderate Severity Burn", label: "Pixels: Moderate Severity" },
                    { key: "High Severity Burn", label: "Pixels: High Severity" },
                    { key: "No Data", label: "Pixels: No Data" }
                ].forEach(function (entry) {
                    var count = burnCounts[entry.key];
                    if (count === undefined || count === null) {
                        count = 0;
                    }
                    metaRows.push(renderMetaRow(entry.label, formatCount(count)));
                });
            }
            if (resource.replaced) {
                metaRows.push(renderMetaRow("Replaced existing file", resource.replaced ? "Yes" : "No"));
            }
            if (resource.missing) {
                metaRows.push(renderMetaRow("Status", "File missing on disk"));
            }

            if (controller.sbsMeta) {
                controller.sbsMeta.innerHTML = metaRows.join("");
            }
        }

        function renderValidation() {
            var validation = controller.state.validation;
            if (!controller.templateCard) {
                return;
            }

            if (!controller.templateInitialised && controller.templateInput && controller.state.snapshot) {
                var storedTemplate = controller.state.snapshot.runid_template || "";
                controller.templateInput.value = storedTemplate || "";
                controller.templateInitialised = true;
            }

            if (!validation) {
                setText(controller.templateStatus, "");
                applyDataState(controller.templateStatus, "");
                deps.dom.hide(controller.validationSummary);
                deps.dom.hide(controller.validationIssues);
                deps.dom.hide(controller.validationPreview);
                return;
            }

            var status = validation.status || "unknown";
            var summary = validation.summary || {};
            var issues = validation.errors || [];
            var preview = validation.preview || [];

            if ((status === "unknown" || status === undefined || status === null) && summary.is_valid === true) {
                status = "ok";
                validation.status = "ok";
            }

            setText(
                controller.templateStatus,
                status === "ok" ? "Template is valid." : "Template requires attention."
            );
            applyDataState(controller.templateStatus, status === "ok" ? "success" : "warning");

            if (controller.validationSummary && controller.validationSummaryList) {
                var items = buildValidationMessage(summary).map(function (item) {
                    return "<li>" + escapeHtml(item) + "</li>";
                });
                controller.validationSummaryList.innerHTML = items.join("");
                deps.dom.toggle(controller.validationSummary, items.length > 0);
            }

            if (controller.validationIssues && controller.validationIssuesList) {
                if (issues.length) {
                    controller.validationIssuesList.innerHTML = issues
                        .slice(0, 10)
                        .map(function (item) {
                            return escapeHtml(item);
                        })
                        .join("<br>");
                    deps.dom.show(controller.validationIssues);
                } else {
                    controller.validationIssuesList.innerHTML = "";
                    deps.dom.hide(controller.validationIssues);
                }
            }

            if (controller.validationPreview && controller.previewBody) {
                if (Array.isArray(preview) && preview.length) {
                    controller.previewBody.innerHTML = preview
                        .slice(0, 25)
                        .map(function (entry) {
                            var rowIndex = escapeHtml(
                                entry.index != null
                                    ? entry.index
                                    : entry.one_based_index != null
                                    ? entry.one_based_index - 1
                                    : "—"
                            );
                            var featureId = escapeHtml(entry.feature_id || entry.featureId || "—");
                            var runid = escapeHtml(entry.runid || entry.runId || entry.run_id || "—");
                            var error = escapeHtml(entry.error || "");
                            return (
                                "<tr><td>" +
                                rowIndex +
                                "</td><td><code>" +
                                featureId +
                                "</code></td><td><code>" +
                                runid +
                                "</code></td><td>" +
                                error +
                                "</td></tr>"
                            );
                        })
                        .join("");
                    deps.dom.show(controller.validationPreview);
                } else {
                    controller.previewBody.innerHTML = "";
                    deps.dom.hide(controller.validationPreview);
                }
            }
        }

        function renderRunDirectives() {
            if (!controller.runDirectiveList) {
                return;
            }

            var snapshot = controller.state.snapshot || {};
            var directives = snapshot.run_directives || [];

            if (!Array.isArray(directives) || directives.length === 0) {
                controller.runDirectiveList.innerHTML =
                    '<div class="wc-text-muted">No batch tasks configured.</div>';
                setRunDirectivesStatus("No batch tasks configured.", "info");
                return;
            }

            var html = directives
                .map(function (directive, index) {
                    if (!directive || typeof directive !== "object") {
                        return "";
                    }
                    var slug = directive.slug || "directive-" + index;
                    var label = directive.label || slug;
                    var controlId = "batch-runner-directive-" + slug;
                    var checked = directive.enabled ? " checked" : "";
                    var disabled = !controller.state.enabled || controller._runDirectivesSaving ? " disabled" : "";
                    return (
                        '<label class="wc-choice wc-choice--checkbox">' +
                        '<input type="checkbox" id="' +
                        controlId +
                        '" data-run-directive="' +
                        escapeHtml(slug) +
                        '"' +
                        checked +
                        disabled +
                        ">" +
                        '<span class="wc-choice__body"><span class="wc-choice__label">' +
                        escapeHtml(label) +
                        "</span></span>" +
                        "</label>"
                    );
                })
                .join("");

            controller.runDirectiveList.innerHTML = html;
            syncRunDirectiveDisabledState();

            if (controller._runDirectivesStatus && controller._runDirectivesStatus.message) {
                applyStoredRunDirectiveStatus();
            } else if (!controller.state.enabled) {
                setRunDirectivesStatus("Batch runner is disabled; tasks cannot be edited.", "warning");
            }
        }

        function renderRunControls(options) {
            options = options || {};
            var preserveMessage = options.preserveMessage === true;
            var preserveDeleteMessage = options.preserveDeleteMessage === true;

            if (!controller.runBatchButton && !controller.deleteBatchButton) {
                return;
            }

            var jobLocked = controller.should_disable_command_button(controller);
            controller.update_command_button_state(controller);
            var enabled = Boolean(controller.state.enabled);

            if (controller.runBatchLock) {
                if (jobLocked) {
                    deps.dom.show(controller.runBatchLock);
                } else {
                    deps.dom.hide(controller.runBatchLock);
                }
            }

            if (jobLocked) {
                if (controller.runBatchButton) {
                    controller.runBatchButton.disabled = true;
                }
                if (controller.deleteBatchButton) {
                    controller.deleteBatchButton.disabled = true;
                }
                setRunBatchMessage("Batch run in progress…", "info");
                if (!preserveDeleteMessage) {
                    setDeleteBatchMessage("", "");
                }
                return;
            }

            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;
            var templateState =
                controller.state.validation || (snapshot.metadata && snapshot.metadata.template_validation) || null;
            var templateStatus = templateState && (templateState.status || "ok");
            var summary = templateState && templateState.summary;
            var templateIsValid = Boolean(templateState && summary && summary.is_valid && templateStatus === "ok");

            var allowRun = enabled && Boolean(resource) && templateIsValid;
            var message = "";
            var state = "info";

            if (!enabled) {
                message = "Batch runner is disabled.";
                state = "warning";
            } else if (!resource) {
                message = "Upload a watershed GeoJSON before running.";
            } else if (!templateIsValid) {
                message = "Validate and resolve template issues before running.";
                state = "warning";
            } else {
                message = "Ready to run batch.";
                state = "success";
            }

            if (controller.runBatchButton) {
                controller.runBatchButton.disabled = !allowRun;
            }

            if (controller.deleteBatchButton) {
                controller.deleteBatchButton.disabled = !enabled;
            }

            if (!preserveMessage || !allowRun) {
                setRunBatchMessage(message, state);
            }
        }

        function syncRunDirectiveDisabledState() {
            if (!controller.runDirectiveList) {
                return;
            }
            var shouldDisable = controller._runDirectivesSaving || !controller.state.enabled;
            var inputs = controller.runDirectiveList.querySelectorAll("input[data-run-directive]");
            inputs.forEach(function (input) {
                input.disabled = shouldDisable;
            });
        }

        function setRunDirectivesBusy(busy) {
            controller._runDirectivesSaving = busy === true;
            syncRunDirectiveDisabledState();
        }

        function setRunBatchBusy(busy, message, state) {
            if (controller.runBatchButton && busy) {
                controller.runBatchButton.disabled = true;
            }
            if (controller.deleteBatchButton && busy) {
                controller.deleteBatchButton.disabled = true;
            }
            if (controller.runBatchLock) {
                if (busy) {
                    deps.dom.show(controller.runBatchLock);
                } else if (!controller.should_disable_command_button(controller)) {
                    deps.dom.hide(controller.runBatchLock);
                }
            }
            if (message != null) {
                setRunBatchMessage(message, state || "info");
            }
            if (!busy) {
                renderRunControls({ preserveMessage: true, preserveDeleteMessage: true });
            }
        }

        function setDeleteBatchBusy(busy, message, state) {
            if (controller.deleteBatchButton) {
                controller.deleteBatchButton.disabled = busy || !controller.state.enabled;
            }
            if (controller.runBatchButton && busy) {
                controller.runBatchButton.disabled = true;
            }
            if (message != null) {
                setDeleteBatchMessage(message, state || "info");
            }
            if (!busy) {
                renderRunControls({ preserveMessage: true, preserveDeleteMessage: true });
            }
        }

        function setRunDirectivesStatus(message, state) {
            controller._runDirectivesStatus = {
                message: message || "",
                state: state || ""
            };
            if (!controller.runDirectiveStatus) {
                return;
            }
            applyDataState(controller.runDirectiveStatus, state);
            setText(controller.runDirectiveStatus, message || "");
        }

        function applyStoredRunDirectiveStatus() {
            if (!controller.runDirectiveStatus) {
                return;
            }
            var status = controller._runDirectivesStatus || {};
            applyDataState(controller.runDirectiveStatus, status.state);
            setText(controller.runDirectiveStatus, status.message || "");
        }

        function setRunBatchMessage(message, state) {
            if (!controller.runBatchStatus) {
                return;
            }
            applyDataState(controller.runBatchStatus, state);
            setText(controller.runBatchStatus, message || "");
        }

        function setDeleteBatchMessage(message, state) {
            if (!controller.deleteBatchStatus) {
                return;
            }
            applyDataState(controller.deleteBatchStatus, state);
            setText(controller.deleteBatchStatus, message || "");
        }

        function setUploadBusy(busy, message) {
            if (controller.uploadButton) {
                controller.uploadButton.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setUploadStatus(message, busy ? "info" : "");
            }
        }

        function setValidateBusy(busy, message) {
            if (controller.validateButton) {
                controller.validateButton.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setText(controller.templateStatus, message);
                applyDataState(controller.templateStatus, busy ? "info" : "");
            }
        }

        function setUploadStatus(message, state) {
            if (!controller.uploadStatus) {
                return;
            }
            applyDataState(controller.uploadStatus, state);
            setText(controller.uploadStatus, message || "");
        }

        function setSbsUploadBusy(busy, message) {
            if (controller.sbsUploadButton) {
                controller.sbsUploadButton.disabled = busy || !controller.state.enabled;
            }
            if (controller.sbsUploadInput) {
                controller.sbsUploadInput.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setSbsUploadStatus(message, busy ? "info" : "");
            }
        }

        function setSbsUploadStatus(message, state) {
            if (!controller.sbsUploadStatus) {
                return;
            }
            applyDataState(controller.sbsUploadStatus, state);
            setText(controller.sbsUploadStatus, message || "");
        }

        function collectRunDirectiveValues() {
            var result = {};
            if (!controller.runDirectiveList) {
                return result;
            }
            var inputs = controller.runDirectiveList.querySelectorAll("input[data-run-directive]");
            inputs.forEach(function (input) {
                var slug = input.getAttribute("data-run-directive");
                if (!slug) {
                    return;
                }
                result[String(slug)] = Boolean(input.checked);
            });
            return result;
        }

        function submitRunDirectives(values) {
            if (!values) {
                return;
            }
            setRunDirectivesBusy(true);
            setRunDirectivesStatus("Saving batch task selection…", "info");

            controller.http
                .postJson(apiUrl("run-directives"), { run_directives: values })
                .then(function (response) {
                    var payload = response.body || {};
                    if (payload.error || payload.errors) {
                        var errorMsg = resolveErrorMessage(payload, "Failed to update batch tasks.");
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot;
                    } else if (Array.isArray(payload.run_directives)) {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.run_directives = payload.run_directives;
                        controller.state.snapshot = snapshot;
                    }

                    setRunDirectivesStatus("Batch tasks updated.", "success");
                    controller.emitter.emit("batch:run-directives:updated", {
                        batchName: controller.state.batchName,
                        directives: controller.state.snapshot.run_directives || []
                    });
                    renderRunDirectives();
                    renderRunControls();
                })
                .catch(function (error) {
                    var message = resolveErrorMessage(error, "Failed to update batch tasks.");
                    setRunDirectivesStatus(message, "critical");
                    controller.emitter.emit("batch:run-directives:update-failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                    renderRunDirectives();
                    renderRunControls();
                })
                .finally(function () {
                    setRunDirectivesBusy(false);
                });
        }

        function handleRunDirectiveToggle(evt) {
            if (controller._runDirectivesSaving) {
                if (evt && typeof evt.preventDefault === "function") {
                    evt.preventDefault();
                }
                return;
            }

            if (!controller.state.enabled) {
                if (evt && typeof evt.preventDefault === "function") {
                    evt.preventDefault();
                }
                renderRunDirectives();
                return;
            }

            var values = collectRunDirectiveValues();
            submitRunDirectives(values);
        }

        function renderRunstate(payload) {
            var panel = controller.runstatePanel;
            if (!panel) {
                return;
            }
            var report = "";
            var message = "";
            if (payload && typeof payload === "object") {
                report = payload.report || "";
                message = payload.message || "";
            }
            if (report) {
                renderRunstateGrid(report);
                controller.runstate.lastReport = report;
                return;
            }
            if (message) {
                panel.textContent = message;
                return;
            }
            if (controller.runstate.lastReport) {
                renderRunstateGrid(controller.runstate.lastReport);
                return;
            }
            panel.textContent = "No batch runs are available yet.";
        }

        function renderRunstateGrid(report) {
            var panel = controller.runstatePanel;
            if (!panel) {
                return;
            }
            var lines = String(report || "")
                .split("\n")
                .filter(function (line) {
                    return line !== "";
                });

            panel.textContent = "";

            if (!lines.length) {
                panel.textContent = "No batch runs are available yet.";
                return;
            }

            lines.forEach(function (line) {
                var cell = document.createElement("span");
                cell.className = "batch-runner-runstate-cell";
                cell.textContent = line;
                panel.appendChild(cell);
            });
        }

        function formatRunstateInterval(ms) {
            if (ms === undefined || ms === null) {
                return "";
            }
            var seconds = Number(ms) / 1000;
            if (!isFinite(seconds) || seconds <= 0) {
                return "";
            }
            var label = Number.isInteger(seconds)
                ? String(seconds)
                : seconds.toFixed(1);
            return "Updates every " + label + "s. Jobs are queued LPT (largest area first).";
        }

        function renderRunstateInterval() {
            if (!controller.runstateInterval) {
                return;
            }
            var text = formatRunstateInterval(controller.runstate.pollIntervalMs);
            setText(controller.runstateInterval, text);
        }

        function cancelRunstateTimer() {
            if (controller.runstate.refreshTimer) {
                clearTimeout(controller.runstate.refreshTimer);
                controller.runstate.refreshTimer = null;
            }
        }

        function ensureRunstateFetchScheduled() {
            if (controller.runstate.fetchInFlight) {
                return;
            }

            var now = Date.now();
            var interval = controller.runstate.pollIntervalMs || 0;
            var lastStarted = controller.runstate.lastFetchStartedAt || 0;
            var elapsed = now - lastStarted;
            var forceNext = controller.runstate.forceNextFetch === true;

            if (!forceNext && interval > 0 && elapsed < interval) {
                if (controller.runstate.refreshTimer) {
                    return;
                }
                controller.runstate.refreshTimer = setTimeout(function () {
                    controller.runstate.refreshTimer = null;
                    performRunstateFetch();
                }, interval - elapsed);
                return;
            }

            controller.runstate.forceNextFetch = false;
            performRunstateFetch();
        }

        function performRunstateFetch() {
            if (!controller.runstatePanel) {
                return;
            }
            if (!controller.state.batchName) {
                return;
            }
            if (controller.runstate.fetchInFlight) {
                return;
            }
            if (!controller.http || typeof controller.http.getJson !== "function") {
                console.warn("BatchRunner requires WCHttp.getJson for runstate polling.");
                return;
            }

            cancelRunstateTimer();
            controller.runstate.forceNextFetch = false;
            controller.runstate.fetchInFlight = true;
            controller.runstate.lastFetchStartedAt = Date.now();

            if (typeof AbortController !== "undefined") {
                if (controller.runstate.abortController) {
                    controller.runstate.abortController.abort();
                }
                controller.runstate.abortController = new AbortController();
            }

            var signal = controller.runstate.abortController
                ? controller.runstate.abortController.signal
                : undefined;

            controller.http
                .getJson(apiUrl("runstate"), { params: { _: Date.now() }, signal: signal })
                .then(function (payload) {
                    renderRunstate(payload);
                })
                .catch(function (error) {
                    if (
                        error &&
                        error.name === "HttpError" &&
                        error.cause &&
                        error.cause.name === "AbortError"
                    ) {
                        return;
                    }
                    var message = resolveErrorMessage(error, "Unable to refresh batch progress.");
                    console.warn("Unable to refresh batch runstate:", error);
                    if (!controller.runstate.lastReport && controller.runstatePanel) {
                        controller.runstatePanel.textContent = message;
                    }
                })
                .finally(function () {
                    if (controller.runstate.abortController) {
                        controller.runstate.abortController = null;
                    }
                    controller.runstate.fetchInFlight = false;
                    if (controller.runstate.refreshPending) {
                        ensureRunstateFetchScheduled();
                    }
                });
        }

        function refreshRunstate(options) {
            options = options || {};
            if (!controller.runstatePanel) {
                return;
            }

            if (options.force === true) {
                controller.runstate.forceNextFetch = true;
                controller.runstate.refreshPending = true;
                cancelRunstateTimer();
                if (!controller.runstate.fetchInFlight) {
                    performRunstateFetch();
                }
                return;
            }

            controller.runstate.refreshPending = true;
            ensureRunstateFetchScheduled();
        }

        function hydrateJobId(bootstrap) {
            var ctx = bootstrap || {};
            var helper = window.WCControllerBootstrap || null;
            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_batch_rq")
                : null;

            if (!jobId && ctx.job_id) {
                jobId = ctx.job_id;
            }

            if (!jobId) {
                var jobIds = ctx.jobIds || ctx.jobs;
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_batch_rq")) {
                    var value = jobIds.run_batch_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (!jobId) {
                var snapshot = ctx.state || {};
                var metadata = snapshot && typeof snapshot === "object" ? snapshot.metadata || {} : {};
                if (metadata && metadata.rq_job_ids && metadata.rq_job_ids.run_batch_rq) {
                    jobId = String(metadata.rq_job_ids.run_batch_rq);
                } else if (metadata && metadata.job_ids && metadata.job_ids.run_batch_rq) {
                    jobId = String(metadata.job_ids.run_batch_rq);
                }
            }

            if (jobId) {
                controller.poll_completion_event = "BATCH_RUN_COMPLETED";
            }

            if (typeof controller.set_rq_job_id === "function") {
                controller.set_rq_job_id(controller, jobId);
            }
        }

        function applyResourceVisibility() {
            var snapshot = controller.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;

            if (!controller.resourceCard) {
                return;
            }

            if (!resource) {
                deps.dom.show(controller.resourceEmpty);
                deps.dom.hide(controller.resourceDetails);
                deps.dom.hide(controller.resourceSchema);
                deps.dom.hide(controller.resourceSamples);
            } else {
                deps.dom.hide(controller.resourceEmpty);
                deps.dom.show(controller.resourceDetails);
            }
        }

        function renderMetaRow(label, value) {
            return (
                '<div class="wc-summary-pane__item">' +
                '<dt class="wc-summary-pane__term">' +
                escapeHtml(label) +
                "</dt>" +
                '<dd class="wc-summary-pane__definition">' +
                escapeHtml(value) +
                "</dd>" +
                "</div>"
            );
        }

        function setText(node, value) {
            if (!node) {
                return;
            }
            node.textContent = value === undefined || value === null ? "" : String(value);
        }

        function handleUpload(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            if (!controller.state.enabled) {
                return;
            }
            var fileInput = controller.uploadInput;
            if (!fileInput || !fileInput.files || !fileInput.files.length) {
                setUploadStatus("Choose a GeoJSON file before uploading.", "warning");
                return;
            }

            var formData = new FormData();
            formData.append("geojson_file", fileInput.files[0]);

            setUploadBusy(true, "Uploading GeoJSON…");
            controller.emitter.emit("batch:upload:started", {
                batchName: controller.state.batchName,
                filename: fileInput.files[0].name,
                size: fileInput.files[0].size
            });

            controller.http
                .request(uploadApiUrl("upload-geojson"), {
                    method: "POST",
                    body: formData,
                    headers: buildAuthHeaders()
                })
                .then(function (response) {
                    var payload = response.body || {};
                    if (payload.error || payload.errors) {
                        var errorMsg = resolveErrorMessage(payload, "Upload failed.");
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot || {};
                        controller.state.validation = extractValidation(controller.state.snapshot);
                    } else {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.resources = snapshot.resources || {};
                        var resource = payload.resource;
                        if (!resource && payload.resource_metadata) {
                            resource = Object.assign({}, payload.resource_metadata);
                            var analysis = payload.template_validation || {};
                            if (analysis && typeof analysis === "object") {
                                if (analysis.feature_count != null) {
                                    resource.feature_count = analysis.feature_count;
                                }
                                if (analysis.bbox) {
                                    resource.bbox = analysis.bbox;
                                }
                                if (analysis.epsg) {
                                    resource.epsg = analysis.epsg;
                                }
                                if (analysis.epsg_source) {
                                    resource.epsg_source = analysis.epsg_source;
                                }
                                if (analysis.checksum) {
                                    resource.checksum = analysis.checksum;
                                }
                                if (analysis.size_bytes != null) {
                                    resource.size_bytes = analysis.size_bytes;
                                }
                                if (analysis.attribute_schema) {
                                    resource.attribute_schema = analysis.attribute_schema;
                                }
                                if (Array.isArray(analysis.properties)) {
                                    resource.properties = analysis.properties;
                                }
                                if (Array.isArray(analysis.sample_properties)) {
                                    resource.sample_properties = analysis.sample_properties;
                                }
                            }
                        }
                        if (resource) {
                            snapshot.resources.watershed_geojson = resource;
                        }
                        snapshot.metadata = snapshot.metadata || {};
                        if (payload.template_validation && payload.template_validation.summary) {
                            snapshot.metadata.template_validation = payload.template_validation;
                            controller.state.validation = payload.template_validation;
                        } else if (snapshot.metadata.template_validation) {
                            snapshot.metadata.template_validation.status = "stale";
                            controller.state.validation = snapshot.metadata.template_validation;
                        } else {
                            controller.state.validation = null;
                        }
                        controller.state.snapshot = snapshot;
                    }

                    setUploadStatus(payload.message || "Upload complete.", "success");
                    if (fileInput) {
                        fileInput.value = "";
                    }
                    controller.templateInitialised = false;
                    applyResourceVisibility();
                    render();

                    controller.emitter.emit("batch:upload:completed", {
                        success: true,
                        batchName: controller.state.batchName,
                        snapshot: controller.state.snapshot
                    });
                })
                .catch(function (error) {
                    var message = resolveErrorMessage(error, "Upload failed.");
                    setUploadStatus(message, "critical");
                    controller.emitter.emit("batch:upload:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setUploadBusy(false);
                });
        }

        function handleSbsUpload(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            if (!controller.state.enabled) {
                return;
            }
            var fileInput = controller.sbsUploadInput;
            if (!fileInput || !fileInput.files || !fileInput.files.length) {
                setSbsUploadStatus("Choose an SBS map before uploading.", "warning");
                return;
            }

            var formData = new FormData();
            formData.append("sbs_map", fileInput.files[0]);

            setSbsUploadBusy(true, "Uploading SBS map…");
            controller.emitter.emit("batch:sbs-upload:started", {
                batchName: controller.state.batchName,
                filename: fileInput.files[0].name,
                size: fileInput.files[0].size
            });

            controller.http
                .request(uploadApiUrl("upload-sbs-map"), {
                    method: "POST",
                    body: formData,
                    headers: buildAuthHeaders()
                })
                .then(function (response) {
                    var payload = response.body || {};
                    if (payload.error || payload.errors) {
                        var errorMsg = resolveErrorMessage(payload, "Upload failed.");
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot || {};
                    } else {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.resources = snapshot.resources || {};
                        if (payload.resource) {
                            snapshot.resources.sbs_map = payload.resource;
                        }
                        controller.state.snapshot = snapshot;
                    }

                    setSbsUploadStatus(payload.message || "Upload complete.", "success");
                    if (fileInput) {
                        fileInput.value = "";
                    }
                    renderSbsResource();

                    controller.emitter.emit("batch:sbs-upload:completed", {
                        batchName: controller.state.batchName,
                        snapshot: controller.state.snapshot
                    });
                })
                .catch(function (error) {
                    var message = resolveErrorMessage(error, "Upload failed.");
                    setSbsUploadStatus(message, "critical");
                    controller.emitter.emit("batch:sbs-upload:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setSbsUploadBusy(false);
                });
        }

        function handleValidate(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            if (!controller.state.enabled) {
                return;
            }
            var template = (controller.templateInput && controller.templateInput.value || "").trim();
            if (!template) {
                setText(controller.templateStatus, "Enter a template before validating.");
                applyDataState(controller.templateStatus, "warning");
                return;
            }

            setValidateBusy(true, "Validating template…");
            controller.emitter.emit("batch:template:validate-started", {
                batchName: controller.state.batchName,
                template: template
            });

            controller.http
                .postJson(apiUrl("validate-template"), { template: template })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.validation) {
                        var errorMsg = resolveErrorMessage(payload, "Template validation failed.");
                        throw new Error(errorMsg);
                    }

                    controller.state.validation = payload.validation;
                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot || {};
                    } else {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.metadata = snapshot.metadata || {};
                        snapshot.metadata.template_validation = payload.stored;
                        snapshot.runid_template = template;
                        controller.state.snapshot = snapshot;
                    }
                    controller.templateInitialised = false;
                    render();

                    controller.emitter.emit("batch:template:validate-completed", {
                        batchName: controller.state.batchName,
                        validation: payload.validation
                    });
                })
                .catch(function (error) {
                    var message = resolveErrorMessage(error, "Template validation failed.");
                    setText(controller.templateStatus, message);
                    applyDataState(controller.templateStatus, "critical");
                    controller.emitter.emit("batch:template:validate-failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setValidateBusy(false);
                });
        }

        function handleDeleteBatch(event) {
            if (event && typeof event.preventDefault === "function") {
                event.preventDefault();
            }
            deleteBatch();
        }

        function runBatch() {
            if (!controller.state.enabled) {
                setRunBatchMessage("Batch runner is disabled.", "warning");
                return;
            }

            if (controller.should_disable_command_button(controller)) {
                return;
            }

            if (typeof controller.reset_panel_state === "function") {
                controller.reset_panel_state(controller);
            }
            cancelRunstateTimer();

            setRunBatchBusy(true, "Submitting batch run…", "info");

            controller.connect_status_stream(controller);

            controller.http
                .postJson(
                    "/rq-engine/api/batch/_/" + encodeURIComponent(controller.state.batchName) + "/run-batch",
                    {},
                    controller.rqEngineToken
                        ? { headers: { Authorization: "Bearer " + controller.rqEngineToken } }
                        : undefined
                )
                .then(function (response) {
                    var payload = response.body || {};
                    if (payload.error || payload.errors) {
                        var errorMsg = resolveErrorMessage(payload, "Failed to submit batch run.");
                        throw new Error(errorMsg);
                    }

                    if (payload.job_id) {
                        controller.poll_completion_event = "BATCH_RUN_COMPLETED";
                        controller.set_rq_job_id(controller, payload.job_id);
                    } else {
                        controller.update_command_button_state(controller);
                    }

                    var successMessage = payload.message || "Batch run submitted.";
                    setRunBatchMessage(successMessage, "success");

                    controller.emitter.emit("batch:run:started", {
                        batchName: controller.state.batchName,
                        job_id: payload.job_id || null
                    });
                    controller.emitter.emit("job:started", {
                        batchName: controller.state.batchName,
                        job_id: payload.job_id || null
                    });
                    refreshRunstate({ force: true });
                })
                .catch(function (error) {
                    var message = resolveErrorMessage(error, "Failed to submit batch run.");
                    setRunBatchMessage(message, "critical");
                    controller.disconnect_status_stream(controller);
                    controller.emitter.emit("batch:run:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                    controller.emitter.emit("job:error", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setRunBatchBusy(false);
                });
        }

        function deleteBatch() {
            if (!controller.state.enabled) {
                setDeleteBatchMessage("Batch runner is disabled.", "warning");
                return;
            }

            if (controller.should_disable_command_button(controller)) {
                return;
            }

            if (!controller.state.batchName) {
                setDeleteBatchMessage("Batch name is missing.", "critical");
                return;
            }

            if (typeof controller.reset_panel_state === "function") {
                controller.reset_panel_state(controller);
            }
            cancelRunstateTimer();
            controller.runstate.refreshPending = false;

            setDeleteBatchBusy(true, "Submitting batch delete…", "info");

            controller.connect_status_stream(controller);

            controller.http
                .postJson(
                    "/rq-engine/api/batch/_/" + encodeURIComponent(controller.state.batchName) + "/delete-batch",
                    {},
                    controller.rqEngineToken
                        ? { headers: { Authorization: "Bearer " + controller.rqEngineToken } }
                        : undefined
                )
                .then(function (response) {
                    var payload = response.body || {};
                    if (payload.error || payload.errors) {
                        var errorMsg = resolveErrorMessage(payload, "Failed to submit batch delete.");
                        throw new Error(errorMsg);
                    }

                    if (payload.job_id) {
                        controller.poll_completion_event = "BATCH_DELETE_COMPLETED";
                        controller.set_rq_job_id(controller, payload.job_id);
                    } else {
                        controller.update_command_button_state(controller);
                    }

                    var successMessage = payload.message || "Batch delete submitted.";
                    setDeleteBatchMessage(successMessage, "success");

                    controller.emitter.emit("batch:delete:started", {
                        batchName: controller.state.batchName,
                        job_id: payload.job_id || null
                    });
                    controller.emitter.emit("job:started", {
                        batchName: controller.state.batchName,
                        job_id: payload.job_id || null
                    });
                })
                .catch(function (error) {
                    var message = resolveErrorMessage(error, "Failed to submit batch delete.");
                    setDeleteBatchMessage(message, "critical");
                    controller.disconnect_status_stream(controller);
                    controller.emitter.emit("batch:delete:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                    controller.emitter.emit("job:error", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setDeleteBatchBusy(false);
                });
        }

        function uploadGeojson(event) {
            handleUpload(event);
            return false;
        }

        function validateTemplate(event) {
            handleValidate(event);
            return false;
        }

        function overrideControlBase(ctrl) {
            function buildBatchCreateUrl() {
                var prefix = ctrl.sitePrefix || "";
                if (prefix && prefix.slice(-1) === "/") {
                    prefix = prefix.slice(0, -1);
                }
                return prefix + "/batch/create/";
            }

            var baseSetRqJobId = ctrl.set_rq_job_id;
            ctrl.set_rq_job_id = function (self, jobId) {
                baseSetRqJobId.call(ctrl, self, jobId);
                if (self === ctrl) {
                    if (jobId) {
                        refreshRunstate({ force: true });
                    }
                }
            };

            var baseHandleJobStatusResponse = ctrl.handle_job_status_response;
            ctrl.handle_job_status_response = function (self, data) {
                baseHandleJobStatusResponse.call(ctrl, self, data);
                if (self === ctrl) {
                    refreshRunstate();
                }
            };

            var baseTriggerEvent = ctrl.triggerEvent;
            ctrl.triggerEvent = function (eventName, payload) {
                if (eventName === "BATCH_DELETE_COMPLETED") {
                    ctrl.disconnect_status_stream(ctrl);
                    ctrl.reset_status_spinner(ctrl);
                    cancelRunstateTimer();
                    ctrl.runstate.refreshPending = false;
                    setDeleteBatchMessage("Batch deleted. Redirecting…", "success");
                    ctrl.emitter.emit("batch:delete:completed", {
                        batchName: ctrl.state.batchName,
                        job_id: ctrl.rq_job_id || null,
                        payload: payload || null
                    });
                    ctrl.emitter.emit("job:completed", {
                        batchName: ctrl.state.batchName,
                        job_id: ctrl.rq_job_id || null,
                        payload: payload || null
                    });
                    setTimeout(function () {
                        window.location.assign(buildBatchCreateUrl());
                    }, 150);
                } else if (eventName === "BATCH_DELETE_FAILED") {
                    var deleteErrorText = payload
                        ? (payload.error_message || payload.message || payload.error)
                        : null;
                    setDeleteBatchMessage(deleteErrorText || "Batch delete failed.", "critical");
                    ctrl.emitter.emit("batch:delete:failed", {
                        error: deleteErrorText || "Batch delete failed.",
                        batchName: ctrl.state.batchName
                    });
                    ctrl.emitter.emit("job:error", {
                        error: deleteErrorText || "Batch delete failed.",
                        batchName: ctrl.state.batchName
                    });
                } else if (eventName === "BATCH_RUN_COMPLETED" || eventName === "END_BROADCAST") {
                    ctrl.disconnect_status_stream(ctrl);
                    ctrl.reset_status_spinner(ctrl);
                    refreshRunstate({ force: true });
                    if (eventName === "BATCH_RUN_COMPLETED") {
                        ctrl.emitter.emit("batch:run:completed", {
                            batchName: ctrl.state.batchName,
                            job_id: ctrl.rq_job_id || null,
                            payload: payload || null
                        });
                        ctrl.emitter.emit("job:completed", {
                            batchName: ctrl.state.batchName,
                            job_id: ctrl.rq_job_id || null,
                            payload: payload || null
                        });
                    }
                } else if (eventName === "BATCH_RUN_FAILED") {
                    var errorText = payload
                        ? (payload.error_message || payload.message || payload.error)
                        : null;
                    ctrl.emitter.emit("batch:run:failed", {
                        error: errorText || "Batch run failed.",
                        batchName: ctrl.state.batchName
                    });
                    ctrl.emitter.emit("job:error", {
                        error: errorText || "Batch run failed.",
                        batchName: ctrl.state.batchName
                    });
                    refreshRunstate({ force: true });
                } else if (eventName === "BATCH_WATERSHED_TASK_COMPLETED") {
                    refreshRunstate();
                }

                baseTriggerEvent.call(ctrl, eventName, payload);
            };
        }
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

window.BatchRunner = BatchRunner;

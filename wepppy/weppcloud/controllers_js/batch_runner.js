/* ----------------------------------------------------------------------------
 * Batch Runner (Modernized)
 * Doc: controllers_js/README.md — Batch Runner Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var BatchRunner = (function () {
    "use strict";

    var instance;

    var RUN_DIRECTIVE_STATUS_CLASSES = ["text-danger", "text-success", "text-muted", "text-warning"];
    var RUN_BATCH_MESSAGE_CLASSES = ["text-danger", "text-success", "text-muted", "text-warning", "text-info"];

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
        "job:started",
        "job:completed",
        "job:error"
    ];

    var JOB_INFO_TERMINAL_STATUSES = new Set([
        "finished",
        "failed",
        "stopped",
        "canceled",
        "not_found",
        "complete",
        "completed",
        "success",
        "error"
    ]);

    var SELECTORS = {
        form: "#batch_runner_form",
        statusDisplay: "#batch_runner_form #status",
        stacktrace: "#batch_runner_form #stacktrace",
        infoPanel: "#batch_runner_form #info",
        rqJob: "#batch_runner_form #rq_job",
        container: "#batch-runner-root",
        resourceCard: "#batch-runner-resource-card",
        templateCard: "#batch-runner-template-card",
        runBatchButton: "#btn_run_batch",
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
        validate: '[data-action="batch-validate"]',
        run: '[data-action="batch-run"]'
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
        if (!http || typeof http.request !== "function") {
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

    function buildValidationMessage(summary) {
        if (!summary || typeof summary !== "object") {
            return [];
        }
        var items = [];
        if (summary.feature_count != null) {
            items.push("Features analysed: " + summary.feature_count);
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
        controller.templateInitialised = false;
        controller.command_btn_id = "btn_run_batch";
        controller.statusStream = null;
        controller.statusSpinnerEl = null;
        controller._statusStreamRunId = null;

        controller._delegates = [];
        controller._runDirectivesSaving = false;
        controller._runDirectivesStatus = { message: "", css: "" };

        controller.jobInfo = {
            pollIntervalMs: 3000,
            refreshTimer: null,
            fetchInFlight: false,
            refreshPending: false,
            lastFetchStartedAt: 0,
            forceNextFetch: false,
            trackedIds: new Set(),
            completedIds: new Set(),
            lastPayload: null,
            abortController: null
        };

        controller.container = null;
        controller.resourceCard = null;
        controller.templateCard = null;

        controller.form = null;
        controller.statusDisplay = null;
        controller.stacktrace = null;
        controller.infoPanel = null;
        controller.rq_job = null;
        controller.runBatchButton = null;
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

        controller._jobInfoTerminalStatuses = JOB_INFO_TERMINAL_STATUSES;
        controller._jobInfoTrackedIds = controller.jobInfo.trackedIds;
        controller._jobInfoCompletedIds = controller.jobInfo.completedIds;

        controller.init = init;
        controller.initCreate = init;
        controller.initManage = init;
        controller.destroy = destroy;
        controller.refreshJobInfo = refreshJobInfo;
        controller.runBatch = runBatch;
        controller.uploadGeojson = uploadGeojson;
        controller.validateTemplate = validateTemplate;

        controller.render = render;
        controller.renderResource = renderResource;
        controller.renderValidation = renderValidation;

        controller._setRunBatchMessage = setRunBatchMessage;
        controller._renderRunControls = renderRunControls;
        controller._setRunBatchBusy = setRunBatchBusy;
        controller._setUploadBusy = setUploadBusy;
        controller._setUploadStatus = setUploadStatus;
        controller._setValidateBusy = setValidateBusy;
        controller._setRunDirectivesStatus = setRunDirectivesStatus;
        controller._renderRunDirectives = renderRunDirectives;
        controller._applyResourceVisibility = applyResourceVisibility;

        controller._handleRunDirectiveToggle = handleRunDirectiveToggle;
        controller._handleUpload = handleUpload;
        controller._handleValidate = handleValidate;

        controller._setRunDirectivesBusy = setRunDirectivesBusy;
        controller._submitRunDirectives = submitRunDirectives;

        controller._renderCoreStatus = renderCoreStatus;
        controller._renderJobInfo = renderJobInfo;
        controller._collectJobNodes = collectJobNodes;
        controller._registerTrackedJobId = registerTrackedJobId;
        controller._registerTrackedJobIds = registerTrackedJobIds;
        controller._unregisterTrackedJobId = unregisterTrackedJobId;
        controller._bootstrapTrackedJobIds = bootstrapTrackedJobIds;
        controller._resolveJobInfoRequestIds = resolveJobInfoRequestIds;
        controller._normalizeJobInfoPayload = normalizeJobInfoPayload;
        controller._registerJobInfoTrees = registerJobInfoTrees;
        controller._dedupeJobNodes = dedupeJobNodes;
        controller._pruneCompletedJobIds = pruneCompletedJobIds;
        controller._cancelJobInfoTimer = cancelJobInfoTimer;
        controller._ensureJobInfoFetchScheduled = ensureJobInfoFetchScheduled;
        controller._performJobInfoFetch = performJobInfoFetch;

        controller._buildBaseUrl = buildBaseUrl;
        controller._apiUrl = apiUrl;

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
            controller.sitePrefix = bootstrap.sitePrefix || "";
            controller.baseUrl = buildBaseUrl();
            controller.templateInitialised = false;

            controller.form = deps.dom.qs(SELECTORS.form);
            controller.statusDisplay = deps.dom.qs(SELECTORS.statusDisplay);
            controller.stacktrace = deps.dom.qs(SELECTORS.stacktrace);
            controller.infoPanel = deps.dom.qs(SELECTORS.infoPanel);
            controller.rq_job = deps.dom.qs(SELECTORS.rqJob);

            controller.container = deps.dom.qs(SELECTORS.container);
            controller.resourceCard = deps.dom.qs(SELECTORS.resourceCard);
            controller.templateCard = deps.dom.qs(SELECTORS.templateCard);

            controller.runBatchButton = deps.dom.qs(SELECTORS.runBatchButton);
            controller.runBatchHint = deps.dom.qs(SELECTORS.runBatchHint);
            controller.runBatchLock = deps.dom.qs(SELECTORS.runBatchLock);
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

            bootstrapTrackedJobIds(bootstrap);

            renderCoreStatus();
            render();
            refreshJobInfo();
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
                logLimit: 400
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
            cancelJobInfoTimer();
            if (controller.jobInfo.abortController && typeof controller.jobInfo.abortController.abort === "function") {
                try {
                    controller.jobInfo.abortController.abort();
                } catch (err) {
                    console.warn("Failed to abort job info request during destroy", err);
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
            controller.runDirectiveList = controller.container.querySelector(DATA_ROLES.runDirectiveList);
            controller.runDirectiveStatus = controller.container.querySelector(DATA_ROLES.runDirectiveStatus);

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
        }

        function buildBaseUrl() {
            var prefix = controller.sitePrefix || "";
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
                            '</code></td><td><pre class="mb-0">' +
                            props +
                            "</pre></td></tr>"
                        );
                    })
                    .join("");
            } else {
                deps.dom.hide(controller.resourceSamples);
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
                deps.dom.hide(controller.validationSummary);
                deps.dom.hide(controller.validationIssues);
                deps.dom.hide(controller.validationPreview);
                return;
            }

            var status = validation.status || "unknown";
            var summary = validation.summary || {};
            var issues = validation.errors || [];
            var preview = validation.preview || [];

            setText(
                controller.templateStatus,
                status === "ok" ? "Template is valid." : "Template requires attention."
            );

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
                            var runid = escapeHtml(entry.runid || entry.runId || "—");
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
                    '<div class="text-muted small">No batch tasks configured.</div>';
                setRunDirectivesStatus("No batch tasks configured.", "text-muted");
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
                        '<div class="custom-control custom-checkbox mb-1">' +
                        '<input type="checkbox" class="custom-control-input" id="' +
                        controlId +
                        '" data-run-directive="' +
                        escapeHtml(slug) +
                        '"' +
                        checked +
                        disabled +
                        ">" +
                        '<label class="custom-control-label" for="' +
                        controlId +
                        '">' +
                        escapeHtml(label) +
                        "</label>" +
                        "</div>"
                    );
                })
                .join("");

            controller.runDirectiveList.innerHTML = html;
            syncRunDirectiveDisabledState();

            if (controller._runDirectivesStatus && controller._runDirectivesStatus.message) {
                applyStoredRunDirectiveStatus();
            } else if (!controller.state.enabled) {
                setRunDirectivesStatus("Batch runner is disabled; tasks cannot be edited.", "text-muted");
            }
        }

        function renderRunControls(options) {
            options = options || {};
            var preserveMessage = options.preserveMessage === true;

            if (!controller.runBatchButton) {
                return;
            }

            var jobLocked = controller.should_disable_command_button(controller);
            controller.update_command_button_state(controller);

            if (controller.runBatchLock) {
                if (jobLocked) {
                    deps.dom.show(controller.runBatchLock);
                } else {
                    deps.dom.hide(controller.runBatchLock);
                }
            }

            if (jobLocked) {
                controller.runBatchButton.disabled = true;
                setRunBatchMessage("Batch run in progress…", "text-muted");
                return;
            }

            var enabled = Boolean(controller.state.enabled);
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
            var cssClass = "text-muted";

            if (!enabled) {
                message = "Batch runner is disabled.";
                cssClass = "text-warning";
            } else if (!resource) {
                message = "Upload a watershed GeoJSON before running.";
            } else if (!templateIsValid) {
                message = "Validate and resolve template issues before running.";
                cssClass = "text-warning";
            } else {
                message = "Ready to run batch.";
            }

            controller.runBatchButton.disabled = !allowRun;

            if (!preserveMessage || !allowRun) {
                setRunBatchMessage(message, cssClass);
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

        function setRunBatchBusy(busy, message, cssClass) {
            if (controller.runBatchButton && busy) {
                controller.runBatchButton.disabled = true;
            }
            if (controller.runBatchLock) {
                if (busy) {
                    deps.dom.show(controller.runBatchLock);
                } else if (!controller.should_disable_command_button(controller)) {
                    deps.dom.hide(controller.runBatchLock);
                }
            }
            if (message != null) {
                setRunBatchMessage(message, cssClass || "text-muted");
            }
            if (!busy) {
                renderRunControls({ preserveMessage: true });
            }
        }

        function setRunDirectivesStatus(message, cssClass) {
            controller._runDirectivesStatus = {
                message: message || "",
                css: cssClass || ""
            };
            if (!controller.runDirectiveStatus) {
                return;
            }
            RUN_DIRECTIVE_STATUS_CLASSES.forEach(function (cls) {
                controller.runDirectiveStatus.classList.remove(cls);
            });
            if (cssClass) {
                controller.runDirectiveStatus.classList.add(cssClass);
            }
            setText(controller.runDirectiveStatus, message || "");
        }

        function applyStoredRunDirectiveStatus() {
            if (!controller.runDirectiveStatus) {
                return;
            }
            var status = controller._runDirectivesStatus || {};
            RUN_DIRECTIVE_STATUS_CLASSES.forEach(function (cls) {
                controller.runDirectiveStatus.classList.remove(cls);
            });
            if (status.css) {
                controller.runDirectiveStatus.classList.add(status.css);
            }
            setText(controller.runDirectiveStatus, status.message || "");
        }

        function setRunBatchMessage(message, cssClass) {
            if (!controller.runBatchHint) {
                return;
            }
            RUN_BATCH_MESSAGE_CLASSES.forEach(function (cls) {
                controller.runBatchHint.classList.remove(cls);
            });
            if (cssClass) {
                controller.runBatchHint.classList.add(cssClass);
            }
            setText(controller.runBatchHint, message || "");
        }

        function setUploadBusy(busy, message) {
            if (controller.uploadButton) {
                controller.uploadButton.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setUploadStatus(message, busy ? "text-muted" : "");
            }
        }

        function setValidateBusy(busy, message) {
            if (controller.validateButton) {
                controller.validateButton.disabled = busy || !controller.state.enabled;
            }
            if (message != null) {
                setText(controller.templateStatus, message);
            }
        }

        function setUploadStatus(message, cssClass) {
            if (!controller.uploadStatus) {
                return;
            }
            RUN_BATCH_MESSAGE_CLASSES.concat(["text-info"]).forEach(function (cls) {
                controller.uploadStatus.classList.remove(cls);
            });
            if (cssClass) {
                controller.uploadStatus.classList.add(cssClass);
            }
            setText(controller.uploadStatus, message || "");
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
            setRunDirectivesStatus("Saving batch task selection…", "text-muted");

            controller.http
                .postJson(apiUrl("run-directives"), { run_directives: values })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload || payload.success !== true) {
                        var errorMsg =
                            (payload && (payload.error || payload.message)) ||
                            "Failed to update batch tasks.";
                        throw new Error(errorMsg);
                    }

                    if (payload.snapshot) {
                        controller.state.snapshot = payload.snapshot;
                    } else if (Array.isArray(payload.run_directives)) {
                        var snapshot = controller.state.snapshot || {};
                        snapshot.run_directives = payload.run_directives;
                        controller.state.snapshot = snapshot;
                    }

                    setRunDirectivesStatus("Batch tasks updated.", "text-success");
                    controller.emitter.emit("batch:run-directives:updated", {
                        success: true,
                        batchName: controller.state.batchName,
                        directives: controller.state.snapshot.run_directives || []
                    });
                    renderRunDirectives();
                    renderRunControls();
                })
                .catch(function (error) {
                    var message =
                        error && error.message ? error.message : "Failed to update batch tasks.";
                    setRunDirectivesStatus(message, "text-danger");
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

        function renderJobInfo(payload) {
            var infoPanel = controller.infoPanel;
            if (!infoPanel) {
                return;
            }

            if (!payload) {
                infoPanel.innerHTML = '<span class="text-muted">Job information unavailable.</span>';
                return;
            }

            controller.jobInfo.lastPayload = payload;
            var normalized = normalizeJobInfoPayload(payload);
            var jobInfos = Array.isArray(normalized.jobs) ? normalized.jobs : [];

            if (!jobInfos.length) {
                infoPanel.innerHTML = '<span class="text-muted">Job information unavailable.</span>';
                return;
            }

            registerJobInfoTrees(jobInfos);

            var nodes = [];
            jobInfos.forEach(function (info) {
                collectJobNodes(info, nodes);
            });
            var dedupedNodes = dedupeJobNodes(nodes);
            pruneCompletedJobIds(dedupedNodes);

            var watershedNodes = dedupedNodes.filter(function (node) {
                return node && node.runid;
            });

            var totalWatersheds = watershedNodes.length;
            var completedWatersheds = watershedNodes.filter(function (node) {
                return node.status === "finished";
            }).length;
            var failedWatersheds = watershedNodes.filter(function (node) {
                return (
                    node.status === "failed" ||
                    node.status === "stopped" ||
                    node.status === "canceled"
                );
            });
            var activeWatersheds = watershedNodes.filter(function (node) {
                return (
                    node.status &&
                    node.status !== "finished" &&
                    node.status !== "failed" &&
                    node.status !== "stopped" &&
                    node.status !== "canceled"
                );
            });

            var parts = [];

            if (jobInfos.length === 1) {
                var rootInfo = jobInfos[0] || {};
                parts.push(
                    "<div><strong>Batch status:</strong> " +
                        escapeHtml(rootInfo.status || "unknown") +
                        "</div>"
                );
                if (rootInfo.id) {
                    parts.push(
                        '<div class="small text-muted">Job ID: <code>' +
                            escapeHtml(rootInfo.id) +
                            "</code></div>"
                    );
                }
            } else {
                parts.push("<div><strong>Tracked jobs:</strong></div>");
                var maxJobsToShow = 6;
                var jobBadges = jobInfos.slice(0, maxJobsToShow).map(function (info) {
                    var safeStatus = escapeHtml((info && info.status) || "unknown");
                    var safeId = escapeHtml((info && info.id) || "—");
                    return (
                        '<span class="badge badge-light text-dark border mr-1 mb-1">' +
                        safeStatus +
                        " · <code>" +
                        safeId +
                        "</code></span>"
                    );
                });
                if (jobInfos.length > maxJobsToShow) {
                    jobBadges.push('<span class="text-muted">…</span>');
                }
                parts.push('<div class="mt-1">' + jobBadges.join(" ") + "</div>");
            }

            var allNotFound = jobInfos.every(function (info) {
                return info && info.status === "not_found";
            });

            if (allNotFound) {
                parts.push(
                    '<div class="small text-muted">Requested job IDs were not found in the queue.</div>'
                );
                infoPanel.innerHTML = parts.join("");
                return;
            }

            if (totalWatersheds > 0) {
                parts.push(
                    '<div class="small text-muted">Watersheds: ' +
                        completedWatersheds +
                        "/" +
                        totalWatersheds +
                        " finished</div>"
                );
            } else {
                parts.push(
                    '<div class="small text-muted">Watershed tasks have not started yet.</div>'
                );
            }

            if (activeWatersheds.length) {
                var activeList = activeWatersheds.slice(0, 6).map(function (node) {
                    return (
                        '<span class="badge badge-info text-dark mr-1 mb-1">' +
                        escapeHtml(node.runid) +
                        " · " +
                        escapeHtml(node.status || "pending") +
                        "</span>"
                    );
                });
                if (activeWatersheds.length > activeList.length) {
                    activeList.push('<span class="text-muted">…</span>');
                }
                parts.push(
                    '<div class="mt-2"><strong>Active</strong><div>' +
                        activeList.join(" ") +
                        "</div></div>"
                );
            }

            if (failedWatersheds.length) {
                var failedList = failedWatersheds.slice(0, 6).map(function (node) {
                    return (
                        '<span class="badge badge-danger text-light mr-1 mb-1">' +
                        escapeHtml(node.runid) +
                        "</span>"
                    );
                });
                if (failedWatersheds.length > failedList.length) {
                    failedList.push('<span class="text-muted">…</span>');
                }
                parts.push(
                    '<div class="mt-2"><strong class="text-danger">Failures</strong><div>' +
                        failedList.join(" ") +
                        "</div></div>"
                );
            }

            infoPanel.innerHTML = parts.join("");
        }

        function collectJobNodes(jobInfo, acc) {
            if (!jobInfo) {
                return;
            }
            acc.push(jobInfo);
            var children = jobInfo.children || {};
            Object.keys(children).forEach(function (orderKey) {
                var bucket = children[orderKey] || [];
                bucket.forEach(function (child) {
                    if (child) {
                        collectJobNodes(child, acc);
                    }
                });
            });
        }

        function registerTrackedJobId(jobId) {
            if (jobId === undefined || jobId === null) {
                return false;
            }
            var normalized = String(jobId).trim();
            if (!normalized) {
                return false;
            }
            if (controller.jobInfo.completedIds.has(normalized)) {
                return false;
            }
            if (!controller.jobInfo.trackedIds.has(normalized)) {
                controller.jobInfo.trackedIds.add(normalized);
                return true;
            }
            return false;
        }

        function unregisterTrackedJobId(jobId) {
            if (jobId === undefined || jobId === null) {
                return false;
            }
            var normalized = String(jobId).trim();
            if (!normalized) {
                return false;
            }
            if (controller.jobInfo.trackedIds.has(normalized)) {
                controller.jobInfo.trackedIds.delete(normalized);
                return true;
            }
            return false;
        }

        function registerTrackedJobIds(collection) {
            if (!collection) {
                return;
            }
            if (Array.isArray(collection)) {
                collection.forEach(registerTrackedJobId);
                return;
            }
            if (typeof collection === "object") {
                Object.keys(collection).forEach(function (key) {
                    registerTrackedJobId(collection[key]);
                });
                return;
            }
            registerTrackedJobId(collection);
        }

        function bootstrapTrackedJobIds(bootstrap) {
            if (!bootstrap || typeof bootstrap !== "object") {
                return;
            }

            if (Array.isArray(bootstrap.jobIds)) {
                registerTrackedJobIds(bootstrap.jobIds);
            }

            if (bootstrap.rqJobIds && typeof bootstrap.rqJobIds === "object") {
                registerTrackedJobIds(bootstrap.rqJobIds);
            }

            var snapshot = bootstrap.state || {};
            var metadata =
                snapshot && typeof snapshot === "object" ? snapshot.metadata || {} : {};

            registerTrackedJobIds(snapshot.job_ids);
            registerTrackedJobIds(metadata.job_ids);
            registerTrackedJobIds(metadata.rq_job_ids);
            registerTrackedJobIds(metadata.tracked_job_ids);
        }

        function resolveJobInfoRequestIds() {
            var ids = new Set();

            if (controller.rq_job_id) {
                var rootId = String(controller.rq_job_id).trim();
                if (rootId && !controller.jobInfo.completedIds.has(rootId)) {
                    ids.add(rootId);
                }
            }

            controller.jobInfo.trackedIds.forEach(function (value) {
                if (!value) {
                    return;
                }
                var normalizedTracked = String(value).trim();
                if (normalizedTracked && !controller.jobInfo.completedIds.has(normalizedTracked)) {
                    ids.add(normalizedTracked);
                }
            });

            return Array.from(ids);
        }

        function normalizeJobInfoPayload(payload) {
            if (!payload || typeof payload !== "object") {
                return { jobs: [] };
            }
            if (Array.isArray(payload.jobs)) {
                return payload;
            }
            if (Array.isArray(payload.job_info)) {
                return { jobs: payload.job_info };
            }
            if (payload.jobs && typeof payload.jobs === "object") {
                return { jobs: Object.values(payload.jobs) };
            }
            return { jobs: [] };
        }

        function registerJobInfoTrees(jobInfos) {
            if (!Array.isArray(jobInfos)) {
                return;
            }
            jobInfos.forEach(function (info) {
                if (info && info.id) {
                    registerTrackedJobId(info.id);
                    if (controller._jobInfoTerminalStatuses.has(info.status)) {
                        controller.jobInfo.completedIds.add(String(info.id).trim());
                    }
                }
            });
        }

        function dedupeJobNodes(nodes) {
            var seen = new Set();
            var result = [];
            nodes.forEach(function (node) {
                if (!node || !node.id) {
                    return;
                }
                var normalized = String(node.id).trim();
                if (seen.has(normalized)) {
                    return;
                }
                seen.add(normalized);
                result.push(node);
            });
            return result;
        }

        function pruneCompletedJobIds(nodes) {
            if (!Array.isArray(nodes)) {
                return;
            }
            nodes.forEach(function (node) {
                if (!node || !node.id) {
                    return;
                }
                var id = String(node.id).trim();
                if (!id) {
                    return;
                }
                if (controller._jobInfoTerminalStatuses.has(node.status)) {
                    controller.jobInfo.completedIds.add(id);
                    controller.jobInfo.trackedIds.delete(id);
                }
            });
        }

        function cancelJobInfoTimer() {
            if (controller.jobInfo.refreshTimer) {
                clearTimeout(controller.jobInfo.refreshTimer);
                controller.jobInfo.refreshTimer = null;
            }
        }

        function ensureJobInfoFetchScheduled() {
            if (controller.jobInfo.fetchInFlight) {
                return;
            }

            var now = Date.now();
            var interval = controller.jobInfo.pollIntervalMs || 0;
            var lastStarted = controller.jobInfo.lastFetchStartedAt || 0;
            var elapsed = now - lastStarted;
            var forceNext = controller.jobInfo.forceNextFetch === true;

            if (!forceNext && interval > 0 && elapsed < interval) {
                if (controller.jobInfo.refreshTimer) {
                    return;
                }
                controller.jobInfo.refreshTimer = setTimeout(function () {
                    controller.jobInfo.refreshTimer = null;
                    performJobInfoFetch();
                }, interval - elapsed);
                return;
            }

            controller.jobInfo.forceNextFetch = false;
            performJobInfoFetch();
        }

        function performJobInfoFetch() {
            if (!controller.infoPanel) {
                return;
            }

            if (controller.jobInfo.fetchInFlight) {
                return;
            }

            cancelJobInfoTimer();
            controller.jobInfo.forceNextFetch = false;

            var jobIds = resolveJobInfoRequestIds();
            if (!jobIds.length) {
                controller.jobInfo.refreshPending = false;
                if (!controller.jobInfo.lastPayload) {
                    controller.infoPanel.innerHTML =
                        '<span class="text-muted">No batch job submitted yet.</span>';
                }
                return;
            }

            jobIds.forEach(registerTrackedJobId);

            controller.jobInfo.refreshPending = false;
            controller.jobInfo.fetchInFlight = true;
            controller.jobInfo.lastFetchStartedAt = Date.now();

            if (typeof AbortController !== "undefined") {
                if (controller.jobInfo.abortController) {
                    controller.jobInfo.abortController.abort();
                }
                controller.jobInfo.abortController = new AbortController();
            }

            var signal = controller.jobInfo.abortController
                ? controller.jobInfo.abortController.signal
                : undefined;

            controller.http
                .postJson("/weppcloud/rq/api/jobinfo", { job_ids: jobIds }, { signal: signal })
                .then(function (response) {
                    var payload = normalizeJobInfoPayload(response.body);
                    registerTrackedJobIds(payload.job_ids);
                    renderJobInfo(payload);
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
                    console.warn("Unable to refresh batch job info:", error);
                    if (controller.infoPanel) {
                        controller.infoPanel.innerHTML =
                            '<span class="text-muted">Unable to refresh batch job details.</span>';
                    }
                })
                .finally(function () {
                    if (controller.jobInfo.abortController) {
                        controller.jobInfo.abortController = null;
                    }
                    controller.jobInfo.fetchInFlight = false;
                    if (controller.jobInfo.refreshPending) {
                        ensureJobInfoFetchScheduled();
                    }
                });
        }

        function refreshJobInfo(options) {
            options = options || {};
            if (!controller.infoPanel) {
                return;
            }

            if (options.force === true) {
                controller.jobInfo.forceNextFetch = true;
                controller.jobInfo.refreshPending = true;
                cancelJobInfoTimer();
                if (!controller.jobInfo.fetchInFlight) {
                    performJobInfoFetch();
                }
                return;
            }

            controller.jobInfo.refreshPending = true;
            ensureJobInfoFetchScheduled();
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
                '<dt class="col-sm-4">' +
                escapeHtml(label) +
                "</dt>" +
                '<dd class="col-sm-8">' +
                escapeHtml(value) +
                "</dd>"
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
                setUploadStatus("Choose a GeoJSON file before uploading.", "text-warning");
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
                .request(apiUrl("upload-geojson"), {
                    method: "POST",
                    body: formData
                })
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.success) {
                        var errorMsg = payload.error || payload.message || "Upload failed.";
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

                    setUploadStatus(payload.message || "Upload complete.", "text-success");
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
                    var message = error && error.message ? error.message : "Upload failed.";
                    setUploadStatus(message, "text-danger");
                    controller.emitter.emit("batch:upload:failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setUploadBusy(false);
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
                        var errorMsg =
                            payload.error || payload.message || "Template validation failed.";
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
                        success: true,
                        batchName: controller.state.batchName,
                        validation: payload.validation
                    });
                })
                .catch(function (error) {
                    var message =
                        error && error.message ? error.message : "Template validation failed.";
                    setText(controller.templateStatus, message);
                    controller.emitter.emit("batch:template:validate-failed", {
                        error: message,
                        batchName: controller.state.batchName
                    });
                })
                .finally(function () {
                    setValidateBusy(false);
                });
        }

        function runBatch() {
            if (!controller.state.enabled) {
                setRunBatchMessage("Batch runner is disabled.", "text-warning");
                return;
            }

            if (controller.should_disable_command_button(controller)) {
                return;
            }

            if (
                controller.jobInfo.abortController &&
                typeof controller.jobInfo.abortController.abort === "function"
            ) {
                try {
                    controller.jobInfo.abortController.abort();
                } catch (abortError) {
                    console.warn(
                        "Failed to abort in-flight job info request before submitting batch:",
                        abortError
                    );
                }
                controller.jobInfo.abortController = null;
            }
            cancelJobInfoTimer();
            controller.jobInfo.fetchInFlight = false;
            controller.jobInfo.refreshPending = false;
            controller.jobInfo.forceNextFetch = false;
            controller.jobInfo.lastFetchStartedAt = 0;
            controller.jobInfo.trackedIds.clear();
            controller.jobInfo.completedIds.clear();
            controller.jobInfo.lastPayload = null;

            setRunBatchBusy(true, "Submitting batch run…", "text-muted");

            controller.connect_status_stream(controller);

            if (controller.infoPanel) {
                controller.infoPanel.innerHTML =
                    '<span class="text-muted">Submitting batch job…</span>';
            }

            controller.http
                .postJson(apiUrl("rq/api/run-batch"), {})
                .then(function (response) {
                    var payload = response.body || {};
                    if (!payload.success) {
                        var errorMsg = payload.error || payload.message || "Failed to submit batch run.";
                        throw new Error(errorMsg);
                    }

                    if (payload.job_id) {
                        controller.set_rq_job_id(controller, payload.job_id);
                    } else {
                        controller.update_command_button_state(controller);
                    }

                    var successMessage = payload.message || "Batch run submitted.";
                    setRunBatchMessage(successMessage, "text-success");

                    controller.emitter.emit("batch:run:started", {
                        batchName: controller.state.batchName,
                        jobId: payload.job_id || null
                    });
                    controller.emitter.emit("job:started", {
                        batchName: controller.state.batchName,
                        jobId: payload.job_id || null
                    });
                })
                .catch(function (error) {
                    var message =
                        error && error.message ? error.message : "Failed to submit batch run.";
                    setRunBatchMessage(message, "text-danger");
                    if (controller.infoPanel) {
                        controller.infoPanel.innerHTML =
                            '<span class="text-danger">' + escapeHtml(message) + "</span>";
                    }
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

        function uploadGeojson(event) {
            handleUpload(event);
            return false;
        }

        function validateTemplate(event) {
            handleValidate(event);
            return false;
        }

        function overrideControlBase(ctrl) {
            var baseSetRqJobId = ctrl.set_rq_job_id;
            ctrl.set_rq_job_id = function (self, jobId) {
                baseSetRqJobId.call(ctrl, self, jobId);
                if (self === ctrl) {
                    if (jobId) {
                        var normalizedJobId = String(jobId).trim();
                        if (ctrl.jobInfo.completedIds) {
                            ctrl.jobInfo.completedIds.delete(normalizedJobId);
                        }
                        registerTrackedJobId(normalizedJobId);
                    }
                    if (jobId) {
                        refreshJobInfo({ force: true });
                    } else if (ctrl.infoPanel) {
                        ctrl.infoPanel.innerHTML =
                            '<span class="text-muted">No batch job submitted yet.</span>';
                    }
                }
            };

            var baseHandleJobStatusResponse = ctrl.handle_job_status_response;
            ctrl.handle_job_status_response = function (self, data) {
                baseHandleJobStatusResponse.call(ctrl, self, data);
                if (self === ctrl) {
                    refreshJobInfo();
                }
            };

            var baseTriggerEvent = ctrl.triggerEvent;
            ctrl.triggerEvent = function (eventName, payload) {
                if (eventName === "BATCH_RUN_COMPLETED" || eventName === "END_BROADCAST") {
                    ctrl.disconnect_status_stream(ctrl);
                    ctrl.reset_status_spinner(ctrl);
                    refreshJobInfo({ force: true });
                    if (eventName === "BATCH_RUN_COMPLETED") {
                        ctrl.emitter.emit("batch:run:completed", {
                            success: true,
                            batchName: ctrl.state.batchName,
                            jobId: ctrl.rq_job_id || null,
                            payload: payload || null
                        });
                        ctrl.emitter.emit("job:completed", {
                            success: true,
                            batchName: ctrl.state.batchName,
                            jobId: ctrl.rq_job_id || null,
                            payload: payload || null
                        });
                    }
                } else if (eventName === "BATCH_RUN_FAILED") {
                    ctrl.emitter.emit("batch:run:failed", {
                        error: payload && payload.error ? payload.error : "Batch run failed.",
                        batchName: ctrl.state.batchName
                    });
                    ctrl.emitter.emit("job:error", {
                        error: payload && payload.error ? payload.error : "Batch run failed.",
                        batchName: ctrl.state.batchName
                    });
                } else if (eventName === "BATCH_WATERSHED_TASK_COMPLETED") {
                    refreshJobInfo();
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

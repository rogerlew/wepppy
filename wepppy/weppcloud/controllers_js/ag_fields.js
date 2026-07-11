/* ----------------------------------------------------------------------------
 * AgFields
 * Doc: wepppy/nodb/mods/ag_fields/ui_control_layout.md
 * ----------------------------------------------------------------------------
 */
var AgFields = (function () {
    "use strict";

    var instance;

    var JOBS = {
        agfields_build_subfields: {
            completionEvent: "AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED",
            statusRole: "subfields-status"
        },
        agfields_plantdb: {
            completionEvent: "AGFIELDS_PLANTDB_TASK_COMPLETED",
            statusRole: "plantdb-status"
        },
        agfields_run_wepp: {
            completionEvent: "AGFIELDS_RUN_WEPP_TASK_COMPLETED",
            statusRole: "run-status"
        }
    };
    var JOB_KEYS = ["agfields_run_wepp", "agfields_plantdb", "agfields_build_subfields"];
    var LAYER_NAME = "AgFields Sub-fields";
    var LAYER_KEY = "agFieldsSubfields";

    var EVENT_NAMES = [
        "agfields:state:loaded",
        "agfields:state:error",
        "agfields:boundaries:uploaded",
        "agfields:schema:confirmed",
        "agfields:subfields:queued",
        "agfields:plantdb:queued",
        "agfields:mapping:loaded",
        "agfields:mapping:saved",
        "agfields:wepp:queued",
        "agfields:artifacts:cleared",
        "agfields:overlay:shown",
        "agfields:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;
        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function") {
            throw new Error("AgFields controller requires WCDom helpers.");
        }
        if (
            !http ||
            typeof http.requestWithSessionToken !== "function" ||
            typeof http.postJsonWithSessionToken !== "function"
        ) {
            throw new Error("AgFields controller requires authenticated WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("AgFields controller requires WCEvents helpers.");
        }
        return { dom: dom, http: http, events: events };
    }

    function createLegacyAdapter(element) {
        return {
            element: element || null,
            length: element ? 1 : 0,
            show: function () {
                if (element) {
                    element.hidden = false;
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                if (element) {
                    element.hidden = true;
                    element.style.display = "none";
                }
            },
            text: function (value) {
                if (!element) {
                    return value === undefined ? "" : undefined;
                }
                if (value === undefined) {
                    return element.textContent;
                }
                element.textContent = value === null ? "" : String(value);
            },
            html: function (value) {
                if (!element) {
                    return value === undefined ? "" : undefined;
                }
                if (value === undefined) {
                    return element.innerHTML;
                }
                element.innerHTML = value === null ? "" : String(value);
            },
            append: function (value) {
                if (element && value !== undefined && value !== null) {
                    element.insertAdjacentHTML("beforeend", String(value));
                }
            },
            empty: function () {
                if (element) {
                    element.textContent = "";
                }
            }
        };
    }

    function asArray(value) {
        return Array.isArray(value) ? value : [];
    }

    function asObject(value) {
        return value && typeof value === "object" ? value : {};
    }

    function asString(value) {
        return value === null || value === undefined ? "" : String(value).trim();
    }

    function isFiniteInteger(value) {
        var number = Number(value);
        return Number.isFinite(number) && Math.floor(number) === number;
    }

    function unwrapResult(result) {
        if (result && Object.prototype.hasOwnProperty.call(result, "body")) {
            return result.body;
        }
        return result;
    }

    function escapeSelectorValue(value) {
        if (window.CSS && typeof window.CSS.escape === "function") {
            return window.CSS.escape(value);
        }
        return String(value).replace(/["\\]/g, "\\$&");
    }

    function resolveErrorPayload(error) {
        if (error && error.body && typeof error.body === "object") {
            return error.body;
        }
        if (error && error.detail && typeof error.detail === "object") {
            return error.detail;
        }
        return { error: { message: error && error.message ? error.message : "Request failed." } };
    }

    function resolveErrorMessage(error, fallback) {
        var payload = error && error.body ? error.body : error;
        if (payload && payload.error) {
            if (typeof payload.error === "string") {
                return payload.error;
            }
            if (payload.error.message) {
                return String(payload.error.message);
            }
            if (payload.error.detail) {
                return String(payload.error.detail);
            }
        }
        if (payload && payload.message) {
            return String(payload.message);
        }
        if (error && error.detail && typeof error.detail === "string") {
            return error.detail;
        }
        if (error && error.message) {
            return error.message;
        }
        return fallback || "Request failed.";
    }

    function isJobConflict(error) {
        var payload = error && error.body ? error.body : {};
        return Boolean(
            error &&
            Number(error.status) === 409 &&
            payload &&
            payload.error &&
            payload.error.code === "agfields_job_active"
        );
    }

    function formatCount(value) {
        var number = Number(value || 0);
        return Number.isFinite(number) ? number.toLocaleString() : "0";
    }

    function formatTimestamp(value) {
        var text = asString(value);
        return text ? text.replace("T", " ").replace(/Z$/, " UTC") : "time unavailable";
    }

    function resolvePatternColumn(pattern, year) {
        var normalized = asString(pattern);
        if (!normalized) {
            return "";
        }
        return normalized.indexOf("{}") === -1
            ? normalized
            : normalized.replace("{}", String(year));
    }

    function detectCropYearPatterns(columns, startYear, endYear) {
        var normalizedColumns = asArray(columns).map(asString).filter(Boolean);
        var columnSet = new Set(normalizedColumns);
        var start = Number(startYear);
        var end = Number(endYear);
        var groups = {};
        var years = [];

        if (!isFiniteInteger(start) || !isFiniteInteger(end) || start > end) {
            return {
                outcome: "none",
                years: [],
                candidates: [],
                completeCandidates: [],
                partialCandidates: [],
                suggested: null
            };
        }

        for (var year = start; year <= end; year += 1) {
            years.push(year);
        }

        normalizedColumns.forEach(function (column) {
            var match = column.match(/^(.*?)(\d{4})$/);
            if (!match) {
                return;
            }
            var matchedYear = Number(match[2]);
            if (matchedYear < start || matchedYear > end) {
                return;
            }
            var pattern = match[1] + "{}";
            groups[pattern] = groups[pattern] || {};
            groups[pattern][matchedYear] = column;
        });

        var candidates = Object.keys(groups).sort(function (left, right) {
            return left.localeCompare(right);
        }).map(function (pattern) {
            var resolutions = years.map(function (candidateYear) {
                var column = resolvePatternColumn(pattern, candidateYear);
                return {
                    year: candidateYear,
                    column: column,
                    found: columnSet.has(column)
                };
            });
            var coverage = resolutions.filter(function (item) { return item.found; }).length;
            return {
                pattern: pattern,
                coverage: coverage,
                complete: coverage === years.length,
                resolutions: resolutions
            };
        });
        var complete = candidates.filter(function (candidate) { return candidate.complete; });
        var partial = candidates.filter(function (candidate) { return !candidate.complete; });
        partial.sort(function (left, right) {
            if (left.coverage !== right.coverage) {
                return right.coverage - left.coverage;
            }
            return left.pattern.localeCompare(right.pattern);
        });

        return {
            outcome: complete.length === 1 ? "single" : (complete.length > 1 ? "multiple" : "none"),
            years: years,
            candidates: candidates,
            completeCandidates: complete,
            partialCandidates: partial,
            suggested: complete[0] || partial[0] || null
        };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var eventsApi = helpers.events;
        var controller = controlBase();
        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());
        var baseTriggerEvent = controller.triggerEvent.bind(controller);

        controller.events = emitter;
        controller.form = null;
        controller.modal = null;
        controller.state = null;
        controller.context = {};
        controller.nodes = {};
        controller.modalNodes = {};
        controller._boundForm = null;
        controller._boundModal = null;
        controller._statusForm = null;
        controller._hydratePromise = null;
        controller._jobKey = null;
        controller._bootstrapJobIds = {};
        controller._terminalJobsSeen = {};
        controller._boundarySignature = null;
        controller._transientDuplicates = [];
        controller._plantInventory = { files: [], valid_files: [], invalid_files: [] };
        controller._mappingPayload = null;
        controller._overlayRegistered = false;
        controller._clearArmedUntil = 0;
        controller.detectCropYearPatterns = detectCropYearPatterns;

        function urlFor(path) {
            return url_for_run(path, { prefix: "/rq-engine/api" });
        }

        function authorizedRequest(path, options) {
            return http.requestWithSessionToken(urlFor(path), options || {}).then(unwrapResult);
        }

        function authorizedGet(path) {
            return authorizedRequest(path, { method: "GET" });
        }

        function authorizedPost(path, payload) {
            return http.postJsonWithSessionToken(urlFor(path), payload || {}, { form: controller.form }).then(unwrapResult);
        }

        function queryRole(role, root) {
            return dom.qs('[data-role="' + role + '"]', root || controller.form);
        }

        function setChip(element, message, state) {
            if (!element) {
                return;
            }
            element.textContent = message || "";
            if (message) {
                element.dataset.state = state || "info";
            } else {
                element.removeAttribute("data-state");
            }
        }

        function setButtonBusy(button, busy, label) {
            if (!button) {
                return;
            }
            if (!button.dataset.agfieldsIdleLabel) {
                button.dataset.agfieldsIdleLabel = button.textContent.trim();
            }
            if (busy) {
                if (button.getAttribute("aria-busy") !== "true") {
                    button.dataset.agfieldsBusyPrevDisabled = button.disabled ? "true" : "false";
                }
                button.disabled = true;
                button.setAttribute("aria-busy", "true");
                if (label) {
                    button.textContent = label;
                }
                return;
            }
            button.removeAttribute("aria-busy");
            button.textContent = button.dataset.agfieldsIdleLabel;
            if (Object.prototype.hasOwnProperty.call(button.dataset, "agfieldsBusyPrevDisabled")) {
                button.disabled = button.dataset.agfieldsBusyPrevDisabled === "true";
                delete button.dataset.agfieldsBusyPrevDisabled;
            }
        }

        function setDisabled(control, disabled) {
            if (!control) {
                return;
            }
            if (control.tagName === "BUTTON") {
                setButtonBusy(control, false);
            }
            control.disabled = Boolean(disabled);
            control.setAttribute("aria-disabled", disabled ? "true" : "false");
        }

        function hasActiveJob(state) {
            var active = asObject(state && state.active_job_ids);
            return JOB_KEYS.some(function (key) { return Boolean(active[key]); });
        }

        function activeJobEntry(state) {
            var active = asObject(state && state.active_job_ids);
            for (var index = 0; index < JOB_KEYS.length; index += 1) {
                var key = JOB_KEYS[index];
                if (active[key]) {
                    return { key: key, jobId: active[key] };
                }
            }
            return null;
        }

        function emitError(scope, error) {
            var payload = resolveErrorPayload(error);
            controller.pushResponseStacktrace(controller, payload);
            emitter.emit("agfields:error", { scope: scope, error: payload });
        }

        function handleRequestError(scope, chip, lead, error) {
            var conflict = isJobConflict(error);
            var message = resolveErrorMessage(error, "Request failed.");
            setChip(chip, lead + ": " + message, conflict ? "warning" : "critical");
            if (conflict) {
                controller.hydrate({ force: true });
                return;
            }
            emitError(scope, error);
        }

        function collectNodes() {
            var form = dom.qs("#ag_fields_form");
            if (!form || !form.isConnected) {
                controller.form = null;
                controller.nodes = {};
                return false;
            }
            controller.form = form;
            controller.nodes = {
                geojsonInput: queryRole("geojson-input", form),
                uploadButton: queryRole("upload-button", form),
                uploadStatus: queryRole("upload-status", form),
                boundaryFileDisplay: queryRole("boundary-file-display", form),
                boundaryFilename: queryRole("boundary-filename", form),
                boundarySummary: queryRole("boundary-summary", form),
                duplicateWarning: queryRole("duplicate-warning", form),
                fieldIdSelect: queryRole("field-id-select", form),
                accessorDisplay: queryRole("accessor-display", form),
                accessorCandidates: queryRole("accessor-candidates", form),
                accessorInput: queryRole("accessor-input", form),
                accessorResolutionBody: queryRole("accessor-resolution-body", form),
                confirmSchemaButton: queryRole("confirm-schema-button", form),
                schemaStatus: queryRole("schema-status", form),
                schemaOptions: dom.qs("#agfields_schema_options", form),
                buildSubfieldsButton: queryRole("build-subfields-button", form),
                subfieldsStatus: queryRole("subfields-status", form),
                subfieldsSummary: queryRole("subfields-summary", form),
                minAreaInput: queryRole("min-area-input", form),
                mappingChip: queryRole("mapping-chip", form),
                openMappingButton: queryRole("open-mapping-button", form),
                plantdbInput: queryRole("plantdb-input", form),
                plantdbUploadButton: queryRole("plantdb-upload-button", form),
                plantdbStatus: queryRole("plantdb-status", form),
                plantfileTableBody: queryRole("plantfile-table-body", form),
                plantdbOptions: dom.qs("#agfields_plantdb_options", form),
                runButton: queryRole("run-button", form),
                runStatus: queryRole("run-status", form),
                weppBinSelect: queryRole("wepp-bin-select", form),
                clearRunsButton: queryRole("clear-runs-button", form),
                resultsLinks: queryRole("results-links", form),
                statusPanel: dom.qs("#ag_fields_status_panel", form),
                statusSpinner: dom.qs("#ag_fields_braille", form),
                statusLog: dom.qs("#ag_fields_status_log", form),
                stacktracePanel: dom.qs("#ag_fields_stacktrace_panel", form),
                stacktraceBody: dom.qs("#ag_fields_stacktrace", form),
                rqJob: dom.qs("#ag_fields_rq_job", form),
                hint: dom.qs("#hint_ag_fields_job", form),
                summary: dom.qs("#ag_fields_summary", form)
            };
            controller.statusPanelEl = controller.nodes.statusPanel;
            controller.statusSpinnerEl = controller.nodes.statusSpinner;
            controller.stacktracePanelEl = controller.nodes.stacktracePanel;
            controller.stacktrace = createLegacyAdapter(controller.nodes.stacktraceBody);
            controller.rq_job = createLegacyAdapter(controller.nodes.rqJob);
            controller.hint = createLegacyAdapter(controller.nodes.hint);
            controller.status = createLegacyAdapter(controller.nodes.statusLog);
            return true;
        }

        function collectModalNodes() {
            var modal = dom.qs("#agfields_rotation_modal");
            if (!modal || !modal.isConnected) {
                controller.modal = null;
                controller.modalNodes = {};
                return false;
            }
            controller.modal = modal;
            controller.modalNodes = {
                tableBody: queryRole("mapping-table-body", modal),
                status: queryRole("mapping-status", modal),
                saveButton: queryRole("mapping-save-button", modal),
                unused: queryRole("unused-mappings", modal),
                unusedBody: queryRole("unused-mappings-body", modal)
            };
            return true;
        }

        function attachStatusStream() {
            if (!controller.form || controller._statusForm === controller.form) {
                return;
            }
            if (controller._statusForm && typeof controller.detach_status_stream === "function") {
                controller.detach_status_stream(controller);
            }
            controller.attach_status_stream(controller, {
                element: controller.nodes.statusPanel,
                logElement: controller.nodes.statusLog,
                channel: "ag_fields",
                runId: asObject(controller.context.run).id || window.runid || window.runId || null,
                spinner: controller.nodes.statusSpinner,
                stacktrace: controller.nodes.stacktracePanel ? {
                    element: controller.nodes.stacktracePanel,
                    body: controller.nodes.stacktraceBody
                } : null,
                logLimit: 300,
                onAppend: handleStatusAppend
            });
            controller._statusForm = controller.form;
        }

        function parseStructuredStatus(detail, marker) {
            var raw = detail && detail.raw !== undefined ? detail.raw : (detail && detail.message);
            var text = asString(raw);
            var index = text.indexOf(marker);
            if (index === -1) {
                return null;
            }
            var serialized = text.slice(index + marker.length).trim();
            try {
                return JSON.parse(serialized);
            } catch (error) {
                return null;
            }
        }

        function handleStatusAppend(detail) {
            var failure = parseStructuredStatus(detail, "EXCEPTION_JSON");
            if (!failure) {
                return;
            }
            var job = JOBS[controller._jobKey];
            var chip = job ? queryRole(job.statusRole, controller.form) : null;
            var identifiers = [];
            if (failure.sub_field_id !== undefined && failure.sub_field_id !== null) {
                identifiers.push("sub-field " + failure.sub_field_id);
            }
            if (failure.field_id !== undefined && failure.field_id !== null) {
                identifiers.push("field " + failure.field_id);
            }
            if (failure.filename) {
                identifiers.push(failure.filename);
            }
            var prefix = identifiers.length ? "Failed for " + identifiers.join(", ") : "AgFields job failed";
            setChip(chip, prefix + ": " + (failure.message || "See details."), "critical");
        }

        function wireFormDelegates() {
            if (!controller.form || controller._boundForm === controller.form) {
                return;
            }
            controller._boundForm = controller.form;
            dom.delegate(controller.form, "click", "[data-action]", function (event) {
                var action = event.target.closest("[data-action]");
                if (!action || !controller.form.contains(action)) {
                    return;
                }
                var name = action.getAttribute("data-action");
                if (name === "upload-boundaries") {
                    event.preventDefault();
                    uploadBoundaries();
                } else if (name === "confirm-schema") {
                    event.preventDefault();
                    confirmSchema();
                } else if (name === "build-subfields") {
                    event.preventDefault();
                    buildSubfields();
                } else if (name === "open-mapping") {
                    loadMapping();
                } else if (name === "upload-plantdb") {
                    event.preventDefault();
                    uploadPlantDatabase();
                } else if (name === "delete-plant-file") {
                    event.preventDefault();
                    deletePlantFile(action.dataset.filename || "");
                } else if (name === "run-wepp") {
                    event.preventDefault();
                    runWepp();
                } else if (name === "clear-runs") {
                    event.preventDefault();
                    clearRuns();
                }
            });
            dom.delegate(controller.form, "input", '[data-role="accessor-input"]', function () {
                renderAccessorResolution(controller.nodes.accessorInput.value);
                controller.nodes.accessorDisplay.textContent = "Manual pattern: " + (controller.nodes.accessorInput.value || "not set");
                renderSchemaAction();
            });
            dom.delegate(controller.form, "change", '[data-role="accessor-candidates"]', function (event) {
                controller.nodes.accessorInput.value = event.target.value;
                controller.nodes.accessorDisplay.textContent = describePattern(event.target.value);
                renderAccessorResolution(event.target.value);
                renderSchemaAction();
            });
        }

        function wireModalDelegates() {
            if (!controller.modal || controller._boundModal === controller.modal) {
                return;
            }
            controller._boundModal = controller.modal;
            dom.delegate(controller.modal, "change", '[data-action="mapping-source"]', function (event) {
                var row = event.target.closest("[data-crop-name]");
                if (!row) {
                    return;
                }
                row.dataset.source = event.target.value;
                row.dataset.rotationId = "";
                populateManagementSelect(row);
                renderMappingRowStatus(row, "unmapped", "Choose a management.");
            });
            dom.delegate(controller.modal, "change", '[data-action="mapping-management"]', function (event) {
                var row = event.target.closest("[data-crop-name]");
                if (!row) {
                    return;
                }
                row.dataset.rotationId = event.target.value;
                renderMappingRowStatus(
                    row,
                    event.target.value ? "ok" : "unmapped",
                    event.target.value ? "Ready to save." : "Choose a management."
                );
            });
            dom.delegate(controller.modal, "click", '[data-action="save-mapping"]', function (event) {
                event.preventDefault();
                saveMapping();
            });
        }

        function refreshDom() {
            var hasForm = collectNodes();
            collectModalNodes();
            wireFormDelegates();
            wireModalDelegates();
            attachStatusStream();
            return hasForm;
        }

        function describePattern(pattern) {
            var state = controller.state || {};
            var readiness = asObject(state.readiness);
            var start = readiness.observed_start_year;
            var end = readiness.observed_end_year;
            if (!pattern || !isFiniteInteger(start) || !isFiniteInteger(end)) {
                return pattern || "Observed climate years are not available.";
            }
            return pattern + " — resolves " + resolvePatternColumn(pattern, start) + "…" + resolvePatternColumn(pattern, end);
        }

        function renderAccessorResolution(pattern) {
            var body = controller.nodes.accessorResolutionBody;
            if (!body) {
                return;
            }
            body.textContent = "";
            var readiness = asObject(controller.state && controller.state.readiness);
            var columns = new Set(asArray(controller.state && controller.state.boundary && controller.state.boundary.field_columns));
            var start = Number(readiness.observed_start_year);
            var end = Number(readiness.observed_end_year);
            if (!isFiniteInteger(start) || !isFiniteInteger(end) || start > end) {
                var emptyRow = document.createElement("tr");
                var emptyCell = document.createElement("td");
                emptyCell.colSpan = 3;
                emptyCell.innerHTML = "<em>Observed years are not available yet.</em>";
                emptyRow.appendChild(emptyCell);
                body.appendChild(emptyRow);
                return;
            }
            for (var year = start; year <= end; year += 1) {
                var column = resolvePatternColumn(pattern, year);
                var found = Boolean(column && columns.has(column));
                var row = document.createElement("tr");
                var yearCell = document.createElement("td");
                var columnCell = document.createElement("td");
                var statusCell = document.createElement("td");
                yearCell.textContent = String(year);
                columnCell.textContent = column || "—";
                statusCell.textContent = found ? "Found" : "Missing";
                statusCell.dataset.state = found ? "found" : "missing";
                row.appendChild(yearCell);
                row.appendChild(columnCell);
                row.appendChild(statusCell);
                body.appendChild(row);
            }
        }

        function configurePattern(force) {
            var nodes = controller.nodes;
            var state = controller.state || {};
            var boundary = asObject(state.boundary);
            var schema = asObject(state.schema);
            var readiness = asObject(state.readiness);
            var signature = [boundary.geojson_hash, boundary.geojson_timestamp, asArray(boundary.field_columns).join("|")].join(":");
            var boundaryChanged = force || signature !== controller._boundarySignature;
            controller._boundarySignature = signature;
            var detected = detectCropYearPatterns(
                boundary.field_columns,
                readiness.observed_start_year,
                readiness.observed_end_year
            );
            var savedPattern = asString(schema.rotation_accessor);
            var selectedPattern = savedPattern;

            if (!selectedPattern && (!nodes.accessorInput.value || boundaryChanged)) {
                selectedPattern = detected.suggested ? detected.suggested.pattern : "";
            } else if (!selectedPattern) {
                selectedPattern = nodes.accessorInput.value;
            }
            nodes.accessorInput.value = selectedPattern;
            nodes.accessorCandidates.textContent = "";
            nodes.accessorCandidates.hidden = true;

            if (savedPattern) {
                nodes.accessorDisplay.textContent = describePattern(savedPattern);
            } else if (!readiness.observed_climate) {
                nodes.accessorDisplay.textContent = "An observed climate with valid year bounds is required before confirming the schema.";
            } else if (detected.outcome === "single") {
                nodes.accessorDisplay.textContent = describePattern(selectedPattern);
            } else if (detected.outcome === "multiple") {
                detected.completeCandidates.forEach(function (candidate) {
                    var option = document.createElement("option");
                    option.value = candidate.pattern;
                    option.textContent = describePattern(candidate.pattern);
                    option.selected = candidate.pattern === selectedPattern;
                    nodes.accessorCandidates.appendChild(option);
                });
                nodes.accessorCandidates.hidden = false;
                nodes.accessorDisplay.textContent = "Multiple complete crop-year patterns were found; choose one.";
            } else {
                nodes.accessorDisplay.textContent = "No pattern covers every observed year; review the missing columns below.";
                if (nodes.schemaOptions) {
                    nodes.schemaOptions.open = true;
                }
            }
            renderAccessorResolution(selectedPattern);
        }

        function populateFieldIdSelect() {
            var select = controller.nodes.fieldIdSelect;
            if (!select) {
                return;
            }
            var boundary = asObject(controller.state && controller.state.boundary);
            var schema = asObject(controller.state && controller.state.schema);
            var selected = asString(schema.field_id_key) || "field_id";
            select.textContent = "";
            asArray(boundary.field_columns).forEach(function (column) {
                var option = document.createElement("option");
                option.value = String(column);
                option.textContent = String(column);
                option.selected = String(column) === selected;
                select.appendChild(option);
            });
            select.disabled = !boundary.geojson_is_valid;
        }

        function renderBoundary() {
            var state = controller.state || {};
            var boundary = asObject(state.boundary);
            var active = hasActiveJob(state);
            var filename = asString(boundary.filename);
            if (controller.nodes.boundaryFilename) {
                controller.nodes.boundaryFilename.textContent = filename;
            }
            if (controller.nodes.boundaryFileDisplay) {
                controller.nodes.boundaryFileDisplay.hidden = !filename;
            }
            if (boundary.geojson_is_valid) {
                setChip(
                    controller.nodes.boundarySummary,
                    formatCount(boundary.field_n) + " fields loaded · " +
                        formatCount(asArray(boundary.field_columns).length) + " columns · uploaded " +
                        formatTimestamp(boundary.geojson_timestamp),
                    "success"
                );
            } else {
                setChip(controller.nodes.boundarySummary, "No field boundaries uploaded yet.", "info");
            }
            if (controller._transientDuplicates.length) {
                setChip(
                    controller.nodes.duplicateWarning,
                    formatCount(controller._transientDuplicates.length) + " duplicate field_id values",
                    "warning"
                );
            } else {
                setChip(controller.nodes.duplicateWarning, "", "warning");
            }
            populateFieldIdSelect();
            configurePattern(false);
            setDisabled(controller.nodes.uploadButton, active);
            if (active) {
                setChip(controller.nodes.uploadStatus, "An AgFields job is running; wait for it to finish before replacing boundaries.", "warning");
            }
        }

        function renderSchemaAction() {
            if (!controller.state || !controller.nodes.confirmSchemaButton) {
                return;
            }
            var boundary = asObject(controller.state.boundary);
            var readiness = asObject(controller.state.readiness);
            var active = hasActiveJob(controller.state);
            var hasPattern = Boolean(asString(controller.nodes.accessorInput.value));
            var disabled = active || !boundary.geojson_is_valid || !readiness.observed_climate || !hasPattern;
            setDisabled(controller.nodes.confirmSchemaButton, disabled);
            if (active) {
                setChip(controller.nodes.schemaStatus, "An AgFields job is running; wait for it to finish before changing the schema.", "warning");
            } else if (!boundary.geojson_is_valid) {
                setChip(controller.nodes.schemaStatus, "Upload field boundaries first.", "info");
            } else if (!readiness.observed_climate) {
                setChip(controller.nodes.schemaStatus, "AgFields requires an observed climate with valid start and end years.", "warning");
            } else if (!hasPattern) {
                setChip(controller.nodes.schemaStatus, "Enter a crop-year pattern and resolve missing columns.", "warning");
            } else if (asObject(controller.state.schema).complete) {
                setChip(controller.nodes.schemaStatus, "Field boundary schema confirmed.", "success");
            } else {
                setChip(controller.nodes.schemaStatus, "Review the detected columns, then confirm the schema.", "info");
            }
        }

        function renderSubfields() {
            var state = controller.state || {};
            var schema = asObject(state.schema);
            var readiness = asObject(state.readiness);
            var subfields = asObject(state.subfields);
            var staleness = asObject(state.staleness);
            var active = hasActiveJob(state);
            var blockedMessage = "";
            if (!schema.complete) {
                blockedMessage = "Confirm the field boundary schema above first.";
            } else if (!readiness.watershed_abstraction) {
                blockedMessage = "Build the watershed subcatchments first.";
            }
            setDisabled(controller.nodes.buildSubfieldsButton, active || Boolean(blockedMessage));
            if (active) {
                setChip(controller.nodes.subfieldsStatus, "An AgFields job is running; wait for it to finish.", "warning");
            } else if (blockedMessage) {
                setChip(controller.nodes.subfieldsStatus, blockedMessage, "warning");
            } else if (staleness.subfields) {
                setChip(controller.nodes.subfieldsStatus, "Sub-fields are stale — rebuild required.", "warning");
            } else if (subfields.complete) {
                setChip(controller.nodes.subfieldsStatus, "Sub-fields are ready for review.", "success");
            } else {
                setChip(controller.nodes.subfieldsStatus, "Ready to build sub-fields.", "info");
            }
            if (Number(subfields.sub_field_n || 0) > 0) {
                var summary = formatCount(subfields.field_n) + " fields → " +
                    formatCount(subfields.sub_field_n) + " sub-fields";
                if (staleness.subfields) {
                    summary += " · stale — rebuild required";
                }
                setChip(controller.nodes.subfieldsSummary, summary, staleness.subfields ? "warning" : "success");
            } else {
                setChip(controller.nodes.subfieldsSummary, "", "info");
            }
        }

        function mappingErrorCount(mapping) {
            return asArray(mapping.results).filter(function (row) {
                return row && row.used && row.status === "error";
            }).length;
        }

        function mappingUsesPlantFiles(mapping) {
            return asArray(mapping.results).some(function (row) {
                return row && row.database === "plant_file_db";
            });
        }

        function renderMapping() {
            var state = controller.state || {};
            var schema = asObject(state.schema);
            var mapping = asObject(state.mapping);
            var active = hasActiveJob(state);
            var errors = mappingErrorCount(mapping);
            var message;
            var chipState;
            if (!schema.complete) {
                message = "Confirm the field boundary schema above before mapping crops.";
                chipState = "warning";
            } else {
                message = formatCount(mapping.mapped_count) + " of " + formatCount(mapping.crop_count) + " crops mapped";
                if (errors) {
                    message += " · " + formatCount(errors) + " mapping error" + (errors === 1 ? "" : "s");
                    chipState = "critical";
                } else {
                    chipState = mapping.complete ? "success" : "warning";
                }
            }
            if (active) {
                message += " · wait for the active AgFields job to finish before editing";
                chipState = "warning";
            }
            setChip(controller.nodes.mappingChip, message, chipState);
            setDisabled(controller.nodes.openMappingButton, active || !schema.complete);
            setDisabled(controller.nodes.plantdbUploadButton, active);
            if (active) {
                setChip(controller.nodes.plantdbStatus, "An AgFields job is running; wait for it to finish before changing plant files.", "warning");
            }
            if (
                controller.nodes.plantdbOptions &&
                (Number(asObject(state.plant_files).valid_count || 0) > 0 ||
                 Number(asObject(state.plant_files).invalid_count || 0) > 0 ||
                 mappingUsesPlantFiles(mapping))
            ) {
                controller.nodes.plantdbOptions.open = true;
            }
        }

        function renderResultsLinks(complete) {
            var container = controller.nodes.resultsLinks;
            if (!container) {
                return;
            }
            container.textContent = "";
            if (!complete) {
                return;
            }
            var browse = document.createElement("a");
            browse.href = url_for_run("browse/wepp/ag_fields/output/");
            browse.target = "_blank";
            browse.rel = "noopener";
            browse.textContent = "Browse outputs";
            var separator = document.createTextNode(" · ");
            var exports = document.createElement("a");
            exports.href = "#features-export";
            exports.textContent = "Export AgFields layers with Features Export";
            container.appendChild(browse);
            container.appendChild(separator);
            container.appendChild(exports);
            container.dataset.state = "success";
        }

        function renderWepp() {
            var state = controller.state || {};
            var subfields = asObject(state.subfields);
            var mapping = asObject(state.mapping);
            var readiness = asObject(state.readiness);
            var wepp = asObject(state.wepp);
            var staleness = asObject(state.staleness);
            var active = hasActiveJob(state);
            var blocked = "";
            if (controller.nodes.weppBinSelect && asString(wepp.wepp_bin)) {
                controller.nodes.weppBinSelect.value = asString(wepp.wepp_bin);
            }
            if (!subfields.complete) {
                blocked = "Build sub-fields first.";
            } else if (!mapping.complete) {
                var unmapped = Math.max(0, Number(mapping.crop_count || 0) - Number(mapping.mapped_count || 0));
                blocked = "Map all crops to managements first (" + formatCount(unmapped) + " unmapped).";
            } else if (!readiness.parent_wepp) {
                blocked = "Run the watershed WEPP hillslopes first — sub-fields reuse their soil and climate files.";
            }
            setDisabled(controller.nodes.runButton, active || Boolean(blocked));
            setDisabled(controller.nodes.weppBinSelect, active);
            setDisabled(controller.nodes.clearRunsButton, active);
            if (active) {
                setChip(controller.nodes.runStatus, "An AgFields job is running; wait for it to finish.", "warning");
            } else if (blocked) {
                setChip(controller.nodes.runStatus, blocked, "warning");
            } else if (staleness.wepp_runs) {
                setChip(controller.nodes.runStatus, "Previous sub-field outputs are stale — run WEPP again.", "warning");
            } else if (wepp.complete) {
                setChip(controller.nodes.runStatus, formatCount(wepp.run_count) + " sub-field runs complete.", "success");
            } else {
                setChip(controller.nodes.runStatus, "Ready to run WEPP on sub-fields.", "info");
            }
            renderResultsLinks(Boolean(wepp.complete));
        }

        function renderSummary() {
            if (!controller.nodes.summary || !controller.state) {
                return;
            }
            var state = controller.state;
            var complete = [
                Boolean(asObject(state.schema).complete),
                Boolean(asObject(state.subfields).complete),
                Boolean(asObject(state.mapping).complete),
                Boolean(asObject(state.wepp).complete)
            ].filter(Boolean).length;
            controller.nodes.summary.textContent = complete + " of 4 stages complete.";
        }

        function renderState() {
            if (!controller.form || !controller.state) {
                return;
            }
            renderBoundary();
            renderSchemaAction();
            renderSubfields();
            renderMapping();
            renderWepp();
            renderSummary();
        }

        function renderPlantInventory(inventory) {
            controller._plantInventory = asObject(inventory);
            var body = controller.nodes.plantfileTableBody;
            if (!body) {
                return;
            }
            body.textContent = "";
            var files = asArray(controller._plantInventory.files);
            if (!files.length) {
                var emptyRow = document.createElement("tr");
                var emptyCell = document.createElement("td");
                emptyCell.colSpan = 4;
                emptyCell.innerHTML = "<em>No plant files uploaded.</em>";
                emptyRow.appendChild(emptyCell);
                body.appendChild(emptyRow);
                return;
            }
            files.forEach(function (file) {
                var row = document.createElement("tr");
                var nameCell = document.createElement("td");
                var formatCell = document.createElement("td");
                var statusCell = document.createElement("td");
                var actionsCell = document.createElement("td");
                var button = document.createElement("button");
                nameCell.textContent = file.filename || "";
                formatCell.textContent = file.format === "2017.1_downgraded" ? "2017.1 → 98.4" : "98.4";
                if (file.valid) {
                    statusCell.textContent = file.replaced ? "Valid · replaced existing file" : "Valid";
                    statusCell.dataset.state = "ok";
                } else {
                    statusCell.textContent = file.error || "Invalid plant file";
                    statusCell.dataset.state = "error";
                }
                button.type = "button";
                button.className = "pure-button button-error";
                button.dataset.action = "delete-plant-file";
                button.dataset.filename = file.filename || "";
                button.textContent = "Delete";
                button.disabled = hasActiveJob(controller.state);
                actionsCell.appendChild(button);
                row.appendChild(nameCell);
                row.appendChild(formatCell);
                row.appendChild(statusCell);
                row.appendChild(actionsCell);
                body.appendChild(row);
            });
        }

        function loadPlantInventory() {
            if (!controller.form) {
                return Promise.resolve(null);
            }
            return authorizedGet("agfields/plant-files").then(function (inventory) {
                renderPlantInventory(inventory || {});
                return inventory;
            }).catch(function (error) {
                setChip(
                    controller.nodes.plantdbStatus,
                    "Could not refresh plant files: " + resolveErrorMessage(error),
                    "critical"
                );
                return null;
            });
        }

        function syncTrackedJob(state) {
            var active = activeJobEntry(state);
            if (active) {
                trackJob(active.key, active.jobId);
                return;
            }
            if (controller.rq_job_id) {
                return;
            }
            var jobIds = Object.assign({}, controller._bootstrapJobIds, asObject(state.job_ids));
            for (var index = 0; index < JOB_KEYS.length; index += 1) {
                var key = JOB_KEYS[index];
                if (jobIds[key]) {
                    trackJob(key, jobIds[key]);
                    return;
                }
            }
        }

        controller.hydrate = function hydrate(options) {
            if (!refreshDom()) {
                return Promise.resolve(null);
            }
            if (controller._hydratePromise) {
                if (options && options.force) {
                    return controller._hydratePromise.then(function () {
                        return controller.hydrate();
                    });
                }
                return controller._hydratePromise;
            }
            controller._hydratePromise = authorizedGet("agfields/state")
                .then(function (state) {
                    controller.state = asObject(state);
                    syncTrackedJob(controller.state);
                    renderState();
                    emitter.emit("agfields:state:loaded", controller.state);
                    return loadPlantInventory().then(function () {
                        var subfields = asObject(controller.state.subfields);
                        var staleness = asObject(controller.state.staleness);
                        if (
                            subfields.overlay_exists &&
                            !staleness.subfields &&
                            !controller._overlayRegistered
                        ) {
                            loadSubfieldsOverlay({ forceVisible: true });
                        }
                        return controller.state;
                    });
                })
                .catch(function (error) {
                    setChip(
                        controller.nodes.uploadStatus,
                        "Could not load AgFields state: " + resolveErrorMessage(error),
                        "critical"
                    );
                    emitError("state", error);
                    emitter.emit("agfields:state:error", { error: resolveErrorPayload(error) });
                    return null;
                })
                .finally(function () {
                    controller._hydratePromise = null;
                });
            return controller._hydratePromise;
        };

        function trackJob(key, jobId) {
            if (!JOBS[key] || !jobId) {
                return;
            }
            controller._jobKey = key;
            controller.poll_completion_event = JOBS[key].completionEvent;
            controller.set_rq_job_id(controller, jobId);
            controller.connect_status_stream(controller);
        }

        function handleTerminalEvent(eventName, payload) {
            var normalized = asString(eventName).toUpperCase();
            var matchingKey = null;
            Object.keys(JOBS).some(function (key) {
                if (JOBS[key].completionEvent === normalized) {
                    matchingKey = key;
                    return true;
                }
                return false;
            });
            if (!matchingKey && normalized !== "JOB:ERROR") {
                return;
            }
            var jobId = payload && payload.job_id ? payload.job_id : controller.rq_job_id;
            var terminalKey = jobId || (matchingKey || normalized);
            if (controller._terminalJobsSeen[terminalKey]) {
                return;
            }
            controller._terminalJobsSeen[terminalKey] = true;
            var overlayWasRegistered = controller._overlayRegistered;
            controller.hydrate({ force: true }).then(function (state) {
                if (
                    matchingKey === "agfields_build_subfields" &&
                    state &&
                    asObject(state.subfields).overlay_exists
                ) {
                    loadSubfieldsOverlay({
                        forceVisible: true,
                        refresh: overlayWasRegistered,
                        announce: true
                    });
                }
            });
        }

        controller.triggerEvent = function triggerEvent(eventName, payload) {
            var result = baseTriggerEvent(eventName, payload);
            handleTerminalEvent(eventName, payload || {});
            return result;
        };

        function uploadBoundaries() {
            var input = controller.nodes.geojsonInput;
            var file = input && input.files ? input.files[0] : null;
            if (!file) {
                setChip(controller.nodes.uploadStatus, "Choose a GeoJSON file before uploading.", "warning");
                return;
            }
            var formData = new FormData();
            formData.append("field_boundaries", file);
            setButtonBusy(controller.nodes.uploadButton, true, "Uploading…");
            setChip(controller.nodes.uploadStatus, "Uploading and validating field boundaries…", "info");
            authorizedRequest("agfields/boundaries", {
                method: "POST",
                body: formData,
                form: controller.form
            }).then(function (payload) {
                var result = asObject(payload && payload.result);
                controller._transientDuplicates = asArray(result.field_id_duplicates);
                setChip(controller.nodes.uploadStatus, payload.message || "Field boundaries uploaded.", "success");
                emitter.emit("agfields:boundaries:uploaded", result);
                return controller.hydrate();
            }).catch(function (error) {
                handleRequestError("boundaries", controller.nodes.uploadStatus, "Field boundary upload failed", error);
            }).finally(function () {
                setButtonBusy(controller.nodes.uploadButton, false);
            });
        }

        function confirmSchema() {
            var payload = {
                field_id_key: controller.nodes.fieldIdSelect ? controller.nodes.fieldIdSelect.value : "",
                rotation_accessor: controller.nodes.accessorInput ? controller.nodes.accessorInput.value.trim() : ""
            };
            setButtonBusy(controller.nodes.confirmSchemaButton, true, "Confirming…");
            setChip(controller.nodes.schemaStatus, "Validating the field ID and crop-year columns…", "info");
            authorizedPost("agfields/schema", payload).then(function (response) {
                setChip(controller.nodes.schemaStatus, response.message || "Field boundary schema confirmed.", "success");
                emitter.emit("agfields:schema:confirmed", asObject(response.result));
                return controller.hydrate();
            }).catch(function (error) {
                if (controller.nodes.schemaOptions) {
                    controller.nodes.schemaOptions.open = true;
                }
                handleRequestError("schema", controller.nodes.schemaStatus, "Schema confirmation failed", error);
            }).finally(function () {
                setButtonBusy(controller.nodes.confirmSchemaButton, false);
            });
        }

        function enqueue(path, payload, key, button, busyLabel, chip, eventName) {
            setButtonBusy(button, true, busyLabel);
            setChip(chip, busyLabel, "info");
            controller.connect_status_stream(controller);
            return authorizedPost(path, payload).then(function (response) {
                if (!response || !response.job_id) {
                    throw new Error("The job response did not include a job id.");
                }
                controller._terminalJobsSeen[response.job_id] = false;
                trackJob(key, response.job_id);
                setChip(chip, "Job queued: " + response.job_id, "success");
                emitter.emit(eventName, { job_id: response.job_id });
                return controller.hydrate();
            }).catch(function (error) {
                handleRequestError(key, chip, "Could not queue the job", error);
                throw error;
            }).finally(function () {
                setButtonBusy(button, false);
            });
        }

        function buildSubfields() {
            var value = controller.nodes.minAreaInput ? controller.nodes.minAreaInput.value : "0";
            enqueue(
                "agfields/build-subfields",
                { sub_field_min_area_threshold_m2: value === "" ? 0 : Number(value) },
                "agfields_build_subfields",
                controller.nodes.buildSubfieldsButton,
                "Queuing sub-field build…",
                controller.nodes.subfieldsStatus,
                "agfields:subfields:queued"
            ).catch(function () {});
        }

        function uploadPlantDatabase() {
            var input = controller.nodes.plantdbInput;
            var file = input && input.files ? input.files[0] : null;
            if (!file) {
                setChip(controller.nodes.plantdbStatus, "Choose a plant file zip before uploading.", "warning");
                return;
            }
            var formData = new FormData();
            formData.append("plant_database", file);
            setButtonBusy(controller.nodes.plantdbUploadButton, true, "Uploading…");
            setChip(controller.nodes.plantdbStatus, "Uploading and checking plant files…", "info");
            controller.connect_status_stream(controller);
            authorizedRequest("agfields/plant-database", {
                method: "POST",
                body: formData,
                form: controller.form
            }).then(function (response) {
                if (!response || !response.job_id) {
                    throw new Error("The job response did not include a job id.");
                }
                controller._terminalJobsSeen[response.job_id] = false;
                trackJob("agfields_plantdb", response.job_id);
                setChip(controller.nodes.plantdbStatus, "Plant file processing queued: " + response.job_id, "success");
                emitter.emit("agfields:plantdb:queued", { job_id: response.job_id });
                return controller.hydrate();
            }).catch(function (error) {
                handleRequestError("plantdb", controller.nodes.plantdbStatus, "Plant file upload failed", error);
            }).finally(function () {
                setButtonBusy(controller.nodes.plantdbUploadButton, false);
            });
        }

        function deletePlantFile(filename) {
            if (!filename) {
                return;
            }
            setChip(controller.nodes.plantdbStatus, "Deleting " + filename + "…", "info");
            authorizedRequest("agfields/plant-files/" + encodeURIComponent(filename), {
                method: "DELETE",
                form: controller.form
            }).then(function (response) {
                var result = asObject(response.result);
                renderPlantInventory(result.inventory || {});
                setChip(controller.nodes.plantdbStatus, response.message || "Plant file deleted.", "success");
                return controller.hydrate();
            }).catch(function (error) {
                handleRequestError("plant-file-delete", controller.nodes.plantdbStatus, "Could not delete plant file", error);
            });
        }

        function mappingOptionsForSource(source) {
            var payload = asObject(controller._mappingPayload);
            if (source === "weppcloud") {
                return asArray(payload.management_options).map(function (option) {
                    return {
                        value: asString(option.id),
                        label: asString(option.description) + " (id " + asString(option.id) + ")"
                    };
                });
            }
            if (source === "plant_file_db") {
                return asArray(asObject(payload.plant_files).valid_files).map(function (filename) {
                    return { value: String(filename), label: String(filename) };
                });
            }
            return [];
        }

        function renderMappingRowStatus(row, status, message) {
            var statusNode = dom.qs('[data-role="mapping-row-status"]', row);
            if (!statusNode) {
                return;
            }
            statusNode.textContent = message || status || "";
            statusNode.dataset.state = status || "unmapped";
        }

        function populateManagementSelect(row) {
            var select = dom.qs('[data-action="mapping-management"]', row);
            if (!select) {
                return;
            }
            var source = row.dataset.source || "";
            var selected = row.dataset.rotationId || "";
            var options = mappingOptionsForSource(source);
            select.textContent = "";
            var placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = source ? "Choose a management…" : "Choose a source first…";
            select.appendChild(placeholder);
            if (selected && !options.some(function (option) { return option.value === selected; })) {
                var missing = document.createElement("option");
                missing.value = selected;
                missing.textContent = selected + " (missing)";
                missing.selected = true;
                select.appendChild(missing);
            }
            options.forEach(function (optionData) {
                var option = document.createElement("option");
                option.value = optionData.value;
                option.textContent = optionData.label;
                option.selected = optionData.value === selected;
                select.appendChild(option);
            });
            select.disabled = !source;
        }

        function createMappingRow(rowData, index) {
            var cropName = asString(rowData.crop_name);
            var source = asString(rowData.database);
            var rotationId = asString(rowData.rotation_id);
            var row = document.createElement("tr");
            row.dataset.cropName = cropName;
            row.dataset.source = source;
            row.dataset.rotationId = rotationId;

            var cropCell = document.createElement("th");
            cropCell.scope = "row";
            cropCell.textContent = cropName;

            var sourceCell = document.createElement("td");
            var sourceGroup = document.createElement("div");
            sourceGroup.className = "agfields-mapping-source";
            [
                { value: "weppcloud", label: "WEPPcloud" },
                { value: "plant_file_db", label: "Plant file" }
            ].forEach(function (choice, choiceIndex) {
                var label = document.createElement("label");
                var input = document.createElement("input");
                input.type = "radio";
                input.name = "agfields_mapping_source_" + index;
                input.id = "agfields_mapping_source_" + index + "_" + choiceIndex;
                input.value = choice.value;
                input.dataset.action = "mapping-source";
                input.checked = source === choice.value;
                label.appendChild(input);
                label.appendChild(document.createTextNode(choice.label));
                sourceGroup.appendChild(label);
            });
            sourceCell.appendChild(sourceGroup);

            var managementCell = document.createElement("td");
            var selectLabel = document.createElement("label");
            var select = document.createElement("select");
            selectLabel.className = "wc-sr-only";
            selectLabel.htmlFor = "agfields_mapping_management_" + index;
            selectLabel.textContent = "Management for " + cropName;
            select.id = "agfields_mapping_management_" + index;
            select.className = "wc-field__control";
            select.dataset.action = "mapping-management";
            managementCell.appendChild(selectLabel);
            managementCell.appendChild(select);

            var statusCell = document.createElement("td");
            var status = document.createElement("span");
            status.dataset.role = "mapping-row-status";
            statusCell.appendChild(status);

            row.appendChild(cropCell);
            row.appendChild(sourceCell);
            row.appendChild(managementCell);
            row.appendChild(statusCell);
            populateManagementSelect(row);
            renderMappingRowStatus(row, rowData.status || "unmapped", rowData.message || (rowData.status === "ok" ? "Mapped" : "Unmapped"));
            return row;
        }

        function renderUnusedMappings(rows) {
            var details = controller.modalNodes.unused;
            var body = controller.modalNodes.unusedBody;
            if (!details || !body) {
                return;
            }
            body.textContent = "";
            if (!rows.length) {
                details.hidden = true;
                return;
            }
            details.hidden = false;
            var list = document.createElement("ul");
            list.className = "wc-list";
            rows.forEach(function (row) {
                var item = document.createElement("li");
                item.textContent = asString(row.crop_name) + " — " +
                    (asString(row.database) || "unmapped") +
                    (row.rotation_id ? ": " + row.rotation_id : "");
                list.appendChild(item);
            });
            body.appendChild(list);
        }

        function renderMappingModal(payload) {
            if (!collectModalNodes()) {
                return;
            }
            controller._mappingPayload = asObject(payload);
            var body = controller.modalNodes.tableBody;
            body.textContent = "";
            var rows = asArray(payload.rows).filter(function (row) { return row && row.used; });
            rows.sort(function (left, right) {
                return asString(left.crop_name).localeCompare(asString(right.crop_name));
            });
            rows.forEach(function (row, index) {
                body.appendChild(createMappingRow(row, index));
            });
            if (!rows.length) {
                var emptyRow = document.createElement("tr");
                var emptyCell = document.createElement("td");
                emptyCell.colSpan = 4;
                emptyCell.innerHTML = "<em>No crops are available until the field schema is confirmed.</em>";
                emptyRow.appendChild(emptyCell);
                body.appendChild(emptyRow);
            }
            renderUnusedMappings(asArray(payload.unused_mappings));
            var mapped = rows.filter(function (row) { return row.status === "ok"; }).length;
            setChip(
                controller.modalNodes.status,
                mapped + " of " + rows.length + " crops currently mapped.",
                mapped === rows.length && rows.length ? "success" : "warning"
            );
        }

        function loadMapping() {
            if (!collectModalNodes()) {
                return Promise.resolve(null);
            }
            setChip(controller.modalNodes.status, "Loading crop mappings…", "info");
            setButtonBusy(controller.modalNodes.saveButton, true, "Loading…");
            return authorizedGet("agfields/rotation-mapping").then(function (payload) {
                renderMappingModal(payload || {});
                emitter.emit("agfields:mapping:loaded", payload || {});
                return payload;
            }).catch(function (error) {
                handleRequestError("mapping-load", controller.modalNodes.status, "Could not load crop mappings", error);
                return null;
            }).finally(function () {
                setButtonBusy(controller.modalNodes.saveButton, false);
            });
        }

        function collectMappingRows() {
            var rows = [];
            if (controller.modalNodes.tableBody) {
                Array.prototype.forEach.call(
                    controller.modalNodes.tableBody.querySelectorAll("[data-crop-name]"),
                    function (row) {
                        rows.push({
                            crop_name: row.dataset.cropName || "",
                            database: row.dataset.source || null,
                            rotation_id: row.dataset.rotationId || null
                        });
                    }
                );
            }
            asArray(asObject(controller._mappingPayload).unused_mappings).forEach(function (row) {
                rows.push({
                    crop_name: row.crop_name,
                    database: row.database,
                    rotation_id: row.rotation_id
                });
            });
            return rows;
        }

        function renderMappingSaveErrors(error) {
            var payload = asObject(error && error.body);
            var errors = asArray(payload.errors);
            errors.forEach(function (item) {
                var path = asString(item.path);
                var cropName = path.indexOf("rows.") === 0 ? path.slice(5) : "";
                if (!cropName || !controller.modalNodes.tableBody) {
                    return;
                }
                var row = controller.modalNodes.tableBody.querySelector(
                    '[data-crop-name="' + escapeSelectorValue(cropName) + '"]'
                );
                if (row) {
                    renderMappingRowStatus(row, "error", item.message || "Invalid mapping.");
                }
            });
            setChip(
                controller.modalNodes.status,
                "Mapping save failed: " + resolveErrorMessage(error, "Review the highlighted rows."),
                "critical"
            );
        }

        function saveMapping() {
            var rows = collectMappingRows();
            setButtonBusy(controller.modalNodes.saveButton, true, "Saving…");
            setChip(controller.modalNodes.status, "Validating and saving mappings…", "info");
            authorizedPost("agfields/rotation-mapping", { rows: rows }).then(function (response) {
                setChip(controller.modalNodes.status, response.message || "Rotation mapping saved.", "success");
                emitter.emit("agfields:mapping:saved", asObject(response.result));
                if (window.ModalManager && typeof window.ModalManager.close === "function") {
                    window.ModalManager.close(controller.modal);
                }
                return controller.hydrate();
            }).catch(function (error) {
                if (isJobConflict(error)) {
                    handleRequestError("mapping-save", controller.modalNodes.status, "Could not save mapping", error);
                    return;
                }
                renderMappingSaveErrors(error);
                emitError("mapping-save", error);
            }).finally(function () {
                setButtonBusy(controller.modalNodes.saveButton, false);
            });
        }

        function runWepp() {
            var weppBin = controller.nodes.weppBinSelect ? controller.nodes.weppBinSelect.value.trim() : "";
            enqueue(
                "agfields/run-wepp",
                { wepp_bin: weppBin },
                "agfields_run_wepp",
                controller.nodes.runButton,
                "Queuing sub-field WEPP runs…",
                controller.nodes.runStatus,
                "agfields:wepp:queued"
            ).catch(function () {});
        }

        function clearRuns() {
            var now = Date.now();
            if (controller._clearArmedUntil < now) {
                controller._clearArmedUntil = now + 8000;
                setChip(
                    controller.nodes.runStatus,
                    "Click “Clear Previous Runs and Outputs” again within 8 seconds to confirm.",
                    "warning"
                );
                return;
            }
            controller._clearArmedUntil = 0;
            setButtonBusy(controller.nodes.clearRunsButton, true, "Clearing…");
            authorizedPost("agfields/clear", {}).then(function (response) {
                setChip(controller.nodes.runStatus, response.message || "AgFields runs and outputs cleared.", "success");
                emitter.emit("agfields:artifacts:cleared", response || {});
                return controller.hydrate();
            }).catch(function (error) {
                handleRequestError("clear", controller.nodes.runStatus, "Could not clear AgFields artifacts", error);
            }).finally(function () {
                setButtonBusy(controller.nodes.clearRunsButton, false);
            });
        }

        function overlayLoader(url, options) {
            var requestOptions = {
                method: "GET"
            };
            if (options && options.signal) {
                requestOptions.signal = options.signal;
            }
            return http.requestWithSessionToken(url, requestOptions).then(unwrapResult);
        }

        function resolveMap() {
            return window.MapController && typeof window.MapController.getInstance === "function"
                ? window.MapController.getInstance()
                : null;
        }

        function refreshOverlay() {
            var map = resolveMap();
            var url = urlFor("agfields/sub-fields.geojson");
            var layer = map && map.overlayMaps ? map.overlayMaps[LAYER_NAME] : null;
            if (layer && typeof layer.refresh === "function") {
                return layer.refresh(url);
            }
            return Promise.resolve(null);
        }

        function loadSubfieldsOverlay(options) {
            var settings = options || {};
            var map = resolveMap();
            if (!map || typeof map.addGeoJsonOverlay !== "function") {
                if (settings.announce) {
                    setChip(controller.nodes.subfieldsStatus, "Sub-fields are ready, but the map is not available yet.", "warning");
                }
                return Promise.resolve(false);
            }
            var url = urlFor("agfields/sub-fields.geojson");
            var layer = map.overlayMaps ? map.overlayMaps[LAYER_NAME] : null;
            if (!layer) {
                map.addGeoJsonOverlay({
                    layerName: LAYER_NAME,
                    mapKey: LAYER_KEY,
                    url: url,
                    loadJson: overlayLoader,
                    layerProps: {
                        filled: true,
                        stroked: true,
                        getFillColor: [36, 123, 160, 55],
                        getLineColor: [20, 84, 110, 220],
                        getLineWidth: 2,
                        lineWidthUnits: "pixels",
                        pickable: true
                    }
                });
                controller._overlayRegistered = true;
                if (settings.announce) {
                    setChip(controller.nodes.subfieldsStatus, "Sub-fields loaded on the map. Use the layer control to hide or show them.", "success");
                }
                emitter.emit("agfields:overlay:shown", { url: url, layerName: LAYER_NAME });
                return Promise.resolve(true);
            }
            controller._overlayRegistered = true;
            if (
                settings.forceVisible &&
                typeof map.hasLayer === "function" &&
                typeof map.addLayer === "function" &&
                !map.hasLayer(layer)
            ) {
                map.addLayer(layer, { skipRefresh: true });
            }
            if (settings.announce) {
                setChip(controller.nodes.subfieldsStatus, "Sub-fields loaded on the map. Use the layer control to hide or show them.", "success");
            }
            emitter.emit("agfields:overlay:shown", { url: url, layerName: LAYER_NAME });
            if (!settings.refresh) {
                return Promise.resolve(true);
            }
            return refreshOverlay().then(function () {
                return true;
            }).catch(function (error) {
                handleRequestError("overlay", controller.nodes.subfieldsStatus, "Could not refresh the sub-field map", error);
                return false;
            });
        }

        function resolveBootstrapJobs(context) {
            var helper = window.WCControllerBootstrap || null;
            var ctx = context || {};
            controller._bootstrapJobIds = {};
            JOB_KEYS.forEach(function (key) {
                var jobId = helper && typeof helper.resolveJobId === "function"
                    ? helper.resolveJobId(ctx, key)
                    : null;
                if (!jobId && ctx.jobIds) {
                    jobId = ctx.jobIds[key];
                }
                controller._bootstrapJobIds[key] = jobId || null;
            });
            for (var index = 0; index < JOB_KEYS.length; index += 1) {
                var key = JOB_KEYS[index];
                if (controller._bootstrapJobIds[key]) {
                    trackJob(key, controller._bootstrapJobIds[key]);
                    break;
                }
            }
        }

        controller.bootstrap = function bootstrap(context) {
            controller.context = context || {};
            if (!refreshDom()) {
                return controller;
            }
            resolveBootstrapJobs(controller.context);
            controller.hydrate();
            return controller;
        };

        controller.loadMapping = loadMapping;
        controller.renderState = function (state) {
            if (state) {
                controller.state = state;
            }
            renderState();
        };
        controller.loadSubfieldsOverlay = loadSubfieldsOverlay;

        return controller;
    }

    var api = {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        },
        detectCropYearPatterns: detectCropYearPatterns
    };

    if (typeof window !== "undefined") {
        window.AgFields = api;
    }
    return api;
})();

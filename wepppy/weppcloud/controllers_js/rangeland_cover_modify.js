/* ----------------------------------------------------------------------------
 * RangelandCoverModify
 * Doc: controllers_js/README.md — Rangeland Cover Modify Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var RangelandCoverModify = (function () {
    var instance;

    var EVENT_NAMES = [
        "rangeland:modify:loaded",
        "rangeland:modify:selection:changed",
        "rangeland:modify:run:started",
        "rangeland:modify:run:completed",
        "rangeland:modify:run:error",
        "rangeland:modify:error",
        "job:started",
        "job:progress",
        "job:completed",
        "job:error",
        "RANGELAND_COVER_MODIFY_TASK_COMPLETED"
    ];

    var DEFAULT_STYLE = {
        color: "white",
        opacity: 1,
        weight: 1,
        fillColor: "#FFEDA0",
        fillOpacity: 0.0
    };

    var SELECTED_STYLE = {
        color: "red",
        opacity: 1,
        weight: 2,
        fillOpacity: 0.0
    };

    var HOVER_STYLE = {
        weight: 2,
        color: "#666",
        dashArray: "",
        fillOpacity: 0.0
    };

    var COVER_FIELDS = [
        { name: "bunchgrass", selector: '[data-rcm-field="bunchgrass"]', label: "Bunch Grass" },
        { name: "forbs", selector: '[data-rcm-field="forbs"]', label: "Forbs/Annuals" },
        { name: "sodgrass", selector: '[data-rcm-field="sodgrass"]', label: "Sod Grass" },
        { name: "shrub", selector: '[data-rcm-field="shrub"]', label: "Shrub" },
        { name: "basal", selector: '[data-rcm-field="basal"]', label: "Basal Plant Cover" },
        { name: "rock", selector: '[data-rcm-field="rock"]', label: "Rock" },
        { name: "litter", selector: '[data-rcm-field="litter"]', label: "Litter" },
        { name: "cryptogams", selector: '[data-rcm-field="cryptogams"]', label: "Biological Crusts Cover" }
    ];

    var EMPTY_COVERS = {
        bunchgrass: "",
        forbs: "",
        sodgrass: "",
        shrub: "",
        basal: "",
        rock: "",
        litter: "",
        cryptogams: ""
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("RangelandCoverModify requires WCDom helpers.");
        }
        if (!forms || typeof forms.formToJSON !== "function") {
            throw new Error("RangelandCoverModify requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("RangelandCoverModify requires WCHttp helpers.");
        }
        if (!events || typeof events.useEventMap !== "function" || typeof events.createEmitter !== "function") {
            throw new Error("RangelandCoverModify requires WCEvents helpers.");
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
                if (element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                element.style.display = "none";
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
            var payload = body;
            if (payload.Error === undefined) {
                var fallback =
                    payload.detail ||
                    payload.message ||
                    payload.error ||
                    payload.errors;
                if (fallback !== undefined && fallback !== null) {
                    payload = Object.assign({}, payload, { Error: fallback });
                }
            }
            if (payload.StackTrace !== undefined || payload.Error !== undefined) {
                return payload;
            }
        } else if (typeof body === "string" && body) {
            return { Error: body };
        }

        if (error && typeof error === "object" && (error.Error !== undefined || error.StackTrace !== undefined)) {
            return error;
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            return { Error: detail || "Request failed" };
        }

        return { Error: (error && error.message) || "Request failed" };
    }

    function normalizeTopazId(value) {
        if (value === null || value === undefined) {
            return null;
        }
        var token = String(value).trim();
        if (!token) {
            return null;
        }
        var parsed = parseInt(token, 10);
        if (Number.isNaN(parsed)) {
            return null;
        }
        return String(parsed);
    }

    function parseTopazField(value) {
        if (value === null || value === undefined) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.map(normalizeTopazId).filter(Boolean);
        }
        var tokens = String(value).split(/[\s,]+/);
        return tokens.map(normalizeTopazId).filter(Boolean);
    }

    function sortIds(ids) {
        return ids.slice().sort(function (a, b) {
            var left = parseInt(a, 10);
            var right = parseInt(b, 10);
            if (Number.isNaN(left) || Number.isNaN(right)) {
                return a.localeCompare(b);
            }
            return left - right;
        });
    }

    function getMapController() {
        try {
            if (window.MapController && typeof window.MapController.getInstance === "function") {
                return window.MapController.getInstance();
            }
        } catch (err) {
            console.warn("RangelandCoverModify unable to load MapController", err);
        }
        return null;
    }

    function refreshDependentControllers() {
        try {
            if (window.SubcatchmentDelineation && typeof window.SubcatchmentDelineation.getInstance === "function") {
                var subCtrl = window.SubcatchmentDelineation.getInstance();
                if (subCtrl) {
                    try {
                        if (typeof subCtrl.getCmapMode === "function" && subCtrl.getCmapMode() === "rangeland_cover" &&
                            typeof subCtrl.setColorMap === "function") {
                            subCtrl.setColorMap("rangeland_cover");
                        }
                    } catch (err) {
                        console.warn("RangelandCoverModify unable to refresh Subcatchment color map", err);
                    }
                    if (typeof subCtrl.cmapRangelandCover === "function") {
                        subCtrl.cmapRangelandCover();
                    }
                }
            }
        } catch (err2) {
            console.warn("RangelandCoverModify: Subcatchment refresh failed", err2);
        }

        try {
            if (window.RangelandCover && typeof window.RangelandCover.getInstance === "function") {
                var rangelandController = window.RangelandCover.getInstance();
                if (rangelandController && typeof rangelandController.report === "function") {
                    rangelandController.report();
                }
            }
        } catch (err3) {
            console.warn("RangelandCoverModify: RangelandCover report refresh failed", err3);
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var modify = controlBase();
        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        var formElement = dom.ensureElement("#modify_rangeland_cover_form", "Modify Rangeland Cover form not found.");
        var statusElement = dom.qs("#modify_rangeland_cover_form #status");
        var stacktraceElement = dom.qs("#modify_rangeland_cover_form #stacktrace");
        var rqJobElement = dom.qs("#modify_rangeland_cover_form #rq_job");
        var toggleElement = dom.ensureElement(
            '#modify_rangeland_cover_form [data-rcm-action="toggle-selection"]',
            "Rangeland Cover Modify toggle checkbox not found."
        );
        var textareaElement = dom.ensureElement(
            '#modify_rangeland_cover_form [data-rcm-field="topaz-ids"]',
            "Rangeland Cover Modify Topaz field not found."
        );
        var submitElement = dom.ensureElement(
            '#modify_rangeland_cover_form [data-rcm-action="submit"]',
            "Rangeland Cover Modify submit button not found."
        );

        var coverElements = {};
        COVER_FIELDS.forEach(function (field) {
            coverElements[field.name] = dom.ensureElement(
                "#modify_rangeland_cover_form " + field.selector,
                "Rangeland Cover Modify field '" + field.name + "' not found."
            );
        });

        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);

        modify.form = formElement;
        modify.status = statusAdapter;
        modify.stacktrace = stacktraceAdapter;
        modify.rq_job = rqJobAdapter;
        modify.checkbox = toggleElement;
        modify.textarea = textareaElement;
        modify.coverElements = coverElements;
        modify.command_btn_id = submitElement.id || "btn_modify_rangeland_cover";
        modify.events = emitter;

        modify.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (!stacktraceElement) {
                return;
            }
            stacktraceElement.hidden = true;
            if (stacktraceElement.style) {
                stacktraceElement.style.display = "none";
            }
        };

        var selectionSet = new Set();
        var selectionModeActive = false;
        var suppressSelectionSync = false;
        var suppressToggleSync = false;
        var summaryRequestToken = 0;
        var geoJsonData = null;
        var geoLayer = null;
        var selectionRectangle = null;
        var dragStart = null;
        var layerIndex = Object.create(null);

        modify.selected = selectionSet;
        modify.data = geoJsonData;
        modify.glLayer = geoLayer;
        modify.selectionRect = selectionRectangle;

        function tryApplyValues(values) {
            if (!forms || !formElement) {
                return false;
            }
            var tagName = formElement.tagName ? String(formElement.tagName).toLowerCase() : "";
            if (tagName === "form") {
                try {
                    forms.applyValues(formElement, values);
                    return true;
                } catch (err) {
                    console.warn("RangelandCoverModify unable to apply values via WCForms", err);
                }
            }
            return false;
        }

        function updateSelectionRect(map, bounds) {
            if (!map || !bounds) {
                return;
            }
            if (!selectionRectangle) {
                selectionRectangle = L.rectangle(bounds, { color: "blue", weight: 1 }).addTo(map);
            } else if (typeof selectionRectangle.setBounds === "function") {
                selectionRectangle.setBounds(bounds);
            }
            modify.selectionRect = selectionRectangle;
        }

        function clearSelectionRect(map) {
            if (selectionRectangle && map) {
                map.removeLayer(selectionRectangle);
            }
            selectionRectangle = null;
            modify.selectionRect = null;
        }

        function applyStylesToLayer(id) {
            var key = String(id);
            var layer = layerIndex[key];
            if (!layer || typeof layer.setStyle !== "function") {
                return;
            }
            if (selectionSet.has(key)) {
                layer.setStyle(SELECTED_STYLE);
            } else {
                layer.setStyle(DEFAULT_STYLE);
            }
        }

        function refreshLayerStyles() {
            Object.keys(layerIndex).forEach(function (key) {
                applyStylesToLayer(key);
            });
        }

        function setTextareaValue(value) {
            if (tryApplyValues({ textarea_modify_rangeland_cover: value }) || !textareaElement) {
                return;
            }
            textareaElement.value = value;
        }

        function syncTextarea(ids) {
            suppressSelectionSync = true;
            try {
                var value = ids.length ? ids.join(", ") : "";
                setTextareaValue(value);
            } finally {
                suppressSelectionSync = false;
            }
        }

        function emitSelectionChanged(ids, source, silent) {
            if (silent) {
                return;
            }
            emitter.emit("rangeland:modify:selection:changed", {
                topazIds: ids.slice(),
                source: source || "unknown"
            });
        }

        function selectionKey(ids) {
            return ids.join("|");
        }

        var lastSummaryKey = "";

        function setCoverValues(values) {
            var payload = values || EMPTY_COVERS;
            COVER_FIELDS.forEach(function (field) {
                var element = coverElements[field.name];
                if (!element) {
                    return;
                }
                var value = payload[field.name];
                element.value = value === undefined || value === null ? "" : String(value);
            });
        }

        function loadCoverSummary(ids, options) {
            var normalized = Array.isArray(ids) ? ids.slice() : [];
            var key = selectionKey(normalized);
            if (!normalized.length) {
                lastSummaryKey = key;
                setCoverValues(EMPTY_COVERS);
                if (!options || !options.silent) {
                    emitter.emit("rangeland:modify:loaded", {
                        topazIds: [],
                        covers: EMPTY_COVERS
                    });
                }
                return Promise.resolve({ topazIds: [], covers: EMPTY_COVERS });
            }

            lastSummaryKey = key;
            var requestId = ++summaryRequestToken;

            return http.postJson(url_for_run("query/rangeland_cover/current_cover_summary/"), {
                topaz_ids: normalized
            }, { form: formElement }).then(function (response) {
                if (summaryRequestToken !== requestId) {
                    return null;
                }
                var body = response.body || {};
                setCoverValues(body);
                if (!options || !options.silent) {
                    emitter.emit("rangeland:modify:loaded", {
                        topazIds: normalized.slice(),
                        covers: body
                    });
                }
                return body;
            }).catch(function (error) {
                if (summaryRequestToken !== requestId) {
                    return null;
                }
                var payload = toResponsePayload(http, error);
                modify.pushResponseStacktrace(modify, payload);
                emitter.emit("rangeland:modify:error", {
                    context: "summary",
                    error: payload
                });
                throw error;
            });
        }

        function applySelection(ids, options) {
            var opts = options || {};
            var unique = [];
            var seen = Object.create(null);

            ids.forEach(function (value) {
                var normalized = normalizeTopazId(value);
                if (!normalized || seen[normalized]) {
                    return;
                }
                seen[normalized] = true;
                unique.push(normalized);
            });

            var sorted = sortIds(unique);
            var changed = sorted.length !== selectionSet.size;

            if (!changed) {
                sorted.some(function (id) {
                    if (!selectionSet.has(id)) {
                        changed = true;
                    }
                    return !selectionSet.has(id);
                });
            }

            if (changed) {
                selectionSet.clear();
                sorted.forEach(function (id) {
                    selectionSet.add(id);
                });
            }

            syncTextarea(sorted);
            refreshLayerStyles();
            emitSelectionChanged(sorted, opts.source, opts.silent);

            if (changed || lastSummaryKey !== selectionKey(sorted)) {
                loadCoverSummary(sorted, { silent: opts.silent });
            }

            return sorted;
        }

        function parseTextarea(value, options) {
            return applySelection(parseTopazField(value), options);
        }

        function ensureInitialSelection() {
            var initialValue = textareaElement ? textareaElement.value : "";
            if (initialValue) {
                parseTextarea(initialValue, { source: "initial", silent: true });
            } else {
                syncTextarea([]);
                loadCoverSummary([], { silent: true });
            }
        }

        function handleFeatureClick(topazId) {
            var ids = Array.from(selectionSet);
            var index = ids.indexOf(topazId);
            if (index !== -1) {
                ids.splice(index, 1);
            } else {
                ids.push(topazId);
            }
            applySelection(ids, { source: "map" });
        }

        function handleSubIntersection(topazIds) {
            var current = Array.from(selectionSet);
            (Array.isArray(topazIds) ? topazIds : []).forEach(function (value) {
                var normalized = normalizeTopazId(value);
                if (!normalized) {
                    return;
                }
                var idx = current.indexOf(normalized);
                if (idx === -1) {
                    current.push(normalized);
                } else {
                    current.splice(idx, 1);
                }
            });
            applySelection(current, { source: "box-select" });
        }

        function buildGeoLayerFeatures(data) {
            var map = getMapController();
            if (!map || !data || !data.features) {
                return;
            }
            layerIndex = Object.create(null);
            if (geoLayer) {
                map.removeLayer(geoLayer);
            }
            geoLayer = L.geoJSON(data.features, {
                style: DEFAULT_STYLE,
                onEachFeature: function (feature, layer) {
                    if (!feature || !feature.properties) {
                        return;
                    }
                    var topazId = normalizeTopazId(feature.properties.TopazID);
                    if (!topazId) {
                        return;
                    }
                    layerIndex[topazId] = layer;

                    layer.on({
                        mouseover: function () {
                            if (typeof layer.setStyle === "function") {
                                layer.setStyle(HOVER_STYLE);
                            }
                        },
                        mouseout: function () {
                            applyStylesToLayer(topazId);
                        },
                        click: function (event) {
                            if (event && event.originalEvent) {
                                event.originalEvent.preventDefault();
                                event.originalEvent.stopPropagation();
                            }
                            handleFeatureClick(topazId);
                        }
                    });

                    applyStylesToLayer(topazId);
                }
            });
            geoLayer.addTo(map);
            modify.glLayer = geoLayer;
        }

        function loadSubcatchments() {
            return http.getJson(url_for_run("resources/subcatchments.json"), {
                params: { _: Date.now() },
                form: formElement
            }).then(function (data) {
                geoJsonData = data || null;
                modify.data = geoJsonData;
                buildGeoLayerFeatures(geoJsonData);
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                modify.pushResponseStacktrace(modify, payload);
                emitter.emit("rangeland:modify:error", {
                    context: "subcatchments",
                    error: payload
                });
                suppressToggleSync = true;
                try {
                    if (!tryApplyValues({ checkbox_modify_rangeland_cover: false }) && toggleElement) {
                        toggleElement.checked = false;
                    }
                } finally {
                    suppressToggleSync = false;
                }
                setSelectionMode(false);
            });
        }

        function onMapMouseDown(event) {
            if (!selectionModeActive) {
                return;
            }
            dragStart = event && event.latlng ? event.latlng : null;
        }

        function onMapMouseMove(event) {
            if (!selectionModeActive) {
                return;
            }
            var map = getMapController();
            if (!map) {
                return;
            }
            if (!dragStart) {
                clearSelectionRect(map);
                return;
            }
            if (!event || !event.latlng) {
                return;
            }
            var bounds = L.latLngBounds(dragStart, event.latlng);
            updateSelectionRect(map, bounds);
        }

        function onMapMouseUp(event) {
            if (!selectionModeActive) {
                dragStart = null;
                return;
            }
            var map = getMapController();
            if (!map) {
                dragStart = null;
                return;
            }
            if (!dragStart || !event || !event.latlng) {
                dragStart = null;
                clearSelectionRect(map);
                return;
            }
            var ll0 = dragStart;
            var ll1 = event.latlng;
            dragStart = null;

            if (ll0.lat === ll1.lat && ll0.lng === ll1.lng) {
                clearSelectionRect(map);
                return;
            }

            var bounds = L.latLngBounds(ll0, ll1);
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [sw.lng, sw.lat, ne.lng, ne.lat];

            http.postJson(url_for_run("tasks/sub_intersection/"), { extent: extent }, { form: formElement })
                .then(function (response) {
                    handleSubIntersection(response.body);
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    modify.pushResponseStacktrace(modify, payload);
                    emitter.emit("rangeland:modify:error", {
                        context: "box-select",
                        error: payload
                    });
                })
                .then(function () {
                    clearSelectionRect(map);
                });
        }

        function attachMapListeners() {
            var map = getMapController();
            if (!map) {
                return;
            }
            map.boxZoom.disable();
            map.on("mousedown", onMapMouseDown);
            map.on("mousemove", onMapMouseMove);
            map.on("mouseup", onMapMouseUp);
        }

        function detachMapListeners() {
            var map = getMapController();
            if (!map) {
                return;
            }
            map.boxZoom.enable();
            map.off("mousedown", onMapMouseDown);
            map.off("mousemove", onMapMouseMove);
            map.off("mouseup", onMapMouseUp);
            if (geoLayer) {
                map.removeLayer(geoLayer);
            }
            geoLayer = null;
            modify.glLayer = null;
            layerIndex = Object.create(null);
            clearSelectionRect(map);
        }

        function setSelectionMode(enabled) {
            var targetState = Boolean(enabled);
            if (selectionModeActive === targetState) {
                return;
            }
            selectionModeActive = targetState;
            if (selectionModeActive) {
                attachMapListeners();
                if (geoJsonData) {
                    buildGeoLayerFeatures(geoJsonData);
                } else {
                    loadSubcatchments();
                }
            } else {
                detachMapListeners();
            }
        }

        function setStatusMessage(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.textContent = message;
            }
        }

        function readCoverValues() {
            var covers = {};
            var invalidFields = [];
            var outOfRangeFields = [];
            COVER_FIELDS.forEach(function (field) {
                var element = coverElements[field.name];
                if (!element) {
                    return;
                }
                var raw = element.value === undefined || element.value === null ? "" : String(element.value).trim();
                if (raw === "") {
                    invalidFields.push(field);
                    return;
                }
                var value = Number(raw);
                if (!Number.isFinite(value)) {
                    invalidFields.push(field);
                    return;
                }
                if (value < 0 || value > 100) {
                    outOfRangeFields.push({ field: field, value: value });
                }
                covers[field.name] = value;
            });

            return { covers: covers, invalidFields: invalidFields, outOfRangeFields: outOfRangeFields };
        }

        function buildValidationError(invalid, outOfRange) {
            if (invalid.length) {
                return "Provide numeric cover values for: " + invalid.map(function (field) {
                    return field.label;
                }).join(", ") + ".";
            }
            if (outOfRange.length) {
                return "Cover values must be between 0 and 100 (%s).".replace("%s", outOfRange.map(function (entry) {
                    return entry.field.label + " (" + entry.value + ")";
                }).join(", "));
            }
            return null;
        }

        function submitModification() {
            var taskMsg = "Modifying rangeland cover";
            setStatusMessage(taskMsg + "...");
            modify.hideStacktrace();

            var ids = Array.from(selectionSet);
            if (!ids.length) {
                var payloadNoSelection = { Error: "Select at least one subcatchment before modifying cover values." };
                modify.pushResponseStacktrace(modify, payloadNoSelection);
                emitter.emit("rangeland:modify:run:error", {
                    topazIds: ids.slice(),
                    error: payloadNoSelection,
                    stage: "validation"
                });
                setStatusMessage(taskMsg + "... Failed");
                return;
            }

            var coversResult = readCoverValues();
            var validationError = buildValidationError(coversResult.invalidFields, coversResult.outOfRangeFields);
            if (validationError) {
                var payloadValidation = { Error: validationError };
                modify.pushResponseStacktrace(modify, payloadValidation);
                emitter.emit("rangeland:modify:run:error", {
                    topazIds: ids.slice(),
                    error: payloadValidation,
                    stage: "validation"
                });
                setStatusMessage(taskMsg + "... Failed");
                return;
            }

            emitter.emit("rangeland:modify:run:started", {
                topazIds: ids.slice(),
                covers: Object.assign({}, coversResult.covers)
            });
            modify.triggerEvent("job:started", {
                task: "rangeland:modify",
                payload: {
                    topazIds: ids.slice(),
                    covers: Object.assign({}, coversResult.covers)
                }
            });

            http.postJson(url_for_run("tasks/modify_rangeland_cover/"), {
                topaz_ids: ids,
                covers: coversResult.covers
            }, { form: formElement }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true || payload.success === true) {
                    applySelection([], { source: "modify", silent: true });

                    suppressToggleSync = true;
                    try {
                        if (!tryApplyValues({ checkbox_modify_rangeland_cover: false }) && toggleElement) {
                            toggleElement.checked = false;
                        }
                        if (toggleElement) {
                            toggleElement.checked = false;
                        }
                    } finally {
                        suppressToggleSync = false;
                    }

                    setSelectionMode(false);
                    setStatusMessage(taskMsg + "... Success");
                    loadCoverSummary([], { silent: true });

                    emitter.emit("rangeland:modify:run:completed", {
                        topazIds: ids.slice(),
                        covers: Object.assign({}, coversResult.covers),
                        response: payload
                    });
                    modify.triggerEvent("job:completed", {
                        task: "rangeland:modify",
                        payload: {
                            topazIds: ids.slice(),
                            covers: Object.assign({}, coversResult.covers)
                        },
                        response: payload
                    });
                    modify.triggerEvent("RANGELAND_COVER_MODIFY_TASK_COMPLETED", {
                        topazIds: ids.slice(),
                        covers: Object.assign({}, coversResult.covers)
                    });
                } else {
                    modify.pushResponseStacktrace(modify, payload);
                    emitter.emit("rangeland:modify:run:error", {
                        topazIds: ids.slice(),
                        error: payload,
                        stage: "response"
                    });
                    modify.triggerEvent("job:error", {
                        task: "rangeland:modify",
                        payload: {
                            topazIds: ids.slice(),
                            covers: Object.assign({}, coversResult.covers)
                        },
                        error: payload
                    });
                    setStatusMessage(taskMsg + "... Failed");
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                modify.pushResponseStacktrace(modify, payload);
                emitter.emit("rangeland:modify:run:error", {
                    topazIds: ids.slice(),
                    error: payload,
                    stage: "request"
                });
                modify.triggerEvent("job:error", {
                    task: "rangeland:modify",
                    payload: {
                        topazIds: ids.slice(),
                        covers: Object.assign({}, coversResult.covers)
                    },
                    error: payload
                });
                setStatusMessage(taskMsg + "... Failed");
            });
        }

        var baseTriggerEvent = modify.triggerEvent.bind(modify);
        modify.triggerEvent = function (eventName, payload) {
            if (EVENT_NAMES.indexOf(eventName) !== -1) {
                emitter.emit(eventName, payload);
            }
            if (eventName === "RANGELAND_COVER_MODIFY_TASK_COMPLETED") {
                try {
                    refreshDependentControllers();
                } catch (err) {
                    console.warn("RangelandCoverModify: dependent controller refresh failed", err);
                }
            }
            baseTriggerEvent(eventName, payload);
        };

        dom.delegate(formElement, "click", '[data-rcm-action="submit"]', function (event) {
            event.preventDefault();
            submitModification();
        });

        dom.delegate(formElement, "change", '[data-rcm-action="toggle-selection"]', function (event, matched) {
            if (suppressToggleSync) {
                return;
            }
            var checkbox = matched || event.target;
            setSelectionMode(Boolean(checkbox && checkbox.checked));
        });

        dom.delegate(formElement, "input", '[data-rcm-field="topaz-ids"]', function (event, matched) {
            if (suppressSelectionSync) {
                return;
            }
            var value = matched ? matched.value : "";
            parseTextarea(value, { source: "manual" });
        });

        ensureInitialSelection();
        if (toggleElement && toggleElement.checked) {
            setSelectionMode(true);
        }

        return modify;
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
    globalThis.RangelandCoverModify = RangelandCoverModify;
}

/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

function flushPromises() {
    return Promise.resolve().then(() => Promise.resolve());
}

function buildFixtureHtml() {
    const catalogPayload = {
        metadata: { catalog_version: "2026.03.26", schema_version: "1" },
        family_order: [
            "watershed",
            "wepp",
            "omni_scenarios",
            "swat_interchange"
        ],
        family_labels: {
            watershed: "Watershed",
            wepp: "WEPP",
            omni_scenarios: "Omni Scenarios",
            swat_interchange: "SWAT Interchange"
        },
        layers: [
            {
                layer_id: "watershed.subcatchments",
                label: "Subcatchments",
                family: "watershed",
                family_label: "Watershed",
                scope_class: "scope_invariant",
                geometry_type: "polygon",
                temporal_modes: [],
                selector_requirements: [],
                columns: [
                    { column_id: "TopazID", label: "Topaz ID", description: "Primary watershed identifier", display_unit: "non-unitized", required: true, default_selected: true },
                    { column_id: "Name", label: "Name", description: "Subcatchment label", display_unit: "non-unitized", required: false, default_selected: true }
                ],
                required_columns: ["TopazID"]
            },
            {
                layer_id: "wepp.summary.hillslopes",
                label: "WEPP Hillslopes",
                family: "wepp",
                family_label: "WEPP",
                scope_class: "scope_aware",
                geometry_type: "polygon",
                temporal_modes: ["annual_average", "yearly", "event"],
                selector_requirements: [],
                columns: [
                    { column_id: "topaz_id", label: "Topaz ID", description: "Primary hillslope identifier", display_unit: "non-unitized", required: true, default_selected: true },
                    { column_id: "runoff_mm", label: "Runoff", description: "Annual runoff depth", display_unit: "mm", required: false, default_selected: true },
                    { column_id: "sediment_yield_kg_ha", label: "Sediment Yield", description: "Annual sediment delivery", display_unit: "kg/ha", required: false, default_selected: true }
                ],
                required_columns: ["topaz_id"]
            },
            {
                layer_id: "omni.scenarios.hillslopes",
                label: "Omni Scenario Boundaries",
                family: "omni_scenarios",
                family_label: "Omni Scenarios",
                scope_class: "scope_invariant",
                geometry_type: "polygon",
                temporal_modes: [],
                selector_requirements: ["omni_scenario"],
                columns: [{ column_id: "topaz_id", label: "Topaz ID", display_unit: "non-unitized", required: true, default_selected: true }],
                required_columns: ["topaz_id"]
            },
            {
                layer_id: "swat.interchange.table",
                label: "SWAT Interchange Table",
                family: "swat_interchange",
                family_label: "SWAT Interchange",
                scope_class: "scope_invariant",
                geometry_type: "table",
                temporal_modes: [],
                selector_requirements: ["swat"],
                columns: [{ column_id: "subbasin", label: "Subbasin", display_unit: "non-unitized", required: true, default_selected: true }],
                required_columns: ["subbasin"]
            },
            {
                layer_id: "wepp.temporal.events",
                label: "WEPP Events",
                family: "wepp",
                family_label: "WEPP",
                scope_class: "scope_aware",
                geometry_type: "polygon",
                temporal_modes: ["event"],
                selector_requirements: [],
                columns: [
                    { column_id: "topaz_id", label: "Topaz ID", display_unit: "non-unitized", required: true, default_selected: true },
                    { column_id: "hill_sediment_tonnes", label: "Hill Sediment", display_unit: "tonnes", required: false, default_selected: true }
                ],
                required_columns: ["topaz_id"]
            },
            {
                layer_id: "wepp.interchange.loss_all_years_hill",
                label: "WEPP Loss All Years Hill",
                family: "wepp",
                family_label: "WEPP",
                scope_class: "scope_aware",
                geometry_type: "polygon",
                temporal_modes: ["yearly"],
                selector_requirements: [],
                columns: [
                    { column_id: "topaz_id", label: "Topaz ID", display_unit: "non-unitized", required: true, default_selected: true },
                    { column_id: "soil_loss_kg", label: "Soil Loss", display_unit: "kg", required: false, default_selected: true }
                ],
                required_columns: ["topaz_id"]
            }
        ],
        load_error: null
    };

    const bootstrapPayload = {
        defaults: {
            format: "geopackage",
            units: "project",
            crs: "wgs",
            output_scopes: ["baseline"]
        },
        profiles: {
            gpkg_adjacent: {
                format: "geopackage",
                units: "project",
                crs: "wgs",
                output_scopes: ["baseline"],
                swat_run_id: "latest",
                layers: ["watershed.subcatchments", "wepp.summary.hillslopes"]
            }
        },
        omni: {
            scenarios: [{ id: "uniform_low", label: "Uniform Low" }],
            contrasts: [{ id: "mulch_vs_control", label: "Mulch vs Control" }]
        },
        swat: {
            preferred_run_id: "run_001",
            runs: [{ id: "run_001", label: "run_001" }],
            tables_by_run: { run_001: ["hru", "rch"] },
            all_tables: ["hru", "rch"]
        },
        discovery: {
            roads_scope_available: true,
            available_layer_ids: [
                "watershed.subcatchments",
                "wepp.summary.hillslopes",
                "wepp.temporal.events",
                "wepp.interchange.loss_all_years_hill",
                "omni.scenarios.hillslopes",
                "swat.interchange.table"
            ],
            available_families: ["watershed", "wepp", "omni_scenarios", "swat_interchange"]
        }
    };

    return `
        <form id="features_export_form" data-features-export-root>
            <div id="features_export_rq_job"></div>
            <span id="features_export_braille"></span>
            <div
                data-features-export-config
                data-features-export-job-key="run_features_export"
                data-features-export-channel="features_export"
                data-features-export-submit-url="/rq-engine/api/runs/test-run/test-cfg/export/features"
                data-features-export-download-url-template="/runs/test-run/test-cfg/download/__ARTIFACT_RELPATH__"
                data-features-export-utm-available="true"
                data-features-export-default-format="geopackage"
                data-features-export-default-units="project"
                data-features-export-default-crs="wgs"
                data-features-export-default-profile-key="gpkg_adjacent"
                hidden></div>
            <script type="application/json" id="features_export_catalog_data" data-features-export-catalog>${JSON.stringify(catalogPayload)}</script>
            <script type="application/json" id="features_export_bootstrap_data" data-features-export-bootstrap>${JSON.stringify(bootstrapPayload)}</script>

            <section data-features-export-group="settings">
                <button type="button" data-features-export-action="load-defaults">Load Defaults</button>
                <button type="button" data-features-export-action="clear-selection">Clear selection</button>
                <select data-features-export-field="format">
                    <option value="geopackage" selected>GeoPackage</option>
                    <option value="geodatabase">Geodatabase</option>
                    <option value="geojson">GeoJSON</option>
                    <option value="parquet">Parquet</option>
                    <option value="csv">CSV</option>
                </select>
                <div data-features-export-tabular-options hidden>
                    <label><input type="checkbox" data-features-export-field="tabular-concatenate-tables">Concatenate tables</label>
                    <label><input type="radio" data-features-export-field="tabular-temporal-layout" name="fx_tabular_temporal_layout" value="wide" checked>wide</label>
                    <label><input type="radio" data-features-export-field="tabular-temporal-layout" name="fx_tabular_temporal_layout" value="long">long</label>
                </div>
                <label><input type="radio" data-features-export-field="units" name="fx_units" value="project" checked>project</label>
                <label><input type="radio" data-features-export-field="units" name="fx_units" value="si">si</label>
                <label><input type="radio" data-features-export-field="units" name="fx_units" value="english">english</label>
                <div data-features-export-geometry-options>
                    <label><input type="radio" data-features-export-field="crs" name="fx_crs" value="wgs" checked>wgs</label>
                    <label><input type="radio" data-features-export-field="crs" name="fx_crs" value="utm">utm</label>
                </div>
                <p data-features-export-region="packaging-hint"></p>
            </section>

            <section data-features-export-group="summary">
                <p data-features-export-region="selected-count"></p>
                <p data-features-export-region="family-counts"></p>
                <p data-features-export-region="scope-aware-count"></p>
                <p data-features-export-region="temporal-capable-count"></p>
                <div
                    class="wc-alert wc-alert--info"
                    data-features-export-validation-alert
                    data-validation-state="pending"
                    role="status"
                    aria-live="polite">
                    <p data-features-export-region="validation" class="wc-alert__body"></p>
                </div>
                <p data-features-export-region="summary-warnings"></p>
            </section>

            <section data-features-export-group="catalog">
                <div id="features_export_catalog_list"></div>
            </section>

            <section data-features-export-group="scopes" hidden>
                <label><input type="checkbox" data-features-export-field="output-scope" value="baseline" checked>baseline</label>
                <label><input type="checkbox" data-features-export-field="output-scope" value="roads">roads</label>
                <p data-features-export-region="roads-scope-note"></p>
            </section>

            <section data-features-export-group="temporal" hidden>
                <div data-features-export-temporal-year-options hidden>
                    <select data-features-export-field="temporal-year-selection">
                        <option value="all" selected>all</option>
                        <option value="custom">custom</option>
                    </select>
                    <div data-features-export-temporal-custom-wrap hidden>
                        <input type="text" data-features-export-field="temporal-exclude-year-indices">
                    </div>
                </div>

                <div data-features-export-temporal-event-options hidden>
                    <label><input type="radio" data-features-export-field="temporal-event-selector" name="fx_temporal_event_selector" value="date">date</label>
                    <label><input type="radio" data-features-export-field="temporal-event-selector" name="fx_temporal_event_selector" value="return_period">rp</label>
                    <div data-features-export-temporal-dates-wrap hidden>
                        <textarea data-features-export-field="temporal-event-dates"></textarea>
                    </div>
                    <div data-features-export-temporal-return-periods-wrap hidden>
                        <textarea data-features-export-field="temporal-event-return-periods"></textarea>
                    </div>
                </div>
            </section>

            <section data-features-export-group="omni" hidden>
                <h3 data-features-export-region="omni-title">Omni Selector</h3>
                <div data-features-export-omni-scenario-wrap hidden>
                    <button type="button" data-features-export-action="omni-select-all" data-omni-target="scenarios">Select All</button>
                    <button type="button" data-features-export-action="omni-unselect-all" data-omni-target="scenarios">Unselect All</button>
                    <label><input type="checkbox" data-features-export-field="scenario" value="uniform_low">Uniform Low</label>
                </div>
                <div data-features-export-omni-contrast-wrap hidden>
                    <button type="button" data-features-export-action="omni-select-all" data-omni-target="contrasts">Select All</button>
                    <button type="button" data-features-export-action="omni-unselect-all" data-omni-target="contrasts">Unselect All</button>
                    <label><input type="checkbox" data-features-export-field="contrast-id" value="mulch_vs_control">Mulch vs Control</label>
                </div>
            </section>

            <section data-features-export-group="swat" hidden>
                <select data-features-export-field="swat-run-id">
                    <option value="latest">latest</option>
                    <option value="run_001" selected>run_001</option>
                </select>
                <select data-features-export-field="swat-table-mode">
                    <option value="all" selected>all</option>
                    <option value="include">include</option>
                    <option value="exclude">exclude</option>
                </select>
                <div id="features_export_swat_tables"></div>
            </section>

            <section data-features-export-group="actions">
                <button id="btn_run_features_export" type="submit" data-features-export-action="submit" disabled>Export Features</button>
                <p id="hint_run_features_export" data-job-hint></p>
            </section>

            <aside id="features_export_results_panel" data-features-export-results>
                <p id="features_export_result_state" data-features-export-region="result-state">Idle</p>
                <div data-features-export-region="download"></div>
                <div data-features-export-region="artifact-meta"></div>
                <ul data-features-export-region="warnings"></ul>
            </aside>

            <section id="features_export_status_panel" class="wc-status-panel" data-status-panel aria-live="polite">
                <p id="features_export_message" data-features-export-region="message">Waiting for export selection.</p>
                <div id="features_export_status_log" class="wc-status-panel__log" data-status-log role="log"></div>
            </section>

            <details id="features_export_stacktrace_panel" data-stacktrace-panel hidden>
                <summary>Stack trace</summary>
                <pre id="features_export_stacktrace" data-stacktrace-body></pre>
            </details>
        </form>
    `;
}

describe("FeaturesExport controller", () => {
    let controller;
    let baseInstance;
    let httpMock;

    beforeEach(async () => {
        jest.resetModules();

        window.runid = "test-run";
        window.runId = "test-run";
        window.config = "test-cfg";

        await import("../dom.js");
        await import("../events.js");
        await import("../forms.js");

        httpMock = {
            request: jest.fn(() => Promise.resolve({ body: { result: {} } })),
            requestWithSessionToken: jest.fn(() => Promise.resolve({ body: { result: {} } })),
            postJsonWithSessionToken: jest.fn(() => Promise.resolve({ body: { job_id: "job-101" } })),
            postJson: jest.fn(() => Promise.resolve({ body: { job_id: "job-101" } })),
            isHttpError: jest.fn((error) => Boolean(error && error.isHttpError))
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance } = createControlBaseStub({
            set_rq_job_id: jest.fn((self, jobId) => {
                self.rq_job_id = jobId || null;
                var hint = document.getElementById("hint_run_features_export");
                if (hint) {
                    hint.textContent = jobId ? "job_id: " + jobId : "";
                }
            }),
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        await import("../features_export.js");
        controller = window.FeaturesExport.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        delete window.FeaturesExport;
        delete global.WCHttp;
        delete global.controlBase;
        delete window.runid;
        delete window.runId;
        delete window.config;
        delete window.site_prefix;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        delete window.WCControllerBootstrap;
    });

    test("bootstrap is resilient before DOM insertion and re-hydrates after dynamic insertion", () => {
        controller.bootstrap({});

        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        expect(baseInstance.attach_status_stream).toHaveBeenCalledWith(
            controller,
            expect.objectContaining({ channel: "features_export" })
        );
        expect(document.querySelectorAll("[data-features-export-layer]").length).toBeGreaterThan(0);
    });

    test("load defaults applies gpkg_adjacent profile and does not auto-submit", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var defaultsEvents = [];
        controller.events.on("features_export:defaults:loaded", (payload) => defaultsEvents.push(payload));

        document
            .querySelector('[data-features-export-action="load-defaults"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(document.querySelector('[data-features-export-field="format"]').value).toBe("geopackage");
        expect(document.querySelector('[data-features-export-field="units"][value="project"]').checked).toBe(true);
        expect(document.querySelector('[data-features-export-field="crs"][value="wgs"]').checked).toBe(true);
        expect(defaultsEvents).toHaveLength(1);
        expect(defaultsEvents[0]).toEqual(expect.objectContaining({
            profileKey: "gpkg_adjacent",
            selectedLayerIds: ["watershed.subcatchments", "wepp.summary.hillslopes"]
        }));
        expect(httpMock.postJsonWithSessionToken).not.toHaveBeenCalled();
    });

    test("year selection remains visible even when no temporal layers are selected", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var yearWrap = document.querySelector("[data-features-export-temporal-year-options]");
        expect(yearWrap).not.toBeNull();
        expect(yearWrap.hidden).toBe(false);

        document
            .querySelector('[data-features-export-action="clear-selection"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        expect(yearWrap.hidden).toBe(false);
    });

    test("progressive disclosure and validation gating respond to selected families", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var scopesGroup = document.querySelector('[data-features-export-group="scopes"]');
        var temporalGroup = document.querySelector('[data-features-export-group="temporal"]');
        var submitButton = document.getElementById("btn_run_features_export");

        expect(scopesGroup.hidden).toBe(false);
        expect(temporalGroup.hidden).toBe(false);
        expect(submitButton.disabled).toBe(false);

        var weppTemporalMode = document.querySelector('[data-features-export-field="layer-temporal-mode"][data-layer-id="wepp.summary.hillslopes"]');
        weppTemporalMode.value = "event";
        weppTemporalMode.dispatchEvent(new Event("change", { bubbles: true }));
        expect(submitButton.disabled).toBe(true);

        var eventSelectorDate = document.querySelector('[data-features-export-field="temporal-event-selector"][value="date"]');
        eventSelectorDate.checked = true;
        eventSelectorDate.dispatchEvent(new Event("change", { bubbles: true }));
        document.querySelector('[data-features-export-field="temporal-event-dates"]').value = "2025-01-01";
        document
            .querySelector('[data-features-export-field="temporal-event-dates"]')
            .dispatchEvent(new Event("input", { bubbles: true }));
        expect(submitButton.disabled).toBe(false);

        document
            .querySelector('[data-features-export-action="clear-selection"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        var omniLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="omni.scenarios.hillslopes"]');
        omniLayer.checked = true;
        omniLayer.dispatchEvent(new Event("change", { bubbles: true }));
        expect(document.querySelector('[data-features-export-group="omni"]').hidden).toBe(false);
        expect(submitButton.disabled).toBe(true);
        var scenarioCheckbox = document.querySelector('[data-features-export-field="scenario"][value="uniform_low"]');
        scenarioCheckbox.checked = true;
        scenarioCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
        expect(submitButton.disabled).toBe(false);

        document
            .querySelector('[data-features-export-action="clear-selection"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        var swatLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="swat.interchange.table"]');
        swatLayer.checked = true;
        swatLayer.dispatchEvent(new Event("change", { bubbles: true }));
        expect(document.querySelector('[data-features-export-group="swat"]').hidden).toBe(false);

        await flushPromises();
    });

    test("validation alert uses distinct ready and error states", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var alertNode = document.querySelector("[data-features-export-validation-alert]");
        expect(alertNode.classList.contains("wc-alert--error")).toBe(true);
        expect(alertNode.getAttribute("data-validation-state")).toBe("error");
        expect(alertNode.getAttribute("role")).toBe("alert");
        expect(alertNode.getAttribute("aria-live")).toBe("assertive");
        expect(document.querySelector('[data-features-export-region="validation"]').textContent)
            .toContain("Select at least one layer.");

        document
            .querySelector('[data-features-export-action="load-defaults"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flushPromises();

        expect(alertNode.classList.contains("wc-alert--success")).toBe(true);
        expect(alertNode.getAttribute("data-validation-state")).toBe("ready");
        expect(alertNode.getAttribute("role")).toBe("status");
        expect(alertNode.getAttribute("aria-live")).toBe("polite");
        expect(document.querySelector('[data-features-export-region="validation"]').textContent)
            .toContain("Ready to export.");
    });

    test("tabular options are format-dependent and included in csv/parquet payloads", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var tabularWrap = document.querySelector("[data-features-export-tabular-options]");
        var geometryWrap = document.querySelector("[data-features-export-geometry-options]");
        expect(tabularWrap.hidden).toBe(true);
        expect(geometryWrap.hidden).toBe(false);

        var formatSelect = document.querySelector('[data-features-export-field="format"]');
        formatSelect.value = "csv";
        formatSelect.dispatchEvent(new Event("change", { bubbles: true }));
        expect(tabularWrap.hidden).toBe(false);
        expect(geometryWrap.hidden).toBe(true);

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var temporalMode = document.querySelector('[data-features-export-field="layer-temporal-mode"][data-layer-id="wepp.summary.hillslopes"]');
        temporalMode.value = "yearly";
        temporalMode.dispatchEvent(new Event("change", { bubbles: true }));

        var concatenateCheckbox = document.querySelector('[data-features-export-field="tabular-concatenate-tables"]');
        concatenateCheckbox.checked = true;
        concatenateCheckbox.dispatchEvent(new Event("change", { bubbles: true }));

        var longRadio = document.querySelector('[data-features-export-field="tabular-temporal-layout"][value="long"]');
        longRadio.checked = true;
        longRadio.dispatchEvent(new Event("change", { bubbles: true }));

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test-run/test-cfg/export/features",
            expect.objectContaining({
                format: "csv",
                tabular: {
                    concatenate_tables: true,
                    temporal_layout: "long"
                }
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
    });

    test("tabular formats do not require CRS and omit CRS from payload", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        document.querySelectorAll('[data-features-export-field="crs"]').forEach((node) => {
            node.checked = false;
        });

        var formatSelect = document.querySelector('[data-features-export-field="format"]');
        formatSelect.value = "csv";
        formatSelect.dispatchEvent(new Event("change", { bubbles: true }));

        var layer = document.querySelector('[data-features-export-action="toggle-layer"][value="watershed.subcatchments"]');
        layer.checked = true;
        layer.dispatchEvent(new Event("change", { bubbles: true }));

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledTimes(1);
        var payload = httpMock.postJsonWithSessionToken.mock.calls[0][1];
        expect(payload.format).toBe("csv");
        expect(Object.prototype.hasOwnProperty.call(payload, "crs")).toBe(false);
    });

    test("tabular long layout blocks mixed event and yearly temporal selections", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var formatSelect = document.querySelector('[data-features-export-field="format"]');
        formatSelect.value = "csv";
        formatSelect.dispatchEvent(new Event("change", { bubbles: true }));

        var eventLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.temporal.events"]');
        var yearlyLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.interchange.loss_all_years_hill"]');
        eventLayer.checked = true;
        yearlyLayer.checked = true;
        eventLayer.dispatchEvent(new Event("change", { bubbles: true }));
        yearlyLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var longRadio = document.querySelector('[data-features-export-field="tabular-temporal-layout"][value="long"]');
        longRadio.checked = true;
        longRadio.dispatchEvent(new Event("change", { bubbles: true }));

        var eventSelectorDate = document.querySelector('[data-features-export-field="temporal-event-selector"][value="date"]');
        eventSelectorDate.checked = true;
        eventSelectorDate.dispatchEvent(new Event("change", { bubbles: true }));
        var eventDates = document.querySelector('[data-features-export-field="temporal-event-dates"]');
        eventDates.value = "2015-01-15";
        eventDates.dispatchEvent(new Event("input", { bubbles: true }));

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).not.toHaveBeenCalled();
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            controller,
            expect.objectContaining({
                error: expect.objectContaining({
                    message: "Features export form validation failed."
                })
            })
        );
        expect(document.querySelector('[data-features-export-region="validation"]').textContent)
            .toContain("Tabular long layout does not support mixing event and yearly temporal modes.");
    });

    test("payload includes per-layer temporal modes and column selection", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var temporalSelect = document.querySelector('[data-features-export-field="layer-temporal-mode"][data-layer-id="wepp.summary.hillslopes"]');
        temporalSelect.value = "yearly";
        temporalSelect.dispatchEvent(new Event("change", { bubbles: true }));

        var sedimentColumn = document.querySelector(
            '[data-features-export-action="toggle-column"][data-layer-id="wepp.summary.hillslopes"][data-column-id="sediment_yield_kg_ha"]'
        );
        sedimentColumn.checked = false;
        sedimentColumn.dispatchEvent(new Event("change", { bubbles: true }));

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test-run/test-cfg/export/features",
            expect.objectContaining({
                layers: ["wepp.summary.hillslopes"],
                temporal: expect.objectContaining({
                    layer_modes: {
                        "wepp.summary.hillslopes": "yearly"
                    }
                }),
                column_selection: expect.objectContaining({
                    "wepp.summary.hillslopes": expect.objectContaining({
                        include: ["topaz_id", "runoff_mm"]
                    })
                })
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
    });

    test("changing layer temporal mode does not replace controls or trigger form submit", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var temporalSelect = document.querySelector(
            '[data-features-export-field="layer-temporal-mode"][data-layer-id="wepp.summary.hillslopes"]'
        );
        expect(temporalSelect).not.toBeNull();

        var form = document.getElementById("features_export_form");
        var submitCount = 0;
        form.addEventListener("submit", function () {
            submitCount += 1;
        });

        temporalSelect.value = "yearly";
        temporalSelect.dispatchEvent(new Event("change", { bubbles: true }));

        expect(submitCount).toBe(0);
        expect(document.contains(temporalSelect)).toBe(true);
        expect(temporalSelect.value).toBe("yearly");
    });

    test("layer details markup keeps hierarchy semantics and renders schema descriptions", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));

        expect(document.querySelector('summary [data-features-export-action="toggle-layer"]')).toBeNull();
        expect(document.querySelectorAll(".features-export-tree__family").length).toBeGreaterThan(0);
        expect(document.querySelectorAll(".features-export-tree__dataset").length).toBeGreaterThan(0);
        expect(document.querySelectorAll(".features-export-tree__column").length).toBeGreaterThan(0);

        var columnInputs = Array.from(
            document.querySelectorAll(
                '[data-features-export-action="toggle-column"][data-layer-id="wepp.summary.hillslopes"]'
            )
        );
        var columnIds = columnInputs.map((node) => node.getAttribute("data-column-id"));
        expect(columnIds).toEqual(Array.from(new Set(columnIds)));

        var firstColumnLabel = columnInputs[0].closest("label");
        expect(firstColumnLabel).not.toBeNull();
        expect(firstColumnLabel.className).toContain("wc-choice");
        expect(firstColumnLabel.className).toContain("wc-choice--checkbox");
        expect(document.getElementById("features_export_catalog_list").textContent).toContain("Annual runoff depth");
    });

    test("family sections load collapsed by default", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var watershedFamily = document.querySelector('[data-features-export-family][data-family="watershed"]');
        var weppFamily = document.querySelector('[data-features-export-family][data-family="wepp"]');

        expect(watershedFamily).not.toBeNull();
        expect(weppFamily).not.toBeNull();
        expect(watershedFamily.open).toBe(false);
        expect(weppFamily.open).toBe(false);
    });

    test("discovery payload hides unavailable layers and disables roads scope when unavailable", () => {
        document.body.innerHTML = buildFixtureHtml();
        var bootstrapNode = document.getElementById("features_export_bootstrap_data");
        var bootstrapPayload = JSON.parse(bootstrapNode.textContent);
        bootstrapPayload.discovery = {
            roads_scope_available: false,
            available_layer_ids: [
                "watershed.subcatchments",
                "wepp.summary.hillslopes"
            ],
            available_families: ["watershed", "wepp"]
        };
        bootstrapNode.textContent = JSON.stringify(bootstrapPayload);

        controller.bootstrap({});

        expect(document.querySelector('[data-features-export-action="toggle-layer"][value="omni.scenarios.hillslopes"]')).toBeNull();
        expect(document.querySelector('[data-features-export-action="toggle-layer"][value="swat.interchange.table"]')).toBeNull();

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var roadsCheckbox = document.querySelector('[data-features-export-field="output-scope"][value="roads"]');
        expect(roadsCheckbox.disabled).toBe(true);
        expect(roadsCheckbox.checked).toBe(false);
        expect(document.querySelector('[data-features-export-region="roads-scope-note"]').textContent)
            .toContain("Roads scope is unavailable for this run.");
    });

    test("status-stream discovery refresh updates availability without page reload", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        expect(document.querySelector('[data-features-export-action="toggle-layer"][value="omni.scenarios.hillslopes"]')).not.toBeNull();

        var attachCall = baseInstance.attach_status_stream.mock.calls[0];
        var streamOptions = attachCall[1];
        expect(typeof streamOptions.onStatus).toBe("function");

        streamOptions.onStatus({
            raw: JSON.stringify({
                refresh_channel: "features_export",
                roads_scope_available: false,
                available_layer_ids: ["watershed.subcatchments", "wepp.summary.hillslopes"],
                available_families: ["watershed", "wepp"]
            })
        });

        expect(document.querySelector('[data-features-export-action="toggle-layer"][value="omni.scenarios.hillslopes"]')).toBeNull();

        var weppLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        weppLayer.checked = true;
        weppLayer.dispatchEvent(new Event("change", { bubbles: true }));
        var roadsCheckbox = document.querySelector('[data-features-export-field="output-scope"][value="roads"]');
        expect(roadsCheckbox.disabled).toBe(true);
    });

    test("omni select-all and unselect-all buttons toggle multi-select checkboxes", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var omniLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="omni.scenarios.hillslopes"]');
        omniLayer.checked = true;
        omniLayer.dispatchEvent(new Event("change", { bubbles: true }));

        var scenarioCheckbox = document.querySelector('[data-features-export-field="scenario"][value="uniform_low"]');
        expect(scenarioCheckbox.checked).toBe(false);

        document
            .querySelector('[data-features-export-action="omni-select-all"][data-omni-target="scenarios"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(scenarioCheckbox.checked).toBe(true);

        document
            .querySelector('[data-features-export-action="omni-unselect-all"][data-omni-target="scenarios"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(scenarioCheckbox.checked).toBe(false);
    });

    test("submit posts JSON and completion fetches jobinfo once per cycle with rendered results", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});
        window.site_prefix = "/weppcloud";
        var responseDownloadUrl = "/runs/test-run/test-cfg/download/export/features/artifacts/artifact-123/features_export%20result.gpkg";
        var expectedDownloadUrl = "/weppcloud" + responseDownloadUrl;

        var layer = document.querySelector('[data-features-export-action="toggle-layer"][value="watershed.subcatchments"]');
        layer.checked = true;
        layer.dispatchEvent(new Event("change", { bubbles: true }));

        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: {
                result: {
                    download_url: responseDownloadUrl,
                    artifact_id: "artifact-123",
                    cache_hit: true,
                    source_job_id: "job-source-7",
                    manifest_relpath: "export/features/job-101/manifest.json",
                    warnings: [{ code: "layer_unavailable", message: "Some layers were skipped." }]
                }
            }
        });

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test-run/test-cfg/export/features",
            expect.objectContaining({
                format: "geopackage",
                units: "project",
                crs: "wgs",
                layers: ["watershed.subcatchments"]
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(controller.poll_completion_event).toBe("FEATURES_EXPORT_TASK_COMPLETED");
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(controller, "job-101");

        controller.triggerEvent("FEATURES_EXPORT_TASK_COMPLETED", { source: "status", job_id: "job-101" });
        controller.triggerEvent("FEATURES_EXPORT_TASK_COMPLETED", { source: "poll", job_id: "job-101" });
        await flushPromises();
        await flushPromises();

        expect(httpMock.requestWithSessionToken).toHaveBeenCalledTimes(1);
        expect(httpMock.requestWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/jobinfo/job-101",
            expect.objectContaining({ method: "GET" })
        );

        expect(document.querySelector('[data-features-export-region="download"]').innerHTML).toContain(
            'href="' + expectedDownloadUrl + '"'
        );
        expect(document.querySelector('[data-features-export-region="artifact-meta"]').innerHTML).toContain(
            "artifact-123"
        );
        expect(document.querySelector('[data-features-export-region="warnings"]').innerHTML).toContain(
            "layer_unavailable"
        );
        expect(document.getElementById("features_export_result_state").textContent).toContain("Partial success");
        expect(document.getElementById("hint_run_features_export").textContent).toContain("job-101");
    });

    test("completion marks command button as terminal-ready so follow-up format and units changes stay enabled", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var layer = document.querySelector('[data-features-export-action="toggle-layer"][value="watershed.subcatchments"]');
        layer.checked = true;
        layer.dispatchEvent(new Event("change", { bubbles: true }));

        var submitButton = document.getElementById("btn_run_features_export");
        submitButton.disabled = true;

        controller.rq_job_id = "job-locked";
        controller.rq_job_status = null;
        controller.update_command_button_state = jest.fn((self) => {
            var status = self && self.rq_job_status ? String(self.rq_job_status.status || "") : "";
            var isTerminal = status === "finished"
                || status === "failed"
                || status === "stopped"
                || status === "canceled"
                || status === "not_found";
            submitButton.disabled = !isTerminal;
        });

        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: {
                result: {
                    download_url: "/runs/test-run/test-cfg/download/export/features/artifacts/artifact-locked/features_export.gpkg"
                }
            }
        });

        controller.triggerEvent("FEATURES_EXPORT_TASK_COMPLETED", { job_id: "job-locked" });
        await flushPromises();
        await flushPromises();

        expect(controller.update_command_button_state).toHaveBeenCalled();
        expect(submitButton.disabled).toBe(false);

        var formatSelect = document.querySelector('[data-features-export-field="format"]');
        formatSelect.value = "csv";
        formatSelect.dispatchEvent(new Event("change", { bubbles: true }));

        var englishUnits = document.querySelector('[data-features-export-field="units"][value="english"]');
        englishUnits.checked = true;
        englishUnits.dispatchEvent(new Event("change", { bubbles: true }));

        expect(submitButton.disabled).toBe(false);
    });

    test("submit accepts canonical wrapped job_id payloads", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var layer = document.querySelector('[data-features-export-action="toggle-layer"][value="watershed.subcatchments"]');
        layer.checked = true;
        layer.dispatchEvent(new Event("change", { bubbles: true }));

        httpMock.postJsonWithSessionToken.mockResolvedValueOnce({
            body: {
                Content: {
                    job_ids: {
                        run_features_export_rq: "job-303"
                    }
                }
            }
        });

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(controller, "job-303");
        expect(baseInstance.pushResponseStacktrace).not.toHaveBeenCalled();
    });

    test("scope_not_applicable warnings are suppressed from result state and warning list", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        var layer = document.querySelector('[data-features-export-action="toggle-layer"][value="wepp.summary.hillslopes"]');
        layer.checked = true;
        layer.dispatchEvent(new Event("change", { bubbles: true }));
        var roadsScope = document.querySelector('[data-features-export-field="output-scope"][value="roads"]');
        roadsScope.checked = true;
        roadsScope.dispatchEvent(new Event("change", { bubbles: true }));

        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: {
                result: {
                    download_url: "/runs/test-run/test-cfg/download/export/features/artifacts/artifact-456/features_export.gpkg",
                    artifact_id: "artifact-456",
                    cache_hit: false,
                    manifest_relpath: "export/features/job-404/manifest.json",
                    warnings: [
                        {
                            code: "scope_not_applicable",
                            message: "Layer 'watershed.subcatchments' is scope-invariant; roads scope is not separately applicable."
                        },
                        {
                            code: "scope_not_applicable",
                            message: "Layer 'watershed.channels' is scope-invariant; roads scope is not separately applicable."
                        }
                    ]
                }
            }
        });

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        controller.triggerEvent("FEATURES_EXPORT_TASK_COMPLETED", { source: "status", job_id: "job-101" });
        await flushPromises();
        await flushPromises();

        expect(document.getElementById("features_export_result_state").textContent).toContain("Success");
        expect(document.querySelector('[data-features-export-region="warnings"]').innerHTML).toBe("");
        expect(baseInstance.append_status_message).toHaveBeenLastCalledWith(
            controller,
            "Features export completed successfully."
        );
    });

    test("bootstrap resolves legacy and rq-suffixed job keys", () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({ jobIds: { run_features_export_rq: "job-bootstrap-rq" } });
        expect(baseInstance.set_rq_job_id).toHaveBeenLastCalledWith(controller, "job-bootstrap-rq");

        controller.bootstrap({ jobIds: { run_features_export: "job-bootstrap-plain" } });
        expect(baseInstance.set_rq_job_id).toHaveBeenLastCalledWith(controller, "job-bootstrap-plain");
    });

    test("validation and async failures route to stacktrace surfaces", async () => {
        document.body.innerHTML = buildFixtureHtml();
        controller.bootstrap({});

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            controller,
            expect.objectContaining({
                error: expect.objectContaining({
                    message: "Features export form validation failed."
                })
            })
        );
        expect(document.getElementById("features_export_stacktrace_panel").hidden).toBe(false);

        var layer = document.querySelector('[data-features-export-action="toggle-layer"][value="watershed.subcatchments"]');
        layer.checked = true;
        layer.dispatchEvent(new Event("change", { bubbles: true }));

        httpMock.postJsonWithSessionToken.mockResolvedValueOnce({ body: { job_id: "job-202" } });
        httpMock.requestWithSessionToken.mockRejectedValueOnce(new Error("jobinfo down"));

        document
            .getElementById("features_export_form")
            .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();
        await flushPromises();

        controller.triggerEvent("FEATURES_EXPORT_TASK_COMPLETED", { source: "status", job_id: "job-202" });
        await flushPromises();
        await flushPromises();

        expect(baseInstance.pushErrorStacktrace).toHaveBeenCalledWith(
            controller,
            expect.any(Error),
            "jobinfo",
            "Failed to load job info."
        );
    });
});

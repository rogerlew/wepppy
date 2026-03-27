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
            "wepp_summary",
            "omni_scenarios",
            "swat_interchange"
        ],
        family_labels: {
            watershed: "Watershed",
            wepp_summary: "WEPP Summary",
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
                selector_requirements: []
            },
            {
                layer_id: "wepp.summary.hillslopes",
                label: "WEPP Hillslopes",
                family: "wepp_summary",
                family_label: "WEPP Summary",
                scope_class: "scope_aware",
                geometry_type: "polygon",
                temporal_modes: ["annual_average", "yearly", "event"],
                selector_requirements: []
            },
            {
                layer_id: "omni.scenarios.boundaries",
                label: "Omni Scenario Boundaries",
                family: "omni_scenarios",
                family_label: "Omni Scenarios",
                scope_class: "scope_invariant",
                geometry_type: "polygon",
                temporal_modes: [],
                selector_requirements: ["omni_scenario"]
            },
            {
                layer_id: "swat.interchange.table",
                label: "SWAT Interchange Table",
                family: "swat_interchange",
                family_label: "SWAT Interchange",
                scope_class: "scope_invariant",
                geometry_type: "table",
                temporal_modes: [],
                selector_requirements: ["swat"]
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
                <select data-features-export-field="format">
                    <option value="geopackage" selected>GeoPackage</option>
                    <option value="geodatabase">Geodatabase</option>
                    <option value="geojson">GeoJSON</option>
                </select>
                <label><input type="radio" data-features-export-field="units" name="fx_units" value="project" checked>project</label>
                <label><input type="radio" data-features-export-field="units" name="fx_units" value="si">si</label>
                <label><input type="radio" data-features-export-field="crs" name="fx_crs" value="wgs" checked>wgs</label>
                <label><input type="radio" data-features-export-field="crs" name="fx_crs" value="utm">utm</label>
                <p data-features-export-region="packaging-hint"></p>
            </section>

            <section data-features-export-group="summary">
                <p data-features-export-region="selected-count"></p>
                <p data-features-export-region="family-counts"></p>
                <p data-features-export-region="capability-counts"></p>
                <p data-features-export-region="validation"></p>
                <p data-features-export-region="summary-warnings"></p>
            </section>

            <section data-features-export-group="catalog">
                <input type="text" data-features-export-field="layer-search">
                <button type="button" data-features-export-filter="all">All</button>
                <button type="button" data-features-export-filter="selected">Selected</button>
                <button type="button" data-features-export-filter="temporal">Temporal</button>
                <button type="button" data-features-export-filter="scope-aware">Scope</button>
                <button type="button" data-features-export-filter="needs-selector">Selector</button>
                <button type="button" data-features-export-action="clear-filters">Clear filters</button>
                <button type="button" data-features-export-action="select-visible">Select visible</button>
                <div id="features_export_catalog_list"></div>
            </section>

            <section data-features-export-group="scopes" hidden>
                <label><input type="checkbox" data-features-export-field="output-scope" value="baseline" checked>baseline</label>
                <label><input type="checkbox" data-features-export-field="output-scope" value="roads">roads</label>
            </section>

            <section data-features-export-group="temporal" hidden>
                <label><input type="radio" data-features-export-field="temporal-mode" name="fx_temporal_mode" value="annual_average">annual</label>
                <label><input type="radio" data-features-export-field="temporal-mode" name="fx_temporal_mode" value="yearly">yearly</label>
                <label><input type="radio" data-features-export-field="temporal-mode" name="fx_temporal_mode" value="event">event</label>

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
                    <select data-features-export-field="scenario">
                        <option value="">Select scenario</option>
                        <option value="uniform_low">Uniform Low</option>
                    </select>
                </div>
                <div data-features-export-omni-contrast-wrap hidden>
                    <select data-features-export-field="contrast-id">
                        <option value="">Select contrast</option>
                        <option value="mulch_vs_control">Mulch vs Control</option>
                    </select>
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
                <button type="button" data-features-export-action="clear-selection">Clear selection</button>
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
        expect(submitButton.disabled).toBe(true);

        document.querySelector('[data-features-export-field="temporal-mode"][value="annual_average"]').checked = true;
        document
            .querySelector('[data-features-export-field="temporal-mode"][value="annual_average"]')
            .dispatchEvent(new Event("change", { bubbles: true }));

        expect(submitButton.disabled).toBe(false);

        document
            .querySelector('[data-features-export-action="clear-selection"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        var omniLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="omni.scenarios.boundaries"]');
        omniLayer.checked = true;
        omniLayer.dispatchEvent(new Event("change", { bubbles: true }));
        expect(document.querySelector('[data-features-export-group="omni"]').hidden).toBe(false);

        document
            .querySelector('[data-features-export-action="clear-selection"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        var swatLayer = document.querySelector('[data-features-export-action="toggle-layer"][value="swat.interchange.table"]');
        swatLayer.checked = true;
        swatLayer.dispatchEvent(new Event("change", { bubbles: true }));
        expect(document.querySelector('[data-features-export-group="swat"]').hidden).toBe(false);

        await flushPromises();
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

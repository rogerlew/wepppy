/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

function buildHtml() {
    return `
        <form id="ag_fields_form">
            <input type="file" data-role="geojson-input">
            <button type="button" data-action="upload-boundaries" data-role="upload-button">Upload Field Boundaries</button>
            <div data-role="upload-status"></div>
            <div data-role="boundary-file-display" hidden><code data-role="boundary-filename"></code></div>
            <div data-role="boundary-summary"></div>
            <div data-role="duplicate-warning"></div>
            <select data-role="field-id-select"></select>
            <p data-role="accessor-display"></p>
            <select data-role="accessor-candidates" hidden></select>
            <input data-role="accessor-input">
            <table><tbody data-role="accessor-resolution-body"></tbody></table>
            <button type="button" data-action="confirm-schema" data-role="confirm-schema-button">Confirm Schema</button>
            <div data-role="schema-status"></div>
            <details id="agfields_schema_options"></details>

            <button type="button" data-action="build-subfields" data-role="build-subfields-button">Build Sub-fields</button>
            <div data-role="subfields-status"></div>
            <div data-role="subfields-summary"></div>
            <input data-role="min-area-input" value="0">

            <div data-role="mapping-chip"></div>
            <button type="button" data-action="open-mapping" data-role="open-mapping-button">Map Crops</button>
            <input type="file" data-role="plantdb-input">
            <button type="button" data-action="upload-plantdb" data-role="plantdb-upload-button">Upload Plant Files</button>
            <div data-role="plantdb-status"></div>
            <details id="agfields_plantdb_options"></details>
            <table><tbody data-role="plantfile-table-body"></tbody></table>

            <button type="button" data-action="run-wepp" data-role="run-button">Run WEPP</button>
            <div data-role="run-status"></div>
            <select data-role="wepp-bin-select">
                <option value="wepp_dcc52a6">wepp_dcc52a6</option>
                <option value="wepp_260606">wepp_260606</option>
            </select>
            <button type="button" data-action="clear-runs" data-role="clear-runs-button">Clear</button>
            <div data-role="results-links"></div>

            <button type="button" data-action="run-watershed" data-role="integration-run-button">Run Watershed</button>
            <button type="button" data-action="clear-watershed" data-role="integration-clear-button">Clear Watershed</button>
            <div data-role="integration-status"></div>
            <div data-role="integration-results"></div>
            <p data-role="integration-limitation"></p>

            <div id="ag_fields_status_panel"><div id="ag_fields_status_log"></div></div>
            <span id="ag_fields_braille"></span>
            <details id="ag_fields_stacktrace_panel"><div id="ag_fields_stacktrace"></div></details>
            <div id="ag_fields_rq_job"></div>
            <div id="ag_fields_summary"></div>
            <p id="hint_ag_fields_job"></p>
        </form>
        <div id="agfields_rotation_modal">
            <table><tbody data-role="mapping-table-body"></tbody></table>
            <details data-role="unused-mappings"><div data-role="unused-mappings-body"></div></details>
            <div data-role="mapping-status"></div>
            <button type="button" data-action="save-mapping" data-role="mapping-save-button">Save Mapping</button>
        </div>
    `;
}

function makeState(overrides = {}) {
    const state = {
        boundary: {
            filename: "My Fields.geojson",
            geojson_is_valid: true,
            geojson_hash: "hash-1",
            geojson_timestamp: "2026-07-09T20:00:00Z",
            field_columns: ["field_id", "Crop2020", "Crop2021"],
            field_n: 12,
        },
        schema: {
            field_id_key: "field_id",
            rotation_accessor: "Crop{}",
            complete: true,
        },
        subfields: {
            field_n: 12,
            sub_field_n: 24,
            sub_field_fp_n: 24,
            overlay_exists: true,
            complete: true,
        },
        mapping: {
            crop_count: 2,
            mapped_count: 2,
            complete: true,
            results: [
                { crop_name: "Corn", database: "weppcloud", rotation_id: "42", status: "ok", used: true },
                { crop_name: "Wheat", database: "weppcloud", rotation_id: "43", status: "ok", used: true },
            ],
        },
        plant_files: { valid_count: 0, invalid_count: 0 },
        wepp: { run_count: 0, output_count: 0, complete: false, wepp_bin: "wepp_dcc52a6" },
        watershed_integration: {
            status: "not_run",
            stale: false,
            summary: null,
            error: null,
            root_relpath: "wepp/ag_fields/watershed",
            limitation: "Field water and sediment are injected at the parent outlet.",
        },
        staleness: { subfields: false, wepp_runs: false },
        readiness: {
            observed_climate: true,
            observed_start_year: 2020,
            observed_end_year: 2021,
            watershed_abstraction: true,
            parent_wepp: true,
            missing_parent_wepp_ids: [],
        },
        job_ids: {
            agfields_build_subfields: null,
            agfields_plantdb: null,
            agfields_run_wepp: null,
            agfields_run_watershed: null,
        },
        active_job_ids: {
            agfields_build_subfields: null,
            agfields_plantdb: null,
            agfields_run_wepp: null,
            agfields_run_watershed: null,
        },
    };
    Object.keys(overrides).forEach((key) => {
        state[key] = Object.assign({}, state[key], overrides[key]);
    });
    return state;
}

function mappingPayload() {
    return {
        rows: [
            {
                crop_name: "Corn",
                database: "weppcloud",
                rotation_id: "42",
                status: "ok",
                message: null,
                used: true,
            },
            {
                crop_name: "Wheat",
                database: null,
                rotation_id: null,
                status: "unmapped",
                message: "Crop is not mapped.",
                used: true,
            },
        ],
        unique_crops: ["Corn", "Wheat"],
        unused_mappings: [
            { crop_name: "Barley", database: "weppcloud", rotation_id: "44", used: false },
        ],
        plant_files: {
            files: [{ filename: "corn.man", valid: true, format: "98.4" }],
            valid_files: ["corn.man"],
            invalid_files: [],
        },
        management_options: [
            { id: "42", description: "Corn rotation" },
            { id: "43", description: "Wheat rotation" },
        ],
    };
}

describe("AgFields controller", () => {
    let httpMock;
    let baseInstance;
    let controller;
    let currentState;
    let currentMapping;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = buildHtml();
        window.runid = "demo-run";
        window.runId = "demo-run";
        window.config = "cfg";

        await import("../dom.js");
        await import("../events.js");

        currentState = makeState();
        currentMapping = mappingPayload();
        httpMock = {
            requestWithSessionToken: jest.fn((url) => {
                if (url.endsWith("agfields/state")) {
                    return Promise.resolve({ body: currentState });
                }
                if (url.endsWith("agfields/plant-files")) {
                    return Promise.resolve({ body: currentMapping.plant_files });
                }
                if (url.endsWith("agfields/rotation-mapping")) {
                    return Promise.resolve({ body: currentMapping });
                }
                return Promise.resolve({ body: {} });
            }),
            postJsonWithSessionToken: jest.fn(() => Promise.resolve({ body: { job_id: "job-new" } })),
            isHttpError: jest.fn((error) => Boolean(error && error.name === "HttpError")),
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance } = createControlBaseStub({
            set_rq_job_id: jest.fn((self, jobId) => {
                self.rq_job_id = jobId;
            }),
            pushResponseStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.url_for_run = jest.fn((path, options) => {
            if (options && options.prefix) {
                return `${options.prefix}/runs/demo-run/cfg/${path}`;
            }
            return `/runs/demo-run/cfg/${path}`;
        });
        window.ModalManager = { close: jest.fn() };
        window.WCControllerBootstrap = {
            resolveJobId: jest.fn(() => null),
        };

        await import("../ag_fields.js");
        controller = window.AgFields.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = "";
        delete window.AgFields;
        delete window.WCDom;
        delete window.WCEvents;
        delete window.WCHttp;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.url_for_run;
        delete window.ModalManager;
        delete window.MapController;
        delete window.WCControllerBootstrap;
        delete window.runid;
        delete window.runId;
        delete window.config;
    });

    async function flushPromises() {
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();
    }

    test("detects single, multiple, absent, and partial crop-year patterns", () => {
        const detect = window.AgFields.detectCropYearPatterns;

        const single = detect(["field_id", "Crop2020", "Crop2021"], 2020, 2021);
        expect(single.outcome).toBe("single");
        expect(single.suggested.pattern).toBe("Crop{}");

        const multiple = detect(
            ["Crop2020", "Crop2021", "Landuse2020", "Landuse2021"],
            2020,
            2021,
        );
        expect(multiple.outcome).toBe("multiple");
        expect(multiple.completeCandidates.map((item) => item.pattern)).toEqual(["Crop{}", "Landuse{}"]);

        const absent = detect(["field_id", "crop_name"], 2020, 2021);
        expect(absent.outcome).toBe("none");
        expect(absent.suggested).toBeNull();

        const partial = detect(["field_id", "Crop2020"], 2020, 2021);
        expect(partial.outcome).toBe("none");
        expect(partial.suggested).toEqual(expect.objectContaining({ pattern: "Crop{}", coverage: 1 }));
    });

    test("bootstraps idempotently, resolves all contractual job keys, and hydrates the snapshot", async () => {
        controller.bootstrap({ jobIds: {} });
        controller.bootstrap({ jobIds: {} });
        await flushPromises();

        expect(window.WCControllerBootstrap.resolveJobId.mock.calls.map((call) => call[1])).toEqual(
            expect.arrayContaining([
                "agfields_build_subfields",
                "agfields_plantdb",
                "agfields_run_wepp",
                "agfields_run_watershed",
            ]),
        );
        expect(baseInstance.attach_status_stream).toHaveBeenCalledTimes(1);
        expect(document.querySelector('[data-role="boundary-summary"]').textContent).toContain("12 fields loaded");
        expect(document.querySelector('[data-role="boundary-file-display"]').hidden).toBe(false);
        expect(document.querySelector('[data-role="boundary-filename"]').textContent).toBe("My Fields.geojson");
        expect(document.querySelector('[data-role="field-id-select"]').value).toBe("field_id");
        expect(document.querySelector('[data-role="run-button"]').disabled).toBe(false);
        expect(document.querySelector('[data-role="wepp-bin-select"]').value).toBe("wepp_dcc52a6");
        expect(document.getElementById("ag_fields_summary").textContent).toBe("3 of 5 stages complete.");
    });

    test("renders snapshot-driven gating and orphan mapping errors", async () => {
        controller.bootstrap({});
        await flushPromises();

        controller.renderState(makeState({
            boundary: { filename: null, geojson_is_valid: false },
            schema: { complete: false, field_id_key: null, rotation_accessor: null },
            subfields: { complete: false, sub_field_n: 0, overlay_exists: false },
        }));
        expect(document.querySelector('[data-role="boundary-file-display"]').hidden).toBe(true);
        expect(document.querySelector('[data-role="build-subfields-button"]').disabled).toBe(true);
        expect(document.querySelector('[data-role="subfields-status"]').textContent).toBe(
            "Confirm the field boundary schema above first.",
        );

        controller.renderState(makeState({
            subfields: { complete: false, sub_field_n: 24, overlay_exists: true },
            staleness: { subfields: true },
        }));
        expect(document.querySelector('[data-role="subfields-status"]').textContent).toBe(
            "Sub-fields are stale — rebuild required.",
        );

        controller.renderState(makeState({
            mapping: {
                crop_count: 2,
                mapped_count: 1,
                complete: false,
                results: [
                    { crop_name: "Corn", status: "ok", used: true },
                    {
                        crop_name: "Wheat",
                        database: "plant_file_db",
                        rotation_id: "missing.man",
                        status: "error",
                        message: "Plant file is missing.",
                        used: true,
                    },
                ],
            },
        }));
        expect(document.querySelector('[data-role="mapping-chip"]').dataset.state).toBe("critical");
        expect(document.querySelector('[data-role="run-status"]').textContent).toBe(
            "Map all crops to managements first (1 unmapped).",
        );
        expect(document.getElementById("agfields_plantdb_options").open).toBe(true);
    });

    test("modal enables dependent management selects and keeps unused mappings", async () => {
        controller.bootstrap({});
        await flushPromises();
        await controller.loadMapping();

        const wheatRow = document.querySelector('[data-crop-name="Wheat"]');
        const select = wheatRow.querySelector('[data-action="mapping-management"]');
        expect(select.disabled).toBe(true);

        const plantSource = wheatRow.querySelector('[data-action="mapping-source"][value="plant_file_db"]');
        plantSource.checked = true;
        plantSource.dispatchEvent(new Event("change", { bubbles: true }));
        expect(select.disabled).toBe(false);
        expect(Array.from(select.options).map((option) => option.value)).toContain("corn.man");
        expect(document.querySelector('[data-role="unused-mappings"]').hidden).toBe(false);
        expect(document.querySelector('[data-role="unused-mappings-body"]').textContent).toContain("Barley");
    });

    test("mapping save failure renders the server error on the matching row without closing", async () => {
        controller.bootstrap({});
        await flushPromises();
        await controller.loadMapping();
        const error = Object.assign(new Error("Bad Request"), {
            name: "HttpError",
            status: 400,
            body: {
                error: { message: "Rotation mapping validation failed" },
                errors: [
                    { path: "rows.Corn", message: "Management id 42 is unavailable." },
                ],
            },
        });
        httpMock.postJsonWithSessionToken.mockRejectedValueOnce(error);

        document.querySelector('[data-action="save-mapping"]').dispatchEvent(
            new MouseEvent("click", { bubbles: true }),
        );
        await flushPromises();

        expect(document.querySelector('[data-crop-name="Corn"] [data-role="mapping-row-status"]').textContent).toBe(
            "Management id 42 is unavailable.",
        );
        expect(window.ModalManager.close).not.toHaveBeenCalled();
        expect(document.querySelector('#agfields_rotation_modal [data-role="mapping-status"]').dataset.state).toBe("critical");
    });

    test("boundary upload sets a busy state and renders the server message in the upload chip", async () => {
        controller.bootstrap({});
        await flushPromises();
        const input = document.querySelector('[data-role="geojson-input"]');
        Object.defineProperty(input, "files", {
            configurable: true,
            value: [new File(["{}"], "fields.geojson", { type: "application/geo+json" })],
        });
        const error = Object.assign(new Error("Bad Request"), {
            name: "HttpError",
            status: 400,
            body: { error: { message: "Missing literal field_id column." } },
        });
        httpMock.requestWithSessionToken.mockImplementationOnce(() => Promise.reject(error));

        const button = document.querySelector('[data-action="upload-boundaries"]');
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(button.getAttribute("aria-busy")).toBe("true");
        await flushPromises();

        expect(document.querySelector('[data-role="upload-status"]').textContent).toContain(
            "Missing literal field_id column.",
        );
        expect(button.disabled).toBe(false);
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalled();
    });

    test("plant zip upload sets a busy state and renders its server error in the plant chip", async () => {
        controller.bootstrap({});
        await controller.hydrate();
        const input = document.querySelector('[data-role="plantdb-input"]');
        Object.defineProperty(input, "files", {
            configurable: true,
            value: [new File(["zip"], "plants.zip", { type: "application/zip" })],
        });
        const error = Object.assign(new Error("Bad Request"), {
            name: "HttpError",
            status: 400,
            body: { error: { message: "Plant database archive contains no .man files." } },
        });
        httpMock.requestWithSessionToken.mockImplementationOnce(() => Promise.reject(error));

        const button = document.querySelector('[data-action="upload-plantdb"]');
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(button.getAttribute("aria-busy")).toBe("true");
        await flushPromises();

        expect(document.querySelector('[data-role="plantdb-status"]').textContent).toContain(
            "Plant database archive contains no .man files.",
        );
        expect(button.disabled).toBe(false);
    });

    test("tracks the contractual completion event for every queued job family", async () => {
        controller.bootstrap({});
        await controller.hydrate();
        const tracked = [];
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            tracked.push({ jobId, completionEvent: self.poll_completion_event });
            self.rq_job_id = jobId;
        });
        httpMock.postJsonWithSessionToken
            .mockResolvedValueOnce({ body: { job_id: "build-1" } })
            .mockResolvedValueOnce({ body: { job_id: "run-1" } })
            .mockResolvedValueOnce({ body: { job_id: "watershed-1" } });
        httpMock.requestWithSessionToken.mockImplementation((url) => {
            if (url.endsWith("agfields/plant-database")) {
                return Promise.resolve({ body: { job_id: "plant-1" } });
            }
            if (url.endsWith("agfields/state")) {
                return Promise.resolve({ body: currentState });
            }
            if (url.endsWith("agfields/plant-files")) {
                return Promise.resolve({ body: currentMapping.plant_files });
            }
            return Promise.resolve({ body: {} });
        });

        document.querySelector('[data-action="build-subfields"]').dispatchEvent(
            new MouseEvent("click", { bubbles: true }),
        );
        await flushPromises();

        const plantInput = document.querySelector('[data-role="plantdb-input"]');
        Object.defineProperty(plantInput, "files", {
            configurable: true,
            value: [new File(["zip"], "plants.zip", { type: "application/zip" })],
        });
        document.querySelector('[data-action="upload-plantdb"]').dispatchEvent(
            new MouseEvent("click", { bubbles: true }),
        );
        await flushPromises();

        document.querySelector('[data-action="run-wepp"]').dispatchEvent(
            new MouseEvent("click", { bubbles: true }),
        );
        await flushPromises();

        currentState = makeState({ wepp: { run_count: 24, complete: true } });
        controller.renderState(currentState);
        document.querySelector('[data-action="run-watershed"]').dispatchEvent(
            new MouseEvent("click", { bubbles: true }),
        );
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            expect.stringContaining("agfields/run-wepp"),
            { wepp_bin: "wepp_dcc52a6" },
            expect.objectContaining({ form: controller.form }),
        );

        expect(tracked).toEqual(expect.arrayContaining([
            {
                jobId: "build-1",
                completionEvent: "AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED",
            },
            {
                jobId: "plant-1",
                completionEvent: "AGFIELDS_PLANTDB_TASK_COMPLETED",
            },
            {
                jobId: "run-1",
                completionEvent: "AGFIELDS_RUN_WEPP_TASK_COMPLETED",
            },
            {
                jobId: "watershed-1",
                completionEvent: "AGFIELDS_RUN_WATERSHED_TASK_COMPLETED",
            },
        ]));
    });

    test("hydrates completed watershed counts, limitation, and browse link", async () => {
        controller.bootstrap({});
        await flushPromises();
        controller.renderState(makeState({
            wepp: { run_count: 24, complete: true },
            watershed_integration: {
                status: "completed",
                summary: { affected_parent_count: 8, sub_field_source_count: 24 },
            },
        }));

        expect(document.querySelector('[data-role="integration-status"]').textContent).toContain(
            "8 affected parents integrated from 24 sub-field sources",
        );
        expect(document.querySelector('[data-role="integration-limitation"]').textContent).toContain(
            "parent outlet",
        );
        expect(document.querySelector('[data-role="integration-results"] a').href).toContain(
            "browse/wepp/ag_fields/watershed/",
        );
        expect(document.getElementById("ag_fields_summary").textContent).toBe("5 of 5 stages complete.");
    });

    test("409 conflict rehydrates and keeps the server-reported active stream", async () => {
        controller.bootstrap({});
        await flushPromises();
        await controller.hydrate();
        const conflict = Object.assign(new Error("Conflict"), {
            name: "HttpError",
            status: 409,
            body: {
                error: {
                    code: "agfields_job_active",
                    message: "An AgFields job is active.",
                },
            },
        });
        httpMock.postJsonWithSessionToken.mockRejectedValueOnce(conflict);
        currentState = makeState({
            active_job_ids: { agfields_build_subfields: "active-1" },
            job_ids: { agfields_build_subfields: "active-1" },
        });

        document.querySelector('[data-action="build-subfields"]').dispatchEvent(
            new MouseEvent("click", { bubbles: true }),
        );
        await flushPromises();
        await new Promise((resolve) => {
            setTimeout(resolve, 0);
        });
        await flushPromises();

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(controller, "active-1");
        expect(controller.rq_job_id).toBe("active-1");
        expect(document.querySelector('[data-role="subfields-status"]').textContent).toContain(
            "An AgFields job is running",
        );
    });

    test("automatically loads the authenticated sub-field overlay and refreshes it after rebuild", async () => {
        const refresh = jest.fn(() => Promise.resolve({ type: "FeatureCollection", features: [] }));
        const map = {
            addGeoJsonOverlay: jest.fn((options) => {
                map.overlayMaps[options.layerName] = { refresh };
            }),
            overlayMaps: {},
        };
        window.MapController = { getInstance: jest.fn(() => map) };
        controller.bootstrap({});
        await controller.hydrate();
        await flushPromises();
        expect(map.addGeoJsonOverlay).toHaveBeenCalledWith(expect.objectContaining({
            layerName: "AgFields Sub-fields",
            url: "/rq-engine/api/runs/demo-run/cfg/agfields/sub-fields.geojson",
            loadJson: expect.any(Function),
        }));

        const options = map.addGeoJsonOverlay.mock.calls[0][0];
        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: { type: "FeatureCollection", features: [] },
        });
        await options.loadJson(options.url, {});
        expect(httpMock.requestWithSessionToken).toHaveBeenLastCalledWith(
            options.url,
            expect.objectContaining({ method: "GET" }),
        );
        expect(document.querySelector('[data-action="show-on-map"]')).toBeNull();

        controller.triggerEvent("AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED", { job_id: "build-finished" });
        await controller.hydrate({ force: true });
        await flushPromises();
        expect(refresh).toHaveBeenCalledWith(
            "/rq-engine/api/runs/demo-run/cfg/agfields/sub-fields.geojson",
        );
    });
});

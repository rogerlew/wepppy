/**
 * @jest-environment jsdom
 */

describe("Climate controller", () => {
    let controlBaseInstance;
    let postJsonMock;
    let requestMock;
    let climate;
    let formDataMock;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div id="climate_status_panel" data-status-panel><div data-status-log></div></div>
            <div id="climate_stacktrace_panel"></div>
            <form id="climate_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <script id="climate_catalog_data" type="application/json">
                    [
                        {
                            "catalog_id": "dataset_a",
                            "label": "Dataset A",
                            "climate_mode": 5,
                            "help_text": "Dataset A help",
                            "inputs": ["stochastic_years", "spatial_mode"],
                            "station_modes": [-1, 0, 1],
                            "spatial_modes": [0, 1],
                            "rap_compatible": false
                        },
                        {
                            "catalog_id": "dataset_b",
                            "label": "Dataset B",
                            "climate_mode": 3,
                            "description": "Dataset B description",
                            "inputs": ["stochastic_years"],
                            "station_modes": [-1, 0, 1],
                            "spatial_modes": [0],
                            "rap_compatible": true
                        }
                    ]
                </script>
                <input type="hidden" id="climate_catalog_id" name="climate_catalog_id" value="dataset_a" data-climate-field="catalog-id">
                <input type="hidden" id="climate_mode" name="climate_mode" value="5" data-climate-field="mode">

                <div id="climate_dataset_section" data-climate-element="dataset">
                    <label class="wc-choice">
                        <input type="radio" name="climate_dataset_choice" value="dataset_a" data-climate-action="dataset" checked>
                        <span>Dataset A</span>
                    </label>
                    <label class="wc-choice">
                        <input type="radio" name="climate_dataset_choice" value="dataset_b" data-climate-action="dataset">
                        <span>Dataset B</span>
                    </label>
                </div>

                <div id="climate_dataset_message"></div>

                <div id="climate_userdefined" data-climate-section="upload"></div>
                <div id="climate_cligen" data-climate-section="cligen"></div>

                <div id="section_stochastic" data-climate-section="stochastic_years"></div>
                <div id="section_spatial" data-climate-section="spatial_mode"></div>

                <div id="precip_scalar" data-precip-section="1" hidden></div>
                <div id="precip_monthly" data-precip-section="2" hidden></div>
                <div id="precip_reference" data-precip-section="3" hidden></div>

                <label class="wc-choice">
                    <input type="radio" name="precip_scaling_mode" value="0" data-climate-action="precip-mode" checked>
                    <span>None</span>
                </label>
                <label class="wc-choice">
                    <input type="radio" name="precip_scaling_mode" value="2" data-climate-action="precip-mode">
                    <span>Monthly</span>
                </label>

                <label class="wc-choice">
                    <input type="radio" name="climatestation_mode" value="-1" data-climate-action="station-mode" checked>
                    <span>Find Closest on Build</span>
                </label>
                <label class="wc-choice">
                    <input type="radio" name="climatestation_mode" value="0" data-climate-action="station-mode">
                    <span>Closest</span>
                </label>
                <label class="wc-choice">
                    <input type="radio" name="climatestation_mode" value="1" data-climate-action="station-mode">
                    <span>Heuristic</span>
                </label>

                <label class="wc-choice">
                    <input type="radio" name="climate_spatialmode" value="0" data-climate-action="spatial-mode" checked>
                    <span>Single</span>
                </label>
                <label class="wc-choice">
                    <input type="radio" name="climate_spatialmode" value="1" data-climate-action="spatial-mode">
                    <span>Multiple</span>
                </label>

                <label class="wc-choice">
                    <input type="radio" name="climate_build_mode" value="0" data-climate-action="build-mode" checked>
                    <span>CLIGEN</span>
                </label>
                <label class="wc-choice">
                    <input type="radio" name="climate_build_mode" value="1" data-climate-action="build-mode">
                    <span>User</span>
                </label>

                <input id="checkbox_use_gridmet_wind_when_applicable" type="checkbox" data-climate-action="gridmet-wind">

                <select id="climate_station_selection" name="climate_station_selection" data-climate-action="station-select">
                    <option value="STA-1">Station 1</option>
                </select>

                <div id="climate_monthlies"></div>
                <button id="btn_upload_cli" type="button" data-climate-action="upload-cli">Upload</button>
                <button id="btn_build_climate" type="button" data-climate-action="build">Build</button>
                <div id="hint_upload_cli"></div>
                <div id="hint_build_climate"></div>
                <input id="input_upload_cli" name="input_upload_cli" type="file">
            </form>
        `;

        const streamStub = { append: jest.fn(), connect: jest.fn(), disconnect: jest.fn() };

        controlBaseInstance = {
            triggerEvent: jest.fn(),
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            stop_job_status_polling: jest.fn(),
            render_job_status: jest.fn(),
            update_command_button_state: jest.fn(),
            attach_status_stream: jest.fn((self, options) => {
                controlBaseInstance.statusStream = streamStub;
                return streamStub;
            }),
            detach_status_stream: jest.fn(() => {
                controlBaseInstance.statusStream = null;
            }),
            connect_status_stream: jest.fn(),
            disconnect_status_stream: jest.fn(),
            reset_status_spinner: jest.fn()
        };

        global.controlBase = jest.fn(() => controlBaseInstance);

        postJsonMock = jest.fn((url) => {
            if (url === "rq/api/build_climate") {
                return Promise.resolve({ body: { Success: true, job_id: "job-123" } });
            }
            return Promise.resolve({ body: { Success: true } });
        });

        requestMock = jest.fn((url, options) => {
            if (url === "tasks/upload_cli/") {
                return Promise.resolve({ body: { Success: true } });
            }
            if (url === "view/closest_stations/") {
                return Promise.resolve({ body: "<option value='STA-1'>Station 1</option>" });
            }
            if (url === "view/heuristic_stations/") {
                return Promise.resolve({ body: "<option value='STA-2'>Station 2</option>" });
            }
            if (url === "view/climate_monthlies/") {
                return Promise.resolve({ body: "<div>Monthlies</div>" });
            }
            if (url === "report/climate/") {
                return Promise.resolve({ body: "<div>Report</div>" });
            }
            return Promise.resolve({ body: "" });
        });

        formDataMock = jest.fn();
        global.FormData = jest.fn(function MockFormData(form) {
            this.form = form;
            this.append = formDataMock;
        });

        await import("../dom.js");
        await import("../events.js");
        await import("../forms.js");

        global.WCHttp = {
            request: requestMock,
            postJson: postJsonMock,
            getJson: jest.fn(),
            isHttpError: jest.fn(() => false)
        };

        global.StatusStream = {
            attach: jest.fn(() => ({ append: jest.fn() }))
        };

        global.Project = {
            getInstance: jest.fn(() => ({
                set_preferred_units: jest.fn()
            }))
        };

        global.url_for_run = (path) => path;
        window.runid = "test-run";
        window.Node = window.Node || Element;

        await import("../climate.js");
        await new Promise((resolve) => setTimeout(resolve, 0));
        climate = window.Climate.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.runid;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.StatusStream;
        delete global.Project;
        delete global.url_for_run;
        delete global.FormData;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        delete window.Climate;
    });

    test("dataset change posts catalog mode and updates message", async () => {
        const handler = jest.fn();
        climate.events.on("climate:dataset:changed", handler);

        const datasetRadios = document.querySelectorAll('input[name="climate_dataset_choice"]');
        datasetRadios[1].checked = true;
        datasetRadios[1].dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_climate_mode/",
            expect.objectContaining({ catalog_id: "dataset_b", mode: 3 }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(handler).toHaveBeenCalledWith(expect.objectContaining({ catalogId: "dataset_b" }));
        expect(document.getElementById("climate_dataset_message").textContent).toContain("Dataset B description");
    });

    test("station mode change refreshes station list and emits events", async () => {
        const listLoaded = jest.fn();
        climate.events.on("climate:station:list:loaded", listLoaded);

        const heuristicRadio = document.querySelector('input[name="climatestation_mode"][value="1"]');
        heuristicRadio.checked = true;
        heuristicRadio.dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_climatestation_mode/",
            expect.objectContaining({ mode: 1 }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(requestMock).toHaveBeenCalledWith(
            "view/heuristic_stations/",
            expect.objectContaining({ params: { mode: 1 } })
        );
        expect(listLoaded).toHaveBeenCalledWith(expect.objectContaining({ mode: 1 }));
        expect(document.getElementById("climate_station_selection").innerHTML).toContain("STA-2");
    });

    test("precip mode toggles sections and emits event", () => {
        const handler = jest.fn();
        climate.events.on("climate:precip:mode", handler);

        const precipRadios = document.querySelectorAll('input[name="precip_scaling_mode"]');
        precipRadios[1].checked = true;
        precipRadios[1].dispatchEvent(new Event("change", { bubbles: true }));

        expect(document.getElementById("precip_monthly").hidden).toBe(false);
        expect(document.getElementById("precip_scalar").hidden).toBe(true);
        expect(handler).toHaveBeenCalledWith(expect.objectContaining({ mode: 2 }));
    });

    test("build enqueues job and emits lifecycle events", async () => {
        const started = jest.fn();
        const completed = jest.fn();
        climate.events.on("climate:build:started", started);
        climate.events.on("climate:build:completed", completed);

        const buildButton = document.querySelector('[data-climate-action="build"]');
        buildButton.dispatchEvent(new Event("click", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "rq/api/build_climate",
            expect.objectContaining({ climate_catalog_id: "dataset_a" }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(controlBaseInstance.set_rq_job_id).toHaveBeenCalledWith(controlBaseInstance, "job-123");
        expect(started).toHaveBeenCalled();
        expect(completed).toHaveBeenCalledWith(expect.objectContaining({ jobId: "job-123" }));
    });

    test("upload posts FormData and emits completion event", async () => {
        const uploadHandler = jest.fn();
        climate.events.on("climate:upload:completed", uploadHandler);

        const uploadButton = document.querySelector('[data-climate-action="upload-cli"]');
        uploadButton.dispatchEvent(new Event("click", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(requestMock).toHaveBeenCalledWith(
            "tasks/upload_cli/",
            expect.objectContaining({
                method: "POST",
                body: expect.any(Object),
                form: expect.any(HTMLFormElement)
            })
        );
        expect(uploadHandler).toHaveBeenCalled();
    });

    test("gridmet checkbox posts JSON and emits event", async () => {
        const handler = jest.fn();
        climate.events.on("climate:gridmet:updated", handler);

        const checkbox = document.getElementById("checkbox_use_gridmet_wind_when_applicable");
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_use_gridmet_wind_when_applicable/",
            expect.objectContaining({ state: true }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(handler).toHaveBeenCalledWith({ state: true });
    });

    test("station selection posts update", async () => {
        requestMock.mockImplementationOnce(() => Promise.resolve({ body: "<option value='STA-1'>Station 1</option>" }));
        const stationSelect = document.getElementById("climate_station_selection");
        stationSelect.value = "STA-1";
        stationSelect.dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_climatestation/",
            expect.objectContaining({ station: "STA-1" }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
    });

    test("attaches status stream using controlBase helper", () => {
        expect(controlBaseInstance.attach_status_stream).toHaveBeenCalledWith(
            controlBaseInstance,
            expect.objectContaining({
                form: expect.any(HTMLFormElement),
                channel: "climate",
                autoConnect: true
            })
        );
        expect(controlBaseInstance.detach_status_stream).toHaveBeenCalled();
    });

    test("bootstrap wires job id and refreshes climate data", () => {
        const precipSpy = jest.spyOn(climate, "handlePrecipScalingModeChange");
        const refreshSpy = jest.spyOn(climate, "refreshStationSelection").mockImplementation(() => {});
        const monthliesSpy = jest.spyOn(climate, "viewStationMonthlies").mockImplementation(() => {});
        climate.report = jest.fn();

        climate.bootstrap({
            jobIds: { build_climate_rq: "climate-job" },
            data: { climate: { hasStation: true, hasClimate: true, precipScalingMode: "model" } }
        });

        expect(controlBaseInstance.set_rq_job_id).toHaveBeenCalledWith(climate, "climate-job");
        expect(precipSpy).toHaveBeenCalledWith("model");
        expect(refreshSpy).toHaveBeenCalled();
        expect(monthliesSpy).toHaveBeenCalled();
        expect(climate.report).toHaveBeenCalled();
    });
});

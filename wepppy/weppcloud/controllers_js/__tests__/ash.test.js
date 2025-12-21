/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Ash controller", () => {
    let requestMock;
    let postJsonMock;
    let baseInstance;
    let statusStreamMock;
    let projectInstance;
    let ash;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="ash_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>

                <input type="radio" name="ash_depth_mode" value="1" data-ash-depth-mode="1" checked>
                <input type="radio" name="ash_depth_mode" value="0" data-ash-depth-mode="0">
                <input type="radio" name="ash_depth_mode" value="2" data-ash-depth-mode="2">

                <div id="ash_depth_mode1_controls"></div>
                <div id="ash_depth_mode0_controls" style="display: none;"></div>
                <div id="ash_depth_mode2_controls" style="display: none;">
                    <input id="input_upload_ash_load" type="file" data-ash-upload="load">
                    <input id="input_upload_ash_type_map" type="file" data-ash-upload="type">
                </div>

                <input id="ini_black_depth" name="ini_black_depth" type="number" value="3.1">
                <input id="ini_white_depth" name="ini_white_depth" type="number" value="4.2">

                <select id="ash_model_select" name="ash_model" data-ash-action="model-select">
                    <option value="multi" selected>Multi</option>
                    <option value="alex">Alex</option>
                </select>

                <select id="ash_transport_mode_select" name="transport_mode" data-ash-action="transport-select">
                    <option value="dynamic" selected>Dynamic</option>
                    <option value="static">Static</option>
                </select>

                <div class="alex-only-param" style="display: none;"></div>
                <div class="anu-only-param"></div>
                <div class="alex-dynamic-param" style="display: none;"></div>
                <div class="alex-static-param" style="display: none;"></div>
                <div id="dynamic_description" style="display: none;"></div>
                <div id="static_description" style="display: none;"></div>

                <input id="white_ini_bulk_den" name="white_ini_bulk_den" value="0.4">
                <input id="black_ini_bulk_den" name="black_ini_bulk_den" value="0.5">
                <input id="white_fin_bulk_den" name="white_fin_bulk_den" value="0.6">
                <input id="black_fin_bulk_den" name="black_fin_bulk_den" value="0.7">

                <input id="white_fin_erod" name="white_fin_erod" value="1.1">
                <input id="black_fin_erod" name="black_fin_erod" value="1.2">

                <input id="field_black_bulkdensity" name="field_black_bulkdensity" value="0.7">
                <input id="field_white_bulkdensity" name="field_white_bulkdensity" value="0.8">

                <input id="checkbox_run_wind_transport" type="checkbox" data-ash-action="toggle-wind">

                <button type="button" data-ash-action="run">Run</button>
            </form>
            <p id="hint_run_ash"></p>
            <script type="application/json" id="ash-model-params-data">
                {
                    "multi": {
                        "white": {
                            "ini_bulk_den": 0.4,
                            "fin_bulk_den": 0.6,
                            "bulk_den_fac": 0.9,
                            "par_den": 1.2,
                            "decomp_fac": 0.01,
                            "ini_erod": 0.5,
                            "fin_erod": 0.3,
                            "roughness_limit": 0.8
                        },
                        "black": {
                            "ini_bulk_den": 0.5,
                            "fin_bulk_den": 0.7,
                            "bulk_den_fac": 1.1,
                            "par_den": 1.3,
                            "decomp_fac": 0.02,
                            "ini_erod": 0.6,
                            "fin_erod": 0.4,
                            "roughness_limit": 0.9
                        }
                    },
                    "alex": {
                        "white": {
                            "ini_bulk_den": 0.45,
                            "fin_bulk_den": 0.65,
                            "bulk_den_fac": 1.0,
                            "par_den": 1.25,
                            "decomp_fac": 0.03,
                            "roughness_limit": 0.85,
                            "org_mat": 0.12,
                            "inistranscap": 0.0
                        },
                        "black": {
                            "ini_bulk_den": 0.55,
                            "fin_bulk_den": 0.75,
                            "bulk_den_fac": 1.15,
                            "par_den": 1.35,
                            "decomp_fac": 0.04,
                            "roughness_limit": 0.95,
                            "org_mat": 0.15,
                            "inistranscap": 0.0
                        }
                    }
                }
            </script>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");
        await import("../http.js");

        requestMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "ash-job" } }));
        postJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));

        global.WCHttp = {
            request: requestMock,
            postJson: postJsonMock,
            isHttpError: jest.fn(() => false),
            HttpError: class extends Error {}
        };

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn()
        }));

        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        projectInstance = {
            set_preferred_units: jest.fn()
        };
        global.Project = {
            getInstance: jest.fn(() => projectInstance)
        };

        global.url_for_run = jest.fn((path) => path);

        await import("../ash.js");
        ash = window.Ash.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Ash;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.Project;
        delete global.url_for_run;
        delete window.WCControllerBootstrap;

        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }

        document.body.innerHTML = "";
    });

    test("depth mode change toggles containers and emits event", () => {
        const modeChanged = jest.fn();
        ash.events.on("ash:mode:changed", modeChanged);

        const loadRadio = document.querySelector('input[name="ash_depth_mode"][value="0"]');
        loadRadio.checked = true;
        loadRadio.dispatchEvent(new Event("change", { bubbles: true }));

        expect(modeChanged).toHaveBeenCalledWith({ mode: 0 });
        expect(document.getElementById("ash_depth_mode0_controls").hidden).toBe(false);
        expect(document.getElementById("ash_depth_mode1_controls").hidden).toBe(true);
    });

    test("model switch caches values and restores on return", () => {
        const whiteBulk = document.getElementById("white_ini_bulk_den");
        whiteBulk.value = "1.23";

        const modelChanged = jest.fn();
        ash.events.on("ash:model:changed", modelChanged);

        const modelSelect = document.getElementById("ash_model_select");
        modelSelect.value = "alex";
        modelSelect.dispatchEvent(new Event("change", { bubbles: true }));

        expect(modelChanged).toHaveBeenLastCalledWith({ model: "alex", previousModel: "multi" });

        modelSelect.value = "multi";
        modelSelect.dispatchEvent(new Event("change", { bubbles: true }));

        expect(whiteBulk.value).toBe("1.23");
    });

    test("transport mode change emits event and toggles panels", () => {
        const transportListener = jest.fn();
        ash.events.on("ash:transport:mode", transportListener);

        const modelSelect = document.getElementById("ash_model_select");
        modelSelect.value = "alex";
        modelSelect.dispatchEvent(new Event("change", { bubbles: true }));

        const transportSelect = document.getElementById("ash_transport_mode_select");
        transportSelect.value = "static";
        transportSelect.dispatchEvent(new Event("change", { bubbles: true }));

        expect(transportListener).toHaveBeenLastCalledWith({ model: "alex", transportMode: "static" });
    });

    test("run submits FormData and emits started event", async () => {
        const runStarted = jest.fn();
        ash.events.on("ash:run:started", runStarted);
        let pollCompletionEvent = null;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        ash.run();
        await Promise.resolve();

        expect(requestMock).toHaveBeenCalledWith("rq/api/run_ash", expect.objectContaining({
            method: "POST",
            form: expect.any(HTMLFormElement),
            body: expect.any(FormData)
        }));

        const formData = requestMock.mock.calls[0][1].body;
        const entries = Array.from(formData.entries());
        expect(entries).toEqual(expect.arrayContaining([
            ["ash_depth_mode", "1"],
            ["ini_black_depth", "3.1"],
            ["ini_white_depth", "4.2"],
            ["ash_model", "multi"]
        ]));

        expect(runStarted).toHaveBeenCalledWith({
            jobId: "ash-job",
            payload: expect.objectContaining({ ash_model: "multi" })
        });
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(ash, "ash-job");
        expect(pollCompletionEvent).toBe("ASH_RUN_TASK_COMPLETED");
    });

    test("run failures push stacktrace and emit completed", async () => {
        const error = new Error("network");
        global.WCHttp.request = jest.fn(() => Promise.reject(error));
        const runCompleted = jest.fn();
        ash.events.on("ash:run:completed", runCompleted);

        ash.run();
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(ash, expect.any(Object));
        expect(runCompleted).toHaveBeenCalledWith(expect.objectContaining({ jobId: null }));
    });

    test("validateBeforeRun flags invalid upload", () => {
        const mapsRadio = document.querySelector('input[name="ash_depth_mode"][value="2"]');
        mapsRadio.checked = true;
        mapsRadio.dispatchEvent(new Event("change", { bubbles: true }));

        const badFile = { name: "bad.txt", size: 10 };
        const loadInput = document.getElementById("input_upload_ash_load");
        Object.defineProperty(loadInput, "files", {
            value: [badFile],
            configurable: true
        });

        const isValid = ash.validateBeforeRun();
        expect(isValid).toBe(false);
        expect(document.getElementById("hint_run_ash").textContent).toContain(".txt");
    });

    test("completion trigger is idempotent", () => {
        const completed = jest.fn();
        ash.events.on("ash:run:completed", completed);
        ash.rq_job_id = "finished-job";
        ash.report = jest.fn();

        ash.triggerEvent("ASH_RUN_TASK_COMPLETED");
        ash.triggerEvent("ASH_RUN_TASK_COMPLETED");

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(ash.report).toHaveBeenCalledTimes(1);
        expect(completed).toHaveBeenCalledWith({
            jobId: "finished-job",
            payload: null
        });
        expect(completed).toHaveBeenCalledTimes(1);
    });

    test("poll failure pushes stacktrace and emits job error", async () => {
        requestMock.mockResolvedValueOnce({ body: { exc_info: "trace line" } });
        ash.rq_job_id = "job-123";

        ash.handle_job_status_response(ash, { status: "failed" });
        await Promise.resolve();
        await Promise.resolve();

        expect(requestMock).toHaveBeenCalledWith("/weppcloud/rq/api/jobinfo/job-123");
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            ash,
            expect.objectContaining({
                Error: expect.stringContaining("failed"),
                StackTrace: expect.any(Array)
            })
        );
        const jobErrorCalls = baseInstance.triggerEvent.mock.calls.filter((call) => call[0] === "job:error");
        expect(jobErrorCalls).toHaveLength(1);
        expect(jobErrorCalls[0][1]).toEqual(expect.objectContaining({ jobId: "job-123", status: "failed", source: "poll" }));
    });

    test("bootstrap wires poll completion before set_rq_job_id", () => {
        window.WCControllerBootstrap = {
            resolveJobId: jest.fn(() => "ash-job-2")
        };
        let pollCompletionEvent = null;
        ash._completion_seen = true;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        ash.bootstrap({});

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(ash, "ash-job-2");
        expect(pollCompletionEvent).toBe("ASH_RUN_TASK_COMPLETED");
        expect(ash._completion_seen).toBe(false);
    });
});

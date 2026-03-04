/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Omni controller", () => {
    let originalHttp;
    let requestMock;
    let getJsonMock;
    let baseInstance;
    let statusStreamMock;
    let omni;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="omni_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div class="wc-card">
                    <button id="add-omni-scenario"
                            type="button"
                            data-omni-action="add-scenario">Add scenario</button>
                    <button id="delete-omni-scenarios"
                            type="button"
                            data-omni-action="delete-selected">Delete selected scenarios</button>
                    <div id="scenario-container"></div>
                </div>
                <button id="btn_run_omni"
                        type="button"
                        data-omni-action="run-scenarios">Run</button>
            </form>
            <p id="hint_run_omni"></p>
            <form id="omni_contrasts_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="braille"></div>
                <select data-omni-contrast-role="control-scenario">
                    <option value="uniform_low">uniform_low</option>
                    <option value="mulch">mulch</option>
                </select>
                <select data-omni-contrast-role="contrast-scenario">
                    <option value="uniform_low">uniform_low</option>
                    <option value="mulch">mulch</option>
                </select>
                <label>
                    <input type="radio" name="omni_contrast_selection_mode" value="cumulative" checked />
                    Cumulative
                </label>
                <button type="button" data-omni-contrast-action="run-contrasts">Run contrasts</button>
                <button type="button" data-omni-contrast-action="delete-contrasts">Delete contrasts</button>
            </form>
            <p id="hint_run_omni_contrasts"></p>
            <div id="omni-delete-modal" data-modal hidden>
                <div data-modal-dismiss></div>
                <div>
                    <ul data-omni-role="delete-list"></ul>
                    <button data-omni-action="confirm-delete">Confirm</button>
                </div>
            </div>
            <div id="omni-contrasts-delete-modal" data-modal hidden>
                <div data-modal-dismiss></div>
                <div>
                    <button data-omni-contrast-action="confirm-delete-contrasts">Confirm delete contrasts</button>
                </div>
            </div>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");
        await import("../http.js");

        originalHttp = { ...global.WCHttp };

        requestMock = jest.fn(() =>
            Promise.resolve({ body: { job_id: "job-321" } })
        );
        getJsonMock = jest.fn(() => Promise.resolve([]));
        global.WCHttp.request = requestMock;
        global.WCHttp.requestWithSessionToken = requestMock;
        global.WCHttp.getJson = getJsonMock;
        global.WCHttp.isHttpError = jest.fn(() => false);

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            update_command_button_state: jest.fn(),
            render_job_status: jest.fn(),
            stop_job_status_polling: jest.fn()
        }));

        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        global.url_for_run = jest.fn((path, options) => {
            if (options && options.prefix) {
                return `${options.prefix}/runs/test/cfg/${path}`;
            }
            return path;
        });

        await import("../omni.js");
        omni = window.Omni.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        Object.assign(global.WCHttp, originalHttp);
        delete window.Omni;
        delete global.controlBase;
        delete global.url_for_run;
        delete window.WCControllerBootstrap;
        document.body.innerHTML = "";
    });

    function addScenarioAndSelect(type) {
        const addButton = document.querySelector("[data-omni-action='add-scenario']");
        addButton.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
        const select = document.querySelector("[data-omni-role='scenario-select']");
        select.value = type;
        select.dispatchEvent(new window.Event("change", { bubbles: true }));
        return select.closest("[data-omni-scenario-item='true']");
    }

    test("run_omni_scenarios posts FormData and emits completion event", async () => {
        const runCompleted = jest.fn();
        omni.events.on("omni:run:completed", runCompleted);
        let pollCompletionEvent = null;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        addScenarioAndSelect("uniform_low");

        omni.run_omni_scenarios();
        expect(requestMock).toHaveBeenCalledTimes(1);

        await requestMock.mock.results[0].value;

        const requestArgs = requestMock.mock.calls[0];
        expect(requestArgs[0]).toBe("/rq-engine/api/runs/test/cfg/run-omni");
        const options = requestArgs[1];
        expect(options.method).toBe("POST");
        expect(options.body instanceof FormData).toBe(true);

        const entries = Array.from(options.body.entries());
        const scenariosEntry = entries.find(([name]) => name === "scenarios");
        expect(scenariosEntry).toBeDefined();
        const parsed = JSON.parse(scenariosEntry[1]);
        expect(parsed).toEqual([{ type: "uniform_low" }]);

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(omni, "job-321");
        expect(pollCompletionEvent).toBe("OMNI_SCENARIO_RUN_TASK_COMPLETED");
        expect(runCompleted).toHaveBeenCalledWith({
            job_id: "job-321",
            scenarios: [{ type: "uniform_low" }]
        });
        const hint = document.getElementById("hint_run_omni");
        expect(hint.innerHTML).toContain("job-321");
    });

    test("run_omni_scenarios handles message-only responses without undefined job id", async () => {
        requestMock.mockResolvedValueOnce({
            body: { message: "Set omni inputs for batch processing" }
        });

        addScenarioAndSelect("uniform_low");

        omni.run_omni_scenarios();
        await requestMock.mock.results[0].value;

        const statusElement = document.getElementById("status");
        expect(statusElement.textContent).toContain("Set omni inputs for batch processing");
        expect(statusElement.textContent).not.toContain("undefined");
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(omni, null);
    });

    test("load_scenarios_from_backend hydrates scenario controls", async () => {
        getJsonMock.mockResolvedValueOnce([
            { type: "thinning", canopy_cover: "40%", ground_cover: "93%" }
        ]);

        await omni.load_scenarios_from_backend();

        expect(global.url_for_run).toHaveBeenCalledWith("api/omni/get_scenarios");
        expect(getJsonMock).toHaveBeenCalledWith("api/omni/get_scenarios");

        const select = document.querySelector("[data-omni-role='scenario-select']");
        expect(select.value).toBe("thinning");

        const canopySelect = document.querySelector("[data-omni-field='canopy_cover']");
        const groundSelect = document.querySelector("[data-omni-field='ground_cover']");
        expect(canopySelect.value).toBe("40%");
        expect(groundSelect.value).toBe("93%");
    });

    test("run_omni_scenarios validates SBS uploads before posting", async () => {
        addScenarioAndSelect("sbs_map");

        const fileInput = document.querySelector("input[data-omni-role='scenario-file']");
        const badFile = new window.File(["123"], "bad.txt", { type: "text/plain" });
        Object.defineProperty(fileInput, "files", {
            value: [badFile],
            writable: false
        });

        omni.run_omni_scenarios();

        expect(requestMock).not.toHaveBeenCalled();

        const statusElement = document.getElementById("status");
        expect(statusElement.textContent).toContain("SBS maps must be");
    });

    test("delete selected scenarios posts delete request and prunes DOM", async () => {
        addScenarioAndSelect("uniform_low");
        const selectToggle = document.querySelector("[data-omni-role='scenario-select-toggle']");
        selectToggle.checked = true;
        selectToggle.dispatchEvent(new window.Event("change", { bubbles: true }));

        requestMock.mockResolvedValueOnce({
            body: { Content: { removed: ["uniform_low"], missing: [] } }
        });

        const deleteButton = document.querySelector("[data-omni-action='delete-selected']");
        deleteButton.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

        const confirmButton = document.querySelector("[data-omni-action='confirm-delete']");
        confirmButton.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

        await requestMock.mock.results[0].value;

        expect(requestMock).toHaveBeenCalledWith(
            "api/omni/delete_scenarios",
            expect.objectContaining({
                method: "POST",
                json: { scenario_names: ["uniform_low"] }
            })
        );

        const remaining = document.querySelectorAll("[data-omni-scenario-item='true']");
        expect(remaining).toHaveLength(0);
    });

    test("run_omni_contrasts handles message-only responses without undefined job id", async () => {
        addScenarioAndSelect("uniform_low");
        addScenarioAndSelect("mulch");

        const controlSelect = document.querySelector("[data-omni-contrast-role='control-scenario']");
        const contrastSelect = document.querySelector("[data-omni-contrast-role='contrast-scenario']");
        controlSelect.innerHTML = `
            <option value="uniform_low">uniform_low</option>
            <option value="mulch">mulch</option>
        `;
        contrastSelect.innerHTML = `
            <option value="uniform_low">uniform_low</option>
            <option value="mulch">mulch</option>
        `;
        controlSelect.value = "uniform_low";
        contrastSelect.value = "mulch";
        controlSelect.dispatchEvent(new window.Event("change", { bubbles: true }));
        contrastSelect.dispatchEvent(new window.Event("change", { bubbles: true }));

        requestMock.mockResolvedValueOnce({
            body: { message: "Set omni inputs for batch processing" }
        });

        omni.run_omni_contrasts();
        expect(requestMock).toHaveBeenCalled();
        await requestMock.mock.results[0].value;

        const statusElement = document.querySelector("#omni_contrasts_form #status");
        expect(statusElement.textContent).toContain("Set omni inputs for batch processing");
        expect(statusElement.textContent).not.toContain("undefined");
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(omni.contrastController, null);
    });

    test("delete contrasts submits job and updates hint/status", async () => {
        const hint = document.getElementById("hint_run_omni_contrasts");
        const statusElement = document.querySelector("#omni_contrasts_form #status");
        let pollCompletionEvent = null;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        requestMock.mockResolvedValueOnce({
            body: { message: "Delete contrasts job submitted.", result: { job_id: "job-456" } }
        });

        const deleteButton = document.querySelector("[data-omni-contrast-action='delete-contrasts']");
        deleteButton.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

        const confirmButton = document.querySelector("[data-omni-contrast-action='confirm-delete-contrasts']");
        confirmButton.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));

        await requestMock.mock.results[0].value;

        expect(requestMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/delete-omni-contrasts",
            expect.objectContaining({
                method: "POST",
                form: document.getElementById("omni_contrasts_form")
            })
        );
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(omni.contrastController, "job-456");
        expect(pollCompletionEvent).toBe("OMNI_CONTRAST_DELETE_TASK_COMPLETED");
        expect(hint.innerHTML).toContain("job-456");
        expect(statusElement.textContent).toContain("job-456");
    });

    test("completion trigger is idempotent", () => {
        const runCompleted = jest.fn();
        omni.events.on("omni:run:completed", runCompleted);
        omni.report_scenarios = jest.fn();

        omni.triggerEvent("OMNI_SCENARIO_RUN_TASK_COMPLETED", { source: "status" });
        omni.triggerEvent("OMNI_SCENARIO_RUN_TASK_COMPLETED", { source: "status" });

        expect(omni.report_scenarios).toHaveBeenCalledTimes(1);
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(runCompleted).toHaveBeenCalledTimes(1);
    });

    test("poll failure pushes stacktrace and emits job error", async () => {
        getJsonMock.mockResolvedValueOnce({ exc_info: "trace line" });
        omni.rq_job_id = "job-123";

        omni.handle_job_status_response(omni, { status: "failed" });
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();

        expect(getJsonMock).toHaveBeenCalledWith("/rq-engine/api/jobinfo/job-123", { params: undefined });
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            omni,
            expect.objectContaining({
                error: expect.objectContaining({ message: expect.stringContaining("failed") }),
                stacktrace: expect.any(Array)
            })
        );
        const jobErrorCalls = baseInstance.triggerEvent.mock.calls.filter((call) => call[0] === "job:error");
        expect(jobErrorCalls).toHaveLength(1);
        expect(jobErrorCalls[0][1]).toEqual(expect.objectContaining({ job_id: "job-123", status: "failed", source: "poll" }));
    });

    test("bootstrap wires poll completion before set_rq_job_id", () => {
        window.WCControllerBootstrap = {
            resolveJobId: jest.fn(() => "job-999")
        };
        const pollCompletionEvents = new Map();
        omni._completion_seen = true;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvents.set(self, self.poll_completion_event);
            return jobId;
        });

        omni.bootstrap({});

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(omni, "job-999");
        expect(pollCompletionEvents.get(omni)).toBe("OMNI_SCENARIO_RUN_TASK_COMPLETED");
        expect(omni._completion_seen).toBe(false);
    });
});

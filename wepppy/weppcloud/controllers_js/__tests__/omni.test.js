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
                    <div id="scenario-container"></div>
                </div>
                <button id="btn_run_omni"
                        type="button"
                        data-omni-action="run-scenarios">Run</button>
            </form>
            <p id="hint_run_omni"></p>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");
        await import("../http.js");

        originalHttp = { ...global.WCHttp };

        requestMock = jest.fn(() =>
            Promise.resolve({ body: { Success: true, job_id: "job-321" } })
        );
        getJsonMock = jest.fn(() => Promise.resolve([]));

        global.WCHttp.request = requestMock;
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

        global.url_for_run = jest.fn((path) => path);

        await import("../omni.js");
        omni = window.Omni.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        Object.assign(global.WCHttp, originalHttp);
        delete window.Omni;
        delete global.controlBase;
        delete global.url_for_run;
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

        addScenarioAndSelect("uniform_low");

        omni.run_omni_scenarios();
        expect(requestMock).toHaveBeenCalledTimes(1);

        await requestMock.mock.results[0].value;

        const requestArgs = requestMock.mock.calls[0];
        expect(requestArgs[0]).toBe("rq/api/run_omni");
        const options = requestArgs[1];
        expect(options.method).toBe("POST");
        expect(options.body instanceof FormData).toBe(true);

        const entries = Array.from(options.body.entries());
        const scenariosEntry = entries.find(([name]) => name === "scenarios");
        expect(scenariosEntry).toBeDefined();
        const parsed = JSON.parse(scenariosEntry[1]);
        expect(parsed).toEqual([{ type: "uniform_low" }]);

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(omni, "job-321");
        expect(runCompleted).toHaveBeenCalledWith({
            jobId: "job-321",
            scenarios: [{ type: "uniform_low" }]
        });
        const hint = document.getElementById("hint_run_omni");
        expect(hint.innerHTML).toContain("job-321");
    });

    test("load_scenarios_from_backend hydrates scenario controls", async () => {
        getJsonMock.mockResolvedValueOnce([
            { type: "thinning", canopy_cover: "40%", ground_cover: "93%" }
        ]);

        await omni.load_scenarios_from_backend();

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
});

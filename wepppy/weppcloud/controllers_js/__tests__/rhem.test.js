/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Rhem controller", () => {
    let httpMock;
    let baseInstance;
    let statusStreamMock;
    let rhem;
    let projectMock;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="rhem_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace" style="display:none;"></div>
                <div id="rq_job"></div>
                <span id="braille"></span>
                <input type="checkbox" name="clean" checked>
                <input type="checkbox" name="prep">
                <button id="btn_run_rhem" type="button" data-rhem-action="run">Run RHEM</button>
            </form>
            <p id="hint_run_rhem"></p>
            <div id="rhem_status_panel"></div>
            <div id="rhem_stacktrace_panel"></div>
            <div id="rhem-results"></div>
        `;

        window.runid = "demo-run";
        window.site_prefix = "";

        await import("../dom.js");
        await import("../events.js");
        await import("../forms.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-456" } })),
            request: jest
                .fn()
                .mockResolvedValue({ body: "<section>ok</section>" }),
            isHttpError: jest.fn(() => false)
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            hideStacktrace: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        global.url_for_run = jest.fn((path) => path);
        projectMock = { set_preferred_units: jest.fn() };
        window.Project = { getInstance: jest.fn(() => projectMock) };

        await import("../rhem.js");
        rhem = window.Rhem.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Rhem;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.url_for_run;
        delete window.WCControllerBootstrap;
        delete window.Project;
        delete window.runid;
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
        document.body.innerHTML = "";
    });

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    test("run posts payload, connects websocket, and records lifecycle events", async () => {
        const started = jest.fn();
        const queued = jest.fn();
        const pollCompletionValues = [];
        rhem.events.on("rhem:run:started", started);
        rhem.events.on("rhem:run:queued", queued);
        baseInstance.set_rq_job_id.mockImplementationOnce((self) => {
            pollCompletionValues.push(self.poll_completion_event);
        });

        const button = document.querySelector("[data-rhem-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "rq/api/run_rhem_rq",
            expect.objectContaining({ clean: true, prep: false }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(rhem, "job-456");
        expect(pollCompletionValues).toEqual(["RHEM_RUN_TASK_COMPLETED"]);
        expect(started).toHaveBeenCalledWith(expect.objectContaining({ runId: "demo-run" }));
        expect(queued).toHaveBeenCalledWith(expect.objectContaining({ jobId: "job-456" }));
    });

    test("completion event triggers report rendering and completion emission", async () => {
        const completions = [];
        rhem.events.on("rhem:run:completed", (payload) => completions.push(payload));

        httpMock.request
            .mockResolvedValueOnce({ body: "<div>Results</div>" })
            .mockResolvedValueOnce({ body: "<div>Summary</div>" });

        rhem.triggerEvent("RHEM_RUN_TASK_COMPLETED");
        await flushPromises();

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(httpMock.request).toHaveBeenNthCalledWith(
            1,
            "report/rhem/results/",
            expect.objectContaining({ method: "GET" })
        );
        expect(httpMock.request).toHaveBeenNthCalledWith(
            2,
            "report/rhem/run_summary/",
            expect.objectContaining({ method: "GET" })
        );
        expect(document.getElementById("rhem-results").innerHTML).toContain("Results");
        expect(document.getElementById("info").innerHTML).toContain("Summary");
        expect(statusStreamMock.append).toHaveBeenCalledWith(expect.stringContaining("Success"), expect.any(Object));
        expect(projectMock.set_preferred_units).toHaveBeenCalled();
        expect(completions).toHaveLength(1);
    });

    test("completion event is idempotent", async () => {
        const completions = [];
        rhem.events.on("rhem:run:completed", (payload) => completions.push(payload));

        httpMock.request
            .mockResolvedValueOnce({ body: "<div>Results</div>" })
            .mockResolvedValueOnce({ body: "<div>Summary</div>" });

        rhem.triggerEvent("RHEM_RUN_TASK_COMPLETED");
        rhem.triggerEvent("RHEM_RUN_TASK_COMPLETED");
        await flushPromises();

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(httpMock.request).toHaveBeenCalledTimes(2);
        expect(completions).toHaveLength(1);
    });

    test("bootstrap wires poll completion before job id", () => {
        const pollCompletionValues = [];
        baseInstance.set_rq_job_id.mockImplementationOnce((self) => {
            pollCompletionValues.push(self.poll_completion_event);
        });
        window.WCControllerBootstrap = {
            getControllerContext: jest.fn(() => ({})),
            resolveJobId: jest.fn(() => "job-bootstrap")
        };

        rhem.bootstrap({ jobIds: {} });

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(rhem, "job-bootstrap");
        expect(pollCompletionValues).toEqual(["RHEM_RUN_TASK_COMPLETED"]);
    });

    test("unsuccessful submission pushes stacktrace and emits error", async () => {
        httpMock.postJson.mockResolvedValueOnce({ body: { Success: false, Error: "Nope" } });
        const errors = [];
        rhem.events.on("rhem:run:failed", (payload) => errors.push(payload));

        rhem.run();
        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            rhem,
            expect.objectContaining({ Success: false, Error: "Nope" })
        );
        expect(errors).toHaveLength(1);
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
    });

    test("request rejection surfaces through controlBase stacktrace", async () => {
        const error = new Error("network failure");
        httpMock.postJson.mockRejectedValueOnce(error);

        rhem.run();
        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            rhem,
            expect.objectContaining({ Error: "network failure" })
        );
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
    });
});

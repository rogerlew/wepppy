/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("DebrisFlow controller", () => {
    let httpMock;
    let baseInstance;
    let statusStreamMock;
    let debris;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="debris_flow_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace" style="display: none;"></div>
                <div id="rq_job"></div>
                <span id="braille"></span>
                <button id="btn_run_debris_flow" data-debris-action="run" type="button">Run</button>
            </form>
            <p id="hint_run_debris_flow"></p>
        `;

        await import("../dom.js");
        await import("../events.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-123" } })),
            request: jest.fn(),
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
        window.site_prefix = "";

        await import("../debris_flow.js");
        debris = window.DebrisFlow.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.DebrisFlow;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.url_for_run;
        delete window.site_prefix;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        document.body.innerHTML = "";
    });

    test("delegated run button posts JSON and records job id", async () => {
        const events = [];
        debris.events.on("debris:run:started", (payload) => events.push({ event: "started", payload }));

        const button = document.querySelector("[data-debris-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await Promise.resolve();
        await Promise.resolve();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "rq/api/run_debris_flow",
            {},
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(debris, "job-123");
        expect(events.length).toBeGreaterThan(0);
        expect(events[0].event).toBe("started");
        expect(events[0].payload).toEqual(expect.objectContaining({ task: "debris:run" }));
    });

    test("reports results and emits completion when websocket event fires", () => {
        const completions = [];
        debris.events.on("debris:run:completed", (payload) => completions.push(payload));

        document.getElementById("debris_flow_form").dispatchEvent(new CustomEvent("DEBRIS_FLOW_RUN_TASK_COMPLETED"));

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(document.getElementById("info").innerHTML).toContain("report/debris_flow/");
        expect(completions).toHaveLength(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:completed",
            expect.objectContaining({ task: "debris:run" })
        );
    });

    test("handles unsuccessful payload by pushing stacktrace and emitting error", async () => {
        httpMock.postJson.mockResolvedValueOnce({ body: { Success: false, Error: "failed" } });
        const errors = [];
        debris.events.on("debris:run:error", (payload) => errors.push(payload));

        debris.run();
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(debris, { Success: false, Error: "failed" });
        expect(errors).toHaveLength(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "debris:run" })
        );
    });

    test("handles request rejection with controlBase stacktrace", async () => {
        const error = new Error("network");
        httpMock.postJson.mockRejectedValueOnce(error);

        debris.run();
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            debris,
            expect.objectContaining({ Error: "network" })
        );
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "debris:run" })
        );
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
    });
});

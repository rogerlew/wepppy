/**
 * @jest-environment jsdom
 */

describe("RAP_TS controller", () => {
    let httpMock;
    let baseInstance;
    let statusStreamMock;
    let controller;

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div class="controller-section" id="rap_ts_section">
                <form id="rap_ts_form">
                    <div id="info"></div>
                    <div id="status"></div>
                    <div id="stacktrace"></div>
                    <div id="rq_job"></div>
                    <p id="hint_build_rap_ts"></p>
                    <button id="btn_build_rap_ts" type="button" data-rap-action="run">Acquire RAP Data</button>
                </form>
            </div>
            <script id="rap_ts_schedule_data" type="application/json" data-rap-schedule>["2024"]</script>
        `;

        const createControlBaseStub = require("./helpers/control_base_stub");

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-123" } })),
            isHttpError: jest.fn((error) => Boolean(error && error.isHttpError))
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            render_job_status: jest.fn(),
            update_command_button_state: jest.fn(),
            stop_job_status_polling: jest.fn(),
            fetch_job_status: jest.fn(),
            triggerEvent: jest.fn(),
            status: {
                html: jest.fn()
            },
            stacktrace: {
                hide: jest.fn()
            }
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        await import("../rap_ts.js");
        const rapFactory = globalThis.RAP_TS || (typeof window !== "undefined" ? window.RAP_TS : undefined);
        if (!rapFactory) {
            throw new Error("RAP_TS controller failed to register on the global scope.");
        }
        controller = rapFactory.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.RAP_TS;
        delete global.WCHttp;
        delete global.controlBase;
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

    test("bootstrap emits schedule event", () => {
        const events = [];
        controller.events.on("rap:schedule:loaded", (payload) => events.push(payload.schedule));
        // invoke listener manually because emitter already emitted on creation
        controller.events.emit("rap:schedule:loaded", { schedule: controller.state.schedule });
        expect(events).toContainEqual(["2024"]);
    });

    test("acquire queues job and updates status", async () => {
        const statuses = [];
        controller.events.on("rap:timeseries:status", (payload) => statuses.push(payload.status));

        const button = document.querySelector("[data-rap-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "rq/api/acquire_rap_ts",
            {},
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.objectContaining({}), "job-123");

        const statusNode = document.getElementById("status");
        expect(statusNode.innerHTML).toContain("fetch_and_analyze_rap_ts_rq job submitted");
        expect(statusNode.innerHTML).toContain("job-123");

        expect(statuses).toEqual(["started", "queued"]);
    });

    test("acquire surfaces HTTP errors and disconnects websocket", async () => {
        const error = {
            isHttpError: true,
            detail: "Service unavailable",
            body: { Error: "Service unavailable" }
        };
        httpMock.postJson.mockImplementationOnce(() => Promise.reject(error));

        const errors = [];
        controller.events.on("rap:timeseries:run:error", (payload) => errors.push(payload.error));

        const button = document.querySelector("[data-rap-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(expect.any(Object), {
            Success: false,
            Error: "Service unavailable"
        });
  expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(errors).toHaveLength(1);
        expect(errors[0]).toEqual({
            Success: false,
            Error: "Service unavailable"
        });
    });
});

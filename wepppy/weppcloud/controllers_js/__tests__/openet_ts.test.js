/**
 * @jest-environment jsdom
 */

describe("OPENET_TS controller", () => {
    let httpMock;
    let baseInstance;
    let controller;

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div class="controller-section" id="openet_ts_section">
                <form id="openet_ts_form">
                    <div id="info"></div>
                    <div id="status"></div>
                    <div id="stacktrace"></div>
                    <div id="rq_job"></div>
                    <p id="hint_build_openet_ts"></p>
                    <button id="btn_build_openet_ts" type="button" data-openet-action="run">Acquire OpenET Data</button>
                </form>
            </div>
        `;

        const createControlBaseStub = require("./helpers/control_base_stub");

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-123" } })),
            request: jest.fn(),
            isHttpError: jest.fn((error) => Boolean(error && error.isHttpError))
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance } = createControlBaseStub({
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

        global.url_for_run = jest.fn((path) => path);

        await import("../openet_ts.js");
        const openetFactory = globalThis.OPENET_TS || (typeof window !== "undefined" ? window.OPENET_TS : undefined);
        if (!openetFactory) {
            throw new Error("OPENET_TS controller failed to register on the global scope.");
        }
        controller = openetFactory.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.OPENET_TS;
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
        delete window.WCControllerBootstrap;
        delete global.url_for_run;
        document.body.innerHTML = "";
    });

    test("bootstrap wires poll completion event before set_rq_job_id", () => {
        window.WCControllerBootstrap = {
            resolveJobId: jest.fn(() => "job-456")
        };
        let pollCompletionEvent = null;
        controller._completion_seen = true;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        controller.bootstrap({});

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.any(Object), "job-456");
        expect(pollCompletionEvent).toBe("OPENET_TS_TASK_COMPLETED");
        expect(controller._completion_seen).toBe(false);
    });

    test("acquire queues job and updates status", async () => {
        const statuses = [];
        controller.events.on("openet:timeseries:status", (payload) => statuses.push(payload.status));
        let pollCompletionEvent = null;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        const button = document.querySelector("[data-openet-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "rq/api/acquire_openet_ts",
            {},
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.objectContaining({}), "job-123");
        expect(pollCompletionEvent).toBe("OPENET_TS_TASK_COMPLETED");

        const statusNode = document.getElementById("status");
        expect(statusNode.innerHTML).toContain("fetch_and_analyze_openet_ts_rq job submitted");
        expect(statusNode.innerHTML).toContain("job-123");

        expect(statuses).toEqual(["started", "queued"]);
    });

    test("completion trigger is idempotent", () => {
        const completions = [];
        controller.events.on("openet:timeseries:run:completed", (payload) => completions.push(payload));

        controller.triggerEvent("OPENET_TS_TASK_COMPLETED", { source: "status" });
        controller.triggerEvent("OPENET_TS_TASK_COMPLETED", { source: "status" });

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(completions).toHaveLength(1);
    });
});

/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Treatments controller", () => {
    let httpRequestMock;
    let postJsonMock;
    let baseInstance;
    let statusStreamMock;
    let treatments;
    let emittedEvents;

    const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

    function createEmitter() {
        return {
            on: jest.fn(),
            once: jest.fn(),
            off: jest.fn(),
            emit: jest.fn((event, payload) => {
                emittedEvents.push({ event, payload });
                return true;
            }),
            listenerCount: jest.fn(() => 0),
        };
    }

    beforeEach(async () => {
        jest.resetModules();
        emittedEvents = [];

        document.body.innerHTML = `
            <form id="treatments_form" data-treatments-form="true">
                <div id="info" data-treatments-role="info"></div>
                <div id="treatments_status_panel" data-status-panel>
                    <div id="status" data-treatments-role="status"></div>
                </div>
                <div id="treatments_stacktrace_panel">
                    <div id="stacktrace" data-treatments-role="stacktrace"></div>
                </div>
                <div id="rq_job" data-treatments-role="job"></div>
                <div id="treatments_mode1_controls" data-treatments-panel="selection"></div>
                <div id="treatments_mode4_controls" data-treatments-panel="upload" style="display:none;" hidden></div>
                <input type="radio" name="treatments_mode" value="1" data-treatments-role="mode" data-treatments-mode="1" checked>
                <input type="radio" name="treatments_mode" value="4" data-treatments-role="mode" data-treatments-mode="4">
                <select id="treatments_single_selection" data-treatments-role="selection">
                    <option value="">--</option>
                    <option value="mulch_30" selected>Mulch 30</option>
                    <option value="mulch_60">Mulch 60</option>
                </select>
                <input type="file" id="input_upload_landuse" data-treatments-role="upload">
                <button id="btn_build_treatments" type="button" data-treatments-action="build">Build</button>
            </form>
            <p id="hint_build_treatments" data-treatments-role="hint"></p>
        `;

        await import("../dom.js");

        global.WCForms = {
            serializeForm: jest.fn((form) => {
                const modeInput = form.querySelector('input[name="treatments_mode"]:checked');
                const selection = form.querySelector("#treatments_single_selection");
                return {
                    treatments_mode: modeInput ? modeInput.value : null,
                    treatments_single_selection: selection ? selection.value : null,
                };
            }),
        };

        global.WCEvents = {
            createEmitter,
            useEventMap: jest.fn((events, emitter) => emitter),
        };

        global.url_for_run = jest.fn((path) => path);

        httpRequestMock = jest.fn((url) => {
            if (url === "rq/api/build_treatments") {
                return Promise.resolve({ body: { Success: true, job_id: "job-123" } });
            }
            if (url === "report/treatments/") {
                return Promise.resolve({ body: "<p>report</p>" });
            }
            return Promise.resolve({ body: {} });
        });

        postJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));

        global.WCHttp = {
            request: httpRequestMock,
            postJson: postJsonMock,
            isHttpError: jest.fn().mockReturnValue(false),
        };

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.StatusStream = undefined;

        await import("../treatments.js");
        treatments = window.Treatments.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Treatments;
        delete global.WCHttp;
        delete global.WCForms;
        delete global.controlBase;
        delete global.StatusStream;
        delete global.WCEvents;
        delete global.url_for_run;
        if (global.WCDom) {
            delete global.WCDom;
        }
        document.body.innerHTML = "";
    });

    test("initializes helpers, captures option list, and emits scenario event", () => {
        expect(global.controlBase).toHaveBeenCalledTimes(1);
        expect(treatments.mode).toBe(1);

        const listEvent = emittedEvents.find((entry) => entry.event === "treatments:list:loaded");
        expect(listEvent).toBeTruthy();
        expect(listEvent.payload.options).toHaveLength(3);

        const scenarioEvent = emittedEvents.find((entry) => entry.event === "treatments:scenario:updated");
        expect(scenarioEvent).toBeTruthy();
        expect(scenarioEvent.payload).toMatchObject({ mode: 1, selection: "mulch_30" });
    });

    test("setMode posts normalized payload and toggles panels", async () => {
        postJsonMock.mockClear();
        emittedEvents.length = 0;

        await treatments.setMode("4");
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_treatments_mode/",
            { mode: 4, single_selection: "mulch_30" },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );

        const selectionPanel = document.querySelector("#treatments_mode1_controls");
        const uploadPanel = document.querySelector("#treatments_mode4_controls");
        expect(selectionPanel.hidden).toBe(true);
        expect(selectionPanel.style.display).toBe("none");
        expect(uploadPanel.hidden).toBe(false);

        const modeChanged = emittedEvents.find((entry) => entry.event === "treatments:mode:changed");
        expect(modeChanged).toBeTruthy();
        expect(modeChanged.payload).toMatchObject({ mode: 4 });
    });

    test("selection change delegates to setMode and emits event", async () => {
        const select = document.querySelector("#treatments_single_selection");
        select.value = "mulch_60";

        postJsonMock.mockClear();
        emittedEvents.length = 0;

        select.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_treatments_mode/",
            { mode: 1, single_selection: "mulch_60" },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );

        const selectionEvent = emittedEvents.find((entry) => entry.event === "treatments:selection:changed");
        expect(selectionEvent).toBeTruthy();
        expect(selectionEvent.payload).toMatchObject({ selection: "mulch_60" });
    });

    test("build submits form data, wires job lifecycle, and updates status", async () => {
        emittedEvents.length = 0;
        let pollCompletionEvent = null;
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            pollCompletionEvent = self.poll_completion_event;
            return jobId;
        });

        treatments.build();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledWith(
            "rq/api/build_treatments",
            expect.objectContaining({ method: "POST", body: expect.any(FormData) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(treatments, "job-123");
        expect(pollCompletionEvent).toBe("TREATMENTS_BUILD_TASK_COMPLETED");
        expect(statusStreamMock.append).toHaveBeenCalledWith(
            expect.stringContaining("build_treatments job submitted"),
            expect.any(Object)
        );

        const started = emittedEvents.find((entry) => entry.event === "treatments:run:started");
        const submitted = emittedEvents.find((entry) => entry.event === "treatments:run:submitted");
        expect(started).toBeTruthy();
        expect(submitted).toBeTruthy();
    });

    test("completion trigger is idempotent", () => {
        emittedEvents.length = 0;

        treatments.triggerEvent("TREATMENTS_BUILD_TASK_COMPLETED", { source: "poll" });
        treatments.triggerEvent("TREATMENTS_BUILD_TASK_COMPLETED", { source: "poll" });

        const completionEvents = emittedEvents.filter((entry) => entry.event === "treatments:job:completed");
        expect(completionEvents).toHaveLength(1);
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
    });

    test("poll failure pushes stacktrace and emits job error", async () => {
        httpRequestMock.mockResolvedValueOnce({ body: { exc_info: "trace line" } });
        treatments.rq_job_id = "job-123";

        treatments.handle_job_status_response(treatments, { status: "failed" });
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledWith("/weppcloud/rq/api/jobinfo/job-123");
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            treatments,
            expect.objectContaining({
                Error: expect.stringContaining("failed"),
                StackTrace: expect.any(Array)
            })
        );
        const jobErrorCalls = baseInstance.triggerEvent.mock.calls.filter((call) => call[0] === "job:error");
        expect(jobErrorCalls).toHaveLength(1);
        expect(jobErrorCalls[0][1]).toEqual(expect.objectContaining({ jobId: "job-123", status: "failed", source: "poll" }));
    });

    test("build failure records stacktrace and emits error event", async () => {
        const error = { name: "HttpError", message: "Upload failed", detail: "Upload failed" };
        global.WCHttp.isHttpError.mockReturnValueOnce(true);
        httpRequestMock.mockImplementationOnce(() => Promise.reject(error));

        treatments.build();
        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            treatments,
            { Error: "Upload failed" }
        );

        const errorEvent = emittedEvents.find((entry) => entry.event === "treatments:run:error");
        expect(errorEvent).toBeTruthy();
        expect(errorEvent.payload.error).toEqual({ Error: "Upload failed" });
    });
});

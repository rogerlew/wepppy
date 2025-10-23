/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Observed controller", () => {
    const STATUS_DONE = "Running observed model fit… done.";

    let httpMock;
    let baseInstance;
    let statusStreamMock;
    let observed;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div class="controller-section" id="observed_section">
                <form id="observed_form">
                    <div id="info"></div>
                    <div id="status"></div>
                    <div id="stacktrace" style="display:none;"></div>
                    <div id="rq_job"></div>
                    <textarea id="observed_text" name="observed_text">Date,Streamflow (mm)
01/01/2020,12
01/02/2020,15
</textarea>
                    <p id="hint_run_wepp"></p>
                    <button id="btn_run_observed" type="button" data-action="observed-run">Run</button>
                </form>
            </div>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true } })),
            getJson: jest.fn(() => Promise.resolve(true)),
            isHttpError: jest.fn((error) => Boolean(error && error.isHttpError))
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
            hideStacktrace: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        window.url_for_run = jest.fn((path) => "/weppcloud/" + path);

        await import("../observed.js");
        observed = window.Observed.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Observed;
        delete global.WCHttp;
        delete global.controlBase;
        delete window.url_for_run;
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

    async function flushPromises() {
        await Promise.resolve();
        await Promise.resolve();
    }

    test("run_model_fit posts CSV payload and reports success", async () => {
        const events = [];
        observed.events.on("observed:model:fit", (payload) => events.push(payload.status));

        const button = document.querySelector("[data-action='observed-run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "tasks/run_model_fit/",
            {
                data: expect.stringContaining("Date,Streamflow (mm)")
            },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:started",
            expect.objectContaining({ task: "observed:model-fit" })
        );
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:completed",
            expect.objectContaining({ task: "observed:model-fit" })
        );
        expect(events).toEqual(["started", "completed"]);

        const statusNode = document.getElementById("status");
        expect(statusNode.innerHTML).toBe(STATUS_DONE);

        const infoNode = document.getElementById("info");
        expect(infoNode.innerHTML).toContain("/weppcloud/report/observed/");
        expect(infoNode.innerHTML).toContain("View Model Fit Results");
    });

    test("run_model_fit surfaces errors via stacktrace and events", async () => {
        const error = {
            isHttpError: true,
            detail: "Invalid dataset",
            body: { Error: "Invalid dataset", StackTrace: ["line 1"] }
        };
        httpMock.postJson.mockImplementationOnce(() => Promise.reject(error));

        const errors = [];
        observed.events.on("observed:error", (payload) => errors.push(payload));

        const button = document.querySelector("[data-action='observed-run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            expect.any(Object),
            expect.objectContaining({ Error: "Invalid dataset" })
        );
        expect(errors).toHaveLength(1);
        expect(errors[0]).toEqual(expect.objectContaining({ task: "observed:model-fit" }));
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
    });

    test("onWeppRunCompleted toggles visibility based on availability", async () => {
        const states = [];
        observed.events.on("observed:data:loaded", (payload) => states.push(payload.available));

        // Hide first to observe transition back to visible.
        observed.hideControl();
        expect(document.getElementById("observed_section").hidden).toBe(true);

        await observed.onWeppRunCompleted();
        await flushPromises();

        expect(httpMock.getJson).toHaveBeenCalledWith("query/climate_has_observed/");
        expect(document.getElementById("observed_section").hidden).toBe(false);
        expect(states).toContain(false);
        expect(states).toContain(true);
    });

    test("bootstrap hides and shows control based on context", () => {
        const hideSpy = jest.spyOn(observed, "hideControl");
        const showSpy = jest.spyOn(observed, "showControl");

        observed.bootstrap({
            data: {
                climate: { hasObserved: true },
                observed: { hasResults: false }
            }
        });

        expect(hideSpy).toHaveBeenCalled();
        expect(showSpy).toHaveBeenCalled();
    });
});

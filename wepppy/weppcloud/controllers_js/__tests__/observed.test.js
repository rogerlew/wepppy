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
    let realControlBase;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div class="controller-section" id="observed_section">
                <form id="observed_form">
                    <div id="info"></div>
                    <section id="observed_status_panel" data-status-panel>
                        <div id="status" data-status-log></div>
                        <div id="rq_job"></div>
                        <span id="braille"></span>
                    </section>
                    <details id="observed_stacktrace_panel" data-stacktrace-panel>
                        <pre id="stacktrace" data-stacktrace-body style="display:none;"></pre>
                    </details>
                    <textarea id="observed_text" name="observed_text">Date,Streamflow (mm)
01/01/2020,12
01/02/2020,15
</textarea>
                    <p id="hint_run_observed"></p>
                    <button id="btn_run_observed" type="button" data-action="observed-run">Run</button>
                </form>
            </div>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: {} })),
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
        realControlBase = global.controlBase;
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        window.url_for_run = jest.fn((path) => path);

        await import("../observed.js");
        observed = window.Observed.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Observed;
        delete global.WCHttp;
        delete global.controlBase;
        delete window.url_for_run;
        delete window.StatusStream;
        delete window.runid;
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

    function getUrlFor(path) {
        const callIndex = window.url_for_run.mock.calls.findIndex(([arg]) => arg === path);
        expect(callIndex).toBeGreaterThan(-1);
        const result = window.url_for_run.mock.results[callIndex];
        expect(result).toBeDefined();
        return result.value;
    }

    test("run_model_fit posts CSV payload and reports success", async () => {
        const events = [];
        observed.events.on("observed:model:fit", (payload) => events.push(payload.status));

        const button = document.querySelector("[data-action='observed-run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(window.url_for_run).toHaveBeenCalledWith("tasks/run_model_fit/");
        expect(httpMock.postJson).toHaveBeenCalledWith(
            getUrlFor("tasks/run_model_fit/"),
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
        expect(window.url_for_run).toHaveBeenCalledWith("report/observed/");
        expect(infoNode.innerHTML).toContain(getUrlFor("report/observed/"));
        expect(infoNode.innerHTML).toContain("View Model Fit Results");
    });

    test("run_model_fit surfaces errors via stacktrace and events", async () => {
        const error = {
            isHttpError: true,
            detail: "Invalid dataset",
            body: { error: { message: "Invalid dataset" } }
        };
        httpMock.postJson.mockImplementationOnce(() => Promise.reject(error));

        const errors = [];
        observed.events.on("observed:error", (payload) => errors.push(payload));

        const button = document.querySelector("[data-action='observed-run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            expect.any(Object),
            expect.objectContaining({ error: { message: "Invalid dataset" } })
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

        expect(window.url_for_run).toHaveBeenCalledWith("query/climate_has_observed/");
        expect(httpMock.getJson).toHaveBeenCalledWith(getUrlFor("query/climate_has_observed/"));
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

    test("enabled empty state remains usable after WEPP completion", async () => {
        observed.bootstrap({ mods: { flags: { observed: true } }, data: { climate: {}, observed: {} } });
        expect(document.getElementById("observed_section").hidden).toBe(false);
        httpMock.getJson.mockResolvedValue(false);
        await observed.onWeppRunCompleted();
        await flushPromises();
        expect(document.getElementById("observed_section").hidden).toBe(false);
    });

    test("absent form is a no-op, then first enable and replacement bind once", async () => {
        const markup = document.body.innerHTML;
        document.body.innerHTML = "";
        observed.bootstrap({ mods: { flags: { observed: false } } });
        await observed.onWeppRunCompleted();
        expect(httpMock.getJson).not.toHaveBeenCalled();
        expect(observed.form).toBeNull();

        for (const value of ["first CSV", "replacement CSV"]) {
            document.body.innerHTML = markup;
            const form = document.getElementById("observed_form");
            document.getElementById("observed_text").value = value;
            observed.bootstrap({ mods: { flags: { observed: true } } });
            observed.bootstrap({ mods: { flags: { observed: true } } });
            expect(observed.form).toBe(form);
            expect(document.getElementById("observed_section").hidden).toBe(false);
            httpMock.postJson.mockClear();
            form.querySelector("button").click();
            await flushPromises();
            expect(httpMock.postJson).toHaveBeenCalledTimes(1);
            expect(httpMock.postJson).toHaveBeenCalledWith(
                "tasks/run_model_fit/", { data: value }, { form }
            );
            expect(form.querySelector("#info").textContent).toContain("View Model Fit Results");
        }
    });

    test("retained results stay visible without an enabled mod", async () => {
        observed.bootstrap({ mods: { flags: { observed: false } }, data: { observed: { hasResults: true } } });
        httpMock.getJson.mockResolvedValue(false);
        await observed.onWeppRunCompleted();
        await flushPromises();
        expect(document.getElementById("observed_section").hidden).toBe(false);
        expect(document.getElementById("info").textContent).toContain("View Model Fit Results");
    });


    test("WEPP notification before first enable does not poison the singleton", async () => {
        const markup = document.body.innerHTML;
        observed.dispose();
        document.body.innerHTML = "";
        jest.resetModules();
        await import("../observed.js");
        observed = window.Observed.getInstance();
        await observed.onWeppRunCompleted();
        expect(httpMock.getJson).not.toHaveBeenCalled();
        document.body.innerHTML = markup;
        observed.bootstrap({ mods: { flags: { observed: true } } });
        document.querySelector("[data-action='observed-run']").click();
        await flushPromises();
        expect(httpMock.postJson).toHaveBeenCalledTimes(1);
        expect(document.getElementById("status").textContent).toBe(STATUS_DONE);
    });


    test("real status handles detach on absence and rebind to replacement panels once", async () => {
        observed.dispose();
        jest.resetModules();
        await import("../status_stream.js");
        global.controlBase = realControlBase;
        window.runid = "observed-test";
        await import("../observed.js");
        observed = window.Observed.getInstance();
        const markup = document.body.innerHTML;
        const oldHandle = observed._statusStreamHandle;
        const oldStream = observed.statusStream;
        expect(oldHandle.element).toBe(document.getElementById("observed_status_panel"));
        document.body.innerHTML = "";
        observed.bootstrap({ mods: { flags: { observed: false } } });
        expect(observed._statusStreamHandle).toBeNull();
        expect(observed.statusStream).toBeNull();
        document.body.innerHTML = markup;
        observed.bootstrap({ mods: { flags: { observed: true } } });
        const newHandle = observed._statusStreamHandle;
        expect(newHandle.element).toBe(document.getElementById("observed_status_panel"));
        expect(observed.statusStream).not.toBe(oldStream);
        observed.bootstrap({ mods: { flags: { observed: true } } });
        expect(observed._statusStreamHandle).toBe(newHandle);
        observed.dispose();
    });

});

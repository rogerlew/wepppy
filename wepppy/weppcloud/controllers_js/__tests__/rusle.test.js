/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Rusle controller", () => {
    let httpMock;
    let baseInstance;
    let rusle;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="rusle_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace" style="display:none;"></div>
                <div id="rq_job"></div>
                <p id="hint_build_rusle"></p>
                <label><input type="radio" name="c_mode" value="observed_rap" data-rusle-c-mode="observed_rap" checked></label>
                <label><input type="radio" name="c_mode" value="scenario_sbs" data-rusle-c-mode="scenario_sbs"></label>
                <div data-rusle-section="rap-year">
                    <select id="rap_year" name="rap_year">
                        <option value="2024" selected>2024</option>
                        <option value="2025">2025</option>
                    </select>
                </div>
                <label><input type="checkbox" id="rusle_k_mode_nomograph" name="k_modes" value="polaris_nomograph" data-rusle-k-mode checked></label>
                <label><input type="checkbox" id="rusle_k_mode_epic" name="k_modes" value="polaris_epic" data-rusle-k-mode></label>
                <select id="default_k_mode" name="default_k_mode">
                    <option value="polaris_nomograph" selected>nomograph</option>
                    <option value="polaris_epic">epic</option>
                </select>
                <input id="p_value" name="p_value" value="1.0">
                <input type="checkbox" id="force_polaris_refresh" name="force_polaris_refresh">
                <button id="btn_build_rusle" type="button" data-rusle-action="run">Build</button>
            </form>
            <div id="rusle-results"></div>
            <div id="rusle_status_panel"><span id="braille"></span></div>
            <div id="rusle_stacktrace_panel"><div id="stacktrace"></div></div>
        `;

        window.runid = "demo-run";
        window.site_prefix = "";

        await import("../dom.js");
        await import("../events.js");
        await import("../forms.js");

        httpMock = {
            postJsonWithSessionToken: jest.fn(() => Promise.resolve({ body: { job_id: "job-rusle-1" } })),
            request: jest.fn(() => Promise.resolve({ body: "<div>RUSLE Results</div>" })),
            isHttpError: jest.fn(() => false)
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            hideStacktrace: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        global.url_for_run = jest.fn((path, options) => {
            if (options && options.prefix) {
                return `${options.prefix}/runs/test/cfg/${path}`;
            }
            return path;
        });

        await import("../rusle.js");
        rusle = window.Rusle.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Rusle;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.url_for_run;
        delete window.WCControllerBootstrap;
        delete window.runid;
        delete window.site_prefix;
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

    test("run submits RQ payload and sets completion event polling", async () => {
        const pollCompletionValues = [];
        baseInstance.set_rq_job_id.mockImplementationOnce((self) => {
            pollCompletionValues.push(self.poll_completion_event);
        });

        const button = document.querySelector("[data-rusle-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/build-rusle",
            expect.objectContaining({
                c_mode: "observed_rap",
                rap_year: "2024",
                k_modes: ["polaris_nomograph"],
                default_k_mode: "polaris_nomograph",
                p_value: "1.0"
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(rusle, "job-rusle-1");
        expect(pollCompletionValues).toEqual(["RUSLE_BUILD_TASK_COMPLETED"]);
    });

    test("scenario_sbs hides rap-year selector and omits rap_year payload", async () => {
        const scenario = document.querySelector('[data-rusle-c-mode="scenario_sbs"]');
        scenario.checked = true;
        scenario.dispatchEvent(new Event("change", { bubbles: true }));

        const rapSection = document.querySelector('[data-rusle-section="rap-year"]');
        expect(rapSection.hidden).toBe(true);

        const button = document.querySelector("[data-rusle-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        const payload = httpMock.postJsonWithSessionToken.mock.calls[0][1];
        expect(payload.c_mode).toBe("scenario_sbs");
        expect(Object.prototype.hasOwnProperty.call(payload, "rap_year")).toBe(false);
    });

    test("run enforces at least one K mode and normalizes default selection", async () => {
        const nomograph = document.getElementById("rusle_k_mode_nomograph");
        const epic = document.getElementById("rusle_k_mode_epic");
        const defaultSelect = document.getElementById("default_k_mode");
        nomograph.checked = false;
        epic.checked = false;
        defaultSelect.value = "polaris_epic";

        const button = document.querySelector("[data-rusle-action='run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        const payload = httpMock.postJsonWithSessionToken.mock.calls[0][1];
        expect(payload.k_modes).toEqual(["polaris_nomograph"]);
        expect(payload.default_k_mode).toBe("polaris_nomograph");
    });

    test("completion event refreshes the run results summary", async () => {
        rusle.triggerEvent("RUSLE_BUILD_TASK_COMPLETED");
        await flushPromises();

        expect(httpMock.request).toHaveBeenCalledWith("report/rusle/results/");
        expect(document.getElementById("rusle-results").innerHTML).toContain("RUSLE Results");
    });

    test("bootstrap fetches the run results summary once", async () => {
        rusle.bootstrap({});
        await flushPromises();
        rusle.bootstrap({});
        await flushPromises();

        expect(httpMock.request).toHaveBeenCalledTimes(1);
        expect(httpMock.request).toHaveBeenCalledWith("report/rusle/results/");
    });
});

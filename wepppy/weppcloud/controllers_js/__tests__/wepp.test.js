/**
 * @jest-environment jsdom
 */

describe("Wepp controller", () => {
    let postFormMock;
    let postJsonMock;
    let getJsonMock;
    let requestMock;
    let controlBaseInstance;
    let wepp;

    function createURLSearchParamsFromForm(form) {
        return new URLSearchParams(new FormData(form));
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="wepp_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <input name="clip_soils" type="checkbox" checked>
                <input name="clip_hillslopes" type="checkbox">
                <input name="initial_sat" type="number" value="0.3">
                <select id="channel_critical_shear">
                    <option value="1">1</option>
                </select>
                <input id="surf_runoff" value="">
                <input id="lateral_flow" value="">
                <input id="baseflow" value="">
                <input id="sediment" value="">
            </form>
            <div id="wepp_status_panel"></div>
            <div id="wepp_stacktrace_panel"></div>
            <div id="wepp-results"></div>
            <button type="button" data-wepp-action="run"></button>
            <input type="checkbox" data-wepp-routine="pmet">
            <input type="file" data-wepp-action="upload-cover-transform">
        `;

        controlBaseInstance = {
            triggerEvent: jest.fn(),
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            manage_ws_client: jest.fn(),
            stop_job_status_polling: jest.fn()
        };

        global.controlBase = jest.fn(() => controlBaseInstance);

        global.WCDom = {
            qs: (selector) => document.querySelector(selector),
            qsa: (selector) => Array.from(document.querySelectorAll(selector)),
            ensureElement: (selector) => {
                var el = document.querySelector(selector);
                if (!el) {
                    throw new Error("Missing element for selector: " + selector);
                }
                return el;
            }
        };

        global.WCForms = {
            serializeForm: createURLSearchParamsFromForm
        };

        postFormMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-1" } }));
        postJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));
        getJsonMock = jest.fn(() => Promise.resolve({
            surf_runoff: 1.23456,
            lateral_flow: 2.34567,
            baseflow: 3.45678,
            sediment: 9.87
        }));
        requestMock = jest.fn((url) => Promise.resolve({ body: "<div>" + url + "</div>" }));

        global.WCHttp = {
            request: requestMock,
            postForm: postFormMock,
            postJson: postJsonMock,
            getJson: getJsonMock,
            isHttpError: jest.fn(() => false)
        };

        global.StatusStream = {
            attach: jest.fn(() => ({ append: jest.fn() }))
        };

        global.Project = {
            getInstance: jest.fn(() => ({
                set_preferred_units: jest.fn()
            }))
        };

        global.SubcatchmentDelineation = {
            getInstance: jest.fn(() => ({
                prefetchLossMetrics: jest.fn()
            }))
        };

        global.Observed = {
            getInstance: jest.fn(() => ({
                onWeppRunCompleted: jest.fn()
            }))
        };

        global.url_for_run = (path) => path;
        window.runid = "test-run";
        window.Node = window.Node || Element;

        await import("../wepp.js");
        wepp = window.Wepp.getInstance();
    });

    afterEach(() => {
        delete window.runid;
        delete global.WCDom;
        delete global.WCForms;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.StatusStream;
        delete global.Project;
        delete global.SubcatchmentDelineation;
        delete global.Observed;
        delete global.url_for_run;
        delete window.Wepp;
    });

    test("run submits form data via WCHttp.postForm", async () => {
        wepp.run();
        await Promise.resolve();
        await Promise.resolve();

        expect(postFormMock).toHaveBeenCalledWith(
            "rq/api/run_wepp",
            expect.any(URLSearchParams),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(controlBaseInstance.set_rq_job_id).toHaveBeenCalledWith(controlBaseInstance, "job-1");
    });

    test("set_run_wepp_routine posts JSON payload", async () => {
        var toggle = document.querySelector('[data-wepp-routine="pmet"]');
        toggle.checked = true;
        toggle.dispatchEvent(new Event("change", { bubbles: true }));
        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_run_wepp_routine/",
            { routine: "pmet", state: true }
        );
    });

    test("updatePhosphorus populates field values", async () => {
        await wepp.updatePhosphorus();
        await Promise.resolve();
        expect(getJsonMock).toHaveBeenCalledWith("query/wepp/phosphorus_opts/");

        var surfRunoff = document.getElementById("surf_runoff");
        var lateralFlow = document.getElementById("lateral_flow");
        var baseflow = document.getElementById("baseflow");
        var sediment = document.getElementById("sediment");

        expect(surfRunoff.value).toBe("1.2346");
        expect(lateralFlow.value).toBe("2.3457");
        expect(baseflow.value).toBe("3.4568");
        expect(sediment.value).toBe("10");
    });

    test("report fetches results and summary", async () => {
        wepp.report();
        await Promise.resolve();
        await Promise.resolve();

        expect(requestMock).toHaveBeenCalledWith("report/wepp/results/");
        expect(requestMock).toHaveBeenCalledWith("report/wepp/run_summary/");
        expect(document.getElementById("wepp-results").innerHTML).toContain("report/wepp/results/");
        expect(document.getElementById("info").innerHTML).toContain("report/wepp/run_summary/");
    });
});

/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Wepp controller", () => {
    let postJsonMock;
    let requestMock;
    let getJsonMock;
    let controlBaseInstance;
    let statusStreamMock;
    let wepp;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="wepp_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="wepp-results"></div>
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
                <button type="button" data-wepp-action="run"></button>
                <input type="checkbox" data-wepp-routine="pmet">
                <select id="reveg_scenario" data-wepp-role="reveg-scenario">
                    <option value="">Observed</option>
                    <option value="user_cover_transform">User cover</option>
                </select>
                <div id="user_defined_cover_transform_container" hidden>
                    <input type="file" data-wepp-action="upload-cover-transform">
                </div>
            </form>
            <div id="wepp_status_panel"></div>
            <div id="wepp_stacktrace_panel"></div>
        `;

        await import("../dom.js");
        await import("../events.js");
        await import("../forms.js");

        ({ base: controlBaseInstance, statusStreamMock } = createControlBaseStub({
            triggerEvent: jest.fn(),
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            stop_job_status_polling: jest.fn()
        }));

        global.controlBase = jest.fn(() => Object.assign({}, controlBaseInstance));

        postJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-1" } }));
        getJsonMock = jest.fn(() => Promise.resolve({
            surf_runoff: 1.23456,
            lateral_flow: 2.34567,
            baseflow: 3.45678,
            sediment: 9.87
        }));
        requestMock = jest.fn((url) => Promise.resolve({ body: "<div>" + url + "</div>" }));

        global.WCHttp = {
            request: requestMock,
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
        jest.clearAllMocks();
        delete window.runid;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.StatusStream;
        delete global.Project;
        delete global.SubcatchmentDelineation;
        delete global.Observed;
        delete global.url_for_run;
        delete window.Wepp;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
    });

    test("run submits JSON payload and sets job id", async () => {
        const runButton = document.querySelector('[data-wepp-action="run"]');
        runButton.dispatchEvent(new Event("click", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "rq/api/run_wepp",
            expect.objectContaining({ clip_soils: true, initial_sat: "0.3" }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(controlBaseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.any(Object), "job-1");
    });

    test("run emits lifecycle events", async () => {
        const started = jest.fn();
        const queued = jest.fn();
        const completed = jest.fn();

        wepp.events.on("wepp:run:started", started);
        wepp.events.on("wepp:run:queued", queued);
        wepp.events.on("wepp:run:completed", completed);

        wepp.run();
        await Promise.resolve();
        await Promise.resolve();
        expect(started).toHaveBeenCalled();
        expect(queued).toHaveBeenCalledWith(expect.objectContaining({ jobId: "job-1" }));

        wepp.triggerEvent("WEPP_RUN_TASK_COMPLETED");
        expect(completed).toHaveBeenCalled();
    });

    test("set_run_wepp_routine posts JSON payload via delegate", async () => {
        var toggle = document.querySelector('[data-wepp-routine="pmet"]');
        toggle.checked = true;
        toggle.dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/set_run_wepp_routine/",
            { routine: "pmet", state: true },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
    });

    test("updatePhosphorus populates numeric fields", async () => {
        await wepp.updatePhosphorus();
        await Promise.resolve();

        expect(getJsonMock).toHaveBeenCalledWith("query/wepp/phosphorus_opts/");

        expect(document.getElementById("surf_runoff").value).toBe("1.2346");
        expect(document.getElementById("lateral_flow").value).toBe("2.3457");
        expect(document.getElementById("baseflow").value).toBe("3.4568");
        expect(document.getElementById("sediment").value).toBe("10");
    });

    test("report fetches results, summary, and emits event", async () => {
        const reportLoaded = jest.fn();
        wepp.events.on("wepp:report:loaded", reportLoaded);

        wepp.report();
        await Promise.resolve();
        await Promise.resolve();

        expect(requestMock).toHaveBeenCalledWith("report/wepp/results/");
        expect(requestMock).toHaveBeenCalledWith("report/wepp/run_summary/");
        expect(document.getElementById("wepp-results").innerHTML).toContain("report/wepp/results/");
        expect(document.getElementById("info").innerHTML).toContain("report/wepp/run_summary/");
        expect(reportLoaded).toHaveBeenCalledWith(expect.objectContaining({
            summary: expect.stringContaining("report/wepp/run_summary/"),
            results: expect.stringContaining("report/wepp/results/")
        }));
    });

    test("cover transform upload delegates to handler", async () => {
        const fileInput = document.querySelector('[data-wepp-action="upload-cover-transform"]');
        const file = new File(["hello"], "cover.csv", { type: "text/csv" });
        Object.defineProperty(fileInput, "files", {
            value: [file],
            configurable: true
        });

        fileInput.dispatchEvent(new Event("change", { bubbles: true }));
        await Promise.resolve();

        expect(postJsonMock).not.toHaveBeenCalledWith("tasks/upload_cover_transform");
        expect(WCHttp.request).toHaveBeenCalledWith(
            "tasks/upload_cover_transform",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
        );
    });

    test("revegetation scenario toggle shows container", () => {
        const container = document.getElementById("user_defined_cover_transform_container");
        expect(container.hidden).toBe(true);

        const select = document.getElementById("reveg_scenario");
        select.value = "user_cover_transform";
        select.dispatchEvent(new Event("change", { bubbles: true }));

        expect(container.hidden).toBe(false);
    });

    test("bootstrap assigns job id and triggers report when run complete", () => {
        const reportSpy = jest.spyOn(wepp, "report").mockImplementation(() => {});

        wepp.bootstrap({
            jobIds: { run_wepp_rq: "wepp-job" },
            data: { wepp: { hasRun: true } }
        });

        expect(controlBaseInstance.set_rq_job_id).toHaveBeenCalledWith(wepp, "wepp-job");
        expect(reportSpy).toHaveBeenCalled();
    });
});

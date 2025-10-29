/**
 * @jest-environment jsdom
 */

describe("DssExport controller", () => {
    let httpMock;
    let baseInstance;
    let statusStreamMock;
    let dss;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div class="controller-section" id="dss_section">
                <form id="dss_export_form">
                    <div id="info"></div>
                    <div id="status"></div>
                    <div id="stacktrace" style="display: none;"></div>
                    <div id="rq_job"></div>
                    <span id="braille"></span>
                    <div id="dss_export_mode1_controls">
                        <input
                            id="dss_export_mode1"
                            type="radio"
                            name="dss_export_mode"
                            value="1"
                            checked
                            data-action="dss-export-mode"
                            data-dss-export-mode="1"
                        >
                        <input type="text" id="dss_export_channel_ids" name="dss_export_channel_ids" value="12, 34">
                    </div>
                    <div id="dss_export_mode2_controls" style="display: none;">
                        <input
                            id="dss_export_mode2"
                            type="radio"
                            name="dss_export_mode"
                            value="2"
                            data-action="dss-export-mode"
                            data-dss-export-mode="2"
                        >
                        <input type="checkbox" id="dss_export_exclude_order_1" name="dss_export_exclude_order_1">
                        <input type="checkbox" id="dss_export_exclude_order_2" name="dss_export_exclude_order_2">
                        <input type="checkbox" id="dss_export_exclude_order_3" name="dss_export_exclude_order_3">
                        <input type="checkbox" id="dss_export_exclude_order_4" name="dss_export_exclude_order_4">
                        <input type="checkbox" id="dss_export_exclude_order_5" name="dss_export_exclude_order_5">
                    </div>
                    <button id="btn_export_dss" type="button" data-action="dss-export-run">Export</button>
                </form>
                <p id="hint_export_dss"></p>
            </div>
            <ul id="toc">
                <li><a href="#dss-export">DSS Export</a></li>
            </ul>
        `;

        const createControlBaseStub = require("./helpers/control_base_stub");

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-xyz" } }))
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            hideStacktrace: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        window.site_prefix = "/weppcloud";

        global.url_for_run = jest.fn((path) => path);

        await import("../dss_export.js");
        dss = window.DssExport.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.DssExport;
        delete global.WCHttp;
        delete global.controlBase;
        delete window.site_prefix;
        delete global.url_for_run;
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

    test("delegated export posts JSON payload and records job id", async () => {
        const startedEvents = [];
        dss.events.on("dss:export:started", (payload) => startedEvents.push(payload));

        const button = document.querySelector("[data-action='dss-export-run']");
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await Promise.resolve();
        await Promise.resolve();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "rq/api/post_dss_export_rq",
            { dss_export_mode: 1, dss_export_channel_ids: [12, 34], dss_export_exclude_orders: [] },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(dss, "job-xyz");
        expect(startedEvents).not.toHaveLength(0);
        expect(startedEvents[0]).toEqual(expect.objectContaining({ task: "dss:export" }));
    });

    test("mode toggle updates panels and emits events", () => {
        const modeEvents = [];
        dss.events.on("dss:mode:changed", (payload) => modeEvents.push(payload));

        const mode2Radio = document.getElementById("dss_export_mode2");
        mode2Radio.checked = true;
        mode2Radio.dispatchEvent(new Event("change", { bubbles: true }));

        expect(modeEvents).toHaveLength(1);
        expect(modeEvents[0]).toEqual({ mode: 2 });

        expect(document.getElementById("dss_export_mode1_controls").style.display).toBe("none");
        expect(document.getElementById("dss_export_mode2_controls").style.display).not.toBe("none");
    });

    test("websocket completion triggers report and job completed event", () => {
        const completions = [];
        dss.events.on("dss:export:completed", (payload) => completions.push(payload));

        document.getElementById("dss_export_form").dispatchEvent(
            new CustomEvent("DSS_EXPORT_TASK_COMPLETED", { bubbles: true })
        );

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(document.getElementById("info").innerHTML).toContain("weppcloud/browse/export/dss.zip");
        expect(completions).toHaveLength(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:completed",
            expect.objectContaining({ task: "dss:export" })
        );
    });

    test("unsuccessful payload pushes stacktrace and emits error", async () => {
        httpMock.postJson.mockResolvedValueOnce({ body: { Success: false, Error: "failed" } });
        const errors = [];
        dss.events.on("dss:export:error", (payload) => errors.push(payload));

        dss.export();
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(dss, { Success: false, Error: "failed" });
        expect(errors.length).toBeGreaterThan(0);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "dss:export" })
        );
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
    });

    test("request rejection routes through pushErrorStacktrace", async () => {
        const error = new Error("network");
        httpMock.postJson.mockRejectedValueOnce(error);

        dss.export();
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushErrorStacktrace).toHaveBeenCalledWith(dss, error);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "dss:export" })
        );
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
    });
});

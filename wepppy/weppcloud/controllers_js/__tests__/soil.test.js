/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Soil controller", () => {
    let postFormMock;
    let postJsonMock;
    let requestMock;
    let baseInstance;
    let statusStreamMock;
    let soil;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="soil_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="soil_mode0_controls"></div>
                <div id="soil_mode1_controls" style="display: none;"></div>
                <div id="soil_mode2_controls" style="display: none;"></div>
                <div id="soil_mode3_controls" style="display: none;"></div>
                <div id="soil_mode4_controls" style="display: none;"></div>
                <input type="radio" id="soil_mode0" name="soil_mode" value="0" checked>
                <input type="radio" id="soil_mode1" name="soil_mode" value="1">
                <input type="radio" id="soil_mode2" name="soil_mode" value="2">
                <input type="text" id="soil_single_selection" name="soil_single_selection" value="101">
                <select id="soil_single_dbselection" name="soil_single_dbselection">
                    <option value="">Select</option>
                    <option value="DB1">DB1</option>
                </select>
                <input type="checkbox" id="checkbox_run_flowpaths" name="checkbox_run_flowpaths">
                <select id="sol_ver" name="sol_ver">
                    <option value="7778.0">7778.0</option>
                    <option value="9002.0">9002.0</option>
                </select>
                <button type="button" id="btn_build_soil">Build</button>
            </form>
            <p id="hint_build_soil"></p>
        `;

        await import("../dom.js");
        await import("../forms.js");

        postFormMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "soil-job" } }));
        postJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));
        requestMock = jest.fn(() => Promise.resolve({ body: "<div>soil report</div>" }));

        global.WCHttp = {
            postForm: postFormMock,
            postJson: postJsonMock,
            request: requestMock,
            getJson: jest.fn(),
            isHttpError: jest.fn().mockReturnValue(false),
        };

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
        }));

        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        global.SubcatchmentDelineation = {
            getInstance: jest.fn(() => ({ enableColorMap: jest.fn() })),
        };

        global.url_for_run = jest.fn((path) => path);

        await import("../soil.js");
        soil = window.Soil.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Soil;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.SubcatchmentDelineation;
        delete global.url_for_run;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        document.body.innerHTML = "";
    });

    test("build posts serialized form data and records job id", async () => {
        document.getElementById("soil_single_dbselection").value = "DB1";
        soil.build();
        await Promise.resolve();

        expect(postFormMock).toHaveBeenCalledWith("rq/api/build_soils", expect.any(URLSearchParams), expect.objectContaining({
            form: expect.any(HTMLFormElement),
        }));
        const params = postFormMock.mock.calls[0][1];
        expect(params.get("soil_single_selection")).toBe("101");
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(soil, "soil-job");
    });

    test("setMode posts JSON payload with parsed integers", async () => {
        document.getElementById("soil_single_selection").value = "303";
        document.getElementById("soil_single_dbselection").value = "DB1";

        soil.setMode(1);
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith("tasks/set_soil_mode/", {
            mode: 1,
            soil_single_selection: 303,
            soil_single_dbselection: "DB1",
        }, expect.objectContaining({ form: expect.any(HTMLFormElement) }));

        expect(soil.mode).toBe(1);
        expect(document.getElementById("soil_mode1_controls").hidden).toBe(false);
        expect(document.getElementById("soil_mode0_controls").hidden).toBe(true);
    });

    test("ksflag change posts boolean payload", async () => {
        postJsonMock.mockClear();
        soil.set_ksflag(true);
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith("tasks/set_soils_ksflag/", { ksflag: true }, expect.any(Object));
    });

    test("sol_ver change triggers disturbed payload", async () => {
        postJsonMock.mockClear();
        const select = document.getElementById("sol_ver");
        select.value = "9002.0";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await Promise.resolve();

        expect(postJsonMock).toHaveBeenCalledWith("tasks/set_disturbed_sol_ver/", { sol_ver: "9002.0" }, expect.any(Object));
    });
});

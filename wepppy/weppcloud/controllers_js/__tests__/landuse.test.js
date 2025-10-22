/**
 * @jest-environment jsdom
 */

describe("Landuse controller", () => {
    let httpRequestMock;
    let httpPostJsonMock;
    let wsClientInstance;
    let baseInstance;
    let landuse;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <form id="landuse_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="landuse_mode0_controls"></div>
                <div id="landuse_mode1_controls" hidden></div>
                <div id="landuse_mode2_controls" hidden></div>
                <div id="landuse_mode3_controls" hidden></div>
                <div id="landuse_mode4_controls" hidden></div>
                <input type="radio" id="landuse_mode0" name="landuse_mode" value="0" checked>
                <input type="radio" id="landuse_mode1" name="landuse_mode" value="1">
                <select id="landuse_db">
                    <option value="nlcd">NLCD</option>
                </select>
                <select id="landuse_single_selection">
                    <option value="101">Option 101</option>
                    <option value="202">Option 202</option>
                </select>
                <button type="button" id="btn_build_landuse">Build</button>
            </form>
            <div id="hint_build_landuse"></div>
        `;

        await import("../dom.js");

        global.WCForms = {
            serializeForm: jest.fn(() => ({
                landuse_mode: "0",
                landuse_single_selection: "101",
            })),
        };

        httpRequestMock = jest.fn((url) => {
            if (url === "rq/api/build_landuse") {
                return Promise.resolve({ body: { Success: true, job_id: "job-1" } });
            }
            if (url === "report/landuse/") {
                return Promise.resolve({ body: "<div>report</div>" });
            }
            return Promise.resolve({ body: {} });
        });

        httpPostJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));

        global.WCHttp = {
            request: httpRequestMock,
            postJson: httpPostJsonMock,
            postForm: jest.fn(),
            getJson: jest.fn(),
            isHttpError: jest.fn().mockReturnValue(false),
        };

        baseInstance = {
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
        };
        global.controlBase = jest.fn(() => baseInstance);

        wsClientInstance = {
            connect: jest.fn(),
            disconnect: jest.fn(),
            attachControl: jest.fn(),
        };
        global.WSClient = jest.fn(() => wsClientInstance);
        global.SubcatchmentDelineation = {
            getInstance: jest.fn(() => ({ enableColorMap: jest.fn() })),
        };
        global.url_for_run = jest.fn((path) => path);

        await import("../landuse.js");
        landuse = window.Landuse.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Landuse;
        delete global.WCHttp;
        delete global.WCForms;
        delete global.controlBase;
        delete global.WSClient;
        delete global.SubcatchmentDelineation;
        delete global.url_for_run;
        if (global.WCDom) {
            delete global.WCDom;
        }
        document.body.innerHTML = "";
    });

    test("build submits form data and records job id", async () => {
        landuse.build();
        await Promise.resolve();

        expect(httpRequestMock).toHaveBeenCalledWith("rq/api/build_landuse", expect.objectContaining({
            method: "POST",
        }));
        const requestOptions = httpRequestMock.mock.calls[0][1];
        expect(requestOptions.body).toBeInstanceOf(FormData);
        expect(wsClientInstance.connect).toHaveBeenCalled();
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(landuse, "job-1");
        expect(document.querySelector("#status").textContent).toContain("build_landuse job submitted");
    });

    test("modify_mapping posts payload and refreshes report", async () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});

        landuse.modify_mapping("100", "200");
        await Promise.resolve();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "tasks/modify_landuse_mapping/",
            { dom: "100", newdom: "200" },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(landuse.report).toHaveBeenCalled();
    });

    test("mapping select delegate posts updates", async () => {
        landuse.infoElement.innerHTML = `
            <select data-landuse-role="mapping-select" data-landuse-dom="5">
                <option value="alpha" selected>Alpha</option>
            </select>
        `;
        landuse.bindReportEvents();
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        httpPostJsonMock.mockClear();

        const select = landuse.infoElement.querySelector("select");
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await Promise.resolve();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "tasks/modify_landuse_mapping/",
            { dom: "5", newdom: "alpha" },
            expect.any(Object)
        );
    });

    test("toggle button expands details panel", () => {
        landuse.infoElement.innerHTML = `
            <button type="button" data-landuse-toggle="panel-1" aria-expanded="false">Toggle</button>
            <table><tr><td>
                <details id="panel-1"></details>
            </td></tr></table>
        `;
        landuse.bindReportEvents();
        const button = landuse.infoElement.querySelector("button");
        button.dispatchEvent(new Event("click", { bubbles: true }));

        const details = landuse.infoElement.querySelector("#panel-1");
        expect(details.open).toBe(true);
        expect(button.getAttribute("aria-expanded")).toBe("true");
    });

    test("network errors surface via pushResponseStacktrace", async () => {
        const error = new Error("boom");
        global.WCHttp.isHttpError.mockReturnValue(true);
        httpPostJsonMock.mockRejectedValueOnce(error);

        landuse.modify_mapping("10", "11");
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(landuse, { Error: "boom" });
    });
});

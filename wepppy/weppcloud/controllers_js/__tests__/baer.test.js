/**
 * @jest-environment jsdom
 */

describe("Baer controller", () => {
    let httpRequestMock;
    let baseInstance;
    let wsClientInstance;
    let emitter;
    let mapInstance;
    let overlayMock;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <div id="sbs_legend"></div>
            <form id="sbs_upload_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="sbs_mode0_controls"></div>
                <div id="sbs_mode1_controls" hidden></div>
                <input type="radio" name="sbs_mode" id="sbs_mode0" value="0" checked>
                <input type="radio" name="sbs_mode" id="sbs_mode1" value="1">
                <input type="file" id="input_upload_sbs" name="input_upload_sbs">
                <input type="text" id="firedate" name="firedate" value="2024-07-04">
                <input type="text" id="baer_brk0" name="baer_brk0" value="1">
                <input type="text" id="baer_brk1" name="baer_brk1" value="2">
                <input type="text" id="baer_brk2" name="baer_brk2" value="3">
                <input type="text" id="baer_brk3" name="baer_brk3" value="4">
                <input type="text" id="baer_nodata" name="baer_nodata" value="999">
                <button type="button" data-baer-action="upload">Upload</button>
            </form>
        `;

        await import("../dom.js");

        emitter = {
            emit: jest.fn(),
        };

        global.WCEvents = {
            createEmitter: jest.fn(() => emitter),
            useEventMap: jest.fn((_, e) => e),
        };

        global.WCForms = {
            serializeForm: jest.fn(() => ({
                firedate: "2024-07-04",
                baer_brk0: "1",
                baer_brk1: "2",
                baer_brk2: "3",
                baer_brk3: "4",
                baer_nodata: "999",
            })),
        };

        httpRequestMock = jest.fn((url) => {
            if (url === "tasks/upload_sbs/") {
                return Promise.resolve({ body: { Success: true } });
            }
            if (url === "tasks/remove_sbs") {
                return Promise.resolve({ body: { Success: true } });
            }
            if (url === "tasks/build_uniform_sbs/1") {
                return Promise.resolve({ body: { Success: true } });
            }
            if (url === "query/baer_wgs_map/") {
                return Promise.resolve({
                    body: {
                        Success: true,
                        Content: {
                            bounds: [[0, 0], [1, 1]],
                            imgurl: "resources/baer.png",
                        },
                    },
                });
            }
            if (url === "query/has_dem/") {
                return Promise.resolve({ body: false });
            }
            if (url === "resources/legends/sbs/") {
                return Promise.resolve({ body: "<div>legend</div>" });
            }
            return Promise.resolve({ body: { Success: true } });
        });

        global.WCHttp = {
            request: httpRequestMock,
            isHttpError: jest.fn().mockReturnValue(false),
        };

        baseInstance = {
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            hideStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
        };
        global.controlBase = jest.fn(() => baseInstance);

        wsClientInstance = {
            attachControl: jest.fn(),
            connect: jest.fn(),
            disconnect: jest.fn(),
        };
        global.WSClient = jest.fn(() => wsClientInstance);

        mapInstance = {
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            removeLayer: jest.fn(),
            flyToBounds: jest.fn(),
        };
        global.MapController = {
            getInstance: jest.fn(() => mapInstance),
        };
        global.SubcatchmentDelineation = {
            getInstance: jest.fn(() => ({})),
        };

        overlayMock = {
            addTo: jest.fn(() => mapInstance),
            setOpacity: jest.fn(),
            options: { opacity: 0.7 },
            _bounds: [[0, 0], [1, 1]],
        };
        global.L = {
            imageOverlay: jest.fn(() => overlayMock),
        };

        await import("../baer.js");
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Baer;
        delete global.WCHttp;
        delete global.WCForms;
        delete global.controlBase;
        delete global.WSClient;
        delete global.MapController;
        delete global.SubcatchmentDelineation;
        delete global.WCEvents;
        delete global.L;
        if (global.WCDom) {
            delete global.WCDom;
        }
        document.body.innerHTML = "";
    });

    function getController() {
        return window.Baer.getInstance();
    }

    test("initialises and toggles modes via delegated handlers", () => {
        const baer = getController();
        const mode0 = document.querySelector("#sbs_mode0_controls");
        const mode1 = document.querySelector("#sbs_mode1_controls");

        expect(mode0.hidden).toBe(false);
        expect(mode1.hidden).toBe(true);

        const radio1 = document.querySelector("#sbs_mode1");
        radio1.checked = true;
        radio1.dispatchEvent(new Event("change", { bubbles: true }));

        expect(mode0.hidden).toBe(true);
        expect(mode1.hidden).toBe(false);
        expect(emitter.emit).toHaveBeenCalledWith("baer:mode:changed", { mode: 1 });
        expect(wsClientInstance.attachControl).toHaveBeenCalledWith(baer);
    });

    test("upload_sbs posts form data and emits lifecycle events", async () => {
        const baer = getController();

        await baer.upload_sbs();
        await Promise.resolve();

        expect(httpRequestMock).toHaveBeenCalledWith("tasks/upload_sbs/", expect.objectContaining({
            method: "POST",
            body: expect.any(FormData),
            form: expect.any(HTMLFormElement),
        }));
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith("job:started", expect.objectContaining({ task: "baer:upload" }));
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith("job:completed", expect.objectContaining({ task: "baer:upload" }));
        expect(emitter.emit).toHaveBeenCalledWith("baer:upload:started", {});
        expect(emitter.emit).toHaveBeenCalledWith("baer:upload:completed", expect.objectContaining({ response: { Success: true } }));
    });

    test("remove_sbs removes overlay and clears info", async () => {
        const baer = getController();
        baer.baer_map = overlayMock;

        await baer.remove_sbs();
        await Promise.resolve();

        expect(httpRequestMock).toHaveBeenCalledWith("tasks/remove_sbs", expect.objectContaining({
            method: "POST",
        }));
        expect(mapInstance.ctrls.removeLayer).toHaveBeenCalledWith(overlayMock);
        expect(mapInstance.removeLayer).toHaveBeenCalledWith(overlayMock);
        expect(baer.baer_map).toBeNull();
        expect(emitter.emit).toHaveBeenCalledWith("baer:remove:completed", expect.any(Object));
    });

    test("show_sbs loads imagery, legend, and binds opacity slider", async () => {
        const baer = getController();

        await baer.show_sbs();
        await Promise.resolve();

        expect(httpRequestMock).toHaveBeenCalledWith("query/baer_wgs_map/", expect.objectContaining({ method: "GET" }));
        expect(global.L.imageOverlay).toHaveBeenCalled();
        const imageOverlayArgs = global.L.imageOverlay.mock.calls[0];
        expect(imageOverlayArgs[0]).toMatch(/^resources\/baer\.png\?v=\d+$/);
        expect(imageOverlayArgs[1]).toEqual([[0, 0], [1, 1]]);
        expect(imageOverlayArgs[2]).toEqual({ opacity: 0.7 });
        expect(mapInstance.ctrls.addOverlay).toHaveBeenCalledWith(overlayMock, "Burn Severity Map");

        const slider = document.querySelector("#baer-opacity-slider");
        expect(slider).not.toBeNull();
        slider.value = "0.5";
        slider.dispatchEvent(new Event("input", { bubbles: true }));

        expect(overlayMock.setOpacity).toHaveBeenCalledWith(0.5);
        expect(emitter.emit).toHaveBeenCalledWith("baer:map:opacity", { opacity: 0.5 });
    });

    test("upload_sbs surfaces http errors via stacktrace", async () => {
        httpRequestMock.mockImplementationOnce(() => Promise.reject(new Error("failure")));
        const baer = getController();

        await baer.upload_sbs();
        await Promise.resolve();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalled();
        expect(emitter.emit).toHaveBeenCalledWith("baer:upload:error", expect.any(Object));
    });
});

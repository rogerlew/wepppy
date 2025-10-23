/**
 * @jest-environment jsdom
 */

describe("Outlet controller", () => {
    let httpRequestMock;
    let httpGetJsonMock;
    let baseInstance;
    let statusStreamMock;
    let mapInstance;
    let outlet;
    let markerFactory;
    let popupFactory;

    function resetDom() {
        document.body.innerHTML = `
            <form id="set_outlet_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div class="wc-stack" data-outlet-root>
                    <fieldset>
                        <label>
                            <input type="radio" id="set_outlet_mode_cursor" name="set_outlet_mode" value="0" checked>
                            Cursor
                        </label>
                        <label>
                            <input type="radio" id="set_outlet_mode_entry" name="set_outlet_mode" value="1">
                            Entry
                        </label>
                    </fieldset>
                    <div
                        id="set_outlet_mode0_controls"
                        data-mode="cursor"
                        data-outlet-mode-section>
                        <button
                            id="btn_set_outlet_cursor"
                            type="button"
                            data-outlet-action="cursor-toggle">
                            Use Cursor
                        </button>
                        <p id="hint_set_outlet_cursor" aria-live="polite"></p>
                    </div>
                    <div
                        id="set_outlet_mode1_controls"
                        data-mode="entry"
                        data-outlet-mode-section
                        hidden>
                        <input
                            id="input_set_outlet_entry"
                            type="text"
                            data-outlet-entry-field>
                        <button
                            id="btn_set_outlet_entry"
                            type="button"
                            data-outlet-action="entry-submit">
                            Specify Lon/Lat
                        </button>
                    </div>
                </div>
            </form>
        `;
    }

    beforeEach(async () => {
        jest.resetModules();
        resetDom();
        window.cellsize = 30;

        const createControlBaseStub = require("./helpers/control_base_stub");

        await import("../dom.js");
        await import("../events.js");

        markerFactory = () => {
            const marker = {
                setLatLng: jest.fn().mockReturnThis(),
                addTo: jest.fn().mockReturnThis()
            };
            return marker;
        };

        popupFactory = () => ({
            setLatLng: jest.fn().mockReturnThis(),
            setContent: jest.fn().mockReturnThis(),
            openOn: jest.fn().mockReturnThis(),
            remove: jest.fn()
        });

        const triggerEventMock = jest.fn();
        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(function (target, jobId) {
                target.rq_job_id = jobId;
            }),
            triggerEvent: triggerEventMock,
            __triggerEventMock: triggerEventMock,
            command_btn_id: []
        }));

        mapInstance = {
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn()
            },
            removeLayer: jest.fn(),
            on: jest.fn()
        };

        httpRequestMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-123" } }));
        httpGetJsonMock = jest.fn(() => Promise.resolve({ lat: 45, lng: -120 }));

        global.WCHttp = {
            request: httpRequestMock,
            getJson: httpGetJsonMock,
            isHttpError: jest.fn().mockReturnValue(false)
        };
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.MapController = {
            getInstance: jest.fn(() => mapInstance)
        };
        global.url_for_run = jest.fn((path) => path);

        global.L = {
            marker: jest.fn(() => markerFactory()),
            latLng: (lat, lng) => ({ lat, lng }),
            popup: jest.fn(() => popupFactory())
        };

        global.plotty = {
            plot: jest.fn()
        };

        await import("../outlet.js");
        outlet = window.Outlet.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Outlet;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.MapController;
        delete global.url_for_run;
        delete global.L;
        delete global.plotty;
        delete global.WCDom;
        delete global.WCEvents;
        document.body.innerHTML = "";
    });

    test("mode change toggles sections and emits event", () => {
        const cursorSection = document.getElementById("set_outlet_mode0_controls");
        const entrySection = document.getElementById("set_outlet_mode1_controls");
        const entryRadio = document.getElementById("set_outlet_mode_entry");

        const modeListener = jest.fn();
        outlet.events.on("outlet:mode:change", modeListener);

        expect(cursorSection.hidden).toBe(false);
        expect(entrySection.hidden).toBe(true);

        entryRadio.checked = true;
        entryRadio.dispatchEvent(new Event("change", { bubbles: true }));

        expect(cursorSection.hidden).toBe(true);
        expect(entrySection.hidden).toBe(false);
        expect(modeListener).toHaveBeenCalledWith({ mode: "entry", value: 1 });
    });

    test("cursor submission posts JSON and triggers lifecycle events", async () => {
        const queuedListener = jest.fn();
        const successListener = jest.fn();
        outlet.events.on("outlet:set:queued", queuedListener);
        outlet.events.on("outlet:set:success", successListener);

        await outlet.set_outlet({ latlng: window.L.latLng(46.1, -112.5) });
        await Promise.resolve();

        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(httpRequestMock).toHaveBeenCalledWith(
            "rq/api/set_outlet",
            expect.objectContaining({
                method: "POST",
                json: { latitude: 46.1, longitude: -112.5 },
                form: expect.any(HTMLFormElement)
            })
        );
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(outlet, "job-123");
        expect(baseInstance.__triggerEventMock).toHaveBeenCalledWith(
            "job:started",
            expect.objectContaining({
                jobId: "job-123",
                task: "outlet:set"
            })
        );
        expect(queuedListener).toHaveBeenCalledWith(
            expect.objectContaining({ jobId: "job-123", coordinates: { lat: 46.1, lng: -112.5 } })
        );

        outlet.show = jest.fn();
        outlet.triggerEvent("SET_OUTLET_TASK_COMPLETED", { message: "done" });

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.__triggerEventMock).toHaveBeenCalledWith(
            "job:completed",
            expect.objectContaining({ jobId: "job-123", task: "outlet:set" })
        );
        expect(successListener).toHaveBeenCalledWith(
            expect.objectContaining({
                jobId: "job-123",
                submission: expect.objectContaining({ jobId: "job-123" })
            })
        );
    });

    test("entry submission validates coordinates", () => {
        const input = document.getElementById("input_set_outlet_entry");
        input.value = "bad,data";

        const result = outlet.handleEntrySubmit();

        expect(result).toBe(false);
        expect(baseInstance.append_status_message).toHaveBeenCalledWith(
            expect.any(Object),
            expect.stringContaining("Invalid coordinates")
        );
    });

    test("show refreshes outlet display and populates info", async () => {
        const reportResponse = "<div>report</div>";
        httpGetJsonMock.mockResolvedValueOnce({ lat: 44, lng: -120 });
        httpRequestMock.mockImplementationOnce(() => Promise.resolve({ body: reportResponse }));

        outlet.show();
        await Promise.resolve();
        await Promise.resolve();

        expect(httpGetJsonMock).toHaveBeenCalledWith("query/outlet/", expect.objectContaining({ params: expect.any(Object) }));
        expect(httpRequestMock).toHaveBeenCalledWith("report/outlet/", expect.objectContaining({ params: expect.any(Object) }));
        expect(mapInstance.ctrls.addOverlay).toHaveBeenCalled();
        expect(document.getElementById("info").innerHTML).toBe(reportResponse);
    });

    test("delegate handler toggles cursor selection", () => {
        const cursorButton = document.getElementById("btn_set_outlet_cursor");
        expect(outlet.cursorSelectionOn).toBe(false);
        cursorButton.click();
        expect(outlet.cursorSelectionOn).toBe(true);
        cursorButton.click();
        expect(outlet.cursorSelectionOn).toBe(false);
    });
});

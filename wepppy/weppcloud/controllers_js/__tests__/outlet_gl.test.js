/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Outlet GL controller", () => {
    let baseInstance;
    let mapStub;
    let clickHandler;
    let outlet;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="set_outlet_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div class="wc-stack" data-outlet-root>
                    <input type="radio" id="set_outlet_mode_cursor" name="set_outlet_mode" value="0" checked>
                    <input type="radio" id="set_outlet_mode_entry" name="set_outlet_mode" value="1">
                    <div id="set_outlet_mode0_controls" data-outlet-mode-section data-mode="cursor">
                        <button type="button" id="btn_set_outlet_cursor" data-outlet-action="cursor-toggle">Use Cursor</button>
                        <p id="set_outlet_cursor_hint"></p>
                    </div>
                    <div id="set_outlet_mode1_controls" data-outlet-mode-section data-mode="entry" hidden>
                        <input id="input_set_outlet_entry" data-outlet-entry-field />
                        <button type="button" id="btn_set_outlet_entry" data-outlet-action="entry-submit">Specify</button>
                    </div>
                </div>
                <div id="set_outlet_status_panel"><span id="braille"></span></div>
                <div id="set_outlet_stacktrace_panel"></div>
                <p id="hint_set_outlet_cursor"></p>
            </form>
            <div id="mapid"></div>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");
        await import("../utils.js");

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            update_command_button_state: jest.fn(),
            should_disable_command_button: jest.fn(() => false)
        }));

        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        global.WCHttp = {
            request: jest.fn(),
            getJson: jest.fn(),
            isHttpError: jest.fn().mockReturnValue(false),
        };

        global.url_for_run = jest.fn((path) => path);

        clickHandler = null;
        mapStub = {
            addLayer: jest.fn(),
            removeLayer: jest.fn(),
            registerOverlay: jest.fn(),
            unregisterOverlay: jest.fn(),
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            on: jest.fn((eventName, handler) => {
                if (eventName === "click") {
                    clickHandler = handler;
                }
            }),
            off: jest.fn(),
        };

        global.MapController = {
            getInstance: jest.fn(() => mapStub),
        };

        function Layer(props) {
            this.props = props || {};
            this.id = props ? props.id : undefined;
        }
        global.deck = {
            GeoJsonLayer: Layer,
            TextLayer: Layer,
            IconLayer: Layer,
        };

        await import("../outlet_gl.js");
        outlet = window.Outlet.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Outlet;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.MapController;
        delete global.url_for_run;
        delete global.deck;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        if (global.WCControllerBootstrap) {
            delete global.WCControllerBootstrap;
        }
        if (global.WCUtils) {
            delete global.WCUtils;
        }
        document.body.innerHTML = "";
    });

    test("cursor click submits outlet and creates temp layers", async () => {
        outlet.bootstrap({});
        outlet.setCursorSelection(true);

        global.WCHttp.request.mockResolvedValueOnce({ body: { Success: true, job_id: "job-123" } });

        await clickHandler({ latlng: { lat: 45.1, lng: -120.3 } });

        expect(global.WCHttp.request).toHaveBeenCalledWith(
            "rq/api/set_outlet",
            expect.objectContaining({
                method: "POST",
                json: { latitude: 45.1, longitude: -120.3 },
                form: expect.any(HTMLFormElement),
            })
        );
        expect(outlet.tempSelectionLayer).toBeTruthy();
        expect(outlet.tempDialogLayer).toBeTruthy();
        expect(mapStub.addLayer).toHaveBeenCalledTimes(2);
        expect(outlet.cursorSelectionOn).toBe(false);
    });

    test("completion clears temp layers", async () => {
        outlet.bootstrap({});
        outlet.setCursorSelection(true);

        global.WCHttp.request.mockResolvedValueOnce({ body: { Success: true, job_id: "job-123" } });
        global.WCHttp.getJson.mockResolvedValueOnce({ lat: 45.2, lng: -120.4 });
        global.WCHttp.request.mockResolvedValueOnce({ body: "<div>Report</div>" });

        await clickHandler({ latlng: { lat: 45.1, lng: -120.3 } });

        outlet.triggerEvent("SET_OUTLET_TASK_COMPLETED", {});
        await Promise.resolve();
        await Promise.resolve();

        expect(outlet.tempSelectionLayer).toBeNull();
        expect(outlet.tempDialogLayer).toBeNull();
        expect(mapStub.removeLayer).toHaveBeenCalled();
    });

    test("show renders outlet marker and registers overlay", async () => {
        global.WCHttp.getJson.mockResolvedValueOnce({ lat: 45.3, lng: -120.5 });
        global.WCHttp.request.mockResolvedValueOnce({ body: "<div>Report</div>" });

        outlet.show();
        await Promise.resolve();
        await Promise.resolve();

        expect(mapStub.addLayer).toHaveBeenCalledWith(expect.any(Object));
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Outlet");
        expect(outlet.outletLayer).toBeTruthy();

        const outletLayer = outlet.outletLayer;
        const outletData = outletLayer.props.data[0];
        const iconKey = outletLayer.props.getIcon(outletData);
        const mapping = outletLayer.props.iconMapping[iconKey];

        expect(outletLayer.props.iconAtlas).toContain("/static/images/map-marker.png");
        expect(iconKey).toBe("outlet-pin");
        expect(mapping.width).toBe(198);
        expect(mapping.height).toBe(320);
        expect(mapping.anchorX).toBe(99);
        expect(mapping.anchorY).toBe(320);
        expect(mapping.mask).toBe(false);
        expect(outletLayer.props.sizeUnits).toBe("meters");
        expect(outletLayer.props.getSize()).toBe(360);
        expect(outletLayer.props.sizeScale).toBe(1);
    });

    test("bootstrap honors controllerContext.hasOutlet when watershed is missing", async () => {
        global.WCControllerBootstrap = {
            getControllerContext: jest.fn(() => ({ hasOutlet: true })),
        };

        outlet.show = jest.fn();
        outlet.bootstrap({});

        expect(outlet.show).toHaveBeenCalledTimes(1);
    });
});

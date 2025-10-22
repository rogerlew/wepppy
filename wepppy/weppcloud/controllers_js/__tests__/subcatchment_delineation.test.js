/**
 * @jest-environment jsdom
 */

describe("Subcatchment Delineation controller", () => {
    let httpPostJsonMock;
    let httpRequestMock;
    let baseInstance;
    let wsClientInstance;
    let mapInstance;
    let subcatchment;
    let delegateSpy;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <form id="build_subcatchments_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <input type="checkbox" name="clip_hillslopes" checked>
            </form>
            <div id="sub_legend"></div>
            <input type="radio"
                   id="wepp_sub_cmap_radio_runoff"
                   name="wepp_sub_cmap_radio"
                   value="sub_runoff"
                   data-subcatchment-role="cmap-option">
            <input type="range"
                   id="wepp_sub_cmap_range_runoff"
                   data-subcatchment-role="scale-range"
                   data-subcatchment-scale="runoff">
        `;

        global.render_legend = jest.fn();

        await import("../utils.js");
        global.fromHex = jest.fn(() => ({ r: 1, g: 1, b: 1, a: 1 }));
        global.linearToLog = jest.fn(() => 1);
        global.createColormap = jest.fn(() => ({ map: jest.fn(() => "#ffffff") }));
        global.updateRangeMaxLabel_mm = jest.fn();
        global.updateRangeMaxLabel_kgha = jest.fn();
        global.updateRangeMaxLabel_tonneha = jest.fn();

        await import("../dom.js");
        delegateSpy = jest.spyOn(global.WCDom, "delegate");

        global.WCForms = {
            serializeForm: jest.fn(() => ({
                clip_hillslopes: true,
            })),
        };

        function createEmitter() {
            const listeners = {};
            return {
                on(event, handler) {
                    (listeners[event] = listeners[event] || []).push(handler);
                    return () => {
                        listeners[event] = (listeners[event] || []).filter((fn) => fn !== handler);
                    };
                },
                once(event, handler) {
                    const unsubscribe = this.on(event, (payload) => {
                        unsubscribe();
                        handler(payload);
                    });
                    return unsubscribe;
                },
                off(event, handler) {
                    if (!listeners[event]) {
                        return;
                    }
                    if (!handler) {
                        listeners[event] = [];
                        return;
                    }
                    listeners[event] = listeners[event].filter((fn) => fn !== handler);
                },
                emit(event, payload) {
                    (listeners[event] || []).slice().forEach((fn) => fn(payload));
                },
                listenerCount(event) {
                    if (event) {
                        return (listeners[event] || []).length;
                    }
                    return Object.keys(listeners).reduce((total, key) => total + (listeners[key] || []).length, 0);
                },
            };
        }

        global.WCEvents = {
            createEmitter,
            useEventMap: jest.fn((events, emitter) => emitter),
        };

        httpPostJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-77" } }));
        httpRequestMock = jest.fn(() => Promise.resolve({ body: {} }));

        global.WCHttp = {
            postJson: httpPostJsonMock,
            request: httpRequestMock,
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

        const glLayer = {
            remove: jest.fn(),
            setStyle: jest.fn(),
            addTo: jest.fn(() => glLayer),
        };

        mapInstance = {
            ctrls: {
                removeLayer: jest.fn(),
                addOverlay: jest.fn(),
            },
            removeLayer: jest.fn(),
            sub_legend: {
                html: jest.fn(),
            },
            subQuery: jest.fn(),
        };
        global.MapController = {
            getInstance: jest.fn(() => mapInstance),
        };

        global.ChannelDelineation = { getInstance: jest.fn(() => ({ show: jest.fn() })) };
        global.Wepp = { getInstance: jest.fn(() => ({ updatePhosphorus: jest.fn() })) };
        global.Project = { getInstance: jest.fn(() => ({ set_preferred_units: jest.fn() })) };
        global.UnitizerClient = { ready: jest.fn(() => Promise.resolve({
            renderValue: jest.fn((value) => `${value}`),
            renderUnits: jest.fn(() => "kg/m^2"),
        })) };
        global.url_for_run = jest.fn((path) => path);
        global.polylabel = jest.fn(() => [0, 0]);

        global.L = {
            layerGroup: jest.fn(() => ({
                clearLayers: jest.fn(),
                addLayer: jest.fn(),
            })),
            glify: {
                layer: jest.fn(() => glLayer),
            },
            marker: jest.fn(() => ({
                addTo: jest.fn(),
            })),
            divIcon: jest.fn(() => ({})),
        };

        await import("../subcatchment_delineation.js");
        subcatchment = window.SubcatchmentDelineation.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.SubcatchmentDelineation;
        delete global.WCHttp;
        delete global.WCForms;
        delete global.WCEvents;
        delete global.controlBase;
        delete global.WSClient;
        delete global.MapController;
        delete global.ChannelDelineation;
        delete global.Wepp;
        delete global.Project;
        delete global.UnitizerClient;
        delete global.url_for_run;
        delete global.polylabel;
        delete global.L;
        delete global.render_legend;
        delete global.fromHex;
        delete global.linearToLog;
        delete global.createColormap;
        delete global.updateRangeMaxLabel_mm;
        delete global.updateRangeMaxLabel_kgha;
        delete global.updateRangeMaxLabel_tonneha;
        if (delegateSpy) {
            delegateSpy.mockRestore();
            delegateSpy = undefined;
        }
        document.body.innerHTML = "";
    });

    test("build posts JSON payload and records job id", async () => {
        subcatchment.build();
        await Promise.resolve();
        await Promise.resolve();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "rq/api/build_subcatchments_and_abstract_watershed",
            { clip_hillslopes: true },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(wsClientInstance.connect).toHaveBeenCalled();
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(subcatchment, "job-77");
    });

    test("registers delegated handlers for map controls", () => {
        expect(delegateSpy).toBeDefined();
        const changeCall = delegateSpy.mock.calls.find(([root, eventName, selector]) => root === document && eventName === "change" && selector === "[data-subcatchment-role='cmap-option']");
        const inputCall = delegateSpy.mock.calls.find(([root, eventName, selector]) => root === document && eventName === "input" && selector === "[data-subcatchment-role='scale-range']");
        expect(changeCall).toBeDefined();
        expect(inputCall).toBeDefined();
    });

    test("build errors propagate through controller events", async () => {
        const httpError = { name: "HttpError", detail: "failure" };
        httpPostJsonMock.mockRejectedValueOnce(httpError);
        global.WCHttp.isHttpError.mockImplementation((err) => err === httpError);

        const events = [];
        subcatchment.events.on("subcatchment:build:error", (payload) => events.push(payload));

        subcatchment.build();
        await Promise.resolve();
        await Promise.resolve();

        expect(events).toHaveLength(1);
        expect(events[0].error).toEqual({ Error: "failure" });
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalled();
    });
});

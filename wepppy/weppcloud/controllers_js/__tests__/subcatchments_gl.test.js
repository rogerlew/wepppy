/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("SubcatchmentDelineation GL controller", () => {
    let requestMock;
    let postJsonMock;
    let baseInstance;
    let mapStub;
    let layers;
    function flushPromises(times = 2) {
        let chain = Promise.resolve();
        for (let i = 0; i < times; i += 1) {
            chain = chain.then(() => new Promise((resolve) => setTimeout(resolve, 0)));
        }
        return chain;
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="build_subcatchments_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="braille"></div>
                <button type="button" id="btn_build_subcatchments" data-subcatchment-action="build">Build</button>
            </form>
            <div id="subcatchments_stacktrace_panel"></div>
            <small id="hint_build_subcatchments"></small>
            <div id="sub_legend"></div>
            <input type="radio" id="sub_cmap_radio_dom_lc">
            <input type="radio" id="sub_cmap_radio_dom_soil">
            <input type="radio" id="sub_cmap_radio_slope">
            <input type="radio" id="sub_cmap_radio_aspect">
            <input type="radio" id="sub_cmap_radio_rangeland_cover">
            <input type="range"
                   id="wepp_sub_cmap_range_runoff"
                   value="50"
                   data-subcatchment-role="scale-range"
                   data-subcatchment-scale="runoff">
            <input type="range"
                   id="wepp_sub_cmap_range_loss"
                   value="50"
                   data-subcatchment-role="scale-range"
                   data-subcatchment-scale="loss">
            <input type="range"
                   id="wepp_grd_cmap_range_loss"
                   value="10"
                   data-subcatchment-role="scale-range"
                   data-subcatchment-scale="grd_loss">
            <span id="wepp_sub_cmap_canvas_runoff_min"></span>
            <span id="wepp_sub_cmap_canvas_runoff_max"></span>
            <span id="wepp_sub_cmap_canvas_loss_min"></span>
            <span id="wepp_sub_cmap_canvas_loss_max"></span>
            <span id="wepp_grd_cmap_range_loss_min"></span>
            <span id="wepp_grd_cmap_range_loss_max"></span>
            <span id="wepp_grd_cmap_range_loss_units"></span>
        `;

        HTMLCanvasElement.prototype.getContext = jest.fn(() => ({
            createImageData: (width, height) => ({ data: new Uint8ClampedArray(width * height * 4) }),
            putImageData: jest.fn(),
        }));

        await import("../dom.js");
        await import("../forms.js");
        await import("../utils.js");

        global.createColormap = jest.fn(() => ({ map: jest.fn(() => "#ff0000") }));
        global.render_legend = jest.fn();
        global.UnitizerClient = {
            ready: jest.fn(() => Promise.resolve({
                renderValue: jest.fn((value, unit) => `${value} ${unit || ""}`.trim()),
                renderUnits: jest.fn(() => "kg/m^2"),
            })),
        };
        const emitter = {
            on: jest.fn(),
            once: jest.fn(),
            off: jest.fn(),
            emit: jest.fn(),
            listenerCount: jest.fn(() => 0),
        };
        global.WCEvents = {
            createEmitter: jest.fn(() => emitter),
            useEventMap: jest.fn((eventsList, baseEmitter) => baseEmitter),
        };

        requestMock = jest.fn(() => Promise.resolve({ body: {} }));
        postJsonMock = jest.fn(() => Promise.resolve({ body: { records: [] } }));

        global.WCHttp = {
            request: requestMock,
            getJson: requestMock,
            postJson: postJsonMock,
            isHttpError: jest.fn().mockReturnValue(false),
        };
        global.WCForms = {
            serializeForm: jest.fn(() => ({ clip_hillslopes: true })),
        };

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
            attach_status_stream: jest.fn(),
            connect_status_stream: jest.fn(),
            disconnect_status_stream: jest.fn(),
            reset_panel_state: jest.fn(),
            set_rq_job_id: jest.fn(),
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        layers = [];
        mapStub = {
            addLayer: jest.fn((layer) => {
                layers.push(layer);
            }),
            removeLayer: jest.fn((layer) => {
                layers = layers.filter((item) => item !== layer);
            }),
            hasLayer: jest.fn((layer) => layers.indexOf(layer) !== -1),
            registerOverlay: jest.fn(),
            unregisterOverlay: jest.fn(),
            clearFindFlashCache: jest.fn(),
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            sub_legend: {
                html: jest.fn(),
            },
            subQuery: jest.fn(),
        };
        global.MapController = {
            getInstance: jest.fn(() => mapStub),
        };

        function GeoJsonLayer(props) {
            this.props = props || {};
            this.id = props ? props.id : undefined;
        }
        function TextLayer(props) {
            this.props = props || {};
            this.id = props ? props.id : undefined;
        }
        function BitmapLayer(props) {
            this.props = props || {};
            this.id = props ? props.id : undefined;
        }
        global.deck = {
            GeoJsonLayer,
            TextLayer,
            BitmapLayer,
        };

        global.url_for_run = jest.fn((path) => `/runs/test/cfg/${path}`);

        window.history.pushState({}, "", "/runs/test/cfg/");

        global.fetch = jest.fn(() => Promise.resolve({
            ok: true,
            arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
        }));
        global.GeoTIFF = {
            fromArrayBuffer: jest.fn(() => Promise.resolve({
                getImage: jest.fn(() => Promise.resolve({
                    getWidth: () => 2,
                    getHeight: () => 2,
                    readRasters: () => Promise.resolve(new Uint8Array([0, 1, 2, 3])),
                    getBoundingBox: () => [0, 0, 1, 1],
                })),
            })),
        };

        await import("../subcatchments_gl.js");
    });

    afterEach(() => {
        delete window.SubcatchmentDelineation;
        delete global.WCHttp;
        delete global.WCEvents;
        delete global.controlBase;
        delete global.MapController;
        delete global.deck;
        delete global.createColormap;
        delete global.render_legend;
        delete global.UnitizerClient;
        delete global.url_for_run;
        delete global.fetch;
        delete global.GeoTIFF;
        if (global.ChannelDelineation) {
            delete global.ChannelDelineation;
        }
        if (global.Wepp) {
            delete global.Wepp;
        }
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
    });

    test("show loads subcatchments and registers overlays", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        requestMock.mockResolvedValueOnce({
            body: {
                type: "FeatureCollection",
                features: [
                    {
                        type: "Feature",
                        properties: { TopazID: 1 },
                        geometry: {
                            type: "Polygon",
                            coordinates: [[
                                [-120.1, 45.1],
                                [-120.2, 45.1],
                                [-120.2, 45.2],
                                [-120.1, 45.2],
                                [-120.1, 45.1],
                            ]],
                        },
                    },
                ],
            },
        });

        await sub.show();

        expect(requestMock).toHaveBeenCalledWith(
            "/runs/test/cfg/resources/subcatchments.json",
            expect.objectContaining({ params: expect.any(Object) }),
        );
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Subcatchments");
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Subcatchment Labels");
        expect(mapStub.addLayer).toHaveBeenCalledWith(expect.any(Object));
        expect(mapStub.clearFindFlashCache).toHaveBeenCalledWith("subcatchments");
        expect(sub.glLayer).toBeTruthy();
    });

    test("build posts payload and sets job id", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        postJsonMock.mockResolvedValueOnce({
            body: { Success: true, job_id: "job-123" },
        });

        await sub.build();

        expect(baseInstance.reset_panel_state).toHaveBeenCalledWith(
            sub,
            expect.objectContaining({ taskMessage: "Building Subcatchments" }),
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(sub);
        expect(postJsonMock).toHaveBeenCalledWith(
            "/runs/test/cfg/rq/api/build_subcatchments_and_abstract_watershed",
            expect.any(Object),
            expect.objectContaining({ form: expect.any(HTMLFormElement) }),
        );
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(sub, "job-123");
    });

    test("setColorMap updates loss style and legend labels", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        requestMock
            .mockResolvedValueOnce({
                body: {
                    type: "FeatureCollection",
                    features: [
                        {
                            type: "Feature",
                            properties: { TopazID: 1, WeppID: "1" },
                            geometry: {
                                type: "Polygon",
                                coordinates: [[
                                    [-120.1, 45.1],
                                    [-120.2, 45.1],
                                    [-120.2, 45.2],
                                    [-120.1, 45.2],
                                    [-120.1, 45.1],
                                ]],
                            },
                        },
                    ],
                },
            });

        postJsonMock.mockResolvedValueOnce({
            body: {
                records: [{ wepp_id: "1", value: 5 }],
            },
        });

        await sub.show();
        sub.setColorMap("sub_loss");
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith(
            "http://localhost/query-engine/runs/test/query",
            expect.any(Object),
            expect.any(Object),
        );
        expect(sub.state.cmapMode).toBe("loss");
        await Promise.resolve();
        expect(document.getElementById("wepp_sub_cmap_canvas_loss_min").textContent).not.toBe("");
        expect(document.getElementById("wepp_sub_cmap_canvas_loss_max").textContent).not.toBe("");
    });

    test("setColorMap slp_asp maps to slope normalization", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        requestMock
            .mockResolvedValueOnce({
                body: {
                    type: "FeatureCollection",
                    features: [
                        {
                            type: "Feature",
                            properties: { TopazID: 1 },
                            geometry: {
                                type: "Polygon",
                                coordinates: [[
                                    [-120.1, 45.1],
                                    [-120.2, 45.1],
                                    [-120.2, 45.2],
                                    [-120.1, 45.2],
                                    [-120.1, 45.1],
                                ]],
                            },
                        },
                    ],
                },
            })
            .mockResolvedValueOnce({
                body: {
                    "1": { slope_scalar: 0.25, aspect: 180 },
                },
            });

        await sub.show();
        sub.setColorMap("slp_asp");
        await flushPromises();

        const mapper = sub.state.colorMappers.slopeAspect;
        sub.glLayer.props.getFillColor({ properties: { TopazID: 1 } });

        expect(sub.state.cmapMode).toBe("slope");
        expect(mapper.map).toHaveBeenCalledWith(0.25);
    });

    test("setColorMap aspect uses hue wheel colors", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        requestMock
            .mockResolvedValueOnce({
                body: {
                    type: "FeatureCollection",
                    features: [
                        {
                            type: "Feature",
                            properties: { TopazID: 1 },
                            geometry: {
                                type: "Polygon",
                                coordinates: [[
                                    [-120.1, 45.1],
                                    [-120.2, 45.1],
                                    [-120.2, 45.2],
                                    [-120.1, 45.2],
                                    [-120.1, 45.1],
                                ]],
                            },
                        },
                    ],
                },
            })
            .mockResolvedValueOnce({
                body: {
                    "1": { slope_scalar: 0.25, aspect: 180 },
                },
            });

        await sub.show();
        sub.setColorMap("aspect");
        await flushPromises();

        const mapper = sub.state.colorMappers.slopeAspect;
        const color = sub.glLayer.props.getFillColor({ properties: { TopazID: 1 } });

        expect(sub.state.cmapMode).toBe("aspect");
        expect(mapper.map).not.toHaveBeenCalled();
        expect(color).toEqual([55, 255, 255, 230]);
    });

    test("range slider updates trigger style refresh", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        requestMock.mockResolvedValueOnce({
            body: {
                type: "FeatureCollection",
                features: [
                    {
                        type: "Feature",
                        properties: { TopazID: 1, WeppID: "1" },
                        geometry: {
                            type: "Polygon",
                            coordinates: [[
                                [-120.1, 45.1],
                                [-120.2, 45.1],
                                [-120.2, 45.2],
                                [-120.1, 45.2],
                                [-120.1, 45.1],
                            ]],
                        },
                    },
                ],
            },
        });

        postJsonMock.mockResolvedValueOnce({
            body: {
                records: [{ wepp_id: "1", value: 5 }],
            },
        });

        await sub.show();
        sub.setColorMap("sub_runoff");
        await flushPromises();

        const initialAddCount = mapStub.addLayer.mock.calls.length;
        const slider = document.getElementById("wepp_sub_cmap_range_runoff");
        slider.value = "70";
        slider.dispatchEvent(new Event("input", { bubbles: true }));

        expect(mapStub.addLayer.mock.calls.length).toBeGreaterThan(initialAddCount);
    });

    test("setColorMap grd_loss adds raster overlay", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        requestMock.mockResolvedValueOnce({
            body: {
                type: "FeatureCollection",
                features: [],
            },
        });

        await sub.show();
        sub.setColorMap("grd_loss");
        await flushPromises();

        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Gridded Output");
        expect(mapStub.addLayer).toHaveBeenCalledWith(expect.any(Object));
    });

    test("completion events are idempotent and trigger report wiring", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();
        sub.show = jest.fn(() => Promise.resolve());
        sub.report = jest.fn(() => Promise.resolve());
        sub.enableColorMap = jest.fn();

        const channelShow = jest.fn();
        global.ChannelDelineation = { getInstance: jest.fn(() => ({ show: channelShow })) };
        const updatePhosphorus = jest.fn();
        global.Wepp = { getInstance: jest.fn(() => ({ updatePhosphorus })) };

        sub.triggerEvent("BUILD_SUBCATCHMENTS_TASK_COMPLETED", {});
        sub.triggerEvent("BUILD_SUBCATCHMENTS_TASK_COMPLETED", {});

        expect(sub.show).toHaveBeenCalledTimes(1);
        expect(channelShow).toHaveBeenCalledTimes(1);

        sub.triggerEvent("WATERSHED_ABSTRACTION_TASK_COMPLETED", {});
        sub.triggerEvent("WATERSHED_ABSTRACTION_TASK_COMPLETED", {});

        expect(sub.report).toHaveBeenCalledTimes(1);
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(sub);
        expect(sub.enableColorMap).toHaveBeenCalledWith("slope");
        expect(updatePhosphorus).toHaveBeenCalled();
        expect(sub.show).toHaveBeenCalledTimes(1);
    });

    test("updateLayerAvailability enables preflight-gated radios", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();

        const slope = document.getElementById("sub_cmap_radio_slope");
        const aspect = document.getElementById("sub_cmap_radio_aspect");
        const domLc = document.getElementById("sub_cmap_radio_dom_lc");
        const domSoil = document.getElementById("sub_cmap_radio_dom_soil");
        const rangeland = document.getElementById("sub_cmap_radio_rangeland_cover");
        slope.disabled = true;
        aspect.disabled = true;
        domLc.disabled = true;
        domSoil.disabled = true;
        rangeland.disabled = true;

        window.lastPreflightChecklist = {
            subcatchments: true,
            landuse: true,
            rangeland_cover: true,
            soils: true,
        };

        sub.updateLayerAvailability();

        expect(slope.disabled).toBe(false);
        expect(aspect.disabled).toBe(false);
        expect(domLc.disabled).toBe(false);
        expect(domSoil.disabled).toBe(false);
        expect(rangeland.disabled).toBe(false);
    });

    test("watershed completion loads subcatchments when build completion was not seen", async () => {
        const sub = window.SubcatchmentDelineation.getInstance();
        sub.show = jest.fn(() => Promise.resolve());
        sub.report = jest.fn(() => Promise.resolve());
        sub.enableColorMap = jest.fn();

        sub._completion_seen = {
            BUILD_SUBCATCHMENTS_TASK_COMPLETED: false,
            WATERSHED_ABSTRACTION_TASK_COMPLETED: false,
        };

        sub.triggerEvent("WATERSHED_ABSTRACTION_TASK_COMPLETED", {});

        expect(sub.show).toHaveBeenCalledTimes(1);
        expect(sub.report).toHaveBeenCalledTimes(1);
    });

    test("watershed completion schedules a follow-up show when build completion is missing", async () => {
        jest.useFakeTimers();
        const sub = window.SubcatchmentDelineation.getInstance();
        sub.show = jest.fn(() => Promise.resolve());

        const channelShow = jest.fn();
        global.ChannelDelineation = { getInstance: jest.fn(() => ({ show: channelShow })) };

        sub._completion_seen = {
            BUILD_SUBCATCHMENTS_TASK_COMPLETED: false,
            WATERSHED_ABSTRACTION_TASK_COMPLETED: false,
        };

        sub.triggerEvent("WATERSHED_ABSTRACTION_TASK_COMPLETED", {});

        expect(sub.show).toHaveBeenCalledTimes(1);

        jest.runOnlyPendingTimers();

        expect(sub.show).toHaveBeenCalledTimes(2);
        expect(channelShow).toHaveBeenCalledTimes(2);
        jest.useRealTimers();
    });
});

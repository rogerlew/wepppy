/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Omni contrast overlays controller", () => {
    let getJsonMock;
    let mapStub;
    let baseInstance;
    let mapEventHandlers;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = "<div></div>";
        mapEventHandlers = {};

        getJsonMock = jest.fn(() => Promise.resolve({
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: { contrast_label: "101" },
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
        }));

        global.WCHttp = {
            getJson: getJsonMock,
            request: jest.fn(() => Promise.resolve({})),
        };

        let layers = [];
        mapStub = {
            addLayer: jest.fn((layer) => {
                layers.push(layer);
            }),
            removeLayer: jest.fn((layer) => {
                layers = layers.filter((item) => item !== layer);
            }),
            hasLayer: jest.fn((layer) => layers.indexOf(layer) !== -1),
            registerOverlay: jest.fn(),
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            events: {
                on: jest.fn((eventName, handler) => {
                    if (!mapEventHandlers[eventName]) {
                        mapEventHandlers[eventName] = [];
                    }
                    mapEventHandlers[eventName].push(handler);
                }),
            },
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
        global.deck = {
            GeoJsonLayer,
            TextLayer,
        };

        global.url_for_run = jest.fn((path) => `/runs/test/cfg/${path}`);

        const omniEmitter = { on: jest.fn() };
        global.Omni = {
            getInstance: jest.fn(() => ({ events: omniEmitter })),
        };

        ({ base: baseInstance } = createControlBaseStub());
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        await import("../omni_contrasts_gl.js");
    });

    afterEach(() => {
        delete window.OmniContrastOverlays;
        delete global.WCHttp;
        delete global.MapController;
        delete global.deck;
        delete global.url_for_run;
        delete global.controlBase;
        delete global.Omni;
        document.body.innerHTML = "";
    });

    test("bootstrap registers contrast overlays and uses browse download route", async () => {
        const controller = window.OmniContrastOverlays.getInstance();
        controller.bootstrap({ data: { omni: { hasRanContrasts: true } } });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(global.url_for_run).toHaveBeenCalledWith(
            "download/omni/contrasts/contrast_ids.wgs.geojson"
        );
        expect(getJsonMock).toHaveBeenCalledWith(
            "/runs/test/cfg/download/omni/contrasts/contrast_ids.wgs.geojson",
            expect.objectContaining({ params: expect.any(Object) }),
        );
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Contrast IDs");
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Contrast ID Labels");
        expect(mapStub.addLayer).not.toHaveBeenCalled();
    });

    test("toggling contrast overlay off clears hover state", async () => {
        const controller = window.OmniContrastOverlays.getInstance();
        controller.bootstrap({ data: { omni: { hasRanContrasts: true } } });

        await new Promise((resolve) => setTimeout(resolve, 0));

        const feature = controller.state.data.features[0];
        controller.state.layer.props.onHover({ object: feature });

        expect(controller.state.hoveredKey).toBe("101");
        expect(controller.state.hoverLabelLayer).not.toBeNull();

        mapEventHandlers["map:layer:toggled"].forEach((handler) => {
            handler({ name: "Contrast IDs", visible: false });
        });

        expect(controller.state.hoveredKey).toBeNull();
        expect(controller.state.hoverLabelLayer).toBeNull();
    });
});

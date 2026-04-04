/**
 * @jest-environment jsdom
 */

describe("Roads map overlay controller", () => {
    let getJsonMock;
    let mapStub;
    let mapEventHandlers;
    let layerSet;

    function roadsPayload() {
        return {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: {
                        type: "LineString",
                        coordinates: [
                            [-117.0, 46.0],
                            [-117.001, 46.001],
                            [-117.002, 46.002],
                        ],
                    },
                    properties: {
                        segment_id: "roads-seg-000101",
                        design: "inslope_bd",
                        surface: "gravel",
                        traffic: "low",
                    },
                },
            ],
        };
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = '<div id="mapid"></div>';
        layerSet = [];
        mapEventHandlers = {};

        getJsonMock = jest.fn(() => Promise.resolve(roadsPayload()));

        global.WCHttp = {
            getJson: getJsonMock,
            request: jest.fn(),
            isHttpError: jest.fn((error) => Boolean(error && error.name === "HttpError")),
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
            useEventMap: jest.fn((_names, base) => base),
        };

        mapStub = {
            addLayer: jest.fn((layer) => {
                if (layerSet.indexOf(layer) === -1) {
                    layerSet.push(layer);
                }
            }),
            removeLayer: jest.fn((layer) => {
                layerSet = layerSet.filter((item) => item !== layer);
            }),
            hasLayer: jest.fn((layer) => layerSet.indexOf(layer) !== -1),
            registerOverlay: jest.fn(),
            unregisterOverlay: jest.fn(),
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            events: {
                on: jest.fn((eventName, handler) => {
                    mapEventHandlers[eventName] = handler;
                }),
            },
            roadQuery: jest.fn(),
            _deck: {
                getViewports: jest.fn(() => [{
                    unproject: jest.fn(() => [-117.01, 46.01]),
                }]),
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
            GeoJsonLayer: GeoJsonLayer,
            TextLayer: TextLayer,
        };

        global.url_for_run = jest.fn((path) => `/runs/test/cfg/${path}`);

        await import("../map_gl_shared.js");
        await import("../roads_gl.js");
    });

    afterEach(() => {
        delete window.RoadsMapOverlay;
        delete window.WCMapGlShared;
        delete global.RoadsMapOverlay;
        delete global.WCHttp;
        delete global.WCEvents;
        delete global.MapController;
        delete global.deck;
        delete global.url_for_run;
    });

    test("show registers roads overlays and adds roads layer", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();

        await roadsMap.show();

        expect(getJsonMock).toHaveBeenCalledWith(
            "/runs/test/cfg/resources/roads.json",
            expect.objectContaining({ params: expect.any(Object) }),
        );
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Roads");
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Road Labels");
        expect(mapStub.addLayer).toHaveBeenCalledWith(roadsMap.state.glLayer);
        expect(roadsMap.state.labelLayer).toBeTruthy();
    });

    test("show removes overlays when roads prepare artifacts are unavailable", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();

        await roadsMap.show();
        getJsonMock.mockRejectedValueOnce({
            name: "HttpError",
            status: 404,
            message: "Prepared roads segments not found.",
        });

        await roadsMap.show();

        expect(roadsMap.state.glLayer).toBeNull();
        expect(roadsMap.state.labelLayer).toBeNull();
        expect(mapStub.unregisterOverlay).toHaveBeenCalled();
    });

    test("hover adds highlighted segment + compact label and click routes to roadQuery", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        await roadsMap.show();

        const feature = roadsMap.state.glData.features[0];
        roadsMap.state.glLayer.props.onHover({ object: feature, x: 120, y: 80 });

        expect(roadsMap.state.hoverLayer).toBeTruthy();
        expect(mapStub.addLayer).toHaveBeenCalledWith(roadsMap.state.hoverLayer, { skipRefresh: true });
        expect(roadsMap.state.hoverLabelLayer).toBeTruthy();
        expect(roadsMap.state.hoverLabelLayer.props.data[0].text).toBe("roads-seg-000101");

        roadsMap.state.glLayer.props.onClick({ object: feature });
        expect(mapStub.roadQuery).toHaveBeenCalledWith("roads-seg-000101");
    });

    test("hover on the same segment does not rebuild hover layers", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        await roadsMap.show();

        const feature = roadsMap.state.glData.features[0];
        roadsMap.state.glLayer.props.onHover({ object: feature, x: 120, y: 80 });
        const addLayerCountAfterFirstHover = mapStub.addLayer.mock.calls.length;

        roadsMap.state.glLayer.props.onHover({ object: feature, x: 126, y: 84 });

        expect(mapStub.addLayer.mock.calls).toHaveLength(addLayerCountAfterFirstHover);
    });

    test("show refresh clears hover artifacts before rebuilding overlays", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        await roadsMap.show();

        const feature = roadsMap.state.glData.features[0];
        roadsMap.state.glLayer.props.onHover({ object: feature, x: 120, y: 80 });

        const hoverLayer = roadsMap.state.hoverLayer;
        const hoverLabelLayer = roadsMap.state.hoverLabelLayer;
        expect(hoverLayer).toBeTruthy();
        expect(hoverLabelLayer).toBeTruthy();

        await roadsMap.show();

        expect(mapStub.removeLayer).toHaveBeenCalledWith(hoverLayer, { skipOverlay: true });
        expect(mapStub.removeLayer).toHaveBeenCalledWith(hoverLabelLayer, { skipOverlay: true });
        expect(roadsMap.state.hoverLayer).toBeNull();
        expect(roadsMap.state.hoverLabelLayer).toBeNull();
    });

    test("hover compact label is suppressed while Road Labels overlay is visible", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        await roadsMap.show();
        mapStub.addLayer(roadsMap.state.labelLayer);

        const feature = roadsMap.state.glData.features[0];
        roadsMap.state.glLayer.props.onHover({ object: feature, x: 100, y: 60 });

        expect(roadsMap.state.hoverLayer).toBeTruthy();
        expect(roadsMap.state.hoverLabelLayer).toBeNull();
    });

    test("layer toggle events clear roads hover artifacts", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        await roadsMap.show();

        const feature = roadsMap.state.glData.features[0];
        roadsMap.state.glLayer.props.onHover({ object: feature, x: 120, y: 80 });
        expect(roadsMap.state.hoverLayer).toBeTruthy();
        expect(roadsMap.state.hoverLabelLayer).toBeTruthy();

        mapEventHandlers["map:layer:toggled"]({ name: "Road Labels", visible: true });
        expect(roadsMap.state.hoverLabelLayer).toBeNull();
        expect(roadsMap.state.hoverLayer).toBeTruthy();

        mapEventHandlers["map:layer:toggled"]({ name: "Roads", visible: false });
        expect(roadsMap.state.hoverLayer).toBeNull();
        expect(roadsMap.state.hoverLabelLayer).toBeNull();
    });

    test("bootstrap only loads roads layers when roads mod is enabled", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        const showSpy = jest.spyOn(roadsMap, "show").mockResolvedValue(null);

        roadsMap.bootstrap({ mods: { flags: { roads: false } } });
        expect(showSpy).not.toHaveBeenCalled();

        roadsMap.bootstrap({ mods: { flags: { roads: true } } });
        expect(showSpy).toHaveBeenCalledTimes(1);
    });

    test("bootstrap refreshes roads overlay on roads completion events", async () => {
        const roadsMap = window.RoadsMapOverlay.getInstance();
        const showSpy = jest.spyOn(roadsMap, "show").mockResolvedValue(null);

        roadsMap.bootstrap({ mods: { flags: { roads: true } } });
        expect(showSpy).toHaveBeenCalledTimes(1);

        document.dispatchEvent(new Event("ROADS_PREPARE_TASK_COMPLETED"));
        document.dispatchEvent(new Event("ROADS_RUN_TASK_COMPLETED"));

        expect(showSpy).toHaveBeenCalledTimes(3);
    });
});

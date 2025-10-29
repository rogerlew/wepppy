/**
 * @jest-environment jsdom
 */

describe("Map controller", () => {
    let postJsonMock;
    let getJsonMock;
    let requestMock;
    let emittedEvents;
    let mapStub;
    let controlStub;
    let geoJsonMock;
    let tileLayerMock;
    let mapInstance;

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    function setupLeaflet() {
        const handlers = {};
        const panes = {};

        mapStub = {
            scrollWheelZoom: { disable: jest.fn() },
            createPane: jest.fn((name) => {
                panes[name] = panes[name] || { style: {} };
                return panes[name];
            }),
            getPane: jest.fn((name) => panes[name]),
            getContainer: jest.fn(() => document.getElementById("mapid")),
            on: jest.fn((event, handler) => {
                handlers[event] = handlers[event] || [];
                handlers[event].push(handler);
            }),
            handlers: handlers,
            getCenter: jest.fn(() => ({ lat: 46.8, lng: -117.5 })),
            getZoom: jest.fn(() => 12),
            getBounds: jest.fn(() => ({
                getSouthWest: () => ({ lat: 46.2, lng: -118.0 }),
                getNorthEast: () => ({ lat: 47.1, lng: -116.9 }),
                toBBoxString: () => "-118.0,46.2,-116.9,47.1",
            })),
            flyTo: jest.fn(),
            setView: jest.fn(),
            setZoom: jest.fn(),
            hasLayer: jest.fn(() => true),
            addLayer: jest.fn(),
            removeLayer: jest.fn(),
            invalidateSize: jest.fn(),
        };

        controlStub = {
            addTo: jest.fn(),
            addOverlay: jest.fn(),
        };

        tileLayerMock = jest.fn(() => ({
            addTo: jest.fn(),
        }));

        geoJsonMock = jest.fn(() => ({
            addTo: jest.fn(),
            clearLayers: jest.fn(),
            addData: jest.fn(),
        }));

        global.L = {
            map: jest.fn(() => mapStub),
            control: {
                layers: jest.fn(() => controlStub),
            },
            tileLayer: tileLayerMock,
            geoJSON: geoJsonMock,
            circleMarker: jest.fn(() => ({})),
        };
    }

    beforeEach(async () => {
        jest.resetModules();
        jest.useFakeTimers();

        global.runid = "test-run";
        global.config = "cfg";

        document.body.innerHTML = `
            <form id="setloc_form">
                <div class="wc-map-controls">
                    <input id="input_centerloc" type="text" />
                    <button type="button" id="btn_setloc" data-map-action="go">Go</button>
                    <button type="button" id="btn_find_topaz_id" data-map-action="find-topaz">Find Topaz</button>
                    <button type="button" id="btn_find_wepp_id" data-map-action="find-wepp">Find WEPP</button>
                </div>
                <div data-tabset>
                    <div role="tablist">
                        <button role="tab" class="is-active" aria-selected="true" data-tab-target="layers">Layers</button>
                        <button role="tab" aria-selected="false" data-tab-target="drilldown">Drilldown</button>
                    </div>
                    <div id="layers" role="tabpanel" class="is-active"></div>
                    <div id="drilldown" role="tabpanel" hidden></div>
                </div>
            </form>
            <div id="sub_legend"></div>
            <div id="sbs_legend"></div>
            <div id="mapstatus"></div>
            <span id="mouseelev"></span>
            <div id="mapid"></div>
        `;

        global.coordRound = jest.fn((value) => Math.round(value * 1000) / 1000);

        await import("../dom.js");

        emittedEvents = [];
        const emitter = {
            on: jest.fn(),
            once: jest.fn(),
            off: jest.fn(),
            emit: jest.fn((name, payload) => {
                emittedEvents.push({ name, payload });
            }),
            listenerCount: jest.fn().mockReturnValue(0),
        };
        global.WCEvents = {
            createEmitter: jest.fn(() => emitter),
            useEventMap: jest.fn((eventsList, baseEmitter) => baseEmitter),
        };

        postJsonMock = jest.fn(() => Promise.resolve({ body: { Elevation: 321.5 } }));
        getJsonMock = jest.fn(() => Promise.resolve({ type: "FeatureCollection", features: [] }));
        requestMock = jest.fn(() => Promise.resolve({ body: "<div>result</div>" }));

        global.WCHttp = {
            postJson: postJsonMock,
            getJson: getJsonMock,
            request: requestMock,
            isHttpError: jest.fn(() => false),
        };

        setupLeaflet();

        global.url_for_run = jest.fn((path) => path);
        global.Project = { getInstance: jest.fn(() => ({ set_preferred_units: jest.fn() })) };
        global.SubcatchmentDelineation = { getInstance: jest.fn(() => ({ onMapChange: jest.fn(), enableColorMap: jest.fn() })) };
        global.ChannelDelineation = { getInstance: jest.fn(() => ({ onMapChange: jest.fn() })) };
        global.WEPP_FIND_AND_FLASH = {
            ID_TYPE: { TOPAZ: "topaz", WEPP: "wepp" },
            FEATURE_TYPE: { SUBCATCHMENT: "sub", CHANNEL: "chn" },
            findAndFlashById: jest.fn(),
        };

        await import("../map.js");
        mapInstance = global.MapController.getInstance();
    });

    afterEach(() => {
        jest.useRealTimers();
        delete global.L;
        delete global.WCEvents;
        delete global.WCHttp;
        delete global.Project;
        delete global.SubcatchmentDelineation;
        delete global.ChannelDelineation;
        delete global.WEPP_FIND_AND_FLASH;
        delete global.coordRound;
        delete global.url_for_run;
        delete global.ResizeObserver;
        delete global.runid;
        delete global.config;
        emittedEvents = [];
    });

    test("activates tab panels", () => {
        mapInstance.tabset.activate("drilldown", true);

        const drilldownPanel = document.getElementById("drilldown");
        expect(drilldownPanel.classList.contains("is-active")).toBe(true);
        expect(drilldownPanel.hasAttribute("hidden")).toBe(false);
    });

    test("clicking Go triggers flyTo and event emission", () => {
        const input = document.getElementById("input_centerloc");
        input.value = "-117.52,46.88,13";

        document.querySelector('[data-map-action="go"]').click();

        expect(mapStub.flyTo).toHaveBeenCalledWith([46.88, -117.52], 13);
        expect(emittedEvents.some((evt) => evt.name === "map:center:requested")).toBe(true);
    });

    test("find topaz delegates to WEPP_FIND_AND_FLASH and loads subcatchment", () => {
        const input = document.getElementById("input_centerloc");
        input.value = "555";

        const subQuerySpy = jest.spyOn(mapInstance, "subQuery");
        global.WEPP_FIND_AND_FLASH.findAndFlashById.mockImplementation((options) => {
            options.onFlash({
                featureType: global.WEPP_FIND_AND_FLASH.FEATURE_TYPE.SUBCATCHMENT,
                hits: [{ properties: { TopazID: "555" } }],
            });
        });

        document.querySelector('[data-map-action="find-topaz"]').click();

        expect(global.WEPP_FIND_AND_FLASH.findAndFlashById).toHaveBeenCalled();
        expect(subQuerySpy).toHaveBeenCalledWith("555");
        expect(emittedEvents.some((evt) => evt.name === "map:search:requested" && evt.payload.type === "topaz")).toBe(true);
    });

    test("elevation fetch populates display and emits loaded event", async () => {
        const handler = mapStub.handlers.mousemove[0];
        handler({ latlng: { lat: 46.9, lng: -117.1 } });

        await flushPromises();
        jest.runOnlyPendingTimers();

        const mouse = document.getElementById("mouseelev");
        expect(mouse.textContent).toContain("321.5");
        expect(emittedEvents.some((evt) => evt.name === "map:elevation:loaded")).toBe(true);
        expect(postJsonMock).toHaveBeenCalledWith("/runs/test-run/cfg/elevationquery/", { lat: 46.9, lng: -117.1 }, expect.any(Object));
    });

    test("elevation error path emits error event", async () => {
        postJsonMock.mockResolvedValueOnce({ body: { Error: "Too far" } });
        const handler = mapStub.handlers.mousemove[0];
        handler({ latlng: { lat: 46.2, lng: -117.8 } });

        await flushPromises();
        jest.runOnlyPendingTimers();

        const mouse = document.getElementById("mouseelev");
        expect(mouse.textContent).toContain("Too far");
        expect(emittedEvents.some((evt) => evt.name === "map:elevation:error")).toBe(true);
    });

    test("loadUSGSGageLocations refreshes geojson when layer is active", async () => {
        const refreshSpy = jest.spyOn(mapInstance.usgs_gage, "refresh");
        mapStub.getZoom.mockReturnValue(10);
        mapStub.hasLayer.mockReturnValue(true);

        mapInstance.loadUSGSGageLocations();
        await flushPromises();

        expect(refreshSpy).toHaveBeenCalledWith("/resources/usgs/gage_locations/?&bbox=-118.0,46.2,-116.9,47.1");
    });

    test("overlayadd emits layer toggled event", () => {
        const overlayHandler = mapStub.handlers.overlayadd[0];
        overlayHandler({ layer: mapInstance.usgs_gage, name: "USGS Gage Locations" });

        expect(emittedEvents.some((evt) => evt.name === "map:layer:toggled" && evt.payload.visible === true)).toBe(true);
    });

    test("addGeoJsonOverlay fetches data and registers overlay", async () => {
        getJsonMock.mockResolvedValueOnce({ type: "FeatureCollection", features: [] });

        mapInstance.addGeoJsonOverlay({ url: "/resources/example", layerName: "Example" });
        await flushPromises();

        expect(getJsonMock).toHaveBeenCalledWith("/resources/example", expect.any(Object));
        expect(controlStub.addOverlay).toHaveBeenCalled();
        expect(emittedEvents.some((evt) => evt.name === "map:layer:refreshed" && evt.payload.name === "Example")).toBe(true);
    });

    test("bootstrap applies context and boundary overlay", () => {
        const resizeObserverMock = jest.fn(function (callback) {
            this.observe = jest.fn(() => callback());
        });
        global.ResizeObserver = resizeObserverMock;

        const setViewSpy = jest.spyOn(mapInstance, "setView");
        const addOverlaySpy = jest.spyOn(mapInstance, "addGeoJsonOverlay");
        const onMapChangeSpy = jest.spyOn(mapInstance, "onMapChange");

        mapInstance.bootstrap({
            map: {
                center: [46.25, -117.45],
                zoom: 11,
                boundary: {
                    url: "/resources/boundary",
                    layerName: "Run Boundary",
                    style: { color: "#00ff00", weight: 2 }
                }
            }
        });

        expect(setViewSpy).toHaveBeenCalledWith([46.25, -117.45], 11);
        expect(addOverlaySpy).toHaveBeenCalledWith({
            url: "/resources/boundary",
            layerName: "Run Boundary",
            style: { color: "#00ff00", weight: 2 }
        });
        expect(onMapChangeSpy).toHaveBeenCalled();
    });

    test("hillQuery respects drilldown suppression", () => {
        const activateSpy = jest.spyOn(mapInstance.tabset, "activate");
        requestMock.mockClear();

        mapInstance.suppressDrilldown("landuse-modify");
        mapInstance.hillQuery("report/sub_summary/1001/");

        expect(mapInstance.isDrilldownSuppressed()).toBe(true);
        expect(activateSpy).not.toHaveBeenCalled();
        expect(requestMock).not.toHaveBeenCalled();

        mapInstance.releaseDrilldown("landuse-modify");
        activateSpy.mockClear();
        mapInstance.hillQuery("report/sub_summary/1001/");

        expect(mapInstance.isDrilldownSuppressed()).toBe(false);
        expect(activateSpy).toHaveBeenCalledWith("drilldown", true);
        expect(requestMock).toHaveBeenCalledWith("report/sub_summary/1001/", expect.objectContaining({
            method: "GET",
            headers: expect.objectContaining({ Accept: "text/html,application/xhtml+xml" })
        }));
    });
});

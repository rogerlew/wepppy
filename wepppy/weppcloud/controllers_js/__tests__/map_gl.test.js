/**
 * @jest-environment jsdom
 */

describe("Map GL controller", () => {
    let emittedEvents;
    let deckInstance;
    let mapElement;

    beforeEach(async () => {
        jest.resetModules();

        global.runid = "test-run";
        global.config = "cfg";
        global.url_for_run = jest.fn((path) => `/runs/${global.runid}/${global.config}/${path}`);

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

        mapElement = document.getElementById("mapid");
        mapElement.getBoundingClientRect = () => ({
            width: 640,
            height: 480,
        });

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

        global.WCHttp = {
            postJson: jest.fn(),
            getJson: jest.fn(() => Promise.resolve({ type: "FeatureCollection", features: [] })),
            request: jest.fn(),
            isHttpError: jest.fn(() => false),
        };

        global.createImageBitmap = jest.fn(() => Promise.resolve({}));
        if (global.window) {
            global.window.createImageBitmap = global.createImageBitmap;
        }

        function Deck(props) {
            this.props = props || {};
            this.setProps = jest.fn((next) => {
                this.props = Object.assign({}, this.props, next);
            });
            deckInstance = this;
        }
        function MapView() {}
        function TileLayer(props) {
            this.props = props || {};
        }
        function BitmapLayer(props) {
            this.props = props || {};
        }
        function GeoJsonLayer(props) {
            this.props = props || {};
        }
        function WebMercatorViewport(opts) {
            this.opts = opts || {};
            this.getBounds = () => [
                (this.opts.longitude || 0) - 1,
                (this.opts.latitude || 0) - 1,
                (this.opts.longitude || 0) + 1,
                (this.opts.latitude || 0) + 1,
            ];
        }
        function FlyToInterpolator() {}

        global.deck = {
            Deck: Deck,
            MapView: MapView,
            TileLayer: TileLayer,
            BitmapLayer: BitmapLayer,
            GeoJsonLayer: GeoJsonLayer,
            WebMercatorViewport: WebMercatorViewport,
            FlyToInterpolator: FlyToInterpolator,
        };

        await import("../map_gl.js");
    });

    afterEach(() => {
        delete global.deck;
        delete global.WCEvents;
        delete global.WCHttp;
        delete global.MapController;
        delete global.WeppMap;
        delete global.coordRound;
        delete global.runid;
        delete global.config;
        delete global.url_for_run;
        delete global.createImageBitmap;
        if (global.window) {
            delete global.window.createImageBitmap;
        }
        emittedEvents = [];
    });

    test("getInstance returns singleton and emits map:ready", () => {
        const mapInstance = global.MapController.getInstance();
        const secondInstance = global.MapController.getInstance();

        expect(mapInstance).toBe(secondInstance);

        mapInstance.bootstrap({ map: { center: [46.8, -117.5], zoom: 10 } });

        expect(emittedEvents.some((evt) => evt.name === "map:ready")).toBe(true);
        expect(global.WeppMap).toBe(global.MapController);
        expect(mapInstance._deck).toBe(deckInstance);
        expect(Array.isArray(deckInstance.props.layers)).toBe(true);
        expect(deckInstance.props.layers.length).toBeGreaterThan(0);
        expect(document.querySelector('[data-map-layer-control="true"]')).not.toBeNull();
        expect(document.querySelectorAll('input[name="wc-map-basemap"]').length).toBeGreaterThan(0);
    });

    test("setView updates map status and emits center change", () => {
        const mapInstance = global.MapController.getInstance();

        mapInstance.setView([46.8, -117.5], 10);

        const status = document.getElementById("mapstatus");
        expect(status.textContent).toContain("Center:");
        expect(status.textContent).toContain("46.8");
        expect(status.textContent).toContain("-117.5");
        expect(emittedEvents.some((evt) => evt.name === "map:center:changed")).toBe(true);
    });

    test("overlay control registers USGS/SNOTEL/NHD with zoom gating labels", () => {
        global.MapController.getInstance();

        const overlayInputs = Array.from(document.querySelectorAll('input[name="wc-map-overlay"]'));
        expect(overlayInputs.length).toBeGreaterThanOrEqual(4);

        const labels = overlayInputs.map((input) => {
            const text = input.parentElement.querySelector(".wc-map-layer-control__text");
            return text ? text.textContent : "";
        });

        expect(labels.some((label) => label.includes("USGS Gage Locations"))).toBe(true);
        expect(labels.some((label) => label.includes("SNOTEL Locations"))).toBe(true);
        expect(labels.some((label) => label.includes("NHD"))).toBe(true);
        expect(labels.some((label) => label.includes("Burn Severity Map"))).toBe(true);

        const usgsLabel = labels.find((label) => label.includes("USGS Gage Locations"));
        expect(usgsLabel).toContain("zoom >= 9");

        const usgsIndex = labels.findIndex((label) => label.includes("USGS Gage Locations"));
        const snotelIndex = labels.findIndex((label) => label.includes("SNOTEL Locations"));
        const nhdIndex = labels.findIndex((label) => label.includes("NHD"));
        expect(usgsIndex).toBeLessThan(snotelIndex);
        expect(snotelIndex).toBeLessThan(nhdIndex);
    });

    test("loadSbsMap emits map:layer:refreshed and shows legend", async () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.addLayer(mapInstance.sbs_layer, { skipRefresh: true });

        global.WCHttp.getJson.mockResolvedValueOnce({
            Success: true,
            Content: {
                bounds: [[40.0, -120.0], [41.0, -119.0]],
                imgurl: "resources/baer.png",
            },
        });
        global.WCHttp.request.mockImplementation((url) => {
            if (String(url).includes("legends/sbs")) {
                return Promise.resolve({ body: "<div>Legend</div>" });
            }
            return Promise.resolve({ body: new Blob([""], { type: "image/png" }) });
        });

        emittedEvents = [];
        await mapInstance.loadSbsMap();

        const refreshed = emittedEvents.find(
            (evt) => evt.name === "map:layer:refreshed" && evt.payload.name === "Burn Severity Map"
        );
        expect(refreshed).toBeTruthy();
        const legend = document.getElementById("sbs_legend");
        expect(legend.hidden).toBe(false);
        expect(legend.innerHTML).toContain("Legend");
    });

    test("SBS opacity slider updates layer opacity and emits event", async () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.addLayer(mapInstance.sbs_layer, { skipRefresh: true });

        global.WCHttp.getJson.mockResolvedValueOnce({
            Success: true,
            Content: {
                bounds: [[40.0, -120.0], [41.0, -119.0]],
                imgurl: "resources/baer.png",
            },
        });
        global.WCHttp.request.mockImplementation((url) => {
            if (String(url).includes("legends/sbs")) {
                return Promise.resolve({ body: "<div>Legend</div>" });
            }
            return Promise.resolve({ body: new Blob([""], { type: "image/png" }) });
        });

        emittedEvents = [];
        await mapInstance.loadSbsMap();

        const slider = document.getElementById("baer-opacity-slider");
        expect(slider).not.toBeNull();

        slider.value = "0.4";
        slider.dispatchEvent(new Event("input"));

        expect(mapInstance.sbs_layer.props.opacity).toBeCloseTo(0.4, 1);
        const opacityEvent = emittedEvents.find((evt) => evt.name === "baer:map:opacity");
        expect(opacityEvent).toBeTruthy();
    });

    test("loadSbsMap emits map:layer:error and clears legend on failure", async () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.addLayer(mapInstance.sbs_layer, { skipRefresh: true });

        const legend = document.getElementById("sbs_legend");
        legend.innerHTML = "<div>Existing</div>";
        legend.hidden = false;

        global.WCHttp.getJson.mockResolvedValueOnce({
            Success: false,
            Error: "No SBS map has been specified",
        });

        emittedEvents = [];
        await mapInstance.loadSbsMap();

        const errorEvent = emittedEvents.find(
            (evt) => evt.name === "map:layer:error" && evt.payload.name === "Burn Severity Map"
        );
        expect(errorEvent).toBeTruthy();
        expect(legend.hidden).toBe(true);
        expect(legend.innerHTML).toBe("");
    });

    test("removeLayer clears SBS legend", async () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.addLayer(mapInstance.sbs_layer, { skipRefresh: true });

        global.WCHttp.getJson.mockResolvedValueOnce({
            Success: true,
            Content: {
                bounds: [[40.0, -120.0], [41.0, -119.0]],
                imgurl: "resources/baer.png",
            },
        });
        global.WCHttp.request.mockImplementation((url) => {
            if (String(url).includes("legends/sbs")) {
                return Promise.resolve({ body: "<div>Legend</div>" });
            }
            return Promise.resolve({ body: new Blob([""], { type: "image/png" }) });
        });

        await mapInstance.loadSbsMap();

        const legend = document.getElementById("sbs_legend");
        expect(legend.hidden).toBe(false);

        mapInstance.removeLayer(mapInstance.sbs_layer);

        expect(legend.hidden).toBe(true);
        expect(legend.innerHTML).toBe("");
    });

    test("loadUSGSGageLocations gated by zoom and emits refreshed", async () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.addLayer(mapInstance.usgs_gage);

        mapInstance.setView([44.0, -116.0], 8);
        global.WCHttp.getJson.mockClear();
        await mapInstance.loadUSGSGageLocations();
        expect(global.WCHttp.getJson).not.toHaveBeenCalled();

        mapInstance.setView([44.0, -116.0], 10);
        global.WCHttp.getJson.mockClear();
        emittedEvents = [];
        await mapInstance.loadUSGSGageLocations();

        expect(global.WCHttp.getJson).toHaveBeenCalled();
        const refreshed = emittedEvents.find(
            (evt) => evt.name === "map:layer:refreshed" && evt.payload.name === "USGS Gage Locations"
        );
        expect(refreshed).toBeTruthy();
    });

    test("goToEnteredLocation parses lon/lat and optional zoom", () => {
        const mapInstance = global.MapController.getInstance();
        const originalFlyTo = mapInstance.flyTo.bind(mapInstance);
        const flyToSpy = jest.spyOn(mapInstance, "flyTo").mockImplementation((center, zoom) => {
            return originalFlyTo(center, zoom);
        });

        const input = document.getElementById("input_centerloc");
        input.value = "-120.1595, 39.0451, 10";

        mapInstance.goToEnteredLocation();

        expect(flyToSpy).toHaveBeenCalledWith([39.0451, -120.1595], 10);
        const center = mapInstance.getCenter();
        expect(center.lat).toBeCloseTo(39.0451);
        expect(center.lng).toBeCloseTo(-120.1595);
        expect(mapInstance.getZoom()).toBe(10);
        const status = document.getElementById("mapstatus");
        expect(status.textContent).toContain("Zoom: 10");

        const lastProps = deckInstance.setProps.mock.calls[deckInstance.setProps.mock.calls.length - 1][0];
        expect(lastProps.viewState.transitionDuration).toBe(4000);
        expect(lastProps.viewState.transitionInterpolator).toBeInstanceOf(global.deck.FlyToInterpolator);
    });

    test("enter key emits map:center:requested and keeps zoom when omitted", () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.setView([44.5, -115.9], 7);

        const input = document.getElementById("input_centerloc");
        input.value = "-121.0, 40.5";
        input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

        const requested = emittedEvents.find((evt) => evt.name === "map:center:requested");
        expect(requested).toEqual(expect.objectContaining({
            name: "map:center:requested",
            payload: expect.objectContaining({
                source: "input",
                query: input.value,
            }),
        }));
        const center = mapInstance.getCenter();
        expect(center.lat).toBeCloseTo(40.5);
        expect(center.lng).toBeCloseTo(-121.0);
        expect(mapInstance.getZoom()).toBe(7);
    });

    test("invalid location input warns and does not move", () => {
        const mapInstance = global.MapController.getInstance();
        mapInstance.setView([44.0, -116.0], 6);

        const warnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
        const input = document.getElementById("input_centerloc");
        input.value = "200, 95";

        mapInstance.goToEnteredLocation();

        const center = mapInstance.getCenter();
        expect(center.lat).toBeCloseTo(44.0);
        expect(center.lng).toBeCloseTo(-116.0);
        expect(mapInstance.getZoom()).toBe(6);
        expect(warnSpy).toHaveBeenCalled();
        warnSpy.mockRestore();
    });

    test("invalidateSize resizes deck", () => {
        const mapInstance = global.MapController.getInstance();

        mapInstance.invalidateSize();

        expect(deckInstance.setProps).toHaveBeenCalledWith(expect.objectContaining({
            width: 640,
            height: 480,
        }));
    });
});

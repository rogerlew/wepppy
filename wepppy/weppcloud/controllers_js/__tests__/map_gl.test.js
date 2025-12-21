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
            getJson: jest.fn(),
            request: jest.fn(),
            isHttpError: jest.fn(() => false),
        };

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
        function WebMercatorViewport(opts) {
            this.opts = opts || {};
            this.getBounds = () => [
                (this.opts.longitude || 0) - 1,
                (this.opts.latitude || 0) - 1,
                (this.opts.longitude || 0) + 1,
                (this.opts.latitude || 0) + 1,
            ];
        }

        global.deck = {
            Deck: Deck,
            MapView: MapView,
            TileLayer: TileLayer,
            BitmapLayer: BitmapLayer,
            WebMercatorViewport: WebMercatorViewport,
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

    test("invalidateSize resizes deck", () => {
        const mapInstance = global.MapController.getInstance();

        mapInstance.invalidateSize();

        expect(deckInstance.setProps).toHaveBeenCalledWith(expect.objectContaining({
            width: 640,
            height: 480,
        }));
    });
});

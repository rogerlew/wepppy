/**
 * @jest-environment jsdom
 */

describe("Map GL controller", () => {
    let emittedEvents;

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

        global.deck = { Deck: function Deck() {} };

        await import("../map_gl.js");
    });

    afterEach(() => {
        delete global.deck;
        delete global.WCEvents;
        delete global.WCHttp;
        delete global.MapController;
        delete global.WeppMap;
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
    });
});

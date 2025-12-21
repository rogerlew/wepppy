/**
 * @jest-environment jsdom
 */

describe("ChannelDelineation GL controller", () => {
    let emittedEvents;
    let mapStub;

    beforeEach(async () => {
        jest.resetModules();

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
            getJson: jest.fn(() => Promise.resolve({ type: "FeatureCollection", features: [] })),
        };

        global.url_for_run = jest.fn((path) => `/runs/test/cfg/${path}`);

        mapStub = {
            addLayer: jest.fn(),
            removeLayer: jest.fn(),
            registerOverlay: jest.fn(),
            unregisterOverlay: jest.fn(),
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
        };
        global.MapController = {
            getInstance: jest.fn(() => mapStub),
        };

        function GeoJsonLayer(props) {
            this.props = props || {};
            this.id = props ? props.id : undefined;
        }
        global.deck = {
            GeoJsonLayer: GeoJsonLayer,
        };

        await import("../channel_gl.js");
    });

    afterEach(() => {
        delete window.ChannelDelineation;
        delete global.WCEvents;
        delete global.WCHttp;
        delete global.url_for_run;
        delete global.MapController;
        delete global.deck;
        emittedEvents = [];
    });

    test("show registers overlay and emits channel:layers:loaded", async () => {
        const channel = window.ChannelDelineation.getInstance();

        global.WCHttp.getJson.mockResolvedValueOnce({
            type: "FeatureCollection",
            features: [],
        });

        await channel.show();

        expect(global.WCHttp.getJson).toHaveBeenCalledWith(
            "/runs/test/cfg/resources/netful.json",
            expect.objectContaining({ params: expect.any(Object) }),
        );
        expect(mapStub.registerOverlay).toHaveBeenCalledWith(expect.any(Object), "Channels");
        expect(mapStub.addLayer).toHaveBeenCalledWith(expect.any(Object));
        expect(emittedEvents.some((evt) => evt.name === "channel:layers:loaded")).toBe(true);
        expect(channel.glLayer).toBeTruthy();
    });

    test("getLineColor uses palette order for netful channels", async () => {
        const channel = window.ChannelDelineation.getInstance();

        global.WCHttp.getJson.mockResolvedValueOnce({
            type: "FeatureCollection",
            features: [{ type: "Feature", properties: { Order: 2 } }],
        });

        await channel.show();

        const color = channel.glLayer.props.getLineColor({ properties: { Order: 2 } });
        expect(color).toEqual([71, 158, 255, 230]);
    });

    test("rebuild hook returns a fresh layer with the same palette", async () => {
        const channel = window.ChannelDelineation.getInstance();

        global.WCHttp.getJson.mockResolvedValueOnce({
            type: "FeatureCollection",
            features: [{ type: "Feature", properties: { Order: 1 } }],
        });

        await channel.show();

        const firstLayer = channel.glLayer;
        expect(typeof firstLayer.__wcRebuild).toBe("function");

        const nextLayer = firstLayer.__wcRebuild();
        expect(nextLayer).not.toBe(firstLayer);
        expect(nextLayer.id).toBe("wc-channels-netful");
        const color = nextLayer.props.getLineColor({ properties: { Order: 1 } });
        expect(color).toEqual([101, 200, 254, 230]);
    });
});

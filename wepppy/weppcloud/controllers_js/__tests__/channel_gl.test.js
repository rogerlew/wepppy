/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("ChannelDelineation GL controller", () => {
    let emittedEvents;
    let requestMock;
    let getJsonMock;
    let baseInstance;
    let mapStub;
    let outletRemoveMock;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="build_channels_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="braille"></div>

                <input type="hidden" id="map_center" name="map_center" value="-117.52,46.88">
                <input type="hidden" id="map_zoom" name="map_zoom" value="13">
                <input type="hidden" id="map_bounds" name="map_bounds" value="-118.0,46.5,-117.0,47.0">
                <input type="hidden" id="map_distance" name="map_distance" value="10000">

                <div id="map_bounds_text_group" style="display: none;">
                    <input id="map_bounds_text" name="map_bounds_text" type="text" value="-118.0,46.5,-117.0,47.0">
                </div>

                <div id="map_object_group" style="display: none;">
                    <textarea id="map_object" name="map_object" rows="8"></textarea>
                </div>

                <div id="wbt_blc_dist_container" style="display: none;">
                    <input id="wbt_blc_dist" name="wbt_blc_dist" type="text" value="400">
                </div>

                <input type="radio" id="set_extent_mode_map" name="set_extent_mode" value="0" data-channel-role="extent-mode" checked>
                <input type="radio" id="set_extent_mode_manual" name="set_extent_mode" value="1" data-channel-role="extent-mode">
                <input type="radio" id="set_extent_mode_map_object" name="set_extent_mode" value="2" data-channel-role="extent-mode">

                <select id="input_wbt_fill_or_breach" name="wbt_fill_or_breach" data-channel-role="wbt-fill">
                    <option value="fill">Fill</option>
                    <option value="breach" selected>Breach</option>
                    <option value="breach_least_cost">Breach (Least Cost)</option>
                </select>

                <input id="input_mcl" name="mcl" value="60">
                <input id="input_csa" name="csa" value="5">

                <button type="button" id="btn_build_channels_en" data-channel-action="build">Build Channels</button>
            </form>
            <small id="hint_build_channels_en"></small>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../utils.js");

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

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            update_command_button_state: jest.fn(),
            should_disable_command_button: jest.fn(() => false),
            connect_status_stream: jest.fn(),
            disconnect_status_stream: jest.fn(),
        }));

        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        requestMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-99" } }));
        getJsonMock = jest.fn(() => Promise.resolve({ type: "FeatureCollection", features: [] }));

        global.WCHttp = {
            request: requestMock,
            getJson: getJsonMock,
            isHttpError: jest.fn().mockReturnValue(false),
        };

        global.url_for_run = jest.fn((path) => `/runs/test/cfg/${path}`);

        mapStub = {
            _zoom: 13,
            addLayer: jest.fn(),
            removeLayer: jest.fn(),
            registerOverlay: jest.fn(),
            unregisterOverlay: jest.fn(),
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            on: jest.fn(),
            events: { on: jest.fn() },
            getCenter: jest.fn(() => ({ lng: -117.52, lat: 46.88 })),
            getZoom: jest.fn(function () {
                return this._zoom;
            }),
            getBounds: jest.fn(() => ({
                getSouthWest: () => ({ lat: 46.5, lng: -118.0 }),
                getNorthEast: () => ({ lat: 47.0, lng: -117.0 }),
            })),
            distance: jest.fn(() => 1500),
            flyTo: jest.fn(),
        };
        global.MapController = {
            getInstance: jest.fn(() => mapStub),
        };

        outletRemoveMock = jest.fn();
        global.Outlet = {
            getInstance: jest.fn(() => ({ remove: outletRemoveMock })),
        };

        if (!global.parseBboxText) {
            global.parseBboxText = (text) => {
                const toks = text
                    .replace(/[^\d\s,.\-+eE]/g, "")
                    .split(/[\s,]+/)
                    .filter(Boolean)
                    .map(Number);
                if (toks.length !== 4 || toks.some(Number.isNaN)) {
                    throw new Error("Extent must have exactly 4 numeric values: minLon, minLat, maxLon, maxLat.");
                }
                const minLon = Math.min(toks[0], toks[2]);
                const minLat = Math.min(toks[1], toks[3]);
                const maxLon = Math.max(toks[0], toks[2]);
                const maxLat = Math.max(toks[1], toks[3]);
                if (minLon >= maxLon || minLat >= maxLat) {
                    throw new Error("Invalid extent: ensure minLon < maxLon and minLat < maxLat.");
                }
                return [minLon, minLat, maxLon, maxLat];
            };
        }

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
        delete global.controlBase;
        delete global.Outlet;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.parseBboxText) {
            delete global.parseBboxText;
        }
        emittedEvents = [];
        document.body.innerHTML = "";
    });

    test("show registers overlay and emits channel:layers:loaded", async () => {
        const channel = window.ChannelDelineation.getInstance();

        getJsonMock.mockResolvedValueOnce({
            type: "FeatureCollection",
            features: [],
        });

        await channel.show();

        expect(getJsonMock).toHaveBeenCalledWith(
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

        getJsonMock.mockResolvedValueOnce({
            type: "FeatureCollection",
            features: [{ type: "Feature", properties: { Order: 2 } }],
        });

        await channel.show();

        const color = channel.glLayer.props.getLineColor({ properties: { Order: 2 } });
        expect(color).toEqual([71, 158, 255, 230]);
    });

    test("rebuild hook returns a fresh layer with the same palette", async () => {
        const channel = window.ChannelDelineation.getInstance();

        getJsonMock.mockResolvedValueOnce({
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

    test("build posts payload and records job id", async () => {
        const channel = window.ChannelDelineation.getInstance();

        const result = await channel.build();

        expect(result).toMatchObject({ Success: true, job_id: "job-99" });
        expect(requestMock).toHaveBeenCalledWith(
            "/runs/test/cfg/rq/api/fetch_dem_and_build_channels",
            expect.objectContaining({
                method: "POST",
                json: expect.any(Object),
                form: expect.any(HTMLFormElement),
            }),
        );
        const jsonPayload = requestMock.mock.calls[0][1].json;
        expect(jsonPayload.map_center).toEqual([-117.52, 46.88]);
        expect(jsonPayload.map_bounds).toEqual([-118.0, 46.5, -117.0, 47.0]);
        expect(jsonPayload.mcl).toBe(60);
        expect(jsonPayload.csa).toBe(5);
        expect(jsonPayload.set_extent_mode).toBe(0);
        expect(jsonPayload.map_object).toBeNull();

        expect(baseInstance.connect_status_stream).toHaveBeenCalled();
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(channel, "job-99");
        const startedEvents = emittedEvents.filter((evt) => evt.name === "channel:build:started");
        expect(startedEvents).toHaveLength(1);
        expect(startedEvents[0].payload.payload.map_center).toEqual([-117.52, 46.88]);
    });

    test("triggerEvent handles completion once and emits report + layer", async () => {
        const channel = window.ChannelDelineation.getInstance();

        channel.show = jest.fn(() => Promise.resolve());
        channel.report = jest.fn(() => Promise.resolve());

        channel.triggerEvent("BUILD_CHANNELS_TASK_COMPLETED", { payload: "ok" });
        channel.triggerEvent("BUILD_CHANNELS_TASK_COMPLETED", { payload: "ok" });

        expect(channel.show).toHaveBeenCalledTimes(1);
        expect(channel.report).toHaveBeenCalledTimes(1);
        const completionEvents = emittedEvents.filter((evt) => evt.name === "channel:build:completed");
        expect(completionEvents).toHaveLength(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:completed",
            expect.objectContaining({ task: "channel:build" }),
        );
    });

    test("triggerEvent emits job:error on failure", async () => {
        const channel = window.ChannelDelineation.getInstance();

        channel.triggerEvent("BUILD_CHANNELS_TASK_FAILED", { detail: "failed" });

        const errorEvents = emittedEvents.filter((evt) => evt.name === "channel:build:error");
        expect(errorEvents.length).toBeGreaterThan(0);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "channel:build" }),
        );
    });

    test("onMapChange updates inputs and build button state", async () => {
        const channel = window.ChannelDelineation.getInstance();
        const buildButton = document.getElementById("btn_build_channels_en");
        const hint = document.getElementById("hint_build_channels_en");
        const mapCenterInput = document.getElementById("map_center");
        const mapZoomInput = document.getElementById("map_zoom");

        mapStub._zoom = 10;
        channel.onMapChange();
        expect(buildButton.disabled).toBe(true);
        expect(hint.textContent).toContain("zoom must be 12");

        mapStub._zoom = 13;
        channel.onMapChange();
        expect(buildButton.disabled).toBe(false);
        expect(mapCenterInput.value).toBe("-117.52,46.88");
        expect(mapZoomInput.value).toBe("13");
    });
});

/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Channel Delineation controller", () => {
    let requestMock;
    let getJsonMock;
    let baseInstance;
    let statusStreamMock;
    let mapStub;
    let channel;
    let outletRemoveMock;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="build_channels_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>

                <input type="hidden" id="map_center" name="map_center" value="-117.52,46.88">
                <input type="hidden" id="map_zoom" name="map_zoom" value="13">
                <input type="hidden" id="map_bounds" name="map_bounds" value="-118.0,46.5,-117.0,47.0">
                <input type="hidden" id="map_distance" name="map_distance" value="10000">

                <div id="map_bounds_text_group" style="display: none;">
                    <input id="map_bounds_text" name="map_bounds_text" type="text" value="-118.0,46.5,-117.0,47.0">
                </div>

                <div id="wbt_blc_dist_container" style="display: none;">
                    <input id="wbt_blc_dist" name="wbt_blc_dist" type="text" value="400">
                </div>

                <input type="radio" id="set_extent_mode_map" name="set_extent_mode" value="0" data-channel-role="extent-mode" checked>
                <input type="radio" id="set_extent_mode_manual" name="set_extent_mode" value="1" data-channel-role="extent-mode">

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
        await import("../events.js");
        await import("../utils.js");

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            update_command_button_state: jest.fn(),
            should_disable_command_button: jest.fn(() => false)
        }));

        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        requestMock = jest.fn(() => Promise.resolve({ body: { Success: true, job_id: "job-99" } }));
        getJsonMock = jest.fn(() => Promise.resolve({ type: "FeatureCollection", features: [] }));

        global.WCHttp = {
            request: requestMock,
            getJson: getJsonMock,
            isHttpError: jest.fn().mockReturnValue(false),
        };

        global.url_for_run = jest.fn((path) => path);

        mapStub = {
            _zoom: 13,
            ctrls: {
                addOverlay: jest.fn(),
                removeLayer: jest.fn(),
            },
            removeLayer: jest.fn(),
            getCenter: jest.fn(() => ({ lng: -117.52, lat: 46.88 })),
            getZoom: jest.fn(function () {
                return this._zoom;
            }),
            getBounds: jest.fn(() => ({
                getSouthWest: () => ({ lat: 46.5, lng: -118.0 }),
                getNorthEast: () => ({ lat: 47.0, lng: -117.0 }),
            })),
            distance: jest.fn(() => 1500),
            chnQuery: jest.fn(),
        };

        global.MapController = {
            getInstance: jest.fn(() => mapStub),
        };

        outletRemoveMock = jest.fn();
        global.Outlet = {
            getInstance: jest.fn(() => ({ remove: outletRemoveMock })),
        };

        global.fromHex = jest.fn((color, alpha) => ({ color, alpha }));
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
        global.L = {
            glify: {
                layer: jest.fn(() => ({
                    addTo: jest.fn(() => mapStub),
                })),
            },
            layerGroup: jest.fn(() => ({
                addLayer: jest.fn(),
            })),
            marker: jest.fn(() => ({})),
            divIcon: jest.fn(() => ({})),
        };

        await import("../channel_delineation.js");
        channel = window.ChannelDelineation.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.ChannelDelineation;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.MapController;
        delete global.Outlet;
        delete global.L;
        delete global.fromHex;
        delete global.url_for_run;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        if (global.parseBboxText) {
            delete global.parseBboxText;
        }
        document.body.innerHTML = "";
    });

    test("build posts JSON payload and records job id", async () => {
        const events = [];
        channel.events.on("channel:build:started", (payload) => events.push({ type: "started", payload }));

        const result = await channel.build();

        expect(result).toMatchObject({ Success: true, job_id: "job-99" });
        expect(requestMock).toHaveBeenCalledWith(
            "rq/api/fetch_dem_and_build_channels",
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

        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(channel, "job-99");
        expect(events).toHaveLength(1);
        expect(events[0].payload.payload.map_center).toEqual([-117.52, 46.88]);
    });

    test("build rejects when manual extent is invalid", async () => {
        document.getElementById("set_extent_mode_manual").checked = true;
        document.getElementById("set_extent_mode_map").checked = false;
        document.getElementById("map_bounds_text").value = "invalid";

        const errors = [];
        channel.events.on("channel:build:error", (payload) => errors.push(payload));

        await expect(channel.build()).rejects.toThrow("Extent");

        expect(requestMock).not.toHaveBeenCalled();
        expect(document.getElementById("status").innerHTML).toContain("Extent must have exactly 4 numeric values");
        expect(errors).toHaveLength(1);
        expect(errors[0].reason).toBe("validation");
    });

    test("onMapChange disables build button when zoom is too low", () => {
        mapStub._zoom = 10;
        const events = [];
        channel.events.on("channel:map:updated", (payload) => events.push(payload));

        channel.onMapChange();

        const button = document.getElementById("btn_build_channels_en");
        expect(button.disabled).toBe(true);
        expect(button.dataset.mapDisabled).toBe("true");
        expect(document.getElementById("hint_build_channels_en").textContent).toContain("zoom must be");
        expect(events).toHaveLength(1);
        expect(events[0].zoom).toBe(10);
    });

    test("show loads WebGL layer when delineation pass is 1", async () => {
        requestMock.mockResolvedValueOnce({ body: "1" });
        getJsonMock.mockResolvedValueOnce({ type: "FeatureCollection", features: [] });

        await channel.show();

        expect(requestMock).toHaveBeenCalledWith(
            "query/delineation_pass/",
            expect.objectContaining({ params: expect.any(Object) }),
        );
        expect(getJsonMock).toHaveBeenCalledWith(
            "resources/netful.json",
            expect.objectContaining({ params: expect.any(Object) }),
        );
        expect(global.L.glify.layer).toHaveBeenCalled();
        expect(mapStub.ctrls.addOverlay).toHaveBeenCalled();
    });

    test("bootstrap assigns job id and triggers initial report", () => {
        const setJobSpy = jest.spyOn(channel, "set_rq_job_id");
        const onMapChangeSpy = jest.spyOn(channel, "onMapChange").mockImplementation(() => {});
        const reportSpy = jest.spyOn(channel, "report").mockImplementation(() => {});
        const showSpy = jest.spyOn(channel, "show").mockImplementation(() => {});

        channel.bootstrap({
            jobIds: { fetch_dem_and_build_channels_rq: "job-123" },
            data: { watershed: { hasChannels: true, hasSubcatchments: false } }
        });

        expect(setJobSpy).toHaveBeenCalledWith(channel, "job-123");
        expect(onMapChangeSpy).toHaveBeenCalled();
        expect(reportSpy).toHaveBeenCalled();
        expect(showSpy).toHaveBeenCalled();
    });
});

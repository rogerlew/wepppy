/**
 * @jest-environment jsdom
 */

describe("LanduseModify controller", () => {
    let httpPostJsonMock;
    let httpGetJsonMock;
    let baseInstance;
    let mapInstance;
    let landuseModify;
    let formContainer;
    let checkboxEl;
    let textareaEl;
    let selectEl;
    let statusEl;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div id="modify_landuse_form">
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <input id="checkbox_modify_landuse"
                       name="checkbox_modify_landuse"
                       type="checkbox"
                       data-landuse-modify-action="toggle-selection">
                <textarea id="textarea_modify_landuse"
                          name="textarea_modify_landuse"
                          data-landuse-modify-field="topaz-ids">101, 202</textarea>
                <select id="selection_modify_landuse"
                        name="selection_modify_landuse"
                        data-landuse-modify-field="landuse-code">
                    <option value=""></option>
                    <option value="202" selected>202</option>
                </select>
                <button id="btn_modify_landuse"
                        type="button"
                        data-landuse-modify-action="submit">
                    Modify Landuse
                </button>
            </div>
        `;

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpPostJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));
        httpGetJsonMock = jest.fn(() => Promise.resolve({ features: [] }));
        global.WCHttp = {
            request: jest.fn(),
            postJson: httpPostJsonMock,
            getJson: httpGetJsonMock,
            isHttpError: jest.fn().mockReturnValue(false)
        };

        baseInstance = {
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
            hideStacktrace: jest.fn()
        };
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        const mapListeners = {};
        mapInstance = {
            boxZoom: { disable: jest.fn(), enable: jest.fn() },
            on: jest.fn((event, handler) => { mapListeners[event] = handler; }),
            off: jest.fn((event) => { delete mapListeners[event]; }),
            removeLayer: jest.fn()
        };
        window.MapController = {
            getInstance: jest.fn(() => mapInstance)
        };

        window.L = {
            rectangle: jest.fn(() => {
                const rect = {
                    setBounds: jest.fn(),
                    addTo: jest.fn(() => rect)
                };
                return rect;
            }),
            latLngBounds: jest.fn((a, b) => ({
                getSouthWest: () => ({ lat: Math.min(a.lat, b.lat), lng: Math.min(a.lng, b.lng) }),
                getNorthEast: () => ({ lat: Math.max(a.lat, b.lat), lng: Math.max(a.lng, b.lng) })
            })),
            geoJSON: jest.fn((features, options) => {
                (features || []).forEach((feature) => {
                    const dummyLayer = {
                        setStyle: jest.fn(),
                        on: jest.fn()
                    };
                    if (options && typeof options.onEachFeature === "function") {
                        options.onEachFeature(feature, dummyLayer);
                    }
                });
                return {
                    addTo(layer) { return layer; },
                    setStyle: jest.fn(),
                    on: jest.fn()
                };
            })
        };

        window.SubcatchmentDelineation = {
            getInstance: jest.fn(() => ({
                getCmapMode: jest.fn(() => "dom_lc"),
                setColorMap: jest.fn()
            }))
        };
        window.Landuse = {
            getInstance: jest.fn(() => ({
                report: jest.fn()
            }))
        };

        await import("../landuse_modify.js");
        landuseModify = window.LanduseModify.getInstance();

        formContainer = document.getElementById("modify_landuse_form");
        checkboxEl = document.querySelector('[data-landuse-modify-action="toggle-selection"]');
        textareaEl = document.querySelector('[data-landuse-modify-field="topaz-ids"]');
        selectEl = document.querySelector('[data-landuse-modify-field="landuse-code"]');
        statusEl = document.querySelector("#status");
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.LanduseModify;
        delete global.WCHttp;
        delete global.controlBase;
        delete window.MapController;
        delete window.SubcatchmentDelineation;
        delete window.Landuse;
        delete window.L;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        document.body.innerHTML = "";
    });

    function clickSubmit() {
        const button = document.querySelector('[data-landuse-modify-action="submit"]');
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        return Promise.resolve().then(() => Promise.resolve());
    }

    test("submit posts JSON payload, clears selection, and emits completion event", async () => {
        const completedEvents = [];
        landuseModify.events.on("landuse:modify:completed", (payload) => completedEvents.push(payload));

        await clickSubmit();

        expect(global.WCHttp.postJson).toHaveBeenCalledWith(
            "tasks/modify_landuse/",
            { topaz_ids: ["101", "202"], landuse: "202" },
            expect.objectContaining({ form: formContainer })
        );
        expect(statusEl.textContent).toContain("Success");
        expect(textareaEl.value).toBe("");
        expect(checkboxEl.checked).toBe(false);
        expect(landuseModify.selected.size).toBe(0);
        expect(completedEvents).toHaveLength(1);
        expect(window.Landuse.getInstance).toHaveBeenCalled();
        const subcatchmentCtrl = window.SubcatchmentDelineation.getInstance.mock.results[0].value;
        expect(subcatchmentCtrl.setColorMap).toHaveBeenCalledWith("dom_lc");
    });

    test("unsuccessful response pushes stacktrace and emits error", async () => {
        const errorPayload = { Success: false, Error: "failed" };
        global.WCHttp.postJson.mockResolvedValueOnce({ body: errorPayload });

        const errors = [];
        landuseModify.events.on("landuse:modify:error", (payload) => errors.push(payload));

        await clickSubmit();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(landuseModify, errorPayload);
        expect(errors).toHaveLength(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "landuse:modify" })
        );
    });

    test("request rejection routes to pushResponseStacktrace and emits error", async () => {
        const networkError = new Error("network");
        global.WCHttp.postJson.mockRejectedValueOnce(networkError);

        const errors = [];
        landuseModify.events.on("landuse:modify:error", (payload) => errors.push(payload));

        await clickSubmit();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalled();
        expect(errors).toHaveLength(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "landuse:modify" })
        );
    });

    test("enabling selection mode loads subcatchments", async () => {
        checkboxEl.checked = true;
        checkboxEl.dispatchEvent(new Event("change", { bubbles: true }));
        await Promise.resolve();

        expect(global.WCHttp.getJson).toHaveBeenCalledWith(
            "resources/subcatchments.json",
            expect.objectContaining({ form: formContainer })
        );
        expect(mapInstance.boxZoom.disable).toHaveBeenCalled();
    });

    test("manual textarea edits update selection and emit events", () => {
        const events = [];
        landuseModify.events.on("landuse:selection:changed", (payload) => events.push(payload));

        textareaEl.value = "4, 7";
        textareaEl.dispatchEvent(new Event("input", { bubbles: true }));

        expect(Array.from(landuseModify.selected)).toEqual(["4", "7"]);
        expect(events).toHaveLength(1);
        expect(events[0]).toEqual({ topazIds: ["4", "7"], source: "manual" });
    });

    test("missing landuse value yields user-facing error", async () => {
        selectEl.value = "";
        const errors = [];
        landuseModify.events.on("landuse:modify:error", (payload) => errors.push(payload));

        await clickSubmit();

        expect(global.WCHttp.postJson).not.toHaveBeenCalled();
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            landuseModify,
            { Error: "Select a landuse value before modifying." }
        );
        expect(errors).toHaveLength(1);
    });
});

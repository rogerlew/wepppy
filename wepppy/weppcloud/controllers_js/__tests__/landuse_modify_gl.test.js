/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("LanduseModify GL controller", () => {
    let httpPostJsonMock;
    let httpGetJsonMock;
    let baseInstance;
    let mapStub;
    let landuseModify;
    let formContainer;
    let checkboxEl;
    let textareaEl;
    let selectEl;
    let statusEl;
    let mapElement;

    function flushPromises(times = 2) {
        let chain = Promise.resolve();
        for (let i = 0; i < times; i += 1) {
            chain = chain.then(() => new Promise((resolve) => setTimeout(resolve, 0)));
        }
        return chain;
    }

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
            <div id="mapid"></div>
        `;

        mapElement = document.getElementById("mapid");
        mapElement.getBoundingClientRect = () => ({
            left: 0,
            top: 0,
            width: 400,
            height: 300
        });

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        httpPostJsonMock = jest.fn((url) => {
            if (url === "tasks/sub_intersection/") {
                return Promise.resolve({ body: ["5", "6"] });
            }
            if (url === "tasks/modify_landuse/") {
                return Promise.resolve({ body: { Success: true } });
            }
            return Promise.resolve({ body: {} });
        });
        httpGetJsonMock = jest.fn(() => Promise.resolve({
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: { TopazID: 101 },
                    geometry: { type: "Polygon", coordinates: [] }
                }
            ]
        }));

        global.WCHttp = {
            request: jest.fn(),
            postJson: httpPostJsonMock,
            getJson: httpGetJsonMock,
            isHttpError: jest.fn().mockReturnValue(false)
        };

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        mapStub = {
            addLayer: jest.fn(),
            removeLayer: jest.fn(),
            boxZoom: { disable: jest.fn(), enable: jest.fn() },
            suppressDrilldown: jest.fn(),
            releaseDrilldown: jest.fn(),
            _deck: {
                unproject: jest.fn((coords) => coords)
            }
        };

        window.MapController = {
            getInstance: jest.fn(() => mapStub)
        };

        function GeoJsonLayer(props) {
            this.props = props || {};
            this.id = props ? props.id : undefined;
        }
        global.deck = { GeoJsonLayer };

        global.url_for_run = jest.fn((path) => path);

        await import("../landuse_modify_gl.js");
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
        delete global.deck;
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
        document.body.innerHTML = "";
    });

    test("enabling selection mode loads subcatchments and adds layer", async () => {
        checkboxEl.checked = true;
        checkboxEl.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        expect(global.WCHttp.getJson).toHaveBeenCalledWith(
            "resources/subcatchments.json",
            expect.objectContaining({ form: formContainer })
        );
        expect(mapStub.addLayer).toHaveBeenCalledWith(expect.any(Object), expect.any(Object));
        expect(mapStub.boxZoom.disable).toHaveBeenCalled();
        expect(mapStub.suppressDrilldown).toHaveBeenCalledWith("landuse-modify");
        expect(landuseModify.isSelectionModeActive()).toBe(true);
    });

    test("box selection posts intersection and toggles selection", async () => {
        landuseModify.clearSelection();
        checkboxEl.checked = true;
        checkboxEl.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        mapElement.dispatchEvent(new MouseEvent("pointerdown", {
            clientX: 10,
            clientY: 20,
            shiftKey: true,
            bubbles: true
        }));
        mapElement.dispatchEvent(new MouseEvent("pointermove", {
            clientX: 110,
            clientY: 120,
            shiftKey: true,
            bubbles: true
        }));
        window.dispatchEvent(new MouseEvent("pointerup", {
            clientX: 110,
            clientY: 120,
            shiftKey: true
        }));
        await flushPromises();

        expect(global.WCHttp.postJson).toHaveBeenCalledWith(
            "tasks/sub_intersection/",
            { extent: [10, 20, 110, 120] },
            expect.objectContaining({ form: formContainer })
        );
        expect(Array.from(landuseModify.selected)).toEqual(["5", "6"]);
    });

    test("submit clears selection and disables selection mode", async () => {
        checkboxEl.checked = true;
        checkboxEl.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        textareaEl.value = "4, 7";
        textareaEl.dispatchEvent(new Event("input", { bubbles: true }));

        selectEl.value = "202";
        const button = document.querySelector('[data-landuse-modify-action="submit"]');
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flushPromises();

        expect(global.WCHttp.postJson).toHaveBeenCalledWith(
            "tasks/modify_landuse/",
            { topaz_ids: ["4", "7"], landuse: "202" },
            expect.objectContaining({ form: formContainer })
        );
        expect(statusEl.textContent).toContain("Success");
        expect(checkboxEl.checked).toBe(false);
        expect(landuseModify.selected.size).toBe(0);
        expect(mapStub.removeLayer).toHaveBeenCalled();
    });
});

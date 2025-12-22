/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("RangelandCoverModify GL controller", () => {
    let httpPostJsonMock;
    let httpGetJsonMock;
    let baseInstance;
    let mapStub;
    let rangelandModify;
    let formContainer;
    let checkboxEl;
    let textareaEl;
    let statusEl;
    let coverInputs;
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
            <div id="modify_rangeland_cover_form">
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <input id="checkbox_modify_rangeland_cover"
                       name="checkbox_modify_rangeland_cover"
                       type="checkbox"
                       data-rcm-action="toggle-selection">
                <textarea id="textarea_modify_rangeland_cover"
                          name="textarea_modify_rangeland_cover"
                          data-rcm-field="topaz-ids">101, 202</textarea>
                <input id="input_bunchgrass_cover"
                       name="input_bunchgrass_cover"
                       data-rcm-field="bunchgrass"
                       value="10">
                <input id="input_forbs_cover"
                       name="input_forbs_cover"
                       data-rcm-field="forbs"
                       value="20">
                <input id="input_sodgrass_cover"
                       name="input_sodgrass_cover"
                       data-rcm-field="sodgrass"
                       value="30">
                <input id="input_shrub_cover"
                       name="input_shrub_cover"
                       data-rcm-field="shrub"
                       value="40">
                <input id="input_basal_cover"
                       name="input_basal_cover"
                       data-rcm-field="basal"
                       value="15">
                <input id="input_rock_cover"
                       name="input_rock_cover"
                       data-rcm-field="rock"
                       value="5">
                <input id="input_litter_cover"
                       name="input_litter_cover"
                       data-rcm-field="litter"
                       value="25">
                <input id="input_cryptogams_cover"
                       name="input_cryptogams_cover"
                       data-rcm-field="cryptogams"
                       value="10">
                <button id="btn_modify_rangeland_cover"
                        type="button"
                        data-rcm-action="submit">
                    Modify Rangeland Cover
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
        await import("../selection_utils.js");

        httpPostJsonMock = jest.fn((url) => {
            if (url === "query/rangeland_cover/current_cover_summary/") {
                return Promise.resolve({
                    body: {
                        bunchgrass: "11",
                        forbs: "22",
                        sodgrass: "33",
                        shrub: "44",
                        basal: "55",
                        rock: "66",
                        litter: "77",
                        cryptogams: "88"
                    }
                });
            }
            if (url === "tasks/sub_intersection/") {
                return Promise.resolve({ body: ["7", "9"] });
            }
            if (url === "tasks/modify_rangeland_cover/") {
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
            isHttpError: jest.fn(() => false)
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

        await import("../rangeland_cover_modify_gl.js");
        rangelandModify = window.RangelandCoverModify.getInstance();

        formContainer = document.getElementById("modify_rangeland_cover_form");
        checkboxEl = formContainer.querySelector('[data-rcm-action="toggle-selection"]');
        textareaEl = formContainer.querySelector('[data-rcm-field="topaz-ids"]');
        statusEl = formContainer.querySelector("#status");
        coverInputs = {
            bunchgrass: formContainer.querySelector('[data-rcm-field="bunchgrass"]'),
            forbs: formContainer.querySelector('[data-rcm-field="forbs"]'),
            sodgrass: formContainer.querySelector('[data-rcm-field="sodgrass"]'),
            shrub: formContainer.querySelector('[data-rcm-field="shrub"]'),
            basal: formContainer.querySelector('[data-rcm-field="basal"]'),
            rock: formContainer.querySelector('[data-rcm-field="rock"]'),
            litter: formContainer.querySelector('[data-rcm-field="litter"]'),
            cryptogams: formContainer.querySelector('[data-rcm-field="cryptogams"]')
        };

        await flushPromises();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.RangelandCoverModify;
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
        if (global.WCSelectionUtils) {
            delete global.WCSelectionUtils;
        }
        document.body.innerHTML = "";
    });

    test("initializes by loading cover summary values", () => {
        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "query/rangeland_cover/current_cover_summary/",
            { topaz_ids: ["101", "202"] },
            expect.objectContaining({ form: formContainer })
        );
        expect(coverInputs.bunchgrass.value).toBe("11");
        expect(coverInputs.cryptogams.value).toBe("88");
    });

    test("box selection posts intersection and toggles selection", async () => {
        rangelandModify.clearSelection();
        checkboxEl.checked = true;
        checkboxEl.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        mapElement.dispatchEvent(new MouseEvent("pointerdown", {
            clientX: 20,
            clientY: 30,
            shiftKey: true,
            bubbles: true
        }));
        mapElement.dispatchEvent(new MouseEvent("pointermove", {
            clientX: 140,
            clientY: 160,
            shiftKey: true,
            bubbles: true
        }));
        window.dispatchEvent(new MouseEvent("pointerup", {
            clientX: 140,
            clientY: 160,
            shiftKey: true
        }));
        await flushPromises();

        expect(global.WCHttp.postJson).toHaveBeenCalledWith(
            "tasks/sub_intersection/",
            { extent: [20, 30, 140, 160] },
            expect.objectContaining({ form: formContainer })
        );
        expect(mapStub.suppressDrilldown).toHaveBeenCalledWith("rangeland-cover-modify");
        expect(Array.from(rangelandModify.selected)).toEqual(["7", "9"]);
    });

    test("submit posts payload and clears selection", async () => {
        checkboxEl.checked = true;
        checkboxEl.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        textareaEl.value = "4, 7";
        textareaEl.dispatchEvent(new Event("input", { bubbles: true }));

        const button = formContainer.querySelector('[data-rcm-action="submit"]');
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flushPromises();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "tasks/modify_rangeland_cover/",
            expect.objectContaining({
                topaz_ids: ["4", "7"]
            }),
            expect.objectContaining({ form: formContainer })
        );
        expect(statusEl.textContent).toContain("Success");
        expect(checkboxEl.checked).toBe(false);
        expect(rangelandModify.selected.size).toBe(0);
        expect(mapStub.removeLayer).toHaveBeenCalled();
        expect(mapStub.releaseDrilldown).toHaveBeenCalledWith("rangeland-cover-modify");
    });
});

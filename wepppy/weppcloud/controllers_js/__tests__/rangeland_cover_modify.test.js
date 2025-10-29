/**
 * @jest-environment jsdom
 */

describe("RangelandCoverModify controller", () => {
    let httpPostJsonMock;
    let httpGetJsonMock;
    let baseInstance;
    let rangelandModify;
    let formContainer;
    let checkboxEl;
    let textareaEl;
    let statusEl;
    let coverInputs;

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    function setupDom() {
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
        `;
    }

    beforeEach(async () => {
        jest.resetModules();
        setupDom();

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

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
            if (url === "tasks/modify_rangeland_cover/") {
                return Promise.resolve({ body: { Success: true } });
            }
            return Promise.resolve({ body: {} });
        });
        httpGetJsonMock = jest.fn(() => Promise.resolve({ features: [] }));
        global.WCHttp = {
            request: jest.fn(),
            postJson: httpPostJsonMock,
            getJson: httpGetJsonMock,
            isHttpError: jest.fn(() => false)
        };

        baseInstance = {
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
            hideStacktrace: jest.fn()
        };
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        window.MapController = {
            getInstance: jest.fn(() => ({
                boxZoom: { disable: jest.fn(), enable: jest.fn() },
                on: jest.fn(),
                off: jest.fn(),
                removeLayer: jest.fn()
            }))
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
            geoJSON: jest.fn(() => ({
                addTo(layer) { return layer; },
                setStyle: jest.fn(),
                on: jest.fn()
            }))
        };

        window.SubcatchmentDelineation = {
            getInstance: jest.fn(() => ({
                getCmapMode: jest.fn(() => "rangeland_cover"),
                setColorMap: jest.fn(),
                cmapRangelandCover: jest.fn()
            }))
        };
        window.RangelandCover = {
            getInstance: jest.fn(() => ({
                report: jest.fn()
            }))
        };

        global.url_for_run = jest.fn((path) => path);

        await import("../rangeland_cover_modify.js");
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
        delete window.SubcatchmentDelineation;
        delete window.RangelandCover;
        delete window.L;
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

    function clickSubmit() {
        const button = formContainer.querySelector('[data-rcm-action="submit"]');
        button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        return flushPromises();
    }

    test("initializes by loading cover summary values", () => {
        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "query/rangeland_cover/current_cover_summary/",
            { topaz_ids: ["101", "202"] },
            expect.objectContaining({ form: formContainer })
        );
        expect(coverInputs.bunchgrass.value).toBe("11");
        expect(coverInputs.cryptogams.value).toBe("88");
    });

    test("submit posts payload, clears selection, and emits completion event", async () => {
        const completed = [];
        rangelandModify.events.on("rangeland:modify:run:completed", (payload) => completed.push(payload));

        await clickSubmit();
        await flushPromises();

        const modifyCalls = httpPostJsonMock.mock.calls.filter((call) => call[0] === "tasks/modify_rangeland_cover/");
        expect(modifyCalls).toHaveLength(1);
        expect(modifyCalls[0][1]).toEqual({
            topaz_ids: ["101", "202"],
            covers: {
                bunchgrass: 11,
                forbs: 22,
                sodgrass: 33,
                shrub: 44,
                basal: 55,
                rock: 66,
                litter: 77,
                cryptogams: 88
            }
        });
        expect(textareaEl.value).toBe("");
        expect(checkboxEl.checked).toBe(false);
        expect(rangelandModify.selected.size).toBe(0);
        expect(statusEl.textContent).toContain("Success");
        expect(completed).toHaveLength(1);
        expect(window.RangelandCover.getInstance).toHaveBeenCalled();
        const subcatchmentCtrl = window.SubcatchmentDelineation.getInstance.mock.results[0].value;
        expect(subcatchmentCtrl.setColorMap).toHaveBeenCalledWith("rangeland_cover");
        expect(subcatchmentCtrl.cmapRangelandCover).toHaveBeenCalled();
    });

    test("validation error blocks submission and pushes stacktrace", async () => {
        coverInputs.bunchgrass.value = "";
        const errors = [];
        rangelandModify.events.on("rangeland:modify:run:error", (payload) => errors.push(payload));

        await clickSubmit();
        await flushPromises();

        const modifyCalls = httpPostJsonMock.mock.calls.filter((call) => call[0] === "tasks/modify_rangeland_cover/");
        expect(modifyCalls).toHaveLength(0);
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalled();
        expect(errors).toHaveLength(1);
    });
});

/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("RangelandCover bootstrap requirements", () => {
    beforeEach(() => {
        jest.resetModules();
        document.body.innerHTML = `
            <form id="rangeland_cover_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
            </form>
            <p id="hint_build_rangeland_cover"></p>
        `;

        const { base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn()
        });
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.url_for_run = jest.fn((path) => path);
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete global.controlBase;
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
        if (global.WCHttp) {
            delete global.WCHttp;
        }
        document.body.innerHTML = "";
    });

    test("throws when helpers are missing", async () => {
        await import("../rangeland_cover.js");
        expect(() => window.RangelandCover.getInstance()).toThrow("Rangeland cover controller requires WCDom helpers.");
    });
});

describe("RangelandCover controller", () => {
    let httpRequestMock;
    let httpPostJsonMock;
    let baseInstance;
    let statusStreamMock;
    let rangeland;
    let eventLog;

    beforeEach(async () => {
        jest.resetModules();
        eventLog = [];

        document.body.innerHTML = `
            <form id="rangeland_cover_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div class="form-group">
                    <input type="radio" id="rangeland_cover_mode0" name="rangeland_cover_mode"
                           value="0" class="disable-readonly" data-rangeland-role="mode"
                           data-rangeland-mode="0" checked>
                    <input type="radio" id="rangeland_cover_mode2" name="rangeland_cover_mode"
                           value="2" class="disable-readonly" data-rangeland-role="mode"
                           data-rangeland-mode="2">
                    <input type="radio" id="rangeland_cover_mode1" name="rangeland_cover_mode"
                           value="1" class="disable-readonly" data-rangeland-role="mode"
                           data-rangeland-mode="1">
                </div>
                <div id="rangeland_cover_rap_year_div" data-rangeland-rap-section>
                    <input id="rap_year" name="rap_year" value="2020" data-rangeland-input="rap-year">
                </div>
                <input id="input_bunchgrass_cover" name="input_bunchgrass_cover" value="10">
                <input id="input_forbs_cover" name="input_forbs_cover" value="20">
                <input id="input_sodgrass_cover" name="input_sodgrass_cover" value="30">
                <input id="input_shrub_cover" name="input_shrub_cover" value="40">
                <input id="input_basal_cover" name="input_basal_cover" value="15">
                <input id="input_rock_cover" name="input_rock_cover" value="5">
                <input id="input_litter_cover" name="input_litter_cover" value="25">
                <input id="input_cryptogams_cover" name="input_cryptogams_cover" value="5">
                <button id="btn_build_rangeland_cover" type="button" data-rangeland-action="build">
                    Build
                </button>
            </form>
            <p id="hint_build_rangeland_cover"></p>
        `;

        await import("../dom.js");
        await import("../forms.js");

        global.WCEvents = {
            useEventMap: jest.fn((events, emitter) => emitter),
            createEmitter: () => {
                const listeners = {};
                return {
                    on(event, handler) {
                        (listeners[event] = listeners[event] || []).push(handler);
                        return () => {
                            listeners[event] = (listeners[event] || []).filter((fn) => fn !== handler);
                        };
                    },
                    once(event, handler) {
                        const unsubscribe = this.on(event, (payload) => {
                            unsubscribe();
                            handler(payload);
                        });
                        return unsubscribe;
                    },
                    off(event, handler) {
                        if (!listeners[event]) {
                            return;
                        }
                        if (!handler) {
                            listeners[event] = [];
                            return;
                        }
                        listeners[event] = listeners[event].filter((fn) => fn !== handler);
                    },
                    emit(event, payload) {
                        eventLog.push({ event, payload });
                        const bucket = listeners[event] || [];
                        bucket.slice().forEach((fn) => fn(payload));
                        return bucket.length > 0;
                    },
                    listenerCount(event) {
                        if (event) {
                            return (listeners[event] || []).length;
                        }
                        return Object.keys(listeners).reduce((total, key) => total + (listeners[key] || []).length, 0);
                    }
                };
            }
        };

        httpRequestMock = jest.fn(() => Promise.resolve({ body: "<div>report</div>" }));
        httpPostJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));

        global.WCHttp = {
            request: httpRequestMock,
            postJson: httpPostJsonMock,
            isHttpError: jest.fn(() => false)
        };

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
            set_rq_job_id: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        const colorMapMock = { enableColorMap: jest.fn() };
        global.SubcatchmentDelineation = {
            getInstance: jest.fn(() => colorMapMock)
        };
        global.url_for_run = jest.fn((path) => path);

        await import("../rangeland_cover.js");
        rangeland = window.RangelandCover.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.RangelandCover;
        delete global.controlBase;
        delete global.SubcatchmentDelineation;
        delete global.url_for_run;
        delete global.WCHttp;
        delete global.WCEvents;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        document.body.innerHTML = "";
    });

    test("emits config loaded event on bootstrap", () => {
        const configEvent = eventLog.find((item) => item.event === "rangeland:config:loaded");
        expect(configEvent).toBeDefined();
        expect(configEvent.payload).toEqual({
            mode: 0,
            rapYear: 2020,
            defaults: {
                bunchgrass: 10,
                forbs: 20,
                sodgrass: 30,
                shrub: 40,
                basal: 15,
                rock: 5,
                litter: 25,
                cryptogams: 5
            }
        });
    });

    test("mode change posts payload and emits mode event", async () => {
        eventLog.length = 0;
        const modeRadio = document.querySelector('#rangeland_cover_mode2');
        modeRadio.checked = true;
        modeRadio.dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "tasks/set_rangeland_cover_mode/",
            { mode: 2, rap_year: 2020 },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );

        const modeEvent = eventLog.find((item) => item.event === "rangeland:mode:changed");
        expect(modeEvent).toBeDefined();
        expect(modeEvent.payload).toEqual({ mode: 2 });

        const rapSection = document.querySelector("[data-rangeland-rap-section]");
        expect(rapSection.hidden).toBe(false);
    });

    test("rap year change emits event and syncs mode", async () => {
        eventLog.length = 0;
        const rapInput = document.querySelector('[data-rangeland-input="rap-year"]');
        rapInput.value = "2025";
        rapInput.dispatchEvent(new Event("change", { bubbles: true }));

        await Promise.resolve();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "tasks/set_rangeland_cover_mode/",
            { mode: 0, rap_year: 2025 },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );

        const rapEvent = eventLog.find((item) => item.event === "rangeland:rap-year:changed");
        expect(rapEvent).toBeDefined();
        expect(rapEvent.payload).toEqual({ year: 2025 });
    });

    test("build success updates status, emits events, and refreshes report", async () => {
        eventLog.length = 0;
        const enableColorMap = global.SubcatchmentDelineation.getInstance().enableColorMap;

        rangeland.build();
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();

        expect(httpPostJsonMock).toHaveBeenCalledWith(
            "tasks/build_rangeland_cover/",
            expect.objectContaining({
                rap_year: 2020,
                defaults: expect.objectContaining({ bunchgrass: 10 })
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(httpRequestMock).toHaveBeenCalledWith("report/rangeland_cover/", expect.objectContaining({
            method: "GET"
        }));
        expect(enableColorMap).toHaveBeenCalledWith("rangeland_cover");

        const started = eventLog.find((item) => item.event === "rangeland:run:started");
        const completed = eventLog.find((item) => item.event === "rangeland:run:completed");
        const reportLoaded = eventLog.find((item) => item.event === "rangeland:report:loaded");

        expect(started).toBeDefined();
        expect(completed).toBeDefined();
        expect(reportLoaded).toBeDefined();

        expect(document.querySelector("#status").textContent).toContain("Success");
    });

    test("build failure surfaces stack trace and emits failure event", async () => {
        httpPostJsonMock.mockImplementationOnce(() => Promise.reject(new Error("boom")));
        eventLog.length = 0;

        rangeland.build();
        await Promise.resolve();
        await Promise.resolve();

        const failedEvent = eventLog.find((item) => item.event === "rangeland:run:failed");
        expect(failedEvent).toBeDefined();
        expect(document.querySelector("#status").textContent).toContain("Failed to build rangeland cover.");
    });
});

describe("RangelandCover legacy compatibility", () => {
    let eventLog;

    beforeEach(async () => {
        jest.resetModules();
        eventLog = [];

        document.body.innerHTML = `
            <form id="rangeland_cover_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <input type="radio" name="rangeland_cover_mode" value="0" checked>
                <input id="rap_year" name="rap_year" value="2021">
                <input id="bunchgrass" name="bunchgrass_cover" value="12">
                <input id="forbs" name="forbs_cover" value="8">
                <input id="sodgrass" name="sodgrass_cover" value="18">
                <input id="shrub" name="shrub_cover" value="28">
                <input id="basal" name="basal_cover" value="14">
                <input id="rock" name="rock_cover" value="6">
                <input id="litter" name="litter_cover" value="22">
                <input id="cryptogams" name="cryptogams_cover" value="4">
                <button id="btn_build_rangeland_cover" type="button" data-rangeland-action="build"></button>
            </form>
            <p id="hint_build_rangeland_cover"></p>
        `;

        await import("../dom.js");
        await import("../forms.js");

        global.WCEvents = {
            useEventMap: jest.fn((events, emitter) => emitter),
            createEmitter: () => {
                const listeners = {};
                return {
                    emit(event, payload) {
                        eventLog.push({ event, payload });
                        const bucket = listeners[event] || [];
                        bucket.slice().forEach((fn) => fn(payload));
                        return bucket.length > 0;
                    },
                    on(event, handler) {
                        (listeners[event] = listeners[event] || []).push(handler);
                        return () => {
                            listeners[event] = (listeners[event] || []).filter((fn) => fn !== handler);
                        };
                    }
                };
            }
        };

        const { base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
            set_rq_job_id: jest.fn()
        });
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.WCHttp = {
            request: jest.fn(() => Promise.resolve({ body: "" })),
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true } })),
            isHttpError: jest.fn(() => false)
        };
        global.url_for_run = jest.fn((path) => path);

        await import("../rangeland_cover.js");
        window.RangelandCover.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.RangelandCover;
        delete global.controlBase;
        delete global.url_for_run;
        delete global.WCHttp;
        delete global.WCEvents;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        document.body.innerHTML = "";
    });

    test("reads defaults from legacy cover field names", () => {
        const configEvent = eventLog.find((item) => item.event === "rangeland:config:loaded");
        expect(configEvent).toBeDefined();
        expect(configEvent.payload).toEqual({
            mode: 0,
            rapYear: 2021,
            defaults: {
                bunchgrass: 12,
                forbs: 8,
                sodgrass: 18,
                shrub: 28,
                basal: 14,
                rock: 6,
                litter: 22,
                cryptogams: 4
            }
        });
    });
});

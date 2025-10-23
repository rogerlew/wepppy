/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Disturbed controller", () => {
    let httpRequestMock;
    let controlBaseInstance;
    let statusStreamMock;
    let emitter;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <form id="sbs_upload_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="sbs_mode0_controls"></div>
                <div id="sbs_mode1_controls" hidden></div>
                <p id="hint_upload_sbs"></p>
                <p id="hint_remove_sbs"></p>
                <p id="hint_low_sbs"></p>
                <p id="hint_moderate_sbs"></p>
                <p id="hint_high_sbs"></p>
                <input type="radio" name="sbs_mode" value="0" checked>
                <input type="radio" name="sbs_mode" value="1">
                <button id="btn_upload_sbs" type="button" data-sbs-action="upload"></button>
                <button id="btn_remove_sbs" type="button" data-sbs-action="remove"></button>
                <button id="btn_remove_sbs_uniform" type="button" data-sbs-action="remove"></button>
                <button id="btn_uniform_low_sbs" type="button" data-sbs-uniform="1"></button>
                <button id="btn_uniform_moderate_sbs" type="button" data-sbs-uniform="2"></button>
                <button id="btn_uniform_high_sbs" type="button" data-sbs-uniform="3"></button>
                <input id="firedate" name="firedate" value="2024-01-01">
                <button id="btn_set_firedate" type="button" data-sbs-action="set-firedate" data-sbs-target="#firedate"></button>
            </form>
            <button type="button" data-disturbed-action="reset-lookup"></button>
            <button type="button" data-disturbed-action="load-extended-lookup"></button>
        `;

        await import("../dom.js");

        emitter = {
            emit: jest.fn(),
        };

        global.WCEvents = {
            createEmitter: jest.fn(() => emitter),
            useEventMap: jest.fn((_, e) => e),
        };

        global.WCForms = {
            serializeForm: jest.fn(() => ({ firedate: "2024-01-01" })),
        };

        httpRequestMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));

        global.WCHttp = {
            request: httpRequestMock,
            isHttpError: jest.fn().mockReturnValue(false),
        };

        ({ base: controlBaseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            triggerEvent: jest.fn(),
        }));
        global.controlBase = jest.fn(() => Object.assign({}, controlBaseInstance));

        await import("../disturbed.js");
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Disturbed;
        delete global.WCHttp;
        delete global.WCForms;
        delete global.controlBase;
        delete global.WCEvents;
        if (global.WCDom) {
            delete global.WCDom;
        }
        document.body.innerHTML = "";
    });

    function getController() {
        return window.Disturbed.getInstance();
    }

    test("switching modes toggles panels and emits mode event", () => {
        const controller = getController();
        const mode0 = document.querySelector("#sbs_mode0_controls");
        const mode1 = document.querySelector("#sbs_mode1_controls");
        const modeRadio = document.querySelector('input[name="sbs_mode"][value="1"]');

        expect(mode0.hidden).toBe(false);
        expect(mode1.hidden).toBe(true);

        modeRadio.checked = true;
        modeRadio.dispatchEvent(new Event("change", { bubbles: true }));

        expect(mode0.hidden).toBe(true);
        expect(mode1.hidden).toBe(false);
        expect(emitter.emit).toHaveBeenCalledWith("disturbed:mode:changed", { mode: 1 });
        expect(controller).toBeDefined();
    });

    test("set_has_sbs_cached updates cache and dispatches DOM event", () => {
        const controller = getController();
        const listener = jest.fn();
        document.addEventListener("disturbed:has_sbs_changed", listener);

        controller.set_has_sbs_cached(true);

        expect(listener).toHaveBeenCalledWith(expect.objectContaining({
            detail: { hasSbs: true, source: "manual" },
        }));
        expect(emitter.emit).toHaveBeenCalledWith("disturbed:sbs:state", { hasSbs: true, source: "manual" });
        document.removeEventListener("disturbed:has_sbs_changed", listener);
    });

    test("has_sbs triggers refresh when forced", async () => {
        const controller = getController();
        controller.clear_has_sbs_cache();
        expect(controller.has_sbs({ forceRefresh: true })).toBe(false);
        expect(httpRequestMock).toHaveBeenCalledWith("api/disturbed/has_sbs/", expect.objectContaining({
            method: "GET",
        }));
        await Promise.resolve();
    });

    test("build_uniform_sbs posts JSON payload", async () => {
        httpRequestMock.mockImplementationOnce((url, options) => {
            expect(url).toBe("tasks/build_uniform_sbs");
            expect(options.json).toEqual({ value: 2 });
            expect(options.method).toBe("POST");
            return Promise.resolve({ body: { Success: true } });
        });

        const controller = getController();
        await controller.build_uniform_sbs(2);
        expect(controlBaseInstance.triggerEvent).toHaveBeenCalledWith("job:completed", expect.objectContaining({
            task: "disturbed:uniform",
            severity: 2,
        }));
    });

    test("reset_land_soil_lookup posts to task endpoint", async () => {
        httpRequestMock.mockImplementationOnce((url, options) => {
            expect(url).toBe("tasks/reset_disturbed");
            expect(options.method).toBe("POST");
            return Promise.resolve({ body: { Success: true } });
        });

        const controller = getController();
        await controller.reset_land_soil_lookup();
        expect(emitter.emit).toHaveBeenCalledWith("disturbed:lookup:reset", {});
    });

    test("bootstrap seeds has_sbs cache", () => {
        const controller = getController();
        controller.clear_has_sbs_cache();

        controller.bootstrap({ flags: { initialHasSbs: true } });

        expect(controller.has_sbs()).toBe(true);
    });
});

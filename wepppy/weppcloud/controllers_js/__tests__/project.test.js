/**
 * @jest-environment jsdom
 */

describe("Project controller", () => {
    let project;
    let postJsonMock;
    let unitizerClient;
    let delegateTeardowns;
    let commandBar;

    function flushPromises() {
        return Promise.resolve();
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <div id="project-fixture">
                <input data-project-field="name" value="Existing Name">
                <input data-project-field="scenario" value="Initial Scenario">
                <input type="checkbox" data-project-toggle="readonly">
                <input type="checkbox" data-project-toggle="public">
                <input id="readonlyTarget" class="disable-readonly" type="text" value="editable">
                <label><input type="radio" name="unit_main_selector" value="0" data-project-unitizer="global" checked></label>
                <label><input type="radio" name="unit_main_selector" value="1" data-project-unitizer="global"></label>
                <section data-unitizer-category="discharge">
                    <input type="radio"
                           name="unitizer_discharge_radio"
                           value="units-metric"
                           data-project-unitizer="category"
                           checked>
                    <input type="radio"
                           name="unitizer_discharge_radio"
                           value="units-english"
                           data-project-unitizer="category">
                </section>
            </div>
        `;
        document.title = "Base Title";

        global.site_prefix = "/weppcloud";
        global.runid = "run-123";
        global.config = "config-a";

        commandBar = {
            showResult: jest.fn(),
            hideResult: jest.fn()
        };
        global.initializeCommandBar = jest.fn(() => commandBar);

        delegateTeardowns = [];
        global.controlBase = jest.fn(() => ({
            pushResponseStacktrace: jest.fn(),
            stacktrace: { show: jest.fn(), text: jest.fn() },
            command_btn_id: null
        }));

        global.WCDom = {
            qsa: jest.fn((selector) => Array.from(document.querySelectorAll(selector))),
            show: jest.fn((target) => {
                var element = typeof target === "string" ? document.querySelector(target) : target;
                if (!element) {
                    return;
                }
                element.hidden = false;
                element.style.display = "";
            }),
            hide: jest.fn((target) => {
                var element = typeof target === "string" ? document.querySelector(target) : target;
                if (!element) {
                    return;
                }
                element.hidden = true;
                element.style.display = "none";
            }),
            delegate: jest.fn((root, eventName, selector, handler) => {
                var element = root === document ? document : document.querySelector(root);
                if (!element) {
                    throw new Error("Delegate root not found for selector: " + selector);
                }
                var listener = function (event) {
                    var matched = event.target && event.target.closest(selector);
                    if (matched && element.contains(matched)) {
                        handler.call(matched, event, matched);
                    }
                };
                element.addEventListener(eventName, listener);
                delegateTeardowns.push(function () {
                    element.removeEventListener(eventName, listener);
                });
                return function unsubscribe() {
                    element.removeEventListener(eventName, listener);
                };
            })
        };

        postJsonMock = jest.fn((url, payload) => {
            if (url.indexOf("tasks/setname/") !== -1) {
                return Promise.resolve({ body: { Success: true, Content: { name: payload.name } } });
            }
            if (url.indexOf("tasks/setscenario/") !== -1) {
                return Promise.resolve({ body: { Success: true, Content: { scenario: payload.scenario } } });
            }
            if (url.indexOf("tasks/set_readonly") !== -1) {
                return Promise.resolve({ body: { Success: true, Content: { readonly: payload.readonly, job_id: "job-1" } } });
            }
            if (url.indexOf("tasks/set_public") !== -1) {
                return Promise.resolve({ body: { Success: true, Content: { public: payload.public } } });
            }
            if (url.indexOf("tasks/set_unit_preferences") !== -1) {
                return Promise.resolve({ body: { Success: true, Content: { preferences: payload } } });
            }
            return Promise.resolve({ body: { Success: true } });
        });

        global.WCHttp = {
            postJson: postJsonMock,
            request: jest.fn(() => Promise.resolve({ body: { Success: true } })),
            getJson: jest.fn(() => Promise.resolve({ body: { Success: true } })),
            isHttpError: jest.fn(() => false)
        };

        unitizerClient = {
            setGlobalPreference: jest.fn(),
            applyPreferenceRadios: jest.fn(),
            applyGlobalRadio: jest.fn(),
            syncPreferencesFromDom: jest.fn(),
            getPreferenceTokens: jest.fn(() => ({ discharge: "units-metric" })),
            getPreferencePayload: jest.fn(() => ({ discharge: "metric" })),
            updateUnitLabels: jest.fn(),
            registerNumericInputs: jest.fn(),
            updateNumericFields: jest.fn(),
            dispatchPreferenceChange: jest.fn()
        };

        global.UnitizerClient = {
            ready: jest.fn(() => Promise.resolve(unitizerClient))
        };

        await import("../events.js");
        await import("../project.js");
        project = window.Project.getInstance();
        await flushPromises();
    });

    afterEach(() => {
        delegateTeardowns.forEach((fn) => fn());
        jest.clearAllMocks();
        jest.clearAllTimers();
        jest.useRealTimers();

        delete window.Project;
        delete global.WCDom;
        delete global.WCHttp;
        delete global.UnitizerClient;
        delete global.controlBase;
        delete global.site_prefix;
        delete global.runid;
        delete global.config;
        delete global.initializeCommandBar;
        delete global.setGlobalUnitizerPreference;

        document.body.innerHTML = "";
        document.title = "";
    });

    test("setName updates DOM and emits project:name:updated", async () => {
        const handler = jest.fn();
        project.events.on("project:name:updated", handler);

        await project.setName("New Name");

        expect(postJsonMock).toHaveBeenCalledWith("tasks/setname/", { name: "New Name" });
        expect(document.querySelector('[data-project-field="name"]').value).toBe("New Name");
        expect(document.title).toBe("Base Title - New Name");
        expect(handler).toHaveBeenCalledWith(expect.objectContaining({
            name: "New Name",
            previous: "Existing Name"
        }));
        expect(commandBar.showResult).toHaveBeenCalledWith('Saved project name to "New Name"');
    });

    test("setScenarioFromInput debounces network calls", async () => {
        jest.useFakeTimers();

        const scenarioInput = document.querySelector('[data-project-field="scenario"]');
        scenarioInput.value = "Alpha Scenario";

        project.setScenarioFromInput({ source: scenarioInput, debounceMs: 50 });

        expect(postJsonMock).not.toHaveBeenCalledWith("tasks/setscenario/", expect.anything());

        jest.advanceTimersByTime(49);
        await flushPromises();
        expect(postJsonMock).not.toHaveBeenCalledWith("tasks/setscenario/", expect.anything());

        jest.advanceTimersByTime(1);
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith("tasks/setscenario/", { scenario: "Alpha Scenario" });
    });

    test("setScenario restores previous value and emits failure on error", async () => {
        const handler = jest.fn();
        const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
        project.events.on("project:scenario:update:failed", handler);

        postJsonMock.mockRejectedValueOnce(new Error("network"));

        const result = await project.setScenario("Failure Scenario");

        expect(result).toBeNull();
        expect(document.querySelector('[data-project-field="scenario"]').value).toBe("Initial Scenario");
        expect(handler).toHaveBeenCalledWith(expect.objectContaining({
            attempted: "Failure Scenario",
            previous: "Initial Scenario"
        }));
        expect(commandBar.showResult).toHaveBeenCalledWith("Error saving scenario");
        consoleSpy.mockRestore();
    });

    test("set_readonly updates controls and emits project:readonly:changed", async () => {
        const handler = jest.fn();
        project.events.on("project:readonly:changed", handler);

        await project.set_readonly(true);

        expect(postJsonMock).toHaveBeenCalledWith("tasks/set_readonly", { readonly: true });
        expect(document.querySelector('[data-project-toggle="readonly"]').checked).toBe(true);
        expect(document.getElementById("readonlyTarget").readOnly).toBe(true);
        expect(handler).toHaveBeenCalledWith(expect.objectContaining({
            readonly: true,
            previous: false
        }));
    });

    test("readonly checkbox change delegates to controller", async () => {
        const checkbox = document.querySelector('[data-project-toggle="readonly"]');
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));

        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith("tasks/set_readonly", { readonly: true });
    });

    test("handleGlobalUnitPreference persists preferences and emits events", async () => {
        const handler = jest.fn();
        project.events.on("project:unitizer:preferences", handler);

        await project.handleGlobalUnitPreference(1);

        expect(UnitizerClient.ready).toHaveBeenCalled();
        expect(postJsonMock).toHaveBeenCalledWith(
            "runs/run-123/config-a/tasks/set_unit_preferences/",
            { discharge: "metric" }
        );
        expect(handler).toHaveBeenCalledWith(expect.objectContaining({
            preferences: { discharge: "metric" },
            source: "global"
        }));
        expect(document.querySelector('[data-project-unitizer="global"][value="1"]').checked).toBe(true);
    });

    test("global setGlobalUnitizerPreference delegates to controller", async () => {
        const spy = jest.spyOn(project, "handleGlobalUnitPreference").mockResolvedValue(undefined);
        await global.setGlobalUnitizerPreference(0);
        expect(spy).toHaveBeenCalledWith(0);
        spy.mockRestore();
    });
});

/**
 * @jest-environment jsdom
 */

describe("Project controller", () => {
    let project;
    let postJsonMock;
    let requestMock;
    let getJsonMock;
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
        global.WCRecorder = { emit: jest.fn() };

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
                return Promise.resolve({ body: { Content: { name: payload.name } } });
            }
            if (url.indexOf("tasks/setscenario/") !== -1) {
                return Promise.resolve({ body: { Content: { scenario: payload.scenario } } });
            }
            if (url.indexOf("tasks/set_readonly") !== -1) {
                return Promise.resolve({ body: { Content: { readonly: payload.readonly, job_id: "job-1" } } });
            }
            if (url.indexOf("tasks/set_public") !== -1) {
                return Promise.resolve({ body: { Content: { public: payload.public } } });
            }
            if (url.indexOf("tasks/set_unit_preferences") !== -1) {
                return Promise.resolve({ body: { Content: { preferences: payload } } });
            }
            return Promise.resolve({ body: {} });
        });

        requestMock = jest.fn(() => Promise.resolve({ body: {} }));
        getJsonMock = jest.fn(() => Promise.resolve({ body: {} }));
        global.WCHttp = {
            postJson: postJsonMock,
            request: requestMock,
            getJson: getJsonMock,
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

        global.url_for_run = jest.fn((path) => path);

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
        delete global.WCRecorder;
        delete global.url_for_run;
        delete global.setGlobalUnitizerPreference;
        delete window.Geneva;
        delete window.runContext;

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

    test("set_mod bootstraps Geneva after rendering the dynamic section", async () => {
        window.runContext = { mods: { list: [], flags: {} } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="geneva" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="geneva">
        `);
        const eventOrder = [];
        const updatedHandler = jest.fn(() => {
            eventOrder.push("event");
        });
        project.events.on("project:mod:updated", updatedHandler);

        const workflowClickHandler = jest.fn();
        const bootstrap = jest.fn(() => {
            eventOrder.push("bootstrap");
            document
                .querySelector('[data-geneva-action="run-workflow"]')
                .addEventListener("click", workflowClickHandler);
        });
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };
        requestMock.mockResolvedValueOnce({ body: { Content: { label: "Geneva" } } });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: '<section id="geneva"><form id="geneva_form"><button type="button" data-geneva-action="run-workflow">Run Geneva Workflow</button></form></section>'
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });

        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => {
            setTimeout(resolve, 0);
        });
        await resultPromise;

        expect(requestMock).toHaveBeenCalledWith("tasks/set_mod", {
            method: "POST",
            json: { mod: "geneva", enabled: true }
        });
        expect(getJsonMock).toHaveBeenCalledWith("view/mod/geneva");
        expect(document.querySelector('[data-mod-nav="geneva"]').hidden).toBe(false);
        expect(document.querySelector('[data-mod-section="geneva"]').hidden).toBe(false);
        expect(input.checked).toBe(true);
        expect(input.disabled).toBe(false);
        expect(window.runContext.mods.list).toContain("geneva");
        expect(window.runContext.mods.flags.geneva).toBe(true);
        expect(window.Geneva.getInstance).toHaveBeenCalled();
        expect(bootstrap).toHaveBeenCalledWith(window.runContext);
        expect(updatedHandler).toHaveBeenCalledWith(expect.objectContaining({
            mod: "geneva",
            enabled: true,
            label: "Geneva"
        }));
        expect(bootstrap.mock.invocationCallOrder[0]).toBeLessThan(updatedHandler.mock.invocationCallOrder[0]);
        expect(eventOrder).toEqual(["bootstrap", "event"]);

        document.querySelector('[data-geneva-action="run-workflow"]').click();
        expect(workflowClickHandler).toHaveBeenCalled();
    });

    test("set_mod bootstraps AgFields after rendering the dynamic section", async () => {
        window.runContext = { mods: { list: [], flags: {} } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="ag_fields" hidden></li>
            <div data-mod-section="ag_fields" hidden></div>
            <input type="checkbox" data-project-mod="ag_fields">
        `);
        const bootstrap = jest.fn();
        window.AgFields = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };
        requestMock.mockResolvedValueOnce({ body: { Content: { label: "Agricultural Fields" } } });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: '<section id="ag-fields"><form id="ag_fields_form"></form></section>'
            }
        });

        const input = document.querySelector('[data-project-mod="ag_fields"]');
        input.checked = true;
        const resultPromise = project.set_mod("ag_fields", true, { input, notify: false });

        await flushPromises();
        await new Promise((resolve) => {
            setTimeout(resolve, 0);
        });
        await resultPromise;

        expect(getJsonMock).toHaveBeenCalledWith("view/mod/ag_fields");
        expect(window.AgFields.getInstance).toHaveBeenCalled();
        expect(bootstrap).toHaveBeenCalledWith(window.runContext);
        expect(window.runContext.mods.flags.ag_fields).toBe(true);
        expect(document.querySelector('[data-mod-section="ag_fields"]').hidden).toBe(false);
    });

    test("set_mod reconciles authoritative backend mods and syncs dependent toggles", async () => {
        window.runContext = { mods: { list: [], flags: { geneva: false, roads: false } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="openet_ts" hidden></li>
            <li data-mod-nav="geneva" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="openet_ts">
            <input type="checkbox" data-project-mod="geneva">
            <input type="checkbox" data-project-mod="roads">
        `);

        const bootstrap = jest.fn();
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["geneva", "roads"]
                }
            }
        });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: "<section id='geneva'>Geneva control</section>"
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await resultPromise;

        expect(window.runContext.mods.list).toEqual(expect.arrayContaining(["geneva", "roads"]));
        expect(window.runContext.mods.flags.geneva).toBe(true);
        expect(window.runContext.mods.flags.roads).toBe(true);
        expect(document.querySelector('[data-project-mod="roads"]').checked).toBe(true);
        expect(document.querySelector('[data-mod-nav="geneva"]').hidden).toBe(false);
        expect(document.querySelector('[data-mod-nav="roads"]').hidden).toBe(false);
    });

    test("set_mod preserves capability-gated flags while syncing authoritative dependencies", async () => {
        window.runContext = {
            mods: {
                list: ["openet_ts"],
                flags: { openet_ts: false, geneva: false, roads: false }
            }
        };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="openet_ts" hidden></li>
            <li data-mod-nav="geneva" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="openet_ts">
            <input type="checkbox" data-project-mod="geneva">
            <input type="checkbox" data-project-mod="roads">
        `);

        const bootstrap = jest.fn();
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["openet_ts", "geneva", "roads"]
                }
            }
        });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: "<section id='geneva'>Geneva control</section>"
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await resultPromise;

        expect(window.runContext.mods.list).toEqual(["openet_ts", "geneva", "roads"]);
        expect(window.runContext.mods.flags.openet_ts).toBe(false);
        expect(window.runContext.mods.flags.geneva).toBe(true);
        expect(window.runContext.mods.flags.roads).toBe(true);
        expect(document.querySelector('[data-project-mod="openet_ts"]').checked).toBe(false);
        expect(document.querySelector('[data-project-mod="roads"]').checked).toBe(true);
        expect(document.querySelector('[data-mod-nav="openet_ts"]').hidden).toBe(true);
        expect(document.querySelector('[data-mod-nav="geneva"]').hidden).toBe(false);
        expect(document.querySelector('[data-mod-nav="roads"]').hidden).toBe(false);
    });

    test("set_mod keeps capability-gated flags disabled when backend reintroduces gated mods", async () => {
        window.runContext = {
            mods: {
                list: [],
                flags: { openet_ts: false, geneva: false, roads: false }
            }
        };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="openet_ts" hidden></li>
            <li data-mod-nav="geneva" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="openet_ts">
            <input type="checkbox" data-project-mod="geneva">
            <input type="checkbox" data-project-mod="roads">
        `);

        const bootstrap = jest.fn();
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["openet_ts", "geneva", "roads"]
                }
            }
        });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: "<section id='geneva'>Geneva control</section>"
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await resultPromise;

        expect(window.runContext.mods.flags.openet_ts).toBe(false);
        expect(document.querySelector('[data-project-mod="openet_ts"]').checked).toBe(false);
        expect(document.querySelector('[data-mod-nav="openet_ts"]').hidden).toBe(true);
        expect(window.runContext.mods.flags.roads).toBe(true);
        expect(document.querySelector('[data-project-mod="roads"]').checked).toBe(true);
        expect(document.querySelector('[data-mod-nav="roads"]').hidden).toBe(false);
    });

    test("set_mod defaults sticky-gated mods to hidden when gate flag key is absent", async () => {
        window.runContext = {
            mods: {
                list: [],
                flags: { geneva: false, roads: false }
            }
        };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="openet_ts" hidden></li>
            <li data-mod-nav="geneva" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="openet_ts">
            <input type="checkbox" data-project-mod="geneva">
            <input type="checkbox" data-project-mod="roads">
        `);

        const bootstrap = jest.fn();
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["openet_ts", "geneva", "roads"]
                }
            }
        });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: "<section id='geneva'>Geneva control</section>"
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await resultPromise;

        expect(window.runContext.mods.flags.openet_ts).toBe(false);
        expect(document.querySelector('[data-project-mod="openet_ts"]').checked).toBe(false);
        expect(document.querySelector('[data-mod-nav="openet_ts"]').hidden).toBe(true);
        expect(window.runContext.mods.flags.roads).toBe(true);
        expect(document.querySelector('[data-project-mod="roads"]').checked).toBe(true);
    });

    test("set_mod loads and bootstraps newly enabled dependent modules from authoritative response", async () => {
        window.runContext = { mods: { list: [], flags: { geneva: false, roads: false } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="geneva" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <div data-mod-section="roads" hidden></div>
            <input type="checkbox" data-project-mod="geneva">
            <input type="checkbox" data-project-mod="roads">
        `);

        const genevaBootstrap = jest.fn();
        const roadsBootstrap = jest.fn();
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap: genevaBootstrap }))
        };
        window.Roads = {
            getInstance: jest.fn(() => ({ bootstrap: roadsBootstrap }))
        };

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["geneva", "roads"]
                }
            }
        });
        getJsonMock
            .mockResolvedValueOnce({ Content: { html: "<section id='geneva'>Geneva control</section>" } })
            .mockResolvedValueOnce({ Content: { html: "<section id='roads'>Roads control</section>" } });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await resultPromise;

        expect(getJsonMock).toHaveBeenNthCalledWith(1, "view/mod/geneva");
        expect(getJsonMock).toHaveBeenNthCalledWith(2, "view/mod/roads");
        expect(document.querySelector('[data-mod-section="roads"]').hidden).toBe(false);
        expect(document.querySelector('[data-mod-section="roads"]').innerHTML).toContain("Roads control");
        expect(roadsBootstrap).toHaveBeenCalledWith(window.runContext);
        expect(window.runContext.mods.flags.roads).toBe(true);
    });

    test("set_mod returns dependency failure and suppresses success event when dependent bootstrap fails", async () => {
        window.runContext = { mods: { list: [], flags: { geneva: false, roads: false } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="geneva" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <div data-mod-section="roads" hidden></div>
            <input type="checkbox" data-project-mod="geneva">
            <input type="checkbox" data-project-mod="roads">
        `);

        const updatedHandler = jest.fn();
        const failedHandler = jest.fn();
        project.events.on("project:mod:updated", updatedHandler);
        project.events.on("project:mod:update:failed", failedHandler);

        const genevaBootstrap = jest.fn();
        const roadsBootstrap = jest.fn(() => {
            throw new Error("roads bootstrap failure");
        });
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap: genevaBootstrap }))
        };
        window.Roads = {
            getInstance: jest.fn(() => ({ bootstrap: roadsBootstrap }))
        };

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["geneva", "roads"]
                }
            }
        });
        getJsonMock
            .mockResolvedValueOnce({ Content: { html: "<section id='geneva'>Geneva control</section>" } })
            .mockResolvedValueOnce({ Content: { html: "<section id='roads'>Roads control</section>" } });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        const result = await resultPromise;

        expect(result).toEqual(expect.objectContaining({
            error: expect.objectContaining({
                phase: "dependency"
            }),
            dependency_error: expect.objectContaining({
                mod: "roads"
            })
        }));
        expect(updatedHandler).not.toHaveBeenCalled();
        expect(failedHandler).toHaveBeenCalledWith(expect.objectContaining({
            mod: "roads",
            phase: "bootstrap"
        }));
        expect(input.disabled).toBe(false);
        expect(input.checked).toBe(true);
    });

    test("set_mod skips render/bootstrap when authoritative mods exclude requested mod", async () => {
        window.runContext = { mods: { list: [], flags: { geneva: false } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="geneva" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="geneva">
        `);
        const bootstrap = jest.fn();
        window.Geneva = {
            getInstance: jest.fn(() => ({ bootstrap }))
        };
        const updatedHandler = jest.fn();
        project.events.on("project:mod:updated", updatedHandler);

        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: []
                }
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const result = await project.set_mod("geneva", true, { input, notify: false });

        expect(result).toEqual(expect.objectContaining({
            Content: expect.objectContaining({
                mods: []
            })
        }));
        expect(getJsonMock).not.toHaveBeenCalled();
        expect(window.Geneva.getInstance).not.toHaveBeenCalled();
        expect(bootstrap).not.toHaveBeenCalled();
        expect(window.runContext.mods.flags.geneva).toBe(false);
        expect(window.runContext.mods.list).toEqual([]);
        expect(document.querySelector('[data-mod-nav="geneva"]').hidden).toBe(true);
        expect(input.checked).toBe(false);
        expect(updatedHandler).toHaveBeenCalledWith(expect.objectContaining({
            mod: "geneva",
            enabled: false,
            desired: true
        }));
    });

    test("set_mod disable path syncs nav, section teardown, and runContext", async () => {
        window.runContext = { mods: { list: ["geneva"], flags: { geneva: true } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="geneva"></li>
            <div data-mod-section="geneva"><div>Loaded</div></div>
            <input type="checkbox" data-project-mod="geneva" checked>
        `);
        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: []
                }
            }
        });

        const failedHandler = jest.fn();
        const updatedHandler = jest.fn();
        project.events.on("project:mod:update:failed", failedHandler);
        project.events.on("project:mod:updated", updatedHandler);

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = false;
        const result = await project.set_mod("geneva", false, { input, notify: false });

        expect(result).toEqual(expect.objectContaining({
            Content: expect.objectContaining({
                mods: []
            })
        }));
        expect(window.runContext.mods.list).toEqual([]);
        expect(window.runContext.mods.flags.geneva).toBe(false);
        expect(document.querySelector('[data-mod-nav="geneva"]').hidden).toBe(true);
        expect(document.querySelector('[data-mod-section="geneva"]').innerHTML).toBe("");
        expect(input.checked).toBe(false);
        expect(updatedHandler).toHaveBeenCalledWith(expect.objectContaining({
            mod: "geneva",
            enabled: false,
            desired: false
        }));
        expect(failedHandler).not.toHaveBeenCalled();
    });

    test("set_mod preserves enabled state when bootstrap fails after authoritative enable", async () => {
        window.runContext = { mods: { list: [], flags: { geneva: false } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="geneva" hidden></li>
            <div data-mod-section="geneva" hidden></div>
            <input type="checkbox" data-project-mod="geneva">
        `);
        window.Geneva = {
            getInstance: jest.fn(() => ({
                bootstrap: () => {
                    throw new Error("bootstrap failure");
                }
            }))
        };
        requestMock.mockResolvedValueOnce({
            body: {
                Content: {
                    label: "Geneva",
                    mods: ["geneva"]
                }
            }
        });
        getJsonMock.mockResolvedValueOnce({
            Content: {
                html: "<section id='geneva'>Geneva control</section>"
            }
        });

        const input = document.querySelector('[data-project-mod="geneva"]');
        input.checked = true;
        const resultPromise = project.set_mod("geneva", true, { input, notify: false });
        await flushPromises();
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));
        const result = await resultPromise;

        expect(result).toEqual(expect.objectContaining({
            error: expect.objectContaining({
                phase: "bootstrap"
            })
        }));
        expect(window.runContext.mods.list).toEqual(expect.arrayContaining(["geneva"]));
        expect(window.runContext.mods.flags.geneva).toBe(true);
        expect(document.querySelector('[data-mod-nav="geneva"]').hidden).toBe(false);
        expect(input.checked).toBe(true);
        expect(commandBar.showResult.mock.calls.join("\n")).not.toContain("Geneva enabled.");
    });

    test("set_mod restores prior checkbox state on request failure during idempotent enable", async () => {
        window.runContext = { mods: { list: ["rusle"], flags: { rusle: true } } };
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <input type="checkbox" data-project-mod="rusle" checked>
        `);
        requestMock.mockRejectedValueOnce(new Error("network down"));

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        const result = await project.set_mod("rusle", true, { input, notify: false });

        expect(result).toBeNull();
        expect(input.disabled).toBe(false);
        expect(input.checked).toBe(true);
    });

    test("set_mod surfaces response diagnostics to users when backend returns an error payload", async () => {
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <input type="checkbox" data-project-mod="rusle">
        `);
        requestMock.mockResolvedValueOnce({
            body: {
                error: {
                    message: "RUSLE requires disturbed mode",
                    details: "Traceback (most recent call last):\nValueError: requirement failed"
                }
            }
        });

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        const result = await project.set_mod("rusle", true, { input });

        expect(result).toEqual(expect.objectContaining({
            error: expect.objectContaining({
                message: "RUSLE requires disturbed mode"
            })
        }));
        expect(input.disabled).toBe(false);
        expect(input.checked).toBe(false);

        const lastMessage = commandBar.showResult.mock.calls[commandBar.showResult.mock.calls.length - 1][0];
        expect(lastMessage).toContain("project.set_mod failed");
        expect(lastMessage).toContain("mod=rusle enabled=true phase=response");
        expect(lastMessage).toContain("message=RUSLE requires disturbed mode");
        expect(lastMessage).toContain("stacktrace:");
        expect(lastMessage).toContain("Traceback (most recent call last):");
        expect(global.WCRecorder.emit).toHaveBeenCalledWith(
            "project_mod_toggle_error",
            expect.objectContaining({
                category: "mod-toggle",
                mod: "rusle",
                enabled: true,
                phase: "response"
            })
        );
    });

    test("set_mod redacts sensitive diagnostics before command bar and recorder emission", async () => {
        const failedHandler = jest.fn();
        project.events.on("project:mod:update:failed", failedHandler);
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <input type="checkbox" data-project-mod="rusle">
        `);
        requestMock.mockResolvedValueOnce({
            body: {
                error: {
                    message: "authorization=Bearer abc.def",
                    details: "Traceback (most recent call last):\ncookie=sessionid=abc\nurl=/x?token=abc123"
                }
            }
        });

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        await project.set_mod("rusle", true, { input });

        const lastMessage = commandBar.showResult.mock.calls[commandBar.showResult.mock.calls.length - 1][0];
        expect(lastMessage).toContain("message=authorization=[redacted]");
        expect(lastMessage).toContain("cookie=[redacted]");
        expect(lastMessage).toContain("token=[redacted]");
        expect(lastMessage).not.toContain("abc.def");
        expect(lastMessage).not.toContain("sessionid=abc");
        expect(lastMessage).not.toContain("abc123");

        expect(global.WCRecorder.emit).toHaveBeenCalledWith(
            "project_mod_toggle_error",
            expect.objectContaining({
                message: "authorization=[redacted]",
                detail: expect.stringContaining("cookie=[redacted]"),
                stacktrace: expect.arrayContaining([
                    expect.stringContaining("token=[redacted]")
                ])
            })
        );
        expect(failedHandler).toHaveBeenCalledWith(expect.objectContaining({
            phase: "response",
            response: expect.objectContaining({
                error: expect.objectContaining({
                    message: "authorization=[redacted]",
                    details: expect.stringContaining("cookie=[redacted]")
                })
            }),
            error: null
        }));
    });

    test("set_mod surfaces request diagnostics to users when transport throws", async () => {
        const failedHandler = jest.fn();
        project.events.on("project:mod:update:failed", failedHandler);

        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <input type="checkbox" data-project-mod="rusle">
        `);
        const transportError = new Error("network down");
        transportError.status = 503;
        transportError.statusText = "Service Unavailable";
        transportError.url = "/runs/run-123/config-a/tasks/set_mod";
        transportError.detail = "upstream timeout";
        transportError.body = {
            error: {
                message: "upstream timeout",
                details: "Traceback (most recent call last):\nRuntimeError: upstream timeout"
            }
        };
        transportError.stack = "Error: network down\n    at set_mod";
        requestMock.mockRejectedValueOnce(transportError);

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        const result = await project.set_mod("rusle", true, { input });

        expect(result).toBeNull();
        expect(input.disabled).toBe(false);
        expect(input.checked).toBe(false);

        const lastMessage = commandBar.showResult.mock.calls[commandBar.showResult.mock.calls.length - 1][0];
        expect(lastMessage).toContain("project.set_mod failed");
        expect(lastMessage).toContain("mod=rusle enabled=true phase=request");
        expect(lastMessage).toContain("status=503 Service Unavailable");
        expect(lastMessage).toContain("message=upstream timeout");
        expect(lastMessage).toContain("detail=Traceback (most recent call last):");
        expect(lastMessage).toContain("RuntimeError: upstream timeout");
        expect(lastMessage).toContain("stacktrace:");
        expect(lastMessage).toContain("Error: network down");
        expect(lastMessage).toContain("RuntimeError: upstream timeout");
        expect(global.WCRecorder.emit).toHaveBeenCalledWith(
            "project_mod_toggle_error",
            expect.objectContaining({
                category: "mod-toggle",
                mod: "rusle",
                enabled: true,
                phase: "request",
                status: 503
            })
        );
        expect(failedHandler).toHaveBeenCalledWith(expect.objectContaining({
            mod: "rusle",
            phase: "request",
            diagnostic: expect.objectContaining({
                detail: expect.stringContaining("RuntimeError: upstream timeout"),
                stack: expect.arrayContaining([
                    expect.stringContaining("RuntimeError: upstream timeout")
                ])
            })
        }));
    });

    test("set_mod emits sanitized request-phase error payload on failed events", async () => {
        const failedHandler = jest.fn();
        project.events.on("project:mod:update:failed", failedHandler);

        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <input type="checkbox" data-project-mod="rusle">
        `);
        const transportError = new Error("network down");
        transportError.detail = "authorization=Bearer abc.def";
        transportError.body = {
            error: {
                message: "request failed",
                details: {
                    access_token: "abc123",
                    cookie: "sessionid=abc"
                }
            }
        };
        requestMock.mockRejectedValueOnce(transportError);

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        await project.set_mod("rusle", true, { input, notify: false });

        expect(failedHandler).toHaveBeenCalledWith(expect.objectContaining({
            phase: "request",
            error: expect.objectContaining({
                detail: "authorization=[redacted]",
                body: expect.objectContaining({
                    error: expect.objectContaining({
                        details: expect.objectContaining({
                            access_token: "[redacted]",
                            cookie: "[redacted]"
                        })
                    })
                })
            })
        }));
        const errorPayload = failedHandler.mock.calls[0][0].error;
        expect(JSON.stringify(errorPayload)).not.toContain("abc.def");
        expect(JSON.stringify(errorPayload)).not.toContain("sessionid=abc");
    });

    test("set_mod preserves nested traceback arrays from transport detail objects", async () => {
        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <input type="checkbox" data-project-mod="rusle">
        `);
        const transportError = new Error("network down");
        transportError.status = 503;
        transportError.statusText = "Service Unavailable";
        transportError.detail = {
            message: "transport wrapper",
            details: [
                "Traceback (most recent call last):",
                "RuntimeError: nested transport detail"
            ]
        };
        transportError.body = {
            error: {
                message: "upstream timeout",
                details: [
                    "Traceback (most recent call last):",
                    "RuntimeError: nested upstream timeout"
                ]
            }
        };
        requestMock.mockRejectedValueOnce(transportError);

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        await project.set_mod("rusle", true, { input });

        const lastMessage = commandBar.showResult.mock.calls[commandBar.showResult.mock.calls.length - 1][0];
        expect(lastMessage).toContain("detail=Traceback (most recent call last):");
        expect(lastMessage).toContain("RuntimeError: nested transport detail");
        expect(lastMessage).toContain("RuntimeError: nested upstream timeout");

        expect(global.WCRecorder.emit).toHaveBeenCalledWith(
            "project_mod_toggle_error",
            expect.objectContaining({
                stacktrace: expect.arrayContaining([
                    expect.stringContaining("RuntimeError: nested transport detail"),
                    expect.stringContaining("RuntimeError: nested upstream timeout")
                ])
            })
        );
    });

    test("set_mod surfaces render-phase diagnostics when module section loading fails", async () => {
        const failedHandler = jest.fn();
        project.events.on("project:mod:update:failed", failedHandler);
        window.runContext = { mods: { list: [], flags: { rusle: false, roads: false } } };

        document.getElementById("project-fixture").insertAdjacentHTML("beforeend", `
            <li data-mod-nav="rusle" hidden></li>
            <li data-mod-nav="roads" hidden></li>
            <div data-mod-section="rusle" hidden></div>
            <input type="checkbox" data-project-mod="rusle">
            <input type="checkbox" data-project-mod="roads">
        `);
        requestMock.mockResolvedValueOnce({
            body: { Content: { label: "RUSLE", mods: ["rusle", "roads"] } }
        });
        getJsonMock.mockRejectedValueOnce({
            status: 500,
            statusText: "Internal Server Error",
            body: {
                error: {
                    message: "Module fragment unavailable",
                    details: "Traceback (most recent call last):\nRuntimeError: render failed\ncookie=sessionid=abc"
                }
            }
        });

        const input = document.querySelector('[data-project-mod="rusle"]');
        input.checked = true;
        const result = await project.set_mod("rusle", true, { input });

        expect(result).toEqual(expect.objectContaining({
            error: expect.objectContaining({
                message: "Module fragment unavailable",
                detail: expect.stringContaining("RuntimeError: render failed"),
                details: expect.stringContaining("RuntimeError: render failed"),
                phase: "render"
            }),
            Content: expect.objectContaining({ label: "RUSLE", mods: ["rusle", "roads"] }),
            response: expect.objectContaining({
                Content: expect.objectContaining({ label: "RUSLE", mods: ["rusle", "roads"] })
            }),
            render_error: expect.objectContaining({
                details: expect.stringContaining("RuntimeError: render failed"),
                phase: "render"
            }),
            diagnostic: expect.objectContaining({
                phase: "render",
                message: "Module fragment unavailable"
            })
        }));
        expect(input.disabled).toBe(false);
        expect(input.checked).toBe(true);
        expect(document.querySelector('[data-project-mod="roads"]').checked).toBe(true);
        expect(document.querySelector('[data-mod-nav="rusle"]').hidden).toBe(false);
        expect(document.querySelector('[data-mod-nav="roads"]').hidden).toBe(false);
        expect(window.runContext.mods.list).toEqual(["rusle", "roads"]);
        expect(window.runContext.mods.flags.rusle).toBe(true);
        expect(window.runContext.mods.flags.roads).toBe(true);

        const lastMessage = commandBar.showResult.mock.calls[commandBar.showResult.mock.calls.length - 1][0];
        expect(lastMessage).toContain("project.set_mod failed");
        expect(lastMessage).toContain("mod=rusle enabled=true phase=render");
        expect(lastMessage).toContain("message=Module fragment unavailable");
        expect(lastMessage).toContain("stacktrace:");
        expect(lastMessage).toContain("RuntimeError: render failed");
        expect(lastMessage).toContain("cookie=[redacted]");
        expect(lastMessage).not.toContain("sessionid=abc");

        expect(failedHandler).toHaveBeenCalledWith(expect.objectContaining({
            mod: "rusle",
            enabled: true,
            phase: "render",
            error: expect.objectContaining({
                body: expect.objectContaining({
                    error: expect.objectContaining({
                        details: expect.stringContaining("cookie=[redacted]")
                    })
                })
            }),
            response: expect.objectContaining({
                Content: expect.objectContaining({ label: "RUSLE", mods: ["rusle", "roads"] })
            }),
            diagnostic: expect.objectContaining({
                message: "Module fragment unavailable"
            })
        }));
    });
});

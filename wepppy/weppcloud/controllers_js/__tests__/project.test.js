/**
 * @jest-environment jsdom
 */

describe("Project controller", () => {
    let postFormMock;
    let project;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <input id="input_name" data-project-field="name" value="Existing Name">
            <input id="input_scenario" data-project-field="scenario" value="Initial Scenario">
        `;
        document.title = "Base Title";

        global.controlBase = jest.fn(() => ({
            pushResponseStacktrace: jest.fn(),
            stacktrace: { show: jest.fn(), text: jest.fn() },
            command_btn_id: null,
        }));

        global.WCDom = {
            qsa: jest.fn((selector) => Array.from(document.querySelectorAll(selector))),
            hide: jest.fn(),
            show: jest.fn(),
        };

        postFormMock = jest.fn(() => Promise.resolve({ body: { Success: true } }));

        global.WCHttp = {
            postForm: postFormMock,
            postJson: jest.fn(() => Promise.resolve({ body: { Success: true } })),
            getJson: jest.fn(() => Promise.resolve({ Success: true })),
            request: jest.fn(() => Promise.resolve({ body: { Success: true } })),
            isHttpError: jest.fn(() => false),
        };

        const unitizerClient = {
            getPreferenceTokens: jest.fn(() => ({})),
            updateUnitLabels: jest.fn(),
            registerNumericInputs: jest.fn(),
            updateNumericFields: jest.fn(),
            dispatchPreferenceChange: jest.fn(),
            syncPreferencesFromDom: jest.fn(),
            setGlobalPreference: jest.fn(),
            applyPreferenceRadios: jest.fn(),
            applyGlobalRadio: jest.fn(),
            getPreferencePayload: jest.fn(() => ({})),
        };

        global.UnitizerClient = {
            ready: jest.fn(() => Promise.resolve(unitizerClient)),
        };

        await import("../project.js");
        project = window.Project.getInstance();
        await Promise.resolve();
    });

    afterEach(() => {
        jest.useRealTimers();
        delete window.Project;
        delete global.WCDom;
        delete global.WCHttp;
        delete global.UnitizerClient;
        delete global.controlBase;
        document.body.innerHTML = "";
        document.title = "";
    });

    test("setName posts trimmed value and updates the DOM", async () => {
        const result = await project.setName("  New Name  ");

        expect(result).toEqual({ Success: true });
        expect(postFormMock).toHaveBeenCalledWith("tasks/setname/", { name: "New Name" });

        const nameInput = document.querySelector('[data-project-field="name"]');
        expect(nameInput.value).toBe("New Name");
        expect(document.title).toBe("Base Title - New Name");
    });

    test("setScenarioFromInput debounces network calls", async () => {
        jest.useFakeTimers();
        const scenarioInput = document.querySelector('[data-project-field="scenario"]');
        scenarioInput.value = "Alpha Scenario";

        project.setScenarioFromInput({ debounceMs: 20 });

        expect(postFormMock).not.toHaveBeenCalled();

        jest.advanceTimersByTime(19);
        expect(postFormMock).not.toHaveBeenCalled();

        jest.advanceTimersByTime(1);
        await Promise.resolve();

        expect(postFormMock).toHaveBeenCalledWith("tasks/setscenario/", { scenario: "Alpha Scenario" });
    });

    test("setScenario restores previous value when request fails", async () => {
        const error = new Error("network");
        postFormMock.mockImplementationOnce(() => Promise.reject(error));

        project._notifyCommandBar = jest.fn();
        const originalScenario = project._currentScenario;

        const result = await project.setScenario("Failure Scenario");

        expect(result).toBeNull();
        expect(project._currentScenario).toBe(originalScenario);

        const scenarioInput = document.querySelector('[data-project-field="scenario"]');
        expect(scenarioInput.value).toBe(originalScenario);
        expect(project._notifyCommandBar).toHaveBeenCalledWith("Error saving scenario", { duration: null });
        expect(postFormMock).toHaveBeenCalledWith("tasks/setscenario/", { scenario: "Failure Scenario" });
    });
});

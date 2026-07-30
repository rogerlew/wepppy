/**
 * @jest-environment jsdom
 */

const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

function deferred() {
    var resolvePromise;
    var promise = new Promise((resolveDeferred) => {
        resolvePromise = resolveDeferred;
    });
    return { promise, resolve: resolvePromise };
}

function response(payload, ok = true) {
    return {
        ok,
        json: jest.fn().mockResolvedValue(payload)
    };
}

function flushPromises() {
    return new Promise((resolveFlush) => setTimeout(resolveFlush, 0));
}

describe("user preferences auto-save", () => {
    beforeEach(() => {
        jest.resetModules();
        document.body.innerHTML = `
          <form action="/preferences" data-user-preferences-form>
            <input name="csrf_token" value="csrf">
            <select name="unit_system">
              <option value="config">Auto</option>
              <option value="si">SI</option>
              <option value="english">English</option>
            </select>
            <select name="wbt_boundary_touch_behavior">
              <option value="config">Auto</option>
              <option value="warn">Warn</option>
              <option value="error">Error</option>
            </select>
            <p data-user-preferences-status>Changes save automatically.</p>
            <div data-user-preferences-error hidden>
              <span data-user-preferences-error-message></span>
              <button type="button" data-user-preferences-retry>Retry</button>
            </div>
          </form>
        `;
        window.fetch = jest.fn();
        var scriptPath = resolve(
            require.resolve("../../static/js/user_preferences.js")
        );
        window.eval(readFileSync(scriptPath, "utf-8"));
        window.WCUserPreferences.init(document);
    });

    afterEach(() => {
        delete window.WCUserPreferences;
        delete window.fetch;
    });

    test("saves the complete form and announces success on change", async () => {
        window.fetch.mockResolvedValue(
            response({ ok: true, message: "Preferences saved." })
        );
        var unitSelect = document.querySelector("[name='unit_system']");
        unitSelect.value = "si";
        unitSelect.dispatchEvent(new Event("change"));

        expect(document.querySelector("form").getAttribute("aria-busy"))
            .toBe("true");
        expect(
            document.querySelector("[data-user-preferences-status]").textContent
        ).toBe("Saving preferences…");

        await flushPromises();

        expect(window.fetch).toHaveBeenCalledTimes(1);
        var request = window.fetch.mock.calls[0];
        expect(request[0]).toBe("http://localhost/preferences");
        expect(request[1].method).toBe("POST");
        expect(request[1].headers.Accept).toBe("application/json");
        expect(request[1].body.get("unit_system")).toBe("si");
        expect(request[1].body.get("wbt_boundary_touch_behavior"))
            .toBe("config");
        expect(
            document.querySelector("[data-user-preferences-status]").textContent
        ).toBe("Preferences saved.");
        expect(document.querySelector("form").hasAttribute("aria-busy"))
            .toBe(false);
    });

    test("serializes a later complete selection behind the active save", async () => {
        var first = deferred();
        window.fetch
            .mockReturnValueOnce(first.promise)
            .mockResolvedValueOnce(
                response({ ok: true, message: "Preferences saved." })
            );
        var unitSelect = document.querySelector("[name='unit_system']");
        var boundarySelect = document.querySelector(
            "[name='wbt_boundary_touch_behavior']"
        );

        unitSelect.value = "si";
        unitSelect.dispatchEvent(new Event("change"));
        boundarySelect.value = "error";
        boundarySelect.dispatchEvent(new Event("change"));
        expect(window.fetch).toHaveBeenCalledTimes(1);

        first.resolve(response({ ok: true, message: "Preferences saved." }));
        await flushPromises();
        await flushPromises();

        expect(window.fetch).toHaveBeenCalledTimes(2);
        var latestBody = window.fetch.mock.calls[1][1].body;
        expect(latestBody.get("unit_system")).toBe("si");
        expect(latestBody.get("wbt_boundary_touch_behavior")).toBe("error");
    });

    test("shows an assertive error and retries the current selection", async () => {
        window.fetch
            .mockResolvedValueOnce(
                response(
                    { ok: false, message: "Could not save preferences." },
                    false
                )
            )
            .mockResolvedValueOnce(
                response({ ok: true, message: "Preferences saved." })
            );
        var unitSelect = document.querySelector("[name='unit_system']");
        unitSelect.value = "english";
        unitSelect.dispatchEvent(new Event("change"));
        await flushPromises();

        var error = document.querySelector("[data-user-preferences-error]");
        expect(error.hidden).toBe(false);
        expect(error.textContent).toContain("Could not save preferences.");

        document.querySelector("[data-user-preferences-retry]").click();
        await flushPromises();

        expect(window.fetch).toHaveBeenCalledTimes(2);
        expect(window.fetch.mock.calls[1][1].body.get("unit_system"))
            .toBe("english");
        expect(error.hidden).toBe(true);
    });

    test("enhanced form submission saves without navigating", async () => {
        window.fetch.mockResolvedValue(
            response({ ok: true, message: "Preferences saved." })
        );
        var form = document.querySelector("form");
        var submitEvent = new Event("submit", { cancelable: true });

        form.dispatchEvent(submitEvent);
        await flushPromises();

        expect(submitEvent.defaultPrevented).toBe(true);
        expect(window.fetch).toHaveBeenCalledTimes(1);
    });
});

/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const template = fs.readFileSync(
    path.resolve(__dirname, "../../templates/user/usermod.html"),
    "utf8"
);
const script = template.match(
    /<script type="module">([\s\S]*?)<\/script>/
)[1].replace(
    "{{ url_for(\"admin.task_usermod\") }}",
    "/tasks/usermod/"
);

async function flushPromises() {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("Root usermod inline contract", () => {
    beforeEach(() => {
        document.head.innerHTML = '<meta name="csrf-token" content="csrf-value">';
        document.body.innerHTML = `
          <p data-usermod-status aria-live="polite" hidden></p>
          <input type="checkbox" name="usermod_Dev_42">
          <input type="checkbox" name="usermod_Root_7" checked disabled>
        `;
        global.fetch = jest.fn();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("submits exact CSRF JSON and reports success without console output", async () => {
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({})
        });
        const consoleLog = jest.spyOn(console, "log").mockImplementation(() => {});
        const consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
        window.eval(script);

        const checkbox = document.querySelector('[name="usermod_Dev_42"]');
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        expect(checkbox.disabled).toBe(true);
        await flushPromises();

        expect(fetch).toHaveBeenCalledWith("/tasks/usermod/", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": "csrf-value"
            },
            body: JSON.stringify({
                user_id: 42,
                role: "Dev",
                role_state: true
            })
        });
        expect(checkbox.checked).toBe(true);
        expect(checkbox.disabled).toBe(false);
        const status = document.querySelector("[data-usermod-status]");
        expect(status.hidden).toBe(false);
        expect(status.textContent).toBe("Role updated.");
        expect(status.className).toContain("wc-alert--success");
        expect(consoleLog).not.toHaveBeenCalled();
        expect(consoleError).not.toHaveBeenCalled();
    });

    test.each([
        {
            response: {
                ok: false,
                json: () => Promise.resolve({
                    error: { message: "<b>Role denied.</b>" }
                })
            },
            expected: "<b>Role denied.</b>"
        },
        {
            response: {
                ok: false,
                json: () => Promise.reject(new Error("invalid JSON"))
            },
            expected: "Role update failed."
        }
    ])("reverts failed responses with text-only status", async ({
        response,
        expected
    }) => {
        fetch.mockResolvedValue(response);
        window.eval(script);

        const checkbox = document.querySelector('[name="usermod_Dev_42"]');
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        await flushPromises();

        expect(checkbox.checked).toBe(false);
        const status = document.querySelector("[data-usermod-status]");
        expect(status.textContent).toBe(expected);
        expect(status.innerHTML).not.toContain("<b>");
        expect(status.className).toContain("wc-alert--error");
    });

    test("reverts transport failure and preserves a disabled control", async () => {
        fetch.mockRejectedValue(new Error("network down"));
        window.eval(script);

        const checkbox = document.querySelector('[name="usermod_Dev_42"]');
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        const selfRoot = document.querySelector('[name="usermod_Root_7"]');
        selfRoot.dispatchEvent(new Event("change"));
        await flushPromises();

        expect(checkbox.checked).toBe(false);
        expect(
            document.querySelector("[data-usermod-status]").textContent
        ).toBe("network down");
        expect(selfRoot.disabled).toBe(true);
    });
});

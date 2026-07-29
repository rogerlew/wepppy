/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const capScript = fs.readFileSync(
    path.resolve(__dirname, "../../templates/security/_cap_form_script.html"),
    "utf8"
).match(/<script>([\s\S]*?)<\/script>/)[1];

const loginTemplate = fs.readFileSync(
    path.resolve(__dirname, "../../templates/security/login_user.html"),
    "utf8"
);
const loginScripts = [...loginTemplate.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
const passwordScript = loginScripts.at(-1)[1];

function dispatchReady() {
    document.dispatchEvent(new Event("DOMContentLoaded"));
}

describe("security authentication inline contracts", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
    });

    test("CAP solve permits its form while a missing token opens verification", () => {
        document.body.innerHTML = `
          <form class="wc-auth-form" id="solved-form">
            <div class="wc-auth-cap">
              <button data-cap-trigger type="button"></button>
              <span class="wc-cap-prompt"></span>
              <span data-cap-status></span>
              <cap-widget data-cap-section></cap-widget>
              <input data-cap-token value="">
            </div>
          </form>
          <form class="wc-auth-form" id="blocked-form">
            <div class="wc-auth-cap">
              <button data-cap-trigger type="button" id="blocked-trigger"></button>
              <cap-widget data-cap-section></cap-widget>
              <input data-cap-token value="">
            </div>
          </form>
        `;
        const trigger = document.querySelector("#blocked-trigger");
        trigger.click = jest.fn();
        window.eval(capScript);
        dispatchReady();

        const solvedForm = document.querySelector("#solved-form");
        solvedForm.querySelector("cap-widget").dispatchEvent(
            new CustomEvent("solve", { detail: { token: "<token-value>" } })
        );
        const solvedSubmit = new Event("submit", { cancelable: true });
        solvedForm.dispatchEvent(solvedSubmit);

        expect(solvedForm.querySelector("[data-cap-token]").value).toBe("<token-value>");
        expect(solvedForm.querySelector(".wc-cap-prompt").dataset.capVerified).toBe("true");
        expect(solvedForm.querySelector("[data-cap-status]").textContent).toBe(
            "Verification complete."
        );
        expect(solvedSubmit.defaultPrevented).toBe(false);

        const blockedSubmit = new Event("submit", { cancelable: true });
        document.querySelector("#blocked-form").dispatchEvent(blockedSubmit);

        expect(blockedSubmit.defaultPrevented).toBe(true);
        expect(trigger.click).toHaveBeenCalledTimes(1);
    });

    test("password toggle changes only its owned input and accessible label", () => {
        document.body.innerHTML = `
          <input id="password" type="password">
          <input id="other-password" type="password">
          <button class="wc-password-toggle" data-target="password">Show</button>
        `;
        window.eval(passwordScript);
        dispatchReady();

        const toggle = document.querySelector(".wc-password-toggle");
        toggle.click();
        expect(document.querySelector("#password").type).toBe("text");
        expect(document.querySelector("#other-password").type).toBe("password");
        expect(toggle.textContent).toBe("Hide");
        expect(toggle.getAttribute("aria-label")).toBe("Hide password");

        toggle.click();
        expect(document.querySelector("#password").type).toBe("password");
        expect(toggle.textContent).toBe("Show");
        expect(toggle.getAttribute("aria-label")).toBe("Show password");
    });
});

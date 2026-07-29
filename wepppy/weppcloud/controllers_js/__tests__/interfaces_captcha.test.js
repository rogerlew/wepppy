/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(
    path.resolve(__dirname, "../interfaces_captcha.js"),
    "utf8"
);

function installSection(section, formId) {
    document.body.insertAdjacentHTML(
        "beforeend",
        `
        <div class="wc-cap-prompt" data-cap-section="${section}">
          <button type="button" data-cap-trigger></button>
          <span data-cap-status></span>
        </div>
        <cap-widget data-cap-section="${section}"></cap-widget>
        <form id="${formId}" method="post" data-cap-section="${section}" data-cap-required="true">
          <input name="config" value="${formId}-config">
          <input name="cap_token" value="" data-cap-token>
          <button type="button" disabled aria-disabled="true" data-run-action="/rq-engine/create/">
            Create
          </button>
        </form>
        `
    );
    const form = document.querySelector(`#${formId}`);
    form.requestSubmit = jest.fn();
    return form;
}

describe("interfaces CAPTCHA controller", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
    });

    test("a solve enables only forms in its section and copies no token elsewhere", () => {
        const disturbed = installSection("disturbed", "disturbed-form");
        const rhem = installSection("rhem", "rhem-form");

        window.eval(source);
        document.querySelector('cap-widget[data-cap-section="disturbed"]').dispatchEvent(
            new CustomEvent("solve", { detail: { token: "<disturbed-token>" } })
        );

        expect(disturbed.querySelector("[data-cap-token]").value).toBe("<disturbed-token>");
        expect(disturbed.querySelector("[data-run-action]").disabled).toBe(false);
        expect(
            document.querySelector(
                '.wc-cap-prompt[data-cap-section="disturbed"] [data-cap-status]'
            ).textContent
        ).toBe("Verification complete.");
        expect(rhem.querySelector("[data-cap-token]").value).toBe("");
        expect(rhem.querySelector("[data-run-action]").disabled).toBe(true);
    });

    test("a missing token blocks submission and opens only the owned prompt", () => {
        const form = installSection("disturbed", "disturbed-form");
        const trigger = document.querySelector(
            '.wc-cap-prompt[data-cap-section="disturbed"] [data-cap-trigger]'
        );
        trigger.click = jest.fn();

        window.eval(source);
        const click = new Event("click", { bubbles: true, cancelable: true });
        form.querySelector("[data-run-action]").dispatchEvent(click);

        expect(click.defaultPrevented).toBe(true);
        expect(trigger.click).toHaveBeenCalledTimes(1);
        expect(form.requestSubmit).not.toHaveBeenCalled();
    });

    test("a solved form submits once after repeated controller execution", () => {
        const form = installSection("disturbed", "disturbed-form");
        const widget = document.querySelector('cap-widget[data-cap-section="disturbed"]');

        window.eval(source);
        window.eval(source);
        widget.dispatchEvent(new CustomEvent("solve", { detail: { token: "token-1" } }));
        form.querySelector("[data-run-action]").click();

        expect(form.method).toBe("post");
        expect(form.requestSubmit).toHaveBeenCalledTimes(1);
    });

    test("is inert for absent DOM and ignores empty solve tokens", () => {
        expect(() => window.eval(source)).not.toThrow();
        const form = installSection("disturbed", "disturbed-form");

        window.eval(source);
        document.querySelector('cap-widget[data-cap-section="disturbed"]').dispatchEvent(
            new CustomEvent("solve", { detail: { token: "" } })
        );

        expect(form.querySelector("[data-cap-token]").value).toBe("");
        expect(form.querySelector("[data-run-action]").disabled).toBe(true);
    });
});

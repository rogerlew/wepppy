/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const profileTemplate = fs.readFileSync(
    path.resolve(__dirname, "../../templates/user/profile.html"),
    "utf8"
);
const profileScript = [...profileTemplate.matchAll(
    /<script type="text\/javascript">([\s\S]*?)<\/script>/g
)][0][1];

function dispatchReady() {
    document.dispatchEvent(new Event("DOMContentLoaded"));
}

async function flushPromises() {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("user profile inline token contract", () => {
    beforeEach(() => {
        document.head.innerHTML = '<meta name="csrf-token" content="csrf-value">';
        document.body.innerHTML = `
          <section data-profile-token-root data-mint-endpoint="/profile/mint-token">
            <div hidden data-profile-token-message>
              <p data-profile-token-message-body></p>
            </div>
            <button type="button" data-profile-token-action="mint">Mint</button>
            <textarea readonly data-profile-token-field="token"></textarea>
            <button type="button" data-profile-token-action="copy-token" disabled>Copy</button>
            <p data-profile-token-expiry></p>
          </section>
        `;
        global.fetch = jest.fn();
        Object.defineProperty(navigator, "clipboard", {
            configurable: true,
            value: { writeText: jest.fn(() => Promise.resolve()) }
        });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("mints with CSRF, renders token only on success, copies, and handles rejection", async () => {
        fetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    Content: {
                        token: "secret-token",
                        expires_at: 1893456000
                    }
                })
            })
            .mockResolvedValueOnce({
                ok: false,
                json: () => Promise.resolve({
                    error: { message: "Role no longer permits token minting." }
                })
            });
        window.eval(profileScript);
        dispatchReady();

        const mint = document.querySelector('[data-profile-token-action="mint"]');
        const copy = document.querySelector('[data-profile-token-action="copy-token"]');
        const token = document.querySelector('[data-profile-token-field="token"]');
        const message = document.querySelector("[data-profile-token-message]");
        const messageBody = document.querySelector("[data-profile-token-message-body]");

        mint.click();
        expect(mint.disabled).toBe(true);
        expect(token.value).toBe("");
        await flushPromises();

        expect(fetch).toHaveBeenNthCalledWith(1, "/profile/mint-token", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                Accept: "application/json",
                "X-CSRFToken": "csrf-value"
            }
        });
        expect(token.value).toBe("secret-token");
        expect(copy.disabled).toBe(false);
        expect(document.querySelector("[data-profile-token-expiry]").textContent)
            .toMatch(/^Expires: /);
        expect(message.className).toContain("wc-alert--success");
        expect(messageBody.textContent).toBe("Token minted.");
        expect(mint.disabled).toBe(false);

        copy.click();
        await flushPromises();
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith("secret-token");
        expect(messageBody.textContent).toBe("Token copied.");

        navigator.clipboard.writeText.mockRejectedValueOnce(new Error("denied"));
        document.execCommand = jest.fn(() => true);
        copy.click();
        await flushPromises();
        expect(document.execCommand).toHaveBeenCalledWith("copy");
        expect(messageBody.textContent).toBe("Token copied.");

        navigator.clipboard.writeText.mockRejectedValueOnce(new Error("denied"));
        document.execCommand.mockReturnValueOnce(false);
        copy.click();
        await flushPromises();
        expect(message.className).toContain("wc-alert--warning");
        expect(messageBody.textContent).toBe("Copy failed. Copy manually.");

        token.value = "";
        copy.disabled = true;
        mint.click();
        await flushPromises();

        expect(fetch).toHaveBeenCalledTimes(2);
        expect(token.value).toBe("");
        expect(copy.disabled).toBe(true);
        expect(message.className).toContain("wc-alert--error");
        expect(messageBody.textContent).toBe("Role no longer permits token minting.");
        expect(mint.disabled).toBe(false);
    });
});

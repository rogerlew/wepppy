/**
 * @jest-environment jsdom
 */

/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const templatePath = path.resolve(__dirname, "../../templates/controls/poweruser_panel.htm");
const template = fs.readFileSync(templatePath, "utf8");
const scripts = Array.from(template.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g), (match) => match[1]);

function rendered(script) {
    return script
        .replaceAll("{{ site_prefix }}", "/weppcloud")
        .replaceAll("{{ VAPID_PUBLIC_KEY }}", "QQ");
}

describe("PowerUser panel inline clients", () => {
    test("absent notification toggle has no browser or network side effects", async () => {
        const requestPermission = jest.fn();
        const register = jest.fn();
        Object.defineProperty(window, "Notification", {
            configurable: true,
            value: { permission: "default", requestPermission }
        });
        Object.defineProperty(navigator, "serviceWorker", {
            configurable: true,
            value: { register, ready: Promise.resolve({}) }
        });
        window.PushManager = function PushManager() {};
        window.fetch = jest.fn();

        window.eval(rendered(scripts[0]));
        document.dispatchEvent(new Event("DOMContentLoaded"));
        await Promise.resolve();

        expect(requestPermission).not.toHaveBeenCalled();
        expect(register).not.toHaveBeenCalled();
        expect(window.fetch).not.toHaveBeenCalled();
    });

    test("token client keeps one owner and mints through CSRF-protected POST", async () => {
        document.head.innerHTML = '<meta name="csrf-token" content="csrf-123">';
        document.body.innerHTML = `
            <section data-run-token-root data-mint-endpoint="/runs/r/c/mint">
              <div data-run-token-message hidden><p data-run-token-message-body></p></div>
              <button data-run-token-action="mint">Mint</button>
              <textarea data-run-token-field="token"></textarea>
              <button data-run-token-action="copy-token" disabled>Copy</button>
              <p data-run-token-expiry></p>
            </section>
        `;
        window.fetch = jest.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ Content: { token: "secret-token", expires_at: 1800000000 } })
        });

        window.eval(scripts[1]);
        window.eval(scripts[1]);
        document.dispatchEvent(new Event("DOMContentLoaded"));
        document.querySelector('[data-run-token-action="mint"]').click();
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(window.fetch).toHaveBeenCalledTimes(1);
        expect(window.fetch).toHaveBeenCalledWith(
            "/runs/r/c/mint",
            expect.objectContaining({
                method: "POST",
                credentials: "same-origin",
                headers: expect.objectContaining({ "X-CSRFToken": "csrf-123" })
            })
        );
        expect(document.querySelector('[data-run-token-field="token"]').value).toBe("secret-token");
        expect(document.querySelector('[data-run-token-action="copy-token"]').disabled).toBe(false);
    });
});

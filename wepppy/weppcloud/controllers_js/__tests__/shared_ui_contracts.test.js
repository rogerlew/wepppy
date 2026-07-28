/**
 * @jest-environment jsdom
 */

describe("shared Pure UI producer contracts", () => {
    test("ModalManager preserves focus, traps keyboard navigation, and loads once", async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <button id="open-modal" type="button" data-modal-open="fixture-modal">Open</button>
            <div id="fixture-modal" class="wc-modal" data-modal hidden tabindex="-1">
                <div class="wc-modal__overlay" data-modal-dismiss></div>
                <div class="wc-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="fixture-title">
                    <h2 id="fixture-title">Fixture</h2>
                    <button id="first-modal-action" type="button">First</button>
                    <button id="last-modal-action" type="button" data-modal-dismiss>Close</button>
                </div>
            </div>
        `;

        await import("../modal.js");
        const manager = window.ModalManager;
        jest.resetModules();
        await import("../modal.js");

        expect(window.ModalManager).toBe(manager);

        const trigger = document.getElementById("open-modal");
        const modal = document.getElementById("fixture-modal");
        const first = document.getElementById("first-modal-action");
        const last = document.getElementById("last-modal-action");
        trigger.focus();
        trigger.click();

        expect(manager.activeModal).toBe(modal);
        expect(modal.hidden).toBe(false);
        expect(modal.getAttribute("data-modal-open")).toBe("true");
        expect(modal.classList.contains("is-visible")).toBe(true);
        expect(document.body.classList.contains("wc-modal-open")).toBe(true);
        expect(document.activeElement).toBe(first);

        last.focus();
        document.dispatchEvent(new KeyboardEvent("keydown", {
            key: "Tab",
            bubbles: true,
            cancelable: true,
        }));
        expect(document.activeElement).toBe(first);

        document.dispatchEvent(new KeyboardEvent("keydown", {
            key: "Escape",
            bubbles: true,
            cancelable: true,
        }));
        expect(manager.activeModal).toBeNull();
        expect(modal.hidden).toBe(true);
        expect(document.body.classList.contains("wc-modal-open")).toBe(false);
        expect(document.activeElement).toBe(trigger);

        manager.open("fixture-modal");
        expect(manager.activeModal).toBe(modal);
        manager.close(modal);
        expect(manager.activeModal).toBeNull();

        manager.toggle("fixture-modal");
        expect(manager.activeModal).toBe(modal);
        manager.toggle(modal);
        expect(manager.activeModal).toBeNull();

        trigger.click();
        document.querySelector(".wc-modal__overlay").click();
        expect(manager.activeModal).toBeNull();
        expect(modal.hidden).toBe(true);
        expect(document.activeElement).toBe(trigger);
    });

    test("WCDetailsMenu retains inside clicks, dismisses outside/Escape, and loads once", async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <details id="run-menu" class="wc-run-header__menu" open>
                <summary>Run menu</summary>
                <button id="inside-menu" type="button">Inside</button>
            </details>
            <details id="nav-menu" class="wc-nav__menu" open>
                <summary>Nav menu</summary>
            </details>
            <button id="outside-menu" type="button">Outside</button>
        `;

        const runMenu = document.getElementById("run-menu");
        const navMenu = document.getElementById("nav-menu");
        const runRemove = jest.spyOn(runMenu, "removeAttribute");
        const navRemove = jest.spyOn(navMenu, "removeAttribute");
        const addEventListener = jest.spyOn(document, "addEventListener");

        await import("../details_menu.js");
        const api = window.WCDetailsMenu;
        jest.resetModules();
        await import("../details_menu.js");

        expect(window.WCDetailsMenu).toBe(api);
        expect(addEventListener.mock.calls.filter(([type]) => type === "click")).toHaveLength(1);
        expect(addEventListener.mock.calls.filter(([type]) => type === "keyup")).toHaveLength(1);

        document.getElementById("inside-menu").click();
        expect(runMenu.open).toBe(true);
        expect(navMenu.open).toBe(false);

        navMenu.open = true;
        runRemove.mockClear();
        navRemove.mockClear();
        document.getElementById("outside-menu").click();
        expect(runMenu.open).toBe(false);
        expect(navMenu.open).toBe(false);
        expect(runRemove).toHaveBeenCalledTimes(1);
        expect(navRemove).toHaveBeenCalledTimes(1);

        runMenu.open = true;
        document.dispatchEvent(new KeyboardEvent("keyup", { key: "Escape", bubbles: true }));
        expect(runMenu.open).toBe(false);

        navMenu.open = true;
        api.closeAll();
        expect(navMenu.open).toBe(false);
        addEventListener.mockRestore();
    });

    test("theme producer validates storage, syncs selects, emits once, and loads once", async () => {
        jest.resetModules();
        const readyState = Object.getOwnPropertyDescriptor(document, "readyState");
        Object.defineProperty(document, "readyState", { configurable: true, value: "complete" });
        window.localStorage.setItem("wc-theme", "removed-theme");
        document.documentElement.setAttribute("data-theme", "ayu-mirage");
        document.body.innerHTML = `
            <select id="theme-one" data-theme-select>
                <option value="default">Default</option>
                <option value="ayu-mirage">Ayu Mirage</option>
            </select>
            <select id="theme-two" data-theme-select>
                <option value="default">Default</option>
                <option value="ayu-mirage">Ayu Mirage</option>
            </select>
        `;
        const changes = [];
        document.addEventListener("wc-theme:change", (event) => changes.push(event.detail.theme));

        await import("../theme.js");
        jest.resetModules();
        await import("../../static/js/theme.js");

        expect(window.localStorage.getItem("wc-theme")).toBeNull();
        expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
        expect(document.getElementById("theme-one").value).toBe("default");
        expect(document.getElementById("theme-two").value).toBe("default");
        expect(changes).toEqual(["default"]);

        const firstSelect = document.getElementById("theme-one");
        firstSelect.value = "ayu-mirage";
        firstSelect.dispatchEvent(new Event("change", { bubbles: true }));
        expect(document.documentElement.getAttribute("data-theme")).toBe("ayu-mirage");
        expect(window.localStorage.getItem("wc-theme")).toBe("ayu-mirage");
        expect(document.getElementById("theme-two").value).toBe("ayu-mirage");
        expect(changes).toEqual(["default", "ayu-mirage"]);

        firstSelect.value = "default";
        firstSelect.dispatchEvent(new Event("change", { bubbles: true }));
        expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
        expect(window.localStorage.getItem("wc-theme")).toBeNull();

        const setItem = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
            throw new Error("storage unavailable");
        });
        firstSelect.value = "ayu-mirage";
        expect(() => {
            firstSelect.dispatchEvent(new Event("change", { bubbles: true }));
        }).not.toThrow();
        expect(document.documentElement.getAttribute("data-theme")).toBe("ayu-mirage");
        expect(changes.at(-1)).toBe("ayu-mirage");
        setItem.mockRestore();

        if (readyState) {
            Object.defineProperty(document, "readyState", readyState);
        }
    });

    test("WCConsoleConfig merges explicit config, normalizes booleans, and loads once", async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <section id="console-root"
                     data-runid="fallback-run"
                     data-enabled="false"
                     data-container-only="ready">
                <div data-console-config
                     data-runid="configured-run"
                     data-enabled="TRUE"
                     data-config-only="present"></div>
            </section>
        `;

        await import("../../static/js/console_utils.js");
        const api = window.WCConsoleConfig;
        jest.resetModules();
        await import("../../static/js/console_utils.js");

        expect(window.WCConsoleConfig).toBe(api);
        expect(api.readConfig(
            document.getElementById("console-root"),
            "[data-console-config]"
        )).toEqual({
            consoleConfig: "",
            runid: "configured-run",
            enabled: true,
            configOnly: "present",
            containerOnly: "ready",
        });
        expect(api.readConfig(null, "[data-console-config]")).toEqual({});
    });
});

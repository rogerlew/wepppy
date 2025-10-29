/* ----------------------------------------------------------------------------
 * Theme Switcher
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var STORAGE_KEY = "wc-theme";
    var SELECTOR = "[data-theme-select]";
    var root = global.document ? global.document.documentElement : null;

    function emitThemeChange(theme) {
        if (!global.document) {
            return;
        }
        var detail = { theme: theme && theme !== "" ? theme : "default" };
        global.document.dispatchEvent(new CustomEvent("wc-theme:change", { detail: detail }));
    }

    function getStoredTheme() {
        try {
            return global.localStorage.getItem(STORAGE_KEY);
        } catch (err) {
            return null;
        }
    }

    function storeTheme(theme) {
        try {
            if (!theme || theme === "default") {
                global.localStorage.removeItem(STORAGE_KEY);
            } else {
                global.localStorage.setItem(STORAGE_KEY, theme);
            }
        } catch (err) {
            // ignore storage errors (private mode, etc.)
        }
    }

    function applyTheme(theme) {
        if (!root) {
            return;
        }
        if (!theme || theme === "default") {
            root.removeAttribute("data-theme");
        } else {
            root.setAttribute("data-theme", theme);
        }
    }

    function syncSelects(theme) {
        var value = theme && theme !== "" ? theme : "default";
        var selects = global.document.querySelectorAll(SELECTOR);
        selects.forEach(function (select) {
            if (select.value !== value) {
                select.value = value;
            }
        });
    }

    function handleChange(event) {
        var select = event.target;
        if (!select || select.matches(SELECTOR) === false) {
            return;
        }
        var theme = select.value;
        applyTheme(theme);
        storeTheme(theme);
        syncSelects(theme);
        emitThemeChange(theme);
    }

    function init() {
        if (!root || !global.document) {
            return;
        }
        var selects = global.document.querySelectorAll(SELECTOR);
        if (!selects.length) {
            return;
        }

        var stored = getStoredTheme();
        var initial = stored || root.getAttribute("data-theme") || "default";
        applyTheme(initial);
        syncSelects(initial);
        emitThemeChange(initial);

        global.document.addEventListener("change", handleChange, { passive: true });
    }

    if (typeof global.document !== "undefined") {
        if (global.document.readyState === "loading") {
            global.document.addEventListener("DOMContentLoaded", init, { once: true });
        } else {
            init();
        }
    }
}(typeof globalThis !== "undefined" ? globalThis : window));

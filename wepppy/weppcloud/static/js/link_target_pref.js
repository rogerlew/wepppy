(function (global) {
    "use strict";

    var doc = global.document;
    if (!doc) {
        return;
    }

    var COOKIE_NAME = "wc_open_links_new_tab";
    var DEFAULT_ENABLED = true;
    var COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

    function readCookie(name) {
        if (!doc.cookie) {
            return null;
        }
        var escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        var pattern = new RegExp("(?:^|; )" + escapedName + "=([^;]*)");
        var match = doc.cookie.match(pattern);
        return match ? decodeURIComponent(match[1]) : null;
    }

    function writeCookie(name, value) {
        var parts = [name + "=" + encodeURIComponent(value), "path=/", "max-age=" + COOKIE_MAX_AGE, "samesite=lax"];
        if (global.location && global.location.protocol === "https:") {
            parts.push("secure");
        }
        doc.cookie = parts.join("; ");
    }

    function parsePreference(rawValue) {
        if (rawValue === null || rawValue === undefined || rawValue === "") {
            return DEFAULT_ENABLED;
        }
        var normalized = String(rawValue).toLowerCase();
        if (["1", "true", "yes", "on"].indexOf(normalized) !== -1) {
            return true;
        }
        if (["0", "false", "no", "off"].indexOf(normalized) !== -1) {
            return false;
        }
        return DEFAULT_ENABLED;
    }

    function ensureNoopener(link) {
        var rel = link.getAttribute("rel") || "";
        if (/\bnoopener\b/i.test(rel)) {
            return;
        }
        var trimmed = rel.trim();
        link.setAttribute("rel", trimmed ? (trimmed + " noopener") : "noopener");
    }

    function applyPreference(enabled) {
        var links = doc.querySelectorAll("[data-open-tab-pref]");
        links.forEach(function (link) {
            if (!(link instanceof HTMLAnchorElement)) {
                return;
            }
            if (enabled) {
                link.setAttribute("target", "_blank");
                ensureNoopener(link);
            } else {
                link.removeAttribute("target");
            }
        });
    }

    function syncToggles(enabled) {
        var toggles = doc.querySelectorAll("[data-open-tab-pref-toggle]");
        toggles.forEach(function (toggle) {
            if (toggle.type === "checkbox") {
                toggle.checked = enabled;
            }
        });
    }

    function updatePreference(enabled) {
        writeCookie(COOKIE_NAME, enabled ? "1" : "0");
        applyPreference(enabled);
        syncToggles(enabled);
    }

    function init() {
        var raw = readCookie(COOKIE_NAME);
        var enabled = parsePreference(raw);
        if (raw === null) {
            writeCookie(COOKIE_NAME, enabled ? "1" : "0");
        }
        applyPreference(enabled);
        syncToggles(enabled);
        var toggles = doc.querySelectorAll("[data-open-tab-pref-toggle]");
        toggles.forEach(function (toggle) {
            toggle.addEventListener("change", function () {
                updatePreference(toggle.checked);
            });
        });
    }

    if (doc.readyState === "loading") {
        doc.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})(window);

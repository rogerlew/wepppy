function coordRound(v) {
    var w = Math.floor(v);
    var d = v - w;
    d = Math.round(d * 10000) / 10000;
    return w + d;
}

// utility function to be used by ControlBase subclasses to build URLs for pup runs.
// not to be used elsewhere.
function url_for_run(url, options) {
    var sitePrefix = "";
    if (typeof window.site_prefix === "string" && window.site_prefix) {
        sitePrefix = window.site_prefix.replace(/\/+$/, "");
    }

    function normalizePrefix(prefix) {
        if (!prefix) {
            return "";
        }
        if (prefix === "/") {
            return "";
        }
        if (prefix.charAt(0) !== "/") {
            prefix = "/" + prefix;
        }
        return prefix.replace(/\/+$/, "");
    }

    var outputPrefix = sitePrefix;
    if (options !== undefined) {
        if (typeof options === "string") {
            outputPrefix = normalizePrefix(options);
        } else if (options && typeof options === "object" && Object.prototype.hasOwnProperty.call(options, "prefix")) {
            outputPrefix = normalizePrefix(options.prefix);
        }
    }

    function resolveRunContextFromLocation() {
        var path = window.location && window.location.pathname ? window.location.pathname : "";
        var prefix = sitePrefix;
        if (prefix && prefix !== "/" && prefix.charAt(0) !== "/") {
            prefix = "/" + prefix;
        }
        if (prefix && path.indexOf(prefix) === 0) {
            path = path.slice(prefix.length);
        }

        var parts = path.split("/").filter(function (segment) {
            return segment.length > 0;
        });
        var runsIndex = parts.indexOf("runs");
        if (runsIndex === -1 || parts.length <= runsIndex + 2) {
            return null;
        }
        return {
            runId: decodeURIComponent(parts[runsIndex + 1]),
            config: decodeURIComponent(parts[runsIndex + 2])
        };
    }

    var normalizedUrl = url || "";
    if (normalizedUrl.charAt(0) === "/") {
        normalizedUrl = normalizedUrl.substring(1);
    }

    var resolved = resolveRunContextFromLocation();
    var activeRunId = resolved && resolved.runId ? resolved.runId : (typeof window.runId === "string" ? window.runId : "");
    var activeConfig = resolved && resolved.config ? resolved.config : (typeof window.config === "string" ? window.config : "");

    var runScopedPath = normalizedUrl;
    if (activeRunId && activeConfig) {
        runScopedPath = "runs/" + encodeURIComponent(activeRunId) + "/" + encodeURIComponent(activeConfig) + "/";
        if (normalizedUrl) {
            runScopedPath += normalizedUrl;
        }
    }

    if (runScopedPath.charAt(0) !== "/") {
        runScopedPath = "/" + runScopedPath;
    }

    return outputPrefix + runScopedPath;
}

function pass() {
    return undefined;

} const fromHex = (rgbHex, alpha = 0.5) => {
    // Validate hex input
    if (!rgbHex || typeof rgbHex !== 'string') {
        console.warn(`Invalid hex value: ${rgbHex}. Returning default color.`);
        return { r: 0, g: 0, b: 0, a: 1 };
    }

    // Ensure hex is a valid hex string
    let hex = rgbHex.replace(/^#/, '');
    if (!/^[0-9A-Fa-f]{6}$/.test(hex)) {
        console.warn(`Invalid hex format: ${hex}. Returning default color.`);
        return { r: 0, g: 0, b: 0, a: 1 };
    }

    // Validate alpha
    if (typeof alpha !== 'number' || alpha < 0 || alpha > 1) {
        console.warn(`Invalid alpha value: ${alpha}. Using default alpha: 1.`);
        alpha = 1;
    }

    // Convert hex to RGB and normalize to 0-1 range
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;

    return { r, g, b, a: alpha };
};


function linearToLog(value, minLog, maxLog, maxLinear) {
    if (isNaN(value)) return minLog;
    value = Math.max(0, Math.min(value, maxLinear));

    // Logarithmic mapping: minLog * (maxLog / minLog) ^ (value / maxLinear)
    return minLog * Math.pow(maxLog / minLog, value / maxLinear);
}


function lockButton(buttonId, lockImageId) {
    const button = document.getElementById(buttonId);
    const lockImage = document.getElementById(lockImageId);

    // Disable the button and show the lock image
    button.disabled = true;
    lockImage.style.display = 'inline';
}


function unlockButton(buttonId, lockImageId) {
    const button = document.getElementById(buttonId);
    const lockImage = document.getElementById(lockImageId);

    // Re-enable the button and hide the lock image
    button.disabled = false;
    lockImage.style.display = 'none';
}

// Normalize HTML/text writes across DOM elements, jQuery-style wrappers, and legacy adapters
function applyLabelHtml(label, html) {
    if (!label) {
        return;
    }
    var textFallback = function () {
        try {
            if (label && "textContent" in label) {
                label.textContent = String(html);
            }
        } catch (noop) {
            // ignore
        }
    };

    try {
        var maybeHtml = label && label.html;
        if (typeof maybeHtml === "function") {
            maybeHtml.call(label, html);
            return;
        }
        if ("innerHTML" in label) {
            label.innerHTML = html;
            return;
        }
        if ("textContent" in label) {
            label.textContent = html;
            return;
        }
        textFallback();
    } catch (err) {
        console.warn("applyLabelHtml: failed to write label content, falling back to textContent", err);
        textFallback();
    }
}
if (typeof globalThis !== "undefined") {
    globalThis.applyLabelHtml = applyLabelHtml;
}


const updateRangeMaxLabel_mm = function (r, labelMax) {
    UnitizerClient.ready()
        .then(function (client) {
            var html = client.renderValue(r, 'mm', { includeUnits: true });
            applyLabelHtml(labelMax, html);
        })
        .catch(function (error) {
            console.error("Failed to update unitizer label (mm)", error);
            applyLabelHtml(labelMax, r + ' mm');
        });
};


const updateRangeMaxLabel_kgha = function (r, labelMax) {
    UnitizerClient.ready()
        .then(function (client) {
            var html = client.renderValue(r, 'kg/ha', { includeUnits: true });
            applyLabelHtml(labelMax, html);
        })
        .catch(function (error) {
            console.error("Failed to update unitizer label (kg/ha)", error);
            applyLabelHtml(labelMax, r + ' kg/ha');
        });
};


const updateRangeMaxLabel_tonneha = function (r, labelMax) {
    UnitizerClient.ready()
        .then(function (client) {
            var html = client.renderValue(r, 'tonne/ha', { includeUnits: true });
            applyLabelHtml(labelMax, html);
        })
        .catch(function (error) {
            console.error("Failed to update unitizer label (tonne/ha)", error);
            applyLabelHtml(labelMax, r + ' tonne/ha');
        });
};


function parseBboxText(text) {
    // Keep digits, signs, decimal, scientific notation, commas and spaces
    const toks = text
        .replace(/[^\d\s,.\-+eE]/g, '')
        .split(/[\s,]+/)
        .filter(Boolean)
        .map(Number);

    if (toks.length !== 4 || toks.some(Number.isNaN)) {
        throw new Error("Extent must have exactly 4 numeric values: minLon, minLat, maxLon, maxLat.");
    }

    let [x1, y1, x2, y2] = toks;
    // Normalize (user might give two corners in any order)
    const minLon = Math.min(x1, x2);
    const minLat = Math.min(y1, y2);
    const maxLon = Math.max(x1, x2);
    const maxLat = Math.max(y1, y2);

    // Basic sanity check
    if (minLon >= maxLon || minLat >= maxLat) {
        throw new Error("Invalid extent: ensure minLon < maxLon and minLat < maxLat.");
    }
    return [minLon, minLat, maxLon, maxLat];
}

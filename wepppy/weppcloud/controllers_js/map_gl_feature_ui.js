/* ----------------------------------------------------------------------------
 * Map GL Feature Tooltip/Modal Helpers
 * ----------------------------------------------------------------------------
 */
var WCMapGlFeatureUi = (function () {
    "use strict";

    function createHoverTooltip() {
        if (typeof document === "undefined") {
            return null;
        }
        var tooltip = document.createElement("div");
        tooltip.className = "wc-map-hover-info";
        tooltip.style.position = "fixed";
        tooltip.style.pointerEvents = "none";
        tooltip.style.zIndex = "1000";
        tooltip.style.padding = "6px 8px";
        tooltip.style.borderRadius = "6px";
        tooltip.style.background = "rgba(10, 10, 10, 0.85)";
        tooltip.style.color = "#f5f5f5";
        tooltip.style.fontSize = "14px";
        tooltip.style.lineHeight = "1.4";
        tooltip.style.maxWidth = "280px";
        tooltip.style.boxShadow = "0 8px 18px rgba(0, 0, 0, 0.25)";
        tooltip.style.display = "none";
        tooltip.style.transform = "translate(-50%, -120%)";
        document.body.appendChild(tooltip);

        return {
            show: function (text, x, y) {
                tooltip.textContent = text;
                tooltip.style.left = x + "px";
                tooltip.style.top = y + "px";
                tooltip.style.display = "block";
            },
            hide: function () {
                tooltip.style.display = "none";
            }
        };
    }

    function sanitizeInfoHtml(html) {
        if (!html || typeof document === "undefined") {
            return "";
        }
        var container = document.createElement("div");
        container.innerHTML = String(html);

        var blocked = container.querySelectorAll("script, style, iframe, object, embed, link");
        Array.prototype.forEach.call(blocked, function (node) {
            node.remove();
        });

        var nodes = container.querySelectorAll("*");
        Array.prototype.forEach.call(nodes, function (node) {
            if (!node.attributes) {
                return;
            }
            Array.prototype.slice.call(node.attributes).forEach(function (attr) {
                var name = attr.name.toLowerCase();
                var value = String(attr.value || "").toLowerCase();
                if (name.indexOf("on") === 0) {
                    node.removeAttribute(attr.name);
                    return;
                }
                if ((name === "href" || name === "src") && value.indexOf("javascript:") === 0) {
                    node.removeAttribute(attr.name);
                }
            });
        });

        return container.innerHTML;
    }

    function extractFeatureDescription(feature) {
        if (!feature || !feature.properties) {
            return null;
        }
        if (feature.properties.Description) {
            return String(feature.properties.Description);
        }
        if (feature.properties.description) {
            return String(feature.properties.description);
        }
        return null;
    }

    function extractFeatureName(feature) {
        if (!feature || !feature.properties) {
            return null;
        }
        var props = feature.properties;
        var candidates = [
            "Name",
            "name",
            "StationName",
            "station_name",
            "SiteName",
            "site_name",
            "LocationName",
            "location_name",
            "StationID",
            "station_id",
            "ID",
            "id"
        ];
        for (var i = 0; i < candidates.length; i += 1) {
            var value = props[candidates[i]];
            if (value !== undefined && value !== null) {
                var text = String(value).trim();
                if (text) {
                    return text;
                }
            }
        }
        var description = extractFeatureDescription(feature);
        if (description) {
            var container = document.createElement("div");
            container.innerHTML = description;
            var content = container.textContent || "";
            var firstLine = content.split(/\n+/)[0] || "";
            var trimmed = firstLine.trim();
            if (trimmed) {
                return trimmed;
            }
        }
        return null;
    }

    function createFeatureModal() {
        if (typeof document === "undefined") {
            return null;
        }
        var modal = document.createElement("div");
        modal.className = "wc-modal";
        modal.id = "wc-map-feature-modal";
        modal.setAttribute("data-modal", "");
        modal.setAttribute("hidden", "hidden");

        var overlay = document.createElement("div");
        overlay.className = "wc-modal__overlay";
        overlay.setAttribute("data-modal-dismiss", "");

        var dialog = document.createElement("div");
        dialog.className = "wc-modal__dialog";
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");

        var header = document.createElement("div");
        header.className = "wc-modal__header";

        var title = document.createElement("h2");
        title.className = "wc-modal__title";
        title.textContent = "";

        var close = document.createElement("button");
        close.type = "button";
        close.className = "wc-modal__close";
        close.setAttribute("aria-label", "Close");
        close.setAttribute("data-modal-dismiss", "");
        close.textContent = "×";

        var body = document.createElement("div");
        body.className = "wc-modal__body";

        header.appendChild(title);
        header.appendChild(close);
        dialog.appendChild(header);
        dialog.appendChild(body);
        modal.appendChild(overlay);
        modal.appendChild(dialog);
        document.body.appendChild(modal);

        function openModal() {
            if (window.ModalManager && typeof window.ModalManager.open === "function") {
                window.ModalManager.open(modal);
                return;
            }
            modal.removeAttribute("hidden");
            modal.setAttribute("data-modal-open", "true");
            modal.classList.add("is-visible");
            document.body.classList.add("wc-modal-open");
        }

        function closeModal() {
            if (window.ModalManager && typeof window.ModalManager.close === "function") {
                window.ModalManager.close(modal);
                return;
            }
            modal.classList.remove("is-visible");
            modal.removeAttribute("data-modal-open");
            modal.setAttribute("hidden", "hidden");
            document.body.classList.remove("wc-modal-open");
        }

        overlay.addEventListener("click", function () {
            closeModal();
        });
        close.addEventListener("click", function () {
            closeModal();
        });

        return {
            show: function (name, html) {
                title.textContent = name || "Location";
                if (html) {
                    body.innerHTML = sanitizeInfoHtml(html);
                } else {
                    body.textContent = "No additional details available.";
                }
                openModal();
            },
            hide: function () {
                closeModal();
            }
        };
    }

    function create(options) {
        var mapCanvasElement = options && options.mapCanvasElement ? options.mapCanvasElement : null;
        var hoverTooltip = createHoverTooltip();
        var featureModal = createFeatureModal();

        function updateHoverTooltip(info) {
            if (!hoverTooltip) {
                return;
            }
            if (!info || !info.object) {
                hoverTooltip.hide();
                return;
            }
            var name = extractFeatureName(info.object);
            if (!name) {
                hoverTooltip.hide();
                return;
            }
            var rect = mapCanvasElement ? mapCanvasElement.getBoundingClientRect() : { left: 0, top: 0 };
            var x = rect.left + (info.x || 0);
            var y = rect.top + (info.y || 0);
            hoverTooltip.show(name, x, y);
        }

        function openFeatureModal(feature) {
            if (!featureModal) {
                return;
            }
            var name = extractFeatureName(feature) || "Location";
            var description = extractFeatureDescription(feature);
            featureModal.show(name, description);
        }

        return {
            updateHoverTooltip: updateHoverTooltip,
            openFeatureModal: openFeatureModal
        };
    }

    return {
        create: create
    };
}());

window.WCMapGlFeatureUi = WCMapGlFeatureUi;

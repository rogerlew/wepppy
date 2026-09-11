/* SBS errors belong in Details; Summary contains accepted model results. */
var WCSbsError = (function () {
    "use strict";
    var allowed = new Set([
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span", "br",
        "pre", "code", "strong", "em", "b", "i", "ul", "ol", "li",
        "blockquote", "table", "thead", "tbody", "tr", "th", "td"
    ]);

    function renderHtml(target, html) {
        // Template content stays inert during parsing, including resource elements.
        var template = document.createElement("template");
        template.innerHTML = html;
        var fragment = document.createDocumentFragment();
        var pending = [ [template.content, fragment] ];
        while (pending.length) {
            var pair = pending.pop();
            Array.prototype.forEach.call(pair[0].childNodes, function (source) {
                if (source.nodeType === 3) {
                    pair[1].appendChild(document.createTextNode(source.textContent));
                } else if (source.nodeType === 1 &&
                           source.namespaceURI === "http://www.w3.org/1999/xhtml" &&
                           allowed.has(source.localName)) {
                    var element = document.createElement(source.localName);
                    pair[1].appendChild(element);
                    pending.push([source, element]);
                }
                // Discard every other subtree; never clone nodes or copy attributes.
            });
        }
        target.replaceChildren(fragment);
    }

    var errors = new WeakMap();

    function render(controller, payload, error) {
        var response = error && error.response;
        var contentType = response && response.headers && response.headers.get
            ? response.headers.get("content-type") || "" : "";
        var html = error && typeof error.body === "string" &&
            contentType.split(";")[0].trim().toLowerCase() === "text/html";
        var form = controller.form;
        var target = form && form.querySelector("#stacktrace");
        if (html && target) {
            renderHtml(target, error.body);
            target.hidden = false;
            target.style.removeProperty("display");
            var panel = target.closest("[data-stacktrace-panel]");
            if (panel) {
                panel.hidden = false;
                panel.style.removeProperty("display");
                if ("open" in panel) { panel.open = true; }
            }
        } else {
            // Omit Summary targets from the shared escaped-text renderer.
            controller.pushResponseStacktrace({ stacktrace: controller.stacktrace }, payload);
        }
    }

    function show(controller, payload, error, source) {
        var key = controller.form;
        if (key) {
            var current = errors.get(key) || new Map();
            current.set(source || "upload", { payload: payload, error: error });
            errors.set(key, current);
        }
        render(controller, payload, error);
    }

    function clear(controller, source) {
        var current = errors.get(controller.form);
        if (current && source) { current.delete(source); }
        if (current && source && current.size) {
            var remaining = Array.from(current.values()).pop();
            render(controller, remaining.payload, remaining.error);
            return false;
        }
        errors.delete(controller.form);
        if (controller.stacktrace) { controller.stacktrace.text(""); }
        var target = controller.form && controller.form.querySelector("#stacktrace");
        var panel = target && target.closest("[data-stacktrace-panel]");
        if (panel) { panel.hidden = true; }
        return true;
    }

    return { show: show, clear: clear };
}());
if (typeof window !== "undefined") { window.WCSbsError = WCSbsError; }

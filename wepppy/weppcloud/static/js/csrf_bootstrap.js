(function (global) {
    "use strict";

    var doc = global.document;
    if (!doc) {
        return;
    }

    function getCsrfToken() {
        var meta = doc.querySelector('meta[name="csrf-token"]');
        if (!meta) {
            return "";
        }
        return String(meta.getAttribute("content") || "").trim();
    }

    function isSafeMethod(method) {
        var token = String(method || "GET").toUpperCase();
        return token === "GET" || token === "HEAD" || token === "OPTIONS" || token === "TRACE";
    }

    function toAbsoluteUrl(rawUrl) {
        try {
            return new URL(String(rawUrl || ""), global.location ? global.location.href : undefined);
        } catch (_error) {
            return null;
        }
    }

    function isSameOrigin(rawUrl) {
        var url = toAbsoluteUrl(rawUrl);
        if (!url || !global.location) {
            return false;
        }
        return url.origin === global.location.origin;
    }

    var csrfToken = getCsrfToken();
    if (!csrfToken) {
        return;
    }
    global.__csrfToken = csrfToken;

    function ensureFormCsrfTokens() {
        var forms = doc.querySelectorAll("form");
        for (var i = 0; i < forms.length; i += 1) {
            var form = forms[i];
            var method = (form.getAttribute("method") || "GET").toUpperCase();
            if (isSafeMethod(method)) {
                continue;
            }

            var action = form.getAttribute("action") || (global.location ? global.location.href : "");
            if (!isSameOrigin(action)) {
                continue;
            }

            var actionUrl = toAbsoluteUrl(action);
            if (actionUrl && (actionUrl.pathname === "/rq-engine" || actionUrl.pathname.indexOf("/rq-engine/") === 0)) {
                continue;
            }

            if (form.querySelector('input[name="csrf_token"]')) {
                continue;
            }

            var hidden = doc.createElement("input");
            hidden.type = "hidden";
            hidden.name = "csrf_token";
            hidden.value = csrfToken;
            form.appendChild(hidden);
        }
    }

    if (doc.readyState === "loading") {
        doc.addEventListener("DOMContentLoaded", ensureFormCsrfTokens, { once: true });
    } else {
        ensureFormCsrfTokens();
    }

    if (typeof global.fetch !== "function") {
        return;
    }

    var nativeFetch = global.fetch.bind(global);

    function hasCsrfHeader(headers) {
        return headers.has("X-CSRFToken") || headers.has("X-CSRF-Token");
    }

    global.fetch = function (input, init) {
        var method = "GET";
        var requestUrl = "";
        if (input && typeof input === "object" && "url" in input) {
            requestUrl = input.url || "";
            method = input.method || method;
        } else {
            requestUrl = String(input || "");
        }
        if (init && init.method) {
            method = init.method;
        }

        if (isSafeMethod(method) || !isSameOrigin(requestUrl)) {
            return nativeFetch(input, init);
        }

        if (typeof Request !== "undefined" && input instanceof Request) {
            var requestInit = init ? Object.assign({}, init) : {};
            var requestHeaders = new Headers(input.headers || {});
            if (requestInit.headers) {
                var overrideHeaders = new Headers(requestInit.headers);
                overrideHeaders.forEach(function (value, key) {
                    requestHeaders.set(key, value);
                });
            }
            if (!hasCsrfHeader(requestHeaders)) {
                requestHeaders.set("X-CSRFToken", csrfToken);
            }
            requestInit.headers = requestHeaders;
            return nativeFetch(new Request(input, requestInit));
        }

        var nextInit = init ? Object.assign({}, init) : {};
        var headers = new Headers(nextInit.headers || {});
        if (!hasCsrfHeader(headers)) {
            headers.set("X-CSRFToken", csrfToken);
        }
        nextInit.headers = headers;
        return nativeFetch(input, nextInit);
    };
})(window);

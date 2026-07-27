(function (root) {
  "use strict";

  function setMessage(rootNode, kind, messageText) {
    var message = rootNode.querySelector("[data-browser-reset-message]");
    var messageBody = rootNode.querySelector("[data-browser-reset-message-body]");
    if (!message || !messageBody) {
      return;
    }
    message.hidden = false;
    message.className = "wc-alert wc-alert--" + kind;
    messageBody.textContent = messageText;
  }

  function setBusy(rootNode, isBusy) {
    var action = rootNode.querySelector('[data-browser-reset-action="reset"]');
    if (!action) {
      return;
    }
    action.disabled = isBusy;
    action.setAttribute("aria-busy", isBusy ? "true" : "false");
  }

  function clearWeppStorage(storage) {
    if (!storage || typeof storage.length !== "number") {
      return;
    }

    var keys = [];
    for (var index = 0; index < storage.length; index += 1) {
      var key = storage.key(index);
      if (key) {
        keys.push(String(key));
      }
    }

    keys.forEach(function (key) {
      var normalized = key.toLowerCase();
      if (normalized.indexOf("wc-") === 0 || normalized.indexOf("wepp") === 0) {
        try {
          storage.removeItem(key);
        } catch (_error) {
          // Continue clearing other WEPPcloud keys when one storage entry is inaccessible.
        }
      }
    });
  }

  function clearBrowserStorage() {
    try {
      clearWeppStorage(root.localStorage);
    } catch (_error) {
      // Storage access itself can fail when browser privacy controls block it.
    }
    try {
      clearWeppStorage(root.sessionStorage);
    } catch (_error) {
      // Storage access itself can fail when browser privacy controls block it.
    }
  }

  function parseError(payload, fallback) {
    if (payload && payload.error && payload.error.message) {
      return payload.error.message;
    }
    return fallback;
  }

  function csrfHeaders(baseHeaders) {
    var headers = Object.assign({}, baseHeaders || {});
    var meta = document.querySelector('meta[name="csrf-token"]');
    var token = meta ? String(meta.getAttribute("content") || "").trim() : "";
    if (token && !headers["X-CSRFToken"] && !headers["X-CSRF-Token"]) {
      headers["X-CSRFToken"] = token;
    }
    return headers;
  }

  function runReset(rootNode) {
    var endpoint = rootNode.getAttribute("data-reset-endpoint");
    var loginUrl = rootNode.getAttribute("data-login-url") || "/login";
    if (!endpoint) {
      setMessage(rootNode, "error", "Browser reset endpoint is not configured.");
      return Promise.resolve(false);
    }

    setBusy(rootNode, true);
    setMessage(rootNode, "info", "Resetting browser state...");

    return root.fetch(endpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders({
        "Accept": "application/json"
      })
    }).then(function (response) {
      return response.json().catch(function () {
        return {};
      }).then(function (payload) {
        return {ok: response.ok, payload: payload};
      });
    }).then(function (result) {
      if (!result.ok || (result.payload && result.payload.error)) {
        throw new Error(parseError(result.payload, "Browser reset failed."));
      }

      clearBrowserStorage();
      setMessage(rootNode, "success", "Browser state reset. Redirecting to login...");
      root.setTimeout(function () {
        var redirectTo = result.payload && result.payload.login_url
          ? result.payload.login_url
          : loginUrl;
        root.location.assign(redirectTo || "/login");
      }, 300);
      return true;
    }).catch(function (error) {
      setMessage(
        rootNode,
        "error",
        error && error.message ? error.message : "Browser reset failed."
      );
      setBusy(rootNode, false);
      return false;
    });
  }

  function initialize() {
    var rootNode = document.querySelector("[data-browser-reset-root]");
    if (!rootNode) {
      return;
    }
    var action = rootNode.querySelector('[data-browser-reset-action="reset"]');
    if (action) {
      action.addEventListener("click", function () {
        runReset(rootNode);
      });
    }
  }

  root.WEPPDiagnosticsBrowserReset = {
    clearWeppStorage: clearWeppStorage,
    runReset: runReset
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})(window);

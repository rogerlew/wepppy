(function () {
  "use strict";

  if (window.__weppSessionHeartbeatLoaded === true) {
    return;
  }
  window.__weppSessionHeartbeatLoaded = true;

  var DEFAULT_INTERVAL_MS = 5 * 60 * 1000;
  var MAX_FAILURES = 3;
  var EXPIRED_EVENT_NAME = "wepp:session-heartbeat-expired";

  var timerId = null;
  var stopped = false;
  var consecutiveFailures = 0;
  var failureWarningIssued = false;
  var inFlight = false;
  var runtimeContext = null;
  var visibilityHandler = null;
  var beforeUnloadHandler = null;
  var pageHideHandler = null;

  function normalizePrefix(value) {
    if (!value) {
      return "";
    }
    var text = String(value).trim();
    if (!text || text === "/") {
      return "";
    }
    if (text.charAt(0) !== "/") {
      text = "/" + text;
    }
    return text.replace(/\/+$/, "");
  }

  function deriveSitePrefix(pathname) {
    var normalizedPath = typeof pathname === "string" ? pathname : "";
    if (normalizedPath.indexOf("/runs/") !== -1) {
      var idx = normalizedPath.indexOf("/runs/");
      return normalizePrefix(normalizedPath.slice(0, idx));
    }
    if (normalizedPath.indexOf("/weppcloud/") === 0 || normalizedPath === "/weppcloud") {
      return "/weppcloud";
    }
    return "";
  }

  function getContext() {
    var body = document.body;
    if (!body || !body.dataset) {
      return null;
    }

    var userAuthenticated = body.dataset.userAuthenticated === "true";
    if (!userAuthenticated) {
      return null;
    }

    var pathname = window.location && typeof window.location.pathname === "string"
      ? window.location.pathname
      : "";
    var sitePrefix = normalizePrefix(body.dataset.sitePrefix);
    if (!sitePrefix) {
      sitePrefix = deriveSitePrefix(pathname);
    }

    return {
      sitePrefix: sitePrefix
    };
  }

  function resolveHeartbeatUrl(context) {
    return (context.sitePrefix || "") + "/api/auth/session-heartbeat";
  }

  function resolveLoginUrl(context) {
    var currentPath = "/";
    if (window.location) {
      currentPath = (window.location.pathname || "/") + (window.location.search || "") + (window.location.hash || "");
    }
    return (context.sitePrefix || "") + "/login?next=" + encodeURIComponent(currentPath);
  }

  function readCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) {
      return "";
    }
    return String(meta.getAttribute("content") || "").trim();
  }

  function createSessionExpiredBanner(context) {
    if (document.getElementById("wc-session-expired-banner")) {
      return;
    }

    var container = document.createElement("div");
    container.id = "wc-session-expired-banner";
    container.setAttribute("role", "alert");
    container.style.position = "fixed";
    container.style.left = "0";
    container.style.right = "0";
    container.style.bottom = "0";
    container.style.zIndex = "1200";
    container.style.background = "#fff4e5";
    container.style.borderTop = "1px solid #f0b429";
    container.style.padding = "12px 16px";
    container.style.display = "flex";
    container.style.flexWrap = "wrap";
    container.style.gap = "8px 12px";
    container.style.alignItems = "center";
    container.style.justifyContent = "space-between";

    var message = document.createElement("span");
    message.textContent = "Session expired. Sign in again to continue.";
    message.style.color = "#5f370e";
    message.style.fontWeight = "600";

    var actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";

    var loginLink = document.createElement("a");
    loginLink.href = resolveLoginUrl(context);
    loginLink.textContent = "Sign in";
    loginLink.style.padding = "6px 10px";
    loginLink.style.border = "1px solid #9f580a";
    loginLink.style.borderRadius = "4px";
    loginLink.style.background = "#9f580a";
    loginLink.style.color = "#ffffff";
    loginLink.style.textDecoration = "none";

    var reloadButton = document.createElement("button");
    reloadButton.type = "button";
    reloadButton.textContent = "Reload";
    reloadButton.style.padding = "6px 10px";
    reloadButton.style.border = "1px solid #9f580a";
    reloadButton.style.borderRadius = "4px";
    reloadButton.style.background = "#ffffff";
    reloadButton.style.color = "#5f370e";
    reloadButton.addEventListener("click", function () {
      if (window.location && typeof window.location.reload === "function") {
        window.location.reload();
      }
    });

    actions.appendChild(loginLink);
    actions.appendChild(reloadButton);
    container.appendChild(message);
    container.appendChild(actions);
    document.body.appendChild(container);
  }

  function stopHeartbeat(reason) {
    if (stopped) {
      return;
    }
    stopped = true;
    if (timerId !== null) {
      clearInterval(timerId);
      timerId = null;
    }
    if (visibilityHandler) {
      document.removeEventListener("visibilitychange", visibilityHandler);
      visibilityHandler = null;
    }
    if (beforeUnloadHandler) {
      window.removeEventListener("beforeunload", beforeUnloadHandler);
      beforeUnloadHandler = null;
    }
    if (pageHideHandler) {
      window.removeEventListener("pagehide", pageHideHandler);
      pageHideHandler = null;
    }
    if (reason === "unauthorized") {
      createSessionExpiredBanner(runtimeContext || { sitePrefix: "" });
      document.dispatchEvent(new CustomEvent(EXPIRED_EVENT_NAME));
    }
  }

  function sendHeartbeat(url) {
    if (stopped || inFlight) {
      return;
    }
    inFlight = true;
    var headers = {
      Accept: "application/json"
    };
    var csrfToken = readCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: headers
    })
      .then(function (response) {
        if (!response.ok) {
          var error = new Error("Session heartbeat failed");
          error.status = response.status;
          throw error;
        }
        consecutiveFailures = 0;
        failureWarningIssued = false;
      })
      .catch(function (error) {
        consecutiveFailures += 1;
        if (error && (error.status === 401 || error.status === 403)) {
          stopHeartbeat("unauthorized");
          return;
        }
        if (consecutiveFailures >= MAX_FAILURES && !failureWarningIssued) {
          failureWarningIssued = true;
          if (window.console && typeof window.console.warn === "function") {
            window.console.warn("Session heartbeat is retrying after repeated network errors.");
          }
        }
      })
      .finally(function () {
        inFlight = false;
      });
  }

  function startHeartbeat() {
    var context = getContext();
    if (!context) {
      return;
    }
    runtimeContext = context;
    var intervalMs = DEFAULT_INTERVAL_MS;
    var url = resolveHeartbeatUrl(context);

    sendHeartbeat(url);
    timerId = setInterval(function () {
      sendHeartbeat(url);
    }, intervalMs);

    visibilityHandler = function () {
      if (document.visibilityState === "visible") {
        sendHeartbeat(url);
      }
    };
    document.addEventListener("visibilitychange", visibilityHandler);

    beforeUnloadHandler = function () {
      stopHeartbeat("unload");
    };
    pageHideHandler = function (event) {
      if (event && event.persisted === true) {
        return;
      }
      stopHeartbeat("hide");
    };
    window.addEventListener("beforeunload", beforeUnloadHandler);
    window.addEventListener("pagehide", pageHideHandler);
  }

  function init() {
    if (stopped || timerId !== null) {
      return;
    }
    startHeartbeat();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

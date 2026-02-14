(function () {
  "use strict";

  if (window.__weppControllersGlStaleCheckLoaded === true) {
    return;
  }
  window.__weppControllersGlStaleCheckLoaded = true;

  var STALE_BANNER_ID = "wc-stale-client-banner";
  var SESSION_BANNER_ID = "wc-session-expired-banner";
  var SESSION_EXPIRED_EVENT_NAME = "wepp:session-heartbeat-expired";
  var RELOAD_REQUESTED_EVENT_NAME = "wepp:controllers-gl-stale-reload";
  var dismissed = false;

  function normalizeBuildId(value) {
    if (value === undefined || value === null) {
      return "";
    }
    var text = String(value).trim();
    if (!text) {
      return "";
    }
    if (text.toLowerCase() === "none") {
      return "";
    }
    return text;
  }

  function getExpectedBuildId() {
    var body = document.body;
    if (!body || !body.dataset) {
      return "";
    }
    return normalizeBuildId(body.dataset.controllersGlExpectedBuildId);
  }

  function getActualBuildId() {
    return normalizeBuildId(window.__weppControllersGlBuildId);
  }

  function resolveExistingBanner() {
    return document.getElementById(STALE_BANNER_ID);
  }

  function createStaleBanner() {
    var existing = resolveExistingBanner();
    if (existing) {
      return existing;
    }

    var body = document.body;
    if (!body) {
      return null;
    }

    var container = document.createElement("div");
    container.id = STALE_BANNER_ID;
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
    message.textContent = "Update available. Save your work, then reload to load the latest UI.";
    message.style.color = "#5f370e";
    message.style.fontWeight = "600";

    var actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";

    var reloadButton = document.createElement("button");
    reloadButton.type = "button";
    reloadButton.textContent = "Reload";
    reloadButton.dataset.wcStaleAction = "reload";
    reloadButton.style.padding = "6px 10px";
    reloadButton.style.border = "1px solid #9f580a";
    reloadButton.style.borderRadius = "4px";
    reloadButton.style.background = "#9f580a";
    reloadButton.style.color = "#ffffff";
    reloadButton.addEventListener("click", function () {
      try {
        if (typeof Event === "function") {
          document.dispatchEvent(new Event(RELOAD_REQUESTED_EVENT_NAME));
        }
      } catch (err) {
        // Best-effort instrumentation; reload remains the primary behavior.
      }
      var userAgent = window.navigator && window.navigator.userAgent
        ? String(window.navigator.userAgent).toLowerCase()
        : "";
      if (userAgent.indexOf("jsdom") !== -1) {
        return;
      }
      if (window.location && typeof window.location.reload === "function") {
        window.location.reload();
      }
    });

    var dismissButton = document.createElement("button");
    dismissButton.type = "button";
    dismissButton.textContent = "Dismiss";
    dismissButton.dataset.wcStaleAction = "dismiss";
    dismissButton.style.padding = "6px 10px";
    dismissButton.style.border = "1px solid #9f580a";
    dismissButton.style.borderRadius = "4px";
    dismissButton.style.background = "#ffffff";
    dismissButton.style.color = "#5f370e";
    dismissButton.addEventListener("click", function () {
      dismissed = true;
      if (container && container.parentNode) {
        container.parentNode.removeChild(container);
      }
    });

    actions.appendChild(reloadButton);
    actions.appendChild(dismissButton);
    container.appendChild(message);
    container.appendChild(actions);
    body.appendChild(container);

    return container;
  }

  function adjustBannerOffset() {
    var banner = resolveExistingBanner();
    if (!banner) {
      return;
    }
    var bottomOffset = 0;
    var sessionBanner = document.getElementById(SESSION_BANNER_ID);
    if (sessionBanner && sessionBanner.offsetHeight) {
      bottomOffset = sessionBanner.offsetHeight;
    }
    banner.style.bottom = bottomOffset + "px";
  }

  function renderIfStale(expectedBuildId, actualBuildId) {
    if (dismissed) {
      return;
    }
    if (!expectedBuildId) {
      return;
    }
    if (actualBuildId && actualBuildId === expectedBuildId) {
      return;
    }
    var banner = createStaleBanner();
    if (!banner) {
      return;
    }
    adjustBannerOffset();
  }

  function init() {
    var expected = getExpectedBuildId();
    if (!expected) {
      return;
    }
    var actual = getActualBuildId();
    renderIfStale(expected, actual);
  }

  document.addEventListener(SESSION_EXPIRED_EVENT_NAME, adjustBannerOffset);
  window.addEventListener("resize", adjustBannerOffset);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

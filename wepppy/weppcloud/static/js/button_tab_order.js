(function () {
  "use strict";

  if (window.__weppButtonTabOrderLoaded === true) {
    return;
  }
  window.__weppButtonTabOrderLoaded = true;

  var AUTO_TABINDEX_ATTR = "data-wc-auto-tabindex";
  var TABBABLE_BUTTON_SELECTOR = [
    "button",
    "input[type='button']",
    "input[type='submit']",
    "input[type='reset']",
    ".pure-button",
    ".wc-oauth-button",
  ].join(",");

  function hasExplicitTabindex(element) {
    if (!element.hasAttribute("tabindex")) {
      return false;
    }
    return element.getAttribute(AUTO_TABINDEX_ATTR) !== "true";
  }

  function isDisabled(element) {
    if (typeof element.disabled === "boolean" && element.disabled) {
      return true;
    }
    if (element.getAttribute("aria-disabled") === "true") {
      return true;
    }
    return element.classList.contains("pure-button-disabled");
  }

  function normalizeButtonTabIndex(element) {
    if (!element || element.matches(TABBABLE_BUTTON_SELECTOR) === false) {
      return;
    }
    if (hasExplicitTabindex(element)) {
      return;
    }
    if (isDisabled(element)) {
      if (element.getAttribute(AUTO_TABINDEX_ATTR) === "true") {
        element.removeAttribute("tabindex");
        element.removeAttribute(AUTO_TABINDEX_ATTR);
      }
      return;
    }
    if (!element.hasAttribute("tabindex")) {
      element.setAttribute("tabindex", "0");
      element.setAttribute(AUTO_TABINDEX_ATTR, "true");
    }
  }

  function normalizeScope(root) {
    if (!root) {
      return;
    }
    if (root.nodeType === 1 && root.matches(TABBABLE_BUTTON_SELECTOR)) {
      normalizeButtonTabIndex(root);
    }
    if (!root.querySelectorAll) {
      return;
    }
    root.querySelectorAll(TABBABLE_BUTTON_SELECTOR).forEach(function (element) {
      normalizeButtonTabIndex(element);
    });
  }

  function observeMutations() {
    if (typeof MutationObserver === "undefined" || !document.documentElement) {
      return;
    }
    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (mutation.type === "attributes") {
          normalizeButtonTabIndex(mutation.target);
          return;
        }
        mutation.addedNodes.forEach(function (node) {
          if (node && node.nodeType === 1) {
            normalizeScope(node);
          }
        });
      });
    });
    observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["disabled", "aria-disabled", "class", "tabindex"],
    });
  }

  function init() {
    normalizeScope(document);
    observeMutations();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

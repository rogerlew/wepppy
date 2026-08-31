(function (global) {
  "use strict";

  if (global.__weppTableOverflowAccessibilityLoaded === true) {
    return;
  }
  global.__weppTableOverflowAccessibilityLoaded = true;

  var WRAPPER_SELECTOR = ".wc-table-wrapper";
  var OVERFLOW_ATTR = "data-wc-horizontal-overflow";
  var HINT_CLASS = "wc-table-overflow-hint";
  var HINT_TEXT = "More columns are available. Scroll horizontally to view them: use Shift + mouse wheel, or focus this table and use Left and Right Arrow keys.";
  var states = new WeakMap();
  var observedWrappers = new WeakSet();
  var observedTables = new WeakSet();
  var hintSequence = 0;
  var resizeObserver = null;
  var mutationObserver = null;

  function stateFor(wrapper) {
    var state = states.get(wrapper);
    if (!state) {
      state = {
        hint: null,
        generatedTabindex: false,
        generatedRole: false,
        generatedLabel: null,
      };
      states.set(wrapper, state);
    }
    return state;
  }

  function textIsUsable(value) {
    return typeof value === "string" && value.trim().length > 0;
  }

  function labelledbyIsUsable(wrapper) {
    if (!wrapper.hasAttribute("aria-labelledby")) {
      return false;
    }
    return wrapper
      .getAttribute("aria-labelledby")
      .split(/\s+/)
      .filter(Boolean)
      .some(function (id) {
        var labelledBy = document.getElementById(id);
        return labelledBy && textIsUsable(labelledBy.textContent);
      });
  }

  function authoredNameState(wrapper, state) {
    var generatedLabelIsCurrent = state.generatedLabel !== null
      && wrapper.getAttribute("aria-label") === state.generatedLabel;
    var hasAuthoredLabel = wrapper.hasAttribute("aria-label") && !generatedLabelIsCurrent;
    var hasAuthoredLabelledby = wrapper.hasAttribute("aria-labelledby");
    var usableLabelledby = hasAuthoredLabelledby && labelledbyIsUsable(wrapper);
    var usableLabel = hasAuthoredLabel && textIsUsable(wrapper.getAttribute("aria-label"));

    return {
      hasAuthoredAttribute: hasAuthoredLabel || hasAuthoredLabelledby,
      usable: usableLabelledby || usableLabel,
    };
  }

  function fallbackLabel(wrapper, table) {
    var caption = table.querySelector("caption");
    if (caption && textIsUsable(caption.textContent)) {
      return caption.textContent.trim();
    }
    var section = wrapper.closest("section");
    var headings = section ? section.querySelectorAll("h1, h2, h3, h4, h5, h6") : [];
    for (var index = 0; index < headings.length; index += 1) {
      if (textIsUsable(headings[index].textContent)) {
        return headings[index].textContent.trim();
      }
    }
    return "Scrollable data table";
  }

  function ensureHint(wrapper, state) {
    if (state.hint && state.hint.isConnected) {
      return state.hint;
    }
    hintSequence += 1;
    var hint = document.createElement("p");
    hint.id = "wc-table-overflow-hint-" + hintSequence;
    hint.className = HINT_CLASS;
    hint.textContent = HINT_TEXT;
    wrapper.parentNode.insertBefore(hint, wrapper);
    state.hint = hint;
    return hint;
  }

  function appendDescription(wrapper, hintId) {
    var tokens = (wrapper.getAttribute("aria-describedby") || "")
      .split(/\s+/)
      .filter(Boolean);
    if (tokens.indexOf(hintId) === -1) {
      tokens.push(hintId);
      wrapper.setAttribute("aria-describedby", tokens.join(" "));
    }
  }

  function removeDescription(wrapper, hintId) {
    if (!hintId || !wrapper.hasAttribute("aria-describedby")) {
      return;
    }
    var tokens = wrapper
      .getAttribute("aria-describedby")
      .split(/\s+/)
      .filter(function (token) {
        return token && token !== hintId;
      });
    if (tokens.length > 0) {
      wrapper.setAttribute("aria-describedby", tokens.join(" "));
    } else {
      wrapper.removeAttribute("aria-describedby");
    }
  }

  function removeGeneratedRoleAndLabel(wrapper, state) {
    if (state.generatedRole) {
      if (wrapper.getAttribute("role") === "region") {
        wrapper.removeAttribute("role");
      }
      state.generatedRole = false;
    }
    if (state.generatedLabel !== null) {
      if (wrapper.getAttribute("aria-label") === state.generatedLabel) {
        wrapper.removeAttribute("aria-label");
      }
      state.generatedLabel = null;
    }
  }

  function activate(wrapper, table, state) {
    var hint = ensureHint(wrapper, state);
    wrapper.setAttribute(OVERFLOW_ATTR, "true");
    appendDescription(wrapper, hint.id);

    if (!wrapper.hasAttribute("tabindex")) {
      wrapper.setAttribute("tabindex", "0");
      state.generatedTabindex = true;
    } else if (state.generatedTabindex && wrapper.getAttribute("tabindex") !== "0") {
      state.generatedTabindex = false;
    }

    var nameState = authoredNameState(wrapper, state);
    if (nameState.hasAuthoredAttribute && !nameState.usable) {
      removeGeneratedRoleAndLabel(wrapper, state);
      return;
    }

    if (!wrapper.hasAttribute("role")) {
      wrapper.setAttribute("role", "region");
      state.generatedRole = true;
    } else if (state.generatedRole && wrapper.getAttribute("role") !== "region") {
      state.generatedRole = false;
    }

    if (nameState.usable) {
      if (state.generatedLabel !== null) {
        if (wrapper.getAttribute("aria-label") === state.generatedLabel) {
          wrapper.removeAttribute("aria-label");
        }
        state.generatedLabel = null;
      }
      return;
    }

    if (!wrapper.hasAttribute("aria-label") && !wrapper.hasAttribute("aria-labelledby")) {
      var label = fallbackLabel(wrapper, table);
      wrapper.setAttribute("aria-label", label);
      state.generatedLabel = label;
    }
  }

  function deactivate(wrapper, state) {
    var hintId = state.hint ? state.hint.id : null;
    removeDescription(wrapper, hintId);
    if (state.hint && state.hint.parentNode) {
      state.hint.parentNode.removeChild(state.hint);
    }
    state.hint = null;
    wrapper.removeAttribute(OVERFLOW_ATTR);

    if (state.generatedTabindex) {
      if (wrapper.getAttribute("tabindex") === "0") {
        wrapper.removeAttribute("tabindex");
      }
      state.generatedTabindex = false;
    }
    removeGeneratedRoleAndLabel(wrapper, state);
  }

  function sync(wrapper) {
    if (!wrapper || !wrapper.matches || !wrapper.matches(WRAPPER_SELECTOR)) {
      return;
    }
    var state = stateFor(wrapper);
    var table = wrapper.querySelector("table");
    var overflows = table !== null
      && wrapper.clientWidth > 0
      && wrapper.scrollWidth > wrapper.clientWidth + 1;
    if (overflows) {
      activate(wrapper, table, state);
    } else {
      deactivate(wrapper, state);
    }
  }

  function observeWrapper(wrapper) {
    if (!observedWrappers.has(wrapper)) {
      observedWrappers.add(wrapper);
      if (resizeObserver) {
        resizeObserver.observe(wrapper);
      }
    }
    var table = wrapper.querySelector("table");
    if (resizeObserver && table && !observedTables.has(table)) {
      observedTables.add(table);
      resizeObserver.observe(table);
    }
  }

  function refresh(root) {
    var scope = root || document;
    if (scope.nodeType === 1 && scope.matches(WRAPPER_SELECTOR)) {
      observeWrapper(scope);
      sync(scope);
    }
    if (!scope.querySelectorAll) {
      return;
    }
    scope.querySelectorAll(WRAPPER_SELECTOR).forEach(function (wrapper) {
      observeWrapper(wrapper);
      sync(wrapper);
    });
  }

  function refreshMutations(mutations) {
    var wrappers = [];
    function addWrapper(wrapper) {
      if (wrapper && wrappers.indexOf(wrapper) === -1) {
        wrappers.push(wrapper);
      }
    }

    mutations.forEach(function (mutation) {
      var target = mutation.target && mutation.target.nodeType === 1
        ? mutation.target
        : null;
      if (target) {
        addWrapper(target.matches(WRAPPER_SELECTOR) ? target : target.closest(WRAPPER_SELECTOR));
      }
      mutation.addedNodes.forEach(function (node) {
        if (!node || node.nodeType !== 1) {
          return;
        }
        if (node.matches(WRAPPER_SELECTOR)) {
          addWrapper(node);
        }
        node.querySelectorAll(WRAPPER_SELECTOR).forEach(addWrapper);
      });
    });

    wrappers.forEach(function (wrapper) {
      observeWrapper(wrapper);
      sync(wrapper);
    });
  }

  function init() {
    if (typeof global.ResizeObserver === "function") {
      resizeObserver = new global.ResizeObserver(function (entries) {
        entries.forEach(function (entry) {
          var wrapper = entry.target.matches(WRAPPER_SELECTOR)
            ? entry.target
            : entry.target.closest(WRAPPER_SELECTOR);
          if (wrapper) {
            sync(wrapper);
          }
        });
      });
    }
    refresh(document);

    if (typeof global.MutationObserver === "function" && document.documentElement) {
      mutationObserver = new global.MutationObserver(refreshMutations);
      mutationObserver.observe(document.documentElement, {
        childList: true,
        subtree: true,
      });
    }
  }

  global.WCTableOverflowAccessibility = {
    refresh: refresh,
    sync: sync,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})(typeof window !== "undefined" ? window : this);

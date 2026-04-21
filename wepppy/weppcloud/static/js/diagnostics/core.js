(function (root) {
  "use strict";

  if (!root || root.WEPPDiagnosticsCore) {
    return;
  }

  var CHECK_DEFINITIONS = [
    {
      id: "javascript-execution",
      title: "JavaScript execution sentinel",
      severity: "blocker",
      fix_hint: "Enable JavaScript for this site, then reload diagnostics."
    },
    {
      id: "browser-api-baseline",
      title: "Browser API baseline",
      severity: "blocker",
      fix_hint: "Upgrade to a modern browser that supports the WEPPcloud baseline APIs."
    },
    {
      id: "cookie-storage",
      title: "Cookie write/read/delete",
      severity: "blocker",
      fix_hint: "Allow first-party cookies for this site and retry diagnostics."
    },
    {
      id: "local-storage",
      title: "localStorage write/read/delete",
      severity: "info",
      fix_hint: "Enable persistent site data if you need local browser caching features."
    },
    {
      id: "abort-controller",
      title: "AbortController availability",
      severity: "info",
      fix_hint: "Use an up-to-date browser for better request cancellation support."
    }
  ];

  var CHECK_ORDER = [];
  var idx;
  for (idx = 0; idx < CHECK_DEFINITIONS.length; idx += 1) {
    CHECK_ORDER.push(CHECK_DEFINITIONS[idx].id);
  }

  var EXTENSION_CHECKS = [];

  var ALLOWED_STATUSES = {
    pass: true,
    fail: true,
    warn: true,
    skipped: true
  };

  var ALLOWED_SEVERITIES = {
    blocker: true,
    degraded: true,
    info: true
  };

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

  function readSitePrefix() {
    var body = document.body;
    if (!body || !body.dataset) {
      return "";
    }
    return normalizePrefix(document.body.dataset.sitePrefix || "");
  }

  function readCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) {
      return "";
    }
    return String(meta.getAttribute("content") || "").trim();
  }

  function isUserAuthenticated() {
    var body = document.body;
    if (!body || !body.dataset) {
      return false;
    }
    return body.dataset.userAuthenticated === "true";
  }

  function buildContext() {
    return {
      sitePrefix: readSitePrefix(),
      userAuthenticated: isUserAuthenticated(),
      csrfToken: readCsrfToken()
    };
  }

  function cloneCheckDefinition(definition) {
    return {
      id: definition.id,
      title: definition.title,
      severity: definition.severity,
      fix_hint: definition.fix_hint
    };
  }

  function makeResult(definition, status, evidence, fixHintOverride) {
    return {
      id: definition.id,
      title: definition.title,
      severity: definition.severity,
      status: status,
      evidence: evidence,
      fix_hint: fixHintOverride || definition.fix_hint
    };
  }

  function hasCookie(cookieName) {
    var cookieSource = String(document.cookie || "");
    var escaped = cookieName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    var pattern = new RegExp("(?:^|;\\s*)" + escaped + "=");
    return pattern.test(cookieSource);
  }

  function runJavascriptExecutionCheck(definition) {
    return makeResult(definition, "pass", "Diagnostics script executed successfully.");
  }

  function isApiAvailable(apiName) {
    if (apiName === "Promise") {
      return typeof root.Promise === "function";
    }
    if (apiName === "CustomEvent") {
      return typeof root.CustomEvent === "function" || typeof root.CustomEvent === "object";
    }
    return typeof root[apiName] !== "undefined" && root[apiName] !== null;
  }

  function runBrowserApiBaselineCheck(definition) {
    var requiredApis = ["fetch", "Promise", "CustomEvent", "URL", "URLSearchParams", "FormData"];
    var missingApis = [];
    var apiIdx;

    for (apiIdx = 0; apiIdx < requiredApis.length; apiIdx += 1) {
      if (!isApiAvailable(requiredApis[apiIdx])) {
        missingApis.push(requiredApis[apiIdx]);
      }
    }

    if (missingApis.length > 0) {
      return makeResult(
        definition,
        "fail",
        "Missing required APIs: " + missingApis.join(", ") + "."
      );
    }

    return makeResult(definition, "pass", "All baseline browser APIs are available.");
  }

  function runCookieCheck(definition) {
    var probeName = "wepp_diag_cookie_probe_" + String(new Date().getTime());

    try {
      document.cookie = probeName + "=1; path=/";

      if (!hasCookie(probeName)) {
        return makeResult(
          definition,
          "fail",
          "Cookie probe could not be read after write attempt."
        );
      }

      document.cookie = probeName + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
      if (hasCookie(probeName)) {
        return makeResult(
          definition,
          "fail",
          "Cookie probe remained present after delete attempt."
        );
      }

      return makeResult(definition, "pass", "Cookie probe write/read/delete succeeded.");
    } catch (error) {
      return makeResult(
        definition,
        "fail",
        "Cookie probe raised " + (error && error.name ? error.name : "an unexpected error") + "."
      );
    }
  }

  function runLocalStorageCheck(definition) {
    var probeKey = "wepp_diag_localstorage_probe";

    try {
      if (!root.localStorage) {
        return makeResult(
          definition,
          "warn",
          "localStorage is not available in this context."
        );
      }

      root.localStorage.setItem(probeKey, "1");
      if (root.localStorage.getItem(probeKey) !== "1") {
        return makeResult(
          definition,
          "warn",
          "localStorage write/read round-trip did not return expected probe value."
        );
      }

      root.localStorage.removeItem(probeKey);
      return makeResult(definition, "pass", "localStorage write/read/delete succeeded.");
    } catch (error) {
      return makeResult(
        definition,
        "warn",
        "localStorage probe raised " + (error && error.name ? error.name : "an unexpected error") + "."
      );
    }
  }

  function runAbortControllerCheck(definition) {
    if (typeof root.AbortController === "function") {
      return makeResult(definition, "pass", "AbortController is available.");
    }

    return makeResult(
      definition,
      "warn",
      "AbortController is not available in this browser."
    );
  }

  function normalizeExtensionDefinition(rawDefinition) {
    if (!rawDefinition || typeof rawDefinition !== "object") {
      return null;
    }

    var id = String(rawDefinition.id || "").trim();
    if (!id || typeof rawDefinition.run !== "function") {
      return null;
    }

    var severity = String(rawDefinition.severity || "info").toLowerCase();
    if (!ALLOWED_SEVERITIES[severity]) {
      severity = "info";
    }

    return {
      id: id,
      title: String(rawDefinition.title || id),
      severity: severity,
      fix_hint: String(rawDefinition.fix_hint || "Review browser settings and retry diagnostics."),
      run: rawDefinition.run
    };
  }

  function findExtensionIndex(checkId) {
    var checkIdText = String(checkId || "");
    var extensionIdx;
    for (extensionIdx = 0; extensionIdx < EXTENSION_CHECKS.length; extensionIdx += 1) {
      if (EXTENSION_CHECKS[extensionIdx].id === checkIdText) {
        return extensionIdx;
      }
    }
    return -1;
  }

  function registerCheck(rawDefinition) {
    var normalized = normalizeExtensionDefinition(rawDefinition);
    if (!normalized) {
      return false;
    }

    var existingIndex = findExtensionIndex(normalized.id);
    if (existingIndex >= 0) {
      EXTENSION_CHECKS[existingIndex] = normalized;
      return true;
    }

    EXTENSION_CHECKS.push(normalized);
    return true;
  }

  function registerChecks(rawDefinitions) {
    if (!Array.isArray(rawDefinitions)) {
      return 0;
    }

    var accepted = 0;
    var definitionIdx;
    for (definitionIdx = 0; definitionIdx < rawDefinitions.length; definitionIdx += 1) {
      if (registerCheck(rawDefinitions[definitionIdx])) {
        accepted += 1;
      }
    }

    return accepted;
  }

  function getCheckOrder() {
    var order = CHECK_ORDER.slice();
    var extensionIdx;

    for (extensionIdx = 0; extensionIdx < EXTENSION_CHECKS.length; extensionIdx += 1) {
      order.push(EXTENSION_CHECKS[extensionIdx].id);
    }

    return order;
  }

  function normalizeExtensionResult(definition, rawResult) {
    var result = rawResult && typeof rawResult === "object" ? rawResult : {};
    var status = String(result.status || "fail").toLowerCase();
    if (!ALLOWED_STATUSES[status]) {
      status = "fail";
    }

    return {
      id: definition.id,
      title: definition.title,
      severity: definition.severity,
      status: status,
      evidence: String(result.evidence || "No evidence provided."),
      fix_hint: String(result.fix_hint || definition.fix_hint)
    };
  }

  function runCoreChecks() {
    var results = [];

    results.push(runJavascriptExecutionCheck(CHECK_DEFINITIONS[0]));
    results.push(runBrowserApiBaselineCheck(CHECK_DEFINITIONS[1]));
    results.push(runCookieCheck(CHECK_DEFINITIONS[2]));
    results.push(runLocalStorageCheck(CHECK_DEFINITIONS[3]));
    results.push(runAbortControllerCheck(CHECK_DEFINITIONS[4]));

    return results;
  }

  function runExtensionChecks(context) {
    var results = [];
    var sequence = Promise.resolve();
    var extensionIdx;

    for (extensionIdx = 0; extensionIdx < EXTENSION_CHECKS.length; extensionIdx += 1) {
      (function (definition) {
        sequence = sequence.then(function () {
          return Promise.resolve()
            .then(function () {
              return definition.run(context);
            })
            .then(function (rawResult) {
              results.push(normalizeExtensionResult(definition, rawResult));
            })
            .catch(function (error) {
              var reason = "Unexpected diagnostics check error.";
              if (error && error.message) {
                reason = String(error.message);
              }
              results.push(
                normalizeExtensionResult(definition, {
                  status: "fail",
                  evidence: reason,
                  fix_hint: definition.fix_hint
                })
              );
            });
        });
      })(EXTENSION_CHECKS[extensionIdx]);
    }

    return sequence.then(function () {
      return results;
    });
  }

  function runAllChecks() {
    var context = buildContext();
    var coreResults = runCoreChecks();

    return runExtensionChecks(context).then(function (extensionResults) {
      return coreResults.concat(extensionResults);
    });
  }

  function getCheckDefinitions() {
    var definitions = [];
    var definitionIdx;

    for (definitionIdx = 0; definitionIdx < CHECK_DEFINITIONS.length; definitionIdx += 1) {
      definitions.push(cloneCheckDefinition(CHECK_DEFINITIONS[definitionIdx]));
    }

    for (definitionIdx = 0; definitionIdx < EXTENSION_CHECKS.length; definitionIdx += 1) {
      definitions.push(cloneCheckDefinition(EXTENSION_CHECKS[definitionIdx]));
    }

    return definitions;
  }

  function flushPendingChecks() {
    var pending = root.__weppDiagnosticsPendingChecks;
    if (!Array.isArray(pending) || !pending.length) {
      return;
    }

    registerChecks(pending);
    pending.length = 0;
  }

  root.WEPPDiagnosticsCore = {
    CHECK_ORDER: CHECK_ORDER.slice(),
    readSitePrefix: readSitePrefix,
    readCsrfToken: readCsrfToken,
    isUserAuthenticated: isUserAuthenticated,
    buildContext: buildContext,
    getCheckOrder: getCheckOrder,
    getCheckDefinitions: getCheckDefinitions,
    runCoreChecks: runCoreChecks,
    runAllChecks: runAllChecks,
    registerCheck: registerCheck,
    registerChecks: registerChecks
  };

  flushPendingChecks();
})(window);

(function (root) {
  "use strict";

  if (!root || root.WEPPDiagnosticsAuthChecks) {
    return;
  }

  function extractErrorMessage(payload) {
    if (!payload || typeof payload !== "object") {
      return "";
    }
    if (payload.error && typeof payload.error === "object" && typeof payload.error.message === "string") {
      return String(payload.error.message).trim();
    }
    if (typeof payload.message === "string") {
      return String(payload.message).trim();
    }
    return "";
  }

  function mapStatus(statusCode) {
    if (statusCode === 400) {
      return {
        status: "fail",
        evidence: "HTTP 400 indicates CSRF token validation failed.",
        fix_hint: "Refresh the page to obtain a fresh CSRF token and rerun diagnostics."
      };
    }

    if (statusCode === 401) {
      return {
        status: "skipped",
        evidence: "HTTP 401 indicates no authenticated session for this auth-only check.",
        fix_hint: "Sign in to WEPPcloud, then rerun diagnostics."
      };
    }

    if (statusCode === 403) {
      return {
        status: "fail",
        evidence: "HTTP 403 indicates same-origin policy enforcement blocked the request.",
        fix_hint: "Run diagnostics from the WEPPcloud origin without cross-site proxy/header rewriting."
      };
    }

    return {
      status: "fail",
      evidence: "Unexpected auth endpoint response.",
      fix_hint: "Retry diagnostics and inspect server logs if this status persists."
    };
  }

  function parseJsonSafely(response) {
    return response
      .json()
      .then(function (payload) {
        return payload;
      })
      .catch(function () {
        return null;
      });
  }

  function combineEvidence(baseEvidence, payload) {
    var message = extractErrorMessage(payload);
    if (!message) {
      return baseEvidence;
    }
    return baseEvidence + " " + message;
  }

  function authSkippedResult() {
    return {
      status: "skipped",
      evidence: "No authenticated user session detected for this auth-only check.",
      fix_hint: "Sign in to WEPPcloud to run auth diagnostics."
    };
  }

  function csrfMissingResult() {
    return {
      status: "fail",
      evidence: "CSRF token meta tag is missing or empty.",
      fix_hint: "Reload the diagnostics page to restore CSRF metadata before retrying."
    };
  }

  function postAuthEndpoint(context, endpointPath) {
    var headers = {
      Accept: "application/json",
      "X-CSRFToken": context.csrfToken
    };

    return fetch((context.sitePrefix || "") + endpointPath, {
      method: "POST",
      credentials: "same-origin",
      headers: headers
    }).then(function (response) {
      return parseJsonSafely(response).then(function (payload) {
        return {
          statusCode: response.status,
          payload: payload
        };
      });
    });
  }

  function runSessionHeartbeat(context) {
    if (!context || !context.userAuthenticated) {
      return Promise.resolve(authSkippedResult());
    }

    if (!context.csrfToken) {
      return Promise.resolve(csrfMissingResult());
    }

    return postAuthEndpoint(context, "/api/auth/session-heartbeat")
      .then(function (result) {
        if (result.statusCode === 200) {
          var heartbeatPayload = result.payload || {};
          if (heartbeatPayload.ok === true) {
            return {
              status: "pass",
              evidence: "Heartbeat endpoint accepted this authenticated session.",
              fix_hint: ""
            };
          }

          return {
            status: "fail",
            evidence: "Heartbeat endpoint returned HTTP 200 without ok=true.",
            fix_hint: "Validate the session-heartbeat response contract and retry diagnostics."
          };
        }

        var mapped = mapStatus(result.statusCode);
        return {
          status: mapped.status,
          evidence: combineEvidence(mapped.evidence, result.payload),
          fix_hint: mapped.fix_hint
        };
      })
      .catch(function (error) {
        var message = error && error.message ? String(error.message) : "Network failure while calling session-heartbeat endpoint.";
        return {
          status: "fail",
          evidence: message,
          fix_hint: "Check browser connectivity and retry diagnostics."
        };
      });
  }

  function runRqEngineToken(context) {
    if (!context || !context.userAuthenticated) {
      return Promise.resolve(authSkippedResult());
    }

    if (!context.csrfToken) {
      return Promise.resolve(csrfMissingResult());
    }

    return postAuthEndpoint(context, "/api/auth/rq-engine-token")
      .then(function (result) {
        if (result.statusCode === 200) {
          var tokenPayload = result.payload || {};
          var hasToken = typeof tokenPayload.token === "string" && tokenPayload.token.trim().length > 0;

          if (hasToken) {
            return {
              status: "pass",
              evidence: "Token endpoint returned a token payload (token value redacted).",
              fix_hint: ""
            };
          }

          return {
            status: "fail",
            evidence: "Token endpoint returned HTTP 200 without a token field.",
            fix_hint: "Validate the rq-engine-token response contract and retry diagnostics."
          };
        }

        var mapped = mapStatus(result.statusCode);
        return {
          status: mapped.status,
          evidence: combineEvidence(mapped.evidence, result.payload),
          fix_hint: mapped.fix_hint
        };
      })
      .catch(function (error) {
        var message = error && error.message ? String(error.message) : "Network failure while calling rq-engine-token endpoint.";
        return {
          status: "fail",
          evidence: message,
          fix_hint: "Check browser connectivity and retry diagnostics."
        };
      });
  }

  var authChecks = [
    {
      id: "session-heartbeat",
      title: "Authenticated session heartbeat",
      severity: "blocker",
      fix_hint: "Sign in and retry diagnostics if this check does not pass.",
      run: runSessionHeartbeat
    },
    {
      id: "rq-engine-token",
      title: "RQ-engine token mint endpoint",
      severity: "blocker",
      fix_hint: "Sign in and retry diagnostics if this check does not pass.",
      run: runRqEngineToken
    }
  ];

  function registerWithCore() {
    var core = root.WEPPDiagnosticsCore;
    if (core && typeof core.registerChecks === "function") {
      core.registerChecks(authChecks);
      return;
    }

    if (!Array.isArray(root.__weppDiagnosticsPendingChecks)) {
      root.__weppDiagnosticsPendingChecks = [];
    }

    var idx;
    for (idx = 0; idx < authChecks.length; idx += 1) {
      root.__weppDiagnosticsPendingChecks.push(authChecks[idx]);
    }
  }

  registerWithCore();

  root.WEPPDiagnosticsAuthChecks = {
    checks: authChecks,
    mapStatus: mapStatus
  };
})(window);

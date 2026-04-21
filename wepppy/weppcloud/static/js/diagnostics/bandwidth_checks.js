(function (root) {
  "use strict";

  if (!root || root.WEPPDiagnosticsBandwidthChecks) {
    return;
  }

  var RTT_PROBE_BYTES = 1;
  var DEFAULT_DOWNLOAD_BYTES = 256 * 1024;
  var DEFAULT_UPLOAD_BYTES = 256 * 1024;
  var RTT_TIMEOUT_MS = 4000;
  var DOWNLOAD_TIMEOUT_MS = 12000;
  var UPLOAD_TIMEOUT_MS = 12000;
  var MIN_TIMEOUT_MS = 500;
  var MAX_TIMEOUT_MS = 30000;

  function nowMs() {
    return Date.now();
  }

  function normalizeTimeoutMs(value, fallback) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      parsed = fallback;
    }
    parsed = Math.trunc(parsed);
    if (parsed < MIN_TIMEOUT_MS) {
      return MIN_TIMEOUT_MS;
    }
    if (parsed > MAX_TIMEOUT_MS) {
      return MAX_TIMEOUT_MS;
    }
    return parsed;
  }

  function normalizeByteCount(value, fallback) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      parsed = fallback;
    }
    parsed = Math.trunc(parsed);
    if (parsed < 0) {
      return 0;
    }
    return parsed;
  }

  function normalizeElapsedMs(value) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return 0;
    }
    parsed = Math.trunc(parsed);
    if (parsed < 0) {
      return 0;
    }
    return parsed;
  }

  function formatMbps(value) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return "0.00";
    }
    return parsed.toFixed(2);
  }

  function computeApproxMbps(bytes, elapsedMs) {
    var byteCount = normalizeByteCount(bytes, 0);
    var elapsed = normalizeElapsedMs(elapsedMs);
    if (byteCount <= 0 || elapsed <= 0) {
      return 0;
    }
    return (byteCount * 8) / (elapsed / 1000) / 1000000;
  }

  function createMetrics(bytes, elapsedMs) {
    var normalizedBytes = normalizeByteCount(bytes, 0);
    var normalizedElapsed = normalizeElapsedMs(elapsedMs);
    return {
      bytes: normalizedBytes,
      elapsedMs: normalizedElapsed,
      mbps: computeApproxMbps(normalizedBytes, normalizedElapsed)
    };
  }

  function buildMetricsEvidence(prefix, metrics, detail) {
    var evidence = String(prefix || "");
    if (evidence && evidence.charAt(evidence.length - 1) !== " ") {
      evidence += " ";
    }
    evidence += "Approximate metric (environment-dependent): bytes="
      + String(metrics.bytes)
      + ", elapsed_ms="
      + String(metrics.elapsedMs)
      + ", approx_mbps="
      + formatMbps(metrics.mbps)
      + ".";
    if (detail) {
      evidence += " " + String(detail);
    }
    return evidence;
  }

  function resolveFetchFn() {
    if (typeof root.fetch === "function") {
      return root.fetch.bind(root);
    }
    return null;
  }

  function parseJsonSafely(response) {
    if (!response || typeof response.json !== "function") {
      return Promise.resolve(null);
    }
    return response
      .json()
      .then(function (payload) {
        return payload;
      })
      .catch(function () {
        return null;
      });
  }

  function extractErrorCode(payload) {
    if (!payload || typeof payload !== "object" || !payload.error || typeof payload.error !== "object") {
      return "";
    }
    if (typeof payload.error.code !== "string") {
      return "";
    }
    var token = payload.error.code.trim();
    if (!token) {
      return "";
    }
    if (!/^[A-Za-z0-9_.-]+$/.test(token)) {
      return "";
    }
    return token;
  }

  function isSaveDataEnabled() {
    var navigatorLike = root.navigator;
    if (!navigatorLike || !navigatorLike.connection) {
      return false;
    }
    return navigatorLike.connection.saveData === true;
  }

  function saveDataSkippedResult(bytes) {
    return {
      status: "skipped",
      evidence: buildMetricsEvidence(
        "Skipped because navigator.connection.saveData === true.",
        createMetrics(bytes, 0),
        "Set Save-Data off to run this informational probe."
      ),
      fix_hint: "Disable Save-Data and rerun diagnostics to collect approximate network metrics."
    };
  }

  function buildWarnResult(prefix, bytes, elapsedMs, detail, fixHint) {
    return {
      status: "warn",
      evidence: buildMetricsEvidence(prefix, createMetrics(bytes, elapsedMs), detail),
      fix_hint: fixHint
    };
  }

  function buildPassResult(prefix, bytes, elapsedMs, detail) {
    return {
      status: "pass",
      evidence: buildMetricsEvidence(prefix, createMetrics(bytes, elapsedMs), detail),
      fix_hint: ""
    };
  }

  async function executeFetchProbe(config) {
    var fetchFn = resolveFetchFn();
    var timeoutMs = normalizeTimeoutMs(config.timeoutMs, 10000);
    if (!fetchFn) {
      return {
        ok: false,
        timedOut: false,
        reason: "Fetch API unavailable in this browser runtime.",
        elapsedMs: 0,
        timeoutMs: timeoutMs
      };
    }

    var AbortCtor = typeof root.AbortController === "function" ? root.AbortController : null;
    var abortController = AbortCtor ? new AbortCtor() : null;
    var timedOut = false;
    var timeoutId = null;
    var started = nowMs();

    var requestOptions = {
      method: String(config.method || "GET"),
      credentials: "same-origin",
      cache: "no-store"
    };
    if (config.headers && typeof config.headers === "object") {
      requestOptions.headers = config.headers;
    }
    if (typeof config.body !== "undefined") {
      requestOptions.body = config.body;
    }
    if (abortController) {
      requestOptions.signal = abortController.signal;
    }

    try {
      var requestPromise = Promise.resolve()
        .then(function () {
          return fetchFn(config.url, requestOptions);
        })
        .then(function (response) {
          var consume = typeof config.consume === "function"
            ? config.consume
            : function () {
              return Promise.resolve(null);
            };
          return Promise.resolve(consume(response)).then(function (consumed) {
            return {
              response: response,
              consumed: consumed
            };
          });
        });

      var timeoutPromise = new Promise(function (_resolve, reject) {
        timeoutId = setTimeout(function () {
          timedOut = true;
          if (abortController && typeof abortController.abort === "function") {
            abortController.abort();
          }
          reject(new Error("timeout"));
        }, timeoutMs);
      });

      var result = await Promise.race([requestPromise, timeoutPromise]);
      return {
        ok: true,
        response: result.response,
        consumed: result.consumed,
        elapsedMs: Math.max(1, nowMs() - started),
        timeoutMs: timeoutMs
      };
    } catch (error) {
      var reason = timedOut ? "timeout after " + String(timeoutMs) + "ms" : "Network error during probe request.";
      if (!timedOut && error && error.message) {
        reason = String(error.message);
      }

      return {
        ok: false,
        error: error,
        timedOut: timedOut || !!(error && error.name === "AbortError"),
        reason: reason,
        elapsedMs: Math.max(1, nowMs() - started),
        timeoutMs: timeoutMs
      };
    } finally {
      if (timeoutId !== null) {
        clearTimeout(timeoutId);
      }
    }
  }

  function createDownloadConsume() {
    return function (response) {
      if (!response || !response.ok) {
        return parseJsonSafely(response).then(function (payload) {
          return {
            bytes: null,
            payload: payload
          };
        });
      }
      return response.arrayBuffer().then(function (buffer) {
        var byteLength = buffer && typeof buffer.byteLength === "number" ? buffer.byteLength : 0;
        return {
          bytes: byteLength,
          payload: null
        };
      });
    };
  }

  function runDownloadLikeProbe(config) {
    return executeFetchProbe({
      url: config.url,
      method: "GET",
      timeoutMs: config.timeoutMs,
      headers: {
        Accept: "application/octet-stream"
      },
      consume: createDownloadConsume()
    }).then(function (outcome) {
      var measuredBytes = 0;
      if (outcome.ok && outcome.consumed && typeof outcome.consumed.bytes === "number") {
        measuredBytes = outcome.consumed.bytes;
      }

      if (!outcome.ok) {
        return buildWarnResult(
          config.warnPrefix,
          measuredBytes,
          outcome.elapsedMs,
          "target_bytes=" + String(config.bytes)
            + ". reason=" + outcome.reason
            + ". timeout_ms=" + String(outcome.timeoutMs) + ".",
          config.warnFixHint
        );
      }

      var statusCode = outcome.response && typeof outcome.response.status === "number"
        ? outcome.response.status
        : 0;
      if (!outcome.response || !outcome.response.ok) {
        var payload = outcome.consumed && outcome.consumed.payload ? outcome.consumed.payload : null;
        var errorCode = extractErrorCode(payload);
        var detail = "http_status=" + String(statusCode || "unknown") + ".";
        if (errorCode) {
          detail += " error_code=" + errorCode + ".";
        }
        return buildWarnResult(
          config.warnPrefix,
          measuredBytes,
          outcome.elapsedMs,
          "target_bytes=" + String(config.bytes) + ". " + detail,
          config.warnFixHint
        );
      }

      return buildPassResult(
        config.passPrefix,
        measuredBytes,
        outcome.elapsedMs,
        config.passDetail
      );
    });
  }

  function makeUploadPayload(bytes) {
    var size = normalizeByteCount(bytes, DEFAULT_UPLOAD_BYTES);
    var payload = new Uint8Array(size);
    var idx;
    for (idx = 0; idx < payload.length; idx += 1) {
      payload[idx] = idx % 251;
    }
    return payload;
  }

  function runRttProbe() {
    if (isSaveDataEnabled()) {
      return Promise.resolve(saveDataSkippedResult(RTT_PROBE_BYTES));
    }

    return runDownloadLikeProbe({
      url: "/query-engine/diagnostics/bandwidth/download?bytes=" + String(RTT_PROBE_BYTES),
      bytes: RTT_PROBE_BYTES,
      timeoutMs: RTT_TIMEOUT_MS,
      passPrefix: "RTT probe completed.",
      passDetail: "rtt_ms approximated by elapsed_ms.",
      warnPrefix: "RTT probe warning.",
      warnFixHint: "This is informational only. Retry diagnostics when network conditions stabilize."
    });
  }

  function runDownloadProbe() {
    if (isSaveDataEnabled()) {
      return Promise.resolve(saveDataSkippedResult(DEFAULT_DOWNLOAD_BYTES));
    }

    return runDownloadLikeProbe({
      url: "/query-engine/diagnostics/bandwidth/download?bytes=" + String(DEFAULT_DOWNLOAD_BYTES),
      bytes: DEFAULT_DOWNLOAD_BYTES,
      timeoutMs: DOWNLOAD_TIMEOUT_MS,
      passPrefix: "Download probe completed.",
      passDetail: "Target_bytes=" + String(DEFAULT_DOWNLOAD_BYTES) + ".",
      warnPrefix: "Download probe warning.",
      warnFixHint: "This is informational only. Retry diagnostics later or on a less constrained connection."
    });
  }

  function runUploadProbe() {
    if (isSaveDataEnabled()) {
      return Promise.resolve(saveDataSkippedResult(DEFAULT_UPLOAD_BYTES));
    }

    var payload = makeUploadPayload(DEFAULT_UPLOAD_BYTES);
    return executeFetchProbe({
      url: "/query-engine/diagnostics/bandwidth/upload",
      method: "POST",
      timeoutMs: UPLOAD_TIMEOUT_MS,
      headers: {
        "Content-Type": "application/octet-stream",
        Accept: "application/json"
      },
      body: payload,
      consume: function (response) {
        return parseJsonSafely(response).then(function (jsonPayload) {
          return {
            payload: jsonPayload
          };
        });
      }
    }).then(function (outcome) {
      var reportedPayload = outcome.ok && outcome.consumed && outcome.consumed.payload
        ? outcome.consumed.payload
        : null;
      var measuredBytes = 0;
      if (
        reportedPayload
        && typeof reportedPayload.bytes_received === "number"
        && Number.isFinite(reportedPayload.bytes_received)
      ) {
        measuredBytes = normalizeByteCount(reportedPayload.bytes_received, DEFAULT_UPLOAD_BYTES);
      }

      if (!outcome.ok) {
        return buildWarnResult(
          "Upload probe warning.",
          measuredBytes,
          outcome.elapsedMs,
          "target_bytes=" + String(DEFAULT_UPLOAD_BYTES)
            + ". reason=" + outcome.reason
            + ". timeout_ms=" + String(outcome.timeoutMs) + ".",
          "This is informational only. Retry diagnostics when upload bandwidth is less constrained."
        );
      }

      var statusCode = outcome.response && typeof outcome.response.status === "number"
        ? outcome.response.status
        : 0;
      if (!outcome.response || !outcome.response.ok) {
        var code = extractErrorCode(reportedPayload);
        var detail = "http_status=" + String(statusCode || "unknown") + ".";
        if (code) {
          detail += " error_code=" + code + ".";
        }
        return buildWarnResult(
          "Upload probe warning.",
          measuredBytes,
          outcome.elapsedMs,
          "target_bytes=" + String(DEFAULT_UPLOAD_BYTES) + ". " + detail,
          "This is informational only. Non-2xx upload probe responses do not block readiness."
        );
      }

      var serverElapsedMs = "";
      if (reportedPayload && typeof reportedPayload.elapsed_ms === "number" && Number.isFinite(reportedPayload.elapsed_ms)) {
        serverElapsedMs = " server_elapsed_ms=" + String(Math.trunc(reportedPayload.elapsed_ms)) + ".";
      }

      return buildPassResult(
        "Upload probe completed.",
        measuredBytes,
        outcome.elapsedMs,
        "Target_bytes=" + String(DEFAULT_UPLOAD_BYTES) + "." + serverElapsedMs
      );
    });
  }

  var bandwidthChecks = [
    {
      id: "bandwidth-rtt",
      title: "RTT probe (approximate)",
      severity: "info",
      fix_hint: "Bandwidth probes are informational and environment-dependent.",
      run: runRttProbe
    },
    {
      id: "bandwidth-download",
      title: "Bandwidth download probe (approximate)",
      severity: "info",
      fix_hint: "Bandwidth probes are informational and environment-dependent.",
      run: runDownloadProbe
    },
    {
      id: "bandwidth-upload",
      title: "Bandwidth upload probe (approximate)",
      severity: "info",
      fix_hint: "Bandwidth probes are informational and environment-dependent.",
      run: runUploadProbe
    }
  ];

  function registerWithCore() {
    var core = root.WEPPDiagnosticsCore;
    if (core && typeof core.registerChecks === "function") {
      core.registerChecks(bandwidthChecks);
      return;
    }

    if (!Array.isArray(root.__weppDiagnosticsPendingChecks)) {
      root.__weppDiagnosticsPendingChecks = [];
    }

    var idx;
    for (idx = 0; idx < bandwidthChecks.length; idx += 1) {
      root.__weppDiagnosticsPendingChecks.push(bandwidthChecks[idx]);
    }
  }

  registerWithCore();

  root.WEPPDiagnosticsBandwidthChecks = {
    checks: bandwidthChecks,
    defaults: {
      rttBytes: RTT_PROBE_BYTES,
      downloadBytes: DEFAULT_DOWNLOAD_BYTES,
      uploadBytes: DEFAULT_UPLOAD_BYTES,
      rttTimeoutMs: RTT_TIMEOUT_MS,
      downloadTimeoutMs: DOWNLOAD_TIMEOUT_MS,
      uploadTimeoutMs: UPLOAD_TIMEOUT_MS
    },
    _internals: {
      computeApproxMbps: computeApproxMbps,
      isSaveDataEnabled: isSaveDataEnabled,
      extractErrorCode: extractErrorCode,
      executeFetchProbe: executeFetchProbe
    }
  };
})(window);

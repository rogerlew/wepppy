(function () {
  "use strict";

  if (window.WCDiagnosticsRealtime) {
    return;
  }

  var DIAGNOSTICS_CHANNEL = "diagnostics";
  var MIN_PROBE_WINDOW_MS = 20000;
  var DEFAULT_HEALTH_PROBE_TIMEOUT_MS = 5000;
  var MAX_HEALTH_PROBE_TIMEOUT_MS = 20000;
  var MAX_RECONNECT_RETRIES = 1;
  var MAX_DIAG_RUN_ID_LENGTH = 64;
  var RUN_ID_PATTERN = /^[A-Za-z0-9_.;-]+$/;
  var DEFAULT_STATUS_CHECK_ID = "realtime-status-websocket";
  var DEFAULT_PREFLIGHT_CHECK_ID = "realtime-preflight-websocket";
  var DEFAULT_STATUS_HEALTH_CHECK_ID = "status-health-reachability";
  var DEFAULT_PREFLIGHT_HEALTH_CHECK_ID = "preflight-health-reachability";

  var registeredEngines = typeof WeakSet === "function" ? new WeakSet() : null;
  var registeredEngineList = [];
  var pageDiagRunId = null;

  function nowMs() {
    return Date.now();
  }

  function normalizeInt(value, fallback) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return Math.trunc(parsed);
  }

  function normalizeProbeWindowMs(value) {
    var requested = normalizeInt(value, MIN_PROBE_WINDOW_MS);
    if (requested < MIN_PROBE_WINDOW_MS) {
      return MIN_PROBE_WINDOW_MS;
    }
    return requested;
  }

  function normalizeReconnectRetries(value) {
    var retries = normalizeInt(value, MAX_RECONNECT_RETRIES);
    if (retries < 0) {
      return 0;
    }
    if (retries > MAX_RECONNECT_RETRIES) {
      return MAX_RECONNECT_RETRIES;
    }
    return retries;
  }

  function normalizeHealthProbeTimeoutMs(value) {
    var timeoutMs = normalizeInt(value, DEFAULT_HEALTH_PROBE_TIMEOUT_MS);
    if (timeoutMs < 500) {
      return 500;
    }
    if (timeoutMs > MAX_HEALTH_PROBE_TIMEOUT_MS) {
      return MAX_HEALTH_PROBE_TIMEOUT_MS;
    }
    return timeoutMs;
  }

  function stripInvalidRunIdCharacters(value) {
    if (!value) {
      return "";
    }
    var sanitized = String(value).replace(/:/g, "-");
    sanitized = sanitized.replace(/[^A-Za-z0-9_.;-]/g, "-");
    sanitized = sanitized.replace(/-+/g, "-");
    sanitized = sanitized.replace(/^-+|-+$/g, "");
    if (sanitized.length > MAX_DIAG_RUN_ID_LENGTH) {
      sanitized = sanitized.slice(0, MAX_DIAG_RUN_ID_LENGTH);
    }
    return sanitized;
  }

  function isValidDiagRunId(value) {
    if (!value || typeof value !== "string") {
      return false;
    }
    if (value.indexOf(":") !== -1) {
      return false;
    }
    if (value.length > MAX_DIAG_RUN_ID_LENGTH) {
      return false;
    }
    return RUN_ID_PATTERN.test(value);
  }

  function createRandomBase36(length) {
    var requestedLength = normalizeInt(length, 8);
    if (requestedLength < 4) {
      requestedLength = 4;
    }
    if (requestedLength > 16) {
      requestedLength = 16;
    }

    var output = "";

    if (window.crypto && typeof window.crypto.getRandomValues === "function") {
      var bytes = new Uint8Array(requestedLength);
      window.crypto.getRandomValues(bytes);
      for (var i = 0; i < bytes.length; i += 1) {
        output += (bytes[i] % 36).toString(36);
      }
      return output;
    }

    while (output.length < requestedLength) {
      output += Math.random().toString(36).slice(2);
    }

    return output.slice(0, requestedLength);
  }

  function createDiagRunId(options) {
    var opts = options || {};
    var candidate = stripInvalidRunIdCharacters(opts.diagRunId || "");
    if (isValidDiagRunId(candidate)) {
      return candidate;
    }

    var epochSeconds = Math.floor(nowMs() / 1000);
    var randomSuffix = createRandomBase36(opts.randomLength || 8);
    var generated = stripInvalidRunIdCharacters("diag-" + String(epochSeconds) + "-" + randomSuffix);

    if (!isValidDiagRunId(generated)) {
      generated = stripInvalidRunIdCharacters("diag-" + String(epochSeconds));
    }

    if (!isValidDiagRunId(generated)) {
      generated = "diag-" + String(epochSeconds);
    }

    return generated;
  }

  function getSharedDiagRunId(options) {
    var opts = options || {};
    if (opts.diagRunId && isValidDiagRunId(String(opts.diagRunId))) {
      return String(opts.diagRunId);
    }
    if (!pageDiagRunId) {
      pageDiagRunId = createDiagRunId(opts);
    }
    return pageDiagRunId;
  }

  function resolveLocation(options) {
    if (options && options.location) {
      return options.location;
    }
    if (typeof window !== "undefined" && window.location) {
      return window.location;
    }
    return {
      protocol: "http:",
      host: "localhost"
    };
  }

  function resolveWsProtocol(locationLike) {
    if (locationLike && locationLike.protocol === "https:") {
      return "wss:";
    }
    return "ws:";
  }

  function createStatusProbeUrl(diagRunId, options) {
    var locationLike = resolveLocation(options);
    var wsProtocol = resolveWsProtocol(locationLike);
    var encodedRunId = encodeURIComponent(diagRunId);
    return wsProtocol + "//" + String(locationLike.host || "")
      + "/weppcloud-microservices/status/" + encodedRunId + ":" + DIAGNOSTICS_CHANNEL;
  }

  function createPreflightProbeUrl(diagRunId, options) {
    var locationLike = resolveLocation(options);
    var wsProtocol = resolveWsProtocol(locationLike);
    var encodedRunId = encodeURIComponent(diagRunId);
    return wsProtocol + "//" + String(locationLike.host || "")
      + "/weppcloud-microservices/preflight/" + encodedRunId;
  }

  function createStatusHealthUrl() {
    return "/weppcloud-microservices/status/health";
  }

  function createPreflightHealthUrl() {
    return "/weppcloud-microservices/preflight/health";
  }

  function resolveSocketConstructor(options) {
    if (options && typeof options.WebSocket === "function") {
      return options.WebSocket;
    }
    if (typeof window !== "undefined" && typeof window.WebSocket === "function") {
      return window.WebSocket;
    }
    return null;
  }

  function resolveFetchFn(options) {
    if (options && typeof options.fetch === "function") {
      return options.fetch;
    }
    if (typeof window !== "undefined" && typeof window.fetch === "function") {
      return window.fetch.bind(window);
    }
    return null;
  }

  function sendSocketMessage(socket, payload) {
    if (!socket || typeof socket.send !== "function") {
      return false;
    }
    try {
      socket.send(JSON.stringify(payload));
      return true;
    } catch (_error) {
      return false;
    }
  }

  function closeSocketQuietly(socket) {
    if (!socket || typeof socket.close !== "function") {
      return;
    }
    try {
      socket.close(1000, "diagnostics-probe-complete");
    } catch (_error) {
      // no-op
    }
  }

  function parseSocketMessageType(eventData) {
    if (typeof eventData !== "string") {
      return "";
    }

    var parsed = null;
    try {
      parsed = JSON.parse(eventData);
    } catch (_error) {
      return "";
    }

    if (!parsed || typeof parsed !== "object" || typeof parsed.type !== "string") {
      return "";
    }

    return parsed.type.toLowerCase();
  }

  function makeAttemptOutcome(summary) {
    return {
      ok: !!summary.ok,
      reason: String(summary.reason || ""),
      opened: !!summary.opened,
      sawPing: !!summary.sawPing,
      sawPreflight: !!summary.sawPreflight,
      durationMs: normalizeInt(summary.durationMs, 0),
      attempt: normalizeInt(summary.attempt, 1)
    };
  }

  function runProbeAttempt(config) {
    return new Promise(function (resolve) {
      var socket = null;
      var timerId = null;
      var settled = false;
      var opened = false;
      var sawPing = false;
      var sawPreflight = false;
      var startTime = nowMs();

      function complete(outcome) {
        if (settled) {
          return;
        }
        settled = true;

        if (timerId !== null) {
          clearTimeout(timerId);
          timerId = null;
        }

        closeSocketQuietly(socket);

        resolve(makeAttemptOutcome({
          ok: outcome.ok,
          reason: outcome.reason,
          opened: opened,
          sawPing: sawPing,
          sawPreflight: sawPreflight,
          durationMs: nowMs() - startTime,
          attempt: config.attempt
        }));
      }

      function fail(reason) {
        complete({
          ok: false,
          reason: reason
        });
      }

      function pass() {
        complete({
          ok: true,
          reason: "probe window complete"
        });
      }

      var SocketCtor = config.SocketCtor;
      if (!SocketCtor) {
        fail("WebSocket API is unavailable in this browser.");
        return;
      }

      try {
        socket = new SocketCtor(config.url);
      } catch (error) {
        fail("WebSocket construction failed: " + String(error && error.message ? error.message : error));
        return;
      }

      timerId = setTimeout(function () {
        if (!opened) {
          fail("timeout after " + String(config.probeWindowMs) + "ms before socket open");
          return;
        }
        if (!sawPing) {
          fail("timeout after " + String(config.probeWindowMs) + "ms without service ping frame");
          return;
        }
        if (config.requirePreflightFrame && !sawPreflight) {
          fail("timeout after " + String(config.probeWindowMs) + "ms without preflight frame");
          return;
        }
        pass();
      }, config.probeWindowMs);

      socket.onopen = function () {
        opened = true;
        if (!sendSocketMessage(socket, { type: "init" })) {
          fail("socket opened but init frame failed to send");
        }
      };

      socket.onmessage = function (event) {
        var messageType = parseSocketMessageType(event && event.data);
        if (!messageType) {
          return;
        }

        if (messageType === "ping") {
          sawPing = true;
          if (!sendSocketMessage(socket, { type: "pong" })) {
            fail("received ping but failed to send pong");
            return;
          }
        }

        if (messageType === "preflight") {
          sawPreflight = true;
        }
      };

      socket.onerror = function () {
        fail("socket error event");
      };

      socket.onclose = function (event) {
        if (settled) {
          return;
        }

        var reason = "socket closed";
        if (event && typeof event.code !== "undefined") {
          reason += " (code " + String(event.code) + ")";
        }
        if (event && event.reason) {
          reason += ": " + String(event.reason);
        }

        fail(reason);
      };
    });
  }

  async function runProbeWithRetry(config) {
    var attempts = [];
    var totalAttempts = 1 + normalizeReconnectRetries(config.reconnectRetries);

    for (var attempt = 1; attempt <= totalAttempts; attempt += 1) {
      var attemptOutcome = await runProbeAttempt({
        SocketCtor: config.SocketCtor,
        url: config.url,
        probeWindowMs: config.probeWindowMs,
        requirePreflightFrame: !!config.requirePreflightFrame,
        attempt: attempt
      });
      attempts.push(attemptOutcome);

      if (attemptOutcome.ok) {
        return {
          ok: true,
          attempts: attempts
        };
      }
    }

    return {
      ok: false,
      attempts: attempts
    };
  }

  function buildRetryEvidence(summary, options) {
    var attempts = summary.attempts || [];
    var probeWindowMs = options.probeWindowMs;

    if (!attempts.length) {
      return "No probe attempts were recorded.";
    }

    if (summary.ok) {
      if (attempts.length === 1) {
        return "Attempt 1 passed after " + String(probeWindowMs)
          + "ms probe window (ping/pong observed).";
      }
      return "Attempt 1 failed (" + attempts[0].reason
        + "); retried once and attempt 2 passed after " + String(probeWindowMs) + "ms.";
    }

    if (attempts.length === 1) {
      return "Attempt 1 failed: " + attempts[0].reason + ".";
    }

    return "Attempt 1 failed (" + attempts[0].reason
      + "); retried once and attempt 2 failed (" + attempts[1].reason + ").";
  }

  function buildCheckResult(check, status, evidence, fixHint, extra) {
    var payload = {
      id: check.id,
      title: check.title,
      severity: check.severity,
      status: status,
      evidence: evidence,
      fix_hint: fixHint
    };

    if (extra && typeof extra === "object") {
      for (var key in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, key)) {
          payload[key] = extra[key];
        }
      }
    }

    return payload;
  }

  function createStatusRealtimeCheck(shared) {
    return {
      id: DEFAULT_STATUS_CHECK_ID,
      title: "Status websocket connectivity",
      severity: "degraded",
      run: async function () {
        var SocketCtor = resolveSocketConstructor(shared);
        if (!SocketCtor) {
          return buildCheckResult(
            this,
            "fail",
            "Browser does not expose window.WebSocket; status realtime probe unavailable.",
            "Use a browser/runtime with WebSocket support enabled.",
            {
              diag_run_id: shared.diagRunId,
              probe_url: shared.statusUrl
            }
          );
        }

        var result = await runProbeWithRetry({
          SocketCtor: SocketCtor,
          url: shared.statusUrl,
          probeWindowMs: shared.probeWindowMs,
          reconnectRetries: shared.reconnectRetries,
          requirePreflightFrame: false
        });

        var evidence = buildRetryEvidence(result, {
          probeWindowMs: shared.probeWindowMs
        });
        evidence += " URL: " + shared.statusUrl;

        if (result.ok) {
          return buildCheckResult(this, "pass", evidence, "", {
            diag_run_id: shared.diagRunId,
            probe_url: shared.statusUrl,
            attempts: result.attempts.length
          });
        }

        return buildCheckResult(
          this,
          "fail",
          evidence,
          "Verify status2 service, websocket proxy route, and ping/pong traffic.",
          {
            diag_run_id: shared.diagRunId,
            probe_url: shared.statusUrl,
            attempts: result.attempts.length
          }
        );
      }
    };
  }

  function createPreflightRealtimeCheck(shared) {
    return {
      id: DEFAULT_PREFLIGHT_CHECK_ID,
      title: "Preflight websocket connectivity",
      severity: "degraded",
      run: async function () {
        var SocketCtor = resolveSocketConstructor(shared);
        if (!SocketCtor) {
          return buildCheckResult(
            this,
            "fail",
            "Browser does not expose window.WebSocket; preflight realtime probe unavailable.",
            "Use a browser/runtime with WebSocket support enabled.",
            {
              diag_run_id: shared.diagRunId,
              probe_url: shared.preflightUrl
            }
          );
        }

        var result = await runProbeWithRetry({
          SocketCtor: SocketCtor,
          url: shared.preflightUrl,
          probeWindowMs: shared.probeWindowMs,
          reconnectRetries: shared.reconnectRetries,
          requirePreflightFrame: true
        });

        var evidence = buildRetryEvidence(result, {
          probeWindowMs: shared.probeWindowMs
        });
        evidence += " URL: " + shared.preflightUrl;

        if (result.ok) {
          return buildCheckResult(this, "pass", evidence, "", {
            diag_run_id: shared.diagRunId,
            probe_url: shared.preflightUrl,
            attempts: result.attempts.length
          });
        }

        return buildCheckResult(
          this,
          "fail",
          evidence,
          "Verify preflight2 service, websocket proxy route, and checklist frame publishing.",
          {
            diag_run_id: shared.diagRunId,
            probe_url: shared.preflightUrl,
            attempts: result.attempts.length
          }
        );
      }
    };
  }

  async function runHealthReachabilityProbe(config) {
    if (!config.fetchFn) {
      return {
        ok: false,
        statusCode: 0,
        reason: "Fetch API is unavailable in this browser runtime."
      };
    }

    var timeoutMs = normalizeHealthProbeTimeoutMs(config.timeoutMs);
    var timeoutHandle = null;
    var timedOut = false;
    var AbortCtor = typeof AbortController === "function" ? AbortController : null;
    var abortController = AbortCtor ? new AbortCtor() : null;

    var requestOptions = {
      method: "GET",
      credentials: "omit",
      cache: "no-store"
    };
    if (abortController) {
      requestOptions.signal = abortController.signal;
    }

    try {
      var timeoutPromise = new Promise(function (_resolve, reject) {
        timeoutHandle = setTimeout(function () {
          timedOut = true;
          if (abortController && typeof abortController.abort === "function") {
            abortController.abort();
          }
          reject(new Error("timeout"));
        }, timeoutMs);
      });

      var response = await Promise.race([
        config.fetchFn(config.url, requestOptions),
        timeoutPromise
      ]);
      var statusCode = response && typeof response.status === "number" ? response.status : 0;
      if (response && response.ok) {
        return {
          ok: true,
          statusCode: statusCode
        };
      }
      return {
        ok: false,
        statusCode: statusCode,
        reason: "HTTP " + String(statusCode || "unknown")
      };
    } catch (error) {
      if (timedOut || (error && error.name === "AbortError")) {
        return {
          ok: false,
          statusCode: 0,
          reason: "timeout after " + String(timeoutMs) + "ms"
        };
      }
      return {
        ok: false,
        statusCode: 0,
        reason: "Network error: " + String(error && error.message ? error.message : error)
      };
    } finally {
      if (timeoutHandle !== null) {
        clearTimeout(timeoutHandle);
      }
    }
  }

  function createStatusHealthCheck(shared) {
    return {
      id: DEFAULT_STATUS_HEALTH_CHECK_ID,
      title: "Status service health reachability",
      severity: "degraded",
      run: async function () {
        var result = await runHealthReachabilityProbe({
          fetchFn: resolveFetchFn(shared),
          url: shared.statusHealthUrl,
          timeoutMs: shared.healthProbeTimeoutMs
        });

        if (result.ok) {
          return buildCheckResult(
            this,
            "pass",
            "GET " + shared.statusHealthUrl + " returned HTTP " + String(result.statusCode || 200) + ".",
            ""
          );
        }

        return buildCheckResult(
          this,
          "fail",
          "GET " + shared.statusHealthUrl + " failed: " + result.reason + ".",
          "Confirm status2 is running and the /weppcloud-microservices/status/* proxy route targets it."
        );
      }
    };
  }

  function createPreflightHealthCheck(shared) {
    return {
      id: DEFAULT_PREFLIGHT_HEALTH_CHECK_ID,
      title: "Preflight service health reachability",
      severity: "degraded",
      run: async function () {
        var result = await runHealthReachabilityProbe({
          fetchFn: resolveFetchFn(shared),
          url: shared.preflightHealthUrl,
          timeoutMs: shared.healthProbeTimeoutMs
        });

        if (result.ok) {
          return buildCheckResult(
            this,
            "pass",
            "GET " + shared.preflightHealthUrl + " returned HTTP " + String(result.statusCode || 200) + ".",
            ""
          );
        }

        return buildCheckResult(
          this,
          "fail",
          "GET " + shared.preflightHealthUrl + " failed: " + result.reason + ".",
          "Confirm preflight2 is running and the /weppcloud-microservices/preflight/* proxy route targets it."
        );
      }
    };
  }

  function buildRealtimeChecks(options) {
    var opts = options || {};
    var diagRunId = getSharedDiagRunId(opts);
    if (!isValidDiagRunId(diagRunId)) {
      diagRunId = createDiagRunId(opts);
      pageDiagRunId = diagRunId;
    }

    var shared = {
      diagRunId: diagRunId,
      statusUrl: createStatusProbeUrl(diagRunId, opts),
      preflightUrl: createPreflightProbeUrl(diagRunId, opts),
      statusHealthUrl: createStatusHealthUrl(),
      preflightHealthUrl: createPreflightHealthUrl(),
      probeWindowMs: normalizeProbeWindowMs(opts.probeWindowMs),
      healthProbeTimeoutMs: normalizeHealthProbeTimeoutMs(opts.healthProbeTimeoutMs),
      reconnectRetries: normalizeReconnectRetries(opts.reconnectRetries),
      WebSocket: opts.WebSocket,
      location: opts.location,
      fetch: opts.fetch
    };

    return {
      diagRunId: diagRunId,
      checks: [
        createStatusRealtimeCheck(shared),
        createPreflightRealtimeCheck(shared),
        createStatusHealthCheck(shared),
        createPreflightHealthCheck(shared)
      ]
    };
  }

  function hasRegisteredEngine(engine) {
    if (!engine || typeof engine !== "object") {
      return false;
    }
    if (registeredEngines) {
      return registeredEngines.has(engine);
    }
    return registeredEngineList.indexOf(engine) !== -1;
  }

  function markEngineRegistered(engine) {
    if (!engine || typeof engine !== "object") {
      return;
    }
    if (registeredEngines) {
      registeredEngines.add(engine);
      return;
    }
    if (registeredEngineList.indexOf(engine) === -1) {
      registeredEngineList.push(engine);
    }
  }

  function resolveDiagnosticsEngine(explicitEngine) {
    if (explicitEngine && typeof explicitEngine === "object") {
      return explicitEngine;
    }
    if (window.WCDiagnostics && typeof window.WCDiagnostics === "object") {
      return window.WCDiagnostics;
    }
    return null;
  }

  function registerChecksWithEngine(engine, checks) {
    if (!engine || !checks || !checks.length) {
      return false;
    }

    if (typeof engine.registerChecks === "function") {
      engine.registerChecks(checks);
      return true;
    }

    if (typeof engine.registerCheck === "function") {
      for (var i = 0; i < checks.length; i += 1) {
        engine.registerCheck(checks[i]);
      }
      return true;
    }

    if (typeof engine.addCheck === "function") {
      for (var j = 0; j < checks.length; j += 1) {
        engine.addCheck(checks[j]);
      }
      return true;
    }

    return false;
  }

  function queuePendingChecks(checks) {
    if (!checks || !checks.length) {
      return 0;
    }

    if (!Array.isArray(window.__wcDiagnosticsPendingChecks)) {
      window.__wcDiagnosticsPendingChecks = [];
    }

    var queue = window.__wcDiagnosticsPendingChecks;
    var count = 0;

    for (var i = 0; i < checks.length; i += 1) {
      var check = checks[i];
      if (!check || typeof check.id !== "string") {
        continue;
      }

      var alreadyQueued = false;
      for (var q = 0; q < queue.length; q += 1) {
        if (queue[q] && queue[q].id === check.id) {
          alreadyQueued = true;
          break;
        }
      }
      if (alreadyQueued) {
        continue;
      }

      queue.push(check);
      count += 1;
    }

    return count;
  }

  function registerRealtimeChecks(explicitEngine, options) {
    var engine = resolveDiagnosticsEngine(explicitEngine);
    var buildResult = buildRealtimeChecks(options || {});

    if (!engine) {
      var queuedCount = queuePendingChecks(buildResult.checks);
      return {
        registered: false,
        diagRunId: buildResult.diagRunId,
        checks: buildResult.checks,
        queued: queuedCount > 0
      };
    }

    if (hasRegisteredEngine(engine)) {
      return {
        registered: false,
        diagRunId: buildResult.diagRunId,
        checks: buildResult.checks,
        reason: "already-registered"
      };
    }

    var registered = registerChecksWithEngine(engine, buildResult.checks);
    if (registered) {
      markEngineRegistered(engine);
    }

    return {
      registered: registered,
      diagRunId: buildResult.diagRunId,
      checks: buildResult.checks
    };
  }

  function installEngineReadyListener() {
    if (typeof document === "undefined" || typeof document.addEventListener !== "function") {
      return;
    }

    document.addEventListener("wc:diagnostics:engine-ready", function (event) {
      var detail = event && event.detail ? event.detail : null;
      var engine = detail && detail.engine ? detail.engine : null;
      registerRealtimeChecks(engine || null, null);
    });
  }

  var api = {
    DIAGNOSTICS_CHANNEL: DIAGNOSTICS_CHANNEL,
    MIN_PROBE_WINDOW_MS: MIN_PROBE_WINDOW_MS,
    MAX_RECONNECT_RETRIES: MAX_RECONNECT_RETRIES,
    isValidDiagRunId: isValidDiagRunId,
    createDiagRunId: createDiagRunId,
    createStatusProbeUrl: createStatusProbeUrl,
    createPreflightProbeUrl: createPreflightProbeUrl,
    createStatusHealthUrl: createStatusHealthUrl,
    createPreflightHealthUrl: createPreflightHealthUrl,
    buildRealtimeChecks: buildRealtimeChecks,
    registerRealtimeChecks: registerRealtimeChecks,
    _internals: {
      runProbeAttempt: runProbeAttempt,
      runProbeWithRetry: runProbeWithRetry,
      buildRetryEvidence: buildRetryEvidence,
      getSharedDiagRunId: getSharedDiagRunId,
      normalizeProbeWindowMs: normalizeProbeWindowMs,
      normalizeReconnectRetries: normalizeReconnectRetries,
      normalizeHealthProbeTimeoutMs: normalizeHealthProbeTimeoutMs
    }
  };

  window.WCDiagnosticsRealtime = api;

  registerRealtimeChecks(null, null);
  installEngineReadyListener();
})();

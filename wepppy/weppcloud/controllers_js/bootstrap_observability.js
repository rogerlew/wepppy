/* ----------------------------------------------------------------------------
 * Bootstrap Observability Helpers
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var DEFAULT_MAX_STACK_LINES = 80;
    var DEFAULT_MAX_RECORDER_EVENTS = 8;
    var DEFAULT_MAX_ERROR_KEYS = 256;
    var DEFAULT_UPGRADE_BUDGET = 1;

    var SECRET_KEYS = [
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "key",
        "api_key",
        "apikey",
        "api-key",
        "x-api-key",
        "authorization",
        "set-cookie",
        "cookie",
        "session",
        "email",
        "auth",
        "x-auth-token",
        "x-csrf-token"
    ];
    var SECRET_KEYS_ALT = SECRET_KEYS.join("|");
    var SECRET_HEADER_KEYS = [
        "authorization",
        "set-cookie",
        "cookie",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-csrf-token"
    ];
    var SECRET_HEADER_KEYS_ALT = SECRET_HEADER_KEYS.join("|");

    function splitErrorLines(value) {
        if (value === undefined || value === null) {
            return [];
        }
        if (Array.isArray(value)) {
            var lines = [];
            value.forEach(function (entry) {
                if (entry === undefined || entry === null) {
                    return;
                }
                String(entry).split(/\r?\n/).forEach(function (line) {
                    if (line !== "") {
                        lines.push(line);
                    }
                });
            });
            return lines;
        }
        if (typeof value === "string") {
            return value.split(/\r?\n/).filter(function (line) {
                return line !== "";
            });
        }
        return splitErrorLines(String(value));
    }

    function sanitizeDiagnosticLine(line) {
        var text = String(line === undefined || line === null ? "" : line);
        text = text.replace(new RegExp(
            "\\b(" + SECRET_HEADER_KEYS_ALT + ")\\b\\s*:\\s*[^\\r\\n]*",
            "gi"
        ), "$1: [redacted]");
        text = text.replace(/\bauthorization\b\s*=\s*[^\r\n]*/gi, "authorization=[redacted]");
        text = text.replace(/\b(set-cookie|cookie)\b\s*=\s*[^\r\n]*/gi, "$1=[redacted]");
        text = text.replace(new RegExp(
            "\\b(" + SECRET_HEADER_KEYS_ALT + ")\\b\\s*=\\s*[^\\r\\n\\s,;]+",
            "gi"
        ), "$1=[redacted]");
        text = text.replace(
            /\bauthorization\b\s+(?:Bearer|Token)\s+[^\s,;]+/gi,
            "authorization [redacted]"
        );
        text = text.replace(/\b(Bearer|Token)\s+[A-Za-z0-9._~+\/-]+=*/gi, "$1 [redacted]");
        text = text.replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[redacted-email]");
        text = text.replace(
            new RegExp(
                "((?:\\\\[\\\"'])?(?:" + SECRET_KEYS_ALT + ")(?:\\\\[\\\"'])?\\s*:\\s*(?:\\\\[\\\"']))([^\\\\]*?)((?:\\\\[\\\"']))",
                "gi"
            ),
            "$1[redacted]$3"
        );
        text = text.replace(
            new RegExp(
                "((?:\\\\?[\\\"'])?(?:" + SECRET_KEYS_ALT + ")(?:\\\\?[\\\"'])?\\s*:\\s*(?:\\\\?[\\\"']))([^\\\"\\\\]*?)((?:\\\\?[\\\"']))",
                "gi"
            ),
            "$1[redacted]$3"
        );
        text = text.replace(
            new RegExp(
                "([?&](?:" + SECRET_KEYS_ALT + ")=)([^&\\s#]+)",
                "gi"
            ),
            "$1[redacted]"
        );
        text = text.replace(
            new RegExp(
                "(\\b(?:" + SECRET_KEYS_ALT + ")\\b\\s*=\\s*)([^\\s,;&]+)",
                "gi"
            ),
            "$1[redacted]"
        );
        text = text.replace(
            new RegExp(
                "(\\b(?:" + SECRET_KEYS_ALT + ")\\b\\s*:\\s*)([^,\\s}&]+)",
                "gi"
            ),
            "$1[redacted]"
        );
        return text;
    }

    function sanitizeDiagnosticLines(lines) {
        return (Array.isArray(lines) ? lines : []).map(function (line) {
            return sanitizeDiagnosticLine(line);
        });
    }

    function resolveBootstrapErrorMessage(err) {
        if (err === undefined || err === null) {
            return "";
        }
        if (typeof err === "string") {
            return err;
        }
        if (typeof err === "number" || typeof err === "boolean" || typeof err === "bigint") {
            return String(err);
        }
        if (typeof err === "object") {
            if (typeof err.message === "string" && err.message !== "") {
                return err.message;
            }
            if (typeof err.detail === "string" && err.detail !== "") {
                return err.detail;
            }
        }
        try {
            return String(err);
        } catch (stringifyErr) {
            return "";
        }
    }

    function resolveBootstrapStack(err, maxStackLines) {
        var maxLines = typeof maxStackLines === "number" && maxStackLines > 0
            ? maxStackLines
            : DEFAULT_MAX_STACK_LINES;
        var stack = [];
        if (err && err.stack) {
            stack = splitErrorLines(err.stack);
        }
        if (!stack.length && err && err.detail) {
            stack = splitErrorLines(err.detail);
        }
        if (!stack.length) {
            stack = splitErrorLines(resolveBootstrapErrorMessage(err));
        }
        if (stack.length > maxLines) {
            stack = stack.slice(0, maxLines);
            stack.push("... [truncated]");
        }
        return stack;
    }

    function formatBootstrapErrorMessage(summary, err, meta, maxStackLines) {
        var lines = [];
        lines.push("[bootstrap] " + summary);
        if (meta && meta.stage) {
            lines.push("stage=" + meta.stage);
        }
        if (meta && meta.controller) {
            lines.push("controller=" + meta.controller);
        }
        var message = resolveBootstrapErrorMessage(err);
        if (message) {
            lines.push("message=" + sanitizeDiagnosticLine(message));
        }
        var stack = resolveBootstrapStack(err, maxStackLines);
        if (stack.length) {
            lines.push("stacktrace:");
            stack.forEach(function (line) {
                lines.push(sanitizeDiagnosticLine(line));
            });
        }
        return lines.join("\n");
    }

    function bootstrapErrorKey(summary, err, meta) {
        return [
            summary || "",
            meta && meta.stage ? meta.stage : "",
            meta && meta.controller ? meta.controller : "",
            resolveBootstrapErrorMessage(err)
        ].join("|");
    }

    function bootstrapSpecificity(meta) {
        if (meta && meta.controller) {
            return 2;
        }
        return 1;
    }

    function createBootstrapErrorNotifier(options) {
        var opts = options || {};
        var logger = opts.logger || (global.console || {});
        var maxStackLines = typeof opts.maxStackLines === "number" && opts.maxStackLines > 0
            ? opts.maxStackLines
            : DEFAULT_MAX_STACK_LINES;
        var maxRecorderEvents = typeof opts.maxRecorderEvents === "number" && opts.maxRecorderEvents > 0
            ? opts.maxRecorderEvents
            : DEFAULT_MAX_RECORDER_EVENTS;
        var maxErrorKeys = typeof opts.maxErrorKeys === "number" && opts.maxErrorKeys > 0
            ? opts.maxErrorKeys
            : DEFAULT_MAX_ERROR_KEYS;
        var commandBarFactory = typeof opts.commandBarFactory === "function" ? opts.commandBarFactory : function () { return null; };
        var recorderFactory = typeof opts.recorderFactory === "function"
            ? opts.recorderFactory
            : function () { return opts.recorder || null; };

        var errorKeys = {};
        var errorKeyOrder = [];
        var recorderEventCount = 0;
        var recorderOverflowNotified = false;
        var commandBarShown = false;
        var commandBarSpecificity = 0;
        var commandBarUpgradeBudget = DEFAULT_UPGRADE_BUDGET;

        function shouldShowCommandBar(meta) {
            var specificity = bootstrapSpecificity(meta);
            if (!commandBarShown) {
                commandBarSpecificity = specificity;
                return true;
            }
            if (specificity > commandBarSpecificity && commandBarUpgradeBudget > 0) {
                commandBarUpgradeBudget -= 1;
                commandBarSpecificity = specificity;
                return true;
            }
            return false;
        }

        function notify(summary, err, meta) {
            var key = bootstrapErrorKey(summary, err, meta);
            if (errorKeys[key]) {
                return { deduped: true };
            }
            errorKeys[key] = true;
            errorKeyOrder.push(key);
            if (errorKeyOrder.length > maxErrorKeys) {
                var oldestKey = errorKeyOrder.shift();
                if (oldestKey !== undefined) {
                    delete errorKeys[oldestKey];
                }
            }

            var diagnostic = formatBootstrapErrorMessage(summary, err, meta, maxStackLines);
            var commandBarNotified = false;
            var recorderNotified = false;
            if (shouldShowCommandBar(meta)) {
                try {
                    var commandBar = commandBarFactory();
                    if (commandBar && typeof commandBar.showResult === "function") {
                        commandBar.showResult(diagnostic);
                        commandBarShown = true;
                        commandBarNotified = true;
                    }
                } catch (commandBarErr) {
                    if (logger && typeof logger.warn === "function") {
                        logger.warn("[Bootstrap] Failed to notify command bar", commandBarErr);
                    }
                }
            }

            var recorder = null;
            try {
                recorder = recorderFactory();
            } catch (recorderFactoryErr) {
                if (logger && typeof logger.warn === "function") {
                    logger.warn("[Bootstrap] Failed to resolve recorder for bootstrap error", recorderFactoryErr);
                }
            }

            if (recorder && typeof recorder.emit === "function") {
                if (recorderEventCount >= maxRecorderEvents) {
                    if (!recorderOverflowNotified) {
                        if (logger && typeof logger.warn === "function") {
                            logger.warn("[Bootstrap] Suppressing additional recorder bootstrap errors");
                        }
                        recorderOverflowNotified = true;
                    }
                } else {
                    var resolvedStack = resolveBootstrapStack(err, maxStackLines);
                    var sanitizedStack = sanitizeDiagnosticLines(resolvedStack);
                    var sanitizedMessage = sanitizeDiagnosticLine(resolveBootstrapErrorMessage(err));
                    try {
                        recorder.emit("bootstrap_error", {
                            category: "controller-bootstrap",
                            summary: summary,
                            stage: meta && meta.stage ? meta.stage : null,
                            controller: meta && meta.controller ? meta.controller : null,
                            message: sanitizedMessage || null,
                            stacktrace: sanitizedStack
                        });
                        recorderEventCount += 1;
                        recorderNotified = true;
                    } catch (recorderErr) {
                        if (logger && typeof logger.warn === "function") {
                            logger.warn("[Bootstrap] Failed to emit recorder bootstrap error", recorderErr);
                        }
                    }
                }
            }

            if (!commandBarNotified && !recorderNotified) {
                if (logger && typeof logger.error === "function") {
                    logger.error(diagnostic);
                } else if (logger && typeof logger.warn === "function") {
                    logger.warn(diagnostic);
                }
            }

            return { deduped: false };
        }

        return {
            notify: notify
        };
    }

    global.WCBootstrapObservability = {
        splitErrorLines: splitErrorLines,
        sanitizeDiagnosticLine: sanitizeDiagnosticLine,
        sanitizeDiagnosticLines: sanitizeDiagnosticLines,
        resolveBootstrapStack: resolveBootstrapStack,
        formatBootstrapErrorMessage: formatBootstrapErrorMessage,
        createBootstrapErrorNotifier: createBootstrapErrorNotifier
    };
}(typeof globalThis !== "undefined" ? globalThis : window));

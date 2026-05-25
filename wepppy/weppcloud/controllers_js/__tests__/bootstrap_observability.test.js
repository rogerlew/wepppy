/**
 * @jest-environment jsdom
 */

describe("bootstrap observability helpers", () => {
    beforeEach(async () => {
        jest.resetModules();
        await import("../bootstrap_observability.js");
    });

    afterEach(() => {
        delete window.WCBootstrapObservability;
    });

    test("sanitizeDiagnosticLine redacts headers, query keys, and quoted secret fields", () => {
        const api = window.WCBootstrapObservability;
        const plain = '{"access_token":"abc123","authorization":"Bearer topsecret","email":"person@example.com"}';
        const escaped = '\\"session\\":\\"raw-session-token\\"';
        const escapedApiKey = '\\"x-api-key\\":\\"raw-api-key\\"';
        const query = "GET /endpoint?key=abc123&x-api-key=def456";
        const authHeader = "authorization: Bearer abc.def";
        const authBare = "authorization Bearer abc.def";
        const cookieHeader = "cookie: sessionid=abc; csrftoken=def; _ga=xyz";
        const setCookieHeader = "set-cookie: sessionid=abc; HttpOnly; Secure";
        const authEquals = "authorization=Bearer abc.def";
        const cookieEquals = "cookie=sessionid=abc; csrftoken=def";

        const plainSanitized = api.sanitizeDiagnosticLine(plain);
        const escapedSanitized = api.sanitizeDiagnosticLine(escaped);
        const escapedApiKeySanitized = api.sanitizeDiagnosticLine(escapedApiKey);
        const querySanitized = api.sanitizeDiagnosticLine(query);
        const authHeaderSanitized = api.sanitizeDiagnosticLine(authHeader);
        const authBareSanitized = api.sanitizeDiagnosticLine(authBare);
        const cookieHeaderSanitized = api.sanitizeDiagnosticLine(cookieHeader);
        const setCookieHeaderSanitized = api.sanitizeDiagnosticLine(setCookieHeader);
        const authEqualsSanitized = api.sanitizeDiagnosticLine(authEquals);
        const cookieEqualsSanitized = api.sanitizeDiagnosticLine(cookieEquals);

        expect(plainSanitized).toContain('"access_token":"[redacted]"');
        expect(plainSanitized).toContain('"authorization":"[redacted]"');
        expect(plainSanitized).not.toContain("abc123");
        expect(plainSanitized).not.toContain("topsecret");
        expect(plainSanitized).not.toContain("person@example.com");

        expect(escapedSanitized).toContain('\\"session\\":\\"[redacted]\\"');
        expect(escapedSanitized).not.toContain("raw-session-token");

        expect(escapedApiKeySanitized).toContain('\\"x-api-key\\":\\"[redacted]\\"');
        expect(escapedApiKeySanitized).not.toContain("raw-api-key");
        expect(querySanitized).toContain("?key=[redacted]");
        expect(querySanitized).toContain("&x-api-key=[redacted]");
        expect(querySanitized).not.toContain("abc123");
        expect(querySanitized).not.toContain("def456");
        expect(authHeaderSanitized).toBe("authorization: [redacted]");
        expect(authBareSanitized).toBe("authorization [redacted]");
        expect(cookieHeaderSanitized).toBe("cookie: [redacted]");
        expect(setCookieHeaderSanitized).toBe("set-cookie: [redacted]");
        expect(authEqualsSanitized).toBe("authorization=[redacted]");
        expect(authEqualsSanitized).not.toContain("abc.def");
        expect(cookieEqualsSanitized).toBe("cookie=[redacted]");
        expect(cookieEqualsSanitized).not.toContain("sessionid=abc");
        expect(cookieEqualsSanitized).not.toContain("csrftoken=def");
    });

    test("notifier dedupes, limits recorder events, and upgrades command-bar specificity once", () => {
        const api = window.WCBootstrapObservability;
        const commandBar = { showResult: jest.fn() };
        const recorder = { emit: jest.fn() };
        const logger = { warn: jest.fn() };
        const notifier = api.createBootstrapErrorNotifier({
            maxStackLines: 20,
            maxRecorderEvents: 2,
            commandBarFactory: () => commandBar,
            recorder: recorder,
            logger: logger
        });

        notifier.notify("Controller bootstrap failure", new Error("generic failure"), { stage: "bootstrapMany" });
        notifier.notify("Controller bootstrap failure", new Error("generic failure"), { stage: "bootstrapMany" });
        notifier.notify("Controller bootstrap failure", new Error("controller failure A"), {
            stage: "fallback",
            controller: "roads"
        });
        notifier.notify("Controller bootstrap failure", new Error("controller failure B"), {
            stage: "fallback",
            controller: "geneva"
        });

        expect(commandBar.showResult).toHaveBeenCalledTimes(2);
        expect(commandBar.showResult.mock.calls[0][0]).toContain("stage=bootstrapMany");
        expect(commandBar.showResult.mock.calls[1][0]).toContain("controller=roads");
        expect(recorder.emit).toHaveBeenCalledTimes(2);
        expect(logger.warn).toHaveBeenCalledWith("[Bootstrap] Suppressing additional recorder bootstrap errors");
    });

    test("notifier uses detail fallback for stack resolution and sanitizes emitted stacktrace", () => {
        const api = window.WCBootstrapObservability;
        const recorder = { emit: jest.fn() };
        const commandBar = { showResult: jest.fn() };
        const notifier = api.createBootstrapErrorNotifier({
            recorder: recorder,
            commandBarFactory: () => commandBar
        });

        notifier.notify(
            "Controller bootstrap failure",
            {
                message: "detail fallback",
                detail: 'trace line\nauthorization: Bearer abc\na\\\"session\\\":\\\"secret\\\"'
            },
            { stage: "fallback", controller: "project" }
        );

        expect(recorder.emit).toHaveBeenCalledTimes(1);
        const payload = recorder.emit.mock.calls[0][1];
        expect(payload.stacktrace).toEqual(expect.arrayContaining([
            expect.stringContaining("authorization: [redacted]"),
            expect.stringContaining('a\\\"session\\\":\\\"[redacted]\\\"')
        ]));
        expect(commandBar.showResult).toHaveBeenCalledWith(expect.stringContaining("authorization: [redacted]"));
        expect(commandBar.showResult).toHaveBeenCalledWith(expect.not.stringContaining("Bearer abc"));
    });

    test("notifier resolves recorder lazily on each notify call", () => {
        const api = window.WCBootstrapObservability;
        const recorder = { emit: jest.fn() };
        let activeRecorder = null;
        const notifier = api.createBootstrapErrorNotifier({
            recorderFactory: () => activeRecorder,
            commandBarFactory: () => null
        });

        notifier.notify("Controller bootstrap failure", new Error("before recorder"), { stage: "bootstrapMany" });
        activeRecorder = recorder;
        notifier.notify("Controller bootstrap failure", new Error("after recorder"), { stage: "bootstrapMany" });

        expect(recorder.emit).toHaveBeenCalledTimes(1);
        expect(recorder.emit).toHaveBeenCalledWith(
            "bootstrap_error",
            expect.objectContaining({
                message: "after recorder"
            })
        );
    });

    test("notifier normalizes primitive throw values for message, stack, and dedupe keys", () => {
        const api = window.WCBootstrapObservability;
        const recorder = { emit: jest.fn() };
        const commandBar = { showResult: jest.fn() };
        const notifier = api.createBootstrapErrorNotifier({
            recorder: recorder,
            commandBarFactory: () => commandBar
        });

        notifier.notify(
            "Controller bootstrap failure",
            "authorization=Bearer abc.def",
            { stage: "fallback", controller: "project" }
        );
        notifier.notify(
            "Controller bootstrap failure",
            "authorization=Bearer abc.def",
            { stage: "fallback", controller: "project" }
        );

        expect(commandBar.showResult).toHaveBeenCalledTimes(1);
        expect(commandBar.showResult).toHaveBeenCalledWith(
            expect.stringContaining("message=authorization=[redacted]")
        );
        expect(commandBar.showResult).toHaveBeenCalledWith(
            expect.stringContaining("stacktrace:\nauthorization=[redacted]")
        );
        expect(recorder.emit).toHaveBeenCalledTimes(1);
        expect(recorder.emit).toHaveBeenCalledWith(
            "bootstrap_error",
            expect.objectContaining({
                message: "authorization=[redacted]",
                stacktrace: expect.arrayContaining(["authorization=[redacted]"])
            })
        );
    });

    test("notifier logs sanitized diagnostic when no command bar or recorder sink is available", () => {
        const api = window.WCBootstrapObservability;
        const logger = { error: jest.fn() };
        const notifier = api.createBootstrapErrorNotifier({
            commandBarFactory: () => null,
            recorderFactory: () => null,
            logger: logger
        });

        notifier.notify(
            "Controller bootstrap failure",
            {
                message: "authorization=Bearer abc.def",
                detail: "cookie=sessionid=abc"
            },
            { stage: "fallback", controller: "project" }
        );

        expect(logger.error).toHaveBeenCalledTimes(1);
        const diagnostic = logger.error.mock.calls[0][0];
        expect(diagnostic).toContain("message=authorization=[redacted]");
        expect(diagnostic).toContain("cookie=[redacted]");
        expect(diagnostic).not.toContain("abc.def");
        expect(diagnostic).not.toContain("sessionid=abc");
    });

    test("notifier logs diagnostic when recorder suppression is active and command bar is unavailable", () => {
        const api = window.WCBootstrapObservability;
        const logger = { warn: jest.fn(), error: jest.fn() };
        const recorder = { emit: jest.fn() };
        const notifier = api.createBootstrapErrorNotifier({
            maxRecorderEvents: 1,
            recorder: recorder,
            commandBarFactory: () => null,
            logger: logger
        });

        notifier.notify("Controller bootstrap failure", new Error("first failure"), {
            stage: "fallback",
            controller: "alpha"
        });
        notifier.notify("Controller bootstrap failure", new Error("second failure"), {
            stage: "fallback",
            controller: "beta"
        });

        expect(logger.warn).toHaveBeenCalledWith("[Bootstrap] Suppressing additional recorder bootstrap errors");
        expect(logger.error).toHaveBeenCalledWith(expect.stringContaining("controller=beta"));
    });
});

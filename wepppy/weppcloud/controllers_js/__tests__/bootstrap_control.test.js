/**
 * @jest-environment jsdom
 */

describe("BootstrapControl", () => {
    let controller;
    let httpMock;
    let baseInstance;
    let delegateTeardowns;

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    function buildFixture() {
        document.body.innerHTML = `
            <form id="wepp_form">
                <div data-bootstrap-root>
                    <div class="wc-alert" data-bootstrap-message>
                        <p data-bootstrap-message-body></p>
                    </div>
                    <section data-bootstrap-disabled>
                        <button type="button" data-bootstrap-action="enable">Enable Bootstrap</button>
                    </section>
                    <section data-bootstrap-enabled hidden>
                        <textarea data-bootstrap-clone-command></textarea>
                        <textarea data-bootstrap-remote-command></textarea>
                        <code data-bootstrap-current-ref>—</code>
                        <select data-bootstrap-field="commit"></select>
                        <p data-bootstrap-commit-meta>—</p>
                        <button type="button" data-bootstrap-action="mint">Mint Token</button>
                        <button type="button" data-bootstrap-action="refresh">Refresh</button>
                        <button type="button" data-bootstrap-action="checkout">Checkout</button>
                        <button type="button" data-bootstrap-action="copy-clone">Copy Clone</button>
                        <button type="button" data-bootstrap-action="copy-remote">Copy Remote</button>
                        <button type="button" data-bootstrap-action="disable">Disable</button>
                    </section>
                </div>
            </form>
        `;
    }

    function installDomHelpers() {
        delegateTeardowns = [];
        global.WCDom = {
            qs: jest.fn((selector) => document.querySelector(selector)),
            delegate: jest.fn((root, eventName, selector, handler) => {
                var element = typeof root === "string" ? document.querySelector(root) : root;
                if (!element) {
                    throw new Error("Delegate root not found: " + selector);
                }
                var listener = function (event) {
                    var matched = event.target && event.target.closest(selector);
                    if (matched && element.contains(matched)) {
                        handler.call(matched, event, matched);
                    }
                };
                element.addEventListener(eventName, listener);
                delegateTeardowns.push(function () {
                    element.removeEventListener(eventName, listener);
                });
                return function unsubscribe() {
                    element.removeEventListener(eventName, listener);
                };
            })
        };
    }

    beforeEach(async () => {
        jest.resetModules();
        buildFixture();
        installDomHelpers();

        httpMock = {
            request: jest.fn(),
            postJson: jest.fn((url) => {
                if (url === "bootstrap/enable") {
                    return Promise.resolve({
                        body: {
                            Content: {
                                enabled: false,
                                queued: true,
                                job_id: "job-enable-1"
                            }
                        }
                    });
                }
                return Promise.resolve({ body: { Content: {} } });
            }),
            getJson: jest.fn((url) => {
                if (url === "bootstrap/current-ref") {
                    return Promise.resolve({ Content: { ref: "main" } });
                }
                if (url === "bootstrap/commits") {
                    return Promise.resolve({
                        Content: {
                            commits: [{
                                sha: "abc123456789",
                                short_sha: "abc1234",
                                message: "Initial commit",
                                author: "tester"
                            }]
                        }
                    });
                }
                return Promise.resolve({ Content: {} });
            })
        };
        global.WCHttp = httpMock;

        baseInstance = {
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn()
        };
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.url_for_run = jest.fn((path) => path);

        await import("../bootstrap_control.js");
        controller = window.BootstrapControl.getInstance();
        controller.bootstrap({
            user: {
                isAuthenticated: true,
                isAdmin: false,
                isRoot: false
            },
            data: {
                bootstrap: {
                    enabled: false,
                    adminDisabled: false,
                    isAnonymous: false
                }
            }
        });
    });

    afterEach(() => {
        delegateTeardowns.forEach((teardown) => teardown());
        jest.clearAllMocks();
        delete global.WCDom;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.url_for_run;
        delete window.BootstrapControl;
        delete globalThis.BootstrapControl;
        document.body.innerHTML = "";
    });

    test("tracks queued enable jobs and refreshes state after completion", async () => {
        document
            .querySelector('[data-bootstrap-action="enable"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "bootstrap/enable",
            {},
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.any(Object), "job-enable-1");
        expect(controller.poll_completion_event).toBe("BOOTSTRAP_ENABLE_TASK_COMPLETED");
        expect(document.querySelector('[data-bootstrap-action="mint"]').disabled).toBe(true);
        expect(document.querySelector("[data-bootstrap-message-body]").textContent)
            .toContain("Waiting for completion.");

        controller.triggerEvent("BOOTSTRAP_ENABLE_TASK_COMPLETED", {
            source: "poll",
            job_id: "job-enable-1",
            status: { status: "finished" }
        });
        await flushPromises();

        expect(baseInstance.set_rq_job_id).toHaveBeenLastCalledWith(expect.any(Object), null);
        expect(httpMock.getJson).toHaveBeenCalledWith("bootstrap/current-ref");
        expect(httpMock.getJson).toHaveBeenCalledWith("bootstrap/commits");
        expect(document.querySelector('[data-bootstrap-action="mint"]').disabled).toBe(false);
        expect(document.querySelector("[data-bootstrap-message-body]").textContent).toContain("Bootstrap enabled.");
    });

    test("resets pending enable state when the tracked job fails", async () => {
        document
            .querySelector('[data-bootstrap-action="enable"]')
            .dispatchEvent(new MouseEvent("click", { bubbles: true }));

        await flushPromises();

        controller.triggerEvent("job:error", {
            source: "poll",
            job_id: "job-enable-1",
            status: "failed"
        });
        await flushPromises();

        expect(baseInstance.set_rq_job_id).toHaveBeenLastCalledWith(expect.any(Object), null);
        expect(document.querySelector("[data-bootstrap-disabled]").hidden).toBe(false);
        expect(document.querySelector('[data-bootstrap-action="enable"]').disabled).toBe(false);
        expect(document.querySelector("[data-bootstrap-message-body]").textContent)
            .toContain("initialization failed");
        expect(httpMock.getJson).not.toHaveBeenCalledWith("bootstrap/current-ref");
        expect(httpMock.getJson).not.toHaveBeenCalledWith("bootstrap/commits");
    });
});

/**
 * @jest-environment jsdom
 */

describe("WCControllerBootstrap", () => {
    beforeEach(async () => {
        jest.resetModules();
        await import("../bootstrap.js");
    });

    afterEach(() => {
        delete window.WCControllerBootstrap;
    });

    test("bootstrapManyBestEffort continues after controller bootstrap failure", () => {
        const api = window.WCControllerBootstrap;
        const callOrder = [];
        const onError = jest.fn();
        const context = { run: { id: "run-123" } };

        const firstController = {
            getInstance: () => ({
                bootstrap: (_ctx, meta) => {
                    callOrder.push("first:" + meta.name);
                }
            })
        };
        const failingController = {
            getInstance: () => ({
                bootstrap: () => {
                    throw new Error("beta failed");
                }
            })
        };
        const thirdController = {
            getInstance: () => ({
                bootstrap: (_ctx, meta) => {
                    callOrder.push("third:" + meta.name);
                }
            })
        };

        const results = api.bootstrapManyBestEffort([
            { controller: firstController, name: "alpha" },
            { controller: failingController, name: "beta" },
            { controller: thirdController, name: "gamma" }
        ], context, onError);

        expect(callOrder).toEqual(["first:alpha", "third:gamma"]);
        expect(results).toHaveLength(3);
        expect(results[1]).toBeNull();
        expect(onError).toHaveBeenCalledTimes(1);
        expect(onError).toHaveBeenCalledWith(
            expect.any(Error),
            expect.objectContaining({ name: "beta" })
        );
    });

    test("bootstrapManyBestEffort handles tuple entries and preserves context", () => {
        const api = window.WCControllerBootstrap;
        const bootstrap = jest.fn();
        const tupleController = {
            getInstance: () => ({ bootstrap })
        };
        const context = { run: { id: "run-456" } };

        api.bootstrapManyBestEffort([[tupleController, "tupleKey"]], context);

        expect(bootstrap).toHaveBeenCalledWith(
            context,
            expect.objectContaining({ name: "tupleKey" })
        );
    });

    test("bootstrapManyBestEffort continues when error callback throws", () => {
        const api = window.WCControllerBootstrap;
        const callOrder = [];
        const warnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});
        const onError = jest.fn(() => {
            throw new Error("callback failed");
        });
        const context = { run: { id: "run-789" } };

        const firstController = {
            getInstance: () => ({
                bootstrap: (_ctx, meta) => {
                    callOrder.push("first:" + meta.name);
                }
            })
        };
        const failingController = {
            getInstance: () => ({
                bootstrap: () => {
                    throw new Error("beta failed");
                }
            })
        };
        const thirdController = {
            getInstance: () => ({
                bootstrap: (_ctx, meta) => {
                    callOrder.push("third:" + meta.name);
                }
            })
        };

        api.bootstrapManyBestEffort([
            { controller: firstController, name: "alpha" },
            { controller: failingController, name: "beta" },
            { controller: thirdController, name: "gamma" }
        ], context, onError);

        expect(callOrder).toEqual(["first:alpha", "third:gamma"]);
        expect(onError).toHaveBeenCalledTimes(1);
        expect(warnSpy).toHaveBeenCalledWith("[Bootstrap] Error callback failed", expect.any(Error));
        warnSpy.mockRestore();
    });
});

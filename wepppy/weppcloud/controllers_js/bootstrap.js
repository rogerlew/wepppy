/* ----------------------------------------------------------------------------
 * Controller Bootstrap Helper
 * ----------------------------------------------------------------------------
 */
(function (global) {
    "use strict";

    var storedContext = null;

    function isObject(value) {
        return value !== null && typeof value === "object";
    }

    function setContext(context) {
        storedContext = context && typeof context === "object" ? context : {};
        return storedContext;
    }

    function getContext() {
        return storedContext;
    }

    function ensureController(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            var resolved = global[target];
            if (!resolved) {
                throw new Error("Controller not found: " + target);
            }
            target = resolved;
        }
        if (typeof target.getInstance === "function") {
            return target.getInstance();
        }
        return target;
    }

    function bootstrap(target, key, context) {
        var ctx = context && typeof context === "object" ? context : storedContext || {};
        if (context && context !== storedContext) {
            storedContext = ctx;
        }
        var instance = ensureController(target);
        if (!instance) {
            return null;
        }
        if (typeof instance.bootstrap === "function") {
            instance.bootstrap(ctx, { name: key || null });
        }
        return instance;
    }

    function bootstrapMany(entries, context) {
        if (!Array.isArray(entries)) {
            return [];
        }
        return entries.map(function (entry) {
            if (!entry) {
                return null;
            }
            if (Array.isArray(entry)) {
                return bootstrap(entry[0], entry[1], context);
            }
            if (typeof entry === "object" && entry.controller) {
                return bootstrap(entry.controller, entry.name || entry.key, context);
            }
            return bootstrap(entry, null, context);
        });
    }

    function getControllerContext(context, key) {
        var ctx = context || storedContext || {};
        if (!key) {
            return {};
        }
        var controllers = ctx.controllers;
        if (isObject(controllers) && Object.prototype.hasOwnProperty.call(controllers, key)) {
            var value = controllers[key];
            return isObject(value) ? value : {};
        }
        return {};
    }

    function resolveJobId(context, jobKey) {
        if (!jobKey) {
            return null;
        }
        var ctx = context || storedContext || {};
        var jobIds = ctx.jobIds || ctx.jobs;
        if (!isObject(jobIds)) {
            return null;
        }
        if (!Object.prototype.hasOwnProperty.call(jobIds, jobKey)) {
            return null;
        }
        var value = jobIds[jobKey];
        if (value === undefined || value === null) {
            return null;
        }
        return String(value);
    }

    var api = {
        setContext: setContext,
        getContext: getContext,
        bootstrap: bootstrap,
        bootstrapMany: bootstrapMany,
        getControllerContext: getControllerContext,
        resolveJobId: resolveJobId
    };

    global.WCControllerBootstrap = api;
}(typeof globalThis !== "undefined" ? globalThis : window));

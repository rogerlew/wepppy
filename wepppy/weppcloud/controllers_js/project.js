/* ----------------------------------------------------------------------------
 * Project
 * ----------------------------------------------------------------------------
 */
var Project = (function () {
    "use strict";

    var instance;

    var NAME_SELECTOR = '[data-project-field="name"]';
    var SCENARIO_SELECTOR = '[data-project-field="scenario"]';
    var READONLY_SELECTOR = '[data-project-toggle="readonly"]';
    var PUBLIC_SELECTOR = '[data-project-toggle="public"]';
    var ACTION_SELECTOR = '[data-project-action]';
    var MOD_SELECTOR = '[data-project-mod]';
    var GLOBAL_UNIT_SELECTOR = '[data-project-unitizer="global"]';
    var CATEGORY_UNIT_SELECTOR = '[data-project-unitizer="category"]';

    var DEFAULT_DEBOUNCE_MS = 800;

    var EVENT_NAMES = [
        "project:name:updated",
        "project:name:update:failed",
        "project:scenario:updated",
        "project:scenario:update:failed",
        "project:readonly:changed",
        "project:readonly:update:failed",
        "project:public:changed",
        "project:public:update:failed",
        "project:unitizer:sync:started",
        "project:unitizer:preferences",
        "project:unitizer:sync:completed",
        "project:unitizer:sync:failed"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (
            !dom ||
            typeof dom.qsa !== "function" ||
            typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" ||
            typeof dom.hide !== "function"
        ) {
            throw new Error("Project controller requires WCDom helpers.");
        }
        if (
            !http ||
            typeof http.postJson !== "function" ||
            typeof http.request !== "function" ||
            typeof http.getJson !== "function"
        ) {
            throw new Error("Project controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Project controller requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
    }

    function firstFieldValue(dom, selector, fallback) {
        var elements = dom.qsa(selector);
        if (!elements || elements.length === 0) {
            return fallback || "";
        }
        var value = elements[0].value;
        if (value === undefined || value === null) {
            return fallback || "";
        }
        return String(value);
    }

    function syncFieldValue(dom, selector, value) {
        var elements = dom.qsa(selector);
        if (!elements) {
            return;
        }
        elements.forEach(function (input) {
            if (document.activeElement === input && input.value === value) {
                return;
            }
            input.value = value;
        });
    }

    function readToggleState(dom, selector, fallback) {
        var elements = dom.qsa(selector);
        if (!elements || elements.length === 0) {
            return Boolean(fallback);
        }
        return Boolean(elements[0].checked);
    }

    function syncToggleState(dom, selector, state) {
        var elements = dom.qsa(selector);
        if (!elements) {
            return;
        }
        elements.forEach(function (input) {
            input.checked = Boolean(state);
        });
    }

    function updateTitleWithName(nameValue) {
        try {
            var parts = (document.title || "").split(" - ");
            var baseTitle = parts[0] || document.title || "";
            document.title = baseTitle + " - " + (nameValue || "Untitled");
        } catch (err) {
            console.warn("Failed to update document title with project name", err);
        }
    }

    function updateTitleWithScenario(scenarioValue) {
        try {
            var parts = (document.title || "").split(" - ");
            var baseTitle = parts[0] || document.title || "";
            document.title = baseTitle + " - " + (scenarioValue || "");
        } catch (err) {
            console.warn("Failed to update document title with scenario", err);
        }
    }

    function notifyError(message, error) {
        if (error) {
            if (window.WCHttp && typeof window.WCHttp.isHttpError === "function" && window.WCHttp.isHttpError(error)) {
                console.error(message, error.detail || error.body, error);
            } else {
                console.error(message, error);
            }
        } else {
            console.error(message);
        }
    }

    function unpackResponse(result) {
        if (!result) {
            return null;
        }
        if (result.body !== undefined) {
            return result.body;
        }
        return result;
    }

    function isSuccess(response) {
        return response && response.Success === true;
    }

    function getContent(response) {
        if (!response || typeof response !== "object") {
            return {};
        }
        return response.Content || response.content || {};
    }

    function emitEvent(emitter, name, payload) {
        if (!emitter || typeof emitter.emit !== "function") {
            return;
        }
        emitter.emit(name, payload);
    }

    function applyReadonlyState(dom, readonly) {
        var hideElements = dom.qsa(".hide-readonly");
        hideElements.forEach(function (element) {
            if (readonly) {
                dom.hide(element);
            } else {
                dom.show(element);
            }
        });

        var targets = dom.qsa(".disable-readonly");
        targets.forEach(function (element) {
            var tagName = element.tagName ? element.tagName.toLowerCase() : "";
            if (tagName === "input") {
                var type = (element.getAttribute("type") || "").toLowerCase();
                if (type === "radio" || type === "checkbox" || type === "button" || type === "submit" || type === "reset") {
                    element.disabled = readonly;
                } else {
                    element.readOnly = readonly;
                    if (readonly) {
                        element.setAttribute("readonly", "readonly");
                    } else {
                        element.removeAttribute("readonly");
                    }
                }
            } else if (tagName === "select" || tagName === "button") {
                element.disabled = readonly;
            } else if (tagName === "textarea") {
                element.readOnly = readonly;
                if (readonly) {
                    element.setAttribute("readonly", "readonly");
                } else {
                    element.removeAttribute("readonly");
                }
            } else if (readonly) {
                element.setAttribute("aria-disabled", "true");
            } else {
                element.removeAttribute("aria-disabled");
            }
        });

        if (!readonly) {
            try {
                if (window.Outlet && typeof window.Outlet.getInstance === "function") {
                    var outlet = window.Outlet.getInstance();
                    if (outlet && typeof outlet.setMode === "function") {
                        outlet.setMode(0);
                    }
                }
            } catch (err) {
                console.warn("Failed to reset Outlet mode", err);
            }
        }
    }

    function getRunContext() {
        var runid = typeof window.runid === "string" && window.runid ? window.runid : null;
        var config = typeof window.config === "string" && window.config ? window.config : null;
        if (!runid || !config) {
            return null;
        }
        return { runid: runid, config: config };
    }

    function updateGlobalUnitizerRadios(dom, targetValue) {
        var radios = dom.qsa(GLOBAL_UNIT_SELECTOR);
        if (!radios || radios.length === 0) {
            return;
        }
        var normalized = String(targetValue);
        radios.forEach(function (radio) {
            radio.checked = false;
            radio.removeAttribute("checked");
        });
        radios.forEach(function (radio) {
            if (String(radio.value) === normalized) {
                radio.checked = true;
                radio.setAttribute("checked", "checked");
            }
        });
    }

    function applyUnitizerPreferences(client, root) {
        var scope = root || document;
        if (!scope || !client || typeof client.getPreferenceTokens !== "function") {
            return;
        }

        var tokens = client.getPreferenceTokens();
        Object.keys(tokens).forEach(function (categoryKey) {
            var groupName = "unitizer_" + categoryKey + "_radio";
            var radios = scope.querySelectorAll("input[name='" + groupName + "']");
            Array.prototype.forEach.call(radios, function (radio) {
                var value = radio.value;
                var elements = scope.querySelectorAll(".units-" + value);
                Array.prototype.forEach.call(elements, function (el) {
                    el.classList.add("invisible");
                });
            });

            var preferredToken = tokens[categoryKey];
            if (!preferredToken) {
                return;
            }
            var preferredElements = scope.querySelectorAll(".units-" + preferredToken);
            Array.prototype.forEach.call(preferredElements, function (el) {
                el.classList.remove("invisible");
            });
        });

        if (typeof client.updateUnitLabels === "function") {
            client.updateUnitLabels(scope);
        }
        if (typeof client.registerNumericInputs === "function") {
            client.registerNumericInputs(scope);
        }
        if (typeof client.updateNumericFields === "function") {
            client.updateNumericFields(scope);
        }
        if (typeof client.dispatchPreferenceChange === "function") {
            client.dispatchPreferenceChange();
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;

        var project = controlBase();
        var emitter = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                emitter = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                emitter = emitterBase;
            }
            project.events = emitter;
        }

        var runContext = typeof window !== "undefined" ? window.runContext || {} : {};
        var state = {
            name: firstFieldValue(dom, NAME_SELECTOR, ""),
            scenario: firstFieldValue(dom, SCENARIO_SELECTOR, ""),
            readonly: readToggleState(dom, READONLY_SELECTOR, false),
            public: readToggleState(dom, PUBLIC_SELECTOR, false),
            mods: Array.isArray(runContext.mods && runContext.mods.list)
                ? runContext.mods.list.slice()
                : []
        };

        project.state = state;
        project._currentName = state.name;
        project._currentScenario = state.scenario;
        project._nameDebounceTimer = null;
        project._scenarioDebounceTimer = null;
        project._notifyTimer = null;
        project._unitPreferenceInflight = null;
        project._pendingUnitPreference = null;

        project.notifyCommandBar = function (message, options) {
            options = options || {};
            var duration = options.duration;
            if (duration === undefined) {
                duration = 2500;
            }
            if (typeof window.initializeCommandBar !== "function") {
                return;
            }
            var commandBar = window.initializeCommandBar();
            if (!commandBar || typeof commandBar.showResult !== "function") {
                return;
            }
            commandBar.showResult(message);
            if (project._notifyTimer) {
                clearTimeout(project._notifyTimer);
            }
            if (duration !== null && typeof commandBar.hideResult === "function") {
                project._notifyTimer = setTimeout(function () {
                    commandBar.hideResult();
                }, duration);
            }
        };
        project._notifyCommandBar = project.notifyCommandBar;

        project.setName = function (name, options) {
            options = options || {};
            var trimmed = (name || "").trim();
            if (trimmed === state.name) {
                return Promise.resolve({ Success: true, skipped: true });
            }

            var previous = state.name;
            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = null;

            return http.postJson(url_for_run("tasks/setname/"), { name: trimmed }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    var content = getContent(response);
                    var savedName = typeof content.name === "string" ? content.name : trimmed;
                    state.name = savedName;
                    project._currentName = savedName;
                    syncFieldValue(dom, NAME_SELECTOR, savedName);
                    updateTitleWithName(savedName);
                    if (options.notify !== false) {
                        var displayName = savedName || "Untitled";
                        project.notifyCommandBar('Saved project name to "' + displayName + '"');
                    }
                    emitEvent(emitter, "project:name:updated", {
                        name: state.name,
                        previous: previous,
                        response: response
                    });
                } else {
                    state.name = previous;
                    project._currentName = previous;
                    syncFieldValue(dom, NAME_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error saving project name", { duration: null });
                    }
                    emitEvent(emitter, "project:name:update:failed", {
                        attempted: trimmed,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                state.name = previous;
                project._currentName = previous;
                syncFieldValue(dom, NAME_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error saving project name", { duration: null });
                }
                notifyError("Error saving project name", error);
                emitEvent(emitter, "project:name:update:failed", {
                    attempted: trimmed,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };

        project.setNameFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, NAME_SELECTOR, ""));
            var wait = typeof opts.debounceMs === "number" ? opts.debounceMs : DEFAULT_DEBOUNCE_MS;

            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = setTimeout(function () {
                project.setName(value, opts);
            }, wait);
        };

        project.commitNameFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, NAME_SELECTOR, ""));
            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = null;
            project.setName(value, opts);
        };

        project.setScenario = function (scenario, options) {
            options = options || {};
            var trimmed = (scenario || "").trim();
            if (trimmed === state.scenario) {
                return Promise.resolve({ Success: true, skipped: true });
            }

            var previous = state.scenario;
            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = null;

            return http.postJson(url_for_run("tasks/setscenario/"), { scenario: trimmed }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    var content = getContent(response);
                    var savedScenario = typeof content.scenario === "string" ? content.scenario : trimmed;
                    state.scenario = savedScenario;
                    project._currentScenario = savedScenario;
                    syncFieldValue(dom, SCENARIO_SELECTOR, savedScenario);
                    updateTitleWithScenario(savedScenario);
                    if (options.notify !== false) {
                        var message = savedScenario ? ('Saved scenario to "' + savedScenario + '"') : "Cleared scenario";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:scenario:updated", {
                        scenario: state.scenario,
                        previous: previous,
                        response: response
                    });
                } else {
                    state.scenario = previous;
                    project._currentScenario = previous;
                    syncFieldValue(dom, SCENARIO_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error saving scenario", { duration: null });
                    }
                    emitEvent(emitter, "project:scenario:update:failed", {
                        attempted: trimmed,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                state.scenario = previous;
                project._currentScenario = previous;
                syncFieldValue(dom, SCENARIO_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error saving scenario", { duration: null });
                }
                notifyError("Error saving project scenario", error);
                emitEvent(emitter, "project:scenario:update:failed", {
                    attempted: trimmed,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };

        project.setScenarioFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, SCENARIO_SELECTOR, ""));
            var wait = typeof opts.debounceMs === "number" ? opts.debounceMs : DEFAULT_DEBOUNCE_MS;

            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = setTimeout(function () {
                project.setScenario(value, opts);
            }, wait);
        };

        project.commitScenarioFromInput = function (options) {
            var opts = options || {};
            var source = opts.source;
            var value = opts.value !== undefined
                ? opts.value
                : (source && source.value !== undefined ? source.value : firstFieldValue(dom, SCENARIO_SELECTOR, ""));
            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = null;
            project.setScenario(value, opts);
        };

        project.set_readonly_controls = function (readonly) {
            applyReadonlyState(dom, Boolean(readonly));
        };

        project.set_readonly = function (stateValue, options) {
            options = options || {};
            var desiredState = Boolean(stateValue);
            var previous = readToggleState(dom, READONLY_SELECTOR, state.readonly);

            return http.postJson(url_for_run("tasks/set_readonly"), { readonly: desiredState }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    syncToggleState(dom, READONLY_SELECTOR, desiredState);
                    state.readonly = desiredState;
                    project.set_readonly_controls(desiredState);
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "READONLY set to True. Project controls disabled."
                            : "READONLY set to False. Project controls enabled.";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:readonly:changed", {
                        readonly: desiredState,
                        previous: previous,
                        response: response
                    });
                } else {
                    syncToggleState(dom, READONLY_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error updating READONLY state.", { duration: null });
                    }
                    emitEvent(emitter, "project:readonly:update:failed", {
                        attempted: desiredState,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                syncToggleState(dom, READONLY_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating READONLY state.", { duration: null });
                }
                notifyError("Error updating READONLY state", error);
                emitEvent(emitter, "project:readonly:update:failed", {
                    attempted: desiredState,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };
        project.setReadonly = project.set_readonly;

        project.set_public = function (stateValue, options) {
            options = options || {};
            var desiredState = Boolean(stateValue);
            var previous = readToggleState(dom, PUBLIC_SELECTOR, state.public);

            return http.postJson(url_for_run("tasks/set_public"), { public: desiredState }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    syncToggleState(dom, PUBLIC_SELECTOR, desiredState);
                    state.public = desiredState;
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "PUBLIC set to True. Project is now publicly accessible."
                            : "PUBLIC set to False. Project access limited to collaborators.";
                        project.notifyCommandBar(message);
                    }
                    emitEvent(emitter, "project:public:changed", {
                        isPublic: desiredState,
                        previous: previous,
                        response: response
                    });
                } else {
                    syncToggleState(dom, PUBLIC_SELECTOR, previous);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project.notifyCommandBar("Error updating PUBLIC state.", { duration: null });
                    }
                    emitEvent(emitter, "project:public:update:failed", {
                        attempted: desiredState,
                        previous: previous,
                        response: response
                    });
                }
                return response;
            }).catch(function (error) {
                syncToggleState(dom, PUBLIC_SELECTOR, previous);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating PUBLIC state.", { duration: null });
                }
                notifyError("Error updating PUBLIC state", error);
                emitEvent(emitter, "project:public:update:failed", {
                    attempted: desiredState,
                    previous: previous,
                    error: error
                });
                return null;
            });
        };
        project.setPublic = project.set_public;

        project.set_mod = function (modName, enabled, options) {
            options = options || {};
            var normalized = typeof modName === "string" ? modName.trim() : "";
            if (!normalized) {
                return Promise.resolve(null);
            }
            var desiredState = Boolean(enabled);
            var input = options.input || null;
            if (input) {
                input.disabled = true;
            }

            return http.request(url_for_run("tasks/set_mod"), {
                method: "POST",
                json: { mod: normalized, enabled: desiredState }
            }).then(function (result) {
                var response = unpackResponse(result);
                if (isSuccess(response)) {
                    if (options.notify !== false) {
                        var label = response.Content && response.Content.label ? response.Content.label : normalized;
                        var verb = desiredState ? "enabled" : "disabled";
                        project.notifyCommandBar(label + " " + verb + ". Reloading…");
                    }
                    window.location.reload();
                    return response;
                }

                if (input) {
                    input.disabled = false;
                    input.checked = !desiredState;
                }
                if (response) {
                    project.pushResponseStacktrace(project, response);
                }
                if (options.notify !== false) {
                    project.notifyCommandBar("Unable to update module.", { duration: null });
                }
                return response;
            }).catch(function (error) {
                if (input) {
                    input.disabled = false;
                    input.checked = !desiredState;
                }
                notifyError("Error updating module state", error);
                if (options.notify !== false) {
                    project.notifyCommandBar("Error updating module.", { duration: null });
                }
                return null;
            });
        };

        project.clear_locks = function () {
            return http.request(url_for_run("tasks/clear_locks"), {
                method: "GET",
                params: { _: Date.now() }
            }).then(function (result) {
                var response = unpackResponse(result);
                if (response && response.Success === true) {
                    window.alert("Locks have been cleared");
                } else {
                    window.alert("Error clearing locks");
                }
                return response;
            }).catch(function (error) {
                notifyError("Error clearing locks", error);
                window.alert("Error clearing locks");
                return null;
            });
        };

        project.promote_recorder_profile = function () {
            if (typeof runid === "undefined" || !runid) {
                window.alert("Run ID is not available for promotion.");
                return Promise.resolve(null);
            }

            var defaultSlug = runid;
            var slug = window.prompt("Enter profile slug", defaultSlug);
            if (slug === null) {
                return Promise.resolve(null);
            }

            slug = (slug || "").trim();
            var payload = {};
            if (slug) {
                payload.slug = slug;
            }

            return http.postJson(url_for_run("recorder/promote"), payload).then(function (result) {
                var response = result && result.body ? result.body : result;
                if (response && response.success) {
                    var profileRoot = response.profile && response.profile.profile_root;
                    var message = "Profile draft promoted.";
                    if (profileRoot) {
                        message += "\nSaved to: " + profileRoot;
                    }
                    window.alert(message);
                } else {
                    var errorMessage = response && (response.message || response.error) || "Error promoting profile draft.";
                    window.alert(errorMessage);
                }
                return response;
            }).catch(function (error) {
                notifyError("Error promoting profile draft", error);
                window.alert("Error promoting profile draft.");
                return null;
            });
        };

        project.handleGlobalUnitPreference = function (pref) {
            var numericPref = Number(pref);
            if (Number.isNaN(numericPref)) {
                return Promise.resolve();
            }

            updateGlobalUnitizerRadios(dom, numericPref);

            if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
                console.warn("[Project] UnitizerClient is not available.");
                return Promise.resolve();
            }

            if (project._unitPreferenceInflight) {
                project._pendingUnitPreference = numericPref;
                return project._unitPreferenceInflight;
            }

            project._pendingUnitPreference = null;
            project._unitPreferenceInflight = window.UnitizerClient.ready()
                .then(function (client) {
                    if (typeof client.setGlobalPreference === "function") {
                        client.setGlobalPreference(numericPref);
                    }
                    if (typeof client.applyPreferenceRadios === "function") {
                        client.applyPreferenceRadios(document);
                    }
                    if (typeof client.applyGlobalRadio === "function") {
                        client.applyGlobalRadio(numericPref, document);
                    }
                    applyUnitizerPreferences(client, document);
                    return project.unitChangeEvent({
                        syncFromDom: false,
                        client: client,
                        source: "global"
                    });
                })
                .catch(function (error) {
                    console.error("Error applying global unit preference", error);
                })
                .finally(function () {
                    var nextPref = project._pendingUnitPreference;
                    project._unitPreferenceInflight = null;
                    if (nextPref !== null && nextPref !== undefined) {
                        project._pendingUnitPreference = null;
                        project.handleGlobalUnitPreference(nextPref);
                    }
                });

            return project._unitPreferenceInflight;
        };

        project.handleUnitPreferenceChange = function () {
            if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
                console.warn("[Project] UnitizerClient is not available.");
                return Promise.resolve();
            }
            return project.unitChangeEvent({ source: "category" });
        };

        project.unitChangeEvent = function (options) {
            options = options || {};
            emitEvent(emitter, "project:unitizer:sync:started", { source: options.source || "unknown" });

            var clientPromise = options.client ? Promise.resolve(options.client) : (
                window.UnitizerClient && typeof window.UnitizerClient.ready === "function"
                    ? window.UnitizerClient.ready()
                    : Promise.reject(new Error("UnitizerClient not available"))
            );

            var syncPromise = clientPromise.then(function (client) {
                var root = options.root || document;
                if (options.syncFromDom !== false && typeof client.syncPreferencesFromDom === "function") {
                    client.syncPreferencesFromDom(root);
                }

                applyUnitizerPreferences(client, root);

                var preferences = typeof client.getPreferencePayload === "function"
                    ? client.getPreferencePayload()
                    : {};

                var context = getRunContext();
                if (!context) {
                    console.warn("[Project] Cannot persist unit preferences without run context.");
                    emitEvent(emitter, "project:unitizer:sync:failed", {
                        error: new Error("Missing run context"),
                        preferences: preferences,
                        source: options.source || "unknown"
                    });
                    return null;
                }

                return http.postJson(
                    "runs/" + context.runid + "/" + context.config + "/tasks/set_unit_preferences/",
                    preferences
                ).then(function (result) {
                    var response = unpackResponse(result);
                    if (!isSuccess(response)) {
                        if (response) {
                            project.pushResponseStacktrace(project, response);
                        }
                        emitEvent(emitter, "project:unitizer:sync:failed", {
                            response: response,
                            preferences: preferences,
                            source: options.source || "unknown"
                        });
                        return response;
                    }

                    emitEvent(emitter, "project:unitizer:preferences", {
                        preferences: preferences,
                        response: response,
                        source: options.source || "unknown"
                    });
                    return response;
                }).catch(function (error) {
                    notifyError("Failed to persist unit preferences", error);
                    emitEvent(emitter, "project:unitizer:sync:failed", {
                        error: error,
                        preferences: preferences,
                        source: options.source || "unknown"
                    });
                    return null;
                });
            }).catch(function (error) {
                notifyError("Failed to load unitizer client", error);
                emitEvent(emitter, "project:unitizer:sync:failed", {
                    error: error,
                    source: options.source || "unknown"
                });
                return null;
            });

            return syncPromise.finally(function () {
                emitEvent(emitter, "project:unitizer:sync:completed", { source: options.source || "unknown" });
            });
        };

        project.set_preferred_units = function (root) {
            if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
                console.warn("[Project] UnitizerClient is not available.");
                return Promise.resolve(null);
            }
            return window.UnitizerClient.ready()
                .then(function (client) {
                    var scope = root || document;
                    if (typeof client.syncPreferencesFromDom === "function") {
                        client.syncPreferencesFromDom(scope);
                    }
                    applyUnitizerPreferences(client, scope);
                    return client;
                })
                .catch(function (error) {
                    console.error("Failed to apply unit preferences", error);
                    return null;
                });
        };

        dom.delegate(document, "input", NAME_SELECTOR, function (event, target) {
            project.setNameFromInput({ source: target });
        });

        dom.delegate(document, "focusout", NAME_SELECTOR, function (event, target) {
            project.commitNameFromInput({ source: target });
        });

        dom.delegate(document, "input", SCENARIO_SELECTOR, function (event, target) {
            project.setScenarioFromInput({ source: target });
        });

        dom.delegate(document, "focusout", SCENARIO_SELECTOR, function (event, target) {
            project.commitScenarioFromInput({ source: target });
        });

        dom.delegate(document, "change", READONLY_SELECTOR, function (event, target) {
            project.set_readonly(target.checked);
        });

        dom.delegate(document, "change", PUBLIC_SELECTOR, function (event, target) {
            project.set_public(target.checked);
        });

        dom.delegate(document, "change", MOD_SELECTOR, function (event, target) {
            var modName = target.getAttribute("data-project-mod");
            if (!modName) {
                return;
            }
            project.set_mod(modName, target.checked, { input: target });
        });

        dom.delegate(document, "click", ACTION_SELECTOR, function (event, target) {
            var action = target.getAttribute("data-project-action");
            if (!action) {
                return;
            }
            event.preventDefault();
            if (action === "clear-locks") {
                project.clear_locks();
            } else if (action === "recorder-promote") {
                project.promote_recorder_profile();
            }
        });

        dom.delegate(document, "change", GLOBAL_UNIT_SELECTOR, function (event, target) {
            project.handleGlobalUnitPreference(target.value);
        });

        dom.delegate(document, "change", CATEGORY_UNIT_SELECTOR, function () {
            project.handleUnitPreferenceChange();
        });

        project.set_readonly_controls(state.readonly);

        project.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var controllerContext = ctx.controllers && ctx.controllers.project ? ctx.controllers.project : {};
            var readonly = controllerContext.readonly;
            if (readonly === undefined && ctx.user) {
                readonly = ctx.user.readonly;
            }
            if (readonly !== undefined && typeof project.set_readonly_controls === "function") {
                project.set_readonly_controls(Boolean(readonly));
            }
            return project;
        };

        return project;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.Project = Project;
    globalThis.setGlobalUnitizerPreference = function (pref) {
        var controller = Project.getInstance();
        if (controller && typeof controller.handleGlobalUnitPreference === "function") {
            return controller.handleGlobalUnitPreference(pref);
        }
        return undefined;
    };
}

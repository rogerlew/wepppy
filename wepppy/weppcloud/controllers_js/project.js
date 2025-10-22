/* ----------------------------------------------------------------------------
 * Project
 * ----------------------------------------------------------------------------
 */
var Project = (function () {
    var instance;

    function createInstance() {
        var project = controlBase();
        var dom = window.WCDom;
        var http = window.WCHttp;

        if (!dom || typeof dom.qsa !== "function" || typeof dom.hide !== "function" || typeof dom.show !== "function") {
            throw new Error("Project controller requires WCDom helpers.");
        }
        if (!http || typeof http.postForm !== "function" || typeof http.postJson !== "function") {
            throw new Error("Project controller requires WCHttp helpers.");
        }

        var nameInputs = dom.qsa('[data-project-field="name"]');
        var scenarioInputs = dom.qsa('[data-project-field="scenario"]');
        var readonlyToggles = dom.qsa('[data-project-toggle="readonly"]');
        var publicToggles = dom.qsa('[data-project-toggle="public"]');
        var actionButtons = dom.qsa('[data-project-action]');

        project._nameInputs = nameInputs;
        project._scenarioInputs = scenarioInputs;
        project._readonlyToggles = readonlyToggles;
        project._publicToggles = publicToggles;
        project._currentName = firstInputValue(nameInputs, "");
        project._currentScenario = firstInputValue(scenarioInputs, "");
        project._nameDebounceTimer = null;
        project._scenarioDebounceTimer = null;
        project._notifyTimer = null;
        project._unitPreferenceInflight = null;
        project._pendingUnitPreference = null;

        function firstInputValue(inputs, fallback) {
            if (!inputs || inputs.length === 0) {
                return fallback || "";
            }
            var value = inputs[0].value;
            if (value === undefined || value === null) {
                return fallback || "";
            }
            return String(value);
        }

        function syncInputValues(inputs, value) {
            if (!inputs) {
                return;
            }
            inputs.forEach(function (input) {
                if (document.activeElement === input && input.value === value) {
                    return;
                }
                input.value = value;
            });
        }

        function getToggleState(toggles, fallback) {
            if (!toggles || toggles.length === 0) {
                return fallback || false;
            }
            return Boolean(toggles[0].checked);
        }

        function syncToggleState(toggles, state) {
            if (!toggles) {
                return;
            }
            toggles.forEach(function (toggle) {
                toggle.checked = state;
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
                if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
                    console.error(message, error.detail || error.body, error);
                } else {
                    console.error(message, error);
                }
            } else {
                console.error(message);
            }
        }

        project._notifyCommandBar = function (message, options) {
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

        project.setName = function (name, options) {
            options = options || {};
            var trimmed = (name || "").trim();
            if (trimmed === project._currentName) {
                return Promise.resolve({ Success: true, skipped: true });
            }

            var previous = project._currentName;

            return http.postForm("tasks/setname/", { name: trimmed })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;

                    if (response && response.Success === true) {
                        project._currentName = trimmed;
                        syncInputValues(nameInputs, trimmed);
                        updateTitleWithName(trimmed);
                        if (options.notify !== false) {
                            var displayName = trimmed || "Untitled";
                            project._notifyCommandBar('Saved project name to "' + displayName + '"');
                        }
                    } else {
                        project._currentName = previous;
                        syncInputValues(nameInputs, previous);
                        if (response) {
                            project.pushResponseStacktrace(project, response);
                        }
                        if (options.notify !== false) {
                            project._notifyCommandBar("Error saving project name", { duration: null });
                        }
                    }

                    return response;
                })
                .catch(function (error) {
                    project._currentName = previous;
                    syncInputValues(nameInputs, previous);
                    if (options.notify !== false) {
                        project._notifyCommandBar("Error saving project name", { duration: null });
                    }
                    notifyError("Error saving project name", error);
                    return null;
                });
        };

        project.setNameFromInput = function (options) {
            var opts = options || {};
            var source = opts.source || (nameInputs.length > 0 ? nameInputs[0] : null);
            if (!source) {
                return;
            }
            var value = opts.value !== undefined ? opts.value : source.value;
            var wait = typeof opts.debounceMs === "number" ? opts.debounceMs : 800;

            clearTimeout(project._nameDebounceTimer);
            project._nameDebounceTimer = setTimeout(function () {
                project.setName(value, options);
            }, wait);
        };

        project.commitNameFromInput = function (options) {
            var opts = options || {};
            var source = opts.source || (nameInputs.length > 0 ? nameInputs[0] : null);
            var value = opts.value !== undefined ? opts.value : (source ? source.value : "");
            clearTimeout(project._nameDebounceTimer);
            project.setName(value, options);
        };

        project.setScenario = function (scenario, options) {
            options = options || {};
            var trimmed = (scenario || "").trim();
            if (trimmed === project._currentScenario) {
                return Promise.resolve({ Success: true, skipped: true });
            }

            var previous = project._currentScenario;

            return http.postForm("tasks/setscenario/", { scenario: trimmed })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;

                    if (response && response.Success === true) {
                        project._currentScenario = trimmed;
                        syncInputValues(scenarioInputs, trimmed);
                        updateTitleWithScenario(trimmed);
                        if (options.notify !== false) {
                            var message = trimmed ? ('Saved scenario to "' + trimmed + '"') : "Cleared scenario";
                            project._notifyCommandBar(message);
                        }
                    } else {
                        project._currentScenario = previous;
                        syncInputValues(scenarioInputs, previous);
                        if (response) {
                            project.pushResponseStacktrace(project, response);
                        }
                        if (options.notify !== false) {
                            project._notifyCommandBar("Error saving scenario", { duration: null });
                        }
                    }

                    return response;
                })
                .catch(function (error) {
                    project._currentScenario = previous;
                    syncInputValues(scenarioInputs, previous);
                    if (options.notify !== false) {
                        project._notifyCommandBar("Error saving scenario", { duration: null });
                    }
                    notifyError("Error saving project scenario", error);
                    return null;
                });
        };

        project.setScenarioFromInput = function (options) {
            var opts = options || {};
            var source = opts.source || (scenarioInputs.length > 0 ? scenarioInputs[0] : null);
            if (!source) {
                return;
            }
            var value = opts.value !== undefined ? opts.value : source.value;
            var wait = typeof opts.debounceMs === "number" ? opts.debounceMs : 800;

            clearTimeout(project._scenarioDebounceTimer);
            project._scenarioDebounceTimer = setTimeout(function () {
                project.setScenario(value, options);
            }, wait);
        };

        project.commitScenarioFromInput = function (options) {
            var opts = options || {};
            var source = opts.source || (scenarioInputs.length > 0 ? scenarioInputs[0] : null);
            var value = opts.value !== undefined ? opts.value : (source ? source.value : "");
            clearTimeout(project._scenarioDebounceTimer);
            project.setScenario(value, options);
        };

        project.clear_locks = function () {
            return http.request("tasks/clear_locks", {
                method: "GET",
                params: { _: Date.now() }
            }).then(function (result) {
                var response = result && result.body ? result.body : null;
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

        project.migrate_to_omni = function () {
            return http.getJson("tasks/omni_migration").then(function (response) {
                if (response && response.Success === true) {
                    window.alert("Project has been migrated to Omni. Page will now refresh.");
                    window.location.reload();
                } else {
                    window.alert("Error migrating project to Omni");
                }
                return response;
            }).catch(function (error) {
                notifyError("Error migrating project to Omni", error);
                window.alert("Error migrating project to Omni");
                return null;
            });
        };

        project.enable_path_cost_effective = function () {
            return http.getJson("tasks/path_cost_effective_enable").then(function (response) {
                if (response && response.Success === true) {
                    window.alert("PATH Cost-Effective module enabled. Page will now refresh.");
                    window.location.reload();
                } else {
                    var message = response && (response.Message || (response.Content && response.Content.message));
                    window.alert(message || "Error enabling PATH Cost-Effective module");
                }
                return response;
            }).catch(function (error) {
                notifyError("Error enabling PATH Cost-Effective module", error);
                window.alert("Error enabling PATH Cost-Effective module");
                return null;
            });
        };

        function applyReadonlyState(readonly) {
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

        project.set_readonly_controls = function (readonly) {
            applyReadonlyState(Boolean(readonly));
        };

        project.set_readonly = function (state, options) {
            options = options || {};
            var desiredState = Boolean(state);
            var previousState = getToggleState(readonlyToggles, false);

            return http.postJson("tasks/set_readonly", { readonly: desiredState }).then(function (result) {
                var response = result && result.body ? result.body : null;

                if (response && response.Success === true) {
                    syncToggleState(readonlyToggles, desiredState);
                    project.set_readonly_controls(desiredState);
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "READONLY set to True. Project controls disabled."
                            : "READONLY set to False. Project controls enabled.";
                        project._notifyCommandBar(message);
                    }
                } else {
                    syncToggleState(readonlyToggles, previousState);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project._notifyCommandBar("Error updating READONLY state.", { duration: null });
                    }
                }

                return response;
            }).catch(function (error) {
                syncToggleState(readonlyToggles, previousState);
                if (options.notify !== false) {
                    project._notifyCommandBar("Error updating READONLY state.", { duration: null });
                }
                notifyError("Error updating READONLY state", error);
                return null;
            });
        };

        project.set_public = function (state, options) {
            options = options || {};
            var desiredState = Boolean(state);
            var previousState = getToggleState(publicToggles, false);

            return http.postJson("tasks/set_public", { public: desiredState }).then(function (result) {
                var response = result && result.body ? result.body : null;

                if (response && response.Success === true) {
                    syncToggleState(publicToggles, desiredState);
                    if (options.notify !== false) {
                        var message = desiredState
                            ? "PUBLIC set to True. Project is now publicly accessible."
                            : "PUBLIC set to False. Project access limited to collaborators.";
                        project._notifyCommandBar(message);
                    }
                } else {
                    syncToggleState(publicToggles, previousState);
                    if (response) {
                        project.pushResponseStacktrace(project, response);
                    }
                    if (options.notify !== false) {
                        project._notifyCommandBar("Error updating PUBLIC state.", { duration: null });
                    }
                }

                return response;
            }).catch(function (error) {
                syncToggleState(publicToggles, previousState);
                if (options.notify !== false) {
                    project._notifyCommandBar("Error updating PUBLIC state.", { duration: null });
                }
                notifyError("Error updating PUBLIC state", error);
                return null;
            });
        };

        project.handleGlobalUnitPreference = function (pref) {
            var numericPref = Number(pref);
            console.log("[Unitizer] handleGlobalUnitPreference invoked with", pref);
            if (Number.isNaN(numericPref)) {
                return Promise.resolve();
            }

            if (project._unitPreferenceInflight) {
                project._pendingUnitPreference = numericPref;
                return project._unitPreferenceInflight;
            }

            project._pendingUnitPreference = null;

            project._unitPreferenceInflight = UnitizerClient.ready()
                .then(function (client) {
                    client.setGlobalPreference(numericPref);
                    client.applyPreferenceRadios(document);
                    client.applyGlobalRadio(numericPref, document);
                    applyUnitizerPreferences(client, document);
                    console.log("[Unitizer] Global preference applied", client.getPreferencePayload());
                    return project.unitChangeEvent({ syncFromDom: false, client: client });
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
            console.log("[Unitizer] handleUnitPreferenceChange triggered");
            return project.unitChangeEvent();
        };

        project.unitChangeEvent = function (options) {
            options = options || {};
            console.log("[Unitizer] unitChangeEvent", options);
            return UnitizerClient.ready()
                .then(function (client) {
                    if (options.syncFromDom !== false) {
                        client.syncPreferencesFromDom(document);
                    }
                    console.log("[Unitizer] Preferences before apply", client.getPreferencePayload());
                    applyUnitizerPreferences(client, document);
                    var unitPreferences = client.getPreferencePayload();

                    return http.postForm(site_prefix + "/runs/" + runid + "/" + config + "/tasks/set_unit_preferences/", unitPreferences)
                        .then(function (result) {
                            var response = result && result.body ? result.body : null;
                            if (!response || response.Success !== true) {
                                console.warn("Unit preference update did not succeed", response);
                            }
                            return response;
                        })
                        .catch(function (error) {
                            notifyError("Failed to persist unit preferences", error);
                            return null;
                        });
                })
                .catch(function (error) {
                    console.error("Failed to persist unit preferences", error);
                });
        };

        project.set_preferred_units = function (root) {
            return UnitizerClient.ready()
                .then(function (client) {
                    client.syncPreferencesFromDom(root || document);
                    applyUnitizerPreferences(client, root || document);
                    return client;
                })
                .catch(function (error) {
                    console.error("Failed to apply unit preferences", error);
                });
        };

        function applyUnitizerPreferences(client, root) {
            var scope = root || document;
            var tokens = client.getPreferenceTokens();
            Object.keys(tokens).forEach(function (categoryKey) {
                var groupName = "unitizer_" + categoryKey + "_radio";
                var radios = document.querySelectorAll("input[name='" + groupName + "']");
                radios.forEach(function (radio) {
                    var value = radio.value;
                    var elements = document.querySelectorAll(".units-" + value);
                    elements.forEach(function (el) {
                        el.classList.add("invisible");
                    });
                });

                var preferredToken = tokens[categoryKey];
                if (!preferredToken) {
                    return;
                }
                var preferredElements = document.querySelectorAll(".units-" + preferredToken);
                preferredElements.forEach(function (el) {
                    el.classList.remove("invisible");
                });
            });

            client.updateUnitLabels(scope);
            client.registerNumericInputs(scope);
            client.updateNumericFields(scope);
            client.dispatchPreferenceChange();
        }

        function registerInputListeners() {
            nameInputs.forEach(function (input) {
                input.addEventListener("input", function (event) {
                    project.setNameFromInput({ source: event.target });
                });
                input.addEventListener("blur", function (event) {
                    project.commitNameFromInput({ source: event.target });
                });
            });

            scenarioInputs.forEach(function (input) {
                input.addEventListener("input", function (event) {
                    project.setScenarioFromInput({ source: event.target });
                });
                input.addEventListener("blur", function (event) {
                    project.commitScenarioFromInput({ source: event.target });
                });
            });

            readonlyToggles.forEach(function (toggle) {
                toggle.addEventListener("change", function (event) {
                    project.set_readonly(event.target.checked);
                });
            });

            publicToggles.forEach(function (toggle) {
                toggle.addEventListener("change", function (event) {
                    project.set_public(event.target.checked);
                });
            });

            actionButtons.forEach(function (button) {
                button.addEventListener("click", function (event) {
                    var action = event.currentTarget.getAttribute("data-project-action");
                    if (!action) {
                        return;
                    }
                    if (action === "clear-locks") {
                        project.clear_locks();
                    } else if (action === "migrate-omni") {
                        project.migrate_to_omni();
                    } else if (action === "enable-path-ce") {
                        project.enable_path_cost_effective();
                    }
                });
            });
        }

        registerInputListeners();
        project.set_readonly_controls(getToggleState(readonlyToggles, false));

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
}

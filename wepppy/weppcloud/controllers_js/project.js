/* ----------------------------------------------------------------------------
 * Project
 * ----------------------------------------------------------------------------
 */
var Project = function () {
    var instance;

    function createInstance() {
        var that = controlBase();

        that._nameInput = $("#input_name");
        that._scenarioInput = $("#input_scenario");
        that._currentName = that._nameInput.val() || '';
        that._currentScenario = that._scenarioInput.val() || '';
        that._nameDebounceTimer = null;
        that._scenarioDebounceTimer = null;
        that._notifyTimer = null;

        that._notifyCommandBar = function (message, options) {
            options = options || {};
            var duration = options.duration;
            if (duration === undefined) {
                duration = 2500;
            }

            if (typeof window.initializeCommandBar !== 'function') {
                return;
            }

            var commandBar = window.initializeCommandBar();
            if (!commandBar || typeof commandBar.showResult !== 'function') {
                return;
            }

            commandBar.showResult(message);

            if (that._notifyTimer) {
                clearTimeout(that._notifyTimer);
            }

            if (duration !== null && typeof commandBar.hideResult === 'function') {
                that._notifyTimer = setTimeout(function () {
                    commandBar.hideResult();
                }, duration);
            }
        };

        that.setName = function (name, options) {
            options = options || {};
            var trimmed = (name || '').trim();
            if (trimmed === that._currentName) {
                return $.Deferred().resolve().promise();
            }

            var previous = that._currentName;
            var request = $.post({
                url: "tasks/setname/",
                data: { name: trimmed },
                success: function success(response) {
                    if (response.Success === true) {
                        that._currentName = trimmed;
                        that._nameInput.val(trimmed);
                        try {
                            document.title = document.title.split(" - ")[0] + ' - ' + (trimmed || 'Untitled');
                        } catch (err) { }
                        if (options.notify !== false) {
                            var displayName = trimmed || 'Untitled';
                            that._notifyCommandBar('Saved project name to "' + displayName + '"');
                        }
                    } else {
                        that._currentName = previous;
                        that.pushResponseStacktrace(that, response);
                        if (options.notify !== false) {
                            that._notifyCommandBar('Error saving project name', { duration: null });
                        }
                    }
                },
                error: function error(jqXHR) {
                    that._currentName = previous;
                    console.log(jqXHR.responseJSON);
                    if (options.notify !== false) {
                        that._notifyCommandBar('Error saving project name', { duration: null });
                    }
                    $("#input_name").val(previous);
                }
            });

            return request;
        };

        that.setNameFromInput = function (options) {
            var value = that._nameInput.val();
            var wait = (options && options.debounceMs) || 800;

            clearTimeout(that._nameDebounceTimer);
            that._nameDebounceTimer = setTimeout(function () {
                that.setName(value, options);
            }, wait);
        };

        that.commitNameFromInput = function (options) {
            var value = that._nameInput.val();
            clearTimeout(that._nameDebounceTimer);
            that.setName(value, options);
        };

        that.setScenario = function (scenario, options) {
            options = options || {};
            var trimmed = (scenario || '').trim();
            if (trimmed === that._currentScenario) {
                return $.Deferred().resolve().promise();
            }

            var previous = that._currentScenario;
            var request = $.post({
                url: "tasks/setscenario/",
                data: { scenario: trimmed },
                success: function success(response) {
                    if (response.Success === true) {
                        that._currentScenario = trimmed;
                        that._scenarioInput.val(trimmed);
                        try {
                            document.title = document.title.split(" - ")[0] + ' - ' + trimmed;
                        } catch (err) { }
                        if (options.notify !== false) {
                            var message = trimmed ? ('Saved scenario to "' + trimmed + '"') : 'Cleared scenario';
                            that._notifyCommandBar(message);
                        }
                    } else {
                        that._currentScenario = previous;
                        that.pushResponseStacktrace(that, response);
                        if (options.notify !== false) {
                            that._notifyCommandBar('Error saving scenario', { duration: null });
                        }
                    }
                },
                error: function error(jqXHR) {
                    that._currentScenario = previous;
                    console.log(jqXHR.responseJSON);
                    if (options.notify !== false) {
                        that._notifyCommandBar('Error saving scenario', { duration: null });
                    }
                    $("#input_scenario").val(previous);
                }
            });

            return request;
        };

        that.setScenarioFromInput = function (options) {
            var value = that._scenarioInput.val();
            var wait = (options && options.debounceMs) || 800;

            clearTimeout(that._scenarioDebounceTimer);
            that._scenarioDebounceTimer = setTimeout(function () {
                that.setScenario(value, options);
            }, wait);
        };

        that.commitScenarioFromInput = function (options) {
            var value = that._scenarioInput.val();
            clearTimeout(that._scenarioDebounceTimer);
            that.setScenario(value, options);
        };

        that.handleGlobalUnitPreference = function (pref) {
            var numericPref = Number(pref);
            if (typeof window.setGlobalUnitizerPreference === 'function') {
                window.setGlobalUnitizerPreference(numericPref);
            }
            that.unitChangeEvent();
        };

        that.handleUnitPreferenceChange = function () {
            that.unitChangeEvent();
        };

        that.clear_locks = function () {

            $.get({
                url: "tasks/clear_locks",
                cache: false,
                success: function success(response) {
                    if (response.Success == true) {
                        alert("Locks have been cleared");
                    } else {
                        alert("Error clearing locks");
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    alert("Error clearing locks");
                }
            });
        };

        that.clear_locks = function () {

            $.get({
                url: "tasks/clear_locks",
                cache: false,
                success: function success(response) {
                    if (response.Success == true) {
                        alert("Locks have been cleared");
                    } else {
                        alert("Error clearing locks");
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    alert("Error clearing locks");
                }
            });
        };

        that.migrate_to_omni = function (state) {
            $.get({
                url: "tasks/omni_migration",
                data: JSON.stringify({ public: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    // TODO: inform user of successful migration and refresh page
                    if (response.Success === true) {
                        alert("Project has been migrated to Omni. Page will now refresh.");
                        window.location.reload();
                    } else {
                        alert("Error migrating project to Omni");
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                }
            });
        };

        that.set_readonly = function (state, options) {
            var self = instance;
            options = options || {};

            var desiredState = !!state;
            var previousState = $('#checkbox_readonly').is(':checked');

            var request = $.post({
                url: "tasks/set_readonly",
                data: JSON.stringify({ readonly: desiredState }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        $('#checkbox_readonly').prop('checked', desiredState);
                        self.set_readonly_controls(desiredState);
                        if (options.notify !== false) {
                            var message = desiredState
                                ? 'READONLY set to True. Project controls disabled.'
                                : 'READONLY set to False. Project controls enabled.';
                            self._notifyCommandBar(message);
                        }
                    } else {
                        $('#checkbox_readonly').prop('checked', previousState);
                        self.pushResponseStacktrace(self, response);
                        if (options.notify !== false) {
                            self._notifyCommandBar('Error updating READONLY state.', { duration: null });
                        }
                    }
                },
                error: function error(jqXHR) {
                    $('#checkbox_readonly').prop('checked', previousState);
                    console.log(jqXHR.responseJSON);
                    if (options.notify !== false) {
                        self._notifyCommandBar('Error updating READONLY state.', { duration: null });
                    }
                },
                fail: function fail(error) {
                    $('#checkbox_readonly').prop('checked', previousState);
                    if (options.notify !== false) {
                        self._notifyCommandBar('Error updating READONLY state.', { duration: null });
                    }
                }
            });

            return request;
        };

        that.set_readonly_controls = function (readonly) {
            if (readonly === true) {
                $('.hide-readonly').hide();

                $('.disable-readonly').each(function () {
                    if ($(this).is(':radio, :checkbox, select, button')) {
                        $(this).prop('disabled', true);
                    } else {
                        $(this).prop('readonly', true);
                    }
                });
            } else {
                $('.hide-readonly').show();

                $('.disable-readonly').each(function () {
                    if ($(this).is(':radio, :checkbox, select, button')) {
                        $(this).prop('disabled', false);
                    } else {
                        $(this).prop('readonly', false);
                    }
                });

                Outlet.getInstance().setMode(0);
            }
        };

        that.set_public = function (state, options) {
            var self = instance;
            options = options || {};

            var desiredState = !!state;
            var previousState = $('#checkbox_public').is(':checked');

            var request = $.post({
                url: "tasks/set_public",
                data: JSON.stringify({ public: desiredState }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        $('#checkbox_public').prop('checked', desiredState);
                        if (options.notify !== false) {
                            var message = desiredState
                                ? 'PUBLIC set to True. Project is now publicly accessible.'
                                : 'PUBLIC set to False. Project access limited to collaborators.';
                            self._notifyCommandBar(message);
                        }
                    } else {
                        $('#checkbox_public').prop('checked', previousState);
                        self.pushResponseStacktrace(self, response);
                        if (options.notify !== false) {
                            self._notifyCommandBar('Error updating PUBLIC state.', { duration: null });
                        }
                    }
                },
                error: function error(jqXHR) {
                    $('#checkbox_public').prop('checked', previousState);
                    console.log(jqXHR.responseJSON);
                    if (options.notify !== false) {
                        self._notifyCommandBar('Error updating PUBLIC state.', { duration: null });
                    }
                },
                fail: function fail(error) {
                    $('#checkbox_public').prop('checked', previousState);
                    if (options.notify !== false) {
                        self._notifyCommandBar('Error updating PUBLIC state.', { duration: null });
                    }
                }
            });

            return request;
        };

        function replaceAll(str, find, replace) {
            return str.replace(new RegExp(find, 'g'), replace);
        }

        that.unitChangeEvent = function () {
            var self = instance;

            var prefs = $("[name^=unitizer_]");

            var unit_preferences = {};
            for (var i = 0; i < prefs.length; i++) {
                var name = prefs[i].name;

                var units = $("input[name='" + name + "']:checked").val();

                name = name.replace('unitizer_', '').replace('_radio', '');

                units = replaceAll(units, '_', '/');
                units = replaceAll(units, '-sqr', '^2');
                units = replaceAll(units, '-cube', '^3');

                unit_preferences[name] = units;
            }

            $.post({
                url: site_prefix + "/runs/" + runid + "/" + config + "/tasks/set_unit_preferences/",
                data: unit_preferences,
                success: function success(response) {
                    if (response.Success === true) { } else { }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });

            self.set_preferred_units();
        };

        that.set_preferred_units = function () {
            var units = undefined;
            var prefs = $("[name^=unitizer_]");
            for (var i = 0; i < prefs.length; i++) {
                var name = prefs[i].name;
                var radios = $("input[name='" + name + "']");
                for (var j = 0; j < radios.length; j++) {
                    units = radios[j].value;
                    $(".units-" + units).addClass("invisible");
                }
                units = $("input[name='" + name + "']:checked").val();
                $(".units-" + units).removeClass("invisible");
            }
        };

        return that;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}();

(function (global) {
    "use strict";

    var FIELD_KIND = {
        locale: "locale",
        dem: "dem",
        delineation_backend: "delineation",
        watershed_representation: "representation",
        wepp_binary: "wepp_binary",
        soil: "soil",
        landuse: "landuse",
        climate: "climate",
        climate_station_database: "climate_station_database"
    };
    var REVIEW_LABELS = {
        locale: "Locale",
        dem: "Elevation source",
        dem_default_cellsize: "DEM default cell size",
        cellsize: "Effective cell size",
        cellsize_source: "Cell-size source",
        delineation_backend: "Delineation backend",
        watershed_representation: "Watershed representation",
        wepp_binary: "WEPP binary version",
        soil: "Soil dataset",
        landuse: "Land-cover dataset",
        climate: "Climate dataset",
        climate_station_database: "Climate Station Database",
        mods: "Initialized modules",
        capabilities: "Derived capabilities",
        config_filename: "Runtime filename"
    };

    function ConfigBuilder(root, dependencies) {
        this.root = root;
        this.http = dependencies && dependencies.http ? dependencies.http : global.WCHttp;
        this.dom = dependencies && dependencies.dom ? dependencies.dom : global.WCDom;
        this.navigate = dependencies && dependencies.navigate ? dependencies.navigate : function (location) {
            global.location.assign(location);
        };
        this.form = root.querySelector("[data-builder-form]");
        this.createButton = root.querySelector("[data-builder-create]");
        this.status = root.querySelector("[data-builder-status]");
        this.summary = root.querySelector("[data-builder-error-summary]");
        this.summaryList = root.querySelector("[data-builder-error-list]");
        this.review = root.querySelector("[data-builder-review]");
        this.reviewList = root.querySelector("[data-builder-review-list]");
        this.changeReason = root.querySelector("[data-builder-change-reason]");
        this.overridePanel = root.querySelector("[data-builder-override]");
        this.overrideSelect = root.querySelector("[name=cellsize_override]");
        this.cellsize = root.querySelector("[data-builder-cellsize]");
        this.modsPanel = root.querySelector("[data-builder-mods]");
        this.modsOptions = root.querySelector("[data-builder-mod-options]");
        this.description = null;
        this.components = {};
        this.localeComponents = {};
        this.validatedReview = null;
        this.busy = false;
        this.validationSequence = 0;
        this.descriptionSequence = 0;
        this.descriptionLoading = false;
        this.creating = false;
        this.creationKey = null;
    }

    ConfigBuilder.prototype._setStatus = function (message, focus) {
        this.dom.setText(this.status, message);
        if (focus) {
            this.status.focus();
        }
    };

    ConfigBuilder.prototype._request = function (url, options) {
        var http = this.http;
        return http.getRqEngineToken().then(function (token) {
            var requestOptions = Object.assign({}, options || {});
            requestOptions.headers = Object.assign({}, requestOptions.headers || {}, {
                Authorization: "Bearer " + token
            });
            return http.request(url, requestOptions);
        });
    };

    ConfigBuilder.prototype._byKind = function (kind) {
        return Object.keys(this.components).map(function (id) {
            return this.components[id];
        }, this).filter(function (component) {
            return component.kind === kind;
        });
    };

    ConfigBuilder.prototype._locale = function () {
        var select = this.form.elements.locale;
        return select && this.components[select.value] ? this.components[select.value] : null;
    };

    ConfigBuilder.prototype._graphAxis = function (name) {
        var locale = this.form.elements.locale && this.form.elements.locale.value;
        var graphs = this.description && this.description.capability_graphs_by_locale;
        var graph = graphs && graphs[locale];
        var axes = graph && graph.capabilities;
        return axes && Array.isArray(axes[name]) ? axes[name].slice() : [];
    };

    ConfigBuilder.prototype._graphDefaults = function () {
        var locale = this.form.elements.locale && this.form.elements.locale.value;
        var graphs = this.description && this.description.capability_graphs_by_locale;
        var graph = graphs && graphs[locale];
        return graph && graph.capability_defaults ? graph.capability_defaults : {};
    };

    ConfigBuilder.prototype._activateLocale = function (localeId) {
        var populations = this.description && this.description.components_by_locale;
        var population = populations && populations[localeId];
        if (!Array.isArray(population)) {
            throw new Error("Builder description has no component population for locale " + localeId + ".");
        }
        this.components = Object.assign({}, this.localeComponents);
        population.forEach(function (component) {
            this.components[component.component_id] = component;
        }, this);
    };

    ConfigBuilder.prototype._modelTuples = function () {
        return this._graphAxis("allowed_model_tuples").map(function (token) {
            var parts = token.split("|");
            return {backend: parts[0], representation: parts[1], binary: parts[2]};
        }).filter(function (item) {
            return item.backend && item.representation && item.binary;
        });
    };

    ConfigBuilder.prototype._setOptions = function (field, allowedIds) {
        var select = this.form.elements[field];
        var previous = select.value;
        var options = allowedIds ? allowedIds.map(function (componentId) {
            return this.components[componentId];
        }, this).filter(function (component) {
            return component && component.kind === FIELD_KIND[field];
        }) : this._byKind(FIELD_KIND[field]);
        select.replaceChildren();
        options.forEach(function (component) {
            var option = global.document.createElement("option");
            option.value = component.component_id;
            option.textContent = component.label;
            option.title = component.description;
            select.appendChild(option);
        });
        if (previous && options.some(function (component) { return component.component_id === previous; })) {
            select.value = previous;
        }
    };

    ConfigBuilder.prototype._selectionSnapshot = function () {
        var snapshot = {};
        Object.keys(FIELD_KIND).forEach(function (field) {
            var select = this.form.elements[field];
            snapshot[field] = select ? select.value : "";
        }, this);
        snapshot.mods = Array.prototype.slice.call(this.modsOptions.querySelectorAll("input:checked")).map(function (input) {
            return input.value;
        });
        return snapshot;
    };

    ConfigBuilder.prototype._announceReplacements = function (previous) {
        var messages = [];
        Object.keys(FIELD_KIND).forEach(function (field) {
            var oldValue = previous && previous[field];
            var select = this.form.elements[field];
            if (!oldValue || !select || select.value === oldValue) { return; }
            var selected = select.options[select.selectedIndex];
            var replacement = selected ? selected.text : "no selection";
            messages.push("The previous " + select.labels[0].textContent + " choice is incompatible with the current combination and was replaced with " + replacement + ".");
        }, this);
        var previousMods = previous && Array.isArray(previous.mods) ? previous.mods : [];
        var currentMods = Array.prototype.slice.call(this.modsOptions.querySelectorAll("input:checked")).map(function (input) {
            return input.value;
        });
        if (previousMods.some(function (id) { return currentMods.indexOf(id) === -1; })) {
            messages.push("Unavailable optional modules were removed from the proposal.");
        }
        if (
            previous && Object.prototype.hasOwnProperty.call(previous, "cellsize_override")
            && this._selections().cellsize_override !== previous.cellsize_override
        ) {
            var dem = this.components[this.form.elements.dem.value];
            var defaultCellsize = dem ? String(dem.default_cellsize) + " metres (registered DEM default)" : "the registered DEM default";
            messages.push("The previous Advanced cell-size override choice is incompatible with the current combination and was replaced with " + defaultCellsize + ".");
        }
        this.dom.setText(this.changeReason, messages.join(" "));
    };

    ConfigBuilder.prototype._renderDependencies = function (announce, changedField) {
        var previous = this._selectionSnapshot();
        var localeId = this.form.elements.locale.value;
        this._activateLocale(localeId);
        var graphAxes = {
            dem: "dem_sources",
            soil: "soil_datasets",
            landuse: "landuse_datasets",
            climate: "climate_datasets",
            climate_station_database: "climate_station_databases"
        };
        Object.keys(graphAxes).forEach(function (field) {
            this._setOptions(field, this._graphAxis(graphAxes[field]));
        }, this);
        if (changedField === "locale") {
            var graphDefaults = this._graphDefaults();
            var defaultFields = {
                dem: "dem_source",
                soil: "soil_dataset",
                landuse: "landuse_dataset",
                climate: "climate_dataset",
                climate_station_database: "climate_station_database"
            };
            Object.keys(defaultFields).forEach(function (field) {
                var value = graphDefaults[defaultFields[field]];
                var select = this.form.elements[field];
                if (value && Array.prototype.some.call(select.options, function (option) {
                    return option.value === value;
                })) {
                    select.value = value;
                }
            }, this);
        }

        var tuples = this._modelTuples();
        var backend = this.form.elements.delineation_backend.value;
        var binary = this.form.elements.wepp_binary.value;
        var representationIds = this._graphAxis("watershed_representations").filter(function (id) {
            return tuples.some(function (item) {
                return item.backend === backend && item.binary === binary && item.representation === id;
            });
        });
        this._setOptions("watershed_representation", representationIds);
        var representation = this.form.elements.watershed_representation.value;
        var binaryIds = this._graphAxis("wepp_binaries").filter(function (id) {
            return tuples.some(function (item) {
                return item.backend === backend && item.representation === representation && item.binary === id;
            });
        });
        this._setOptions("wepp_binary", binaryIds);
        binary = this.form.elements.wepp_binary.value;
        var backendIds = this._graphAxis("delineation_backends").filter(function (id) {
            return tuples.some(function (item) {
                return item.backend === id && item.representation === representation && item.binary === binary;
            });
        });
        this._setOptions("delineation_backend", backendIds);
        this._renderMods(this._graphAxis("mods"), false);
        this._renderCellsize();
        if (announce) { this._announceReplacements(previous); }
    };

    ConfigBuilder.prototype._renderMods = function (allowedIds, announce) {
        var selected = Array.prototype.slice.call(this.modsOptions.querySelectorAll("input:checked")).map(function (input) {
            return input.value;
        });
        var removed = selected.filter(function (id) { return allowedIds.indexOf(id) === -1; });
        this.modsOptions.replaceChildren();
        allowedIds.forEach(function (id) {
            var component = this.components[id];
            if (!component) { return; }
            var label = global.document.createElement("label");
            var input = global.document.createElement("input");
            input.type = "checkbox";
            input.name = "mods";
            input.value = id;
            input.checked = selected.indexOf(id) !== -1;
            label.appendChild(input);
            label.appendChild(global.document.createTextNode(" " + component.label));
            this.modsOptions.appendChild(label);
        }, this);
        this.modsPanel.hidden = allowedIds.length === 0;
        if (announce && removed.length) {
            this.dom.setText(this.changeReason, "Unavailable optional modules were removed from the proposal.");
        }
    };

    ConfigBuilder.prototype._renderCellsize = function () {
        var dem = this.components[this.form.elements.dem.value];
        var defaultValue = dem ? Number(dem.default_cellsize) : null;
        this.dom.setText(this.cellsize, defaultValue ? defaultValue + " metres (registered DEM default)" : "Select an elevation source.");
        this.overridePanel.hidden = !this.description.can_override_cellsize;
        this.overrideSelect.replaceChildren();
        if (!this.description.can_override_cellsize || !defaultValue) { return; }
        this.description.allowed_cell_sizes.forEach(function (value) {
            var option = global.document.createElement("option");
            option.value = String(value);
            option.textContent = String(value) + " metres" + (Number(value) === defaultValue ? " (DEM default)" : " (advanced override)");
            this.overrideSelect.appendChild(option);
        }, this);
        this.overrideSelect.value = String(defaultValue);
    };

    ConfigBuilder.prototype._selections = function () {
        var locale = this._locale();
        var capabilityIds = locale && locale.constraints ? locale.constraints.allowed_capability_profiles || [] : [];
        var payload = {
            locale: this.form.elements.locale.value,
            dem: this.form.elements.dem.value,
            delineation_backend: this.form.elements.delineation_backend.value,
            watershed_representation: this.form.elements.watershed_representation.value,
            wepp_binary: this.form.elements.wepp_binary.value,
            soil: this.form.elements.soil.value,
            landuse: this.form.elements.landuse.value,
            climate: this.form.elements.climate.value,
            climate_station_database: this.form.elements.climate_station_database.value,
            mods: Array.prototype.slice.call(this.modsOptions.querySelectorAll("input:checked")).map(function (input) { return input.value; }),
            capability_profile: capabilityIds[0] || ""
        };
        var dem = this.components[payload.dem];
        if (this.description.can_override_cellsize && dem && Number(this.overrideSelect.value) !== Number(dem.default_cellsize)) {
            payload.cellsize_override = Number(this.overrideSelect.value);
        }
        return payload;
    };

    ConfigBuilder.prototype._clearErrors = function () {
        this.summary.hidden = true;
        this.summaryList.replaceChildren();
        this.root.querySelectorAll("[data-builder-field-error]").forEach(function (node) { node.textContent = ""; });
        this.root.querySelectorAll("[aria-invalid=true]").forEach(function (node) { node.removeAttribute("aria-invalid"); });
    };

    ConfigBuilder.prototype._showErrors = function (errors, focus) {
        var normalized = errors && errors.length ? errors : [{field: "request", message: "The server could not validate this proposal."}];
        this._clearErrors();
        normalized.forEach(function (error) {
            var field = error.field || "request";
            var target = this.form.elements[field] || (field === "cellsize_override" ? this.overrideSelect : null);
            var message = error.message || "This selection is invalid.";
            var fieldError = this.root.querySelector('[data-builder-field-error="' + field + '"]');
            if (fieldError) { fieldError.textContent = message; }
            if (target) { target.setAttribute("aria-invalid", "true"); }
            var item = global.document.createElement("li");
            if (target && target.id) {
                var link = global.document.createElement("a");
                link.href = "#" + target.id;
                link.textContent = message;
                item.appendChild(link);
            } else {
                item.textContent = message;
            }
            this.summaryList.appendChild(item);
        }, this);
        this.summary.hidden = false;
        if (focus) { this.summary.focus(); }
    };

    ConfigBuilder.prototype._displayValue = function (value) {
        if (Array.isArray(value)) { return value.length ? value.join(", ") : "None"; }
        if (value && typeof value === "object") {
            return Object.keys(value).map(function (key) {
                var item = value[key];
                return key + ": " + (Array.isArray(item) ? item.join(", ") : String(item));
            }).join("; ");
        }
        return String(value);
    };

    ConfigBuilder.prototype._renderReview = function (review) {
        this.reviewList.replaceChildren();
        Object.keys(REVIEW_LABELS).forEach(function (key) {
            if (!Object.prototype.hasOwnProperty.call(review, key)) { return; }
            var term = global.document.createElement("dt");
            var detail = global.document.createElement("dd");
            term.textContent = REVIEW_LABELS[key];
            detail.textContent = this._displayValue(review[key]);
            this.reviewList.appendChild(term);
            this.reviewList.appendChild(detail);
        }, this);
        this.review.hidden = false;
    };

    ConfigBuilder.prototype._updateActions = function () {
        this.createButton.disabled = !this.validatedReview || this.busy;
    };

    ConfigBuilder.prototype._setSelectionControlsDisabled = function (disabled) {
        this.form.querySelectorAll("select, input").forEach(function (control) {
            control.disabled = disabled;
        });
    };

    ConfigBuilder.prototype.validate = function (focusErrors) {
        if (!this.description || this.descriptionLoading) { return Promise.resolve(); }
        var sequence = ++this.validationSequence;
        this.validatedReview = null;
        this.creationKey = null;
        this.busy = true;
        this._clearErrors();
        this.review.hidden = true;
        this._setStatus("Validating the complete configuration…", false);
        this._updateActions();
        return this._request(this.root.dataset.validationUrl, {
            method: "POST",
            json: {
                builder_description_schema_version: this.description.builder_description_schema_version,
                registry_revision: this.description.registry_revision,
                selections: this._selections()
            },
            form: this.form
        }).then(function (result) {
            if (sequence !== this.validationSequence) { return; }
            this.validatedReview = result.body.review;
            this._renderReview(this.validatedReview);
            this._setStatus("Configuration is valid and ready for review.", false);
        }.bind(this)).catch(function (error) {
            if (sequence !== this.validationSequence) { return; }
            this._showErrors(error.body && error.body.errors, focusErrors);
            this._setStatus((error.body && error.body.error && error.body.error.details) || "Validation failed.", false);
        }.bind(this)).finally(function () {
            if (sequence !== this.validationSequence) { return; }
            this.busy = false;
            this._updateActions();
        }.bind(this));
    };

    ConfigBuilder.prototype._newCreationKey = function () {
        if (global.crypto && typeof global.crypto.randomUUID === "function") {
            return global.crypto.randomUUID();
        }
        if (global.crypto && typeof global.crypto.getRandomValues === "function") {
            var bytes = new Uint8Array(24);
            global.crypto.getRandomValues(bytes);
            return Array.prototype.map.call(bytes, function (value) { return value.toString(16).padStart(2, "0"); }).join("");
        }
        throw new Error("Secure random creation keys are unavailable in this browser.");
    };

    ConfigBuilder.prototype.create = function () {
        if (this.busy || !this.validatedReview) { return Promise.resolve(); }
        this.creationKey = this.creationKey || this._newCreationKey();
        this.creating = true;
        this.busy = true;
        this._setSelectionControlsDisabled(true);
        this._setStatus("Creating project…", true);
        this._updateActions();
        return this._request(this.root.dataset.creationUrl, {
            method: "POST",
            json: {
                builder_description_schema_version: this.description.builder_description_schema_version,
                registry_revision: this.description.registry_revision,
                selections: this._selections(),
                creation_idempotency_key: this.creationKey
            },
            form: this.form
        }).then(function (result) {
            this._setStatus("Project " + result.body.run_id + " was created. Opening it now…", true);
            this.navigate(result.body.location);
        }.bind(this)).catch(function (error) {
            this.creating = false;
            this.busy = false;
            this._updateActions();
            if (error.status === 409 && error.body && error.body.error && error.body.error.code === "stale_builder_schema") {
                this.validatedReview = null;
                this.review.hidden = true;
                this.creationKey = null;
                return this.loadDescription(true).then(function () {
                    if (this.validatedReview) {
                        this._setStatus("Registered choices changed. The refreshed configuration is valid and ready for review.", true);
                    }
                }.bind(this));
            }
            this._setSelectionControlsDisabled(false);
            this._showErrors(error.body && error.body.errors, true);
            this._setStatus((error.body && error.body.error && error.body.error.details) || "Project creation failed; your selections were retained.", true);
            return undefined;
        }.bind(this));
    };

    ConfigBuilder.prototype.loadDescription = function (preserve) {
        var descriptionSequence = ++this.descriptionSequence;
        ++this.validationSequence;
        this.descriptionLoading = true;
        this.busy = true;
        this.validatedReview = null;
        this.creationKey = null;
        this.review.hidden = true;
        this._clearErrors();
        this._setSelectionControlsDisabled(true);
        this._updateActions();
        return this._request(this.root.dataset.descriptionUrl).then(function (result) {
            if (descriptionSequence !== this.descriptionSequence) { return undefined; }
            var prior = preserve && this.description ? this._selections() : null;
            this.description = result.body;
            if (
                this.description.builder_description_schema_version !== 2
                || !this.description.components_by_locale
                || !this.description.capability_graphs_by_locale
            ) {
                throw new Error("Builder description schema version 2 is required.");
            }
            this.localeComponents = {};
            Object.keys(this.description.components_by_locale).forEach(function (localeId) {
                var localeComponent = this.description.components_by_locale[localeId].find(function (component) {
                    return component.kind === "locale" && component.component_id === localeId;
                });
                if (!localeComponent || !this.description.capability_graphs_by_locale[localeId]) {
                    throw new Error("Builder locale authority is incomplete for " + localeId + ".");
                }
                this.localeComponents[localeId] = localeComponent;
            }, this);
            var initialLocale = prior && prior.locale && this.localeComponents[prior.locale]
                ? prior.locale
                : (this.localeComponents["continental-us"]
                    ? "continental-us"
                    : Object.keys(this.localeComponents)[0]);
            this._activateLocale(initialLocale);
            this._setOptions("locale", null);
            this.form.elements.locale.value = initialLocale;
            this._activateLocale(initialLocale);
            [
                ["dem", "dem_sources"],
                ["delineation_backend", "delineation_backends"],
                ["watershed_representation", "watershed_representations"],
                ["wepp_binary", "wepp_binaries"],
                ["soil", "soil_datasets"],
                ["landuse", "landuse_datasets"],
                ["climate", "climate_datasets"],
                ["climate_station_database", "climate_station_databases"]
            ].forEach(function (entry) {
                this._setOptions(entry[0], this._graphAxis(entry[1]));
            }, this);
            var graphDefaults = this._graphDefaults();
            var defaults = Object.assign({}, this.description.default_selections || {}, {
                dem: graphDefaults.dem_source,
                soil: graphDefaults.soil_dataset,
                landuse: graphDefaults.landuse_dataset,
                climate: graphDefaults.climate_dataset,
                climate_station_database: graphDefaults.climate_station_database,
                delineation_backend: graphDefaults.delineation_backend,
                watershed_representation: graphDefaults.watershed_representation,
                wepp_binary: graphDefaults.wepp_binary
            });
            var priorModelIsValid = !prior || this._modelTuples().some(function (item) {
                return item.backend === prior.delineation_backend
                    && item.representation === prior.watershed_representation
                    && item.binary === prior.wepp_binary;
            });
            var modelFields = ["delineation_backend", "watershed_representation", "wepp_binary"];
            Object.keys(defaults).forEach(function (field) {
                var select = this.form.elements[field];
                if (!select) { return; }
                var requestedValue = prior && prior[field];
                if (!priorModelIsValid && modelFields.indexOf(field) !== -1) {
                    requestedValue = null;
                }
                var value = requestedValue || defaults[field];
                if (requestedValue && !Array.prototype.some.call(select.options, function (option) { return option.value === requestedValue; })) {
                    value = defaults[field];
                }
                if (select && Array.prototype.some.call(select.options, function (option) { return option.value === value; })) {
                    select.value = value;
                }
            }, this);
            this._renderDependencies(false, preserve ? null : "locale");
            if (
                prior && Object.prototype.hasOwnProperty.call(prior, "cellsize_override")
                && this.description.can_override_cellsize
                && this.description.allowed_cell_sizes.indexOf(prior.cellsize_override) !== -1
            ) {
                this.overrideSelect.value = String(prior.cellsize_override);
            }
            if (preserve) { this._announceReplacements(prior); }
            this.descriptionLoading = false;
            this._setSelectionControlsDisabled(false);
            this.busy = false;
            this._updateActions();
            return this.validate(false);
        }.bind(this)).catch(function (error) {
            if (descriptionSequence !== this.descriptionSequence) { return undefined; }
            this.descriptionLoading = false;
            this.busy = false;
            this._setSelectionControlsDisabled(true);
            this._setStatus((error.body && error.body.error && error.body.error.details) || "Registered choices could not be loaded.", true);
            this._updateActions();
            return undefined;
        }.bind(this));
    };

    ConfigBuilder.prototype.init = function () {
        this.dom.delegate(this.form, "change", "select, input", function (event) {
            if (this.descriptionLoading || this.creating) { return; }
            this.validatedReview = null;
            this.creationKey = null;
            this.review.hidden = true;
            this._clearErrors();
            if (event.target && ["locale", "delineation_backend", "watershed_representation", "wepp_binary"].indexOf(event.target.name) !== -1) {
                this._renderDependencies(true, event.target.name);
            } else if (event.target && event.target.name === "dem") {
                this._renderCellsize();
            }
            this.validate(false);
        }.bind(this));
        this.createButton.addEventListener("click", function () { this.create(); }.bind(this));
        return this.loadDescription(false);
    };

    global.ConfigBuilder = ConfigBuilder;
    function initialize() {
        var root = global.document.querySelector("[data-config-builder]");
        if (!root || !global.WCHttp || !global.WCDom) { return; }
        var controller = new ConfigBuilder(root);
        root.configBuilder = controller;
        controller.init();
    }
    if (global.document && global.document.readyState === "loading") {
        global.document.addEventListener("DOMContentLoaded", initialize, {once: true});
    } else if (global.document) {
        initialize();
    }
})(typeof window !== "undefined" ? window : globalThis);

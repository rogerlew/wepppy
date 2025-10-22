(function (global) {
    "use strict";

    var doc = global.document;
    var SAFE_CHECKBOX_VALUES = { on: true, true: true, false: true };

    function getDomHelpers() {
        return global.WCDom || null;
    }

    function toFormElement(form) {
        if (!form) {
            throw new Error("WCForms requires a form element or selector.");
        }
        if (global.HTMLFormElement && form instanceof global.HTMLFormElement) {
            return form;
        }
        if (typeof form === "string") {
            var dom = getDomHelpers();
            if (dom && typeof dom.ensureElement === "function") {
                var resolved = dom.ensureElement(form, "Form selector did not match any element.");
                if (resolved instanceof global.HTMLFormElement) {
                    return resolved;
                }
                throw new Error("Selector did not resolve to a form element.");
            }
            if (!doc) {
                throw new Error("Document context unavailable.");
            }
            var el = doc.querySelector(form);
            if (!el) {
                throw new Error("Form selector did not match any element.");
            }
            if (!(el instanceof global.HTMLFormElement)) {
                throw new Error("Selector did not resolve to a form element.");
            }
            return el;
        }
        if (form.nodeType === 1 && form.tagName && form.tagName.toLowerCase() === "form") {
            return form;
        }
        throw new Error("Unsupported form target.");
    }

    function toElementArray(form) {
        if (!form || !form.elements) {
            return [];
        }
        return Array.prototype.slice.call(form.elements);
    }

    function fieldType(field) {
        if (!field || !field.type) {
            return "";
        }
        return String(field.type).toLowerCase();
    }

    function shouldSkipField(field, includeDisabled) {
        if (!field || !field.name) {
            return true;
        }
        if (!includeDisabled && field.disabled) {
            return true;
        }
        var type = fieldType(field);
        if (field.tagName && field.tagName.toLowerCase() === "fieldset") {
            return true;
        }
        if (["submit", "button", "image", "reset"].indexOf(type) !== -1) {
            return true;
        }
        if (type === "file") {
            return true;
        }
        return false;
    }

    function appendValue(target, name, value) {
        if (Object.prototype.hasOwnProperty.call(target, name)) {
            var existing = target[name];
            if (Array.isArray(existing)) {
                if (Array.isArray(value)) {
                    value.forEach(function (item) {
                        existing.push(item);
                    });
                } else {
                    existing.push(value);
                }
            } else {
                if (Array.isArray(value)) {
                    target[name] = [existing].concat(value);
                } else {
                    target[name] = [existing, value];
                }
            }
        } else {
            target[name] = Array.isArray(value) ? value.slice() : value;
        }
    }

    function setValue(target, name, value) {
        target[name] = value;
    }

    function ensureArray(value) {
        if (Array.isArray(value)) {
            return value;
        }
        return [value];
    }

    function serializeFormToParams(form, includeDisabled) {
        var params = new URLSearchParams();
        toElementArray(form).forEach(function (field) {
            if (shouldSkipField(field, includeDisabled)) {
                return;
            }
            var type = fieldType(field);
            if (type === "checkbox" || type === "radio") {
                if (field.checked) {
                    params.append(field.name, field.value || "on");
                }
                return;
            }
            if (field.tagName && field.tagName.toLowerCase() === "select") {
                var options = field.options || [];
                for (var i = 0; i < options.length; i += 1) {
                    var option = options[i];
                    if (option.selected) {
                        params.append(field.name, option.value);
                    }
                }
                return;
            }
            params.append(field.name, field.value);
        });
        return params;
    }

    // Produce a plain object mirroring jQuery's multi-value semantics while normalizing checkboxes.
    function serializeFormToObject(form, includeDisabled) {
        var result = Object.create(null);
        var elements = toElementArray(form);
        var checkboxGroups = Object.create(null);

        elements.forEach(function (field) {
            if (shouldSkipField(field, includeDisabled)) {
                return;
            }
            var type = fieldType(field);
            if (type === "checkbox") {
                if (!checkboxGroups[field.name]) {
                    checkboxGroups[field.name] = [];
                }
                checkboxGroups[field.name].push(field);
                return;
            }
            if (type === "radio") {
                if (field.checked) {
                    setValue(result, field.name, field.value);
                } else if (!Object.prototype.hasOwnProperty.call(result, field.name)) {
                    setValue(result, field.name, null);
                }
                return;
            }
            if (field.tagName && field.tagName.toLowerCase() === "select") {
                var selectValues = [];
                var options = field.options || [];
                for (var i = 0; i < options.length; i += 1) {
                    var option = options[i];
                    if (option.selected) {
                        selectValues.push(option.value);
                    }
                }
                if (field.multiple) {
                    setValue(result, field.name, selectValues);
                } else if (selectValues.length > 0) {
                    setValue(result, field.name, selectValues[0]);
                } else {
                    setValue(result, field.name, null);
                }
                return;
            }
            appendValue(result, field.name, field.value);
        });

        Object.keys(checkboxGroups).forEach(function (name) {
            var group = checkboxGroups[name];
            if (!group || group.length === 0) {
                return;
            }
            if (group.length === 1 && SAFE_CHECKBOX_VALUES[group[0].value || "on"]) {
                setValue(result, name, Boolean(group[0].checked));
                return;
            }
            var values = [];
            group.forEach(function (field) {
                if (field.checked) {
                    values.push(field.value || "on");
                }
            });
            setValue(result, name, values);
        });

        return result;
    }

    function serializeFields(fields, format) {
        if (!Array.isArray(fields)) {
            throw new Error("serializeFields expects an array of field descriptors.");
        }
        var formatType = format || "url";
        if (formatType === "url") {
            var params = new URLSearchParams();
            fields.forEach(function (field) {
                if (!field || !field.name) {
                    return;
                }
                var type = field.type ? String(field.type).toLowerCase() : "";
                if (type === "checkbox") {
                    if (field.checked) {
                        params.append(field.name, field.value || "on");
                    }
                    return;
                }
                if (Array.isArray(field.value)) {
                    field.value.forEach(function (value) {
                        params.append(field.name, value);
                    });
                    return;
                }
                if (field.value !== undefined && field.value !== null) {
                    params.append(field.name, field.value);
                }
            });
            return params;
        }

        var result = Object.create(null);
        fields.forEach(function (field) {
            if (!field || !field.name) {
                return;
            }
            var type = field.type ? String(field.type).toLowerCase() : "";
            if (type === "checkbox") {
                if (field.checked === undefined) {
                    appendValue(result, field.name, Boolean(field.value));
                } else {
                    setValue(result, field.name, Boolean(field.checked));
                }
                return;
            }
            if (Array.isArray(field.value)) {
                appendValue(result, field.name, field.value.slice());
            } else {
                appendValue(result, field.name, field.value);
            }
        });
        return result;
    }

    function serializeForm(form, options) {
        var formElement = toFormElement(form);
        var opts = options || {};
        var format = opts.format || "url";
        var includeDisabled = Boolean(opts.includeDisabled);
        if (format === "url") {
            return serializeFormToParams(formElement, includeDisabled);
        }
        if (format === "object" || format === "json") {
            return serializeFormToObject(formElement, includeDisabled);
        }
        throw new Error("Unsupported serialization format: " + format);
    }

    function formToJSON(form) {
        return serializeForm(form, { format: "json" });
    }

    // Apply an object's values back onto the matching form controls (radios, checkboxes, selects, text).
    function applyValues(form, values) {
        if (!values || typeof values !== "object") {
            return;
        }
        var formElement = toFormElement(form);
        Object.keys(values).forEach(function (name) {
            var fields = formElement.elements.namedItem(name);
            if (!fields) {
                return;
            }
            var value = values[name];
            var isElement = fields instanceof global.Element;
            if (fields instanceof global.RadioNodeList || (fields.length && fields[0] && !isElement)) {
                var list = Array.prototype.slice.call(fields);
                list.forEach(function (field) {
                    var type = fieldType(field);
                    if (type === "checkbox") {
                        if (Array.isArray(value)) {
                            field.checked = value.indexOf(field.value) !== -1;
                        } else {
                            field.checked = Boolean(value);
                        }
                        return;
                    }
                    if (type === "radio") {
                        field.checked = String(field.value) === String(value);
                        return;
                    }
                    if (field.tagName && field.tagName.toLowerCase() === "select" && field.multiple) {
                        var targetValues = ensureArray(value).map(String);
                        Array.prototype.slice.call(field.options).forEach(function (option) {
                            option.selected = targetValues.indexOf(option.value) !== -1;
                        });
                        return;
                    }
                    field.value = value;
                });
                return;
            }
            var singleField = fields;
            if (singleField instanceof global.HTMLSelectElement && singleField.multiple) {
                var multiValues = ensureArray(value).map(String);
                Array.prototype.slice.call(singleField.options).forEach(function (option) {
                    option.selected = multiValues.indexOf(option.value) !== -1;
                });
                return;
            }
            var type = fieldType(singleField);
            if (type === "checkbox") {
                if (Array.isArray(value)) {
                    singleField.checked = value.indexOf(singleField.value) !== -1;
                } else {
                    singleField.checked = Boolean(value);
                }
                return;
            }
            if (type === "radio") {
                singleField.checked = String(singleField.value) === String(value);
                return;
            }
            if (singleField.tagName && singleField.tagName.toLowerCase() === "select" && singleField.multiple) {
                var valuesArray = ensureArray(value).map(String);
                Array.prototype.slice.call(singleField.options).forEach(function (option) {
                    option.selected = valuesArray.indexOf(option.value) !== -1;
                });
                return;
            }
            singleField.value = value === undefined || value === null ? "" : value;
        });
    }

    function readCookie(name) {
        if (!doc || !doc.cookie) {
            return null;
        }
        var escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        var pattern = new RegExp("(?:^|; )" + escapedName + "=([^;]*)");
        var match = doc.cookie.match(pattern);
        return match ? decodeURIComponent(match[1]) : null;
    }

    // Locate a CSRF token from globals, meta tags, the provided form, or well-known cookies.
    function findCsrfToken(form) {
        if (global.__csrfToken) {
            return global.__csrfToken;
        }
        if (global.csrfToken && typeof global.csrfToken === "function") {
            try {
                var token = global.csrfToken();
                if (token) {
                    return token;
                }
            } catch (err) {
                // ignore
            }
        }
        if (global.csrf_token && typeof global.csrf_token === "function") {
            try {
                var tokenFn = global.csrf_token();
                if (tokenFn) {
                    return tokenFn;
                }
            } catch (err) {
                // ignore
            }
        }
        if (doc) {
            var meta = doc.querySelector('meta[name="csrf-token"]');
            if (meta && meta.getAttribute("content")) {
                return meta.getAttribute("content");
            }
        }
        if (form) {
            try {
                var formElement = toFormElement(form);
                var field = formElement.querySelector('input[name="csrf_token"]');
                if (field && field.value) {
                    return field.value;
                }
            } catch (err) {
                // ignore
            }
        }
        var cookieToken = readCookie("csrftoken") || readCookie("csrf_token");
        if (cookieToken) {
            return cookieToken;
        }
        return null;
    }

    global.WCForms = {
        serializeForm: serializeForm,
        serializeFields: serializeFields,
        formToJSON: formToJSON,
        applyValues: applyValues,
        findCsrfToken: findCsrfToken
    };
})(typeof window !== "undefined" ? window : this);

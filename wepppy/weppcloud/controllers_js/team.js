/* ----------------------------------------------------------------------------
 * Team
 * ----------------------------------------------------------------------------
 */
var Team = (function () {
    "use strict";

    var instance;

    var FORM_SELECTOR = "#team_form";
    var MEMBERS_CONTAINER_SELECTOR = "#team-info";
    var EMAIL_FIELD_SELECTOR = '[data-team-field="email"]';
    var ACTION_SELECTOR = "[data-team-action]";
    var STATUS_PANEL_SELECTOR = "#team_status_panel";
    var STACKTRACE_PANEL_SELECTOR = "#team_stacktrace_panel";
    var HINT_SELECTOR = "#hint_run_team";

    var EVENT_NAMES = [
        "team:list:loading",
        "team:list:loaded",
        "team:list:failed",
        "team:invite:started",
        "team:invite:sent",
        "team:invite:failed",
        "team:member:remove:started",
        "team:member:removed",
        "team:member:remove:failed",
        "team:status:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" || typeof dom.ensureElement !== "function") {
            throw new Error("Team controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Team controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.request !== "function") {
            throw new Error("Team controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("Team controller requires WCEvents helpers.");
        }

        return {
            dom: dom,
            forms: forms,
            http: http,
            events: events
        };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return null;
        }
        return {
            text: function (value) {
                element.textContent = value === undefined || value === null ? "" : String(value);
            },
            html: function (html) {
                element.innerHTML = html === undefined || html === null ? "" : String(html);
            },
            append: function (html) {
                if (html === undefined || html === null) {
                    return;
                }
                if (typeof html === "string") {
                    element.insertAdjacentHTML("beforeend", html);
                    return;
                }
                if (typeof window.Node !== "undefined" && html instanceof window.Node) {
                    element.appendChild(html);
                }
            },
            show: function () {
                element.hidden = false;
                element.style.removeProperty("display");
            },
            hide: function () {
                element.hidden = true;
                element.style.display = "none";
            },
            empty: function () {
                element.textContent = "";
            }
        };
    }

    function toResponsePayload(http, error) {
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error.detail || error.body || error.message || "Request failed";
            if (detail && typeof detail === "object") {
                return detail;
            }
            return { Error: detail };
        }
        if (error && typeof error === "object" && error.Error) {
            return error;
        }
        return { Error: (error && error.message) || "Request failed" };
    }

    function getActiveRunId() {
        return window.runid || window.runId || null;
    }

    function setButtonPending(button, isPending) {
        if (!button) {
            return;
        }
        if (isPending) {
            button.dataset.teamPrevDisabled = button.disabled ? "true" : "false";
            button.dataset.teamPending = "true";
            button.disabled = true;
            return;
        }
        delete button.dataset.teamPending;
        if (button.dataset.jobDisabled === "true") {
            return;
        }
        if (button.dataset.teamPrevDisabled !== "true") {
            button.disabled = false;
        }
        delete button.dataset.teamPrevDisabled;
    }

    function readEmailValue(forms, form) {
        var payload = {};
        try {
            payload = forms.serializeForm(form, { format: "object" }) || {};
        } catch (err) {
            payload = {};
        }
        var raw = Object.prototype.hasOwnProperty.call(payload, "email") ? payload.email : payload["adduser-email"];
        if (Array.isArray(raw)) {
            raw = raw[0];
        }
        if (raw === undefined || raw === null) {
            return "";
        }
        return String(raw).trim();
    }

    function normaliseHtmlContent(content) {
        if (content === undefined || content === null) {
            return "";
        }
        if (typeof content === "string") {
            return content;
        }
        if (typeof content === "object" && content !== null && content.html !== undefined) {
            return String(content.html);
        }
        return String(content);
    }

    function normaliseUserId(value) {
        if (value === undefined || value === null) {
            return null;
        }
        var candidate = value;
        if (Array.isArray(candidate)) {
            candidate = candidate[0];
        }
        if (typeof candidate === "string") {
            candidate = candidate.trim();
            if (candidate.length === 0) {
                return null;
            }
        }
        var parsed = parseInt(candidate, 10);
        if (Number.isNaN(parsed)) {
            return null;
        }
        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var team = controlBase();

        var formElement = dom.ensureElement(FORM_SELECTOR, "Team form not found.");
        var infoElement = dom.qs("#team_form #info");
        var statusElement = dom.qs("#team_form #status");
        var stacktraceElement = dom.qs("#team_form #stacktrace");
        var hintElement = dom.qs(HINT_SELECTOR);
        var statusPanelElement = dom.qs(STATUS_PANEL_SELECTOR);
        var stacktracePanelElement = dom.qs(STACKTRACE_PANEL_SELECTOR);
        var membersElement = dom.qs(MEMBERS_CONTAINER_SELECTOR, formElement);
        if (!membersElement) {
            throw new Error("Team members container not found.");
        }
        var emailInput = dom.qs(EMAIL_FIELD_SELECTOR, formElement);

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        team.form = formElement;
        team.info = infoAdapter;
        team.status = statusAdapter;
        team.stacktrace = stacktraceAdapter;
        team.hint = hintAdapter;
        team.statusPanelEl = statusPanelElement || null;
        team.stacktracePanelEl = stacktracePanelElement || null;
        team.statusSpinnerEl = team.statusPanelEl ? team.statusPanelEl.querySelector("#braille") : null;
        team.command_btn_id = "btn_adduser";
        team.events = emitter;
        team.membersElement = membersElement;
        team.emailInput = emailInput || null;
        team._delegates = [];

        team.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (team.statusStream && typeof team.statusStream.append === "function") {
                team.statusStream.append(message, meta || null);
            } else if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.innerHTML = message;
            }
            emitter.emit("team:status:updated", {
                message: message,
                meta: meta || null
            });
        };

        team.hideStacktrace = function () {
            if (team.stacktrace && typeof team.stacktrace.hide === "function") {
                team.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                if (typeof dom.hide === "function") {
                    dom.hide(stacktraceElement);
                } else {
                    stacktraceElement.hidden = true;
                    stacktraceElement.style.display = "none";
                }
            }
        };

        function attachStatusChannel() {
            team.attach_status_stream(team, {
                element: team.statusPanelEl,
                form: formElement,
                channel: "team",
                runId: getActiveRunId(),
                stacktrace: team.stacktracePanelEl ? { element: team.stacktracePanelEl } : null,
                spinner: team.statusSpinnerEl,
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        team.triggerEvent(detail.event, detail);
                    }
                    emitter.emit("team:status:updated", detail || {});
                }
            });
        }

        function refreshMembers(options) {
            var opts = options || {};
            emitter.emit("team:list:loading");
            return http.request(url_for_run("report/users/"), {
                method: "GET",
                params: { _: Date.now() }
            }).then(function (result) {
                var body = result && result.body !== undefined ? result.body : result;
                var html = normaliseHtmlContent(body);
                membersElement.innerHTML = html;
                emitter.emit("team:list:loaded", {
                    html: html,
                    response: body
                });
                if (!opts.silentStatus) {
                    team.appendStatus("Team roster updated.");
                }
                return html;
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                if (!payload.Error) {
                    payload.Error = "Unable to load collaborator list.";
                }
                team.appendStatus(payload.Error);
                team.pushResponseStacktrace(team, payload);
                emitter.emit("team:list:failed", {
                    error: payload
                });
                throw payload;
            });
        }

        function inviteCollaborator(email, options) {
            var opts = options || {};
            var button = opts.button || null;
            var trimmed = (email || "").trim();

            if (!trimmed) {
                var validationError = { Error: "Email address is required." };
                team.appendStatus(validationError.Error);
                emitter.emit("team:invite:failed", {
                    email: "",
                    error: validationError
                });
                return Promise.resolve(null);
            }

            team.hideStacktrace();
            setButtonPending(button, true);
            emitter.emit("team:invite:started", { email: trimmed });
            team.triggerEvent("job:started", { task: "team:adduser", email: trimmed });

            return http.postJson("tasks/adduser/", { email: trimmed }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    if (!response || response.Success !== true) {
                        throw response || { Error: "Collaborator invite failed." };
                    }
                    var content = response.Content || response.content || {};
                    var alreadyMember = Boolean(content.already_member);
                    var statusMessage = alreadyMember ? "Collaborator already has access." : "Collaborator invited.";
                    team.appendStatus(statusMessage, { alreadyMember: alreadyMember });
                    if (team.emailInput) {
                        team.emailInput.value = "";
                    }
                    emitter.emit("team:invite:sent", {
                        email: trimmed,
                        response: response,
                        alreadyMember: alreadyMember
                    });
                    team.triggerEvent("TEAM_ADDUSER_TASK_COMPLETED", {
                        email: trimmed,
                        response: response,
                        alreadyMember: alreadyMember
                    });
                    team.triggerEvent("job:completed", {
                        task: "team:adduser",
                        email: trimmed,
                        response: response
                    });
                    return refreshMembers({ silentStatus: true }).then(function () {
                        return response;
                    });
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    if (!payload.Error) {
                        payload.Error = "Collaborator invite failed.";
                    }
                    team.appendStatus(payload.Error);
                    team.pushResponseStacktrace(team, payload);
                    emitter.emit("team:invite:failed", {
                        email: trimmed,
                        error: payload
                    });
                    team.triggerEvent("job:error", {
                        task: "team:adduser",
                        email: trimmed,
                        error: payload
                    });
                    throw payload;
                })
                .finally(function () {
                    setButtonPending(button, false);
                });
        }

        function removeMemberById(userId, options) {
            var opts = options || {};
            var button = opts.button || null;
            var normalisedId = normaliseUserId(userId);

            if (normalisedId === null) {
                var validationError = { Error: "user_id is required." };
                team.appendStatus(validationError.Error);
                emitter.emit("team:member:remove:failed", {
                    userId: userId,
                    error: validationError
                });
                return Promise.resolve(null);
            }

            team.hideStacktrace();
            setButtonPending(button, true);
            emitter.emit("team:member:remove:started", { userId: normalisedId });
            team.triggerEvent("job:started", { task: "team:removeuser", userId: normalisedId });

            return http.postJson("tasks/removeuser/", { user_id: normalisedId }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    if (!response || response.Success !== true) {
                        throw response || { Error: "Collaborator removal failed." };
                    }
                    var content = response.Content || response.content || {};
                    var alreadyRemoved = Boolean(content.already_removed);
                    var statusMessage = alreadyRemoved ? "Collaborator already removed." : "Collaborator removed.";
                    team.appendStatus(statusMessage, { alreadyRemoved: alreadyRemoved });
                    emitter.emit("team:member:removed", {
                        userId: normalisedId,
                        response: response,
                        alreadyRemoved: alreadyRemoved
                    });
                    team.triggerEvent("TEAM_REMOVEUSER_TASK_COMPLETED", {
                        user_id: normalisedId,
                        response: response,
                        alreadyRemoved: alreadyRemoved
                    });
                    team.triggerEvent("job:completed", {
                        task: "team:removeuser",
                        userId: normalisedId,
                        response: response
                    });
                    return refreshMembers({ silentStatus: true }).then(function () {
                        return response;
                    });
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    if (!payload.Error) {
                        payload.Error = "Collaborator removal failed.";
                    }
                    team.appendStatus(payload.Error);
                    team.pushResponseStacktrace(team, payload);
                    emitter.emit("team:member:remove:failed", {
                        userId: normalisedId,
                        error: payload
                    });
                    team.triggerEvent("job:error", {
                        task: "team:removeuser",
                        userId: normalisedId,
                        error: payload
                    });
                    throw payload;
                })
                .finally(function () {
                    setButtonPending(button, false);
                });
        }

        function handleAction(event, target) {
            if (!target || !target.dataset) {
                return;
            }
            var action = target.dataset.teamAction;
            if (!action) {
                return;
            }
            if (action === "invite") {
                event.preventDefault();
                team.inviteFromForm({ button: target });
                return;
            }
            if (action === "remove") {
                event.preventDefault();
                var userIdValue = target.getAttribute("data-team-user-id") || target.dataset.teamUserId;
                team.removeMemberById(userIdValue, { button: target });
            }
        }

        team._delegates.push(dom.delegate(formElement, "click", ACTION_SELECTOR, handleAction));

        team.refreshMembers = refreshMembers;
        team.inviteCollaborator = function (email, options) {
            return inviteCollaborator(email, options || {});
        };
        team.inviteFromForm = function (options) {
            var btn = options && options.button ? options.button : null;
            var email = readEmailValue(forms, formElement);
            return inviteCollaborator(email, { button: btn });
        };
        team.adduser = function (email) {
            return inviteCollaborator(email || "", {});
        };
        team.adduser_click = function () {
            var button = dom.qs('[data-team-action="invite"]', formElement) || null;
            return team.inviteFromForm({ button: button });
        };
        team.removeMemberById = function (userId, options) {
            return removeMemberById(userId, options || {});
        };
        team.removeuser = function (userId) {
            return removeMemberById(userId, {});
        };
        team.report = function () {
            return refreshMembers({});
        };

        attachStatusChannel();
        refreshMembers({ silentStatus: true });

        return team;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.Team = Team;
}

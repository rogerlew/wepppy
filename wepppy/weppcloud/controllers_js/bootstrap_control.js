/* ----------------------------------------------------------------------------
 * Bootstrap Control
 * ----------------------------------------------------------------------------
 */
var BootstrapControl = (function () {
    "use strict";

    var instance;

    var SELECTORS = {
        root: "[data-bootstrap-root]",
        message: "[data-bootstrap-message]",
        messageBody: "[data-bootstrap-message-body]",
        disabledSection: "[data-bootstrap-disabled]",
        enabledSection: "[data-bootstrap-enabled]",
        cloneCommandInput: "[data-bootstrap-clone-command]",
        remoteCommandInput: "[data-bootstrap-remote-command]",
        currentRef: "[data-bootstrap-current-ref]",
        commitSelect: "[data-bootstrap-field=\"commit\"]",
        commitMeta: "[data-bootstrap-commit-meta]",
        actionEnable: "[data-bootstrap-action=\"enable\"]",
        actionMint: "[data-bootstrap-action=\"mint\"]",
        actionRefresh: "[data-bootstrap-action=\"refresh\"]",
        actionCheckout: "[data-bootstrap-action=\"checkout\"]",
        actionCopyClone: "[data-bootstrap-action=\"copy-clone\"]",
        actionCopyRemote: "[data-bootstrap-action=\"copy-remote\"]",
        actionDisable: "[data-bootstrap-action=\"disable\"]"
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function") {
            throw new Error("BootstrapControl requires WCDom helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("BootstrapControl requires WCHttp helpers.");
        }

        return { dom: dom, http: http };
    }

    function normalizeErrorValue(value) {
        if (value === undefined || value === null) {
            return null;
        }
        if (typeof value === "string") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(function (item) {
                return item === undefined || item === null ? "" : String(item);
            }).join("\n");
        }
        if (typeof value === "object") {
            if (typeof value.message === "string") {
                return value.message;
            }
            if (typeof value.detail === "string") {
                return value.detail;
            }
            if (typeof value.details === "string") {
                return value.details;
            }
            if (value.details !== undefined) {
                return normalizeErrorValue(value.details);
            }
            try {
                return JSON.stringify(value);
            } catch (err) {
                return String(value);
            }
        }
        return String(value);
    }

    function formatErrorList(errors) {
        if (!Array.isArray(errors)) {
            return null;
        }
        var parts = [];
        errors.forEach(function (entry) {
            if (entry === undefined || entry === null) {
                return;
            }
            if (typeof entry === "string") {
                parts.push(entry);
                return;
            }
            if (typeof entry.message === "string") {
                parts.push(entry.message);
                return;
            }
            if (typeof entry.detail === "string") {
                parts.push(entry.detail);
                return;
            }
            if (typeof entry.code === "string") {
                parts.push(entry.code);
                return;
            }
            try {
                parts.push(JSON.stringify(entry));
            } catch (err) {
                parts.push(String(entry));
            }
        });
        return parts.length ? parts.join("\n") : null;
    }

    function resolveErrorMessage(payload, fallback) {
        if (!payload) {
            return fallback || null;
        }
        if (payload.error !== undefined) {
            return normalizeErrorValue(payload.error) || fallback || null;
        }
        if (payload.errors) {
            var errorList = formatErrorList(payload.errors);
            if (errorList) {
                return errorList;
            }
        }
        if (payload.message !== undefined) {
            return normalizeErrorValue(payload.message);
        }
        if (payload.detail !== undefined) {
            return normalizeErrorValue(payload.detail);
        }
        return fallback || null;
    }

    function resolveHttpErrorMessage(error, fallback) {
        if (!error) {
            return fallback || "Request failed";
        }
        if (error.detail !== undefined && error.detail !== null) {
            if (typeof error.detail === "object") {
                return resolveErrorMessage(error.detail, fallback || "Request failed") || fallback || "Request failed";
            }
            return normalizeErrorValue(error.detail) || fallback || "Request failed";
        }
        if (error.body && typeof error.body === "object") {
            return resolveErrorMessage(error.body, fallback || "Request failed") || fallback || "Request failed";
        }
        return error.message || fallback || "Request failed";
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;

        var control = controlBase();
        var formElement = dom.qs("#wepp_form");

        var elements = {
            root: dom.qs(SELECTORS.root),
            message: dom.qs(SELECTORS.message),
            messageBody: dom.qs(SELECTORS.messageBody),
            disabledSection: dom.qs(SELECTORS.disabledSection),
            enabledSection: dom.qs(SELECTORS.enabledSection),
            cloneCommandInput: dom.qs(SELECTORS.cloneCommandInput),
            remoteCommandInput: dom.qs(SELECTORS.remoteCommandInput),
            currentRef: dom.qs(SELECTORS.currentRef),
            commitSelect: dom.qs(SELECTORS.commitSelect),
            commitMeta: dom.qs(SELECTORS.commitMeta),
            enableButton: dom.qs(SELECTORS.actionEnable),
            mintButton: dom.qs(SELECTORS.actionMint),
            refreshButton: dom.qs(SELECTORS.actionRefresh),
            checkoutButton: dom.qs(SELECTORS.actionCheckout),
            copyCloneButton: dom.qs(SELECTORS.actionCopyClone),
            copyRemoteButton: dom.qs(SELECTORS.actionCopyRemote),
            disableButton: dom.qs(SELECTORS.actionDisable)
        };

        var state = {
            bound: false,
            enabled: false,
            adminDisabled: false,
            isAnonymous: false,
            isAuthenticated: false,
            isAdmin: false,
            cloneUrl: "",
            cloneCommand: "",
            remoteCommand: "",
            commits: [],
            selectedSha: null,
            currentRef: "",
            alert: null
        };

        function syncElements() {
            elements.root = dom.qs(SELECTORS.root);
            elements.message = dom.qs(SELECTORS.message);
            elements.messageBody = dom.qs(SELECTORS.messageBody);
            elements.disabledSection = dom.qs(SELECTORS.disabledSection);
            elements.enabledSection = dom.qs(SELECTORS.enabledSection);
            elements.cloneCommandInput = dom.qs(SELECTORS.cloneCommandInput);
            elements.remoteCommandInput = dom.qs(SELECTORS.remoteCommandInput);
            elements.currentRef = dom.qs(SELECTORS.currentRef);
            elements.commitSelect = dom.qs(SELECTORS.commitSelect);
            elements.commitMeta = dom.qs(SELECTORS.commitMeta);
            elements.enableButton = dom.qs(SELECTORS.actionEnable);
            elements.mintButton = dom.qs(SELECTORS.actionMint);
            elements.refreshButton = dom.qs(SELECTORS.actionRefresh);
            elements.checkoutButton = dom.qs(SELECTORS.actionCheckout);
            elements.copyCloneButton = dom.qs(SELECTORS.actionCopyClone);
            elements.copyRemoteButton = dom.qs(SELECTORS.actionCopyRemote);
            elements.disableButton = dom.qs(SELECTORS.actionDisable);
        }

        function setAlert(type, message) {
            state.alert = message ? { type: type || "info", message: String(message) } : null;
            renderAlert();
        }

        function renderAlert() {
            if (!elements.message || !elements.messageBody) {
                return;
            }
            var notice = null;
            if (!state.isAuthenticated) {
                notice = { type: "warning", message: "Sign in to enable Bootstrap." };
            } else if (state.isAnonymous) {
                notice = { type: "warning", message: "Bootstrap requires a non-anonymous run." };
            } else if (state.adminDisabled) {
                notice = { type: "warning", message: "Bootstrap is disabled by an administrator." };
            }
            var active = notice || state.alert;
            if (!active || !active.message) {
                elements.message.hidden = true;
                elements.messageBody.textContent = "";
                return;
            }
            elements.message.hidden = false;
            elements.messageBody.textContent = active.message;

            var classList = elements.message.classList;
            if (classList) {
                ["info", "warning", "error", "success"].forEach(function (variant) {
                    classList.remove("wc-alert--" + variant);
                });
                classList.add("wc-alert--" + (active.type || "info"));
            }
        }

        function showSection(element, show) {
            if (!element) {
                return;
            }
            element.hidden = !show;
        }

        function setDisabled(element, disabled) {
            if (!element) {
                return;
            }
            element.disabled = Boolean(disabled);
        }

        function getContent(payload) {
            if (!payload || typeof payload !== "object") {
                return {};
            }
            return payload.Content || payload.content || {};
        }

        function isErrorPayload(payload) {
            return Boolean(payload && (payload.error || payload.errors));
        }

        function buildCloneCommand(url) {
            return url ? "git clone " + url : "";
        }

        function buildRemoteCommand(url) {
            return url ? "git remote set-url origin " + url : "";
        }

        function updateCloneUrl(url) {
            state.cloneUrl = url || "";
            state.cloneCommand = buildCloneCommand(state.cloneUrl);
            state.remoteCommand = buildRemoteCommand(state.cloneUrl);
            if (elements.cloneCommandInput) {
                elements.cloneCommandInput.value = state.cloneCommand;
            }
            if (elements.remoteCommandInput) {
                elements.remoteCommandInput.value = state.remoteCommand;
            }
            setDisabled(elements.copyCloneButton, !state.cloneCommand);
            setDisabled(elements.copyRemoteButton, !state.remoteCommand);
        }

        function updateCurrentRef(value) {
            state.currentRef = value || "";
            if (elements.currentRef) {
                elements.currentRef.textContent = state.currentRef || "—";
            }
        }

        function commitDisplayText(commit) {
            if (!commit) {
                return "";
            }
            var shortSha = commit.short_sha || (commit.sha ? String(commit.sha).slice(0, 7) : "");
            var message = commit.message || "";
            if (message.length > 80) {
                message = message.slice(0, 77) + "...";
            }
            if (shortSha) {
                return shortSha + " — " + message;
            }
            return message;
        }

        function renderCommitMeta(commit) {
            if (!elements.commitMeta) {
                return;
            }
            if (!commit) {
                elements.commitMeta.textContent = "—";
                return;
            }
            var parts = [];
            if (commit.author) {
                parts.push("Pusher: " + commit.author);
            }
            if (commit.git_author && commit.git_author !== commit.author) {
                parts.push("Git author: " + commit.git_author);
            }
            if (commit.date) {
                parts.push(commit.date);
            }
            elements.commitMeta.textContent = parts.length ? parts.join(" · ") : "—";
        }

        function findCommit(sha) {
            if (!sha) {
                return null;
            }
            return state.commits.find(function (entry) {
                return entry && entry.sha === sha;
            }) || null;
        }

        function renderCommitOptions() {
            if (!elements.commitSelect) {
                return;
            }
            elements.commitSelect.innerHTML = "";

            if (!state.commits.length) {
                var emptyOption = document.createElement("option");
                emptyOption.value = "";
                emptyOption.textContent = "No commits available.";
                elements.commitSelect.appendChild(emptyOption);
                elements.commitSelect.disabled = true;
                renderCommitMeta(null);
                return;
            }

            state.commits.forEach(function (commit) {
                var option = document.createElement("option");
                option.value = commit.sha || "";
                option.textContent = commitDisplayText(commit);
                elements.commitSelect.appendChild(option);
            });

            var targetSha = state.selectedSha;
            if (!targetSha || !findCommit(targetSha)) {
                targetSha = state.commits[0].sha;
            }
            state.selectedSha = targetSha;
            elements.commitSelect.value = targetSha || "";
            elements.commitSelect.disabled = false;
            renderCommitMeta(findCommit(targetSha));
            renderState();
        }

        function renderAdminButton() {
            if (!elements.disableButton) {
                return;
            }
            elements.disableButton.textContent = state.adminDisabled
                ? "Re-enable Bootstrap (Admin)"
                : "Disable Bootstrap (Admin)";
        }

        function renderState() {
            showSection(elements.enabledSection, state.enabled);
            showSection(elements.disabledSection, !state.enabled);

            var canEnable = state.isAuthenticated && !state.isAnonymous && !state.adminDisabled;
            var canMint = state.enabled && state.isAuthenticated && !state.isAnonymous && !state.adminDisabled;
            var canRefresh = state.enabled;
            var canCheckout = state.enabled && Boolean(state.selectedSha);
            var canCopyClone = Boolean(state.cloneCommand);
            var canCopyRemote = Boolean(state.remoteCommand);
            var canAdminToggle = state.isAdmin && state.isAuthenticated;

            setDisabled(elements.enableButton, !canEnable);
            setDisabled(elements.mintButton, !canMint);
            setDisabled(elements.refreshButton, !canRefresh);
            setDisabled(elements.checkoutButton, !canCheckout);
            setDisabled(elements.copyCloneButton, !canCopyClone);
            setDisabled(elements.copyRemoteButton, !canCopyRemote);
            setDisabled(elements.disableButton, !canAdminToggle);

            renderAdminButton();
            renderAlert();
        }

        function refreshCurrentRef() {
            return http.getJson(url_for_run("bootstrap/current-ref"))
                .then(function (payload) {
                    if (isErrorPayload(payload)) {
                        var message = resolveErrorMessage(payload, "Failed to load current ref.");
                        setAlert("error", message);
                        return null;
                    }
                    var content = getContent(payload);
                    updateCurrentRef(content.ref || "");
                    return content;
                })
                .catch(function (error) {
                    setAlert("error", resolveHttpErrorMessage(error, "Failed to load current ref."));
                    return null;
                });
        }

        function refreshCommits() {
            return http.getJson(url_for_run("bootstrap/commits"))
                .then(function (payload) {
                    if (isErrorPayload(payload)) {
                        var message = resolveErrorMessage(payload, "Failed to load commits.");
                        setAlert("error", message);
                        return null;
                    }
                    var content = getContent(payload);
                    state.commits = Array.isArray(content.commits) ? content.commits : [];
                    renderCommitOptions();
                    return content;
                })
                .catch(function (error) {
                    setAlert("error", resolveHttpErrorMessage(error, "Failed to load commits."));
                    return null;
                });
        }

        function refreshData() {
            if (!state.enabled) {
                return;
            }
            refreshCurrentRef();
            refreshCommits();
        }

        function enableBootstrap() {
            setAlert("info", "Enabling Bootstrap...");
            return http.postJson(url_for_run("bootstrap/enable"), {}, { form: formElement })
                .then(function (result) {
                    var payload = result && result.body ? result.body : null;
                    if (isErrorPayload(payload)) {
                        var message = resolveErrorMessage(payload, "Enable failed.");
                        setAlert("error", message);
                        return;
                    }
                    state.enabled = true;
                    setAlert("success", "Bootstrap enabled.");
                    renderState();
                    refreshData();
                })
                .catch(function (error) {
                    setAlert("error", resolveHttpErrorMessage(error, "Enable failed."));
                });
        }

        function mintToken() {
            setAlert("info", "Minting token...");
            return http.postJson(url_for_run("bootstrap/mint-token"), {}, { form: formElement })
                .then(function (result) {
                    var payload = result && result.body ? result.body : null;
                    if (isErrorPayload(payload)) {
                        var message = resolveErrorMessage(payload, "Token mint failed.");
                        setAlert("error", message);
                        return;
                    }
                    var content = getContent(payload);
                    updateCloneUrl(content.clone_url || "");
                    setAlert("success", "Token minted.");
                })
                .catch(function (error) {
                    setAlert("error", resolveHttpErrorMessage(error, "Token mint failed."));
                });
        }

        function checkoutCommit() {
            if (!elements.commitSelect) {
                return;
            }
            var sha = elements.commitSelect.value;
            if (!sha) {
                setAlert("warning", "Select a commit to checkout.");
                return;
            }
            setAlert("info", "Checking out commit...");
            return http.postJson(url_for_run("bootstrap/checkout"), { sha: sha }, { form: formElement })
                .then(function (result) {
                    var payload = result && result.body ? result.body : null;
                    if (isErrorPayload(payload)) {
                        var message = resolveErrorMessage(payload, "Checkout failed.");
                        setAlert("error", message);
                        return;
                    }
                    setAlert("success", "Checked out commit " + sha.slice(0, 7) + ".");
                    updateCurrentRef(sha.slice(0, 7));
                })
                .catch(function (error) {
                    setAlert("error", resolveHttpErrorMessage(error, "Checkout failed."));
                });
        }

        function toggleAdminDisable() {
            var desired = !state.adminDisabled;
            var label = desired ? "Disabling Bootstrap..." : "Re-enabling Bootstrap...";
            setAlert("info", label);
            return http.postJson(url_for_run("bootstrap/disable"), { disabled: desired }, { form: formElement })
                .then(function (result) {
                    var payload = result && result.body ? result.body : null;
                    if (isErrorPayload(payload)) {
                        var message = resolveErrorMessage(payload, "Update failed.");
                        setAlert("error", message);
                        return;
                    }
                    var content = getContent(payload);
                    state.adminDisabled = Boolean(content.bootstrap_disabled);
                    renderState();
                    if (state.adminDisabled) {
                        setAlert("warning", "Bootstrap disabled by admin.");
                    } else {
                        setAlert("success", "Bootstrap re-enabled.");
                    }
                })
                .catch(function (error) {
                    setAlert("error", resolveHttpErrorMessage(error, "Update failed."));
                });
        }

        function copyField(text, field, successMessage) {
            if (!text) {
                return;
            }
            if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
                navigator.clipboard.writeText(text)
                    .then(function () {
                        setAlert("success", successMessage);
                    })
                    .catch(function () {
                        fallbackCopy(text, field, successMessage);
                    });
            } else {
                fallbackCopy(text, field, successMessage);
            }
        }

        function fallbackCopy(text, field, successMessage) {
            if (!field) {
                return;
            }
            field.focus();
            field.select();
            try {
                var ok = document.execCommand("copy");
                if (ok) {
                    setAlert("success", successMessage);
                } else {
                    setAlert("warning", "Copy failed. Select the command and copy manually.");
                }
            } catch (err) {
                setAlert("warning", "Copy failed. Select the command and copy manually.");
            }
        }

        function bindEvents() {
            if (state.bound) {
                return;
            }
            if (!elements.root) {
                return;
            }

            state.bound = true;

            dom.delegate(elements.root, "click", SELECTORS.actionEnable, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                enableBootstrap();
            });

            dom.delegate(elements.root, "click", SELECTORS.actionMint, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                mintToken();
            });

            dom.delegate(elements.root, "click", SELECTORS.actionRefresh, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                refreshData();
            });

            dom.delegate(elements.root, "click", SELECTORS.actionCheckout, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                checkoutCommit();
            });

            dom.delegate(elements.root, "click", SELECTORS.actionCopyClone, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                copyField(state.cloneCommand, elements.cloneCommandInput, "Clone command copied.");
            });

            dom.delegate(elements.root, "click", SELECTORS.actionCopyRemote, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                copyField(state.remoteCommand, elements.remoteCommandInput, "Remote command copied.");
            });

            dom.delegate(elements.root, "click", SELECTORS.actionDisable, function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                toggleAdminDisable();
            });

            if (elements.commitSelect) {
                elements.commitSelect.addEventListener("change", function () {
                    state.selectedSha = elements.commitSelect.value || null;
                    renderCommitMeta(findCommit(state.selectedSha));
                    renderState();
                });
            }
        }

        function hydrateStateFromContext(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "bootstrap")
                : {};
            var dataContext = ctx.data && ctx.data.bootstrap ? ctx.data.bootstrap : {};

            function readFlag(key, fallback) {
                if (controllerContext && Object.prototype.hasOwnProperty.call(controllerContext, key)) {
                    return Boolean(controllerContext[key]);
                }
                if (dataContext && Object.prototype.hasOwnProperty.call(dataContext, key)) {
                    return Boolean(dataContext[key]);
                }
                return Boolean(fallback);
            }

            state.enabled = readFlag("enabled", state.enabled);
            state.adminDisabled = readFlag("adminDisabled", state.adminDisabled);
            state.isAnonymous = readFlag("isAnonymous", state.isAnonymous);

            if (ctx.user) {
                state.isAuthenticated = Boolean(ctx.user.isAuthenticated);
                state.isAdmin = Boolean(ctx.user.isAdmin || ctx.user.isRoot);
            }
        }

        control.bootstrap = function bootstrap(context) {
            syncElements();
            if (!elements.root) {
                return;
            }
            hydrateStateFromContext(context || {});
            bindEvents();
            renderState();
            if (state.enabled) {
                refreshData();
            }
        };

        return control;
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

/* ----------------------------------------------------------------------------
 * Team
 * ----------------------------------------------------------------------------
 */
var Team = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#team_form");
        that.info = $("#team_form #info, #team_form #team-info");
        that.status = $("#team_form  #status");
        that.stacktrace = $("#team_form #stacktrace");
        that.statusPanelEl = document.getElementById("team_status_panel");
        that.stacktracePanelEl = document.getElementById("team_stacktrace_panel");
        that.statusStream = null;
        that.ws_client = null;

        that.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (that.statusStream && typeof that.statusStream.append === "function") {
                that.statusStream.append(message, meta || null);
            }
            if (that.status && that.status.length) {
                that.status.html(message);
            }
        };

        if (typeof StatusStream !== "undefined" && that.statusPanelEl) {
            var stacktraceConfig = null;
            if (that.stacktracePanelEl) {
                stacktraceConfig = { element: that.stacktracePanelEl };
            }
            that.statusStream = StatusStream.attach({
                element: that.statusPanelEl,
                channel: "team",
                runId: window.runid || window.runId || null,
                logLimit: 200,
                stacktrace: stacktraceConfig,
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        that.triggerEvent(detail.event, detail);
                    }
                }
            });
        that.hideStacktrace = function () {
            var self = instance;
            if (self.stacktrace && self.stacktrace.length) {
                self.stacktrace.hide();
            }
        };
        } else {
            that.ws_client = new WSClient('team_form', 'team');
            that.ws_client.attachControl(that);
        }
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.adduser_click = function () {
            var self = instance;
            var email = $('#adduser-email').val()
            self.adduser(email)
        };

        that.adduser = function (email) {
            var self = instance;
            var data = { "adduser-email": email };

            $.post({
                url: "tasks/adduser/",
                data: data,
                success: function success(response) {
                    if (response.Success === true) {
                        self.appendStatus("Collaborator invited.");
                        that.triggerEvent("TEAM_ADDUSER_TASK_COMPLETED", { email: email });
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.removeuser = function (user_id) {
            var self = instance;
            $.post({
                url: "tasks/removeuser/",
                data: JSON.stringify({ user_id: user_id }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.appendStatus("Collaborator removed.");
                        that.triggerEvent("TEAM_REMOVEUSER_TASK_COMPLETED", { user_id: user_id });
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.report = function () {
            var self = instance;

            $.get({
                url: url_for_run("report/users/"),
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
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

/* ----------------------------------------------------------------------------
 * Control Base
 * ----------------------------------------------------------------------------
 */
function controlBase() {
    const TERMINAL_JOB_STATUSES = new Set(["finished", "failed", "stopped", "canceled", "not_found"]);
    const DEFAULT_POLL_INTERVAL_MS = 800;

    function escapeHtml(value) {
        if (value === null || value === undefined) {
            return "";
        }

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function normalizeJobId(jobId) {
        if (jobId === undefined || jobId === null) {
            return null;
        }
        const normalized = String(jobId).trim();
        return normalized.length === 0 ? null : normalized;
    }

    function formatStatusLabel(status) {
        if (!status) {
            return "unknown";
        }
        return status.charAt(0).toUpperCase() + status.slice(1);
    }

    function jobDashboardUrl(jobId) {
        return `https://${window.location.host}/weppcloud/rq/job-dashboard/${encodeURIComponent(jobId)}`;
    }

    function resolveButtons(self) {
        if (!self || !self.command_btn_id) {
            return [];
        }

        const ids = Array.isArray(self.command_btn_id) ? self.command_btn_id : [self.command_btn_id];
        const resolved = [];

        ids.forEach(function (id) {
            if (!id) {
                return;
            }
            const element = document.getElementById(id);
            if (element) {
                resolved.push($(element));
            }
        });

        return resolved;
    }

    return {
        command_btn_id: null,
        rq_job_id: null,
        rq_job_status: null,
        job_status_poll_interval_ms: DEFAULT_POLL_INTERVAL_MS,
        _job_status_poll_timeout: null,
        _job_status_fetch_inflight: false,
        _job_status_error: null,

        pushResponseStacktrace: function pushResponseStacktrace(self, response) {
            self.stacktrace.show();
            self.stacktrace.text("");

            if (response.Error !== undefined) {
                self.stacktrace.append("<h6>" + response.Error + "</h6>");
            }

            if (response.StackTrace !== undefined) {
                self.stacktrace.append("<pre><small class=\"text-muted\">" + response.StackTrace.join('\n') + "</small></pre>");

                if (response.StackTrace.includes('lock() called on an already locked nodb')) {
                    self.stacktrace.append('<a href="https://doc.wepp.cloud/AdvancedTopics.html#Clearing-Locks">Clearing Locks</a>');
                }
            }

            if (response.Error === undefined && response.StackTrace === undefined) {
                self.stacktrace.append("<pre><small class=\"text-muted\">" + response + "</small></pre>");
            }
        },

        pushErrorStacktrace: function pushErrorStacktrace(self, jqXHR, textStatus, errorThrown) {
            self.stacktrace.show();
            self.stacktrace.text("");
            self.stacktrace.append("<h6>" + jqXHR.status + "</h6>");
            self.stacktrace.append("<pre><small class=\"text-muted\">" + textStatus + "</small></pre>");
            self.stacktrace.append("<pre><small class=\"text-muted\">" + errorThrown + "</small></pre>");
        },

        should_disable_command_button: function should_disable_command_button(self) {
            if (!self.rq_job_id) {
                return false;
            }

            if (!self.rq_job_status || !self.rq_job_status.status) {
                return true;
            }

            return !TERMINAL_JOB_STATUSES.has(self.rq_job_status.status);
        },

        update_command_button_state: function update_command_button_state(self) {
            const buttons = resolveButtons(self);
            if (buttons.length === 0) {
                return;
            }

            const disable = self.should_disable_command_button(self);

            buttons.forEach(function ($btn) {
                if (!$btn || $btn.length === 0) {
                    return;
                }

                const wasDisabledByJob = $btn.data('jobDisabled') === true;

                if (disable) {
                    if (!wasDisabledByJob) {
                        $btn.data('jobDisabledPrev', $btn.prop('disabled'));
                    }
                    $btn.prop('disabled', true);
                    $btn.data('jobDisabled', true);
                } else if (wasDisabledByJob) {
                    const previousState = $btn.data('jobDisabledPrev');
                    $btn.prop('disabled', previousState === true);
                    $btn.data('jobDisabled', false);
                }
            });
        },

        set_rq_job_id: function (self, job_id) {
            const normalizedJobId = normalizeJobId(job_id);

            if (normalizedJobId === self.rq_job_id) {
                if (!normalizedJobId) {
                    self.render_job_status(self);
                    self.update_command_button_state(self);
                    self.manage_ws_client(self, null);
                } else if (!self._job_status_fetch_inflight) {
                    self.fetch_job_status(self);
                }
                return;
            }

            self.rq_job_id = normalizedJobId;
            self.rq_job_status = null;
            self._job_status_error = null;

            self.stop_job_status_polling(self);
            self.render_job_status(self);
            self.update_command_button_state(self);

            if (!self.rq_job_id) {
                self.manage_ws_client(self, null);
                return;
            }

            self.fetch_job_status(self);
        },

        fetch_job_status: function fetch_job_status(self) {
            if (!self.rq_job_id || self._job_status_fetch_inflight) {
                return;
            }

            self._job_status_fetch_inflight = true;

            $.ajax({
                url: `/weppcloud/rq/api/jobstatus/${encodeURIComponent(self.rq_job_id)}`,
                method: 'GET',
                dataType: 'json',
                cache: false
            }).done(function (data) {
                self.handle_job_status_response(self, data);
            }).fail(function (jqXHR) {
                self.handle_job_status_error(self, jqXHR);
            }).always(function () {
                self._job_status_fetch_inflight = false;
            });
        },

        handle_job_status_response: function handle_job_status_response(self, data) {
            self._job_status_error = null;
            self.rq_job_status = data || null;

            self.render_job_status(self);
            self.update_command_button_state(self);
            self.manage_ws_client(self, data && data.status ? data.status : null);

            if (self.should_continue_polling(self, data && data.status)) {
                self.schedule_job_status_poll(self);
            } else {
                self.stop_job_status_polling(self);
            }
        },

        handle_job_status_error: function handle_job_status_error(self, jqXHR) {
            const statusCode = jqXHR && jqXHR.status ? jqXHR.status : 'ERR';
            const statusText = jqXHR && jqXHR.statusText ? jqXHR.statusText : 'Unable to refresh job status';
            self._job_status_error = `${statusCode} ${statusText}`.trim();

            self.render_job_status(self);

            if (self.should_continue_polling(self)) {
                self.schedule_job_status_poll(self);
            } else {
                self.stop_job_status_polling(self);
            }
        },

        render_job_status: function render_job_status(self) {
            if (!self.rq_job || self.rq_job.length === 0) {
                return;
            }

            if (!self.rq_job_id) {
                self.rq_job.empty();
                return;
            }

            const statusObj = self.rq_job_status || {};
            const statusLabel = formatStatusLabel(statusObj.status || (self._job_status_error ? 'unknown' : 'checking'));
            const parts = [];

            parts.push(`<div>job_id: <a href="${jobDashboardUrl(self.rq_job_id)}" target="_blank">${escapeHtml(self.rq_job_id)}</a></div>`);
            parts.push(`<div class="small text-muted">Status: ${escapeHtml(statusLabel)}</div>`);

            const _times = [];

            if (statusObj.started_at) {
                _times.push(
                    `<span class="mr-3">Started: ${escapeHtml(statusObj.started_at)}</span>`
                );
            }

            if (statusObj.ended_at) {
                _times.push(
                    `<span class="mr-3">Ended: ${escapeHtml(statusObj.ended_at)}</span>`
                );
            }

            if (_times.length) {
                parts.push(
                    `<div class="small text-muted d-flex flex-wrap align-items-baseline">${_times.join("")}</div>`
                );
            }

            if (self._job_status_error) {
                parts.push(`<div class="text-danger small">${escapeHtml(self._job_status_error)}</div>`);
            }

            self.rq_job.html(parts.join(''));
        },

        schedule_job_status_poll: function schedule_job_status_poll(self) {
            if (!self.rq_job_id) {
                self.stop_job_status_polling(self);
                return;
            }

            const interval = self.job_status_poll_interval_ms || DEFAULT_POLL_INTERVAL_MS;

            self.stop_job_status_polling(self);

            self._job_status_poll_timeout = setTimeout(function () {
                self._job_status_poll_timeout = null;
                self.fetch_job_status(self);
            }, interval);
        },

        stop_job_status_polling: function stop_job_status_polling(self) {
            if (self._job_status_poll_timeout) {
                clearTimeout(self._job_status_poll_timeout);
                self._job_status_poll_timeout = null;
            }
        },

        should_continue_polling: function should_continue_polling(self, status) {
            if (!self.rq_job_id) {
                return false;
            }

            const effectiveStatus = status || (self.rq_job_status && self.rq_job_status.status);
            if (!effectiveStatus) {
                return true;
            }

            return !TERMINAL_JOB_STATUSES.has(effectiveStatus);
        },

        manage_ws_client: function manage_ws_client(self, status) {
            if (!self.ws_client) {
                return;
            }

            if (self.should_continue_polling(self, status)) {
                if (typeof self.ws_client.connect === 'function') {
                    self.ws_client.connect();
                }
            }
        }

    };
}
/* ----------------------------------------------------------------------------
 * Batch Runner (Phase 2)
 * ----------------------------------------------------------------------------
 */
var BatchRunner = (function () {
    var instance;

    function createInstance() {
        var that = controlBase();

        that.container = null;
        that.resourceCard = null;
        that.templateCard = null;
        that.state = {};
        that.sitePrefix = '';
        that.baseUrl = '';
        that.templateInitialised = false;
        that.command_btn_id = 'btn_run_batch';
        that.ws_client = null;
        that._jobInfoAbortController = null;
        that._jobInfoTrackedIds = new Set();
        that._jobInfoLastPayload = null;
        that._runDirectivesSaving = false;
        that._runDirectivesStatus = { message: '', css: 'text-muted' };

        that.init = function init(bootstrap) {
            bootstrap = bootstrap || {};
            this.state = {
                enabled: Boolean(bootstrap.enabled),
                batchName: bootstrap.batchName || '',
                snapshot: bootstrap.state || {},
                geojsonLimitMb: bootstrap.geojsonLimitMb,
            };
            this._bootstrapTrackedJobIds(bootstrap);
            this.state.validation = this._extractValidation(this.state.snapshot);
            this.sitePrefix = bootstrap.sitePrefix || '';
            this.baseUrl = this._buildBaseUrl();

            this.form = $('#batch_runner_form');
            this.statusDisplay = $('#batch_runner_form #status');
            this.stacktrace = $('#batch_runner_form #stacktrace');
            this.infoPanel = $('#batch_runner_form #info');
            this.rq_job = $('#batch_runner_form #rq_job');

            if (!this.ws_client) {
                this.ws_client = new WSClient('batch_runner_form', 'batch');
                this.ws_client.attachControl(this);
            }

            if (this.ws_client && this.state.batchName) {
                this.ws_client.wsUrl = `wss://${window.location.host}/weppcloud-microservices/status/${encodeURIComponent(this.state.batchName)}:batch`;
            }

            this.container = $("#batch-runner-root");
            this.resourceCard = $("#batch-runner-resource-card");
            this.templateCard = $("#batch-runner-template-card");

            if (!this.container.length) {
                console.warn("BatchRunner container not found");
                return this;
            }

            this._cacheElements();
            this._bindEvents();
            this._renderCoreStatus();
            this.render();
            this.refreshJobInfo();
            this.render_job_status(this);
            return this;
        };

        that.initManage = that.init;
        that.initCreate = that.init;

        that._cacheElements = function () {
            this.uploadForm = this.resourceCard.find('[data-role="upload-form"]');
            this.uploadInput = this.resourceCard.find('[data-role="geojson-input"]');
            this.uploadButton = this.resourceCard.find('[data-role="upload-button"]');
            this.uploadStatus = this.resourceCard.find('[data-role="upload-status"]');
            this.resourceEmpty = this.resourceCard.find('[data-role="resource-empty"]');
            this.resourceDetails = this.resourceCard.find('[data-role="resource-details"]');
            this.resourceMeta = this.resourceCard.find('[data-role="resource-meta"]');
            this.resourceSchema = this.resourceCard.find('[data-role="resource-schema"]');
            this.resourceSchemaBody = this.resourceCard.find('[data-role="resource-schema-body"]');
            this.resourceSamples = this.resourceCard.find('[data-role="resource-samples"]');
            this.resourceSamplesBody = this.resourceCard.find('[data-role="resource-samples-body"]');
            this.runBatchButton = $('#btn_run_batch');
            this.runBatchHint = $('#hint_run_batch');
            this.runBatchLock = $('#run_batch_lock');
            this.runDirectiveList = this.container.find('[data-role="run-directive-list"]');
            this.runDirectiveStatus = this.container.find('[data-role="run-directive-status"]');

            this.templateInput = this.templateCard.find('[data-role="template-input"]');
            this.validateButton = this.templateCard.find('[data-role="validate-button"]');
            this.templateStatus = this.templateCard.find('[data-role="template-status"]');
            this.validationSummary = this.templateCard.find('[data-role="validation-summary"]');
            this.validationSummaryList = this.templateCard.find('[data-role="validation-summary-list"]');
            this.validationIssues = this.templateCard.find('[data-role="validation-issues"]');
            this.validationIssuesList = this.templateCard.find('[data-role="validation-issues-list"]');
            this.validationPreview = this.templateCard.find('[data-role="validation-preview"]');
            this.previewBody = this.templateCard.find('[data-role="preview-body"]');
        };

        that._bindEvents = function () {
            var self = this;
            if (this.uploadForm.length) {
                if (this.uploadForm.is('form')) {
                    this.uploadForm.on('submit', function (evt) {
                        evt.preventDefault();
                        self._handleUpload();
                    });
                } else if (this.uploadButton.length && !this.uploadButton.attr('onclick')) {
                    this.uploadButton.on('click', function (evt) {
                        evt.preventDefault();
                        self._handleUpload();
                    });
                }
            }
            if (this.validateButton.length && !this.validateButton.attr('onclick')) {
                this.validateButton.on('click', function (evt) {
                    evt.preventDefault();
                    self._handleValidate();
                });
            }
            if (this.runDirectiveList && this.runDirectiveList.length) {
                this.runDirectiveList.on('change', 'input[data-slug]', function (evt) {
                    self._handleRunDirectiveToggle(evt);
                });
            }
        };

        that._extractValidation = function (snapshot) {
            snapshot = snapshot || {};
            var metadata = snapshot.metadata || {};
            return metadata.template_validation || null;
        };

        that._buildBaseUrl = function () {
            var prefix = this.sitePrefix || '';
            if (prefix && prefix.slice(-1) === '/') {
                prefix = prefix.slice(0, -1);
            }
            if (this.state.batchName) {
                return prefix + '/batch/_/' + encodeURIComponent(this.state.batchName);
            }
            var pathname = window.location.pathname || '';
            return pathname.replace(/\/$/, '');
        };

        that._apiUrl = function (suffix) {
            var base = this.baseUrl || '';
            if (!suffix) {
                return base;
            }
            if (suffix.charAt(0) !== '/') {
                suffix = '/' + suffix;
            }
            return base + suffix;
        };

        that._renderCoreStatus = function () {
            var snapshot = this.state.snapshot || {};
            this.container.find('[data-role="enabled-flag"]').text(this.state.enabled ? 'True' : 'False');
            this.container.find('[data-role="batch-name"]').text(this.state.batchName || '—');
            this.container.find('[data-role="manifest-version"]').text(snapshot.state_version || '—');
            this.container.find('[data-role="created-by"]').text(snapshot.created_by || '—');
            this.container.find('[data-role="manifest-json"]').text(JSON.stringify(snapshot, null, 2));
        };

        that.render = function render() {
            this._renderResource();
            this._renderValidation();
            this._renderRunDirectives();
            this._renderRunControls();
        };

        that._setRunBatchMessage = function (message, cssClass) {
            if (!this.runBatchHint || !this.runBatchHint.length) {
                return;
            }
            this.runBatchHint.removeClass('text-danger text-success text-warning text-muted text-info');
            if (cssClass) {
                this.runBatchHint.addClass(cssClass);
            }
            this.runBatchHint.text(message || '');
        };

        that._renderRunControls = function (options) {
            options = options || {};
            var preserveMessage = options.preserveMessage === true;

            if (!this.runBatchButton || !this.runBatchButton.length) {
                return;
            }

            var jobLocked = this.should_disable_command_button(this);
            this.update_command_button_state(this);

            if (this.runBatchLock && this.runBatchLock.length) {
                if (jobLocked) {
                    this.runBatchLock.show();
                } else {
                    this.runBatchLock.hide();
                }
            }

            if (jobLocked) {
                this.runBatchButton.prop('disabled', true);
                this._setRunBatchMessage('Batch run in progress…', 'text-muted');
                return;
            }

            var enabled = Boolean(this.state.enabled);
            var snapshot = this.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;
            var templateState = this.state.validation || (snapshot.metadata && snapshot.metadata.template_validation) || null;
            var templateStatus = templateState && (templateState.status || 'ok');
            var summary = templateState && templateState.summary;
            var templateIsValid = Boolean(templateState && summary && summary.is_valid && templateStatus === 'ok');

            var allowRun = enabled && Boolean(resource) && templateIsValid;
            var message = '';
            var cssClass = 'text-muted';

            if (!enabled) {
                message = 'Batch runner is disabled.';
                cssClass = 'text-warning';
            } else if (!resource) {
                message = 'Upload a watershed GeoJSON before running.';
            } else if (!templateIsValid) {
                message = 'Validate and resolve template issues before running.';
                cssClass = 'text-warning';
            } else {
                message = 'Ready to run batch.';
            }

            this.runBatchButton.prop('disabled', !allowRun);

            if (!preserveMessage || !allowRun) {
                this._setRunBatchMessage(message, cssClass);
            }
        };

        that._syncRunDirectiveDisabledState = function () {
            if (!this.runDirectiveList || !this.runDirectiveList.length) {
                return;
            }
            var shouldDisable = this._runDirectivesSaving || !this.state.enabled;
            this.runDirectiveList.find('input[data-slug]').prop('disabled', shouldDisable);
        };

        that._setRunDirectivesStatus = function (message, cssClass) {
            this._runDirectivesStatus = {
                message: message || '',
                css: cssClass || '',
            };
            if (!this.runDirectiveStatus || !this.runDirectiveStatus.length) {
                return;
            }
            this.runDirectiveStatus.removeClass('text-danger text-success text-muted text-warning');
            if (cssClass) {
                this.runDirectiveStatus.addClass(cssClass);
            }
            this.runDirectiveStatus.text(message || '');
        };

        that._applyStoredRunDirectiveStatus = function () {
            if (!this.runDirectiveStatus || !this.runDirectiveStatus.length) {
                return;
            }
            var status = this._runDirectivesStatus || {};
            this.runDirectiveStatus.removeClass('text-danger text-success text-muted text-warning');
            if (status.css) {
                this.runDirectiveStatus.addClass(status.css);
            }
            this.runDirectiveStatus.text(status.message || '');
        };

        that._renderRunDirectives = function () {
            if (!this.runDirectiveList || !this.runDirectiveList.length) {
                return;
            }

            var snapshot = this.state.snapshot || {};
            var directives = snapshot.run_directives || [];
            var self = this;

            if (!Array.isArray(directives) || directives.length === 0) {
                this.runDirectiveList.html('<div class="text-muted small">No batch tasks configured.</div>');
                this._setRunDirectivesStatus('No batch tasks configured.', 'text-muted');
                return;
            }

            var html = directives.map(function (directive, index) {
                if (!directive || typeof directive !== 'object') {
                    return '';
                }
                var slug = directive.slug || ('directive-' + index);
                var label = directive.label || slug;
                var controlId = 'batch-runner-directive-' + slug;
                var checked = directive.enabled ? ' checked' : '';
                var disabled = (!self.state.enabled || self._runDirectivesSaving) ? ' disabled' : '';
                return '<div class="custom-control custom-checkbox mb-1">' +
                    '<input type="checkbox" class="custom-control-input" id="' + controlId + '" data-slug="' + slug + '"' + checked + disabled + '>' +
                    '<label class="custom-control-label" for="' + controlId + '">' + self._escapeHtml(label) + '</label>' +
                    '</div>';
            }).join('');

            this.runDirectiveList.html(html);
            this._syncRunDirectiveDisabledState();
            if (!this._runDirectivesStatus || !this._runDirectivesStatus.message) {
                if (!this.state.enabled) {
                    this._setRunDirectivesStatus('Batch runner is disabled; tasks cannot be edited.', 'text-muted');
                } else {
                    this._applyStoredRunDirectiveStatus();
                }
            } else {
                this._applyStoredRunDirectiveStatus();
            }
        };

        that._setRunDirectivesBusy = function (busy) {
            this._runDirectivesSaving = busy === true;
            this._syncRunDirectiveDisabledState();
        };

        that._collectRunDirectiveValues = function () {
            var result = {};
            if (!this.runDirectiveList || !this.runDirectiveList.length) {
                return result;
            }
            this.runDirectiveList.find('input[data-slug]').each(function () {
                var $input = $(this);
                var slug = $input.data('slug');
                if (!slug) {
                    return;
                }
                result[String(slug)] = $input.is(':checked');
            });
            return result;
        };

        that._submitRunDirectives = function (values) {
            if (!values) {
                return;
            }
            var self = this;
            this._setRunDirectivesBusy(true);
            this._setRunDirectivesStatus('Saving batch task selection…', 'text-muted');

            fetch(this._apiUrl('run-directives'), {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ run_directives: values })
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        data._httpStatus = response.status;
                        return data;
                    });
                })
                .then(function (payload) {
                    if (!payload || payload.success !== true) {
                        throw (payload && (payload.error || payload.message)) || 'Failed to update batch tasks.';
                    }

                    if (payload.snapshot) {
                        self.state.snapshot = payload.snapshot;
                    } else if (Array.isArray(payload.run_directives)) {
                        var snapshot = self.state.snapshot || {};
                        snapshot.run_directives = payload.run_directives;
                        self.state.snapshot = snapshot;
                    }

                    self._setRunDirectivesStatus('Batch tasks updated.', 'text-success');
                    self._renderRunDirectives();
                })
                .catch(function (error) {
                    var message = typeof error === 'string' ? error : (error && error.error) || 'Failed to update batch tasks.';
                    self._setRunDirectivesStatus(message, 'text-danger');
                    self._renderRunDirectives();
                })
                .finally(function () {
                    self._setRunDirectivesBusy(false);
                });
        };

        that._handleRunDirectiveToggle = function (evt) {
            if (this._runDirectivesSaving) {
                if (evt && typeof evt.preventDefault === 'function') {
                    evt.preventDefault();
                }
                return;
            }

            if (!this.state.enabled) {
                if (evt && typeof evt.preventDefault === 'function') {
                    evt.preventDefault();
                }
                this._renderRunDirectives();
                return;
            }

            var values = this._collectRunDirectiveValues();
            this._submitRunDirectives(values);
        };

        that._collectJobNodes = function (jobInfo, acc) {
            if (!jobInfo) {
                return;
            }
            acc.push(jobInfo);
            var children = jobInfo.children || {};
            Object.keys(children).forEach(function (orderKey) {
                var bucket = children[orderKey] || [];
                bucket.forEach(function (child) {
                    if (child) {
                        that._collectJobNodes(child, acc);
                    }
                });
            });
        };

        that._registerTrackedJobId = function (jobId) {
            if (jobId === undefined || jobId === null) {
                return false;
            }
            var normalized = String(jobId).trim();
            if (!normalized) {
                return false;
            }
            if (!this._jobInfoTrackedIds.has(normalized)) {
                this._jobInfoTrackedIds.add(normalized);
                return true;
            }
            return false;
        };

        that._registerTrackedJobIds = function (collection) {
            var self = this;
            if (!collection) {
                return;
            }
            if (Array.isArray(collection)) {
                collection.forEach(function (value) {
                    self._registerTrackedJobId(value);
                });
                return;
            }
            if (typeof collection === 'object') {
                Object.keys(collection).forEach(function (key) {
                    self._registerTrackedJobId(collection[key]);
                });
                return;
            }
            self._registerTrackedJobId(collection);
        };

        that._bootstrapTrackedJobIds = function (bootstrap) {
            if (!bootstrap || typeof bootstrap !== 'object') {
                return;
            }

            if (Array.isArray(bootstrap.jobIds)) {
                this._registerTrackedJobIds(bootstrap.jobIds);
            }

            if (bootstrap.rqJobIds && typeof bootstrap.rqJobIds === 'object') {
                this._registerTrackedJobIds(bootstrap.rqJobIds);
            }

            var snapshot = bootstrap.state || {};
            var metadata = snapshot && typeof snapshot === 'object' ? (snapshot.metadata || {}) : {};

            this._registerTrackedJobIds(snapshot.job_ids);
            this._registerTrackedJobIds(metadata.job_ids);
            this._registerTrackedJobIds(metadata.rq_job_ids);
            this._registerTrackedJobIds(metadata.tracked_job_ids);
        };

        that._resolveJobInfoRequestIds = function () {
            var ids = new Set();

            if (this.rq_job_id) {
                ids.add(String(this.rq_job_id).trim());
            }

            if (this._jobInfoTrackedIds && this._jobInfoTrackedIds.size) {
                this._jobInfoTrackedIds.forEach(function (value) {
                    if (value) {
                        ids.add(String(value).trim());
                    }
                });
            }

            var snapshot = (this.state && this.state.snapshot) || {};
            var metadata = snapshot && typeof snapshot === 'object' ? (snapshot.metadata || {}) : {};

            [snapshot.job_ids, metadata.job_ids, metadata.rq_job_ids, metadata.tracked_job_ids].forEach(function (collection) {
                if (!collection) {
                    return;
                }
                var items;
                if (Array.isArray(collection)) {
                    items = collection;
                } else if (typeof collection === 'object') {
                    items = Object.values(collection);
                } else {
                    items = [collection];
                }
                items.forEach(function (item) {
                    if (item === undefined || item === null) {
                        return;
                    }
                    var normalized = String(item).trim();
                    if (normalized) {
                        ids.add(normalized);
                    }
                });
            });

            return Array.from(ids).filter(function (value) {
                return typeof value === 'string' && value.length > 0;
            });
        };

        that._normalizeJobInfoPayload = function (payload) {
            if (!payload) {
                return [];
            }

            if (Array.isArray(payload)) {
                return payload.filter(function (item) {
                    return item && typeof item === 'object';
                });
            }

            if (payload.jobs && typeof payload.jobs === 'object') {
                return Object.keys(payload.jobs).map(function (key) {
                    return payload.jobs[key];
                }).filter(function (item) {
                    return item && typeof item === 'object';
                });
            }

            if (payload.job && typeof payload.job === 'object') {
                return [payload.job];
            }

            if (payload && typeof payload === 'object' && (payload.id || payload.status || payload.children)) {
                return [payload];
            }

            return [];
        };

        that._registerJobInfoTrees = function (jobInfos) {
            var self = this;
            if (!Array.isArray(jobInfos) || jobInfos.length === 0) {
                return;
            }
            jobInfos.forEach(function (info) {
                if (!info || typeof info !== 'object') {
                    return;
                }
                var nodes = [];
                self._collectJobNodes(info, nodes);
                nodes.forEach(function (node) {
                    if (node && node.id) {
                        self._registerTrackedJobId(node.id);
                    }
                });
            });
        };

        that._dedupeJobNodes = function (nodes) {
            if (!Array.isArray(nodes)) {
                return [];
            }
            var deduped = [];
            var seen = new Set();

            nodes.forEach(function (node) {
                if (!node) {
                    return;
                }
                var key = node.id ? String(node.id) : (node.runid ? 'runid:' + node.runid : null);
                if (key && seen.has(key)) {
                    return;
                }
                if (key) {
                    seen.add(key);
                }
                deduped.push(node);
            });

            return deduped;
        };

        that._renderJobInfo = function (payload) {
            if (!this.infoPanel || !this.infoPanel.length) {
                return;
            }

            this._jobInfoLastPayload = payload;

            var jobInfos = this._normalizeJobInfoPayload(payload);
            if (!jobInfos.length) {
                this.infoPanel.html('<span class="text-muted">Job information unavailable.</span>');
                return;
            }

            this._registerJobInfoTrees(jobInfos);

            var that = this;
            var nodes = [];
            jobInfos.forEach(function (info) {
                that._collectJobNodes(info, nodes);
            });
            var dedupedNodes = this._dedupeJobNodes(nodes);

            var watershedNodes = dedupedNodes.filter(function (node) {
                return node && node.runid;
            });

            var totalWatersheds = watershedNodes.length;
            var completedWatersheds = watershedNodes.filter(function (node) {
                return node.status === 'finished';
            }).length;
            var failedWatersheds = watershedNodes.filter(function (node) {
                return node.status === 'failed' || node.status === 'stopped' || node.status === 'canceled';
            });
            var activeWatersheds = watershedNodes.filter(function (node) {
                return node.status && node.status !== 'finished' && node.status !== 'failed' && node.status !== 'stopped' && node.status !== 'canceled';
            });

            var parts = [];

            if (jobInfos.length === 1) {
                var rootInfo = jobInfos[0] || {};
                parts.push('<div><strong>Batch status:</strong> ' + this._escapeHtml(rootInfo.status || 'unknown') + '</div>');
                if (rootInfo.id) {
                    parts.push('<div class="small text-muted">Job ID: <code>' + this._escapeHtml(rootInfo.id) + '</code></div>');
                }
            } else {
                parts.push('<div><strong>Tracked jobs:</strong></div>');
                var maxJobsToShow = 6;
                var jobBadges = jobInfos.slice(0, maxJobsToShow).map(function (info) {
                    var safeStatus = that._escapeHtml((info && info.status) || 'unknown');
                    var safeId = that._escapeHtml((info && info.id) || '—');
                    return '<span class="badge badge-light text-dark border mr-1 mb-1">' + safeStatus + ' · <code>' + safeId + '</code></span>';
                });
                if (jobInfos.length > maxJobsToShow) {
                    jobBadges.push('<span class="text-muted">…</span>');
                }
                parts.push('<div class="mt-1">' + jobBadges.join(' ') + '</div>');
            }

            var allNotFound = jobInfos.every(function (info) {
                return info && info.status === 'not_found';
            });

            if (allNotFound) {
                parts.push('<div class="small text-muted">Requested job IDs were not found in the queue.</div>');
                this.infoPanel.html(parts.join(''));
                return;
            }

            if (totalWatersheds > 0) {
                parts.push('<div class="small text-muted">Watersheds: ' + completedWatersheds + '/' + totalWatersheds + ' finished</div>');
            } else {
                parts.push('<div class="small text-muted">Watershed tasks have not started yet.</div>');
            }

            if (activeWatersheds.length) {
                var activeList = activeWatersheds.slice(0, 6).map(function (node) {
                    return '<span class="badge badge-info text-dark mr-1 mb-1">' + that._escapeHtml(node.runid) + ' · ' + that._escapeHtml(node.status || 'pending') + '</span>';
                });
                if (activeWatersheds.length > activeList.length) {
                    activeList.push('<span class="text-muted">…</span>');
                }
                parts.push('<div class="mt-2"><strong>Active</strong><div>' + activeList.join(' ') + '</div></div>');
            }

            if (failedWatersheds.length) {
                var failedList = failedWatersheds.slice(0, 6).map(function (node) {
                    return '<span class="badge badge-danger text-light mr-1 mb-1">' + that._escapeHtml(node.runid) + '</span>';
                });
                if (failedWatersheds.length > failedList.length) {
                    failedList.push('<span class="text-muted">…</span>');
                }
                parts.push('<div class="mt-2"><strong class="text-danger">Failures</strong><div>' + failedList.join(' ') + '</div></div>');
            }

            this.infoPanel.html(parts.join(''));
        };

        that.refreshJobInfo = function () {
            if (!this.infoPanel || !this.infoPanel.length) {
                return;
            }

            var jobIds = this._resolveJobInfoRequestIds();
            if (!jobIds.length) {
                this.infoPanel.html('<span class="text-muted">No batch job submitted yet.</span>');
                return;
            }

            var self = this;
            jobIds.forEach(function (jobId) {
                self._registerTrackedJobId(jobId);
            });

            if (typeof AbortController !== 'undefined') {
                if (this._jobInfoAbortController) {
                    this._jobInfoAbortController.abort();
                }
                this._jobInfoAbortController = new AbortController();
            }

            var controller = this._jobInfoAbortController;
            fetch('/weppcloud/rq/api/jobinfo', {
                method: 'POST',
                signal: controller ? controller.signal : undefined,
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ job_ids: jobIds })
            })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('Failed to fetch job info');
                    }
                    return response.json();
                })
                .then(function (payload) {
                    if (payload && Array.isArray(payload.job_ids)) {
                        self._registerTrackedJobIds(payload.job_ids);
                    } else if (payload && payload.jobs && typeof payload.jobs === 'object') {
                        self._registerTrackedJobIds(Object.keys(payload.jobs));
                    }

                    self._renderJobInfo(payload);
                    if (controller && controller === self._jobInfoAbortController) {
                        self._jobInfoAbortController = null;
                    }
                })
                .catch(function (error) {
                    if (error && error.name === 'AbortError') {
                        return;
                    }
                    console.warn('Unable to refresh batch job info:', error);
                    if (self.infoPanel && self.infoPanel.length) {
                        self.infoPanel.html('<span class="text-muted">Unable to refresh batch job details.</span>');
                    }
                    if (controller && controller === self._jobInfoAbortController) {
                        self._jobInfoAbortController = null;
                    }
                });
        };

        that._renderResource = function () {
            var snapshot = this.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;
            var self = this;
            console.debug('[BatchRunner] _renderResource snapshot', snapshot);
            console.debug('[BatchRunner] _renderResource resource present?', Boolean(resource), resource);

            if (!this.resourceCard.length) {
                return;
            }

            if (!resource) {
                console.debug('[BatchRunner] No watershed resource on render; showing empty state.');
                this._setHidden(this.resourceEmpty, false);
                this._setHidden(this.resourceDetails, true);
                this._setHidden(this.resourceSchema, true);
                this._setHidden(this.resourceSamples, true);
                return;
            }

            console.debug('[BatchRunner] Watershed resource detected; updating details card.');
            this._setHidden(this.resourceEmpty, true);
            this._setHidden(this.resourceDetails, false);

            var metaHtml = [];
            metaHtml.push(this._renderMetaRow('Filename', resource.filename || resource.original_filename || '—'));
            if (resource.original_filename && resource.original_filename !== resource.filename) {
                metaHtml.push(this._renderMetaRow('Original Filename', resource.original_filename));
            }
            metaHtml.push(this._renderMetaRow('Size', this._formatBytes(resource.size_bytes)));
            metaHtml.push(this._renderMetaRow('Checksum', resource.checksum || '—'));
            metaHtml.push(this._renderMetaRow('Feature Count', resource.feature_count != null ? resource.feature_count : '—'));
            if (Array.isArray(resource.properties)) {
                metaHtml.push(this._renderMetaRow('Property Count', resource.properties.length));
            }
            if (resource.bbox) {
                metaHtml.push(this._renderMetaRow('Bounding Box', this._formatBBox(resource.bbox)));
            }
            if (resource.epsg) {
                var epsgLabel = resource.epsg;
                if (resource.epsg_source && resource.epsg_source !== 'declared') {
                    epsgLabel += ' (inferred)';
                }
                metaHtml.push(this._renderMetaRow('CRS', epsgLabel));
            }
            if (resource.uploaded_at) {
                metaHtml.push(this._renderMetaRow('Uploaded', this._formatTimestamp(resource.uploaded_at)));
            }
            if (resource.uploaded_by) {
                metaHtml.push(this._renderMetaRow('Uploaded By', resource.uploaded_by));
            }
            if (resource.replaced) {
                metaHtml.push(this._renderMetaRow('Replaced Existing', resource.replaced ? 'Yes' : 'No'));
            }

            this.resourceMeta.html(metaHtml.join(''));

            var schema = resource.attribute_schema || {};
            var schemaKeys = Object.keys(schema || {});
            if (schemaKeys.length) {
                schemaKeys.sort();
                var schemaRows = schemaKeys.map(function (name) {
                    return '<tr><td>' + self._escapeHtml(name) + '</td><td>' + self._escapeHtml(schema[name]) + '</td></tr>';
                });
                this.resourceSchemaBody.html(schemaRows.join(''));
                this._setHidden(this.resourceSchema, false);
            } else {
                this.resourceSchemaBody.empty();
                this._setHidden(this.resourceSchema, true);
            }

            var samples = Array.isArray(resource.sample_properties) ? resource.sample_properties : [];
            if (samples.length) {
                var sampleRows = samples.map(function (sample) {
                    var props = sample.properties || {};
                    var propsJson;
                    try {
                        propsJson = JSON.stringify(props, null, 2);
                    } catch (err) {
                        propsJson = String(props);
                    }
                    return '<tr><td>' + self._escapeHtml(sample.index != null ? sample.index : '—') + '</td>' +
                        '<td><pre class="mb-0 small">' + self._escapeHtml(propsJson) + '</pre></td></tr>';
                });
                this.resourceSamplesBody.html(sampleRows.join(''));
                this._setHidden(this.resourceSamples, false);
            } else {
                this.resourceSamplesBody.empty();
                this._setHidden(this.resourceSamples, true);
            }
        };

        that._renderValidation = function () {
            if (!this.templateCard.length) {
                return;
            }

            var snapshot = this.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;
            var manifest = snapshot || {};
            var storedValidation = this._extractValidation(manifest);

            if (!this.templateInitialised) {
                var tpl = snapshot.runid_template || '';
                if (tpl && !this.templateInput.is(':focus')) {
                    this.templateInput.val(tpl);
                }
                this.templateInitialised = true;
            }

            if (!resource) {
                this.templateStatus.text('Upload a GeoJSON resource to enable template validation.');
                this._setHidden(this.validationSummary, true);
                this._setHidden(this.validationIssues, true);
                this._setHidden(this.validationPreview, true);
                return;
            }

            var validation = this.state.validation || storedValidation;
            this.state.validation = validation;

            if (!validation) {
                if (storedValidation && storedValidation.status === 'stale') {
                    this.templateStatus.text('Previous validation is stale. Re-run validation after reviewing the new GeoJSON.');
                } else {
                    this.templateStatus.text('No validation recorded. Provide a template and validate.');
                }
                this._setHidden(this.validationSummary, true);
                this._setHidden(this.validationIssues, true);
                this._setHidden(this.validationPreview, true);
                return;
            }

            var summary = validation.summary || {};
            var summaryItems = [];
            summaryItems.push('<li>Total features: ' + (summary.total_features != null ? summary.total_features : '—') + '</li>');
            summaryItems.push('<li>Valid run IDs: ' + (summary.valid_run_ids != null ? summary.valid_run_ids : '—') + '</li>');
            summaryItems.push('<li>Unique run IDs: ' + (summary.unique_run_ids != null ? summary.unique_run_ids : '—') + '</li>');
            summaryItems.push('<li>Duplicate run IDs: ' + (summary.duplicate_run_ids != null ? summary.duplicate_run_ids : '—') + '</li>');
            summaryItems.push('<li>Errors: ' + (summary.errors != null ? summary.errors : '—') + '</li>');

            var statusText = summary.is_valid ? 'Template is valid.' : 'Template has issues. Review details below.';
            if (validation.status === 'stale') {
                statusText = 'Validation is stale. Re-run validation with the latest resource.';
            }
            this.templateStatus.text(statusText);

            this.validationSummaryList.html(summaryItems.join(''));
            this._setHidden(this.validationSummary, false);

            var issues = [];
            (validation.errors || []).forEach(function (err) {
                issues.push('Feature #' + err.index + (err.feature_id ? ' [' + err.feature_id + ']' : '') + ': ' + err.error);
            });
            (validation.duplicates || []).forEach(function (dup) {
                issues.push('Duplicate run ID ' + dup.run_id + ' found at indexes ' + dup.indexes.join(', '));
            });

            if (issues.length) {
                this.validationIssuesList.html(issues.map(function (text) {
                    return $('<div/>').text(text).html();
                }).join('<br>'));
                this._setHidden(this.validationIssues, false);
            } else {
                this.validationIssuesList.empty();
                this._setHidden(this.validationIssues, true);
            }

            var previewRows = validation.preview || [];
            if (!previewRows.length && validation.rows) {
                previewRows = validation.rows.slice(0, 20);
            }

            if (previewRows.length) {
                var previewHtml = previewRows.map(function (row) {
                    var errorCell = row.error ? $('<span/>').text(row.error).html() : '';
                    var runIdCell = row.run_id ? $('<span/>').text(row.run_id).html() : '';
                    var featureId = row.feature_id != null ? row.feature_id : '—';
                    return '<tr>' +
                        '<td>' + row.index + '</td>' +
                        '<td>' + $('<span/>').text(featureId).html() + '</td>' +
                        '<td>' + runIdCell + '</td>' +
                        '<td>' + errorCell + '</td>' +
                        '</tr>';
                }).join('');
                this.previewBody.html(previewHtml);
                this._setHidden(this.validationPreview, false);
            } else {
                this.previewBody.empty();
                this._setHidden(this.validationPreview, true);
            }
        };

        that._handleUpload = function () {
            if (!this.state.enabled) {
                return;
            }
            var fileInput = this.uploadInput.get(0);
            if (!fileInput || !fileInput.files || !fileInput.files.length) {
                this._setUploadStatus('Please choose a GeoJSON file to upload.', 'text-danger');
                return;
            }

            var formData = new FormData();
            formData.append('geojson_file', fileInput.files[0]);

            var self = this;
            this._setUploadBusy(true, 'Uploading GeoJSON…');

            fetch(this._apiUrl('upload-geojson'), {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        data._httpStatus = response.status;
                        return data;
                    });
                })
                .then(function (payload) {
                    if (!payload.success) {
                        throw payload.error || 'Upload failed.';
                    }

                    if (payload.snapshot) {
                        console.debug('[BatchRunner] Upload response snapshot', payload.snapshot);
                        self.state.snapshot = payload.snapshot || {};
                        self.state.validation = self._extractValidation(self.state.snapshot);
                    } else {
                        console.debug('[BatchRunner] Upload response metadata', payload);
                        var snapshot = self.state.snapshot || {};
                        snapshot.resources = snapshot.resources || {};
                        var resource = payload.resource;
                        if (!resource && payload.resource_metadata) {
                            resource = Object.assign({}, payload.resource_metadata);
                            var analysis = payload.template_validation || {};
                            if (analysis && typeof analysis === 'object') {
                                if (analysis.feature_count != null) {
                                    resource.feature_count = analysis.feature_count;
                                }
                                if (analysis.bbox) {
                                    resource.bbox = analysis.bbox;
                                }
                                if (analysis.epsg) {
                                    resource.epsg = analysis.epsg;
                                }
                                if (analysis.epsg_source) {
                                    resource.epsg_source = analysis.epsg_source;
                                }
                                if (analysis.checksum) {
                                    resource.checksum = analysis.checksum;
                                }
                                if (analysis.size_bytes != null) {
                                    resource.size_bytes = analysis.size_bytes;
                                }
                                if (analysis.attribute_schema) {
                                    resource.attribute_schema = analysis.attribute_schema;
                                }
                                if (Array.isArray(analysis.properties)) {
                                    resource.properties = analysis.properties;
                                }
                                if (Array.isArray(analysis.sample_properties)) {
                                    resource.sample_properties = analysis.sample_properties;
                                }
                            }
                        }
                        if (resource) {
                            console.debug('[BatchRunner] Merging resource into snapshot', resource);
                            snapshot.resources.watershed_geojson = resource;
                        } else {
                            console.debug('[BatchRunner] No resource derived from payload.');
                        }
                        snapshot.metadata = snapshot.metadata || {};
                        if (payload.template_validation && payload.template_validation.summary) {
                            snapshot.metadata.template_validation = payload.template_validation;
                            self.state.validation = payload.template_validation;
                        } else if (snapshot.metadata.template_validation) {
                            snapshot.metadata.template_validation.status = 'stale';
                            self.state.validation = snapshot.metadata.template_validation;
                        } else {
                            self.state.validation = null;
                        }
                        self.state.snapshot = snapshot;
                    }

                    console.debug('[BatchRunner] Post-upload snapshot state', self.state.snapshot);
                    self._setUploadStatus(payload.message || 'Upload complete.', 'text-success');
                    fileInput.value = '';
                    self.templateInitialised = false;
                    self._applyResourceVisibility();
                    self.render();
                })
                .catch(function (error) {
                    var message = typeof error === 'string' ? error : (error && error.error) || 'Upload failed.';
                    self._setUploadStatus(message, 'text-danger');
                })
                .finally(function () {
                    self._setUploadBusy(false);
                });
        };

        that._handleValidate = function () {
            if (!this.state.enabled) {
                return;
            }
            var template = (this.templateInput.val() || '').trim();
            if (!template) {
                this.templateStatus.text('Enter a template before validating.');
                return;
            }

            var self = this;
            this._setValidateBusy(true, 'Validating template…');

            fetch(this._apiUrl('validate-template'), {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ template: template }),
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        data._httpStatus = response.status;
                        return data;
                    });
                })
                .then(function (payload) {
                    if (!payload.validation) {
                        throw payload.error || 'Template validation failed.';
                    }

                    self.state.validation = payload.validation;
                    if (payload.snapshot) {
                        self.state.snapshot = payload.snapshot || {};
                    } else {
                        var snapshot = self.state.snapshot || {};
                        snapshot.metadata = snapshot.metadata || {};
                        snapshot.metadata.template_validation = payload.stored;
                        snapshot.runid_template = template;
                        self.state.snapshot = snapshot;
                    }
                    self.templateInitialised = false;
                    self.render();
                })
                .catch(function (error) {
                    var message = typeof error === 'string' ? error : (error && error.error) || 'Template validation failed.';
                    self.templateStatus.text(message);
                })
                .finally(function () {
                    self._setValidateBusy(false);
                });
        };

        that._setUploadBusy = function (busy, message) {
            if (this.uploadButton.length) {
                this.uploadButton.prop('disabled', busy || !this.state.enabled);
            }
            if (message != null) {
                this._setUploadStatus(message, busy ? 'text-muted' : '');
            }
        };

        that._setValidateBusy = function (busy, message) {
            if (this.validateButton.length) {
                this.validateButton.prop('disabled', busy || !this.state.enabled);
            }
            if (message != null) {
                this.templateStatus.text(message);
            }
        };

        that._setRunBatchBusy = function (busy, message, cssClass) {
            if (this.runBatchButton && this.runBatchButton.length && busy) {
                this.runBatchButton.prop('disabled', true);
            }

            if (this.runBatchLock && this.runBatchLock.length) {
                if (busy) {
                    this.runBatchLock.show();
                } else if (!this.should_disable_command_button(this)) {
                    this.runBatchLock.hide();
                }
            }

            if (message != null) {
                this._setRunBatchMessage(message, cssClass || 'text-muted');
            }

            if (!busy) {
                this._renderRunControls({ preserveMessage: true });
            }
        };

        var baseSetRqJobId = that.set_rq_job_id;
        that.set_rq_job_id = function (self, job_id) {
            baseSetRqJobId.call(this, self, job_id);
            if (self === that) {
                if (job_id) {
                    that._registerTrackedJobId(job_id);
                }
                if (job_id) {
                    that.refreshJobInfo();
                } else if (that.infoPanel && that.infoPanel.length) {
                    that.infoPanel.html('<span class="text-muted">No batch job submitted yet.</span>');
                }
            }
        };

        var baseHandleJobStatusResponse = that.handle_job_status_response;
        that.handle_job_status_response = function (self, data) {
            baseHandleJobStatusResponse.call(this, self, data);
            if (self === that) {
                that.refreshJobInfo();
            }
        };

        that.uploadGeojson = function (evt) {
            if (!this.state.enabled) {
                this._setUploadStatus('Batch runner is disabled.', 'text-warning');
                return false;
            }

            if (evt) {
                evt.preventDefault();
                if (typeof evt.stopImmediatePropagation === 'function') {
                    evt.stopImmediatePropagation();
                }
            }

            this._handleUpload();
            return false;
        };

        that.validateTemplate = function (evt) {
            if (!this.state.enabled) {
                this.templateStatus.text('Batch runner is disabled.');
                return false;
            }

            if (evt) {
                evt.preventDefault();
                if (typeof evt.stopImmediatePropagation === 'function') {
                    evt.stopImmediatePropagation();
                }
            }

            this._handleValidate();
            return false;
        };

        that._setUploadStatus = function (message, cssClass) {
            if (!this.uploadStatus.length) {
                return;
            }
            this.uploadStatus.removeClass('text-danger text-success text-muted text-warning');
            if (cssClass) {
                this.uploadStatus.addClass(cssClass);
            }
            this.uploadStatus.text(message || '');
        };

        that._applyResourceVisibility = function () {
            if (!this.resourceCard || !this.resourceCard.length) {
                return;
            }
            var snapshot = this.state.snapshot || {};
            var resources = snapshot.resources || {};
            var resource = resources.watershed_geojson;
            console.debug('[BatchRunner] _applyResourceVisibility resource present?', Boolean(resource), resource);
            if (resource) {
                this.resourceEmpty.hide();
                this.resourceDetails.show();
            }
        };

        that._escapeHtml = function (value) {
            return $('<span/>').text(value != null ? value : '').html();
        };

        that._renderMetaRow = function (label, value) {
            return '<dt class="col-sm-4">' + this._escapeHtml(label) + '</dt>' +
                '<dd class="col-sm-8">' + this._escapeHtml(value != null ? value : '—') + '</dd>';
        };

        that._setHidden = function (element, hidden) {
            if (!element || !element.length) {
                return;
            }
            var domNode = element[0];
            if (hidden) {
                element.attr('hidden', 'hidden');
                element.prop('hidden', true);
                element.addClass('d-none');
                if (typeof element.hide === 'function') {
                    element.hide();
                }
                if (domNode && domNode.style) {
                    domNode.style.setProperty('display', 'none', 'important');
                }
            } else {
                element.removeAttr('hidden');
                element.prop('hidden', false);
                element.removeClass('d-none');
                if (domNode && domNode.style) {
                    domNode.style.removeProperty('display');
                }
                if (typeof element.show === 'function') {
                    element.show();
                }
            }
        };

        that._formatBytes = function (bytes) {
            if (bytes == null || isNaN(bytes)) {
                return '—';
            }
            var size = Number(bytes);
            if (size < 1024) {
                return size + ' B';
            }
            if (size < 1024 * 1024) {
                return (size / 1024).toFixed(1) + ' KB';
            }
            return (size / (1024 * 1024)).toFixed(1) + ' MB';
        };

        that._formatBBox = function (bbox) {
            if (!bbox || bbox.length !== 4) {
                return '—';
            }
            return bbox.map(function (val) {
                return Number(val).toFixed(4);
            }).join(', ');
        };

        that._formatTimestamp = function (timestamp) {
            try {
                var date = new Date(timestamp);
                if (!isNaN(date.getTime())) {
                    return date.toLocaleString();
                }
            } catch (err) {
                // ignore
            }
            return timestamp || '—';
        };

        that.runBatch = function () {
            if (!this.state.enabled) {
                this._setRunBatchMessage('Batch runner is disabled.', 'text-warning');
                return;
            }

            if (this.should_disable_command_button(this)) {
                return;
            }

            var self = this;
            if (self._jobInfoAbortController && typeof self._jobInfoAbortController.abort === 'function') {
                try {
                    self._jobInfoAbortController.abort();
                } catch (abortError) {
                    console.warn('Failed to abort in-flight job info request before submitting batch:', abortError);
                }
                self._jobInfoAbortController = null;
            }
            if (self._jobInfoTrackedIds && typeof self._jobInfoTrackedIds.clear === 'function') {
                self._jobInfoTrackedIds.clear();
            }
            self._jobInfoLastPayload = null;

            self._setRunBatchBusy(true, 'Submitting batch run…', 'text-muted');

            if (self.ws_client && typeof self.ws_client.connect === 'function') {
                self.ws_client.connect();
            }

            if (self.infoPanel && self.infoPanel.length) {
                self.infoPanel.html('<span class="text-muted">Submitting batch job…</span>');
            }

            fetch(this._apiUrl('rq/api/run-batch'), {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        data._httpStatus = response.status;
                        return data;
                    });
                })
                .then(function (payload) {
                    if (!payload.success) {
                        throw payload.error || 'Failed to submit batch run.';
                    }

                    if (payload.job_id) {
                        self.set_rq_job_id(self, payload.job_id);
                    } else {
                        self.update_command_button_state(self);
                    }

                    var successMessage = payload.message || 'Batch run submitted.';
                    self._setRunBatchMessage(successMessage, 'text-success');
                })
                .catch(function (error) {
                    var message;
                    if (typeof error === 'string') {
                        message = error;
                    } else if (error && typeof error === 'object') {
                        message = error.error || error.message;
                    }
                    self._setRunBatchMessage(message || 'Failed to submit batch run.', 'text-danger');
                    if (self.infoPanel && self.infoPanel.length) {
                        self.infoPanel.html('<span class="text-danger">' + self._escapeHtml(message || 'Failed to submit batch run.') + '</span>');
                    }
                    if (self.ws_client && typeof self.ws_client.disconnect === 'function') {
                        self.ws_client.disconnect();
                    }
                })
                .finally(function () {
                    self._setRunBatchBusy(false);
                });
        };

        var baseTriggerEvent = that.triggerEvent;
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'BATCH_RUN_COMPLETED' || eventName === 'END_BROADCAST') {
                if (this.ws_client && typeof this.ws_client.disconnect === 'function') {
                    this.ws_client.disconnect();
                }
                if (this.ws_client && typeof this.ws_client.resetSpinner === 'function') {
                    this.ws_client.resetSpinner();
                }
                this.refreshJobInfo();
            } else if (eventName === 'BATCH_WATERSHED_TASK_COMPLETED') {
                this.refreshJobInfo();
            }

            baseTriggerEvent.call(this, eventName, payload);
        };

        return that;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

window.BatchRunner = BatchRunner;

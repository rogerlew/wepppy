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

        that.init = function init(bootstrap) {
            bootstrap = bootstrap || {};
            this.state = {
                enabled: Boolean(bootstrap.enabled),
                batchName: bootstrap.batchName || '',
                manifest: bootstrap.manifest || {},
                geojsonLimitMb: bootstrap.geojsonLimitMb,
            };
            this.state.validation = this._extractValidation(this.state.manifest);
            this.sitePrefix = bootstrap.sitePrefix || '';
            this.baseUrl = this._buildBaseUrl();

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
                this.uploadForm.on('submit', function (evt) {
                    evt.preventDefault();
                    self._handleUpload();
                });
            }
            if (this.validateButton.length) {
                this.validateButton.on('click', function (evt) {
                    evt.preventDefault();
                    self._handleValidate();
                });
            }
        };

        that._extractValidation = function (manifest) {
            manifest = manifest || {};
            var metadata = manifest.metadata || {};
            return metadata.template_validation || null;
        };

        that._buildBaseUrl = function () {
            var prefix = this.sitePrefix || '';
            if (prefix && prefix.slice(-1) === '/') {
                prefix = prefix.slice(0, -1);
            }
            if (this.state.batchName) {
                return prefix + '/batch/' + encodeURIComponent(this.state.batchName);
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
            var manifest = this.state.manifest || {};
            this.container.find('[data-role="enabled-flag"]').text(this.state.enabled ? 'True' : 'False');
            this.container.find('[data-role="batch-name"]').text(this.state.batchName || '—');
            this.container.find('[data-role="manifest-version"]').text(manifest.version || '—');
            this.container.find('[data-role="created-by"]').text(manifest.created_by || '—');
            this.container.find('[data-role="manifest-json"]').text(JSON.stringify(manifest, null, 2));
        };

        that.render = function render() {
            this._renderResource();
            this._renderValidation();
        };

        that._renderResource = function () {
            var manifest = this.state.manifest || {};
            var resources = manifest.resources || {};
            var resource = resources.watershed_geojson;

            if (!this.resourceCard.length) {
                return;
            }

            if (!resource) {
                this._setHidden(this.resourceEmpty, false);
                this._setHidden(this.resourceDetails, true);
                return;
            }

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
        };

        that._renderValidation = function () {
            if (!this.templateCard.length) {
                return;
            }

            var manifest = this.state.manifest || {};
            var resources = manifest.resources || {};
            var resource = resources.watershed_geojson;

            if (!this.templateInitialised) {
                var tpl = manifest.runid_template || '';
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

            var validation = this.state.validation || this._extractValidation(manifest);
            this.state.validation = validation;

            if (!validation) {
                if (manifest.metadata && manifest.metadata.template_validation && manifest.metadata.template_validation.status === 'stale') {
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

                    var manifest = self.state.manifest;
                    manifest.resources = manifest.resources || {};
                    manifest.resources.watershed_geojson = payload.resource;
                    manifest.metadata = manifest.metadata || {};
                    if (payload.template_validation) {
                        manifest.metadata.template_validation = payload.template_validation;
                        self.state.validation = payload.template_validation;
                    } else if (manifest.metadata.template_validation) {
                        manifest.metadata.template_validation.status = 'stale';
                        self.state.validation = manifest.metadata.template_validation;
                    }

                    self._setUploadStatus(payload.message || 'Upload complete.', 'text-success');
                    fileInput.value = '';
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
                    var manifest = self.state.manifest;
                    manifest.metadata = manifest.metadata || {};
                    manifest.metadata.template_validation = payload.stored;
                    manifest.runid_template = template;
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

        that._setUploadStatus = function (message, cssClass) {
            if (!this.uploadStatus.length) {
                return;
            }
            this.uploadStatus.removeClass('text-danger text-success text-muted');
            if (cssClass) {
                this.uploadStatus.addClass(cssClass);
            }
            this.uploadStatus.text(message || '');
        };

        that._renderMetaRow = function (label, value) {
            return '<dt class="col-sm-4">' + $('<span/>').text(label).html() + '</dt>' +
                '<dd class="col-sm-8">' + $('<span/>').text(value != null ? value : '—').html() + '</dd>';
        };

        that._setHidden = function (element, hidden) {
            if (!element || !element.length) {
                return;
            }
            if (hidden) {
                element.attr('hidden', 'hidden');
            } else {
                element.removeAttr('hidden');
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

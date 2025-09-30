/* ----------------------------------------------------------------------------
 * Batch Runner (Phase 0)
 * ----------------------------------------------------------------------------
 */
var BatchRunner = (function () {
    var instance;

    function createInstance() {
        var that = controlBase();

        that.container = null;
        that.state = {};

        that.init = function init(bootstrap) {
            bootstrap = bootstrap || {};
            this.state = bootstrap;
            this.container = $("#batch-runner-root");

            if (!this.container.length) {
                console.warn("BatchRunner container not found");
                return this;
            }

            var enabled = Boolean(bootstrap.enabled);
            var manifest = bootstrap.manifest || {};

            this.container.find('[data-role="enabled-flag"]').text(enabled ? 'True' : 'False');
            this.container.find('[data-role="batch-name"]').text(bootstrap.batchName || '—');
            this.container.find('[data-role="manifest-version"]').text(manifest.version || '—');
            this.container.find('[data-role="created-by"]').text(manifest.created_by || '—');
            this.container.find('[data-role="manifest-json"]').text(JSON.stringify(manifest, null, 2));

            return this;
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

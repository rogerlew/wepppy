/* ----------------------------------------------------------------------------
 * Disturbed
 * ----------------------------------------------------------------------------
 */
var Disturbed = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that._has_sbs_cached = undefined;

        that.reset_land_soil_lookup = function () {
            $.get({
                url: "tasks/reset_disturbed",
                cache: false,
                success: function success(response) {
                    if (response.Success == true) {
                        alert("Land Soil Lookup has been reset");
                    } else {
                        alert("Error resetting Land Soil Lookup");
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    alert("Error resetting Land Soil Lookup");
                }
            });
        };

        that.load_extended_land_soil_lookup = function () {
            $.get({
                url: "tasks/load_extended_land_soil_lookup",
                cache: false,
                success: function success(response) {
                    if (response.Success == true) {
                        alert("Land Soil Lookup has been extended");
                    } else {
                        alert("Error extending Land Soil Lookup");
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    alert("Error  extending Land Soil Lookup");
                }
            });
        };

        that.set_has_sbs_cached = function (value) {
            var previous = that._has_sbs_cached;
            if (value === undefined || value === null) {
                that._has_sbs_cached = undefined;
            } else {
                that._has_sbs_cached = value === true;
            }
            if (previous !== that._has_sbs_cached && typeof CustomEvent === 'function') {
                document.dispatchEvent(new CustomEvent('disturbed:has_sbs_changed', {
                    detail: { hasSbs: that._has_sbs_cached }
                }));
            }
            return that._has_sbs_cached;
        };

        that.get_has_sbs_cached = function () {
            return that._has_sbs_cached;
        };

        that.clear_has_sbs_cache = function () {
            that._has_sbs_cached = undefined;
        };

        that.has_sbs = function (options) {
            var opts = options || {};

            if (!opts.forceRefresh && that._has_sbs_cached !== undefined) {
                return that._has_sbs_cached;
            }

            var result = false;
            $.ajax({
                url: "api/disturbed/has_sbs/",
                async: false,  // Makes the request synchronous
                dataType: 'json',  // Ensures response is parsed as JSON
                success: function (response) {
                    result = response.has_sbs === true;
                },
                error: function (jqXHR) {
                    if (jqXHR && jqXHR.responseJSON) {
                        console.log(jqXHR.responseJSON);
                    }
                    result = false;  // Returns false if the request fails
                }
            });
            return that.set_has_sbs_cached(result);
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

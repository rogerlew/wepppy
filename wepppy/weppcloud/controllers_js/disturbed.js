/* ----------------------------------------------------------------------------
 * Disturbed
 * ----------------------------------------------------------------------------
 */
var Disturbed = function () {
    var instance;

    function createInstance() {
        var that = controlBase();

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

        that.has_sbs = function () {
            var result;
            $.ajax({
                url: "api/disturbed/has_sbs/",
                async: false,  // Makes the request synchronous
                dataType: 'json',  // Ensures response is parsed as JSON
                success: function (response) {
                    result = response.has_sbs;
                },
                error: function (jqXHR) {
                    console.log(jqXHR.responseJSON);
                    result = false;  // Returns false if the request fails
                }
            });
            return result;
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
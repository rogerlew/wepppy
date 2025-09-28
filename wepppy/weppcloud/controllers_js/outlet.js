/* ----------------------------------------------------------------------------
 * Outlet
 * ----------------------------------------------------------------------------
 */
var Outlet = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#set_outlet_form");
        that.info = $("#set_outlet_form #info");
        that.status = $("#set_outlet_form  #status");
        that.stacktrace = $("#set_outlet_form #stacktrace");
        that.ws_client = new WSClient('set_outlet_form', 'outlet');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#set_outlet_form #rq_job");
        that.command_btn_id = ['btn_set_outlet_cursor', 'btn_set_outlet_entry'];

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'SET_OUTLET_TASK_COMPLETED') {
                that.ws_client.disconnect();
                if (that.popup && typeof that.popup.remove === 'function') {
                    that.popup.remove();
                }
                that.show();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.outlet = null;
        that.outletMarker = L.marker(undefined, {
            pane: 'markerCustomPane'
        });

        that.remove = function () {
            var self = instance;
            var map = Map.getInstance();
            self.info.html("");
            self.stacktrace.text("");

            map.ctrls.removeLayer(self.outletMarker);
            map.removeLayer(self.outletMarker);
            self.status.html("");

        };

        that.show = function () {
            var self = instance;

            self.remove();

            var task_msg = "Displaying Outlet...";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "query/outlet/",
                cache: false,
                success: function success(response) {
                    var map = Map.getInstance();

                    var offset = cellsize * 5e-6;

                    self.outletMarker.setLatLng([response.lat - offset, response.lng + offset]).addTo(map);
                    map.ctrls.addOverlay(self.outletMarker, "Outlet");
                    self.status.html(task_msg + "... Success");
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: url_for_run("report/outlet/"),
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

        // Cursor Selection Control
        that.popup = L.popup();
        that.cursorSelectionOn = false;

        that.setClickHandler = function (ev) {
            var self = instance;
            if (self.cursorSelectionOn) {
                self.set_outlet(ev);
            }
        };

        that.set_outlet = function (ev) {
            var self = instance;
            var map = Map.getInstance();

            var task_msg = "Attempting to set outlet";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            self.popup.setLatLng(ev.latlng).setContent("finding nearest channel...").openOn(map);

            var lat = ev.latlng.lat;
            var lng = ev.latlng.lng;

            $.post({
                url: "rq/api/set_outlet",
                data: { latitude: lat, longitude: lng },
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`set_outlet job submitted: ${response.job_id}`);
                        self.set_rq_job_id(self, response.job_id);
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
            self.setCursorSelection(false);
        };

        that.setCursorSelection = function (state) {
            var self = instance;
            self.cursorSelectionOn = state;

            if (state) {
                $("#btn_set_outlet_cursor").text("Cancel");
                $(".leaflet-container").css("cursor", "crosshair");
                $("#hint_set_outlet_cursor").text("Click on the map to define outlet.");
            } else {
                $("#btn_set_outlet_cursor").text("Use Cursor");
                $(".leaflet-container").css("cursor", "");
                $("#hint_set_outlet_cursor").text("");
            }
        };

        that.setMode = function (mode) {
            var self = instance;
            self.mode = parseInt(mode, 10);
            if (self.mode === 0) {
                // Enter lng, lat
                $("#set_outlet_mode0_controls").show();
                $("#set_outlet_mode1_controls").hide();
            } else {
                // user cursor
                $("#set_outlet_mode0_controls").hide();
                $("#set_outlet_mode1_controls").show();
                self.setCursorSelection(false);
            }
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

function render_legend(cmap, canvasID) {
    var canvas = $("#" + canvasID);

    var width = canvas.outerWidth();
    var height = canvas.outerHeight();
    var data = new Float32Array(height * width);

    for (var y = 0; y <= height; y++) {
        for (var x = 0; x <= width; x++) {
            data[(y * width) + x] = x / (width - 1.0);
        }
    }

    var plot = new plotty.plot({
        canvas: canvas["0"],
        data: data, width: width, height: height,
        domain: [0, 1], colorScale: cmap
    });
    plot.render();
}

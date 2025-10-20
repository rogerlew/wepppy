/* ----------------------------------------------------------------------------
 * Outlet
 * ----------------------------------------------------------------------------
 */
var Outlet = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        const MODE_SECTIONS = {
            0: $("#set_outlet_mode0_controls"),
            1: $("#set_outlet_mode1_controls")
        };

        function parseMode(value, fallback) {
            var parsed = parseInt(value, 10);
            return Number.isNaN(parsed) ? fallback : parsed;
        }

        that.form = $("#set_outlet_form");
        that.info = $("#set_outlet_form #info");
        that.status = $("#set_outlet_form  #status");
        that.stacktrace = $("#set_outlet_form #stacktrace");
        that.ws_client = new WSClient('set_outlet_form', 'outlet');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#set_outlet_form #rq_job");
        that.command_btn_id = ['btn_set_outlet_cursor', 'btn_set_outlet_entry'];
        that.modeInputs = $("input[name='set_outlet_mode']");

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
            var map = MapController.getInstance();
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
                    var map = MapController.getInstance();

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
        that.cursorButton = $("#btn_set_outlet_cursor");
        that.cursorHint = $("#hint_set_outlet_cursor");
        that.entryInput = $("#input_set_outlet_entry");
        that.entryButton = $("#btn_set_outlet_entry");
        that.popup = L.popup();
        that.cursorSelectionOn = false;

        if (that.modeInputs && that.modeInputs.length) {
            that.modeInputs.off('change.setoutlet').on('change.setoutlet', function () {
                that.handleModeChange(this.value);
            });
        }

        if (that.cursorButton && that.cursorButton.length) {
            that.cursorButton.off('click.setoutlet').on('click.setoutlet', function () {
                that.handleCursorToggle();
            });
        }

        if (that.entryButton && that.entryButton.length) {
            that.entryButton.off('click.setoutlet').on('click.setoutlet', function () {
                that.handleEntrySubmit();
            });
        }

        that.setClickHandler = function (ev) {
            var self = instance;
            if (self.cursorSelectionOn) {
                self.set_outlet(ev);
            }
        };

        that.set_outlet = function (ev) {
            var self = instance;
            var map = MapController.getInstance();

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
                if (self.cursorButton && self.cursorButton.length) {
                    self.cursorButton.text("Cancel");
                }
                $(".leaflet-container").css("cursor", "crosshair");
                if (self.cursorHint && self.cursorHint.length) {
                    self.cursorHint.text("Click on the map to define outlet.");
                }
            } else {
                if (self.cursorButton && self.cursorButton.length) {
                    self.cursorButton.text("Use Cursor");
                }
                $(".leaflet-container").css("cursor", "");
                if (self.cursorHint && self.cursorHint.length) {
                    self.cursorHint.text("");
                }
            }
        };

        that.setMode = function (mode) {
            var self = instance;
            self.mode = parseMode(mode, 0);

            Object.keys(MODE_SECTIONS).forEach(function (key) {
                var section = MODE_SECTIONS[key];
                if (!section || section.length === 0) {
                    return;
                }
                if (Number(key) === self.mode) {
                    section.show();
                } else {
                    section.hide();
                }
            });

            if (self.mode !== 0) {
                self.setCursorSelection(false);
            }
        };

        that.handleModeChange = function (mode) {
            that.setMode(mode);
        };

        that.handleCursorToggle = function () {
            var self = instance;
            self.setCursorSelection(!self.cursorSelectionOn);
        };

        that.handleEntrySubmit = function () {
            var self = instance;
            var raw = self.entryInput && self.entryInput.length ? self.entryInput.val() : '';
            var parts = String(raw || '').split(',');

            if (parts.length < 2) {
                self.status.html('<span class="text-danger">Enter coordinates as "lon, lat".</span>');
                return false;
            }

            var lng = parseFloat(parts[0]);
            var lat = parseFloat(parts[1]);

            if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
                self.status.html('<span class="text-danger">Invalid coordinates.</span>');
                return false;
            }

            var ev = { latlng: L.latLng(lat, lng) };
            self.set_outlet(ev);
            return true;
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

    if (!canvas.length) {
        return;
    }

    var width = Math.round(canvas.outerWidth());
    var height = Math.round(canvas.outerHeight());

    if (width <= 0 || height <= 0) {
        return;
    }

    var element = canvas[0];
    if (element.width !== width) {
        element.width = width;
    }
    if (element.height !== height) {
        element.height = height;
    }

    var data = new Float32Array(width * height);
    var denom = width > 1 ? width - 1 : 1;

    for (var y = 0; y < height; y++) {
        var rowOffset = y * width;
        for (var x = 0; x < width; x++) {
            data[rowOffset + x] = x / denom;
        }
    }

    var plot = new plotty.plot({
        canvas: element,
        data: data,
        width: width,
        height: height,
        domain: [0, 1],
        colorScale: cmap
    });
    plot.render();
}

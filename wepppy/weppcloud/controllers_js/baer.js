/* ----------------------------------------------------------------------------
 * Baer
 * ----------------------------------------------------------------------------
 */
var Baer = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#sbs_upload_form");
        that.info = $("#sbs_upload_form #info");
        that.status = $("#sbs_upload_form  #status");
        that.stacktrace = $("#sbs_upload_form #stacktrace");
        that.ws_client = new WSClient('sbs_upload_form', 'sbs_upload');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#sbs_upload_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };
        that.baer_map = null;


        that.showHideControls = function (mode) {
            // show the appropriate controls
            if (mode === -1) {
                $("#sbs_mode0_controls").hide();
                $("#sbs_mode1_controls").hide();
            } else if (mode === 0) {
                $("#sbs_mode0_controls").show();
                $("#sbs_mode1_controls").hide();
            } else if (mode === 1) {
                $("#sbs_mode0_controls").hide();
                $("#sbs_mode1_controls").show();
            } else {
                throw "ValueError: Landuse unknown mode";
            }
        };

        that.set_firedate = function (fire_date) {
            var self = instance;

            var task_msg = "Setting Fire Date";

            $.post({
                url: "tasks/set_firedate/",
                data: JSON.stringify({ fire_date: fire_date }),
                contentType: "application/json; charset=utf-8",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
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
        };

        that.upload_sbs = function () {
            var self = instance;

            var task_msg = "Uploading SBS";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            var formData = new FormData($('#sbs_upload_form')[0]);

            $.post({
                url: "tasks/upload_sbs/",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("SBS_UPLOAD_TASK_COMPLETE");
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
        };

        that.remove_sbs = function () {
            var self = instance;
            var map = Map.getInstance();

            $.post({
                url: "tasks/remove_sbs/",
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("SBS_REMOVE_TASK_COMPLETE");
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

            if (self.baer_map !== null) {
                map.ctrls.removeLayer(self.baer_map);
                map.removeLayer(self.baer_map);
                self.baer_map = null;
            }

            self.info.html('');
        };

        that.build_uniform_sbs = function (value) {
            var self = instance;

            var task_msg = "Setting Uniform SBS";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/build_uniform_sbs/" + value.toString(),
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("SBS_UPLOAD_TASK_COMPLETE");
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
        };


        that.load_modify_class = function () {
            var self = instance;

            $.get({
                url: "view/modify_burn_class/",
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

        that.modify_classes = function () {

            var self = instance;
            var data = [parseInt($('#baer_brk0').val(), 10),
            parseInt($('#baer_brk1').val(), 10),
            parseInt($('#baer_brk2').val(), 10),
            parseInt($('#baer_brk3').val(), 10)];

            var nodata_vals = $('#baer_nodata').val();

            var task_msg = "Modifying Class Breaks";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/modify_burn_class/",
                data: JSON.stringify({ classes: data, nodata_vals: nodata_vals }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("MODIFY_BURN_CLASS_TASK_COMPLETE");
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
        };


        that.modify_color_map = function () {

            var self = instance;

            var data = {};
            // Use jQuery to find all select fields that start with "baer_color_"
            $("select[id^='baer_color_']").each(function () {
                var id = $(this).attr('id'); // Get the id of the select element
                var rgb = id.replace('baer_color_', ''); // Extract the <R>_<G>_<B> part
                var value = $(this).val(); // Get the selected value of the dropdown
                data[rgb] = value; // Add to the data object
            });

            var task_msg = "Modifying Class Breaks";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/modify_color_map/",
                data: JSON.stringify({ color_map: data }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("MODIFY_BURN_CLASS_TASK_COMPLETE");
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
        };


        that.show_sbs = function () {
            var self = instance;
            var map = Map.getInstance();
            var sub = SubcatchmentDelineation.getInstance();


            if (self.baer_map !== null) {
                map.ctrls.removeLayer(self.baer_map);
                map.removeLayer(self.baer_map);
                self.baer_map = null;
            }

            var task_msg = "Querying SBS map";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "query/baer_wgs_map/",
                cache: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");

                        var bounds = response.Content.bounds;
                        var imgurl = response.Content.imgurl + "?v=" + Date.now();

                        self.baer_map = L.imageOverlay(imgurl, bounds, { opacity: 0.7 });
                        self.baer_map.addTo(map);
                        map.ctrls.addOverlay(self.baer_map, "Burn Severity Map");

                        $.get({
                            url: "query/has_dem/",
                            cache: false,
                            success: function doFlyTo(response) {
                                if (response === false) {
                                    map.flyToBounds(self.baer_map._bounds);
                                }
                            },
                            error: function error(jqXHR) {
                                self.pushResponseStacktrace(self, jqXHR.responseJSON);
                            },
                            fail: function fail(jqXHR, textStatus, errorThrown) {
                                self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                            }
                        });
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
            }).always(function () {
                var self = instance;

                $.get({
                    url: "resources/legends/sbs/",
                    cache: false,
                    success: function (response) {
                        var map = Map.getInstance();
                        map.sbs_legend.html(response);

                        map.sbs_legend.append('<div id="slider-container"><p>SBS Map Opacity</p><input type="range" id="opacity-slider" min="0" max="1" step="0.1" value="0.7"></div>');
                        $('#opacity-slider').on('input change', function () {
                            var newOpacity = $(this).val();
                            self.baer_map.setOpacity(newOpacity);
                        });
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
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
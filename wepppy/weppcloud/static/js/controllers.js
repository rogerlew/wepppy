/* ----------------------------------------------------------------------------
 * Controllers (controllers.js)
 * ----------------------------------------------------------------------------
 */
"use strict";
// globals for JSLint: $, L, polylabel, setTimeout, console

function coordRound(v) {
    var w = Math.floor(v);
    var d = v - w;
    d = Math.round(d * 10000) / 10000;
    return w + d;
}

function pass() {
    return undefined;
}

/* ----------------------------------------------------------------------------
 * WebSocketManager
 * ----------------------------------------------------------------------------
 */

function WSClient(formId, channel) {
    // global runid
    this.formId = formId;
    this.channel = channel;
    this.wsUrl = "wss://" + window.location.host + "/weppcloud-microservices/status/" + runid + ":" + channel;
    this.ws = null;
    this.shouldReconnect = true;
    //    this.connect();
}

WSClient.prototype.connect = function () {
    if (this.ws) {
        return; // If already connected, do nothing
    }

    this.shouldReconnect = true;
    this.ws = new WebSocket(this.wsUrl);
    this.ws.onopen = () => {
        $("#preflight_status").html("Connected");
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ "type": "init" }));
        } else {
            console.error("WebSocket is not in OPEN state: ", this.ws.readyState);
        }
    };

    this.ws.onmessage = (event) => {
        var payload = JSON.parse(event.data);
        if (payload.type === "ping") {
            this.ws.send(JSON.stringify({ "type": "pong" }));
        } else if (payload.type === "hangup") {
            this.disconnect();
        } else if (payload.type === "status") {
            var data = payload.data;
            var lines = data.split('\n');
            if (lines.length > 1) {
                data = lines[0] + '...';
            }

            if (data.includes("EXCEPTION")) {
                var stacktrace = $("#" + this.formId + " #stacktrace");

                stacktrace.show();
                stacktrace.text("");
                stacktrace.append("<h6>Error</h6>");
                stacktrace.append(`<p>${data}</p>`);

                var job_id = data.split(' ')[0].slice(3);
                var job_url = `https://${window.location.host}/weppcloud/rq/jobinfo/${job_id}`;

                // need a short delay here to avoid race condition
                setTimeout(function () {
                    $.get(job_url, function (job_info, status) {
                        if (status === 'success') {
                            stacktrace.append(`<pre><small class="text-muted">${job_info.exc_info}</small></pre>`);
                        }
                    });
                }, 500);
            }

            if (data.includes("TRIGGER")) {
                // need to parse the trigger command and execute it
                // second to last argument is the controller
                // last argument is the event
                var trigger = data.split(' ');
                var controller = trigger[trigger.length - 2];
                var event = trigger[trigger.length - 1];

                if (controller == this.channel) {
                    $("#" + this.formId).trigger(event);
                }

            }
            else {
                $("#" + this.formId + " #status").html(data);
            }
        }
    };

    this.ws.onerror = (error) => {
        console.log("WebSocket Error: ", error);
        this.ws = null;
    };

    this.ws.onclose = () => {
        //        $("#" + this.formId + " #status").html("Connection Closed");
        this.ws = null;
        if (this.shouldReconnect) {
            setTimeout(() => { this.connect(); }, 5000);
        }
    };
};

WSClient.prototype.disconnect = function () {
    if (this.ws) {
        this.shouldReconnect = false;
        this.ws.close();
        this.ws = null;
    }
};


/* ----------------------------------------------------------------------------
 * Control Base
 * ----------------------------------------------------------------------------
 */
function controlBase() {
    return {
        pushResponseStacktrace: function pushResponseStacktrace(self, response) {
            self.stacktrace.show();
            self.stacktrace.text("");

            if (response.Error !== undefined) {
                self.stacktrace.append("<h6>" + response.Error + "</h6>");
            }

            if (response.StackTrace !== undefined) {
                self.stacktrace.append("<pre><small class=\"text-muted\">" + response.StackTrace.join('\n') + "</small></pre>");

                if (response.StackTrace.includes('lock() called on an already locked nodb')) {
                    self.stacktrace.append('<a href="https://doc.wepp.cloud/AdvancedTopics.html#Clearing-Locks">Clearing Locks</a>')
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
        set_rq_job_id: function (self, job_id) {
            if (job_id === null)
                return;

            self.rq_job_id = job_id;
            self.rq_job.html(`job_id: <a href="https://${window.location.host}/weppcloud/rq/job-dashboard/${job_id}" target="_blank">${job_id}</a><div style="height:30px;"></div>`);
        }

    };
}


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
                url: "tasks/reset_disturbed/",
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
                    alert("Error clearing locks");
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



/* ----------------------------------------------------------------------------
 * Project
 * ----------------------------------------------------------------------------
 */
var Project = function () {
    var instance;

    function createInstance() {
        var that = controlBase();

        that.setName = function (name) {
            var self = instance;
            $.post({
                url: "tasks/setname/",
                data: $("#setname_form").serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        $("#input_name").val(name);
                        document.title = document.title.split(" - ")[0] + ' - ' + name;
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.setScenario = function (scenario) {
            var self = instance;
            $.post({
                url: "tasks/setscenario/",
                data: $("#setscenario_form").serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        $("#input_scenario").val(scenario);
                        document.title = document.title.split(" - ")[0] + ' - ' + scenario;
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.clear_locks = function () {

            $.get({
                url: "tasks/clear_locks/",
                cache: false,
                success: function success(response) {
                    if (response.Success == true) {
                        alert("Locks have been cleared");
                    } else {
                        alert("Error clearing locks");
                    }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    alert("Error clearing locks");
                }
            });
        };


        that.set_public = function (state) {
            $.post({
                url: "tasks/set_public/",
                data: JSON.stringify({ public: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                }
            });
        };

        that.set_readonly = function (state) {
            var self = instance;

            $.post({
                url: "tasks/set_readonly/",
                data: JSON.stringify({ readonly: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    self.set_readonly_controls(state);
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                }
            });
        };

        that.set_readonly_controls = function (readonly) {

            if (readonly === true) {
                $('.hide-readonly').each(function (index, element) {
                    $(this).hide();
                });
                $('.disable-readonly').each(function (index, element) {
                    $(this).prop('readonly', true);
                });
            } else {
                $('.hide-readonly').each(function (index, element) {
                    $(this).show();
                });
                $('.disable-readonly').each(function (index, element) {
                    $(this).prop('readonly', false);
                });
                Outlet.getInstance().setMode(0);
            }
        };

        function replaceAll(str, find, replace) {
            return str.replace(new RegExp(find, 'g'), replace);
        }

        that.unitChangeEvent = function () {
            var self = instance;

            var prefs = $("[name^=unitizer_]");

            var unit_preferences = {};
            for (var i = 0; i < prefs.length; i++) {
                var name = prefs[i].name;

                var units = $("input[name='" + name + "']:checked").val();

                name = name.replace('unitizer_', '').replace('_radio', '');

                units = replaceAll(units, '_', '/');
                units = replaceAll(units, '-sqr', '^2');
                units = replaceAll(units, '-cube', '^3');

                unit_preferences[name] = units;
            }

            $.post({
                url: site_prefix + "/runs/" + runid + "/" + config + "/tasks/set_unit_preferences/",
                data: unit_preferences,
                success: function success(response) {
                    if (response.Success === true) { } else { }
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });

            self.set_preferred_units();
        };

        that.set_preferred_units = function () {
            var units = undefined;
            var prefs = $("[name^=unitizer_]");
            for (var i = 0; i < prefs.length; i++) {
                var name = prefs[i].name;
                var radios = $("input[name='" + name + "']");
                for (var j = 0; j < radios.length; j++) {
                    units = radios[j].value;
                    $(".units-" + units).addClass("invisible");
                }
                units = $("input[name='" + name + "']:checked").val();
                $(".units-" + units).removeClass("invisible");
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

/* ----------------------------------------------------------------------------
 * RAP_TS
 * ----------------------------------------------------------------------------
 */
var RAP_TS = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#rap_ts_form");
        that.info = $("#rap_ts_form #info");
        that.status = $("#rap_ts_form  #status");
        that.stacktrace = $("#rap_ts_form #stacktrace");
        that.ws_client = new WSClient('rap_ts_form', 'rap_ts');
        that.rq_job_id = null;
        that.rq_job = $("#rap_ts_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.acquire = function () {
            var self = instance;
            var task_msg = "Acquiring RAP TS maps";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/acquire_rap_ts",
                cache: false,
                success: function success(response) {
                    self.status.html(`fetch_and_analyze_rap_ts_rq job submitted: ${response.job_id}`);
                    self.set_rq_job_id(self, response.job_id);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.report = function () {
            var self = instance;
            self.status.html("RAP Timeseries fetched and analyzed")
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

/* ----------------------------------------------------------------------------
 * Team
 * ----------------------------------------------------------------------------
 */
var Team = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#team_form");
        that.info = $("#team_form #info");
        that.status = $("#team_form  #status");
        that.stacktrace = $("#team_form #stacktrace");
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
                        self.form.trigger("TEAM_ADDUSER_TASK_COMPLETED");
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
                        self.form.trigger("TEAM_REMOVEUSER_TASK_COMPLETED");
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
                url: "report/users/",
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

/* ----------------------------------------------------------------------------
 * Map
 * ----------------------------------------------------------------------------
 */
var Map = function () {
    var instance;

    function createInstance() {

        // Use leaflet map
        var that = L.map("mapid", {
            zoomSnap: 0.5,
            zoomDelta: 0.5
        });

        that.scrollWheelZoom.disable();

        that.createPane('subcatchmentsGlPane');
        that.getPane('subcatchmentsGlPane').style.zIndex = 600;

        that.createPane('channelGlPane');
        that.getPane('channelGlPane').style.zIndex = 650;
        //
        // Elevation feedback on mouseover
        //
        that.isFetchingElevation = false;
        that.mouseelev = $("#mouseelev");
        that.drilldown = $("#drilldown");
        that.sub_legend = $("#sub_legend");
        that.sbs_legend = $("#sbs_legend");

        that.fetchTimer;
        that.fetchElevation = function (ev) {
            var self = instance;

            $.post({
                url: "/webservices/elevationquery/",
                data: JSON.stringify({ lat: ev.latlng.lat, lng: ev.latlng.lng }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                cache: false,
                success: function (response) {
                    var elev = response.Elevation.toFixed(1);
                    var lng = coordRound(ev.latlng.lng);
                    var lat = coordRound(ev.latlng.lat);
                    self.mouseelev.show().text("| Elevation: " + elev + " m | Cursor: " + lng + ", " + lat);
                },
                error: function (jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                complete: function () {
                    // Reset the timer in the complete callback
                    clearTimeout(self.fetchTimer);
                    self.fetchTimer = setTimeout(function () {
                        self.isFetchingElevation = false;
                    }, 1000); // Wait for 1 seconds before allowing another request
                }
            });
        };

        that.on("mousemove", function (ev) {
            var self = instance;

            if (!that.isFetchingElevation) {
                that.isFetchingElevation = true;
                self.fetchElevation(ev);
            }
        });


        that.on("mouseout", function () {
            var self = instance;
            self.mouseelev.fadeOut(2000);
            that.isFetchingElevation = false;
        });

        // define the base layer and add it to the map
        // does not require an API key
        // https://stackoverflow.com/a/32391908
        //
        //
        // h = roads only
        // m = standard roadmap
        // p = terrain
        // r = somehow altered roadmap
        // s = satellite only
        // t = terrain only
        // y = hybrid
        //


        that.googleTerrain = L.tileLayer("https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", {
            maxZoom: 20,
            subdomains: ["mt0", "mt1", "mt2", "mt3"]
        });

        that.googleSat = L.tileLayer("https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {
            maxZoom: 20,
            subdomains: ["mt0", "mt1", "mt2", "mt3"]
        });

        //        that.nlcd = L.tileLayer.wms(
        //            "https://www.mrlc.gov/geoserver/mrlc_display/NLCD_2016_Land_Cover_L48/wms?", {
        //            layers: "NLCD_2016_Land_Cover_L48",
        //            format: "image/png",
        //            transparent: true
        //        });
        that.usgs_gage = L.geoJson.ajax("", {
            onEachFeature: (feature, layer) => {
                if (feature.properties && feature.properties.Description) {
                    layer.bindPopup(feature.properties.Description, { autoPan: false });
                }
            },
            pointToLayer: (feature, latlng) => {
                return L.circleMarker(latlng, {
                    radius: 8,
                    fillColor: "#ff7800",
                    color: "#000",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            }
        });

        that.snotel_locations = L.geoJson.ajax("", {
            onEachFeature: (feature, layer) => {
                if (feature.properties && feature.properties.Description) {
                    layer.bindPopup(feature.properties.Description, { autoPan: false });
                }
            },
            pointToLayer: (feature, latlng) => {
                return L.circleMarker(latlng, {
                    radius: 8,
                    fillColor: "#000078",
                    color: "#000",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            }
        });

        that.baseMaps = {
            "Satellite": that.googleSat,
            "Terrain": that.googleTerrain,
            //            "2016 NLCD": that.nlcd
        };

        that.overlayMaps = {
            'USGS Gage Locations': that.usgs_gage,
            'SNOTEL Locations': that.snotel_locations
        };

        that.googleSat.addTo(that);
        that.googleTerrain.addTo(that);

        that.ctrls = L.control.layers(that.baseMaps, that.overlayMaps);
        that.ctrls.addTo(that);

        that.onMapChange = function () {
            var self = instance;

            var center = self.getCenter();
            var zoom = self.getZoom();
            var lng = coordRound(center.lng);
            var lat = coordRound(center.lat);
            var map_w = $('#mapid').width()
            $("#mapstatus").text("Center: " + lng +
                ", " + lat +
                " | Zoom: " + zoom +
                " ( Map Width:" + map_w + "px )");

        };

        that.hillQuery = function (query_url) {
            var self = instance;
            $.get({
                url: query_url,
                cache: false,
                success: function success(response) {
                    self.drilldown.html(response);
                    var project = Project.getInstance();
                    project.set_preferred_units();
                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.chnQuery = function (topazID) {
            var self = instance;
            var query_url = "report/chn_summary/" + topazID + "/";
            self.hillQuery(query_url);
        };

        that.subQuery = function (topazID) {
            var self = instance;
            var query_url = "report/sub_summary/" + topazID + "/";
            self.hillQuery(query_url);
        };


        //
        // View Methods
        //
        that.loadUSGSGageLocations = function () {
            var self = instance;
            if (self.getZoom() < 9) {
                return;
            }

            if (!self.hasLayer(self.usgs_gage)) {
                return;
            }

            var bounds = self.getBounds();
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [parseFloat(sw.lng), parseFloat(sw.lat), parseFloat(ne.lng), parseFloat(ne.lat)];

            self.usgs_gage.refresh(
                [site_prefix + '/resources/usgs/gage_locations/?&bbox=' + self.getBounds().toBBoxString() + '']);
        };

        that.loadSnotelLocations = function () {
            var self = instance;
            if (self.getZoom() < 9) {
                return;
            }

            if (!self.hasLayer(self.snotel_locations)) {
                return;
            }

            var bounds = self.getBounds();
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [parseFloat(sw.lng), parseFloat(sw.lat), parseFloat(ne.lng), parseFloat(ne.lat)];

            self.snotel_locations.refresh(
                [site_prefix + '/resources/snotel/snotel_locations/?&bbox=' + self.getBounds().toBBoxString() + '']);
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

/* ----------------------------------------------------------------------------
 * Channel Delineation
 * ----------------------------------------------------------------------------
 */
var ChannelDelineation = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.zoom_min = 12;
        that.data = null; // JSON from Flask
        that.polys = null; // Leaflet geoJSON layer
        that.topIds = [];
        that.glLayer = null;        // <- webgl layer
        that.labels = L.layerGroup();

        that.style = function (feature) {
            let order = parseInt(feature.properties.Order, 6);

            if (order > 7) {
                order = 7;
            }

            // simple map for Orders 1–6
            const colors = {
                0: "#8AE5FE",
                1: "#65C8FE",
                2: "#479EFF",
                3: "#306EFE",
                4: "#2500F4",
                5: "#6600cc",
                6: "#50006b",
                7: "#6b006b",
            };
            // default for everything else (>6 or missing)
            const stroke = colors[order] || "#1F00CF";
            const fill = colors[order - 1] || "#2838FE";
            return {
                color: stroke,
                weight: 1,
                opacity: 1,
                fillColor: fill,
                fillOpacity: 0.9
            };
        };

        that.labelStyle = "color:blue; text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF;";

        that.form = $("#build_channels_form");
        that.info = $("#build_channels_form #info");
        that.status = $("#build_channels_form  #status");
        that.stacktrace = $("#build_channels_form #stacktrace");
        that.ws_client = new WSClient('build_channels_form', 'channel_delineation');
        that.rq_job_id = null;
        that.rq_job = $("#build_channels_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.remove = function () {
            var self = instance;
            var map = Map.getInstance();

            if (self.glLayer !== null) {
                map.ctrls.removeLayer(self.glLayer);
                map.removeLayer(self.glLayer);
            }

            if (self.labels !== null) {
                map.ctrls.removeLayer(self.labels);
                map.removeLayer(self.labels);
            }
        };

        that.has_dem = function (onSuccessCallback) {
            var self = instance;

            $.get({
                url: "query/has_dem/",
                cache: false,
                success: onSuccessCallback,
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };


        that.build = function () {
            var self = instance;

            self.remove();
            Outlet.getInstance().remove();

            var task_msg = "Delineating channels";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/fetch_dem_and_build_channels",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`fetch_dem_and_build_channels_rq job submitted: ${response.job_id}`);
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
        };

        that.onMapChange = function () {
            var self = instance;
            var map = Map.getInstance();
            
            var center = map.getCenter();
            var zoom = map.getZoom();
            var bounds = map.getBounds();
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [sw.lng, sw.lat, ne.lng, ne.lat];
            var distance = map.distance(ne, sw);

            $("#map_center").val([center.lng, center.lat]);
            $("#map_zoom").val(zoom);
            $("#map_bounds").val(extent);
            $("#map_distance").val(distance);

            if (zoom >= self.zoom_min || ispoweruser) {
                $("#btn_build_channels").prop("disabled", false);
                $("#hint_build_channels").text("");

                $("#btn_build_channels_en").prop("disabled", false);
                $("#hint_build_channels_en").text("");
            } else {
                $("#btn_build_channels").prop("disabled", true);
                $("#hint_build_channels").text("Area is too large, zoom must be 13 " + self.zoom_min.toString() + ", current zoom is " + zoom.toString());

                $("#btn_build_channels_en").prop("disabled", true);
                $("#hint_build_channels_en").text("Area is too large, zoom must be 13 " + self.zoom_min.toString() + ", current zoom is " + zoom.toString());
            }
        };

        that.show = function () {
            var self = instance;

            self.remove();
            var task_msg = "Identifying topaz_pass";


            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // Ask the Cloud what pass we are on. If the subcatchments have been
            // eliminated we can just show the channels in the watershed. The
            // underlying vector will contain feature.properties.TopazID attributes
            $.get({
                url: "query/delineation_pass/",
                cache: false,
                success: function success(response) {
                    response = parseInt(response, 10);
                    if ($.inArray(response, [0, 1, 2]) === -1) {
                        self.pushResponseStacktrace(self, { Error: "Error Determining Delineation Pass" });
                        return;
                    }

                    if (response === 0) {
                        self.pushResponseStacktrace(self, { Error: "Channels not delineated" });
                        return;
                    }

                    if (response === 1) {
                        self.show_1();
                    } else {
                        self.show_2();
                    }
                    self.status.html(task_msg + "... Success");
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        // Topaz Pass 1
        // Shows the NETFUL.ARC built by TOPAZ
        // --- hex → {r,g,b,a} helper (CSS-Tricks / SO recipe) ---
        const fromHex = hex => {
            hex = hex.replace(/^#/, '');
            const num = parseInt(hex, 16);
            return {
                r: ((num >> 16) & 255) / 255,
                g: ((num >> 8) & 255) / 255,
                b: (num & 255) / 255,
                a: 1
            };
        }; //  [oai_citation:5‡Stack Overflow](https://stackoverflow.com/questions/5623838/rgb-to-hex-and-hex-to-rgb?utm_source=chatgpt.com)

        // same palette you used, just no alpha here
        const palette = [
            "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
            "#2500F4", "#6600cc", "#50006b", "#6b006b"
        ].map(fromHex);

        //------------------------------------------------------------------
        // glify show_1
        //------------------------------------------------------------------
        that.show_1 = function () {
            const self = instance;
            self.remove();

            const task_msg = "Displaying Channel Map (WebGL)";
            self.status.text(`${task_msg}…`);

            $.getJSON("resources/netful.json")
                .done(function (fc) {
                    const map = Map.getInstance();
                    self.glLayer = L.glify.layer({
                        geojson: fc,
                        paneName: 'channelGlPane',
                        glifyOptions: {
                            opacity: 0.9,
                            border: false,
                            color: (i, feat) => {
                                let order = parseInt(feat.properties.Order, 10) || 4;
                                order = Math.min(order, 7);
                                return palette[order];
                            }
                        }
                    }).addTo(map);

                    map.ctrls.addOverlay(self.glLayer, "Channels");

                    self.status.text(`${task_msg} – done`);
                    self.report();
                })
                .fail((jqXHR, textStatus, err) =>
                    self.pushErrorStacktrace(self, jqXHR, textStatus, err)
                );
        };

        // Topaz Pass 2
        // Shows the channels from SUBWTA.ARC built by TOPAZ (channels end with '4')
        //------------------------------------------------------------------
        // glify show_2  – channels from SUBWTA.ARC   (Topaz “4” polygons)
        //------------------------------------------------------------------
        that.show_2 = function () {
            const self = instance;
            self.remove();                                   // clear previous layers
            self.status.text("Displaying SUBWTA channels…");

            $.getJSON("resources/channels.json")
                .done(function (fc) {
                    const map = Map.getInstance();

                    // ---------- WebGL polygons ----------
                    self.glLayer = L.glify.layer({
                        geojson: fc,
                        paneName: 'channelGlPane',
                        glifyOptions: {
                            opacity: 0.6,
                            border: true,
                            color: (i, feat) => {
                                // reuse your style logic – fall back to order 4
                                let order = parseInt(feat.properties.Order, 10) || 4;
                                order = Math.min(order, 7);
                                return palette[order];     // palette[] == [{r,g,b,a}, …]
                            },
                            click: (e, feat) => {
                                const map = Map.getInstance();
                                map.chnQuery(feat.properties.TopazID); // same as before
                            }
                        }
                    }).addTo(map);

                    map.ctrls.addOverlay(self.glLayer, "Channels");

                    // ---------- text labels ----------
                    self.labels = L.layerGroup();
                    const seen = new Set();

                    fc.features.forEach(f => {
                        const topId = f.properties.TopazID;
                        if (seen.has(topId)) return;
                        seen.add(topId);

                        // crude centroid – last ring, first vertex (matches old code)
                        const ring = f.geometry.coordinates[0][0];
                        const center = [ring[1], ring[0]];          // [lat,lng]

                        const lbl = L.marker(center, {
                            icon: L.divIcon({
                                className: "label",
                                html: `<div style="${self.labelStyle}">${topId}</div>`
                            })
                        });
                        self.labels.addLayer(lbl);
                    });

                    //self.labels.addTo(map);
                    map.ctrls.addOverlay(self.labels, "Channel Labels");

                    self.status.text("Displaying SUBWTA channels – done");
                    self.report();
                })
                .fail((jq, txt, err) =>
                    self.pushErrorStacktrace(self, jq, txt, err)
                );
        };

        that.report = function () {
            var self = instance;

            $.get({
                url: "report/channel/",
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

/* ----------------------------------------------------------------------------
 * Set Outlet
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
        that.rq_job_id = null;
        that.rq_job = $("#set_outlet_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.outlet = null;
        that.outletMarker = L.marker();

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
                url: "report/outlet/",
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

/* ----------------------------------------------------------------------------
 * Subcatchment Delineation
 * ----------------------------------------------------------------------------
 */
var SubcatchmentDelineation = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#build_subcatchments_form");
        that.info = $("#build_subcatchments_form #info");
        that.status = $("#build_subcatchments_form  #status");
        that.stacktrace = $("#build_subcatchments_form #stacktrace");
        that.ws_client = new WSClient('build_subcatchments_form', 'subcatchment_delineation');
        that.rq_job_id = null;
        that.rq_job = $("#build_subcatchments_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        //----------------------------------------------------------------------
        // ─── CONSTANTS / HELPERS ──────────────────────────────────────────────
        //----------------------------------------------------------------------
        const fromHex = hex => {
            hex = hex.replace(/^#/, '');
            const n = parseInt(hex, 16);
            return {
                r: ((n >> 16) & 255) / 255,
                g: ((n >> 8) & 255) / 255,
                b: (n & 255) / 255,
                a: 0.5
            };
        };

        // default & clear colours in both CSS and WebGL formats
        that.defaultStyle = {
            color: '#ff7800',
            weight: 2,
            opacity: 0.65,
            fillColor: '#ff7800',
            fillOpacity: 0.3
        };
        that.clearStyle = {
            color: '#ff7800',
            weight: 2,
            opacity: 0.65,
            fillColor: '#ffffff',
            fillOpacity: 0.0
        };
        const COLOR_DEFAULT = fromHex(that.defaultStyle.fillColor);
        const COLOR_CLEAR = fromHex(that.clearStyle.fillColor);

        //----------------------------------------------------------------------
        // ─── STATE ────────────────────────────────────────────────────────────
        //----------------------------------------------------------------------
        that.data = null;          // FeatureCollection GeoJSON
        that.glLayer = null;          // current WebGL layer
        that.labels = L.layerGroup();
        that.cmapMode = 'default';     // active colour-map key
        that.topIds = [];

        // various query-result dicts filled by cmap*() functions
        that.dataCover = null;
        that.dataPhosphorus = null;
        that.dataRunoff = null;
        that.dataLoss = null;


        that.enableColorMap = function (cmap_name) {
            if (cmap_name === "dom_lc") {
                $("#sub_cmap_radio_dom_lc").prop("disabled", false);
            } else if (cmap_name === "rangeland_cover") {
                $("#sub_cmap_radio_rangeland_cover").prop("disabled", false);
            } else if (cmap_name === "dom_soil") {
                $("#sub_cmap_radio_dom_soil").prop("disabled", false);
            } else if (cmap_name === "slp_asp") {
                $("#sub_cmap_radio_slp_asp").prop("disabled", false);
            } else {
                throw "Map.enableColorMap received unexpected parameter: " + cmap_name;
            }
        };

        that.getCmapMode = function () {
            if ($("#sub_cmap_radio_dom_lc").prop("checked")) {
                return "dom_lc";
            } else if ($("#sub_cmap_radio_dom_soil").prop("checked")) {
                return "dom_soil";
            } else if ($("#sub_cmap_radio_slp_asp").prop("checked")) {
                return "slp_asp";
            } else if ($("#sub_cmap_radio_rangeland_cover").prop("checked")) {
                return "rangeland_coer";
            } else {
                return "default";
            }
        };

        that.setColorMap = function (cmap_name) {
            var self = instance;

            if (self.polys === null) {
                throw "Subcatchments have not been drawn";
            }

            if (cmap_name === "default") {
                self.cmap();
                Map.getInstance().sub_legend.html("");
            } else if (cmap_name === "slp_asp") {
                self.renderSlpAsp();
            } else if (cmap_name === "dom_lc") {
                self.renderNLCD();
            } else if (cmap_name === "rangeland_cover") {
                self.renderRangelandCover();
            } else if (cmap_name === "dom_soil") {
                self.renderSoils();
            } else if (cmap_name === "landuse_cover") {
                self.renderCover();
            } else if (cmap_name === "sub_runoff") {
                self.renderRunoff();
            } else if (cmap_name === "sub_subrunoff") {
                self.renderSubrunoff();
            } else if (cmap_name === "sub_baseflow") {
                self.renderBaseflow();
            } else if (cmap_name === "sub_loss") {
                self.renderLoss();
            } else if (cmap_name === "sub_phosphorus") {
                self.renderPhosphorus();
            } else if (cmap_name === "sub_rhem_runoff") {
                self.renderRhemRunoff();
            } else if (cmap_name === "sub_rhem_sed_yield") {
                self.renderRhemSedYield();
            } else if (cmap_name === "sub_rhem_soil_loss") {
                self.renderRhemSoilLoss();
            } else if (cmap_name === "ash_load") {
                self.renderAshLoad();
            } else if (cmap_name === "wind_transport (kg/ha)") {
                self.renderAshTransport();
            } else if (cmap_name === "water_transport (kg/ha") {
                self.renderAshTransport();
            } else if (cmap_name === "ash_transport (kg/ha)") {
                self.renderAshTransport();
            }

            if (cmap_name === "grd_loss") {
                self.renderClear();
                self.renderGriddedLoss();
            } else {
                self.removeGrid();
            }
        };

        //----------------------------------------------------------------------
        // ─── COMMON COLOUR FUNCTION (used by WebGL callback) ─────────────────
        //----------------------------------------------------------------------
        that._colorFn = function (feat) {
            var self = instance;
            const id = feat.properties.TopazID;

            switch (self.cmapMode) {
                case 'default': return COLOR_DEFAULT;
                case 'clear': return COLOR_CLEAR;

                /* ====== slope / aspect ================================================= */
                case 'slp_asp': {
                    const hsvHex = self.dataSlpAsp?.[id];                 // '#aabbcc'
                    return hsvHex ? fromHex(hsvHex) : COLOR_DEFAULT;
                }

                /* ====== land-cover % =================================================== */
                case 'cover': {
                    if (!self.dataCover) return COLOR_DEFAULT;
                    const v = self.dataCover[id];                         // 0-100
                    const hex = self.cmapperCover.map(v);                 // '#rrggbb'
                    return fromHex(hex);
                }

                /* ====== phosphorus, runoff, loss – share the same pattern ============= */
                case 'phosphorus': {
                    if (!self.dataPhosphorus) return COLOR_DEFAULT;
                    const v = parseFloat(self.dataPhosphorus[id].value);  // kg/ha
                    const r = self._rangePhosphorus;                      // current slider
                    const hex = self.cmapperPhosphorus.map(v / r);
                    return fromHex(hex);
                }

                case 'runoff': {
                    const v = parseFloat(self.dataRunoff[id].value);      // mm
                    const r = self._rangeRunoff;
                    const hex = that.cmapperRunoff.map(v / r);
                    return fromHex(hex);
                }

                case 'loss': {
                    const v = parseFloat(self.dataLoss[id].value);        // kg/ha
                    const r = self._rangeLoss;
                    const hex = self.cmapperLoss.map(v / r);
                    return fromHex(hex);
                }

                default: return COLOR_DEFAULT;
            }
        };

        //----------------------------------------------------------------------
        // ─── GL LAYER (re)BUILDER ────────────────────────────────────────────
        //----------------------------------------------------------------------
        that._refreshGlLayer = function () {
            var self = instance;

            console.debug("SubcatchmentDelineation._refreshGlLayer() called");
            console.debug("cmapMode:", self.cmapMode);
            console.log("data:", self.data);

            const map = Map.getInstance();

            if (self.glLayer) {
                self.glLayer.remove();                      // dispose VBOs & canvas
                // keep layer-control checkbox position consistent
                map.ctrls.removeLayer(self.glLayer);
            }

            self.glLayer = L.glify.layer({
                geojson: self.data,
                paneName: 'subcatchmentsGlPane',
                glifyOptions: {
                    opacity: 0.5,
                    border: true,
                    color: (i, f) => self._colorFn(f),
                    click: (e, f) => map.subQuery(f.properties.TopazID)
                }
            }).addTo(map);

            map.ctrls.addOverlay(self.glLayer, 'Subcatchments');
        };

        //----------------------------------------------------------------------
        // ─── LABELS (unchanged, just recalculated once) ──────────────────────
        //----------------------------------------------------------------------
        that._buildLabels = function () {
            that.labels.clearLayers();
            const seen = new Set();

            that.data.features.forEach(f => {
                const id = f.properties.TopazID;
                if (seen.has(id)) return;
                seen.add(id);

                const center = polylabel(f.geometry.coordinates, 1.0);
                const marker = L.marker([center[1], center[0]], {
                    icon: L.divIcon({
                        className: 'label',
                        html: `<div style="${that.labelStyle}">${id}</div>`
                    })
                });
                that.labels.addLayer(marker);
            });
        };

        //----------------------------------------------------------------------
        // ─── INITIAL DRAW ────────────────────────────────────────────────────
        //----------------------------------------------------------------------
        that.show = function () {
            var self = instance;

            self.cmapMode = 'default';           // reset to default cmap

            $.get({
                url: 'resources/subcatchments.json',
                cache: false,
                success: self._onShowSuccess,
                error: jq => self.pushResponseStacktrace(self, jq.responseJSON),
                fail: (jq, s, e) => that.pushErrorStacktrace(that, jq, s, e)
            });
        };

        that._onShowSuccess = function (fc) {
            var self = instance;

            self.data = fc;                      // GeoJSON FeatureCollection
            self._buildLabels();                 // hidden by default

            const map = Map.getInstance();
            self._refreshGlLayer();              // draw polygons

            map.ctrls.addOverlay(self.labels, 'Subcatchment Labels'); // off by default
            self.report();
        };

        //----------------------------------------------------------------------
        // ─── SIMPLE COLOUR-MAPS (default & clear) ────────────────────────────
        //----------------------------------------------------------------------
        that.render = function () { that.cmapMode = 'default'; that._refreshGlLayer(); };
        that.renderClear = function () { that.cmapMode = 'clear'; that._refreshGlLayer(); };

        //----------------------------------------------------------------------
        // ─── DATA-DRIVEN COLOUR-MAPS (examples shown) ────────────────────────
        //----------------------------------------------------------------------
        /* ---------- slope / aspect ------------------------------------------ */
        that.renderSlpAsp = function () {
            that.status.text('Loading slope/aspect …');
            $.get({
                url: 'query/watershed/subcatchments/',
                cache: false,
                success: data => {
                    that.dataSlpAsp = data;          // {TopazID:'#rrggbb', …}
                    that.cmapMode = 'slp_asp';
                    that._refreshGlLayer();
                },
                error: jq => that.pushResponseStacktrace(that, jq.responseJSON),
                fail: (jq, s, e) => that.pushErrorStacktrace(that, jq, s, e)
            }).always(() => {
                $.get('resources/legends/slope_aspect/').done(html => {
                    Map.getInstance().sub_legend.html(html);
                });
            });
        };

        /* ----------  % land-cover  ------------------------------------------ */
        that.renderCover = function () {
            $.get('query/landuse/cover/subcatchments/')
                .done(data => {
                    that.dataCover = data;          // {TopazID:0-100, …}
                    that.cmapMode = 'cover';
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };

        /* ---------- phosphorus (kg/ha)  ------------------------------------- */
        that.renderPhosphorus = function () {
            $.get('query/wepp/phosphorus/subcatchments/')
                .done(data => {
                    that.dataPhosphorus = data;
                    that._rangePhosphorus = parseFloat($('#wepp_sub_cmap_range_phosphorus').val()) ** 2 || 1;
                    that.cmapMode = 'phosphorus';
                    that._refreshGlLayer();
                    // legend / unitizer calls unchanged …
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };

        /* ---------- runoff & variants --------------------------------------- */
        that.renderRunoff = function () { _getRunoff('query/wepp/runoff/subcatchments/', 'runoff'); };
        that.renderSubrunoff = function () { _getRunoff('query/wepp/subrunoff/subcatchments/', 'runoff'); };
        that.renderBaseflow = function () { _getRunoff('query/wepp/baseflow/subcatchments/', 'runoff'); };
        function _getRunoff(url, mode) {
            $.get(url)
                .done(data => {
                    that.dataRunoff = data;
                    const slider = $('#wepp_sub_cmap_range_runoff').val();
                    that._rangeRunoff = 25.0 * (parseFloat(slider) ** 2);
                    that.cmapMode = mode;
                    that._refreshGlLayer();
                    // legend / unitizer unchanged
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        }

        /* ---------- loss ----------------------------------------------------- */
        that.renderLoss = function () {
            $.get('query/wepp/loss/subcatchments/')
                .done(data => {
                    that.dataLoss = data;
                    that._rangeLoss = parseFloat($('#wepp_sub_cmap_range_loss').val()) || 1;
                    that.cmapMode = 'loss';
                    that._refreshGlLayer();
                    // legend / unitizer unchanged
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };

        //
        // Gridded Loss
        //
        that.rangeGriddedLoss = $('#wepp_grd_cmap_range_loss');
        that.labelGriddedLossMin = $("#wepp_grd_cmap_range_loss_min");
        that.labelGriddedLossMax = $("#wepp_grd_cmap_range_loss_max");
        that.labelGriddedLossUnits = $("#wepp_grd_cmap_range_loss_units");

        that.removeGrid = function () {
            var self = instance;
            var map = Map.getInstance();

            if (self.grid !== null) {
                map.ctrls.removeLayer(self.grid);
                map.removeLayer(self.grid);
            }
        };

        that.renderGriddedLoss = function () {
            var self = instance;

            self.gridlabel = "Soil Deposition/Loss";
            var map = Map.getInstance();

            self.removeGrid();

            self.grid = L.leafletGeotiff(
                'resources/flowpaths_loss.tif',
                {
                    band: 0,
                    displayMin: 0,
                    displayMax: 1,
                    name: self.gridlabel,
                    colorScale: "jet2",
                    opacity: 1.0,
                    clampLow: true,
                    clampHigh: true,
                    //vector:true,
                    arrowSize: 20
                }
            ).addTo(map);
            self.updateGriddedLoss();
            map.ctrls.addOverlay(self.grid, "Gridded Output");
        };

        that.updateGriddedLoss = function () {
            var self = instance;
            var v = parseFloat(self.rangeGriddedLoss.val());
            if (self.grid !== null) {
                self.grid.setDisplayRange(-1.0 * v, v);
            }

            $.get({
                url: "unitizer/",
                data: { value: v, in_units: 'kg/m^2' },
                cache: false,
                success: function success(response) {
                    self.labelGriddedLossMax.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer/",
                data: { value: -1.0 * v, in_units: 'kg/m^2' },
                cache: false,
                success: function success(response) {
                    self.labelGriddedLossMin.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer_units/",
                data: { in_units: 'kg/m^2' },
                cache: false,
                success: function success(response) {
                    self.labelGriddedLossUnits.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };


        that.cmapCallback = function (lcjson) {
            var self = instance;

            if (lcjson === null) {
                throw "query returned null, cannot determine colors";
            }

            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var color = lcjson[topId].color;

                layer.setStyle({
                    color: "#FFFFFF",
                    weight: 1,
                    opacity: 0.9,
                    fillColor: color,
                    fillOpacity: 0.9
                });

                layer.redraw();
            });
        };

        // Rhem Visualizations

        //
        // RhemRunoff
        //
        that.dataRhemRunoff = null;
        that.rangeRhemRunoff = $('#rhem_sub_cmap_range_runoff');
        that.labelRhemRunoffMin = $('#rhem_sub_cmap_canvas_runoff_min');
        that.labelRhemRunoffMax = $('#rhem_sub_cmap_canvas_runoff_max');
        that.labelRhemRunoffUnits = $('#rhem_sub_cmap_canvas_runoff_units');
        that.cmapperRhemRunoff = createColormap({ colormap: 'winter', nshades: 64 });

        that.cmapRhemRunoff = function () {
            var self = instance;
            $.get({
                url: "query/rhem/runoff/subcatchments/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataRhemRunoff = data;
                    self.renderRhemRunoff();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderRhemRunoff = function () {
            var self = instance;

            var r = parseFloat(self.rangeRhemRunoff.val()); // 25.0 * Math.pow(parseFloat(self.rangeRhemRunoff.val()), 2.00);
            self.labelRhemRunoffMin.html("0.000");

            $.get({
                url: "unitizer/",
                data: { value: r, in_units: 'mm' },
                cache: false,
                success: function success(response) {
                    self.labelRhemRunoffMax.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer_units/",
                data: { in_units: 'mm' },
                cache: false,
                success: function success(response) {
                    self.labelRhemRunoffUnits.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });


            if (self.polys == null) {
                return;
            }

            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataRhemRunoff[topId].value);

                var c = self.cmapperRhemRunoff.map(v / r);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end RhemRunoff

        //
        // RhemSedYield
        //
        that.dataRhemSedYield = null;
        that.rangeRhemSedYield = $('#rhem_sub_cmap_range_sed_yield');
        that.labelRhemSedYieldMin = $('#rhem_sub_cmap_canvas_sed_yield_min');
        that.labelRhemSedYieldMax = $('#rhem_sub_cmap_canvas_sed_yield_max');
        that.labelRhemSedYieldUnits = $('#rhem_sub_cmap_canvas_sed_yield_units');
        that.cmapperRhemSedYield = createColormap({ colormap: 'viridis', nshades: 64 });

        that.cmapRhemSedYield = function () {
            var self = instance;
            $.get({
                url: "query/rhem/sed_yield/subcatchments/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataRhemSedYield = data;
                    self.renderRhemSedYield();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderRhemSedYield = function () {
            var self = instance;

            var r = parseFloat(self.rangeRhemSedYield.val());
            if (r < 1) {
                r = Math.pow(r, 2.0);
            }

            self.labelRhemSedYieldMin.html("0.000");


            $.get({
                url: "unitizer/",
                data: { value: r, in_units: 'kg/ha' },
                cache: false,
                success: function success(response) {
                    self.labelRhemSedYieldMax.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer_units/",
                data: { in_units: 'kg/ha' },
                cache: false,
                success: function success(response) {
                    self.labelRhemSedYieldUnits.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            if (self.polys == null) {
                return;
            }

            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataRhemSedYield[topId].value);
                var c = self.cmapperRhemSedYield.map(v / r);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end RhemSedYield

        //
        // AshLoad
        //
        that.dataAshLoad = null;
        that.rangeAshLoad = $('#ash_sub_cmap_range_load');
        that.labelAshLoadMin = $('#ash_sub_cmap_canvas_load_min');
        that.labelAshLoadMax = $('#ash_sub_cmap_canvas_load_max');
        that.labelAshLoadUnits = $('#ash_sub_cmap_canvas_load_units');
        that.cmapperAshLoad = createColormap({ colormap: "jet2", nshades: 64 });

        that.cmapAshLoad = function () {
            var self = instance;
            $.get({
                url: "query/ash_out/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataAshLoad = data;
                    self.renderAshLoad();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderAshLoad = function () {
            var self = instance;

            var r = parseFloat(self.rangeAshLoad.val());

            $.get({
                url: "unitizer/",
                data: { value: 0 * r, in_units: 'mm' },
                cache: false,
                success: function success(response) {
                    self.labelAshLoadMin.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer/",
                data: { value: r, in_units: 'mm' },
                cache: false,
                success: function success(response) {
                    self.labelAshLoadMax.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer_units/",
                data: { in_units: 'mm' },
                cache: false,
                success: function success(response) {
                    self.labelAshLoadUnits.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });


            if (self.polys == null) {
                return;
            }

            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataAshLoad[topId]['ash_ini_depth (mm)']);
                var c = self.cmapperAshLoad.map(v / r);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end AshLoad 


        //
        // AshTransport
        //
        that.dataAshTransport = null;
        that.rangeAshTransport = $('#ash_sub_cmap_range_transport');
        that.labelAshTransportMin = $('#ash_sub_cmap_canvas_transport_min');
        that.labelAshTransportMax = $('#ash_sub_cmap_canvas_transport_max');
        that.labelAshTransportUnits = $('#ash_sub_cmap_canvas_transport_units');
        that.cmapperAshTransport = createColormap({ colormap: "jet2", nshades: 64 });

        that.cmapAshTransport = function () {
            var self = instance;
            $.get({
                url: "query/ash_out/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataAshTransport = data;
                    self.renderAshTransport();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.getAshTransportMeasure = function () {
            return $("input[name='wepp_sub_cmap_radio']:checked").val();
        }

        that.renderAshTransport = function () {
            var self = instance;

            var r = parseFloat(self.rangeAshTransport.val());

            $.get({
                url: "unitizer/",
                data: { value: 0 * r, in_units: 'tonne/ha' },
                cache: false,
                success: function success(response) {
                    self.labelAshTransportMin.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer/",
                data: { value: r, in_units: 'tonne/ha' },
                cache: false,
                success: function success(response) {
                    self.labelAshTransportMax.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer_units/",
                data: { in_units: 'tonne/ha' },
                cache: false,
                success: function success(response) {
                    self.labelAshTransportUnits.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });


            if (self.polys == null) {
                return;
            }

            self.polys.eachLayer(function (layer) {
                var measure = self.getAshTransportMeasure();
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataAshTransport[topId][measure]) / 1000.0;
                var c = self.cmapperAshTransport.map(v / r);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end AshTransport 

        //
        // RhemSoilLoss
        //
        that.dataRhemSoilLoss = null;
        that.rangeRhemSoilLoss = $('#rhem_sub_cmap_range_soil_loss');
        that.labelRhemSoilLossMin = $('#rhem_sub_cmap_canvas_soil_loss_min');
        that.labelRhemSoilLossMax = $('#rhem_sub_cmap_canvas_soil_loss_max');
        that.labelRhemSoilLossUnits = $('#rhem_sub_cmap_canvas_soil_loss_units');
        that.cmapperRhemSoilLoss = createColormap({ colormap: "jet2", nshades: 64 });

        that.cmapRhemSoilLoss = function () {
            var self = instance;
            $.get({
                url: "query/rhem/soil_loss/subcatchments/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataRhemSoilLoss = data;
                    self.renderRhemSoilLoss();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderRhemSoilLoss = function () {
            var self = instance;

            var r = parseFloat(self.rangeRhemSoilLoss.val());

            $.get({
                url: "unitizer/",
                data: { value: -1.0 * r, in_units: 'kg/ha' },
                cache: false,
                success: function success(response) {
                    self.labelRhemSoilLossMin.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer/",
                data: { value: r, in_units: 'kg/ha' },
                cache: false,
                success: function success(response) {
                    self.labelRhemSoilLossMax.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "unitizer_units/",
                data: { in_units: 'kg/ha' },
                cache: false,
                success: function success(response) {
                    self.labelRhemSoilLossUnits.html(response.Content);
                    Project.getInstance().set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });


            if (self.polys == null) {
                return;
            }

            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataRhemSoilLoss[topId].value);
                var c = self.cmapperRhemSoilLoss.map(v / (2.0 * r) + 0.5);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end RhemSoilLoss



        //
        // Controller Methods
        //
        that.build = function () {
            var self = instance;
            var map = Map.getInstance();

            var task_msg = "Building Subcatchments";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            if (self.polys !== null) {
                map.ctrls.removeLayer(self.polys);
                map.removeLayer(self.polys);

                map.ctrls.removeLayer(self.labels);
                map.removeLayer(self.labels);
            }

            $.post({
                url: "rq/api/build_subcatchments_and_abstract_watershed",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_subcatchments_and_abstract_watershed_rq job submitted: ${response.job_id}`);
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
        };

        that.report = function () {
            var self = instance;
            var project = Project.getInstance();
            var task_msg = "Fetching Summary";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "report/watershed/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.status.html(task_msg + "... Success");
                    project.set_preferred_units();
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

/* ----------------------------------------------------------------------------
 * Rangeland Cover
 * ----------------------------------------------------------------------------
 */

var RangelandCover = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#rangeland_cover_form");
        that.info = $("#rangeland_cover_form #info");
        that.status = $("#rangeland_cover_form  #status");
        that.stacktrace = $("#rangeland_cover_form #stacktrace");
        that.ws_client = new WSClient('rangeland_cover_form', 'rangeland_cover');
        that.rq_job_id = null;
        that.rq_job = $("#rangeland_cover_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;

            var task_msg = "Building rangeland_cover";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/build_rangeland_cover/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("RANGELAND_COVER_BUILD_TASK_COMPLETED");
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

        that.report = function () {
            var self = instance;
            $.get({
                url: "report/rangeland_cover/",
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

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='rangeland_cover_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var rangeland_rap_year = $("#rangeland_cover_form #rap_year").val();

            var task_msg = "Setting Mode to " + mode + " (" + rangeland_rap_year + ")";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync rangeland_cover with nodb
            $.post({
                url: "tasks/set_rangeland_cover_mode/",
                data: { "mode": mode, "rap_year": rangeland_rap_year },
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
            self.showHideControls(mode);
        };

        that.showHideControls = function (mode) {
            if (mode == 2) {
                $("#rangeland_cover_form #rangeland_cover_rap_year_div").show();
            } else {
                $("#rangeland_cover_form #rangeland_cover_rap_year_div").hide();
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


/* ----------------------------------------------------------------------------
 * Landuse
 * ----------------------------------------------------------------------------
 */
var Landuse = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#landuse_form");
        that.info = $("#landuse_form #info");
        that.status = $("#landuse_form  #status");
        that.stacktrace = $("#landuse_form #stacktrace");
        that.ws_client = new WSClient('landuse_form', 'landuse');
        that.rq_job_id = null;
        that.rq_job = $("#landuse_form #rq_job");


        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building landuse";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var formData = new FormData($('#landuse_form')[0]);

            $.post({
                url: "rq/api/build_landuse",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_landuse job submitted: ${response.job_id}`);
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
        };

        that.modify_coverage = function (dom, cover, value) {
            var data = {
                dom: dom,
                cover: cover,
                value: value
            };

            $.post({
                url: "tasks/modify_landuse_coverage/",
                data: JSON.stringify(data),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.modify_mapping = function (dom, newdom) {
            var self = instance;

            var data = {
                dom: dom,
                newdom: newdom
            };

            $.post({
                url: "tasks/modify_landuse_mapping/",
                data: JSON.stringify(data),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    self.report();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.report = function () {
            var self = instance;
            $.get({
                url: "report/landuse/",
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

        that.restore = function (landuse_mode, landuse_single_selection) {
            console.log("restore landuse mode: " + landuse_mode);
            var self = instance;
            $("#landuse_mode" + landuse_mode).prop("checked", true);

            $('#landuse_single_selection').val('{{ landuse.single_selection }}').prop('selected', true);

            self.showHideControls(landuse_mode);
        };

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='landuse_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var landuse_single_selection = $("#landuse_single_selection").val();

            var task_msg = "Setting Mode to " + mode + " (" + landuse_single_selection + ")";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync landuse with nodb
            $.post({
                url: "tasks/set_landuse_mode/",
                data: { "mode": mode, "landuse_single_selection": landuse_single_selection },
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
            self.showHideControls(mode);
        };

        that.setLanduseDb = function (db) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (db === undefined) {
                db = $("input[name='landuse_db']:checked").val();
            }

            var task_msg = "Setting Landuse Db to " + db;

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync landuse with nodb
            $.post({
                url: "tasks/set_landuse_db/",
                data: { "landuse_db": db },
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
            self.showHideControls(self.mode);
        };

        that.showHideControls = function (mode) {
            // show the appropriate controls
            if (mode === -1) {
                // neither
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 0) {
                // gridded
                $("#landuse_mode0_controls").show();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 1) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").show();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 2) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").show();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 3) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").show();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 4) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").show();
            } else {
                throw "ValueError: unknown mode";
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

/* ----------------------------------------------------------------------------
 * Treatments
 * ----------------------------------------------------------------------------
 */
var Treatments = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#treatments_form");
        that.info = $("#treatments_form #info");
        that.status = $("#treatments_form  #status");
        that.stacktrace = $("#treatments_form #stacktrace");
        that.ws_client = new WSClient('treatments_form', 'treatments');
        that.rq_job_id = null;
        that.rq_job = $("#treatments_form #rq_job");


        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building treatments";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var formData = new FormData($('#treatments_form')[0]);

            $.post({
                url: "rq/api/build_treatments",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_treatments job submitted: ${response.job_id}`);
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
        };

        that.report = function () {
            var self = instance;
            $.get({
                url: "report/treatments/",
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

        that.restore = function (treatments_mode, treatments_single_selection) {
            console.log("restore treatments mode: " + treatments_mode);
            var self = instance;
            $("#treatments_mode" + treatments_mode).prop("checked", true);

            $('#treatments_single_selection').val('{{ treatments.single_selection }}').prop('selected', true);

            self.showHideControls(treatments_mode);
        };

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='treatments_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var treatments_single_selection = $("#treatments_single_selection").val();

            var task_msg = "Setting Mode to " + mode + " (" + treatments_single_selection + ")";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync treatments with nodb
            $.post({
                url: "tasks/set_treatments_mode/",
                data: { "mode": mode, "treatments_single_selection": treatments_single_selection },
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
            self.showHideControls(mode);
        };

        that.showHideControls = function (mode) {
            // show the appropriate controls
            if (mode === -1) {
                // undefined
                $("#treatments_mode1_controls").hide();
                $("#treatments_mode4_controls").hide();
            } else if (mode === 1) {
                // selection
                $("#treatments_mode1_controls").show();
                $("#treatments_mode4_controls").hide();
            } else if (mode === 4) {
                // map
                $("#treatments_mode1_controls").hide();
                $("#treatments_mode4_controls").show();
            } else {
                throw "ValueError: unknown mode";
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

/* ----------------------------------------------------------------------------
 * RangelandCover
 * ----------------------------------------------------------------------------
 */
var RangelandCoverModify = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#modify_rangeland_cover_form");
        that.status = $("#modify_rangeland_cover_form  #status");
        that.stacktrace = $("#modify_rangeland_cover_form #stacktrace");
        //that.ws_client = new WSClient('modify_rangeland_cover_form', 'modify_rangeland_cover');
        that.rq_job_id = null;
        that.rq_job = $("#modify_rangeland_cover_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.checkbox = $('#checkbox_modify_rangeland_cover');
        that.checkbox_box_select = $('#checkbox_box_select_modify_rangeland_cover');
        that.textarea = $('#textarea_modify_rangeland_cover');

        that.input_bunchgrass = $('#input_bunchgrass_cover');
        that.input_forbs = $('#input_forbs_cover');
        that.input_sodgrass = $('#input_sodgrass_cover');
        that.input_shrub = $('#input_shrub_cover');

        that.input_basal = $('#input_basal_cover');
        that.input_rock = $('#input_rock_cover');
        that.input_litter = $('#input_litter_cover');
        that.input_cryptogams = $('#input_cryptogams_cover');

        that.data = null; // Leaflet geoJSON layer
        that.polys = null; // Leaflet geoJSON layer
        that.selected = null;

        that.style = {
            color: "white",
            opacity: 1,
            weight: 1,
            fillColor: "#FFEDA0",
            fillOpacity: 0.0
        };

        that.selectedstyle = {
            color: "red",
            opacity: 1,
            weight: 2,
            fillOpacity: 0.0
        };

        that.mouseoverstyle = {
            weight: 2,
            color: '#666',
            dashArray: '',
            fillOpacity: 0.0
        };

        that.ll0 = null;
        that.selectionRect = null;

        that.boxSelectionModeMouseDown = function (evt) {
            var self = instance;
            self.ll0 = evt.latlng;
        };

        that.boxSelectionModeMouseMove = function (evt) {
            var self = instance;
            var map = Map.getInstance();

            if (self.ll0 === null) {
                if (self.selectedRect !== null) {
                    map.removeLayer(that.selectionRect);
                    self.selectionRect = null;
                }
                return;
            }

            var bounds = L.latLngBounds(self.ll0, evt.latlng);

            if (self.selectionRect === null) {
                self.selectionRect = L.rectangle(bounds, { color: 'blue', weight: 1 }).addTo(map);
            } else {
                self.selectionRect.setLatLngs([bounds.getSouthWest(), bounds.getSouthEast(),
                bounds.getNorthEast(), bounds.getNorthWest()]);
                self.selectionRect.redraw();
            }

        };

        that.find_layer_id = function (topaz_id) {
            var self = instance;

            for (var id in self.polys._layers) {
                var topaz_id2 = self.polys._layers[id].feature.properties.TopazID;

                if (topaz_id === topaz_id2) {
                    return id;
                }
            }
            return undefined;
        };

        that.loadCovers = function () {
            var self = instance;
            var topaz_ids = instance.textarea.val().split(',');

            $.post({
                url: "query/rangeland_cover/current_cover_summary/",
                data: JSON.stringify({ topaz_ids: topaz_ids }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(covers) {

                    that.input_bunchgrass.val(covers['bunchgrass']);
                    that.input_forbs.val(covers['forbs']);
                    that.input_sodgrass.val(covers['sodgrass']);
                    that.input_shrub.val(covers['shrub']);
                    that.input_basal.val(covers['basal']);
                    that.input_rock.val(covers['rock']);
                    that.input_litter.val(covers['litter']);
                    that.input_cryptogams.val(covers['cryptogams']);

                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.boxSelectionModeMouseUp = function (evt) {
            var self = instance;

            var map = Map.getInstance();

            var llend = evt.latlng;

            if (self.ll0.lat === llend.lat && self.ll0.lng === llend.lng) {
                that.ll0 = null;
                map.removeLayer(that.selectionRect);
                that.selectionRect = null;
                return;
            }

            var bounds = L.latLngBounds(self.ll0, llend);

            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [sw.lng, sw.lat, ne.lng, ne.lat];


            $.post({
                url: "tasks/sub_intersection/",
                data: JSON.stringify({ extent: extent }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(topaz_ids) {

                    for (var i = 0; i < topaz_ids.length; i++) {
                        var topaz_id = topaz_ids[i];
                        var id = self.find_layer_id(topaz_id);

                        if (id == undefined) {
                            continue;
                        }

                        var layer = self.polys._layers[id];

                        if (self.selected.has(topaz_id)) {
                            self.selected.delete(topaz_id);
                            layer.setStyle(self.style);
                        } else {
                            self.selected.add(topaz_id);
                            layer.setStyle(self.selectedstyle);
                        }
                    }

                    that.textarea.val(Array.from(self.selected).join());
                    that.loadCovers();

                    map.removeLayer(that.selectionRect);
                    that.selectionRect = null;
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            }).always(function () {
                that.ll0 = null;
            });
        };

        that.toggle = function () {
            var self = instance;

            if (self.checkbox.prop("checked") === true) {
                if (self.polys == null) {
                    self.showModifyMap();
                }
                if (self.selected == null) {
                    self.selected = new Set();
                }
            } else {
                if (self.checkbox_box_select.prop("checked") === false) {
                    self.selected = new Set();
                    self.hideModifyMap();
                }
            }
        };

        that.showModifyMap = function () {
            var self = instance;

            var map = Map.getInstance();
            map.boxZoom.disable();

            map.on('mousedown', self.boxSelectionModeMouseDown);
            map.on('mousemove', self.boxSelectionModeMouseMove);
            map.on('mouseup', self.boxSelectionModeMouseUp);

            self.data = null;
            $.get({
                url: "resources/subcatchments.json",
                cache: false,
                success: self.onShowSuccess,
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.hideModifyMap = function () {
            var self = instance;
            var map = Map.getInstance();

            map.boxZoom.enable();
            map.off('mousedown', self.boxSelectionModeMouseDown);
            map.off('mousemove', self.boxSelectionModeMouseMove);
            map.off('mouseup', self.boxSelectionModeMouseUp);
            map.removeLayer(self.polys);

            self.data = null;
            self.polys = null;
            self.ll0 = null;
        };

        that.onShowSuccess = function (response) {
            var self = instance;
            var map = Map.getInstance();
            self.data = response;
            self.polys = L.geoJSON(self.data.features, {
                style: self.style,
                onEachFeature: self.onEachFeature
            });
            self.polys.addTo(map);
        };

        that.onEachFeature = function (feature, layer) {
            var self = instance;
            var map = Map.getInstance();

            layer.on({
                mouseover: function mouseover(e) {
                    var layer = e.target;

                    layer.setStyle(self.mouseoverstyle);

                    if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                        layer.bringToFront();
                    }
                },
                mouseout: function mouseout(e) {
                    var topaz_id = e.target.feature.properties.TopazID;
                    if (self.selected.has(topaz_id)) {
                        layer.setStyle(self.selectedstyle);
                    } else {
                        layer.setStyle(self.style);
                    }
                },
                click: function click(e) {
                    var layer = e.target;
                    var topaz_id = e.target.feature.properties.TopazID;

                    if (self.selected.has(topaz_id)) {
                        self.selected.delete(topaz_id);
                        layer.setStyle(self.style);
                    } else {
                        self.selected.add(topaz_id);
                        layer.setStyle(self.selectedstyle);
                    }

                    that.textarea.val(Array.from(self.selected).join());
                    that.loadCovers();
                }
            });
        };

        that.modify = function () {
            var self = instance;
            var task_msg = "Modifying rangeland_cover";
            self.status.html(task_msg + "...");
            self.hideStacktrace();

            var topaz_ids = self.textarea.val().split(',');
            $.post({
                url: "tasks/modify_rangeland_cover/",
                data: JSON.stringify({
                    topaz_ids: topaz_ids,
                    covers: {
                        bunchgrass: self.input_bunchgrass.val(),
                        forbs: self.input_forbs.val(),
                        sodgrass: self.input_sodgrass.val(),
                        shrub: self.input_shrub.val(),
                        basal: self.input_basal.val(),
                        rock: self.input_rock.val(),
                        litter: self.input_litter.val(),
                        cryptogams: self.input_cryptogams.val()
                    }
                }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.textarea.val("");
                        self.loadCovers();
                        self.checkbox.prop("checked", false);
                        self.hideModifyMap();
                        self.status.html(task_msg + "... Success");

                        self.form.trigger("RANGELAND_COVER_MODIFY_TASK_COMPLETED");
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

var LanduseModify = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#modify_landuse_form");
        that.status = $("#modify_landuse_form  #status");
        that.stacktrace = $("#modify_landuse_form #stacktrace");
        //that.ws_client = new WSClient('modify_landuse_form', 'modify_landuse');
        that.rq_job_id = null;
        that.rq_job = $("#modify_landuse_form #rq_job");
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.checkbox = $('#checkbox_modify_landuse');
        that.textarea = $('#textarea_modify_landuse');
        that.selection = $('#selection_modify_landuse');
        that.data = null; // Leaflet geoJSON layer
        that.polys = null; // Leaflet geoJSON layer
        that.selected = null;

        that.style = {
            color: "white",
            opacity: 1,
            weight: 1,
            fillColor: "#FFEDA0",
            fillOpacity: 0.0
        };

        that.selectedstyle = {
            color: "red",
            opacity: 1,
            weight: 2,
            fillOpacity: 0.0
        };

        that.mouseoverstyle = {
            weight: 2,
            color: '#666',
            dashArray: '',
            fillOpacity: 0.0
        };

        that.ll0 = null;
        that.selectionRect = null;

        that.boxSelectionModeMouseDown = function (evt) {
            var self = instance;
            self.ll0 = evt.latlng;
        };

        that.boxSelectionModeMouseMove = function (evt) {
            var self = instance;
            var map = Map.getInstance();

            if (self.ll0 === null) {
                if (self.selectedRect !== null) {
                    map.removeLayer(that.selectionRect);
                    self.selectionRect = null;
                }
                return;
            }

            var bounds = L.latLngBounds(self.ll0, evt.latlng);

            if (self.selectionRect === null) {
                self.selectionRect = L.rectangle(bounds, { color: 'blue', weight: 1 }).addTo(map);
            } else {
                self.selectionRect.setLatLngs([bounds.getSouthWest(), bounds.getSouthEast(),
                bounds.getNorthEast(), bounds.getNorthWest()]);
                self.selectionRect.redraw();
            }

        };

        that.find_layer_id = function (topaz_id) {
            var self = instance;

            for (var id in self.polys._layers) {
                var topaz_id2 = self.polys._layers[id].feature.properties.TopazID;

                if (topaz_id === topaz_id2) {
                    return id;
                }
            }
            return undefined;
        }

        that.boxSelectionModeMouseUp = function (evt) {
            var self = instance;

            var map = Map.getInstance();

            var llend = evt.latlng;

            if (self.ll0.lat === llend.lat && self.ll0.lng === llend.lng) {
                that.ll0 = null;
                map.removeLayer(that.selectionRect);
                that.selectionRect = null;
                return;
            }

            var bounds = L.latLngBounds(self.ll0, llend);

            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [sw.lng, sw.lat, ne.lng, ne.lat];

            $.post({
                url: "tasks/sub_intersection/",
                data: JSON.stringify({ extent: extent }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(topaz_ids) {

                    for (var i = 0; i < topaz_ids.length; i++) {
                        var topaz_id = topaz_ids[i];
                        var id = self.find_layer_id(topaz_id);

                        if (id == undefined) {
                            continue;
                        }

                        var layer = self.polys._layers[id];

                        if (self.selected.has(topaz_id)) {
                            self.selected.delete(topaz_id);
                            layer.setStyle(self.style);
                        } else {
                            self.selected.add(topaz_id);
                            layer.setStyle(self.selectedstyle);
                        }
                    }

                    that.textarea.val(Array.from(self.selected).join());

                    map.removeLayer(that.selectionRect);
                    that.selectionRect = null;

                },
                error: function error(jqXHR) {
                    console.log(jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    console.log(error);
                }
            }).always(function () {
                that.ll0 = null;
            });
        };

        that.toggle = function () {
            var self = instance;

            if (self.checkbox.prop("checked") === true) {
                if (self.polys == null) {
                    self.showModifyMap();
                }
                if (self.selected == null) {
                    self.selected = new Set();
                }
            } else {
                self.hideModifyMap();
            }
        };

        that.showModifyMap = function () {
            var self = instance;

            var map = Map.getInstance();
            map.boxZoom.disable();
            //map.dragging.disable();

            map.on('mousedown', self.boxSelectionModeMouseDown);
            map.on('mousemove', self.boxSelectionModeMouseMove);
            map.on('mouseup', self.boxSelectionModeMouseUp);

            self.data = null;
            $.get({
                url: "resources/subcatchments.json",
                cache: false,
                success: self.onShowSuccess,
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.hideModifyMap = function () {
            var self = instance;
            var map = Map.getInstance();

            map.boxZoom.enable();
            //map.dragging.enable();
            map.off('mousedown', self.boxSelectionModeMouseDown);
            map.off('mousemove', self.boxSelectionModeMouseMove);
            map.off('mouseup', self.boxSelectionModeMouseUp);
            map.removeLayer(self.polys);

            self.data = null;
            self.polys = null;
            self.ll0 = null;
        };

        that.onShowSuccess = function (response) {
            var self = instance;
            var map = Map.getInstance();
            self.data = response;
            self.polys = L.geoJSON(self.data.features, {
                style: self.style,
                onEachFeature: self.onEachFeature
            });
            self.polys.addTo(map);
        };

        that.onEachFeature = function (feature, layer) {
            var self = instance;
            var map = Map.getInstance();

            layer.on({
                mouseover: function mouseover(e) {
                    var layer = e.target;

                    layer.setStyle(self.mouseoverstyle);

                    if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                        layer.bringToFront();
                    }
                },
                mouseout: function mouseout(e) {
                    var topaz_id = e.target.feature.properties.TopazID;
                    if (self.selected.has(topaz_id)) {
                        layer.setStyle(self.selectedstyle);
                    } else {
                        layer.setStyle(self.style);
                    }
                },
                click: function click(e) {
                    var layer = e.target;
                    var topaz_id = e.target.feature.properties.TopazID;

                    if (self.selected.has(topaz_id)) {
                        self.selected.delete(topaz_id);
                        layer.setStyle(self.style);
                    } else {
                        self.selected.add(topaz_id);
                        layer.setStyle(self.selectedstyle);
                    }

                    that.textarea.val(Array.from(self.selected).join());
                }
            });
        };

        that.modify = function () {
            var self = instance;
            var task_msg = "Modifying landuse";
            self.status.html(task_msg + "...");
            self.hideStacktrace();

            $.post({
                url: "tasks/modify_landuse/",
                data: {
                    topaz_ids: self.textarea.val(),
                    landuse: self.selection.val()
                },
                success: function success(response) {
                    if (response.Success === true) {
                        self.textarea.val("");
                        self.checkbox.prop("checked", false);
                        self.hideModifyMap();
                        self.status.html(task_msg + "... Success");

                        self.form.trigger("LANDCOVER_MODIFY_TASK_COMPLETED");
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

/* ----------------------------------------------------------------------------
 * Soil
 * ----------------------------------------------------------------------------
 */
var Soil = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#soil_form");
        that.info = $("#soil_form #info");
        that.status = $("#soil_form  #status");
        that.stacktrace = $("#soil_form #stacktrace");
        that.ws_client = new WSClient('soil_form', 'soils');
        that.rq_job_id = null;
        that.rq_job = $("#soil_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building soil";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/build_soils",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_soils_rq job submitted: ${response.job_id}`);
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
        };

        that.report = function () {
            var self = instance;
            $.get({
                url: "report/soils/",
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

        that.restore = function (soil_mode) {
            var self = instance;
            $("#soil_mode" + soil_mode).prop("checked", true);

            self.showHideControls(soil_mode);
        };

        that.set_ksflag = function (state) {
            var self = instance;
            var task_msg = "Setting ksflag (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_soils_ksflag/",
                data: JSON.stringify({ ksflag: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

        };

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='soil_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var soil_single_selection = $("#soil_single_selection").val();
            var soil_single_dbselection = $("#soil_single_dbselection").val();

            var task_msg = "Setting Mode to " + mode;

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync soil with nodb
            $.post({
                url: "tasks/set_soil_mode/",
                data: {
                    "mode": mode,
                    "soil_single_selection": soil_single_selection,
                    "soil_single_dbselection": soil_single_dbselection
                },
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
            self.showHideControls(mode);
        };

        that.showHideControls = function (mode) {
            // show the appropriate controls
            if (mode === -1) {
                // neither
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 0) {
                // gridded
                $("#soil_mode0_controls").show();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 1) {
                // single
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").show();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 2) {
                // singledb
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").show();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 3) {
                // RRED Unburned
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").show();
                $("#soil_mode4_controls").hide();
            } else if (mode === 4) {
                // RRED Burned
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").show();
            } else {
                throw "ValueError: Landuse unknown mode";
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

/* ----------------------------------------------------------------------------
 * Climate
 * ----------------------------------------------------------------------------
 */
var Climate = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#climate_form");
        that.info = $("#climate_form #info");
        that.status = $("#climate_form  #status");
        that.stacktrace = $("#climate_form #stacktrace");
        that.ws_client = new WSClient('climate_form', 'climate');
        that.rq_job_id = null;
        that.rq_job = $("#climate_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.stationselection = $("#climate_station_selection");

        that.setBuildMode = function (mode) {
            var self = instance;
            self.mode = parseInt(mode, 10);
            if (self.mode === 0) {
                $("#climate_cligen").show();
                $("#climate_userdefined").hide();
                //self.setStationMode(-1);
            } else {
                $("#climate_cligen").hide();
                $("#climate_userdefined").show();
                self.setStationMode(4);
            }
        };

        that.setStationMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climatestation_mode']:checked").val();
            }

            var task_msg = "Setting Station Mode to " + mode;

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climatestation_mode/",
                data: { "mode": mode },
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("CLIMATE_SETSTATIONMODE_TASK_COMPLETED");
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

        that.upload_cli = function () {
            var self = instance;

            var task_msg = "Uploading cli";

            self.info.text("");
            self.stacktrace.text("");

            var formData = new FormData($('#climate_form')[0]);

            $.post({
                url: "tasks/upload_cli/",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("CLIMATE_BUILD_TASK_COMPLETED");
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

        that.refreshStationSelection = function () {
            var self = instance;

            var mode = $("input[name='climatestation_mode']:checked").val();
            if (mode === undefined) {
                return;
            }
            mode = parseInt(mode, 10);

            var task_msg = "Fetching Stations " + mode;

            self.info.text("");
            self.stacktrace.text("");

            if (mode === 0) {
                // sync climate with nodb
                $.get({
                    url: "view/closest_stations/",
                    cache: false,
                    data: { "mode": mode },
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 1) {
                // sync climate with nodb
                $.get({
                    url: "view/heuristic_stations/",
                    data: { "mode": mode },
                    cache: false,
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 2) {
                // sync climate with nodb
                $.get({
                    url: "view/eu_heuristic_stations/",
                    data: { "mode": mode },
                    cache: false,
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 3) {
                // sync climate with nodb
                $.get({
                    url: "view/au_heuristic_stations/",
                    data: { "mode": mode },
                    cache: false,
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 4) {
                pass();
            } else if (mode === -1) {
                pass();
            } else {
                throw "Unknown mode for stationselection";
            }
        };

        that.setStation = function () {
            var self = instance;

            var station = $("#climate_station_selection").val();

            var task_msg = "Setting station " + station;

            self.info.text("");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_climatestation/",
                data: { "station": station },
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
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

        that.viewStationMonthlies = function () {
            var self = instance;
            var project = Project.getInstance();
            $.get({
                url: "view/climate_monthlies/",
                cache: false,
                success: function success(response) {
                    $("#climate_monthlies").html(response);
                    project.set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building climate";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/build_climate",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_climate job submitted: ${response.job_id}`);
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

        };

        that.report = function () {
            var self = instance;
            var project = Project.getInstance();
            $.get({
                url: "report/climate/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    project.set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };


        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climate_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var climate_single_selection = $("#climate_single_selection").val();

            var task_msg = "Setting Mode to " + mode + " (" + climate_single_selection + ")";

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climate_mode/",
                data: {
                    "mode": mode,
                    "climate_single_selection": climate_single_selection
                },
                success: function success(response) {
                    if (response.Success === true) {
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
            self.showHideControls(mode);
        };

        that.showHideControls = function (mode) {
            if (mode === undefined) {
                mode = -1;
            }
            // show the appropriate controls
            if (mode === -1) {
                // none selected
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").hide();
            } else if (mode === 0) {
                // vanilla
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").show();
                $("#climate_mode0_controls").show();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if ((mode === 2) || (mode === 11)) {
                // observed daymet or gridmet
                $("#climate_spatialmode2").prop("disabled", false);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").show();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 3) {
                // future
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").show();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 4) {
                // single storm
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").show();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 14) {
                // single storm
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").show();
                $("#btn_build_climate_container").show();
            } else if (mode === 5) {
                // prism
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").show();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 6) {
                // observed database
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").show();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 7) {
                // future database
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").show();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 8) {
                // EOBS (EU)
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").show();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 9) {
                // observed PRISM
                $("#climate_spatialmode2").prop("disabled", false);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").show();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 10) {
                // AGDC (AU)
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").show();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 13) {
                // NEXRAD
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").show();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").show();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            }
            //              else {
            //                throw "ValueError: unknown mode";
            //            }
        };

        that.setSpatialMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climate_spatialmode']:checked").val();
            }
            var task_msg = "Setting SpatialMode to " + mode;

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climate_spatialmode/",
                data: { "spatialmode": mode },
                success: function success(response) {
                    if (response.Success === true) {
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

        that.set_use_gridmet_wind_when_applicable = function (state) {
            var self = instance;
            var task_msg = "Setting " + routine + " (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_use_gridmet_wind_when_applicable/",
                data: JSON.stringify({ state: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
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

/* ----------------------------------------------------------------------------
 * Wepp
 * ----------------------------------------------------------------------------
 */
var Wepp = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#wepp_form");
        that.info = $("#wepp_form #info");
        that.status = $("#wepp_form  #status");
        that.stacktrace = $("#wepp_form #stacktrace");
        that.ws_client = new WSClient('wepp_form', 'wepp');
        that.rq_job_id = null;
        that.rq_job = $("#wepp_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.surf_runoff = $("#wepp_form #surf_runoff");
        that.lateral_flow = $("#wepp_form #lateral_flow");
        that.baseflow = $("#wepp_form #baseflow");
        that.sediment = $("#wepp_form #sediment");
        that.channel_critical_shear = $("#wepp_form #channel_critical_shear");

        that.addChannelCriticalShear = function (x) {
            var self = instance;
            self.channel_critical_shear.append(new Option('User Defined: CS = ' + x, x, true, true));
        };


        that.updatePhosphorus = function () {
            var self = instance;

            $.get({
                url: "query/wepp/phosphorus_opts/",
                cache: false,
                success: function success(response) {
                    if (response.surf_runoff !== null)
                        self.surf_runoff.val(response.surf_runoff.toFixed(4));

                    if (response.lateral_flow !== null)
                        self.lateral_flow.val(response.lateral_flow.toFixed(4));

                    if (response.baseflow !== null)
                        self.baseflow.val(response.baseflow.toFixed(4));

                    if (response.sediment !== null)
                        self.sediment.val(response.sediment.toFixed(0));
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.set_run_wepp_routine = function (routine, state) {
            var self = instance;
            var task_msg = "Setting " + routine + " (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_run_wepp_routine/",
                data: JSON.stringify({ routine: routine, state: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.set_wepp_bin = function (wepp_bin) {
            var self = instance;
            var task_msg = "Setting wepp_bin (" + wepp_bin + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_wepp_bin/",
                data: JSON.stringify({ wepp_bin: wepp_bin }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.set_flowpaths = function (state) {
            var self = instance;
            var task_msg = "Setting run_flowpaths (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_run_flowpaths/",
                data: JSON.stringify({ run_flowpaths: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

        };

        that.run = function () {
            var self = instance;
            var task_msg = "Submitting wepp run";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var data = self.form.serialize();

            $.post({
                url: "rq/api/run_wepp",
                data: data,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_wepp_rq job submitted: ${response.job_id}`);
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
        };

        that.report = function () {
            var self = instance;
            var project = Project.getInstance();
            var task_msg = "Fetching Summary";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "report/wepp/results/",
                cache: false,
                success: function success(response) {
                    $('#wepp-results').html(response);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "report/wepp/run_summary/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.status.html(task_msg + "... Success");
                    project.set_preferred_units();
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


/* ----------------------------------------------------------------------------
 * Observed
 * ----------------------------------------------------------------------------
 */
var Observed = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#observed_form");
        that.textarea = $("#observed_form #observed_text");
        that.info = $("#observed_form #info");
        that.status = $("#observed_form  #status");
        that.stacktrace = $("#observed_form #stacktrace");
        that.ws_client = new WSClient('observed_form', 'observed');
        that.rq_job_id = null;
        that.rq_job = $("#observed_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.hideControl = function () {
            var self = instance;
            self.form.hide();
        };

        that.showControl = function () {
            var self = instance;
            self.form.show();
        };

        that.onWeppRunCompleted = function () {
            var self = instance;

            $.get({
                url: "query/climate_has_observed/",
                success: function success(response) {
                    if (response === true) {
                        self.showControl();
                    } else {
                        self.hideControl();
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

        that.run_model_fit = function () {
            var self = instance;
            var textdata = self.textarea.val();

            var task_msg = "Running observed model fit";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/run_model_fit/",
                data: JSON.stringify({ data: textdata }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... done.");
                        self.report();
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

        that.report = function () {
            var self = instance;
            self.info.html("<a href='report/observed/' target='_blank'>View Model Fit Results</a>");
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


/* ----------------------------------------------------------------------------
 * DebrisFlow
 * ----------------------------------------------------------------------------
 */
var DebrisFlow = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#debris_flow_form");
        that.info = $("#debris_flow_form #info");
        that.status = $("#debris_flow_form  #status");
        that.stacktrace = $("#debris_flow_form #stacktrace");
        that.ws_client = new WSClient('debris_flow_form', 'debris_flow');
        that.rq_job_id = null;
        that.rq_job = $("#debris_flow_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.run_model = function () {
            var self = instance;

            var task_msg = "Running debris_flow model fit";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/run_debris_flow",
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_debris_flow_rq job submitted: ${response.job_id}`);
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
        };

        that.report = function () {
            var self = instance;
            self.info.html("<a href='report/debris_flow/' target='_blank'>View Debris Flow Model Results</a>");
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



/* ----------------------------------------------------------------------------
 * Ash
 * ----------------------------------------------------------------------------
 */
var Ash = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#ash_form");
        that.info = $("#ash_form #info");
        that.status = $("#ash_form  #status");
        that.stacktrace = $("#ash_form #stacktrace");
        that.ws_client = new WSClient('ash_form', 'ash');
        that.rq_job_id = null;
        that.rq_job = $("#ash_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.run_model = function () {
            var self = instance;

            var task_msg = "Running ash model";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var formData = new FormData($('#ash_form')[0]);

            $.post({
                url: "rq/api/run_ash",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_ash job submitted: ${response.job_id}`);
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
        };

        that.setAshDepthMode = function (mode) {
            var self = instance;

            if (mode === undefined) {
                mode = $("input[name='ash_depth_mode']:checked").val();
            }

            self.ash_depth_mode = parseInt(mode, 10);
            self.showHideControls();
        }

        that.set_wind_transport = function (state) {
            var self = instance;
            var task_msg = "Setting wind_transport(" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_ash_wind_transport/",
                data: JSON.stringify({ run_wind_transport: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

        };

        that.showHideControls = function () {
            var self = instance;

            if (self.ash_depth_mode === 1) {
                $("#ash_depth_mode0_controls").hide();
                $("#ash_depth_mode1_controls").show();
                $("#ash_depth_mode2_controls").hide();
            }
            else if (self.ash_depth_mode === 2) {
                $("#ash_depth_mode0_controls").hide();
                $("#ash_depth_mode1_controls").hide();
                $("#ash_depth_mode2_controls").show();
            }
            else {
                $("#ash_depth_mode0_controls").show();
                $("#ash_depth_mode1_controls").hide();
                $("#ash_depth_mode2_controls").hide();
            }
        }

        that.report = function () {
            var self = instance;
            var project = Project.getInstance();
            var task_msg = "Fetching Summary";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "report/run_ash/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.status.html(task_msg + "... Success");
                    project.set_preferred_units();
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


/* ----------------------------------------------------------------------------
 * Rhem
 * ----------------------------------------------------------------------------
 */
var Rhem = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#rhem_form");
        that.info = $("#rhem_form #info");
        that.status = $("#rhem_form  #status");
        that.stacktrace = $("#rhem_form #stacktrace");
        that.ws_client = new WSClient('rhem_form', 'rhem');
        that.rq_job_id = null;
        that.rq_job = $("#rhem_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.run = function () {
            var self = instance;
            var task_msg = "Submitting rhem run";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq_api/run_rhem/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_rhem_rq job submitted: ${response.job_id}`);
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
        };

        that.report = function () {
            var self = instance;
            var project = Project.getInstance();
            var task_msg = "Fetching Summary";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "report/rhem/results/",
                cache: false,
                success: function success(response) {
                    $('#rhem-results').html(response);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "report/rhem/run_summary/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.status.html(task_msg + "... Success");
                    project.set_preferred_units();
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


/* ----------------------------------------------------------------------------
 * Omni
 * ----------------------------------------------------------------------------
 */
var Omni = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#omni_form");
        that.info = $("#omni_form #info");
        that.status = $("#omni_form  #status");
        that.stacktrace = $("#omni_form #stacktrace");
        that.ws_client = new WSClient('omni_form', 'omni');
        that.rq_job_id = null;
        that.rq_job = $("#omni_form #rq_job");

        that.serializeScenarios = function () {
            const formData = new FormData();
            const scenarioItems = document.querySelectorAll('#omni_form #scenario-container .scenario-item');
            const scenariosList = [];

            scenarioItems.forEach((item, index) => {
                const scenarioSelect = item.querySelector('select[name="scenario"]');
                if (!scenarioSelect || !scenarioSelect.value) return;

                const scenario = {
                    type: scenarioSelect.value
                };

                const controls = item.querySelectorAll('.scenario-controls [name]');
                controls.forEach(control => {
                    if (control.type === 'file' && control.files.length > 0) {
                        formData.append(`scenarios[${index}][${control.name}]`, control.files[0]);
                        scenario[control.name] = control.files[0].name;
                    } else if (control.value) {
                        scenario[control.name] = control.value;
                    }
                });

                scenariosList.push(scenario);
            });

            formData.append('scenarios', JSON.stringify(scenariosList));
            return formData;
        };


        that.run_omni_scenarios = function () {
            var self = instance;
            var task_msg = "Submitting omni run";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            const data = self.serializeScenarios();
            console.log('Serialized FormData:');
            for (let [key, value] of data.entries()) {
                console.log(`${key}: ${value instanceof File ? value.name : value}`);
            }

            $.post({
                url: "rq/api/run_omni",
                data: data,
                contentType: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_omni_rq job submitted: ${response.job_id}`);
                        self.set_rq_job_id(self, response.job_id);
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON || { error: "Unknown error occurred" });
                }
            });
        };

        that.load_scenarios_from_backend = function () {
            fetch("api/omni/get_scenarios")
                .then(response => {
                    if (!response.ok) throw new Error("Failed to fetch scenarios");
                    return response.json();
                })
                .then(data => {
                    if (!Array.isArray(data)) throw new Error("Invalid scenario format");

                    data.forEach(scenario => {
                        addScenario();
                        const container = document.querySelectorAll('#scenario-container .scenario-item');
                        const latestItem = container[container.length - 1];
                        const scenarioSelect = latestItem.querySelector('select[name="scenario"]');
                        scenarioSelect.value = scenario.type;

                        // Trigger controls to be rendered
                        updateControls(scenarioSelect);

                        // Populate the controls with values
                        Object.entries(scenario).forEach(([key, value]) => {
                            if (key === "type") return;
                            const input = latestItem.querySelector(`[name="${key}"]`);
                            if (input) {
                                input.value = value;
                            }
                        });
                    });
                })
                .catch(err => {
                    console.error("Error loading scenarios:", err);
                });
        };

        that.report_scenarios = function () {
            var self = instance;
            self.status.html("Omni Scenarios Completed")
        };



        that.report_scenarios = function () {
            var self = instance;

            $.get({
                url: "report/omni_scenarios/",
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


/* ----------------------------------------------------------------------------
 * DSS Export
 * ----------------------------------------------------------------------------
 */
var DssExport = function () {
    var instance;

    function createInstance() {
        var that = controlBase();

        that.form = $("#dss_export_form");
        that.info = $("#dss_export_form #info");
        that.status = $("#dss_export_form  #status");
        that.stacktrace = $("#dss_export_form #stacktrace");
        that.ws_client = new WSClient('dss_export_form', 'dss_export');
        that.rq_job_id = null;
        that.rq_job = $("#dss_export_form #rq_job");

        that.show = function () {
            that.form.show();
            $('a[href="#partitioned-dss-export-for-hec"]').parent().show()
        };

        that.hide = function () {
            that.form.hide();
            $('a[href="#partitioned-dss-export-for-hec"]').parent().hide()
        };

        that.setMode = function (mode) {
            var self = instance;

            // verify mode is 1 or 2
            if (mode !== 1 && mode !== 2) {
                throw "ValueError: unknown mode";
            }

            if (mode === 1) {
                $("#dss_export_mode1_controls").show();
                $("#dss_export_mode2_controls").hide();
            }
            else if (mode === 2) {
                $("#dss_export_mode1_controls").hide();
                $("#dss_export_mode2_controls").show();
            }

        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.export = function () {
            var self = instance;

            var task_msg = "Exporting to DSS";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            console.log(self.form.serialize());

            $.post({
                url: "rq/api/post_dss_export_rq",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`post_dss_export_rq job submitted: ${response.job_id}`);
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
        };
        that.report = function () {
            var self = instance;
            self.info.html("<a href='browse/export/dss.zip' target='_blank'>Download DSS Export Results (.zip)</a>");
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

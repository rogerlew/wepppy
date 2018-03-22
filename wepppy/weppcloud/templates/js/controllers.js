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
                self.stacktrace.append("<pre><small class=\"text-muted\">" + response.StackTrace + "</small></pre>");
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
        }
    };
}

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
                url: "../tasks/setname/",
                data: $("#setname_form").serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        $("#input_name").val(name);
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
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
                url: "../tasks/set_unit_preferences/",
                data: unit_preferences,
                success: function success(response) {
                    if (response.Success === true) {} else {}
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

        that.adduser = function () {
            var self = instance;
            $.post({
                url: "../tasks/adduser/",
                data: $("#team_form").serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("TEAM_ADDUSER_TASK_COMPLETED");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.removeuser = function (user_id) {
            var self = instance;
            $.post({
                url: "../tasks/removeuser/",
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
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.report = function () {
            var self = instance;

            $.get({
                url: "../report/users/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
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
        var that = L.map("mapid");

        that.scrollWheelZoom.disable();

        //
        // Elevation feedback on mouseover
        //
        that.isFetchingElevation = false;
        that.mouseelev = $("#mouseelev");
        that.drilldown = $("#drilldown");

        that.fetchElevation = function (ev) {
            var self = instance;

            $.post({
                url: "https://wepp1.nkn.uidaho.edu/webservices/elevationquery/",
                data: JSON.stringify({ lat: ev.latlng.lat, lng: ev.latlng.lng }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                cache: false,
                success: function success(response) {
                    var elev = response.Elevation.toFixed(1);
                    self.mouseelev.show().text("| Elevation: " + elev + " m");
                    self.isFetchingElevation = false;
                },
                fail: function fail(error) {
                    console.log(error);
                    that.isFetchingElevation = false;
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
        that.googleTerrain = L.tileLayer("https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", {
            maxZoom: 20,
            subdomains: ["mt0", "mt1", "mt2", "mt3"]
        });

        that.googleSat = L.tileLayer("https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {
            maxZoom: 20,
            subdomains: ["mt0", "mt1", "mt2", "mt3"]
        });

        that.nlcd = L.tileLayer.wms("https://raster.nationalmap.gov/arcgis/services/LandCover/USGS_EROS_LandCover_NLCD/MapServer/WMSServer?", {
            layers: "1",
            format: "image/png",
            transparent: true
        });

        that.baseMaps = {
            "Satellite": that.googleSat,
            "Terrain": that.googleTerrain,
            "2011 NLCD": that.nlcd
        };
        that.overlayMaps = {};

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
            $("#mapstatus").text("Center: " + lng + ", " + lat + " | Zoom: " + zoom);
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
                fail: function fail(error) {
                    console.log(error);
                }
            });
        };

        that.chnQuery = function (topazID) {
            var self = instance;
            var query_url = "../report/chn_summary/" + topazID + "/";
            self.hillQuery(query_url);
        };

        that.subQuery = function (topazID) {
            var self = instance;
            var query_url = "../report/sub_summary/" + topazID + "/";
            self.hillQuery(query_url);
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
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };
        that.baer_map = null;

        that.upload_sbs = function () {
            var self = instance;

            var task_msg = "Uploading SBS";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            var formData = new FormData($('#sbs_upload_form')[0]);

            $.post({
                url: "../tasks/upload_sbs/",
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
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.remove_sbs = function () {
            var self = instance;
            var map = Map.getInstance();

            if (self.baer_map !== null) {
                map.ctrls.removeLayer(self.baer_map);
                map.removeLayer(self.baer_map);
                self.baer_map = null;
            }
        };

        that.load_modify_class = function () {
            var self = instance;

            $.get({
                url: "../view/modify_burn_class/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.modify_classes = function () {

            var self = instance;
            var data = [parseInt($('#baer_brk0').val(), 10), parseInt($('#baer_brk1').val(), 10), parseInt($('#baer_brk2').val(), 10), parseInt($('#baer_brk3').val(), 10)];

            var task_msg = "Modifying Class Breaks";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "../tasks/modify_burn_class/",
                data: JSON.stringify({ classes: data }),
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
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.show_sbs = function () {
            var self = instance;
            var map = Map.getInstance();

            self.remove_sbs();

            var task_msg = "Querying SBS map";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "../query/baer_wgs_map/",
                cache: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");

                        var bounds = response.Content.bounds;
                        var imgurl = response.Content.imgurl + "?v=" + Date.now();
                        console.log(bounds);

                        self.baer_map = L.imageOverlay(imgurl, bounds, { opacity: 0.7 });
                        self.baer_map.addTo(map);
                        map.ctrls.addOverlay(self.baer_map, "Burn Severity Map");

                        map.flyToBounds(self.baer_map._bounds);
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
        that.labels = L.layerGroup();

        that.style = function () {
            return {
                color: "#0010FF",
                opacity: 1,
                weight: 1,
                fillColor: "#0010FF",
                fillOpacity: 0.9
            };
        };

        that.labelStyle = "text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF;";

        that.form = $("#build_channels_form");
        that.info = $("#build_channels_form #info");
        that.status = $("#build_channels_form  #status");
        that.stacktrace = $("#build_channels_form #stacktrace");
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.remove = function () {
            var self = instance;
            var map = Map.getInstance();

            if (self.polys !== null) {
                map.ctrls.removeLayer(self.polys);
                map.removeLayer(self.polys);
            }

            if (self.labels !== null) {
                map.ctrls.removeLayer(self.labels);
                map.removeLayer(self.labels);
            }
        };

        that.has_dem = function (onSuccessCallback) {
            var self = instance;

            $.get({
                url: "../query/has_dem/",
                cache: false,
                success: onSuccessCallback,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.build_router = function () {
            var self = instance;
            self.has_dem(self.build_router_callback);
        };

        that.build_router_callback = function (has_dem_response) {
            var self = instance;

            if (has_dem_response === true) {
                self.build();
            } else if (has_dem_response === false) {
                self.fetch_dem();
            } else {
                self.stacktrace.text("has_dem state is unknown");
            }
        };

        that.fetch_dem = function () {
            var self = instance;

            self.remove();
            var task_msg = "Fetching DEM";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "../tasks/fetch_dem/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("FETCH_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.build = function () {
            var self = instance;

            self.remove();
            var task_msg = "Delineating channels";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "../tasks/build_channels/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("BUILD_CHANNELS_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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

            if (zoom >= self.zoom_min) {
                $("#btn_build_channels").prop("disabled", false);
                $("#hint_build_channels").text("");
            } else {
                $("#btn_build_channels").prop("disabled", true);
                $("#hint_build_channels").text("Area is too large, zoom must be \u2265 " + self.zoom_min.toString());
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
                url: "../query/topaz_pass/",
                cache: false,
                success: function success(response) {
                    response = parseInt(response, 10);
                    if ($.inArray(response, [0, 1, 2]) === -1) {
                        self.pushResponseStacktrace(self, { Error: "Error Determining TOPAZ Pass" });
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
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        // Topaz Pass 1
        // Shows the NETFUL.ARC built by TOPAZ
        that.show_1 = function () {
            var self = instance;

            self.remove();
            var task_msg = "Displaying Channel Map";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "../resources/netful.json",
                cache: false,
                success: function success(response) {
                    var map = Map.getInstance();
                    self.data = response;
                    self.polys = L.geoJSON(self.data.features, {
                        style: self.style,
                        onEachFeature: self.on1EachFeature
                    });
                    self.polys.addTo(map);
                    map.ctrls.addOverlay(self.polys, "Channels");

                    self.status.html(task_msg + "... Success");
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.on1EachFeature = function (feature, layer) {
            layer.on({
                click: function click(ev) {
                    var topaz_id = ev.target.feature.properties.TopazID;
                    //                    console.log(feature, topaz_id);
                }
            });
        };

        // Topaz Pass 2
        // Shows the channels from SUBWTA.ARC built by TOPAZ (channels end with '4')
        that.show_2 = function () {
            var self = instance;
            self.data = null;
            $.get({
                url: "../resources/channels.json",
                cache: false,
                success: self.on2Success,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.on2Success = function (response) {
            var self = instance;
            var map = Map.getInstance();
            self.topIds = [];
            self.labels = L.layerGroup();
            self.data = response;
            self.polys = L.geoJSON(self.data.features, {
                style: self.style,
                onEachFeature: self.on2EachFeature
            });
            self.polys.addTo(map);
            map.ctrls.addOverlay(self.polys, "Channels");

            self.labels.addTo(map);
            map.ctrls.addOverlay(self.labels, "Channel Labels");
        };

        that.on2EachFeature = function (feature, layer) {
            var self = instance;
            layer.on({
                zoomend: function zoomend() {
                    self.polys.setStyle(self.style);
                },
                click: function click(ev) {
                    var topaz_id = ev.target.feature.properties.TopazID;
                    var map = Map.getInstance();
                    map.chnQuery(topaz_id);
                }
            });

            // build labels
            var topId = feature.properties.TopazID;
            if ($.inArray(topId, self.topIds) === -1) {
                var center = polylabel(feature.geometry.coordinates, 1.0);
                center = [center[1], center[0]];
                var label = L.marker(center, {
                    icon: L.divIcon({
                        iconSize: null,
                        className: "label",
                        html: "<div style=\"" + self.labelStyle + "\">" + topId + "</div>"
                    })
                });
                self.topIds.push(topId);
                self.labels.addLayer(label);
            }
        };

        that.report = function () {
            var self = instance;

            $.get({
                url: "../report/channel/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
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
        that.form = $("#setoutlet_form");
        that.info = $("#setoutlet_form #info");
        that.status = $("#setoutlet_form  #status");
        that.stacktrace = $("#setoutlet_form #stacktrace");
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.outlet = null;
        that.outletMarker = L.marker();

        that.remove = function () {
            var self = instance;
            var map = Map.getInstance();

            map.removeLayer(self.outletMarker);
        };

        that.show = function () {
            var self = instance;

            self.remove();

            var task_msg = "Displaying Outlet...";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.get({
                url: "../query/outlet/",
                cache: false,
                success: function success(response) {
                    var map = Map.getInstance();

                    self.outletMarker.setLatLng([response.lat, response.lng]).addTo(map);
                    map.ctrls.addOverlay(self.outletMarker, "Outlet");
                    self.status.html(task_msg + "... Success");
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: "../report/outlet/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
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
                self.put(ev);
            }
        };

        that.put = function (ev) {
            var self = instance;
            var map = Map.getInstance();

            var task_msg = "Attempting to set outlet";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            self.popup.setLatLng(ev.latlng).setContent("finding nearest channel...").openOn(map);

            var lat = ev.latlng.lat;
            var lng = ev.latlng.lng;

            $.post({
                url: "../tasks/setoutlet/",
                data: { latitude: lat, longitude: lng },
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("SETOUTLET_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                $("#btn_setoutlet_cursor").text("Cancel");
                $(".leaflet-container").css("cursor", "crosshair");
                $("#hint_setoutlet_cursor").text("Click on the map to define outlet.");
            } else {
                $("#btn_setoutlet_cursor").text("Use Cursor");
                $(".leaflet-container").css("cursor", "");
                $("#hint_setoutlet_cursor").text("");
            }
        };

        that.setMode = function (mode) {
            var self = instance;
            self.mode = parseInt(mode, 10);
            if (self.mode === 0) {
                // Enter lng, lat
                $("#setoutlet_mode0_controls").show();
                $("#setoutlet_mode1_controls").hide();
            } else {
                // user cursor
                $("#setoutlet_mode0_controls").hide();
                $("#setoutlet_mode1_controls").show();
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
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.cmap = "default";
        that.defaultStyle = {
            "color": "#ff7800",
            "weight": 2,
            "opacity": 0.65,
            "fillColor": "#ff7800",
            "fillOpacity": 0.3
        };

        that.labelStyle = "text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF;";

        that.data = null; // JSON from Flask
        that.polys = null; // Leaflet geoJSON layer
        that.topIds = [];
        that.labels = L.layerGroup(); // collection of labels with topaz ids as keys

        //
        // View Methods
        //
        that.show = function () {
            var self = instance;
            self.data = null;
            $.get({
                url: "../resources/subcatchments.json",
                cache: false,
                success: self.onShowSuccess,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.onShowSuccess = function (response) {
            var self = instance;
            var map = Map.getInstance();
            self.topIds = [];
            self.labels = L.layerGroup();
            self.data = response;
            self.polys = L.geoJSON(self.data.features, {
                style: self.defaultStyle,
                onEachFeature: self.onEachFeature
            });
            self.polys.addTo(map);
            map.ctrls.addOverlay(self.polys, "Subcatchments");

            self.labels.addTo(map);
            map.ctrls.addOverlay(self.labels, "Subcatchment Labels");
        };

        that.onEachFeature = function (feature, layer) {
            var self = instance;
            var map = Map.getInstance();

            layer.on({
                click: function click(ev) {
                    var topaz_id = ev.target.feature.properties.TopazID;
                    var map = Map.getInstance();
                    map.subQuery(topaz_id);
                }
            });

            var topId = feature.properties.TopazID;
            if ($.inArray(topId, self.topIds) === -1) {
                var center = polylabel(feature.geometry.coordinates, 1.0);
                center = [center[1], center[0]];
                var label = L.marker(center, {
                    icon: L.divIcon({
                        iconSize: null,
                        className: "label",
                        html: "<div style=\"" + self.labelStyle + "\">" + topId + "</div>"
                    })
                });
                self.topIds.push(topId);
                self.labels.addLayer(label);
            }
        };

        that.enableColorMap = function (cmap_name) {
            if (cmap_name === "dom_lc") {
                $("#sub_cmap_radio_dom_lc").prop("disabled", false);
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
            } else if (cmap_name === "slp_asp") {
                self.cmapSlpAsp();
            } else if (cmap_name === "dom_lc") {
                self.cmapNLCD();
            } else if (cmap_name === "dom_soil") {
                self.cmapSoils();
            } else if (cmap_name === "sub_runoff") {
                self.cmapRunoff();
            } else if (cmap_name === "sub_loss") {
                self.cmapLoss();
            } else if (cmap_name === "sub_phosphorus") {
                self.cmapPhosphorus();
            } else {
                throw "Map.setSubcatchmentLayer received unexpected parameter: " + cmap_name;
            }
        };

        that.cmap = function () {
            var self = instance;

            self.polys.eachLayer(function (layer) {
                layer.setStyle(self.defaultStyle);
            });
        };

        that.cmapSlpAsp = function () {
            var self = instance;

            $.get({
                url: "../query/watershed/subcatchments/",
                cache: false,
                success: that.cmapCallback,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.cmapNLCD = function () {
            var self = instance;

            $.get({
                url: "../query/landuse/subcatchments/",
                cache: false,
                success: that.cmapCallback,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.cmapSoils = function () {
            var self = instance;

            $.get({
                url: "../query/soils/subcatchments/",
                cache: false,
                success: that.cmapCallback,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        //
        // Phosphorus
        //
        that.dataPhosphorus = null;
        that.rangePhosphorus = $('#wepp_sub_cmap_range_phosphorus');
        that.cmapperPhosphorus = createColormap({ colormap: 'viridis', nshades: 64 });

        that.cmapPhosphorus = function () {
            var self = instance;
            $.get({
                url: "../query/wepp/phosphorus/subcatchments/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataPhosphorus = data;
                    self.renderPhosphorus();
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderPhosphorus = function () {
            console.log('in renderPhosphorus');

            var self = instance;
            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataPhosphorus[topId].total_p);
                var r = parseFloat(self.rangePhosphorus.val());
                var c = self.cmapperPhosphorus.map(v / r);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end Phosphorus

        //
        // Runoff
        //
        that.dataRunoff = null;
        that.rangeRunoff = $('#wepp_sub_cmap_range_runoff');
        that.cmapperRunoff = createColormap({ colormap: 'summer', nshades: 64 });

        that.cmapRunoff = function () {
            var self = instance;
            $.get({
                url: "../query/wepp/runoff/subcatchments/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataRunoff = data;
                    self.renderRunoff();
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderRunoff = function () {
            console.log('in renderRunoff');

            var self = instance;
            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataRunoff[topId].runoff);
                var r = parseFloat(self.rangeRunoff.val());
                var c = self.cmapperRunoff.map(v / r);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end Runoff

        //
        // Loss
        //
        that.dataLoss = null;
        that.rangeLoss = $('#wepp_sub_cmap_range_loss');
        that.cmapperLoss = createColormap({ colormap: 'rainbow', nshades: 64 });

        that.cmapLoss = function () {
            var self = instance;
            $.get({
                url: "../query/wepp/loss/subcatchments/",
                cache: false,
                success: function success(data) {
                    if (data === null) {
                        throw "query returned null";
                    }
                    self.dataLoss = data;
                    self.renderLoss();
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.renderLoss = function () {
            console.log('in renderLoss');

            var self = instance;
            self.polys.eachLayer(function (layer) {
                var topId = layer.feature.properties.TopazID;
                var v = parseFloat(self.dataLoss[topId].loss);
                var r = parseFloat(self.rangeLoss.val());
                var c = self.cmapperLoss.map(v / r / 2.0 + 0.5);

                layer.setStyle({
                    color: c,
                    weight: 1,
                    opacity: 0.9,
                    fillColor: c,
                    fillOpacity: 0.9
                });
            });
        };
        // end Loss

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
            });
        };

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

            if (self.polys !== null) {
                map.ctrls.removeLayer(self.polys);
                map.removeLayer(self.polys);

                map.ctrls.removeLayer(self.labels);
                map.removeLayer(self.labels);
            }

            $.post({
                url: "../tasks/build_subcatchments/",
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("BUILD_SUBCATCHMENTS_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.abstract_watershed = function () {
            var self = instance;
            var task_msg = "Abstracting Watershed";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "../tasks/abstract_watershed/",
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("WATERSHED_ABSTRACTION_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                url: "../report/watershed/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.status.html(task_msg + "... Success");
                    project.set_preferred_units();
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

            $.post({
                url: "../tasks/build_landuse/",
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("LANDUSE_BUILD_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.report = function () {
            var self = instance;
            $.get({
                url: "../report/landuse/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.restore = function (landuse_mode, landuse_single_selection) {
            var self = instance;
            $("#landuse_mode" + landuse_mode).prop("checked", true);
            $("#landuse_single_selection").val("" + landuse_single_selection);

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
                url: "../tasks/set_landuse_mode/",
                data: { "mode": mode, "landuse_single_selection": landuse_single_selection },
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
            } else if (mode === 0) {
                // gridded
                $("#landuse_mode0_controls").show();
                $("#landuse_mode1_controls").hide();
            } else if (mode === 1) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").show();
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

var LanduseModify = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#modify_landuse_form");
        that.status = $("#modify_landuse_form  #status");
        that.stacktrace = $("#modify_landuse_form #stacktrace");
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

        that.toggle = function () {
            var self = instance;

            if (self.checkbox.prop("checked") === true) {
                self.showModifyMap();
                self.selected = new Set();
            } else {
                self.hideModifyMap();
            }
        };

        that.showModifyMap = function () {
            var self = instance;
            self.data = null;
            $.get({
                url: "../resources/subcatchments.json",
                cache: false,
                success: self.onShowSuccess,
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.hideModifyMap = function () {
            var self = instance;
            var map = Map.getInstance();
            map.removeLayer(self.polys);
            self.data = null;
            self.polys = null;
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
                url: "../tasks/modify_landuse/",
                data: { topaz_ids: self.textarea.val(),
                    landuse: self.selection.val() },
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

            $.post({
                url: "../tasks/build_soil/",
                success: function success(response) {
                    if (response.Success === true) {
                        self.form.trigger("SOIL_BUILD_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.report = function () {
            var self = instance;
            $.get({
                url: "../report/soils/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
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

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='soil_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var soil_single_selection = $("#soil_single_selection").val();

            var task_msg = "Setting Mode to " + mode;

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync soil with nodb
            $.post({
                url: "../tasks/set_soil_mode/",
                data: { "mode": mode, "soil_single_selection": soil_single_selection },
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
            } else if (mode === 0) {
                // gridded
                $("#soil_mode0_controls").show();
                $("#soil_mode1_controls").hide();
            } else if (mode === 1) {
                // single
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").show();
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
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.stationselection = $("#climate_station_selection");

        that.setStationMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climatestation_mode']:checked").val();
            }

            var task_msg = "Setting Station Mode to " + mode;

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "../tasks/set_climatestation_mode/",
                data: { "mode": mode },
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("CLIMATE_SETSTATIONMODE_TASK_COMPLETED");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            if (mode === 0) {
                // sync climate with nodb
                $.get({
                    url: "../view/closest_stations/",
                    data: { "mode": mode },
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 1) {
                // sync climate with nodb
                $.get({
                    url: "../view/heuristic_stations/",
                    data: { "mode": mode },
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
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
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "../tasks/set_climatestation/",
                data: { "station": station },
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("CLIMATE_SETSTATION_TASK_COMPLETED");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                url: "../view/climate_monthlies/",
                success: function success(response) {
                    $("#climate_monthlies").html(response);
                    project.set_preferred_units();
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

            $.post({
                url: "../tasks/build_climate/",
                data: self.form.serialize(),
                success: function success(response) {
                    console.log(response);
                    if (response.Success === true) {
                        self.form.trigger("CLIMATE_BUILD_TASK_COMPLETED");
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                url: "../report/climate/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    project.set_preferred_units();
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
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "../tasks/set_climate_mode/",
                data: { "mode": mode, "climate_single_selection": climate_single_selection },
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                // none selected
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode1_controls").hide();
                $("#climate_mode2_controls").hide();
                $("#climate_mode3_controls").hide();
                $("#climate_mode4_controls").hide();
                $("#btn_build_climate_container").hide();
            } else if (mode === 0) {
                // single
                $("#input_years_container").show();
                $("#climate_mode0_controls").show();
                $("#climate_mode1_controls").hide();
                $("#climate_mode2_controls").hide();
                $("#climate_mode3_controls").hide();
                $("#climate_mode4_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 1) {
                // localized
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode1_controls").show();
                $("#climate_mode2_controls").hide();
                $("#climate_mode3_controls").hide();
                $("#climate_mode4_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 2) {
                // observed
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode1_controls").hide();
                $("#climate_mode2_controls").show();
                $("#climate_mode3_controls").hide();
                $("#climate_mode4_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 3) {
                // future
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode1_controls").hide();
                $("#climate_mode2_controls").hide();
                $("#climate_mode3_controls").show();
                $("#climate_mode4_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 4) {
                // single storm
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode1_controls").hide();
                $("#climate_mode2_controls").hide();
                $("#climate_mode3_controls").hide();
                $("#climate_mode4_controls").show();
                $("#btn_build_climate_container").show();
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
        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };
        that.status_url = null;

        that.surf_runoff = $("#wepp_form #surf_runoff");
        that.lateral_flow = $("#wepp_form #lateral_flow");
        that.baseflow = $("#wepp_form #baseflow");
        that.sediment = $("#wepp_form #sediment");

        that.updatePhosphorus = function () {
            var self = instance;

            $.get({
                url: "../query/wepp/phosphorus_opts/",
                cache: false,
                success: function success(response) {
                    self.surf_runoff.val(response.surf_runoff);
                    self.lateral_flow.val(response.lateral_flow);
                    self.baseflow.val(response.baseflow);
                    self.sediment.val(response.sediment);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
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

            $.post({
                url: "../tasks/run_wepp/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                        self.form.trigger("WEPP_RUN_TASK_COMPLETED");
                        //                        self.form.trigger("WEPP_RUN_SUBMITTED_COMPLETED");
                        //                        self.status.html(`${task_msg}... Success`);
                        //                        self.status_url = response.status_url;
                        //                        self.status_loop();
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
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
                url: "../report/wepp/loss/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    project.set_preferred_units();
                    $('#wepploss_tbl').DataTable({iDisplayLength: -1});

                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });


            $.get({
                url: "../report/wepp/frq/",
                cache: false,
                success: function success(response) {
                    self.info.append(response);
                    project.set_preferred_units();
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        var attempts = 0;
        that.status_loop = function () {
            var self = instance;
            attempts = 0;
            if (self.status_url !== null) {
                $.get({
                    url: self.status_url,
                    success: function success(response) {

                        console.log(response);

                        if (response.state === "PENDING") {
                            self.status.html(response.info);
                            attempts += 1;
                            if (attempts > 1000) {
                                self.status_url = null;
                            }
                        } else if (response.state === "FAILURE") {
                            self.pushResponseStacktrace(self, {
                                "Success": false,
                                "Error": "WEPP Run Failed",
                                "StackTrace": response.info
                            });
                            self.status_url = null;
                        } else if (response.state === "SUCCESS") {
                            self.status.html(response.info);
                            self.status_url = null;
                            self.form.trigger("WEPP_RUN_TASK_COMPLETED");
                        } else if (response.state === "PROGRESS") {
                            self.status.html(response.info);
                        } else {
                            console.log(response);
                            throw "Unknown response from server";
                        }
                    }
                }).done(function () {
                    setTimeout(self.status_loop, 2000);
                });
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

// end-of-file controller.js -----------------------------------------
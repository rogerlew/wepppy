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
        that.command_btn_id = 'btn_build_channels_en';

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

            try {
                const mode = $('input[name=set_extent_mode]:checked').val();
                if (mode === "1") {
                    // User-specified extent → parse and write into hidden #map_bounds
                    const raw = $('#map_bounds_text').val() || '';
                    const bbox = parseBboxText(raw);
                    $('#map_bounds').val(bbox.join(','));
                }
            } catch (e) {
                // Surface a friendly error and abort
                self.status.html('<span class="text-danger">Invalid extent: ' + e.message + '</span>');
                return;
            }

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
            $("#map_distance").val(distance);
            $("#map_bounds").val(extent.join(","));

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

        // same palette you used, just no alpha here
        const palette = [
            "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
            "#2500F4", "#6600cc", "#50006b", "#6b006b"
        ].map(color => fromHex(color, 0.9));

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
                            }),
                            pane: 'markerCustomPane'
                        });
                        self.labels.addLayer(lbl);
                    });

                    //self.labels.addTo(map);
                    map.ctrls.addOverlay(self.labels, "Channel Labels");

                    self.status.text("Displaying SUBWTA channels – done");
                })
                .fail((jq, txt, err) =>
                    self.pushErrorStacktrace(self, jq, txt, err)
                );
        };

        that.report = function () {
            var self = instance;

            $.get({
                url: url_for_run("report/channel"),
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

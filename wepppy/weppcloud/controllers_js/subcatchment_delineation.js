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
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#build_subcatchments_form #rq_job");
        that.command_btn_id = 'btn_build_subcatchments';

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        //----------------------------------------------------------------------
        // ─── CONSTANTS / HELPERS ──────────────────────────────────────────────
        //----------------------------------------------------------------------


        // default & clear colours in both CSS and WebGL formats
        that.labelStyle = "color:orange; text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF;";


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

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'BUILD_SUBCATCHMENTS_TASK_COMPLETED') {
                that.show();
                ChannelDelineation.getInstance().show();
            } else if (eventName === 'WATERSHED_ABSTRACTION_TASK_COMPLETED') {
                that.report();
                that.ws_client.disconnect();
                that.enableColorMap("slp_asp");
                Wepp.getInstance().updatePhosphorus();
            }

            baseTriggerEvent(eventName, payload);
        };

        function bindRadioGroup(name, handler) {
            var selector = "input[name='" + name + "']";
            var $radios = $(selector);
            if ($radios.length === 0) {
                return;
            }
            $radios.off('change.subcatchment');
            $radios.on('change.subcatchment', handler);
        }

        function bindSlider(selector, handler) {
            var $slider = $(selector);
            if ($slider.length === 0) {
                return;
            }
            $slider.off('input.subcatchment');
            $slider.on('input.subcatchment', handler);
        }

        function renderLegendIfPresent(palette, canvasId) {
            if (typeof render_legend !== 'function') {
                return;
            }
            if (!document.getElementById(canvasId)) {
                return;
            }
            render_legend(palette, canvasId);
        }

        that.initializeColorMapControls = function () {
            bindRadioGroup('sub_cmap_radio', function () {
                var value = $("input[name='sub_cmap_radio']:checked").val();
                if (value) {
                    that.setColorMap(value);
                }
            });

            bindRadioGroup('wepp_sub_cmap_radio', function () {
                var value = $("input[name='wepp_sub_cmap_radio']:checked").val();
                if (value) {
                    that.setColorMap(value);
                }
            });

            bindRadioGroup('rhem_sub_cmap_radio', function () {
                var value = $("input[name='rhem_sub_cmap_radio']:checked").val();
                if (value) {
                    that.setColorMap(value);
                }
            });

            bindSlider('#wepp_sub_cmap_range_phosphorus', function () {
                that.updateGlLayerStyle();
            });
            bindSlider('#wepp_sub_cmap_range_runoff', function () {
                that.updateGlLayerStyle();
            });
            bindSlider('#wepp_sub_cmap_range_loss', function () {
                that.updateGlLayerStyle();
            });
            bindSlider('#wepp_grd_cmap_range_loss', function () {
                that.updateGriddedLoss();
            });

            bindSlider('#rhem_sub_cmap_range_runoff', function () {
                that.updateGlLayerStyle();
            });
            bindSlider('#rhem_sub_cmap_range_sed_yield', function () {
                that.updateGlLayerStyle();
            });
            bindSlider('#rhem_sub_cmap_range_soil_loss', function () {
                that.updateGlLayerStyle();
            });

            bindSlider('#ash_sub_cmap_range_load', function () {
                that.updateGlLayerStyle();
            });
            bindSlider('#ash_sub_cmap_range_transport', function () {
                that.updateGlLayerStyle();
            });

            renderLegendIfPresent('viridis', 'landuse_sub_cmap_canvas_cover');
            renderLegendIfPresent('viridis', 'wepp_sub_cmap_canvas_phosphorus');
            renderLegendIfPresent('winter', 'wepp_sub_cmap_canvas_runoff');
            renderLegendIfPresent('jet2', 'wepp_sub_cmap_canvas_loss');
            renderLegendIfPresent('jet2', 'wepp_grd_cmap_canvas_loss');
            renderLegendIfPresent('winter', 'rhem_sub_cmap_canvas_runoff');
            renderLegendIfPresent('viridis', 'rhem_sub_cmap_canvas_sed_yield');
            renderLegendIfPresent('jet2', 'rhem_sub_cmap_canvas_soil_loss');
            renderLegendIfPresent('jet2', 'ash_sub_cmap_canvas_load');
            renderLegendIfPresent('jet2', 'ash_sub_cmap_canvas_transport');
        };

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

            if (self.glLayer === null) {
                throw "Subcatchments have not been drawn";
            }

            if (cmap_name === "default") {
                self.render();
                Map.getInstance().sub_legend.html("");
            } else if (cmap_name === "slp_asp") {
                self.renderSlpAsp();
            } else if (cmap_name === "dom_lc") {
                self.renderLanduse();
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
        // ─── COLOR FUNCTION FACTORY ──────────────────────────────────────────
        //----------------------------------------------------------------------
        that._colorFn = function () {
            const self = instance;

            // Return a cmapFn based on cmapMode
            switch (self.cmapMode) {
                case 'default':
                    return () => COLOR_DEFAULT;

                case 'clear':
                    return () => COLOR_CLEAR;

                case 'slp_asp':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const rgbHex = self.dataSlpAsp?.[id]?.color; // '#aabbcc'
                        return rgbHex ? fromHex(rgbHex, 0.7) : COLOR_DEFAULT;
                    };

                case 'landuse':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const rgbHex = self.dataLanduse?.[id]?.color; // '#aabbcc'
                        return rgbHex ? fromHex(rgbHex, 0.7) : COLOR_DEFAULT;
                    };

                case 'soils':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const rgbHex = self.dataSoils?.[id]?.color; // '#aabbcc'
                        return rgbHex ? fromHex(rgbHex, 0.7) : COLOR_DEFAULT;
                    };

                case 'cover':
                    return (feat) => {
                        if (!self.dataCover) return COLOR_DEFAULT;
                        const id = feat.properties.TopazID;
                        const v = self.dataCover[id]; // 0-100
                        const hex = self.cmapperCover.map(v); // '#rrggbb'
                        return fromHex(hex);
                    };

                case 'phosphorus':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const v = parseFloat(self.dataPhosphorus[id].value); // kg/ha
                        const linearValue = parseFloat(self.rangePhosphorus.val()); // 0 - 100
                        const minLog = 0.001;  // slider min
                        const maxLog = 10.0;   // slider max
                        const maxLinear = 100;
                        const r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        self.labelPhosphorusMin.html("0.000");
                        updateRangeMaxLabel_kgha(r, self.labelPhosphorusMax);
                        const hex = self.cmapperPhosphorus.map(v / r);
                        return fromHex(hex, 0.9);
                    };

                case 'runoff':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const v = parseFloat(self.dataRunoff[id].value); // mm
                        const linearValue = parseFloat(self.rangeRunoff.val()); // 0 - 100
                        const minLog = 0.1; // slider min
                        const maxLog = 1000;   // slider max
                        const maxLinear = 100;
                        const r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        self.labelRunoffMin.html("0.000");
                        updateRangeMaxLabel_mm(r, self.labelRunoffMax);
                        const hex = self.cmapperRunoff.map(v / r);
                        return fromHex(hex, 0.9);
                    };

                case 'loss':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const v = parseFloat(self.dataLoss[id].value); // mm
                        const linearValue = parseFloat(self.rangeLoss.val()); // 0 - 100
                        const minLog = 1; // slider min
                        const maxLog = 10000;   // slider max
                        const maxLinear = 100;
                        const r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        self.labelLossMin.html("0.000");
                        updateRangeMaxLabel_kgha(r, self.labelLossMax);
                        const hex = self.cmapperLoss.map(v / r);
                        return fromHex(hex, 0.9);
                    };

                case 'ash_load':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const v = parseFloat(self.dataAshLoad[id][self.ashMeasure].value);
                        const linearValue = parseFloat(self.rangeAshLoad.val()); // 0 - 100
                        const minLog = 0.001; // slider min
                        const maxLog = 100;   // slider max
                        const maxLinear = 100;
                        const r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        self.labelAshLoadMin.html("0.000");
                        updateRangeMaxLabel_tonneha(r, self.labelAshLoadMax);
                        const hex = self.cmapperAshLoad.map(v / r);
                        return fromHex(hex, 0.9);
                    };

                case 'rhem_runoff':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const v = parseFloat(self.dataRhemRunoff[id].value); // mm
                        const linearValue = parseFloat(self.rangeRhemRunoff.val()); // 0 - 100
                        const minLog = 0.1; // slider min
                        const maxLog = 1000;   // slider max
                        const maxLinear = 100;
                        const r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        self.labelRhemRunoffMin.html("0.000");
                        updateRangeMaxLabel_mm(r, self.labelRhemRunoffMax);
                        const hex = self.cmapperRhemRunoff.map(v / r);
                        return fromHex(hex, 0.9);
                    };

                case 'rhem_sed_yield':
                    return (feat) => {
                        const id = feat.properties.TopazID;
                        const v = parseFloat(self.dataRhemSedYield[id].value); // mm
                        const linearValue = parseFloat(self.rangeRhemSedYield.val()); // 0 - 100
                        const minLog = 1; // slider min
                        const maxLog = 10000;   // slider max
                        const maxLinear = 100;
                        const r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        self.labelRhemSedYieldMin.html("0.000");
                        updateRangeMaxLabel_mm(r, self.labelRhemSedYieldMax);
                        const hex = self.cmapperRhemSedYield.map(v / r);
                        return fromHex(hex, 0.9);
                    };

                default:
                    return () => COLOR_DEFAULT;
            }
        };


        //----------------------------------------------------------------------
        // ─── GL LAYER (re)BUILDER ────────────────────────────────────────────
        //----------------------------------------------------------------------
        that._refreshGlLayer = function () {
            const self = instance;
            const map = Map.getInstance();

            if (self.glLayer) {
                self.glLayer.remove(); // Dispose VBOs & canvas
                map.ctrls.removeLayer(self.glLayer); // Keep layer control consistent
            }

            const cmapFn = self._colorFn();

            self.glLayer = L.glify.layer({
                geojson: self.data,
                paneName: 'subcatchmentsGlPane',
                glifyOptions: {
                    opacity: 0.5,
                    border: true,
                    color: (i, f) => cmapFn(f),
                    click: (e, f) => map.subQuery(f.properties.TopazID)
                }
            }).addTo(map);

            map.ctrls.addOverlay(self.glLayer, 'Subcatchments');
        };

        that.updateGlLayerStyle = function () {
            var self = instance;

            const cmapFn = self._colorFn();
            self.glLayer.setStyle({ color: (i, f) => cmapFn(f) });
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
                    }),
                    pane: 'markerCustomPane'
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
        const _renderLayer = function (type, dataProp, cmapMode, legendUrl) {
            that.status.text(`Loading ${type} …`);
            $.get({
                url: `query/${type}/subcatchments/`,
                cache: false,
                success: data => {
                    that[dataProp] = data;
                    that.cmapMode = cmapMode;
                    that._refreshGlLayer();
                },
                error: jq => that.pushResponseStacktrace(that, jq.responseJSON),
                fail: (jq, s, e) => that.pushErrorStacktrace(that, jq, s, e)
            }).always(() => {
                $.get({
                    url: `resources/legends/${legendUrl}/`,
                    cache: false,
                    success: function (response) {
                        var map = Map.getInstance();
                        map.sub_legend.html(response);
                    },
                    error: function (jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function (jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            });
        };

        that.renderSlpAsp = function () {
            _renderLayer('watershed', 'dataSlpAsp', 'slp_asp', 'slope_aspect');
        };

        that.renderLanduse = function () {
            _renderLayer('landuse', 'dataLanduse', 'landuse', 'landuse');
        };

        that.renderSoils = function () {
            _renderLayer('soils', 'dataSoils', 'soils', 'soils');
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

        const WEPP_LOSS_METRIC_EXPRESSIONS = Object.freeze({
            runoff: 'CAST(loss."Runoff Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
            subrunoff: 'CAST(loss."Subrunoff Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
            baseflow: 'CAST(loss."Baseflow Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
            loss: 'CAST(loss."Soil Loss" / NULLIF(loss."Hillslope Area", 0) AS DOUBLE)'
        });

        function resolveRunSlugForQuery() {
            var prefix = (typeof site_prefix === 'string') ? site_prefix : '';
            if (prefix && prefix !== '/' && prefix.charAt(0) !== '/') {
                prefix = '/' + prefix;
            }
            if (prefix === '/') {
                prefix = '';
            }

            var path = window.location.pathname || '';
            if (prefix && path.indexOf(prefix) === 0) {
                path = path.slice(prefix.length);
            }

            var parts = path.split('/').filter(function (segment) {
                return segment.length > 0;
            });
            var runsIndex = parts.indexOf('runs');
            if (runsIndex === -1 || parts.length <= runsIndex + 1) {
                return null;
            }
            return decodeURIComponent(parts[runsIndex + 1]);
        }

        function postQueryEngine(payload) {
            var runSlug = resolveRunSlugForQuery();
            if (!runSlug) {
                return $.Deferred(function (defer) {
                    var errorResponse = {
                        status: 400,
                        responseJSON: {
                            Error: 'Unable to resolve run identifier from the current URL.'
                        }
                    };
                    defer.reject(errorResponse, 'error', errorResponse.responseJSON.Error);
                }).promise();
            }

            var path = "/query-engine/runs/" + encodeURIComponent(runSlug) + "/query";
            if (path.charAt(0) !== '/') {
                path = '/' + path;
            }
            var targetUrl = url_for_run(path);

            return $.ajax({
                url: targetUrl,
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                cache: false,
                data: JSON.stringify(payload)
            });
        }

        function fetchLossMetric(metricKey) {
            var expression = WEPP_LOSS_METRIC_EXPRESSIONS[metricKey];
            if (!expression) {
                return $.Deferred(function (defer) {
                    var message = 'Unknown WEPP loss metric: ' + metricKey;
                    var errorResponse = {
                        status: 400,
                        responseJSON: {
                            Error: message
                        }
                    };
                    defer.reject(errorResponse, 'error', message);
                }).promise();
            }

            var payload = {
                datasets: [
                    { path: "wepp/output/interchange/loss_pw0.hill.parquet", alias: "loss" },
                    { path: "watershed/hillslopes.parquet", alias: "hills" }
                ],
                joins: [
                    { left: "loss", right: "hills", left_on: ["wepp_id"], right_on: ["wepp_id"], join_type: "left" }
                ],
                columns: [
                    'hills.topaz_id AS topaz_id',
                    expression + " AS value"
                ],
                order_by: ["topaz_id"]
            };

            return postQueryEngine(payload).then(function (response) {
                var map = {};
                var records = Array.isArray(response && response.records) ? response.records : [];
                records.forEach(function (row) {
                    if (!row) {
                        return;
                    }
                    var topazId = row.topaz_id;
                    if (topazId === undefined || topazId === null) {
                        return;
                    }
                    map[String(topazId)] = {
                        topaz_id: topazId,
                        value: row.value
                    };
                });
                return map;
            });
        }

        /* ---------- runoff & variants --------------------------------------- */

        that.dataRunoff = null;
        that.labelRunoffMin = $('#wepp_sub_cmap_canvas_runoff_min');
        that.labelRunoffMax = $('#wepp_sub_cmap_canvas_runoff_max');
        that.cmapperRunoff = createColormap({ colormap: 'winter', nshades: 64 });
        that.rangeRunoff = $('#wepp_sub_cmap_range_runoff');

        that.renderRunoff = function () { _getRunoff('runoff', 'runoff'); };
        that.renderSubrunoff = function () { _getRunoff('subrunoff', 'runoff'); };
        that.renderBaseflow = function () { _getRunoff('baseflow', 'runoff'); };
        function _getRunoff(metricKey, mode) {
            fetchLossMetric(metricKey)
                .done(function (data) {
                    that.dataRunoff = data;
                    that.cmapMode = mode;
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        }

        /* ---------- loss ----------------------------------------------------- */

        that.dataLoss = null;
        that.labelLossMin = $('#wepp_sub_cmap_canvas_loss_min');
        that.labelLossMax = $('#wepp_sub_cmap_canvas_loss_max');
        that.cmapperLoss = createColormap({ colormap: "jet2", nshades: 64 });
        that.rangeLoss = $('#wepp_sub_cmap_range_loss');

        that.renderLoss = function () {
            fetchLossMetric('loss')
                .done(function (data) {
                    that.dataLoss = data;
                    that.cmapMode = 'loss';
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };


        /* ---------- ash_load ----------------------------------------------------- */

        that.dataAshLoad = null;
        that.ashMeasure = null
        that.rangeAshLoad = $('#ash_sub_cmap_range_load');
        that.labelAshLoadMin = $('#ash_sub_cmap_canvas_load_min');
        that.labelAshLoadMax = $('#ash_sub_cmap_canvas_load_max');
        that.cmapperAshLoad = createColormap({ colormap: "jet2", nshades: 64 });

        that.renderAshLoad = function () {
            $.get('query/ash/out/')
                .done(dataAshLoad => {
                    that.dataAshLoad = dataAshLoad;
                    that.cmapMode = 'ash_load';
                    that.ashMeasure = getAshTransportMeasure();
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };

        /* ---------- phosphorus (kg/ha)  ------------------------------------- */

        that.dataPhosphorus = null;
        that.rangePhosphorus = $('#wepp_sub_cmap_range_phosphorus');
        that.labelPhosphorusMin = $('#wepp_sub_cmap_canvas_phosphorus_min');
        that.labelPhosphorusMax = $('#wepp_sub_cmap_canvas_phosphorus_max');
        that.labelPhosphorusUnits = $('#wepp_sub_cmap_canvas_phosphorus_units');
        that.cmapperPhosphorus = createColormap({ colormap: 'viridis', nshades: 64 });

        that.renderPhosphorus = function () {
            $.get('query/wepp/phosphorus/subcatchments/')
                .done(data => {
                    that.dataPhosphorus = data;
                    that.cmapMode = 'phosphorus';
                    that._refreshGlLayer();
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

            if (self.grid !== undefined && self.grid !== null) {
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

        that.renderRhemRunoff = function () {
            $.get('query/rhem/runoff/subcatchments/')
                .done(data => {
                    that.dataRhemRunoff = data;
                    that.cmapMode = 'rhem_runoff';
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };

        //
        // RhemSedYield
        //
        that.dataRhemSedYield = null;
        that.rangeRhemSedYield = $('#rhem_sub_cmap_range_sed_yield');
        that.labelRhemSedYieldMin = $('#rhem_sub_cmap_canvas_sed_yield_min');
        that.labelRhemSedYieldMax = $('#rhem_sub_cmap_canvas_sed_yield_max');
        that.labelRhemSedYieldUnits = $('#rhem_sub_cmap_canvas_sed_yield_units');
        that.cmapperRhemSedYield = createColormap({ colormap: 'viridis', nshades: 64 });

        that.renderRhemSedYield = function () {
            $.get('query/rhem/sed_yield/subcatchments/')
                .done(data => {
                    that.dataRhemSedYield = data;
                    that.cmapMode = 'rhem_sed_yield';
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };


        //
        // AshTransport
        //
        that.dataAshTransport = null;
        that.rangeAshTransport = $('#ash_sub_cmap_range_transport');
        that.labelAshTransportMin = $('#ash_sub_cmap_canvas_transport_min');
        that.labelAshTransportMax = $('#ash_sub_cmap_canvas_transport_max');
        that.labelAshTransportUnits = $('#ash_sub_cmap_canvas_transport_units');
        that.cmapperAshTransport = createColormap({ colormap: "jet2", nshades: 64 });

        that.renderAshTransport = function () {
            $.get('query/ash_out/')
                .done(data => {
                    that.dataAshTransport = data;
                    that.cmapMode = 'ash_transport';
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };

        that.renderAshTransportWater = function () {
            $.get('query/ash_out/')
                .done(data => {
                    that.dataAshTransport = data;
                    that.cmapMode = 'ash_transport';
                    that._refreshGlLayer();
                })
                .fail((jq, s, e) => that.pushErrorStacktrace(that, jq, s, e));
        };


        that.getAshTransportMeasure = function () {
            return $("input[name='wepp_sub_cmap_radio']:checked").val();
        }

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

            if (self.glLayer !== null) {
                map.ctrls.removeLayer(self.glLayer);
                map.removeLayer(self.glLayer);

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
                url: url_for_run("report/watershed/"),
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

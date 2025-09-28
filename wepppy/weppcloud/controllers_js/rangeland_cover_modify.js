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

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'RANGELAND_COVER_MODIFY_TASK_COMPLETED') {
                var subCtrl = SubcatchmentDelineation.getInstance();
                if (subCtrl.getCmapMode && subCtrl.getCmapMode() === 'rangeland_cover') {
                    subCtrl.setColorMap('rangeland_cover');
                }
                RangelandCover.getInstance().report();
                if (typeof subCtrl.cmapRangelandCover === 'function') {
                    subCtrl.cmapRangelandCover();
                }
            }

            baseTriggerEvent(eventName, payload);
        };

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

            for (var id in self.glLayer._layers) {
                var topaz_id2 = self.glLayer._layers[id].feature.properties.TopazID;

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

                        var layer = self.glLayer._layers[id];

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
                if (self.glLayer == null) {
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
            map.removeLayer(self.glLayer);

            self.data = null;
            self.glLayer = null;
            self.ll0 = null;
        };

        that.onShowSuccess = function (response) {
            var self = instance;
            var map = Map.getInstance();
            self.data = response;
            self.glLayer = L.geoJSON(self.data.features, {
                style: self.style,
                onEachFeature: self.onEachFeature
            });
            self.glLayer.addTo(map);
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

                        self.triggerEvent('RANGELAND_COVER_MODIFY_TASK_COMPLETED');
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

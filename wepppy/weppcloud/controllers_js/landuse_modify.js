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

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'LANDCOVER_MODIFY_TASK_COMPLETED') {
                var subCtrl = SubcatchmentDelineation.getInstance();
                if (subCtrl.getCmapMode && subCtrl.getCmapMode() === 'dom_lc') {
                    subCtrl.setColorMap('dom_lc');
                }
                try {
                    if (typeof Landuse !== 'undefined' && Landuse !== null) {
                        var landuseController = Landuse.getInstance();
                        if (landuseController && typeof landuseController.report === 'function') {
                            landuseController.report();
                        }
                    }
                } catch (err) {
                    console.warn('Landuse report unavailable in current view', err);
                }
            }

            baseTriggerEvent(eventName, payload);
        };

        that.checkbox = $('#checkbox_modify_landuse');
        that.textarea = $('#textarea_modify_landuse');
        that.selection = $('#selection_modify_landuse');
        that.data = null; // Leaflet geoJSON layer
        that.polys = null; // Leaflet geoJSON layer
        that.selected = null;

        $('#btn_modify_landuse').on('click', function () {
            instance.modify();
        });

        that.checkbox.on('change', function () {
            instance.toggle();
        });

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
            var map = MapController.getInstance();

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
        }

        that.boxSelectionModeMouseUp = function (evt) {
            var self = instance;

            var map = MapController.getInstance();

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
                if (self.glLayer == null) {
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

            var map = MapController.getInstance();
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
            var map = MapController.getInstance();

            map.boxZoom.enable();
            //map.dragging.enable();
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
            var map = MapController.getInstance();
            self.data = response;
            self.glLayer = L.geoJSON(self.data.features, {
                style: self.style,
                onEachFeature: self.onEachFeature
            });
            self.glLayer.addTo(map);
        };

        that.onEachFeature = function (feature, layer) {
            var self = instance;
            var map = MapController.getInstance();

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

                        self.triggerEvent('LANDCOVER_MODIFY_TASK_COMPLETED');
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

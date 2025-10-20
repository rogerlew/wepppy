/* ----------------------------------------------------------------------------
 * Map
 * ----------------------------------------------------------------------------
 */

function createTabset(root) {
    if (!root) {
        return null;
    }

    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
    var panels = Array.prototype.slice.call(root.querySelectorAll('[role="tabpanel"]'));

    if (tabs.length === 0 || panels.length === 0) {
        return null;
    }

    function getTarget(tab) {
        return tab ? tab.getAttribute('data-tab-target') : null;
    }

    function setActive(panelId, focusTab) {
        tabs.forEach(function (tab) {
            var target = getTarget(tab);
            var isActive = target === panelId;
            tab.classList.toggle('is-active', isActive);
            tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
            tab.setAttribute('tabindex', isActive ? '0' : '-1');
            if (isActive && focusTab) {
                tab.focus();
            }
        });

        panels.forEach(function (panel) {
            var isActive = panel.id === panelId;
            panel.classList.toggle('is-active', isActive);
            if (isActive) {
                panel.removeAttribute('hidden');
            } else {
                panel.setAttribute('hidden', '');
            }
        });

        root.dispatchEvent(new CustomEvent('wc-tabset:change', {
            detail: { panelId: panelId },
            bubbles: true
        }));
    }

    var current = tabs.find(function (tab) {
        return tab.getAttribute('aria-selected') === 'true' || tab.classList.contains('is-active');
    });
    var initialPanel = getTarget(current) || getTarget(tabs[0]);
    setActive(initialPanel, false);

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            setActive(getTarget(tab), false);
        });

        tab.addEventListener('keydown', function (event) {
            var key = event.key;
            if (key !== 'ArrowLeft' && key !== 'ArrowRight' && key !== 'Home' && key !== 'End') {
                return;
            }

            event.preventDefault();
            var currentIndex = tabs.indexOf(tab);
            if (key === 'ArrowLeft' || key === 'ArrowRight') {
                var offset = key === 'ArrowRight' ? 1 : -1;
                var nextIndex = (currentIndex + offset + tabs.length) % tabs.length;
                setActive(getTarget(tabs[nextIndex]), true);
            } else if (key === 'Home') {
                setActive(getTarget(tabs[0]), true);
            } else if (key === 'End') {
                setActive(getTarget(tabs[tabs.length - 1]), true);
            }
        });
    });

    return {
        activate: function (panelId, focusTab) {
            if (!panelId) {
                return;
            }
            setActive(panelId, focusTab === true);
        }
    };
}

var MapController = function () {
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

        that.createPane('markerCustomPane');
        that.getPane('markerCustomPane').style.zIndex = 700;

        //
        // Elevation feedback on mouseover
        //
        that.isFetchingElevation = false;
        that.mouseelev = $("#mouseelev");
        that.drilldown = $("#drilldown");
        that.sub_legend = $("#sub_legend");
        that.sbs_legend = $("#sbs_legend");

        that.fetchTimer;
        that.centerInput = $("#input_centerloc");
        that.tabset = createTabset(document.querySelector('#setloc_form [data-tabset]'));

        if (that.centerInput && that.centerInput.length) {
            that.centerInput.on('keydown', function (event) {
                that.handleCenterInputKey(event);
            });
        }

        $('#btn_setloc').on('click', function () {
            that.goToEnteredLocation();
        });

        $('#btn_find_topaz_id').on('click', function () {
            that.findByTopazId();
        });

        $('#btn_find_wepp_id').on('click', function () {
            that.findByWeppId();
        });

        setTimeout(function () {
            if (typeof that.invalidateSize === 'function') {
                that.invalidateSize();
            }
        }, 0);

        var encodedRunId = (typeof runid !== "undefined" && runid !== null) ? encodeURIComponent(runid) : null;
        var encodedConfig = (typeof config !== "undefined" && config !== null) ? encodeURIComponent(config) : null;
        var elevationEndpoint = null;
        var elevationCooldownMs = 400;
        if (encodedRunId && encodedConfig) {
            var prefix = (typeof site_prefix === "string") ? site_prefix : "";
            elevationEndpoint = prefix + "/runs/" + encodedRunId + "/" + encodedConfig + "/elevationquery/";
        }

        that.fetchElevation = function (ev) {
            var self = instance;

            if (!elevationEndpoint) {
                self.isFetchingElevation = false;
                return;
            }

            $.ajax({
                method: "POST",
                url: elevationEndpoint,
                data: JSON.stringify({ lat: ev.latlng.lat, lng: ev.latlng.lng }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                cache: false,
                success: function (response) {
                    var cursorLng = coordRound(ev.latlng.lng);
                    var cursorLat = coordRound(ev.latlng.lat);

                    if (!response || typeof response.Elevation !== "number" || !isFinite(response.Elevation)) {
                        var message = (response && response.Error) ? response.Error : "Elevation unavailable";
                        self.mouseelev.show().text("| Elevation: " + message + " | Cursor: " + cursorLng + ", " + cursorLat);
                        return;
                    }

                    var elev = response.Elevation.toFixed(1);
                    self.mouseelev.show().text("| Elevation: " + elev + " m | Cursor: " + cursorLng + ", " + cursorLat);
                },
                error: function (jqXHR) {
                    console.log(jqXHR.responseJSON || jqXHR.statusText || "Elevation request failed");
                },
                complete: function () {
                    // Reset the timer in the complete callback
                    clearTimeout(self.fetchTimer);
                    self.fetchTimer = setTimeout(function () {
                        self.isFetchingElevation = false;
                    }, elevationCooldownMs);
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

        function sanitizeLocationInput(value) {
            if (!value) {
                return [];
            }
            var sanitized = String(value).replace(/[a-zA-Z{}\[\]\\|\/<>;:]/g, '');
            return sanitized.split(/[\s,]+/).filter(function (item) {
                return item !== '';
            });
        }

        that.goToEnteredLocation = function () {
            var parts = sanitizeLocationInput(that.centerInput.val());
            if (parts.length < 2) {
                return;
            }

            var lon = parseFloat(parts[0]);
            var lat = parseFloat(parts[1]);

            if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
                console.warn('Invalid location values', parts);
                return;
            }

            var zoom = that.getZoom();
            if (parts.length >= 3) {
                var parsedZoom = parseInt(parts[2], 10);
                if (Number.isFinite(parsedZoom)) {
                    zoom = parsedZoom;
                }
            }

            that.flyTo([lat, lon], zoom);
        };

        that.handleCenterInputKey = function (event) {
            if (!event) {
                return;
            }
            var key = event.key || event.keyCode;
            if (key === 'Enter' || key === 13) {
                event.preventDefault();
                that.goToEnteredLocation();
            }
        };

        that.findById = function (idType) {
            if (!window.WEPP_FIND_AND_FLASH) {
                console.warn('WEPP_FIND_AND_FLASH helper not available');
                return;
            }

            var value = (that.centerInput.val() || '').trim();
            if (!value) {
                return;
            }

            var subCtrl = SubcatchmentDelineation.getInstance();
            var channelCtrl = ChannelDelineation.getInstance();

            window.WEPP_FIND_AND_FLASH.findAndFlashById({
                idType: idType,
                value: value,
                map: that,
                layers: [
                    { ctrl: subCtrl, type: window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.SUBCATCHMENT },
                    { ctrl: channelCtrl, type: window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.CHANNEL }
                ],
                onFlash: function (result) {
                    var topazId = value;

                    if (idType !== window.WEPP_FIND_AND_FLASH.ID_TYPE.TOPAZ) {
                        var hit = result.hits && result.hits[0];
                        if (hit && hit.properties && hit.properties.TopazID !== undefined && hit.properties.TopazID !== null) {
                            topazId = hit.properties.TopazID;
                        }
                    }

                    if (result.featureType === window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.SUBCATCHMENT) {
                        that.subQuery(topazId);
                    } else if (result.featureType === window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.CHANNEL) {
                        that.chnQuery(topazId);
                    }
                }
            });
        };

        that.findByTopazId = function () {
            that.findById(window.WEPP_FIND_AND_FLASH.ID_TYPE.TOPAZ);
        };

        that.findByWeppId = function () {
            that.findById(window.WEPP_FIND_AND_FLASH.ID_TYPE.WEPP);
        };

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

        that.addGeoJsonOverlay = function (options) {
            options = options || {};
            var url = options.url;
            if (!url) {
                console.warn('addGeoJsonOverlay called without a url');
                return null;
            }

            var layerName = options.layerName || 'Overlay';
            var style = options.style || null;

            $.get({
                url: url,
                cache: false,
                success: function success(response) {
                    var overlay = L.geoJSON(response, {
                        style: style
                    });
                    overlay.addTo(that);
                    that.ctrls.addOverlay(overlay, layerName);
                },
                error: function error(jqXHR) {
                    console.warn('Failed to load overlay', layerName, jqXHR);
                }
            });

            return that;
        };

        function handleViewportChange() {
            that.onMapChange();

            if (typeof ChannelDelineation !== 'undefined' && ChannelDelineation !== null) {
                try {
                    ChannelDelineation.getInstance().onMapChange();
                } catch (err) {
                    console.warn('ChannelDelineation.onMapChange failed', err);
                }
            }
        }

        that.on('zoom', handleViewportChange);
        that.on('move', handleViewportChange);

        function handleViewportSettled() {
            that.loadUSGSGageLocations();
            that.loadSnotelLocations();
        }

        that.on('moveend', handleViewportSettled);
        that.on('zoomend', handleViewportSettled);

        that.onMapChange = function () {
            var self = instance;

            var center = self.getCenter();
            var zoom = self.getZoom();
            var lng = coordRound(center.lng);
            var lat = coordRound(center.lat);
            var map_w = Math.round($('#mapid').width());
            $("#mapstatus").text("Center: " + lng +
                ", " + lat +
                " | Zoom: " + zoom +
                " ( Map Width:" + map_w + "px )");

        };

        that.hillQuery = function (query_url) {
            if (that.tabset && typeof that.tabset.activate === 'function') {
                that.tabset.activate('drilldown', true);
            }

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
            var query_url = url_for_run("report/chn_summary/" + topazID + "/");
            self.hillQuery(query_url);
        };

        that.subQuery = function (topazID) {
            var self = instance;
            var query_url = url_for_run("report/sub_summary/" + topazID + "/");
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

window.MapController = MapController;
window.WeppMap = MapController;

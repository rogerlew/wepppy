"use strict";

var site_prefix = "{{ site_prefix }}";
var runid = "{{ ron.runid }}";
var config = "{{ ron.config_stem }}";

$(document).ready(function () {

    "use strict";
    // globals for JSLint: $, L, polylabel, setTimeout, console

    /*
     * Controller Singletons
     * =====================
     */

    var project = Project.getInstance();
    var team = Team.getInstance();
    var map = Map.getInstance();
    var channel_ctrl = ChannelDelineation.getInstance();
    var outlet = Outlet.getInstance();
    var sub_ctrl = SubcatchmentDelineation.getInstance();
    var landuse = Landuse.getInstance();
    var lc_modify = LanduseModify.getInstance();
    var soil = Soil.getInstance();
    var climate = Climate.getInstance();
    var wepp = Wepp.getInstance();
    var observed = Observed.getInstance();
    var debris_flow = DebrisFlow.getInstance();
    var ash = Ash.getInstance();


    team.hideStacktrace();
    channel_ctrl.hideStacktrace();
    outlet.hideStacktrace();
    sub_ctrl.hideStacktrace();
    landuse.hideStacktrace();
    lc_modify.hideStacktrace();
    soil.hideStacktrace();
    climate.hideStacktrace();
    wepp.hideStacktrace();
    try {
        observed.hideStacktrace();
    } catch (e) { }

    try {
        debris_flow.hideStacktrace();
    } catch (e) { }


    /*
     * Project Initialization
     * ======================
     */

    //
    // Bindings
    //
    $("#input_name").keyup(function (event) {
        if (event.keyCode === 13) {
            $("#btn_setname").click();
        }
    });

    $("#btn_setname").click(function () {
        var name = $("#input_name").val();
        project.setName(name);
    });

    //
    // Units
    //

    $("[name^=unitizer_]").change(function () {
        project.unitChangeEvent();
    });

    $("[name=uni_main_selector]").change(function () {
        var pref = $("input[name='uni_main_selector']:checked").val();
        pref = parseInt(pref, 10);

        // this lives in the controller/unitizer.js template
        // so it can be generated dynamically
        setGlobalUnitizerPreference(pref);

        // sync with server
        project.unitChangeEvent();
    });

    /*
     * Map Initialization
     * ==================
     */

    //
    // Bindingss
    //

    // emulate click if user hits enter while in the entry field
    $("#input_centerloc").keyup(function (event) {
        if (event.keyCode === 13) {
            $("#btn_setloc").click();
        }
    });

    // parse the entry and fly to requested location/zoom
    $("#btn_setloc").click(function () {
        var loc = $("#input_centerloc").val();
        loc = loc.split(",");
        var lon = parseFloat(loc[0]);
        var lat = parseFloat(loc[1]);

        var zoom = map.getZoom();
        if (loc.length === 3) {
            zoom = parseInt(loc[2], 10);
        }

        map.flyTo([lat, lon], zoom);
    });

    /* requires https
    $("#btn_currentloc").click(function (){
        console.log('btn_currentloc');
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function () {
                map.flyTo([position.coords.latitude,
                           position.coords.longitude], 12);
            });
        } else {
            alert("Geolocation is not supported by this browser.");
        }
    });
    */

    //
    // Initial Configuration
    //
    map.setView({{ ron.center0 }}, {{ ron.zoom0 }});

    // call map.onMapChange to update mapStatus
    map.onMapChange();

    if ({{ (ron.boundary != None) | tojson }}) {
        var boundary = null;
        $.get({
            url: "{{ site_prefix }}/{{ ron.boundary }}",
            cache: false,
            success: function success(response) {
                boundary = L.geoJSON(response, {
                    style: {
                        color: "#FF0000",
                        opacity: 1,
                        weight: 2,
                        fillColor: "#FFFFFF",
                        fillOpacity: 0.0
                    }
                });
                boundary.addTo(map);
            }
        });
    }

    {% if 'baer' in ron.mods %}
    /*
     * Baer mod
     * ======================
     */

    var baer = Baer.getInstance();
    baer.hideStacktrace();

    $("#btn_upload_sbs").click(function () {
        baer.upload_sbs();
    });

    baer.form.on("SBS_UPLOAD_TASK_COMPLETE", function () {
        console.log("SBS_UPLOAD_TASK_COMPLETE");
        setTimeout(baer.show_sbs, 4000);
        setTimeout(baer.load_modify_class, 4000);
    });

    baer.form.on("MODIFY_BURN_CLASS_TASK_COMPLETE", function () {
        console.log("MODIFY_BURN_CLASS_TASK_COMPLETE");
        setTimeout(baer.show_sbs, 2000);
        setTimeout(baer.load_modify_class, 4000);
    });

    if ({{ ron.has_sbs | tojson}})
    {
        baer.show_sbs();
        baer.load_modify_class();
    }
    {% endif %}

    /*
     * Channel Initialization
     * ======================
     */

    //
    // Bindings
    //
    var input_mcl = $("#input_mcl");
    var input_mcl_en = $("#input_mcl_en");
    var input_csa = $("#input_csa");
    var input_csa_en = $("#input_csa_en");

    input_mcl.on("input", function () {
        console.log('on input_mcl change.');
        input_mcl_en.val(parseFloat(input_mcl.val()) * 3.28084 );
    });

    input_mcl_en.on("input", function () {
        console.log('on input_mcl_en change.');
        input_mcl.val(parseFloat(input_mcl_en.val()) / 3.28084 );
    });

    input_csa.on("input", function () {
        console.log('on input_csa change.');
        input_csa_en.val(parseFloat(input_csa.val()) * 2.47105 );
    });

    input_csa_en.on("input", function () {
        console.log('on input_csa_en change.');
        input_csa.val(parseFloat(input_csa_en.val()) / 2.47105 );
    });

    $("#btn_build_channels").click(channel_ctrl.build_router);
    $("#btn_build_channels_en").click(channel_ctrl.build_router);

    //
    // Channel Event Handling
    //
    channel_ctrl.form.on("FETCH_TASK_COMPLETED", function () {
        // Build the channels when the dem has been obtained
        setTimeout(channel_ctrl.build, 2000);
    });

    channel_ctrl.form.on("BUILD_CHANNELS_TASK_COMPLETED", function () {
        // Show the results on the map and build a report
        channel_ctrl.show();
        channel_ctrl.report();
    });

    // load the hidden inputs on channel form
    channel_ctrl.onMapChange();

    //
    // Initial Configuration
    //
    channel_ctrl.zoom_min = {{ topaz.zoom_min }};
    if ({{ topaz.has_channels | tojson }}) {
        channel_ctrl.report();
    }
    if ({{ topaz.has_channels | tojson }} && !({{ topaz.has_subcatchments | tojson }})) {
       channel_ctrl.show();
    }

    /*
     * Outlet Initialization
     * =====================
     */

    //
    // Bindings
    //
    // Bind Use Cursor button to the setCursorSelection
    $("#btn_setoutlet_cursor").click(function () {
        outlet.setCursorSelection(!outlet.cursorSelectionOn);
    });

    // Text Entry Control
    $("#btn_setoutlet_entry").click(function () {
        var loc = $("#input_setoutlet_entry").val().split(",");
        var lng = parseFloat(loc[0]);
        var lat = parseFloat(loc[1]);
        var ev = { latlng: L.latLng(lat, lng) };
        outlet.put(ev);
    });

    // Bind radio to the set outlet mode on change
    $("[name='setoutlet_mode']").change(function () {
        var mode = parseInt($("input[name='setoutlet_mode']:checked").val(), 10);
        outlet.setMode(mode);
    });

    //
    // Outlet Event Bindings
    //
    outlet.form.on("SETOUTLET_TASK_COMPLETED", function () {
        outlet.popup.remove();
        outlet.show();
    });

    // Load outlet from server
    if ({{ topaz.has_outlet | tojson }}) {
        outlet.form.trigger("SETOUTLET_TASK_COMPLETED");
    }

    /*
     * Subcatchment Initialization
     * ===========================
     */

    // bind Build button to the controller
    $("#btn_build_subcatchments").click(sub_ctrl.build);

    // Bind radio to change subcatchment appearance
    // radios live in the map.htm template
    $("[name='sub_cmap_radio']").change(function () {
        sub_ctrl.setColorMap($("input[name='sub_cmap_radio']:checked").val());
    });

    {% if 'rhem' not in ron.mods %}
    // Bind radio to change subcatchment appearance
    // radios live in the map.htm template
    $("[name='wepp_sub_cmap_radio']").change(function () {
        sub_ctrl.setColorMap($("input[name='wepp_sub_cmap_radio']:checked").val());
    });
    {% else %}
    // Bind radio to change subcatchment appearance
    // radios live in the map.htm template
    $("[name='rhem_sub_cmap_radio']").change(function () {
        sub_ctrl.setColorMap($("input[name='rhem_sub_cmap_radio']:checked").val());
    });
    {% endif %}

    //
    // Subcatchment Event Bindings
    //
    sub_ctrl.form.on("BUILD_SUBCATCHMENTS_TASK_COMPLETED", function () {
        sub_ctrl.show();
        channel_ctrl.show();
        setTimeout(sub_ctrl.abstract_watershed, 2000);
    });

    sub_ctrl.form.on("WATERSHED_ABSTRACTION_TASK_COMPLETED", function () {
        setTimeout(sub_ctrl.report, 1500);
        sub_ctrl.enableColorMap("slp_asp");
        wepp.updatePhosphorus();
    });

    //
    // Hillslopes Visualizations
    {% if 'rhem' not in ron.mods %}
        // Phosphorus
        render_legend("viridis", "wepp_sub_cmap_canvas_phosphorus");
        sub_ctrl.renderPhosphorus();
        $('#wepp_sub_cmap_range_phosphorus').on('input', function () {
            sub_ctrl.renderPhosphorus();
        });

        // Runoff
        render_legend("winter", "wepp_sub_cmap_canvas_runoff");
        sub_ctrl.renderRunoff();
        $('#wepp_sub_cmap_range_runoff').on('input', function () {
            sub_ctrl.renderRunoff();
        });

        // Loss
        render_legend("electric", "wepp_sub_cmap_canvas_loss");
        sub_ctrl.renderLoss();
        $('#wepp_sub_cmap_range_loss').on('input', function () {
            sub_ctrl.renderLoss();
        });


        //
        // Gridded

        // Soil Deposition / Loss
        render_legend("electric", "wepp_grd_cmap_canvas_loss");
        sub_ctrl.updateGriddedLoss();

        $('#wepp_grd_cmap_range_loss').on('input', function () {
            sub_ctrl.updateGriddedLoss();
        });
    {% else %}

        // Runoff
        render_legend("winter", "rhem_sub_cmap_canvas_runoff");
        sub_ctrl.renderRunoff();
        $('#rhem_sub_cmap_range_runoff').on('input', function () {
            sub_ctrl.renderRhemRunoff();
        });

        // Yield
        render_legend("viridis", "rhem_sub_cmap_canvas_sed_yield");
        sub_ctrl.renderPhosphorus();
        $('#rhem_sub_cmap_range_yield').on('input', function () {
            sub_ctrl.renderRhemSedYield();
        });

        // Loss
        render_legend("electric", "rhem_sub_cmap_canvas_soil_loss");
        sub_ctrl.renderLoss();
        $('#rhem_sub_cmap_range_loss').on('input', function () {
            sub_ctrl.renderRhemSoilLoss();
        });
    {% endif %}

    // load subcatchments
    if ({{ topaz.has_subcatchments | tojson }}) {
        sub_ctrl.show();
        sub_ctrl.report();
        channel_ctrl.show();
        sub_ctrl.enableColorMap("slp_asp");
    }

    {% if 'rangeland_cover' in ron.mods %}
    /*
     * Rangeland Cover Initialization
     * ===============================
     */

    var rangeland_cover = RangelandCover.getInstance();
    rangeland_cover.hideStacktrace();

    //
    // Bindings
    //
    $("[name='rangeland_cover_mode']").change(function () {
        rangeland_cover.setMode();
    });

    $("#rangeland_cover_single_selection").on("change", function () {
        rangeland_cover.setMode();
    });

    $("#btn_build_rangeland_cover").click(rangeland_cover.build);

    //
    // Rangeland Cover Event Bindings
    //
    rangeland_cover.form.on("RANGELAND_COVER_BUILD_TASK_COMPLETED", function () {
        rangeland_cover.report();
    });
    {% endif %}

    /*
     * Landuse Initialization
     * ======================
     */

    //
    // Bindings
    //
    $("[name='landuse_mode']").change(function () {
        landuse.setMode();
    });

    $("#landuse_single_selection").on("change", function () {
        landuse.setMode();
    });

    $("#btn_build_landuse").click(landuse.build);

    //
    // Landuse Event Bindings
    //
    landuse.form.on("LANDUSE_BUILD_TASK_COMPLETED", function () {
        landuse.report();
        sub_ctrl.enableColorMap("dom_lc");
    });

    //
    // Initial Configuration
    //
    landuse.restore({{ landuse.mode | int }}, 0);

    $('#landuse_single_selection').val('{{ landuse.single_selection }}').prop('selected', true);

    // load landuse
    if ( {{ landuse.has_landuse | tojson }} ) {
        landuse.form.trigger("LANDUSE_BUILD_TASK_COMPLETED");
    }

    /*
     * Modify Landuse Initialization
     * ======================
     */

    //
    // Bindings
    //
    $("#checkbox_modify_landuse").on("change", function () {
        lc_modify.toggle();
    });

    $("#btn_modify_landuse").click(lc_modify.modify);

    lc_modify.form.on("LANDCOVER_MODIFY_TASK_COMPLETED", function () {
        if (sub_ctrl.getCmapMode() === "dom_lc") {
            sub_ctrl.setColorMap("dom_lc");
        }
        landuse.report();
    });

    /*
     * Soil Initialization
     * ======================
     */

    //
    // Bindings
    //
    $("[name='soil_mode']").change(function () {
        soil.setMode();
    });

    $("#soil_single_selection").on("input", function () {
        soil.setMode();
    });

    $("#soil_single_dbselection").on("change", function () {
        soil.setMode();
    });

    $("#btn_build_soil").click(soil.build);

    //
    // Subcatchment Event Bindings
    //
    soil.form.on("SOIL_BUILD_TASK_COMPLETED", function () {
        soil.report();
        sub_ctrl.enableColorMap("dom_soil");
    });

    //
    // Initial Configuration
    //
    soil.restore({{ soils.mode | int }});

    if ({{ (soils.single_dbselection != none) | tojson }})
    {
        $('#soil_single_dbselection').val('{{ soils.single_dbselection }}').prop('selected', true);
    }
    // load soil
    if ( {{ soils.has_soils | tojson }} ) {
        soil.form.trigger("SOIL_BUILD_TASK_COMPLETED");
        sub_ctrl.enableColorMap("dom_soil");
    }

    /*
     * Climate Initialization
     * ======================
     */

    //
    // Bindings
    //
    $("[name='climate_mode']").change(function () {
        climate.setMode();
    });

    $("[name='climate_spatialmode']").change(function () {
        climate.setSpatialMode();
    });

    $("[name='climatestation_mode']").change(function () {
        climate.setStationMode();
    });

    $("#climate_station_selection").on("change", function () {
        climate.setStation();
    });

    $("#btn_build_climate").click(climate.build);

    $('#climate_par_link').click(function (e) {
        e.preventDefault();

        var station_id = $("#climate_station_selection").val();
        var url = "https://wepp1.nkn.uidaho.edu/webservices/cligen/fetchpar/" + station_id;
        var win = window.open(url, '_blank');
        if (win) {
            win.focus();
        }

        return false;
    });

    //
    // Climate Event Bindings
    //
    climate.form.on("CLIMATE_SETSTATIONMODE_TASK_COMPLETED", function () {
        climate.refreshStationSelection();
        climate.viewStationMonthlies();
    });

    climate.form.on("CLIMATE_SETSTATION_TASK_COMPLETED", function () {
        climate.viewStationMonthlies();
    });

    climate.form.on("CLIMATE_BUILD_TASK_COMPLETED", function () {
        climate.report();
    });

    //
    // Initial Configuration
    //

    observed.hideControl();
    climate.showHideControls({{ climate.climate_mode | int }});
    // load climate
    if ( {{ climate.has_climate | tojson }} ) {
        climate.refreshStationSelection();
        climate.report();
        climate.viewStationMonthlies();
    }

    if ( {{ climate.has_observed | tojson }} ||
         {{ observed.results is not none | tojson }}) {
        observed.showControl();
    }

    /*
    * Wepp Initialization
    * ======================
    */

    //
    // Bindings
    //
    $("[name='wepp_mode']").change(function () {
        wepp.setMode();
    });

    $("#wepp_single_selection").on("change", function () {
        wepp.setMode();
    });

    $("#btn_run_wepp").click(wepp.run);

    wepp.form.on("WEPP_RUN_TASK_COMPLETED", function () {
        wepp.report();
        observed.onWeppRunCompleted();
    });

    {% if 'rhem' in ron.mods %}
    /*
    * Rhem Initialization
    * ======================
    */

    var rhem = Rhem.getInstance();
    rhem.hideStacktrace();

    //
    // Bindings
    //

    rhem.form.on("RHEM_RUN_TASK_COMPLETED", function () {
        rhem.report();
    });

    if ( {{ rhem.has_run | tojson }} ) {
        rhem.report();
    }

    {% endif %}

    //
    // Initial Configuration
    //
    // show report if wepp has run
    if ( {{ wepp.has_run | tojson }} ) {
        wepp.report();
    }

    // show report if wepp has run
    if ( {{ observed.has_results | tojson }} ) {
        observed.report();
    }

    // show report if ash model has run
    if ( {{ ron.has_ash_results | tojson }} ) {
        ash.report();
    }

    /*
     * Team Initialization
     * ======================
     */

    //
    // Bindings
    //
    $("#btn_adduser").click(team.adduser);

    team.form.on("TEAM_ADDUSER_TASK_COMPLETED", function () {
        team.report();
    });

    team.form.on("TEAM_REMOVEUSER_TASK_COMPLETED", function () {
        team.report();
    });

    // show report if wepp has run
    if ( {{ user.is_authenticated | tojson }} ) {
        team.report();
    }

    /*
     * Map Event Binding
     * =================
     */

    map.on("click", function (ev) {
        outlet.setClickHandler(ev);
        // add additional events here
    });

    map.on("zoom", function (ev) {
        map.onMapChange();
        channel_ctrl.onMapChange();
        // add additional events here
    });

    map.on("move", function (ev) {
        map.onMapChange();
        channel_ctrl.onMapChange();
        // add additional events here
    });

    project.set_readonly_controls({{ ron.readonly | tojson }});

    // konami code!
    Mousetrap.bind('up up down down left right left right b a', function() {
        $('#btnPuModal').click();
    });

    Mousetrap.bind('f8', function() {
        window.scrollTo(0, 0);
    });

});
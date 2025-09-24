"use strict";

var preflight_ws;
let lastPreflightChecklist = null;
let controller_lock_statuses = null;

// Map .nodb files to the UI elements we surface lock icons for.
// NOTE: if a new controller or PowerUser entry needs visual lock feedback,
// add the appropriate (lockImageId, puLockImageId) pair here so updateLocks
// can drive both the main controller button and the PowerUser resource icon.
const LOCKABLE_FILES = Object.freeze({
    "ron.nodb": { lockImageId: null, puLockImageId: "pu_ron_lock" },
    "topaz.nodb": { lockImageId: "build_channels_en_lock", puLockImageId: "pu_topaz_lock" },
    "watershed.nodb": { lockImageId: "build_subcatchments_lock", puLockImageId: "pu_watershed_lock" },
    "landuse.nodb": { lockImageId: "build_landuse_lock", puLockImageId: "pu_landuse_lock" },
    "shrubland.nodb": { lockImageId: null, puLockImageId: "pu_shrubland_lock" },
    "rangeland_cover.nodb": { lockImageId: null, puLockImageId: "pu_rangeland_cover_lock" },
    "soils.nodb": { lockImageId: "build_soil_lock", puLockImageId: "pu_soils_lock" },
    "climate.nodb": { lockImageId: "build_climate_lock", puLockImageId: "pu_climate_lock" },
    "treatments.nodb": { lockImageId: "build_treatments_lock", puLockImageId: null },
    "rhem.nodb": { lockImageId: null, puLockImageId: "pu_rhem_lock" },
    "rhempost.nodb": { lockImageId: null, puLockImageId: "pu_rhempost_lock" },
    "wepp.nodb": { lockImageId: "run_wepp_lock", puLockImageId: "pu_wepp_lock" },
    "wepppost.nodb": { lockImageId: "btn_export_dss_lock", puLockImageId: "pu_wepppost_lock" },
    "observed.nodb": { lockImageId: "run_observed_lock", puLockImageId: "pu_observed_lock" },
    "unitizer.nodb": { lockImageId: null, puLockImageId: "pu_unitizer_lock" },
    "baer.nodb": { lockImageId: null, puLockImageId: "pu_baer_lock" },
    "disturbed.nodb": { lockImageId: null, puLockImageId: "pu_disturbed_lock" },
    "rred.nodb": { lockImageId: null, puLockImageId: "pu_rred_lock" },
    "lt.nodb": { lockImageId: null, puLockImageId: "pu_lt_lock" },
    "ash.nodb": { lockImageId: "run_ash_lock", puLockImageId: "pu_ash_lock" },
    "ashpost.nodb": { lockImageId: "run_ash_lock", puLockImageId: "pu_ashpost_lock" },
    "debris_flow.nodb": { lockImageId: "run_debris_flow_lock", puLockImageId: "pu_debris_flow_lock" },
    "omni.nodb": { lockImageId: null, puLockImageId: "pu_omni_lock" }
});

function initPreflight(runid) {
    var wsUrl = `wss://${window.location.host}/weppcloud-microservices/preflight/${runid}`;

    function connectWebSocket() {
        preflight_ws = new WebSocket(wsUrl);

        preflight_ws.onopen = function() {
            $("#preflight_status").html("Connected");
            preflight_ws.send(JSON.stringify({"type": "init"}));
        };

        preflight_ws.onmessage = function(event) {
            var payload = JSON.parse(event.data);
            if (payload.type === "ping") {
                preflight_ws.send(JSON.stringify({"type": "pong"}));
            } else if (payload.type === "hangup") {
                preflight_ws.close();
                preflight_ws = null;
            } else if (payload.type === "preflight") {
                updateUI(payload.checklist);
                updateLocks(payload.lock_statuses);

                lastPreflightChecklist = payload.checklist;
                controller_lock_statuses = payload.lock_statuses;

            }
        };

        preflight_ws.onclose = function() {
            if (!document.hidden) { // Only reconnect if the page is visible
                $("#preflight_status").html("Preflight Connection Closed");
                setTimeout(connectWebSocket, 5000); // Try to reconnect every 5 seconds.
            }
        };
    }

    connectWebSocket(); // Initial connection setup

    // Handling visibility change
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            if (preflight_ws) {
                preflight_ws.close();
            }
        } else {
            connectWebSocket(); // Reconnect WebSocket when page is visible
        }
    });
}

function updateLocks(lockStatuses) {
    if (!lockStatuses || typeof lockStatuses !== "object") {
        return;
    }

    Object.entries(lockStatuses).forEach(([fileName, isLocked]) => {
        const target = LOCKABLE_FILES[fileName];
        if (!target) {
            return; // This .nodb file does not control a button directly.
        }

        const { lockImageId, puLockImageId } = target;
        const controllerLock = lockImageId ? document.getElementById(lockImageId) : null;
        const panelLock = puLockImageId ? document.getElementById(puLockImageId) : null;

        if (!controllerLock && !panelLock) {
            return;
        }

        const displayValue = isLocked ? 'inline' : 'none';

        if (controllerLock) {
            controllerLock.style.display = displayValue;
        }

        if (panelLock) {
            panelLock.style.display = displayValue;
        }
    });
}


function updateUI(checklist) {
    for (var key in checklist) {
        var selector = getSelectorForKey(key);
        if (readonly === true) {
            $(selector).removeClass('checked').removeClass('unchecked');
        } else if (checklist[key]) {
            $(selector).addClass('checked').removeClass('unchecked');
        } else {
            $(selector).addClass('unchecked').removeClass('checked');
        }
    }

    var selector = getSelectorForKey("sbs_map");
    if (checklist.sbs_map) {
        $(selector).addClass('burned').removeClass('unburned');
    } else {
        $(selector).addClass('unburned').removeClass('burned');
    }
}

// Map keys from the checklist to their corresponding CSS selectors
function getSelectorForKey(key) {
    var mapping = {
        "sbs_map": 'a[href^="#soil-burn-severity-optional"]',
        "channels": 'a[href="#channel-delineation"]',
        "outlet": 'a[href="#outlet"]',
        "subcatchments": 'a[href="#subcatchments-delineation"]',
        "landuse": 'a[href="#landuse-options"]',
        "soils": 'a[href="#soil-options"]',
        "climate": 'a[href="#climate-options"]',
        "rap_ts": 'a[href="#rap-time-series-acquisition"]',
        "wepp": 'a[href="#wepp"]',
        "observed": 'a[href="#observed-data-model-fit"]',
        "debris": 'a[href="#debris-flow-analysis"]',
        "watar": 'a[href="#wildfire-ash-transport-and-risk-watar"]',
        "dss_export": 'a[href="#partitioned-dss-export-for-hec"]'
    };

    return mapping[key];
}

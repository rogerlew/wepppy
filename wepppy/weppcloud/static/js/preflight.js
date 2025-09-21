"use strict";

var preflight_ws;
let lastPreflightChecklist = null;
let controller_lock_statuses = null;

// Map .nodb files to the UI elements we toggle via lockButton/unlockButton.
// NOTE: if a new controller needs to react to lock status pushes, add the
// appropriate (buttonId, lockImageId) pair here so updateLocks can drive it.
const LOCKABLE_FILES = Object.freeze({
    "wepp.nodb": { buttonId: "btn_run_wepp", lockImageId: "run_wepp_lock" },
    "topaz.nodb": { buttonId: "btn_build_channels_en", lockImageId: "build_channels_en_lock" },
    "watershed.nodb": { buttonId: "btn_build_subcatchments", lockImageId: "build_subcatchments_lock" },
    "landuse.nodb": { buttonId: "btn_build_landuse", lockImageId: "build_landuse_lock" },
    "soils.nodb": { buttonId: "btn_build_soil", lockImageId: "build_soil_lock" },
    "climate.nodb": { buttonId: "btn_build_climate", lockImageId: "build_climate_lock" },
    "treatments.nodb": { buttonId: "btn_build_treatments", lockImageId: "build_treatments_lock" },
    "wepppost.nodb": { buttonId: "btn_export_dss", lockImageId: "btn_export_dss_lock" },
    "observed.nodb": { buttonId: "btn_run_observed", lockImageId: "run_observed_lock" },
    "debris_flow.nodb": { buttonId: "btn_run_debris_flow", lockImageId: "run_debris_flow_lock" },
    "ash.nodb": { buttonId: "btn_run_ash", lockImageId: "run_ash_lock" },
    "ashpost.nodb": { buttonId: "btn_run_ash", lockImageId: "run_ash_lock" }
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

        const { buttonId, lockImageId } = target;
        const button = document.getElementById(buttonId);
        const lockImage = document.getElementById(lockImageId);

        // Some legacy views reuse button ids; skip gracefully if the elements
        // are not on the current page to avoid raising exceptions.
        if (!button || !lockImage) {
            return;
        }

        if (isLocked) {
            lockButton(buttonId, lockImageId);
        } else {
            unlockButton(buttonId, lockImageId);
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

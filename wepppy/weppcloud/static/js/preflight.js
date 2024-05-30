"use strict";

var preflight_ws;
let lastPreflightChecklist = null;
let controller_lock_statuses = null;

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
                //updateLocks(payload.lock_statuses);

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

function updateLock(btn_id, lock_id, lock_status) {
    var button = $("#" + btn_id);
    var lock = $("#" + lock_id);

    if (lock_status) {
        button.attr('disabled', true);
        lock.show();
    } else {
        button.attr('disabled', false);
        lock.hide();
    }
}

function updateLocks(lock_statuses) {
    
    updateLock("btn_build_landuse", "build_landuse_lock", lock_statuses.landuse);
    updateLock("btn_build_soil", "build_soil_lock", lock_statuses.soils);
    updateLock("btn_build_channels_en", "build_channels_en_lock", lock_statuses.watershed);
    updateLock("btn_build_subcatchments", "build_subcatchments_lock", lock_statuses.watershed);
    updateLock("btn_build_climate", "build_climate_lock", lock_statuses.climate);
    updateLock("btn_run_wepp", "run_wepp_lock", lock_statuses.wepp);
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
        "watar": 'a[href="#wildfire-ash-transport-and-risk-watar"]'
    };

    return mapping[key];
}


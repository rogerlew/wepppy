"use strict";

var preflight_ws;
let lastPreflightChecklist = null;
let controller_lock_statuses = null;
window.lastPreflightChecklist = lastPreflightChecklist;

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
                preflight_ws.close(1000, "server hangup");
                preflight_ws = null;
            } else if (payload.type === "preflight") {
                updateUI(payload.checklist);
                updateLocks(payload.lock_statuses);

                lastPreflightChecklist = payload.checklist;
                window.lastPreflightChecklist = payload.checklist;
                controller_lock_statuses = payload.lock_statuses;

            }
        };

        preflight_ws.onclose = function(event) {
            console.log(
                "Preflight websocket closed",
                "code:", event && event.code,
                "reason:", event && event.reason,
                "wasClean:", event && event.wasClean
            );
            preflight_ws = null;
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
                preflight_ws.close(1000, "document hidden");
                preflight_ws = null;
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
    var readonly = typeof window.readonly !== 'undefined' ? window.readonly : false;
    
    for (var key in checklist) {
        if (!Object.prototype.hasOwnProperty.call(checklist, key)) {
            continue;
        }
        var selector = getSelectorForKey(key);
        if (!selector || key === "sbs_map") {
            continue;
        }
        var isComplete = readonly === true ? false : Boolean(checklist[key]);
        setTocEmojiState(selector, isComplete);
    }

    var selector = getSelectorForKey("sbs_map");
    if (!selector) {
        return;
    }

    if (readonly === true) {
        $(selector).removeClass('burned').removeClass('unburned');
        setTocEmojiState(selector, false);
    } else {
        setTocEmojiState(selector, Boolean(checklist.sbs_map));
        if (checklist.sbs_map) {
            $(selector).addClass('burned').removeClass('unburned');
        } else {
            $(selector).addClass('unburned').removeClass('burned');
        }
    }
}

// Map keys from the checklist to their corresponding CSS selectors
function getSelectorForKey(key) {
    var mapping = {
        "sbs_map": 'a[href^="#soil-burn-severity-optional"]',
        "channels": 'a[href="#channel-delineation"]',
        "outlet": 'a[href="#outlet"]',
        "subcatchments": 'a[href="#subcatchments-delineation"]',
        "landuse": 'a[href="#landuse-options"], a[href="#landuse"]',
        "soils": 'a[href="#soil-options"], a[href="#soils"]',
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

function setTocEmojiState(selector, isComplete) {
    if (!selector) {
        return;
    }
    var $targets = $(selector);
    if (!$targets.length) {
        return;
    }

    $targets.each(function () {
        var anchor = this;
        if (!anchor || anchor.nodeType !== 1) {
            return;
        }

        if (anchor.classList) {
            anchor.classList.remove('checked');
            anchor.classList.remove('unchecked');
        } else {
            $(anchor).removeClass('checked unchecked');
        }

        var href = anchor.getAttribute('href');
        var emoji = anchor.getAttribute('data-toc-emoji-value');

        if (!emoji && anchor.dataset && anchor.dataset.tocEmojiValue) {
            emoji = anchor.dataset.tocEmojiValue;
        }

        if (!emoji && window.tocTaskEmojis && href && window.tocTaskEmojis[href]) {
            emoji = window.tocTaskEmojis[href];
        }

        if (anchor.dataset) {
            anchor.dataset.tocEmojiValue = emoji || '';
            anchor.dataset.tocEmoji = isComplete && emoji ? emoji : '';
        }
        anchor.setAttribute('data-toc-emoji-value', emoji || '');
        anchor.setAttribute('data-toc-emoji', (isComplete && emoji) ? emoji : '');

        var originalText = anchor.getAttribute('data-original-text');
        if (!originalText && anchor.dataset && anchor.dataset.originalText) {
            originalText = anchor.dataset.originalText;
        }

        if (!originalText) {
            var current = (anchor.textContent || '').trim();
            if (emoji && current.indexOf(emoji) === 0) {
                current = current.slice(emoji.length).trim();
            }
            originalText = current;
        }

        anchor.setAttribute('data-original-text', originalText);
        if (anchor.dataset) {
            anchor.dataset.originalText = originalText;
        }
        if (anchor.textContent !== originalText) {
            anchor.textContent = originalText;
        }
    });
}

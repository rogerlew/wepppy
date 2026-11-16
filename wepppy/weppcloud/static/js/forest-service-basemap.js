/* Optional vector background. Deck owns the camera, input, and analysis layers. */
(function (global) {
    "use strict";
    var ROOT = "https://tiles.arcgis.com/tiles/gGHDlz6USftL5Pau/arcgis/rest/services/FSBasemap_20240617/VectorTileServer/";
    var STYLE = ROOT + "resources/styles/root.json";
    var ITEM = "https://www.arcgis.com/home/item.html?id=2e1593463c30495e9c802098527e3d1b";
    var assetRoot = new URL("../ui-lab/maplibre/", document.currentScript.src).href;
    var libraryPromise;

    function validateResource(value) {
        var url = new URL(value);
        if (url.protocol !== "https:" || url.origin !== "https://tiles.arcgis.com" ||
            !url.pathname.startsWith(new URL(ROOT).pathname) ||
            url.username || url.password || url.search || url.hash) {
            throw new Error("Unapproved Forest Service resource");
        }
        return url.href;
    }

    async function fetchResource(url, options) {
        var response = await fetch(validateResource(url), {
            signal: options.signal, credentials: "omit", referrerPolicy: "no-referrer", redirect: "error"
        });
        if (!response.ok) {
            throw new Error("Forest Service resource unavailable: " + response.status);
        }
        return options.json ? response.json() : response.arrayBuffer();
    }

    function prepareStyle(style) {
        if (style.version !== 8 || !style.sources || !Array.isArray(style.layers)) {
            throw new Error("Unsupported Forest Service style");
        }
        var sources = {};
        Object.keys(style.sources).forEach(function (key) {
            var source = style.sources[key];
            // The official ArcGIS source is not TileJSON. Use its fixed tile template;
            // never load remote attribution HTML or arbitrary source types/URLs.
            if (key !== "esri" || source.type !== "vector" ||
                validateResource(new URL(source.url, STYLE).href) !== ROOT) {
                throw new Error("Unsupported Forest Service source");
            }
            sources[key] = {
                type: "vector", tiles: [ROOT + "tile/{z}/{y}/{x}.pbf"],
                minzoom: source.minzoom, maxzoom: source.maxzoom,
                bounds: source.bounds, attribution: ""
            };
        });
        function resolve(value) {
            return validateResource(new URL(value, STYLE).href).replace(/%7B/g, "{").replace(/%7D/g, "}");
        }
        return { version: 8, sources: sources, layers: style.layers,
            glyphs: resolve(style.glyphs), sprite: resolve(style.sprite) };
    }

    function loadLibrary() {
        if (!libraryPromise) {
            libraryPromise = new Promise(function (resolve, reject) {
                var css = document.createElement("link");
                var script = document.createElement("script");
                var cssReady = false;
                var scriptReady = false;
                var settled = false;
                function fail() {
                    if (settled) { return; }
                    settled = true;
                    script.remove();
                    css.remove();
                    libraryPromise = null;
                    reject(new Error("Forest Service renderer unavailable"));
                }
                function ready() {
                    if (settled || !cssReady || !scriptReady) { return; }
                    var library = global.maplibregl;
                    // Asset initialization boundary: reject incompatible or incomplete builds visibly.
                    try {
                        if (!library || typeof library.Map !== "function" || typeof library.addProtocol !== "function") {
                            fail();
                            return;
                        }
                        library.addProtocol("wc-fs", async function (params, abortController) {
                            var data = await fetchResource(decodeURIComponent(params.url.slice(8)), {
                                signal: abortController.signal, json: params.type === "json"
                            });
                            return { data: data };
                        });
                    } catch (error) {
                        fail();
                        return;
                    }
                    settled = true;
                    resolve(library);
                }
                css.rel = "stylesheet";
                css.href = assetRoot + "maplibre-gl.css?v=5.24.1";
                css.onload = function () { cssReady = true; ready(); };
                css.onerror = fail;
                script.src = assetRoot + "maplibre-gl.js?v=5.24.1";
                script.onload = function () { scriptReady = true; ready(); };
                script.onerror = fail;
                document.head.append(css, script);
            });
        }
        return libraryPromise;
    }

    function create(options) {
        var target = options.target;
        var map = null;
        var host = null;
        var abort = null;
        var generation = 0;
        var view = null;
        var cameraKey = "";
        var disposed = false;
        var info = document.createElement("div");
        info.className = "wc-basemap-credit";
        Object.assign(info.style, { position: "absolute", bottom: "2px", left: "2px", zIndex: "5",
            maxWidth: "75%", padding: "3px 6px", background: "#fff", color: "#222", fontSize: "12px" });
        var credit = document.createElement("span");
        var status = document.createElement("span");
        status.setAttribute("role", "status");
        info.append(credit, status);
        target.appendChild(info);

        function setCredit(key) {
            credit.replaceChildren();
            var link = document.createElement("a");
            link.style.color = "#075985";
            link.rel = "noreferrer";
            if (key === "forestService") {
                link.href = ITEM;
                link.textContent = "USDA, U.S. Forest Service";
                credit.append(link, document.createTextNode(" · Forest Service - Geospatial Office"));
            } else if (key) {
                link.href = key === "osm" ? "https://www.openstreetmap.org/copyright" : "https://www.google.com/maps";
                link.textContent = key === "osm" ? "© OpenStreetMap contributors" : "© Google";
                credit.appendChild(link);
            }
        }

        function clear() {
            if (abort) { abort.abort(); abort = null; }
            if (map) { map.remove(); map = null; }
            if (host) { host.remove(); host = null; }
            cameraKey = "";
        }

        function syncView(nextView) {
            if (nextView) { view = nextView; }
            if (!map || !view) { return; }
            var key = [view.longitude, view.latitude, view.zoom, view.bearing, view.pitch,
                target.clientWidth, target.clientHeight].join(",");
            if (key === cameraKey) { return; }
            cameraKey = key;
            map.resize();
            map.jumpTo({ center: [view.longitude, view.latitude], zoom: view.zoom,
                bearing: view.bearing || 0, pitch: view.pitch || 0 });
        }

        async function select(key) {
            var current = ++generation;
            clear();
            setCredit(key === "forestService" ? null : key);
            status.textContent = "";
            if (key !== "forestService" || disposed) { return; }
            status.textContent = "Loading Forest Service basemap…";
            abort = new AbortController();
            var signal = abort.signal;
            try {
                var results = await Promise.all([loadLibrary(), fetchResource(STYLE, { signal: signal, json: true })]);
                if (current !== generation || disposed) { return; }
                var style = prepareStyle(results[1]);
                host = document.createElement("div");
                host.setAttribute("aria-hidden", "true");
                Object.assign(host.style, { position: "absolute", inset: "0", pointerEvents: "none" });
                target.prepend(host);
                map = new results[0].Map({ container: host, style: style, interactive: false,
                    attributionControl: false, canvasContextAttributes: { preserveDrawingBuffer: false },
                    transformRequest: function (url) {
                        return { url: "wc-fs://" + encodeURIComponent(validateResource(url)) };
                    }
                });
                var failed = false;
                var selectedMap = map;
                map.once("style.load", function () {
                    selectedMap.once("render", function () {
                        if (current === generation) { setCredit("forestService"); }
                    });
                });
                map.on("error", function () {
                    if (current !== generation) { return; }
                    failed = true;
                    status.textContent = " Forest Service basemap unavailable. Choose another basemap.";
                });
                map.on("idle", function () {
                    if (current !== generation) { return; }
                    setCredit("forestService");
                    if (!failed) { status.textContent = ""; }
                });
                syncView(view);
            } catch (error) {
                // Async UI boundary: surface resource/renderer failures; stale selections are cancelled.
                if (current === generation && !disposed && !signal.aborted) {
                    status.textContent = "Forest Service basemap unavailable. Choose another basemap.";
                }
            }
        }

        function dispose(event) {
            if (event && event.persisted) { return; }
            disposed = true;
            generation += 1;
            clear();
            info.remove();
            global.removeEventListener("pagehide", dispose);
        }
        global.addEventListener("pagehide", dispose);
        return { select: select, syncView: syncView, dispose: dispose };
    }

    global.WCForestBasemap = { create: create, validateResource: validateResource,
        prepareStyle: prepareStyle, fetchResource: fetchResource };
})(window);

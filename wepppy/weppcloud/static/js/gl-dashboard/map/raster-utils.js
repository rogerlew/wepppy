/**
 * Raster helpers for gl-dashboard overlay detection.
 * Handles GeoTIFF loading, SBS images, and GDAL info fetches.
 */

/**
 * @typedef {Object} RasterUtilsDeps
 * @property {{ sitePrefix: string, runid: string, config: string, geoTiffUrl?: string }} ctx Run-scoped identifiers and optional GeoTIFF CDN override.
 * @property {() => { geoTiffLoader?: Promise<any> | null }} getState Read reactive state to reuse the GeoTIFF loader promise.
 * @property {(key: string, value: any) => void} setValue Write a single state key (geoTiffLoader cache).
 * @property {(v: number) => number[] | null} colorFn Fallback colormap function returning RGBA-ish array.
 */

/**
 * @typedef {Object} RasterUtils
 * @property {(path: string, colorMap?: Object | ((value: number) => number[] | string | null)) => Promise<{ canvas: HTMLCanvasElement, bounds: number[], values: any, width: number, height: number, sampleMode: string }>} loadRaster Fetch and render a GeoTIFF to canvas with optional colormap.
 * @property {(imgurl: string) => Promise<{ canvas: HTMLCanvasElement, width: number, height: number, values: Uint8ClampedArray, sampleMode: 'rgba' }>} loadSbsImage Load an SBS PNG/JPEG into a canvas and extract RGBA values.
 * @property {(path: string) => Promise<Object|null>} fetchGdalInfo Fetch GDAL info JSON for a raster path.
 */

function resolveGeoTiffGlobal() {
  if (typeof GeoTIFF !== 'undefined' && GeoTIFF && typeof GeoTIFF.fromArrayBuffer === 'function') {
    return GeoTIFF;
  }
  if (typeof geotiff !== 'undefined') {
    if (geotiff.GeoTIFF && typeof geotiff.GeoTIFF.fromArrayBuffer === 'function') {
      return geotiff.GeoTIFF;
    }
    if (geotiff.default && typeof geotiff.default.fromArrayBuffer === 'function') {
      return geotiff.default;
    }
  }
  return null;
}

/**
 * @param {RasterUtilsDeps} params
 * @returns {RasterUtils}
 */
export function createRasterUtils({ ctx, getState, setValue, colorFn }) {
  async function ensureGeoTiff() {
    const existing = resolveGeoTiffGlobal();
    if (existing) return existing;
    const cached = getState().geoTiffLoader;
    if (cached) return cached;

    const loader = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = ctx.geoTiffUrl || 'https://unpkg.com/geotiff@2.1.3/dist-browser/geotiff.js';
      script.async = true;
      script.onload = () => {
        const GT = resolveGeoTiffGlobal();
        if (GT) {
          resolve(GT);
        } else {
          reject(new Error('GeoTIFF global missing after script load'));
        }
      };
      script.onerror = () => reject(new Error('GeoTIFF script failed to load'));
      document.head.appendChild(script);
    });
    setValue('geoTiffLoader', loader);
    return loader;
  }

  async function loadSbsImage(imgurl) {
    const imgResp = await fetch(imgurl);
    if (!imgResp.ok) {
      throw new Error(`SBS image fetch failed: ${imgResp.status}`);
    }
    const blob = await imgResp.blob();
    const bitmap = await createImageBitmap(blob);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx2d = canvas.getContext('2d');
    ctx2d.drawImage(bitmap, 0, 0);
    const imgData = ctx2d.getImageData(0, 0, canvas.width, canvas.height);
    return {
      canvas,
      width: canvas.width,
      height: canvas.height,
      values: imgData.data,
      sampleMode: 'rgba',
    };
  }

  async function fetchGdalInfo(path) {
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/gdalinfo/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) return null;
    return resp.json();
  }

  function normalizeColorEntry(entry, alpha = 230) {
    if (!entry) return null;
    if (Array.isArray(entry)) {
      const [r, g, b, a] = entry;
      if ([r, g, b].every((v) => Number.isFinite(v))) {
        const finalA = Number.isFinite(a) ? a : alpha;
        return [r, g, b, finalA];
      }
    } else if (typeof entry === 'string') {
      const match = /^#?([0-9a-f]{6})$/i.exec(entry.trim());
      if (match) {
        const intVal = parseInt(match[1], 16);
        return [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255, alpha];
      }
    }
    return null;
  }

  function colorize(values, width, height, colorMap) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx2d = canvas.getContext('2d');
    const imgData = ctx2d.createImageData(width, height);
    const mapEntries =
      colorMap &&
      typeof colorMap !== 'function' &&
      Object.entries(colorMap).reduce((acc, [k, hex]) => {
        const v = Number(k);
        if (!Number.isFinite(v)) return acc;
        const parsed = /^#?([0-9a-f]{6})$/i.exec(hex || '');
        if (!parsed) return acc;
        const intVal = parseInt(parsed[1], 16);
        acc[v] = [(intVal >> 16) & 255, (intVal >> 8) & 255, intVal & 255];
        return acc;
      }, {});
    const fnCache = new Map();

    if (mapEntries && Object.keys(mapEntries).length) {
      for (let i = 0, j = 0; i < values.length; i++, j += 4) {
        const v = values[i];
        const rgb = mapEntries[v];
        const color = rgb || [128, 128, 128];
        imgData.data[j] = color[0];
        imgData.data[j + 1] = color[1];
        imgData.data[j + 2] = color[2];
        imgData.data[j + 3] = 230;
      }
    } else {
      for (let i = 0, j = 0; i < values.length; i++, j += 4) {
        const v = values[i];
        let color = [180, 180, 180, 230];
        if (Number.isFinite(v)) {
          if (typeof colorMap === 'function') {
            const mapped = colorMap(v);
            const rgba = normalizeColorEntry(mapped, 230);
            if (rgba) {
              color = rgba;
            }
          } else {
            let fn = fnCache.get(colorMap);
            if (!fn) {
              fn = colorMap ? colorMap : colorFn;
              fnCache.set(colorMap, fn);
            }
            const mapped = typeof fn === 'function' ? fn((v - 1) / 255) : null;
            color = mapped || color;
          }
        }
        imgData.data[j] = color[0];
        imgData.data[j + 1] = color[1];
        imgData.data[j + 2] = color[2];
        imgData.data[j + 3] = color[3] || 230;
      }
    }
    ctx2d.putImageData(imgData, 0, 0);
    return canvas;
  }

  async function loadRaster(path, colorMap) {
    const GT = await ensureGeoTiff();
    const url = `${ctx.sitePrefix}/runs/${ctx.runid}/${ctx.config}/browse/${path}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`Raster fetch failed ${resp.status}: ${url}`);
    }
    const arrayBuffer = await resp.arrayBuffer();
    const tiff = await GT.fromArrayBuffer(arrayBuffer);
    const image = await tiff.getImage();
    const width = image.getWidth();
    const height = image.getHeight();
    const raster = await image.readRasters({ interleave: true, samples: [0] });
    const values = ArrayBuffer.isView(raster) ? raster : raster[0];
    const canvas = colorize(values, width, height, colorMap);
    const bounds = image.getBoundingBox();
    return {
      canvas,
      bounds,
      values,
      width,
      height,
      sampleMode: colorMap ? 'palette' : 'scalar',
    };
  }

  return { loadRaster, loadSbsImage, fetchGdalInfo };
}

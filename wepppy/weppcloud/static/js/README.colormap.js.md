# colormap.js

> Standalone colormap utility for WEPPcloud choropleth rendering and legend generation.

**See also:** [controllers_js/README.md](../../../controllers_js/README.md) for controller architecture, [AGENTS.md](/workdir/wepppy/AGENTS.md) for project conventions.

## Overview

`colormap.js` provides a pure JavaScript colormap generator based on Ben Postlethwaite's MIT-licensed implementation. It creates color lookup tables from named palettes, with a convenient `.map(v)` method for mapping normalized values (0–1) to colors.

**Key Features:**
- 40+ built-in color scales (scientific, perceptual, and diverging)
- Configurable output formats: hex, rgba string, or float arrays
- Linear interpolation between control points
- Clamping to valid range (values outside 0–1 map to endpoints)
- Independent of Plotty—controllers call `createColormap()` directly

## Quick Start

```javascript
// Create a 64-shade viridis mapper
var cmap = createColormap({ colormap: "viridis", nshades: 64 });

// Map a normalized value to a hex color
var color = cmap.map(0.5);  // "#21918d"

// Map out-of-range values (clamps automatically)
cmap.map(-0.5);  // "#440154" (min)
cmap.map(1.5);   // "#fde725" (max)
```

## API Reference

### `createColormap(spec)`

Creates a color lookup array with an attached `.map(v)` method.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `spec.colormap` | `string` or `Array` | `"jet"` | Named colorscale or custom control points |
| `spec.nshades` | `number` | `256` | Number of discrete colors in the palette |
| `spec.format` | `string` | `"hex"` | Output format: `"hex"`, `"rgbaString"`, or `"float"` |
| `spec.alpha` | `number` or `[number, number]` | `[1, 1]` | Alpha range (start, end) for gradient opacity |

**Returns:** `Array` of colors with attached `.map(v)` method.

### `.map(v)`

Maps a normalized value to a color from the palette.

| Parameter | Type | Description |
|-----------|------|-------------|
| `v` | `number` | Value in range 0–1 (clamped if outside) |

**Returns:** Color in the format specified during creation.

## Output Formats

```javascript
// Hex (default) - for CSS, canvas strokeStyle/fillStyle
createColormap({ colormap: "viridis", format: "hex" });
// Returns: ["#440154", "#440255", ..., "#fde725"]

// RGBA string - for CSS rgba() values
createColormap({ colormap: "viridis", format: "rgbaString" });
// Returns: ["rgba(68,1,84,1)", ..., "rgba(253,231,37,1)"]

// Float - for WebGL shaders (0–1 normalized RGB + alpha)
createColormap({ colormap: "viridis", format: "float" });
// Returns: [[0.267, 0.004, 0.329, 1], ..., [0.992, 0.906, 0.145, 1]]
```

## Available Color Scales

### Perceptually Uniform (Recommended)

| Name | Description | Best For |
|------|-------------|----------|
| `viridis` | Purple → green → yellow | General scientific data |
| `inferno` | Black → red → yellow → white | High contrast, dark backgrounds |
| `magma` | Black → pink → cream | Similar to inferno, softer tones |
| `plasma` | Blue → purple → orange → yellow | Vivid color progression |

### Sequential

| Name | Description | Best For |
|------|-------------|----------|
| `jet2` | Cyan → yellow → red (truncated jet) | Soil loss, erosion data |
| `winter` | Blue → green | Runoff, water-related measures |
| `hot` | Black → red → yellow → white | Temperature, intensity |
| `greens` | Dark green → light green | Vegetation, cover data |
| `greys` | Black → white | Grayscale overlays |

### Diverging

| Name | Description | Best For |
|------|-------------|----------|
| `rdbu` | Blue → gray → red | Diverging from neutral |
| `bluered` | Blue → red | Simple diverging |
| `picnic` | Blue → white → red | Centered diverging |

### Oceanographic / Scientific

| Name | Description |
|------|-------------|
| `bathymetry` | Deep ocean depth |
| `chlorophyll` | Phytoplankton concentration |
| `density` | Water density |
| `oxygen` | Dissolved oxygen |
| `salinity` | Salt concentration |
| `temperature` | Thermal gradients |
| `turbidity` | Water clarity |
| `velocity-blue` | Current speed (blue) |
| `velocity-green` | Current speed (green) |

### Other

| Name | Description |
|------|-------------|
| `jet` | Full rainbow (legacy, avoid for new work) |
| `hsv` | Hue-saturation-value cycle |
| `rainbow` | Spectral rainbow |
| `rainbow-soft` | Muted rainbow |
| `cubehelix` | Monotonically increasing luminance |
| `electric` | Black → purple → orange → yellow |
| `electric-boogaloo` | Warm variant (brown → yellow) |
| `earth` | Blue → green → yellow → brown → white |
| `portland` | Blue → teal → yellow → orange → red |
| `blackbody` | Black → red → yellow → white → blue |
| `alpha` | Transparent → opaque white (for opacity gradients) |

## WEPPcloud Measures and Colormaps

The following table documents the measures displayed on WEPPcloud map views with their associated colormaps.

### Subcatchment Choropleths (WebGL/Glify)

| Measure | Colormap | Units | Controller Key | Description |
|---------|----------|-------|----------------|-------------|
| **Runoff** | `winter` | mm | `runoff` | WEPP-modeled average annual runoff per hillslope |
| **Soil Loss** | `jet2` | kg/ha | `loss` | WEPP-modeled sediment loss (erosion) |
| **Phosphorus** | `viridis` | kg/ha | `phosphorus` | Phosphorus export from hillslopes |
| **Ash Load** | `jet2` | tonne/ha | `ashLoad` | Wildfire ash load on subcatchments |
| **Ash Transport** | `jet2` | tonne/ha | `ashTransport` | Ash transport through watershed |
| **RHEM Runoff** | `winter` | mm | `rhemRunoff` | Rangeland runoff (RHEM model) |
| **RHEM Sediment Yield** | `viridis` | kg/ha | `rhemSedYield` | Rangeland sediment yield |
| **RHEM Soil Loss** | `jet2` | kg/ha | `rhemSoilLoss` | Rangeland soil loss |
| **Cover** | `viridis` | fraction (0–1) | `cover` | Vegetation cover fraction |

### Channel Coloring (Strahler Order)

Channels use a fixed 8-color palette indexed by Strahler stream order, not a continuous colormap:

```javascript
var palette = [
    "#8AE5FE",  // Order 1 (small tributaries)
    "#65C8FE",  // Order 2
    "#479EFF",  // Order 3
    "#306EFE",  // Order 4
    "#2500F4",  // Order 5
    "#6600cc",  // Order 6
    "#50006b",  // Order 7
    "#6b006b"   // Order 8+ (main channels)
];
```

### Grid Rasters (Plotty)

Raster tiles (e.g., soil loss grids) use **Plotty** for rendering, not this colormap module. Plotty has its own `colorscales` table with similar names but independent implementation. See `static/js/plotty.js`.

## Integration with Glify

WEPPcloud uses [Leaflet.glify](https://github.com/robertleeplummern/Leaflet.glify) for high-performance WebGL polygon rendering. The integration works as follows:

1. **Create mappers** during controller initialization:
   ```javascript
   state.colorMappers = {
       runoff: createColormap({ colormap: "winter", nshades: 64 }),
       loss: createColormap({ colormap: "jet2", nshades: 64 }),
       phosphorus: createColormap({ colormap: "viridis", nshades: 64 }),
       // ...
   };
   ```

2. **Define color factory** for feature styling:
   ```javascript
   function colorFnFactory() {
       return function (feature) {
           var value = feature.properties.value;
           var rangeMax = resolveRangeMax("loss");
           var hex = state.colorMappers.loss.map(value / rangeMax);
           return fromHex(hex, 0.9);  // Convert to RGBA array for WebGL
       };
   }
   ```

3. **Apply to Glify layer**:
   ```javascript
   L.glify.layer({
       geojson: subcatchments,
       glifyOptions: {
           color: colorFnFactory(),
           opacity: 0.5,
           border: true
       },
       paneName: "subcatchmentsGlPane"
   });
   ```

## Legend Rendering

Colormap legends are rendered to `<canvas>` elements using Plotty (not this module). The `render_legend()` function creates a horizontal gradient:

```javascript
// From outlet.js - uses Plotty for canvas rendering
function render_legend(cmap, canvasID) {
    var element = document.getElementById(canvasID);
    var width = element.width;
    var height = element.height;
    
    // Create gradient data (0→1 across width)
    var data = new Float32Array(width * height);
    for (var y = 0; y < height; y++) {
        for (var x = 0; x < width; x++) {
            data[y * width + x] = x / (width - 1);
        }
    }
    
    // Render using Plotty
    var plot = new plotty.plot({
        canvas: element,
        data: data,
        width: width,
        height: height,
        domain: [0, 1],
        colorScale: cmap
    });
    plot.render();
}
```

**Note:** The colormap names must match between `colormap.js` (for WebGL choropleths) and Plotty (for canvas legends). Both support the common scales: `viridis`, `jet2`, `winter`, etc.

## Custom Colormaps

Define custom scales using control point arrays:

```javascript
var customCmap = createColormap({
    colormap: [
        { index: 0.0, rgb: [255, 255, 255] },      // White at min
        { index: 0.5, rgb: [255, 200, 100] },      // Orange at midpoint
        { index: 1.0, rgb: [139, 69, 19] }         // Brown at max
    ],
    nshades: 64
});
```

Each control point needs:
- `index`: Position in 0–1 range
- `rgb`: Array of [R, G, B] values (0–255)
- Optional 4th element for alpha: `[R, G, B, A]` where A is 0–1

## Relationship to Plotty

| Aspect | colormap.js | Plotty |
|--------|-------------|--------|
| **Purpose** | WebGL polygon fills (Glify) | Raster tile rendering |
| **Rendering** | Returns colors for GL shaders | Renders directly to canvas |
| **Usage** | `createColormap().map(v)` | `new plotty.plot({...}).render()` |
| **Scales** | `colorScale` object | `colorscales` object |
| **File** | `static/js/colormap.js` | `static/js/plotty.js` |

Both modules define similar colorscale names and can be used together—colormap.js for choropleth features and Plotty for legend canvases and raster overlays.

## Credits

Original implementation by Ben Postlethwaite (January 2013), MIT License.
Adapted for WEPPcloud with custom scales (`jet2`, `electric-boogaloo`) and `.map()` convenience method.

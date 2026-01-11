# QR Code Generator - Agent Guide

This document provides guidance for AI agents and developers working with this ISO/IEC 18004:2024 compliant QR code generator.

## Project Structure

```
js-qrcode-cc/
├── index.html      # Main QR code generator with UI
├── tests.html      # Comprehensive test suite (49 tests)
└── .gitignore
```

## Implementation Overview

The QR code generator is implemented as a single JavaScript module (`QRCode`) embedded in `index.html`. It follows the complete encode procedure from ISO/IEC 18004:2024:

1. **Data Analysis** - Detect optimal encoding mode (Numeric, Alphanumeric, Byte)
2. **Data Encoding** - Convert input to bit stream with mode indicator and character count
3. **Error Correction** - Generate Reed-Solomon ECC codewords
4. **Structure Final Message** - Interleave data and ECC blocks
5. **Module Placement** - Place codewords in zigzag pattern with function patterns
6. **Data Masking** - Apply and evaluate 8 mask patterns, select best
7. **Format/Version Info** - Add format and version information

### Key Components

| Function | Location | Purpose |
|----------|----------|---------|
| `detectMode()` | Line ~772 | Determines Numeric/Alphanumeric/Byte mode |
| `encodeNumeric()` | Line ~801 | Encodes digits (10 bits per 3 digits) |
| `encodeAlphanumeric()` | Line ~833 | Encodes uppercase + special chars (11 bits per 2 chars) |
| `encodeByte()` | Line ~861 | Encodes UTF-8 bytes (8 bits each) |
| `calculateECC()` | Line ~737 | Reed-Solomon error correction |
| `generateRSPolynomial()` | Line ~721 | Creates RS generator polynomial |
| `buildFunctionPatterns()` | Line ~1195 | Places finder, timing, alignment patterns |
| `placeDataModules()` | Line ~1168 | Places data in zigzag pattern |
| `applyMask()` | Line ~1254 | Applies one of 8 mask patterns |
| `evaluateMask()` | Line ~1270 | Scores mask using 4 penalty rules |
| `placeFormatInfo()` | Line ~1381 | Places 15-bit format information |

### Important Constants

- `FORMAT_INFO[]` - Pre-computed format info with BCH encoding (line ~671)
- `VERSION_INFO[]` - Version info for versions 7+ (line ~661)
- `ECC_TABLE{}` - Block structure for all version/ECC combinations (line ~372)
- `ALIGNMENT_PATTERNS[]` - Alignment pattern positions per version (line ~616)

## Running Tests

Open `tests.html` in a browser or navigate to `/tests` on the dev server. The test suite includes:

- **Mode Detection** (5 tests) - Verifies correct mode selection
- **Numeric Encoding** (4 tests) - Tests digit encoding
- **Alphanumeric Encoding** (3 tests) - Tests uppercase/special char encoding
- **Byte Encoding** (3 tests) - Tests UTF-8 encoding
- **Error Correction** (3 tests) - Verifies Reed-Solomon calculation
- **Mask Patterns** (4 tests) - Tests mask formulas and evaluation
- **Format Information** (3 tests) - Verifies format info lookup
- **Version Information** (3 tests) - Verifies version info lookup
- **Alignment Patterns** (3 tests) - Tests alignment pattern positions
- **Integration** (7 tests) - End-to-end QR generation tests
- **Edge Cases** (7 tests) - Boundary conditions and error handling
- **Version Selection** (2 tests) - Capacity-based version selection
- **Rendering** (2 tests) - Canvas rendering tests

## Debugging QR Codes

If generated QR codes don't scan, check these common issues in order:

### 1. ECC Calculation
The Reed-Solomon ECC must use correct polynomial indexing:
```javascript
// CORRECT - ecc[j] aligns with generator[numEcc-1-j]
ecc[j] ^= gfMultiply(generator[numEcc - 1 - j], coef);

// WRONG - index mismatch causes invalid ECC
ecc[j] ^= gfMultiply(generator[j], coef);
```

### 2. Format Information Placement
Format info appears in two copies with specific bit ordering:
- **First copy** (around top-left finder): MSB first, D14 at position 0
- **Second copy**:
  - Bottom-left vertical: D0 at row n-1, ascending to D6
  - Top-right horizontal: D7 at column n-8, ascending to D14

### 3. Dark Module Position
The dark module is at `(4*version + 9, 8)` - that's row = 4V+9, column = 8.

### 4. Verify with ZXing
Test generated QR codes at https://zxing.org/w/decode.jspx

### 5. Debug with Browser Console
```javascript
const qr = QRCode.generate('TEST', 'M');
console.log('Version:', qr.version);
console.log('Mask:', qr.maskPattern);
console.log('Matrix:', qr.matrix);

// Check specific positions
console.log('Dark module:', qr.matrix[4*qr.version+9][8]); // Should be 1
console.log('Format info row 8:', qr.matrix[8].slice(0,9));
```

### 6. Compare ECC Against Reference
For "HELLO WORLD" with M-ECC, expected values:
- Data codewords: `20 5b 0b 78 d1 72 dc 4d 43 40 ec 11 ec 11 ec 11`
- ECC codewords: `c4 23 27 77 eb d7 e7 e2 5d 17`

## Reusing QR Generation in Other Pages

### Method 1: Extract the QRCode Module

Copy the `QRCode` IIFE (lines ~293-1559) to a separate file:

```javascript
// qrcode.js
const QRCode = (function() {
    'use strict';
    // ... entire module code ...
    return { generate, render };
})();
```

Then use in your page:
```html
<script src="qrcode.js"></script>
<script>
    const canvas = document.getElementById('myCanvas');
    const qrData = QRCode.generate('https://example.com', 'M');
    QRCode.render(canvas, qrData, 8); // 8px per module
</script>
```

### Method 2: ES Module Export

Convert to ES module:
```javascript
// qrcode.mjs
export function generate(data, eccLevel = 'M') { ... }
export function render(canvas, qrData, moduleSize = 8) { ... }
```

Import in your code:
```javascript
import { generate, render } from './qrcode.mjs';
```

### Method 3: Embed in iframe

```html
<iframe src="https://rogerlew.github.io/js-qrcode-cc/"
        width="400" height="600" frameborder="0"></iframe>
```

### API Reference

```javascript
// Generate QR code data
const qrData = QRCode.generate(data, eccLevel);
// - data: string to encode
// - eccLevel: 'L' | 'M' | 'Q' | 'H' (default: 'M')
// Returns: { matrix, version, size, eccLevel, maskPattern, mode, dataLength }

// Render to canvas
QRCode.render(canvas, qrData, moduleSize);
// - canvas: HTMLCanvasElement
// - qrData: object from generate()
// - moduleSize: pixels per module (default: 8)
```

### Programmatic Usage Example

```javascript
// Generate and download QR code
function downloadQRCode(text, filename = 'qrcode.png') {
    const canvas = document.createElement('canvas');
    const qrData = QRCode.generate(text, 'M');
    QRCode.render(canvas, qrData, 10);

    const link = document.createElement('a');
    link.download = filename;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

// Generate QR code as data URL
function getQRCodeDataURL(text, moduleSize = 8) {
    const canvas = document.createElement('canvas');
    const qrData = QRCode.generate(text, 'M');
    QRCode.render(canvas, qrData, moduleSize);
    return canvas.toDataURL('image/png');
}

// Use in an img tag
const img = document.createElement('img');
img.src = getQRCodeDataURL('https://example.com');
document.body.appendChild(img);
```

## Supported Features

- **Encoding Modes**: Numeric, Alphanumeric, Byte (UTF-8)
- **Versions**: 1-40 (21x21 to 177x177 modules)
- **Error Correction**: L (7%), M (15%), Q (25%), H (30%)
- **Mask Patterns**: All 8 patterns with automatic optimization
- **Character Sets**: Full Unicode via UTF-8 byte mode

## Limitations

- No Kanji mode support
- No ECI (Extended Channel Interpretation)
- No Structured Append (multi-QR sequences)
- No FNC1 mode (GS1 barcodes)

## References

- [ISO/IEC 18004:2024](https://www.iso.org/standard/62021.html) - QR Code specification
- [Thonky QR Code Tutorial](https://www.thonky.com/qr-code-tutorial/) - Excellent step-by-step guide
- [ZXing Decoder](https://zxing.org/w/decode.jspx) - Online QR code validator
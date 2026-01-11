/**
 * QR Code Generator - ISO/IEC 18004:2024 Compliant
 * https://github.com/rogerlew/js-qrcode-cc
 *
 * Usage:
 *   const qrData = QRCode.generate('https://example.com', 'M');
 *   QRCode.render(canvas, qrData, 8);
 */
const QRCode = (function() {
    'use strict';

    // ============================================================
    // CONSTANTS AND TABLES FROM ISO/IEC 18004:2024
    // ============================================================

    const ECC_LEVELS = { L: 0, M: 1, Q: 2, H: 3 };
    const ECC_INDICATORS = { L: 0b01, M: 0b00, Q: 0b11, H: 0b10 };

    const MODE = {
        NUMERIC: 0b0001,
        ALPHANUMERIC: 0b0010,
        BYTE: 0b0100,
        KANJI: 0b1000,
        TERMINATOR: 0b0000
    };

    const ALPHANUMERIC_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:';

    const CHAR_COUNT_BITS = {
        NUMERIC: [10, 12, 14],
        ALPHANUMERIC: [9, 11, 13],
        BYTE: [8, 16, 16],
        KANJI: [8, 10, 12]
    };

    // Data capacity for each version and ECC level (Table 7)
    const BYTE_CAPACITY = [
        null,
        [17, 14, 11, 7], [32, 26, 20, 14], [53, 42, 32, 24], [78, 62, 46, 34],
        [106, 84, 60, 44], [134, 106, 74, 58], [154, 122, 86, 64], [192, 152, 108, 84],
        [230, 180, 130, 98], [271, 213, 151, 119], [321, 251, 177, 137], [367, 287, 203, 155],
        [425, 331, 241, 177], [458, 362, 258, 194], [520, 412, 292, 220], [586, 450, 322, 250],
        [644, 504, 364, 280], [718, 560, 394, 310], [792, 624, 442, 338], [858, 666, 482, 382],
        [929, 711, 509, 403], [1003, 779, 565, 439], [1091, 857, 611, 461], [1171, 911, 661, 511],
        [1273, 997, 715, 535], [1367, 1059, 751, 593], [1465, 1125, 805, 625], [1528, 1190, 868, 658],
        [1628, 1264, 908, 698], [1732, 1370, 982, 742], [1840, 1452, 1030, 790], [1952, 1538, 1112, 842],
        [2068, 1628, 1168, 898], [2188, 1722, 1228, 958], [2303, 1809, 1283, 983], [2431, 1911, 1351, 1051],
        [2563, 1989, 1423, 1093], [2699, 2099, 1499, 1139], [2809, 2213, 1579, 1219], [2953, 2331, 1663, 1273]
    ];

    // Error correction codewords per block (Table 9)
    const ECC_TABLE = {
        1: { L: { total: 26, eccPerBlock: 7, blocks: [[1, 19]] }, M: { total: 26, eccPerBlock: 10, blocks: [[1, 16]] }, Q: { total: 26, eccPerBlock: 13, blocks: [[1, 13]] }, H: { total: 26, eccPerBlock: 17, blocks: [[1, 9]] } },
        2: { L: { total: 44, eccPerBlock: 10, blocks: [[1, 34]] }, M: { total: 44, eccPerBlock: 16, blocks: [[1, 28]] }, Q: { total: 44, eccPerBlock: 22, blocks: [[1, 22]] }, H: { total: 44, eccPerBlock: 28, blocks: [[1, 16]] } },
        3: { L: { total: 70, eccPerBlock: 15, blocks: [[1, 55]] }, M: { total: 70, eccPerBlock: 26, blocks: [[1, 44]] }, Q: { total: 70, eccPerBlock: 18, blocks: [[2, 17]] }, H: { total: 70, eccPerBlock: 22, blocks: [[2, 13]] } },
        4: { L: { total: 100, eccPerBlock: 20, blocks: [[1, 80]] }, M: { total: 100, eccPerBlock: 18, blocks: [[2, 32]] }, Q: { total: 100, eccPerBlock: 26, blocks: [[2, 24]] }, H: { total: 100, eccPerBlock: 16, blocks: [[4, 9]] } },
        5: { L: { total: 134, eccPerBlock: 26, blocks: [[1, 108]] }, M: { total: 134, eccPerBlock: 24, blocks: [[2, 43]] }, Q: { total: 134, eccPerBlock: 18, blocks: [[2, 15], [2, 16]] }, H: { total: 134, eccPerBlock: 22, blocks: [[2, 11], [2, 12]] } },
        6: { L: { total: 172, eccPerBlock: 18, blocks: [[2, 68]] }, M: { total: 172, eccPerBlock: 16, blocks: [[4, 27]] }, Q: { total: 172, eccPerBlock: 24, blocks: [[4, 19]] }, H: { total: 172, eccPerBlock: 28, blocks: [[4, 15]] } },
        7: { L: { total: 196, eccPerBlock: 20, blocks: [[2, 78]] }, M: { total: 196, eccPerBlock: 18, blocks: [[4, 31]] }, Q: { total: 196, eccPerBlock: 18, blocks: [[2, 14], [4, 15]] }, H: { total: 196, eccPerBlock: 26, blocks: [[4, 13], [1, 14]] } },
        8: { L: { total: 242, eccPerBlock: 24, blocks: [[2, 97]] }, M: { total: 242, eccPerBlock: 22, blocks: [[2, 38], [2, 39]] }, Q: { total: 242, eccPerBlock: 22, blocks: [[4, 18], [2, 19]] }, H: { total: 242, eccPerBlock: 26, blocks: [[4, 14], [2, 15]] } },
        9: { L: { total: 292, eccPerBlock: 30, blocks: [[2, 116]] }, M: { total: 292, eccPerBlock: 22, blocks: [[3, 36], [2, 37]] }, Q: { total: 292, eccPerBlock: 20, blocks: [[4, 16], [4, 17]] }, H: { total: 292, eccPerBlock: 24, blocks: [[4, 12], [4, 13]] } },
        10: { L: { total: 346, eccPerBlock: 18, blocks: [[2, 68], [2, 69]] }, M: { total: 346, eccPerBlock: 26, blocks: [[4, 43], [1, 44]] }, Q: { total: 346, eccPerBlock: 24, blocks: [[6, 19], [2, 20]] }, H: { total: 346, eccPerBlock: 28, blocks: [[6, 15], [2, 16]] } },
        11: { L: { total: 404, eccPerBlock: 20, blocks: [[4, 81]] }, M: { total: 404, eccPerBlock: 30, blocks: [[1, 50], [4, 51]] }, Q: { total: 404, eccPerBlock: 28, blocks: [[4, 22], [4, 23]] }, H: { total: 404, eccPerBlock: 24, blocks: [[3, 12], [8, 13]] } },
        12: { L: { total: 466, eccPerBlock: 24, blocks: [[2, 92], [2, 93]] }, M: { total: 466, eccPerBlock: 22, blocks: [[6, 36], [2, 37]] }, Q: { total: 466, eccPerBlock: 26, blocks: [[4, 20], [6, 21]] }, H: { total: 466, eccPerBlock: 28, blocks: [[7, 14], [4, 15]] } },
        13: { L: { total: 532, eccPerBlock: 26, blocks: [[4, 107]] }, M: { total: 532, eccPerBlock: 22, blocks: [[8, 37], [1, 38]] }, Q: { total: 532, eccPerBlock: 24, blocks: [[8, 20], [4, 21]] }, H: { total: 532, eccPerBlock: 22, blocks: [[12, 11], [4, 12]] } },
        14: { L: { total: 581, eccPerBlock: 30, blocks: [[3, 115], [1, 116]] }, M: { total: 581, eccPerBlock: 24, blocks: [[4, 40], [5, 41]] }, Q: { total: 581, eccPerBlock: 20, blocks: [[11, 16], [5, 17]] }, H: { total: 581, eccPerBlock: 24, blocks: [[11, 12], [5, 13]] } },
        15: { L: { total: 655, eccPerBlock: 22, blocks: [[5, 87], [1, 88]] }, M: { total: 655, eccPerBlock: 24, blocks: [[5, 41], [5, 42]] }, Q: { total: 655, eccPerBlock: 30, blocks: [[5, 24], [7, 25]] }, H: { total: 655, eccPerBlock: 24, blocks: [[11, 12], [7, 13]] } },
        16: { L: { total: 733, eccPerBlock: 24, blocks: [[5, 98], [1, 99]] }, M: { total: 733, eccPerBlock: 28, blocks: [[7, 45], [3, 46]] }, Q: { total: 733, eccPerBlock: 24, blocks: [[15, 19], [2, 20]] }, H: { total: 733, eccPerBlock: 30, blocks: [[3, 15], [13, 16]] } },
        17: { L: { total: 815, eccPerBlock: 28, blocks: [[1, 107], [5, 108]] }, M: { total: 815, eccPerBlock: 28, blocks: [[10, 46], [1, 47]] }, Q: { total: 815, eccPerBlock: 28, blocks: [[1, 22], [15, 23]] }, H: { total: 815, eccPerBlock: 28, blocks: [[2, 14], [17, 15]] } },
        18: { L: { total: 901, eccPerBlock: 30, blocks: [[5, 120], [1, 121]] }, M: { total: 901, eccPerBlock: 26, blocks: [[9, 43], [4, 44]] }, Q: { total: 901, eccPerBlock: 28, blocks: [[17, 22], [1, 23]] }, H: { total: 901, eccPerBlock: 28, blocks: [[2, 14], [19, 15]] } },
        19: { L: { total: 991, eccPerBlock: 28, blocks: [[3, 113], [4, 114]] }, M: { total: 991, eccPerBlock: 26, blocks: [[3, 44], [11, 45]] }, Q: { total: 991, eccPerBlock: 26, blocks: [[17, 21], [4, 22]] }, H: { total: 991, eccPerBlock: 26, blocks: [[9, 13], [16, 14]] } },
        20: { L: { total: 1085, eccPerBlock: 28, blocks: [[3, 107], [5, 108]] }, M: { total: 1085, eccPerBlock: 26, blocks: [[3, 41], [13, 42]] }, Q: { total: 1085, eccPerBlock: 30, blocks: [[15, 24], [5, 25]] }, H: { total: 1085, eccPerBlock: 28, blocks: [[15, 15], [10, 16]] } },
        21: { L: { total: 1156, eccPerBlock: 28, blocks: [[4, 116], [4, 117]] }, M: { total: 1156, eccPerBlock: 26, blocks: [[17, 42]] }, Q: { total: 1156, eccPerBlock: 28, blocks: [[17, 22], [6, 23]] }, H: { total: 1156, eccPerBlock: 30, blocks: [[19, 16], [6, 17]] } },
        22: { L: { total: 1258, eccPerBlock: 28, blocks: [[2, 111], [7, 112]] }, M: { total: 1258, eccPerBlock: 28, blocks: [[17, 46]] }, Q: { total: 1258, eccPerBlock: 30, blocks: [[7, 24], [16, 25]] }, H: { total: 1258, eccPerBlock: 24, blocks: [[34, 13]] } },
        23: { L: { total: 1364, eccPerBlock: 30, blocks: [[4, 121], [5, 122]] }, M: { total: 1364, eccPerBlock: 28, blocks: [[4, 47], [14, 48]] }, Q: { total: 1364, eccPerBlock: 30, blocks: [[11, 24], [14, 25]] }, H: { total: 1364, eccPerBlock: 30, blocks: [[16, 15], [14, 16]] } },
        24: { L: { total: 1474, eccPerBlock: 30, blocks: [[6, 117], [4, 118]] }, M: { total: 1474, eccPerBlock: 28, blocks: [[6, 45], [14, 46]] }, Q: { total: 1474, eccPerBlock: 30, blocks: [[11, 24], [16, 25]] }, H: { total: 1474, eccPerBlock: 30, blocks: [[30, 16], [2, 17]] } },
        25: { L: { total: 1588, eccPerBlock: 26, blocks: [[8, 106], [4, 107]] }, M: { total: 1588, eccPerBlock: 28, blocks: [[8, 47], [13, 48]] }, Q: { total: 1588, eccPerBlock: 30, blocks: [[7, 24], [22, 25]] }, H: { total: 1588, eccPerBlock: 30, blocks: [[22, 15], [13, 16]] } },
        26: { L: { total: 1706, eccPerBlock: 28, blocks: [[10, 114], [2, 115]] }, M: { total: 1706, eccPerBlock: 28, blocks: [[19, 46], [4, 47]] }, Q: { total: 1706, eccPerBlock: 28, blocks: [[28, 22], [6, 23]] }, H: { total: 1706, eccPerBlock: 30, blocks: [[33, 16], [4, 17]] } },
        27: { L: { total: 1828, eccPerBlock: 30, blocks: [[8, 122], [4, 123]] }, M: { total: 1828, eccPerBlock: 28, blocks: [[22, 45], [3, 46]] }, Q: { total: 1828, eccPerBlock: 30, blocks: [[8, 23], [26, 24]] }, H: { total: 1828, eccPerBlock: 30, blocks: [[12, 15], [28, 16]] } },
        28: { L: { total: 1921, eccPerBlock: 30, blocks: [[3, 117], [10, 118]] }, M: { total: 1921, eccPerBlock: 28, blocks: [[3, 45], [23, 46]] }, Q: { total: 1921, eccPerBlock: 30, blocks: [[4, 24], [31, 25]] }, H: { total: 1921, eccPerBlock: 30, blocks: [[11, 15], [31, 16]] } },
        29: { L: { total: 2051, eccPerBlock: 30, blocks: [[7, 116], [7, 117]] }, M: { total: 2051, eccPerBlock: 28, blocks: [[21, 45], [7, 46]] }, Q: { total: 2051, eccPerBlock: 30, blocks: [[1, 23], [37, 24]] }, H: { total: 2051, eccPerBlock: 30, blocks: [[19, 15], [26, 16]] } },
        30: { L: { total: 2185, eccPerBlock: 30, blocks: [[5, 115], [10, 116]] }, M: { total: 2185, eccPerBlock: 28, blocks: [[19, 47], [10, 48]] }, Q: { total: 2185, eccPerBlock: 30, blocks: [[15, 24], [25, 25]] }, H: { total: 2185, eccPerBlock: 30, blocks: [[23, 15], [25, 16]] } },
        31: { L: { total: 2323, eccPerBlock: 30, blocks: [[13, 115], [3, 116]] }, M: { total: 2323, eccPerBlock: 28, blocks: [[2, 46], [29, 47]] }, Q: { total: 2323, eccPerBlock: 30, blocks: [[42, 24], [1, 25]] }, H: { total: 2323, eccPerBlock: 30, blocks: [[23, 15], [28, 16]] } },
        32: { L: { total: 2465, eccPerBlock: 30, blocks: [[17, 115]] }, M: { total: 2465, eccPerBlock: 28, blocks: [[10, 46], [23, 47]] }, Q: { total: 2465, eccPerBlock: 30, blocks: [[10, 24], [35, 25]] }, H: { total: 2465, eccPerBlock: 30, blocks: [[19, 15], [35, 16]] } },
        33: { L: { total: 2611, eccPerBlock: 30, blocks: [[17, 115], [1, 116]] }, M: { total: 2611, eccPerBlock: 28, blocks: [[14, 46], [21, 47]] }, Q: { total: 2611, eccPerBlock: 30, blocks: [[29, 24], [19, 25]] }, H: { total: 2611, eccPerBlock: 30, blocks: [[11, 15], [46, 16]] } },
        34: { L: { total: 2761, eccPerBlock: 30, blocks: [[13, 115], [6, 116]] }, M: { total: 2761, eccPerBlock: 28, blocks: [[14, 46], [23, 47]] }, Q: { total: 2761, eccPerBlock: 30, blocks: [[44, 24], [7, 25]] }, H: { total: 2761, eccPerBlock: 30, blocks: [[59, 16], [1, 17]] } },
        35: { L: { total: 2876, eccPerBlock: 30, blocks: [[12, 121], [7, 122]] }, M: { total: 2876, eccPerBlock: 28, blocks: [[12, 47], [26, 48]] }, Q: { total: 2876, eccPerBlock: 30, blocks: [[39, 24], [14, 25]] }, H: { total: 2876, eccPerBlock: 30, blocks: [[22, 15], [41, 16]] } },
        36: { L: { total: 3034, eccPerBlock: 30, blocks: [[6, 121], [14, 122]] }, M: { total: 3034, eccPerBlock: 28, blocks: [[6, 47], [34, 48]] }, Q: { total: 3034, eccPerBlock: 30, blocks: [[46, 24], [10, 25]] }, H: { total: 3034, eccPerBlock: 30, blocks: [[2, 15], [64, 16]] } },
        37: { L: { total: 3196, eccPerBlock: 30, blocks: [[17, 122], [4, 123]] }, M: { total: 3196, eccPerBlock: 28, blocks: [[29, 46], [14, 47]] }, Q: { total: 3196, eccPerBlock: 30, blocks: [[49, 24], [10, 25]] }, H: { total: 3196, eccPerBlock: 30, blocks: [[24, 15], [46, 16]] } },
        38: { L: { total: 3362, eccPerBlock: 30, blocks: [[4, 122], [18, 123]] }, M: { total: 3362, eccPerBlock: 28, blocks: [[13, 46], [32, 47]] }, Q: { total: 3362, eccPerBlock: 30, blocks: [[48, 24], [14, 25]] }, H: { total: 3362, eccPerBlock: 30, blocks: [[42, 15], [32, 16]] } },
        39: { L: { total: 3532, eccPerBlock: 30, blocks: [[20, 117], [4, 118]] }, M: { total: 3532, eccPerBlock: 28, blocks: [[40, 47], [7, 48]] }, Q: { total: 3532, eccPerBlock: 30, blocks: [[43, 24], [22, 25]] }, H: { total: 3532, eccPerBlock: 30, blocks: [[10, 15], [67, 16]] } },
        40: { L: { total: 3706, eccPerBlock: 30, blocks: [[19, 118], [6, 119]] }, M: { total: 3706, eccPerBlock: 28, blocks: [[18, 47], [31, 48]] }, Q: { total: 3706, eccPerBlock: 30, blocks: [[34, 24], [34, 25]] }, H: { total: 3706, eccPerBlock: 30, blocks: [[20, 15], [61, 16]] } }
    };

    // Alignment pattern positions (Table E.1)
    const ALIGNMENT_PATTERNS = [
        null, [],
        [6, 18], [6, 22], [6, 26], [6, 30], [6, 34],
        [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50], [6, 30, 54], [6, 32, 58], [6, 34, 62],
        [6, 26, 46, 66], [6, 26, 48, 70], [6, 26, 50, 74], [6, 30, 54, 78], [6, 30, 56, 82], [6, 30, 58, 86], [6, 34, 62, 90],
        [6, 28, 50, 72, 94], [6, 26, 50, 74, 98], [6, 30, 54, 78, 102], [6, 28, 54, 80, 106], [6, 32, 58, 84, 110], [6, 30, 58, 86, 114], [6, 34, 62, 90, 118],
        [6, 26, 50, 74, 98, 122], [6, 30, 54, 78, 102, 126], [6, 26, 52, 78, 104, 130], [6, 30, 56, 82, 108, 134], [6, 34, 60, 86, 112, 138], [6, 30, 58, 86, 114, 142], [6, 34, 62, 90, 118, 146],
        [6, 30, 54, 78, 102, 126, 150], [6, 24, 50, 76, 102, 128, 154], [6, 28, 54, 80, 106, 132, 158], [6, 32, 58, 84, 110, 136, 162], [6, 26, 54, 82, 110, 138, 166], [6, 30, 58, 86, 114, 142, 170]
    ];

    // Version information bit streams (Table D.1)
    const VERSION_INFO = [
        null, null, null, null, null, null, null,
        0x07C94, 0x085BC, 0x09A99, 0x0A4D3, 0x0BBF6, 0x0C762, 0x0D847, 0x0E60D, 0x0F928,
        0x10B78, 0x1145D, 0x12A17, 0x13532, 0x149A6, 0x15683, 0x168C9, 0x177EC,
        0x18EC4, 0x191E1, 0x1AFAB, 0x1B08E, 0x1CC1A, 0x1D33F, 0x1ED75, 0x1F250,
        0x209D5, 0x216F0, 0x228BA, 0x2379F, 0x24B0B, 0x2542E, 0x26A64, 0x27541, 0x28C69
    ];

    // Format information lookup table (Annex C)
    const FORMAT_INFO = [
        0x5412, 0x5125, 0x5E7C, 0x5B4B, 0x45F9, 0x40CE, 0x4F97, 0x4AA0,
        0x77C4, 0x72F3, 0x7DAA, 0x789D, 0x662F, 0x6318, 0x6C41, 0x6976,
        0x1689, 0x13BE, 0x1CE7, 0x19D0, 0x0762, 0x0255, 0x0D0C, 0x083B,
        0x355F, 0x3068, 0x3F31, 0x3A06, 0x24B4, 0x2183, 0x2EDA, 0x2BED
    ];

    // Remainder bits per version (Table 1)
    const REMAINDER_BITS = [
        0, 0, 7, 7, 7, 7, 7, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3, 3, 3, 3,
        4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0
    ];

    // ============================================================
    // GALOIS FIELD ARITHMETIC FOR REED-SOLOMON
    // ============================================================

    const GF_EXP = new Uint8Array(512);
    const GF_LOG = new Uint8Array(256);

    // Initialize lookup tables
    (function initGaloisField() {
        let x = 1;
        for (let i = 0; i < 255; i++) {
            GF_EXP[i] = x;
            GF_LOG[x] = i;
            x <<= 1;
            if (x & 0x100) {
                x ^= 0x11D; // primitive polynomial
            }
        }
        for (let i = 255; i < 512; i++) {
            GF_EXP[i] = GF_EXP[i - 255];
        }
    })();

    function gfMultiply(a, b) {
        if (a === 0 || b === 0) return 0;
        return GF_EXP[GF_LOG[a] + GF_LOG[b]];
    }

    function gfDivide(a, b) {
        if (b === 0) throw new Error('Division by zero');
        if (a === 0) return 0;
        return GF_EXP[(GF_LOG[a] + 255 - GF_LOG[b]) % 255];
    }

    // Generate Reed-Solomon generator polynomial
    function generateRSPolynomial(numEcc) {
        let poly = new Uint8Array(numEcc + 1);
        poly[0] = 1;

        for (let i = 0; i < numEcc; i++) {
            for (let j = numEcc; j > 0; j--) {
                poly[j] = poly[j - 1] ^ gfMultiply(poly[j], GF_EXP[i]);
            }
            poly[0] = gfMultiply(poly[0], GF_EXP[i]);
        }

        return poly;
    }

    // Calculate Reed-Solomon error correction codewords
    function calculateECC(data, numEcc) {
        const generator = generateRSPolynomial(numEcc);
        const ecc = new Uint8Array(numEcc);

        for (let i = 0; i < data.length; i++) {
            const coef = data[i] ^ ecc[0];
            for (let j = 0; j < numEcc - 1; j++) {
                ecc[j] = ecc[j + 1];
            }
            ecc[numEcc - 1] = 0;

            // ecc[j] represents coefficient of x^(numEcc-1-j)
            // generator[k] represents coefficient of x^k
            // So ecc[j] should be XORed with generator[numEcc-1-j]
            for (let j = 0; j < numEcc; j++) {
                ecc[j] ^= gfMultiply(generator[numEcc - 1 - j], coef);
            }
        }

        return ecc;
    }

    // ============================================================
    // MODE DETECTION AND DATA ENCODING
    // ============================================================

    function isNumeric(char) {
        const code = char.charCodeAt(0);
        return code >= 0x30 && code <= 0x39;
    }

    function isAlphanumeric(char) {
        return ALPHANUMERIC_CHARS.indexOf(char) !== -1;
    }

    function detectMode(data) {
        let allNumeric = true;
        let allAlphanumeric = true;

        for (let i = 0; i < data.length; i++) {
            const char = data[i];
            if (!isNumeric(char)) allNumeric = false;
            if (!isAlphanumeric(char)) allAlphanumeric = false;
        }

        if (allNumeric) return 'NUMERIC';
        if (allAlphanumeric) return 'ALPHANUMERIC';
        return 'BYTE';
    }

    function getCharCountBits(version, mode) {
        let index;
        if (version <= 9) index = 0;
        else if (version <= 26) index = 1;
        else index = 2;

        return CHAR_COUNT_BITS[mode][index];
    }

    function encodeNumeric(data) {
        const bits = [];
        let i = 0;

        while (i < data.length) {
            if (i + 3 <= data.length) {
                const num = parseInt(data.substr(i, 3), 10);
                for (let j = 9; j >= 0; j--) bits.push((num >> j) & 1);
                i += 3;
            } else if (i + 2 <= data.length) {
                const num = parseInt(data.substr(i, 2), 10);
                for (let j = 6; j >= 0; j--) bits.push((num >> j) & 1);
                i += 2;
            } else {
                const num = parseInt(data[i], 10);
                for (let j = 3; j >= 0; j--) bits.push((num >> j) & 1);
                i += 1;
            }
        }

        return bits;
    }

    function encodeAlphanumeric(data) {
        const bits = [];
        const upperData = data.toUpperCase();
        let i = 0;

        while (i < upperData.length) {
            if (i + 2 <= upperData.length) {
                const val1 = ALPHANUMERIC_CHARS.indexOf(upperData[i]);
                const val2 = ALPHANUMERIC_CHARS.indexOf(upperData[i + 1]);
                const num = val1 * 45 + val2;
                for (let j = 10; j >= 0; j--) bits.push((num >> j) & 1);
                i += 2;
            } else {
                const val = ALPHANUMERIC_CHARS.indexOf(upperData[i]);
                for (let j = 5; j >= 0; j--) bits.push((val >> j) & 1);
                i += 1;
            }
        }

        return bits;
    }

    function encodeByte(data) {
        const bits = [];
        const encoder = new TextEncoder();
        const bytes = encoder.encode(data);

        for (let i = 0; i < bytes.length; i++) {
            for (let j = 7; j >= 0; j--) {
                bits.push((bytes[i] >> j) & 1);
            }
        }

        return bits;
    }

    function selectVersion(dataLength, eccLevel, mode) {
        const eccIndex = ECC_LEVELS[eccLevel];

        for (let version = 1; version <= 40; version++) {
            const eccInfo = ECC_TABLE[version][eccLevel];
            let totalDataCodewords = 0;
            for (const [count, dataWords] of eccInfo.blocks) {
                totalDataCodewords += count * dataWords;
            }
            const totalDataBits = totalDataCodewords * 8;

            let requiredBits = 4; // Mode indicator
            requiredBits += getCharCountBits(version, mode);

            if (mode === 'NUMERIC') {
                const groups = Math.floor(dataLength / 3);
                const remainder = dataLength % 3;
                requiredBits += groups * 10;
                if (remainder === 2) requiredBits += 7;
                else if (remainder === 1) requiredBits += 4;
            } else if (mode === 'ALPHANUMERIC') {
                const pairs = Math.floor(dataLength / 2);
                const remainder = dataLength % 2;
                requiredBits += pairs * 11 + remainder * 6;
            } else {
                requiredBits += dataLength * 8;
            }

            if (requiredBits <= totalDataBits) {
                return version;
            }
        }

        return -1;
    }

    function createDataBitstream(data, version, eccLevel, mode) {
        const bits = [];

        // Mode indicator (4 bits)
        const modeIndicator = MODE[mode];
        for (let i = 3; i >= 0; i--) {
            bits.push((modeIndicator >> i) & 1);
        }

        // Character count indicator
        const countBits = getCharCountBits(version, mode);
        let charCount;
        if (mode === 'BYTE') {
            const encoder = new TextEncoder();
            charCount = encoder.encode(data).length;
        } else {
            charCount = data.length;
        }

        for (let i = countBits - 1; i >= 0; i--) {
            bits.push((charCount >> i) & 1);
        }

        // Data bits
        let dataBits;
        if (mode === 'NUMERIC') {
            dataBits = encodeNumeric(data);
        } else if (mode === 'ALPHANUMERIC') {
            dataBits = encodeAlphanumeric(data);
        } else {
            dataBits = encodeByte(data);
        }
        bits.push(...dataBits);

        // Get total data codewords
        const eccInfo = ECC_TABLE[version][eccLevel];
        let totalDataCodewords = 0;
        for (const [count, dataWords] of eccInfo.blocks) {
            totalDataCodewords += count * dataWords;
        }
        const totalDataBits = totalDataCodewords * 8;

        // Add terminator (up to 4 zero bits)
        const terminatorLength = Math.min(4, totalDataBits - bits.length);
        for (let i = 0; i < terminatorLength; i++) {
            bits.push(0);
        }

        // Pad to byte boundary
        while (bits.length % 8 !== 0) {
            bits.push(0);
        }

        // Add pad codewords (alternating 0xEC and 0x11)
        const padCodewords = [0xEC, 0x11];
        let padIndex = 0;
        while (bits.length < totalDataBits) {
            const pad = padCodewords[padIndex % 2];
            for (let i = 7; i >= 0; i--) {
                bits.push((pad >> i) & 1);
            }
            padIndex++;
        }

        return bits;
    }

    function bitsToCodewords(bits) {
        const codewords = [];
        for (let i = 0; i < bits.length; i += 8) {
            let value = 0;
            for (let j = 0; j < 8; j++) {
                value = (value << 1) | bits[i + j];
            }
            codewords.push(value);
        }
        return codewords;
    }

    // ============================================================
    // ERROR CORRECTION AND INTERLEAVING
    // ============================================================

    function generateErrorCorrection(dataCodewords, version, eccLevel) {
        const eccInfo = ECC_TABLE[version][eccLevel];
        const blocks = [];
        let dataIndex = 0;

        for (const [count, dataWords] of eccInfo.blocks) {
            for (let i = 0; i < count; i++) {
                const blockData = dataCodewords.slice(dataIndex, dataIndex + dataWords);
                const ecc = calculateECC(blockData, eccInfo.eccPerBlock);
                blocks.push({
                    data: Array.from(blockData),
                    ecc: Array.from(ecc)
                });
                dataIndex += dataWords;
            }
        }

        // Interleave data codewords
        const result = [];
        const maxDataLength = Math.max(...blocks.map(b => b.data.length));
        for (let i = 0; i < maxDataLength; i++) {
            for (const block of blocks) {
                if (i < block.data.length) {
                    result.push(block.data[i]);
                }
            }
        }

        // Interleave ECC codewords
        for (let i = 0; i < eccInfo.eccPerBlock; i++) {
            for (const block of blocks) {
                result.push(block.ecc[i]);
            }
        }

        return result;
    }

    // ============================================================
    // MATRIX CONSTRUCTION
    // ============================================================

    function createMatrix(version) {
        const size = version * 4 + 17;
        const matrix = [];
        const reserved = [];

        for (let i = 0; i < size; i++) {
            matrix[i] = new Array(size).fill(null);
            reserved[i] = new Array(size).fill(false);
        }

        return { matrix, reserved, size };
    }

    function placeFinderPattern(matrix, reserved, row, col) {
        for (let r = -1; r <= 7; r++) {
            for (let c = -1; c <= 7; c++) {
                const mr = row + r;
                const mc = col + c;

                if (mr < 0 || mr >= matrix.length || mc < 0 || mc >= matrix.length) {
                    continue;
                }

                if (r === -1 || r === 7 || c === -1 || c === 7) {
                    matrix[mr][mc] = 0;
                } else if (r === 0 || r === 6 || c === 0 || c === 6) {
                    matrix[mr][mc] = 1;
                } else if (r >= 2 && r <= 4 && c >= 2 && c <= 4) {
                    matrix[mr][mc] = 1;
                } else {
                    matrix[mr][mc] = 0;
                }
                reserved[mr][mc] = true;
            }
        }
    }

    function placeAlignmentPattern(matrix, reserved, centerRow, centerCol) {
        for (let r = -2; r <= 2; r++) {
            for (let c = -2; c <= 2; c++) {
                const mr = centerRow + r;
                const mc = centerCol + c;

                if (reserved[mr][mc]) continue;

                if (r === -2 || r === 2 || c === -2 || c === 2) {
                    matrix[mr][mc] = 1;
                } else if (r === 0 && c === 0) {
                    matrix[mr][mc] = 1;
                } else {
                    matrix[mr][mc] = 0;
                }
                reserved[mr][mc] = true;
            }
        }
    }

    function placeTimingPatterns(matrix, reserved, size) {
        for (let i = 8; i < size - 8; i++) {
            const bit = (i + 1) % 2;

            if (!reserved[6][i]) {
                matrix[6][i] = bit;
                reserved[6][i] = true;
            }

            if (!reserved[i][6]) {
                matrix[i][6] = bit;
                reserved[i][6] = true;
            }
        }
    }

    function placeDarkModule(matrix, reserved, version) {
        const row = 4 * version + 9;
        matrix[row][8] = 1;
        reserved[row][8] = true;
    }

    function reserveFormatInfo(matrix, reserved, size) {
        for (let i = 0; i < 9; i++) {
            if (!reserved[8][i]) reserved[8][i] = true;
            if (!reserved[i][8]) reserved[i][8] = true;
        }

        for (let i = 0; i < 8; i++) {
            if (!reserved[size - 1 - i][8]) reserved[size - 1 - i][8] = true;
        }

        for (let i = 0; i < 8; i++) {
            if (!reserved[8][size - 1 - i]) reserved[8][size - 1 - i] = true;
        }
    }

    function reserveVersionInfo(matrix, reserved, size, version) {
        if (version < 7) return;

        for (let i = 0; i < 6; i++) {
            for (let j = 0; j < 3; j++) {
                reserved[size - 11 + j][i] = true;
            }
        }

        for (let i = 0; i < 6; i++) {
            for (let j = 0; j < 3; j++) {
                reserved[i][size - 11 + j] = true;
            }
        }
    }

    function placeDataModules(matrix, reserved, size, data) {
        let dataIndex = 0;
        let upward = true;

        for (let col = size - 1; col > 0; col -= 2) {
            if (col === 6) col = 5;

            for (let row = 0; row < size; row++) {
                const actualRow = upward ? size - 1 - row : row;

                if (!reserved[actualRow][col] && dataIndex < data.length) {
                    matrix[actualRow][col] = data[dataIndex++];
                }

                if (col > 0 && !reserved[actualRow][col - 1] && dataIndex < data.length) {
                    matrix[actualRow][col - 1] = data[dataIndex++];
                }
            }

            upward = !upward;
        }
    }

    function buildFunctionPatterns(version) {
        const { matrix, reserved, size } = createMatrix(version);

        placeFinderPattern(matrix, reserved, 0, 0);
        placeFinderPattern(matrix, reserved, 0, size - 7);
        placeFinderPattern(matrix, reserved, size - 7, 0);

        if (version >= 2) {
            const positions = ALIGNMENT_PATTERNS[version];
            for (let i = 0; i < positions.length; i++) {
                for (let j = 0; j < positions.length; j++) {
                    const row = positions[i];
                    const col = positions[j];

                    if ((row < 9 && col < 9) ||
                        (row < 9 && col > size - 10) ||
                        (row > size - 10 && col < 9)) {
                        continue;
                    }

                    placeAlignmentPattern(matrix, reserved, row, col);
                }
            }
        }

        placeTimingPatterns(matrix, reserved, size);
        placeDarkModule(matrix, reserved, version);
        reserveFormatInfo(matrix, reserved, size);
        reserveVersionInfo(matrix, reserved, size, version);

        return { matrix, reserved, size };
    }

    // ============================================================
    // DATA MASKING
    // ============================================================

    const MASK_PATTERNS = [
        (i, j) => (i + j) % 2 === 0,
        (i, j) => i % 2 === 0,
        (i, j) => j % 3 === 0,
        (i, j) => (i + j) % 3 === 0,
        (i, j) => (Math.floor(i / 2) + Math.floor(j / 3)) % 2 === 0,
        (i, j) => ((i * j) % 2) + ((i * j) % 3) === 0,
        (i, j) => (((i * j) % 2) + ((i * j) % 3)) % 2 === 0,
        (i, j) => (((i + j) % 2) + ((i * j) % 3)) % 2 === 0
    ];

    function applyMask(matrix, reserved, size, maskPattern) {
        const masked = matrix.map(row => [...row]);
        const condition = MASK_PATTERNS[maskPattern];

        for (let i = 0; i < size; i++) {
            for (let j = 0; j < size; j++) {
                if (!reserved[i][j] && condition(i, j)) {
                    masked[i][j] ^= 1;
                }
            }
        }

        return masked;
    }

    function evaluateMask(matrix, size) {
        let penalty = 0;

        // Rule 1: Adjacent modules in row/column in same color
        for (let i = 0; i < size; i++) {
            let rowRun = 1;
            let colRun = 1;

            for (let j = 1; j < size; j++) {
                if (matrix[i][j] === matrix[i][j - 1]) {
                    rowRun++;
                } else {
                    if (rowRun >= 5) penalty += 3 + (rowRun - 5);
                    rowRun = 1;
                }

                if (matrix[j][i] === matrix[j - 1][i]) {
                    colRun++;
                } else {
                    if (colRun >= 5) penalty += 3 + (colRun - 5);
                    colRun = 1;
                }
            }

            if (rowRun >= 5) penalty += 3 + (rowRun - 5);
            if (colRun >= 5) penalty += 3 + (colRun - 5);
        }

        // Rule 2: Block of modules in same color (2x2)
        for (let i = 0; i < size - 1; i++) {
            for (let j = 0; j < size - 1; j++) {
                const color = matrix[i][j];
                if (matrix[i][j + 1] === color &&
                    matrix[i + 1][j] === color &&
                    matrix[i + 1][j + 1] === color) {
                    penalty += 3;
                }
            }
        }

        // Rule 3: Finder-like pattern
        const pattern1 = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0];
        const pattern2 = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1];

        for (let i = 0; i < size; i++) {
            for (let j = 0; j <= size - 11; j++) {
                let match1 = true;
                let match2 = true;
                for (let k = 0; k < 11; k++) {
                    if (matrix[i][j + k] !== pattern1[k]) match1 = false;
                    if (matrix[i][j + k] !== pattern2[k]) match2 = false;
                }
                if (match1 || match2) penalty += 40;

                match1 = true;
                match2 = true;
                for (let k = 0; k < 11; k++) {
                    if (matrix[j + k][i] !== pattern1[k]) match1 = false;
                    if (matrix[j + k][i] !== pattern2[k]) match2 = false;
                }
                if (match1 || match2) penalty += 40;
            }
        }

        // Rule 4: Proportion of dark modules
        let darkCount = 0;
        for (let i = 0; i < size; i++) {
            for (let j = 0; j < size; j++) {
                if (matrix[i][j] === 1) darkCount++;
            }
        }
        const percent = (darkCount * 100) / (size * size);
        const deviation = Math.abs(percent - 50);
        penalty += Math.floor(deviation / 5) * 10;

        return penalty;
    }

    function selectBestMask(matrix, reserved, size) {
        let bestMask = 0;
        let bestPenalty = Infinity;

        for (let mask = 0; mask < 8; mask++) {
            const masked = applyMask(matrix, reserved, size, mask);
            const penalty = evaluateMask(masked, size);

            if (penalty < bestPenalty) {
                bestPenalty = penalty;
                bestMask = mask;
            }
        }

        return bestMask;
    }

    // ============================================================
    // FORMAT AND VERSION INFORMATION
    // ============================================================

    function placeFormatInfo(matrix, size, eccLevel, maskPattern) {
        const eccIndicator = ECC_INDICATORS[eccLevel];
        const formatData = (eccIndicator << 3) | maskPattern;
        const formatBits = FORMAT_INFO[formatData];

        // Place around top-left finder pattern (first copy)
        for (let i = 0; i < 6; i++) {
            matrix[8][i] = (formatBits >> (14 - i)) & 1;
        }
        matrix[8][7] = (formatBits >> 8) & 1;
        matrix[8][8] = (formatBits >> 7) & 1;
        matrix[7][8] = (formatBits >> 6) & 1;
        for (let i = 0; i < 6; i++) {
            matrix[5 - i][8] = (formatBits >> (5 - i)) & 1;
        }

        // Place around bottom-left finder pattern (vertical strip)
        for (let i = 0; i < 7; i++) {
            matrix[size - 1 - i][8] = (formatBits >> i) & 1;
        }

        // Place around top-right finder pattern (horizontal strip)
        for (let i = 0; i < 8; i++) {
            matrix[8][size - 8 + i] = (formatBits >> (7 + i)) & 1;
        }
    }

    function placeVersionInfo(matrix, size, version) {
        if (version < 7) return;

        const versionBits = VERSION_INFO[version];

        for (let i = 0; i < 6; i++) {
            for (let j = 0; j < 3; j++) {
                const bit = (versionBits >> (i * 3 + j)) & 1;
                matrix[size - 11 + j][i] = bit;
            }
        }

        for (let i = 0; i < 6; i++) {
            for (let j = 0; j < 3; j++) {
                const bit = (versionBits >> (i * 3 + j)) & 1;
                matrix[i][size - 11 + j] = bit;
            }
        }
    }

    // ============================================================
    // MAIN GENERATION FUNCTION
    // ============================================================

    function generate(data, eccLevel = 'M') {
        if (!data || data.length === 0) {
            throw new Error('Data cannot be empty');
        }

        const mode = detectMode(data);

        let dataLength;
        if (mode === 'BYTE') {
            const encoder = new TextEncoder();
            dataLength = encoder.encode(data).length;
        } else {
            dataLength = data.length;
        }

        const version = selectVersion(dataLength, eccLevel, mode);
        if (version === -1) {
            throw new Error('Data too long for QR code');
        }

        const dataBits = createDataBitstream(data, version, eccLevel, mode);
        const dataCodewords = bitsToCodewords(dataBits);
        const finalCodewords = generateErrorCorrection(dataCodewords, version, eccLevel);

        const bits = [];
        for (const codeword of finalCodewords) {
            for (let i = 7; i >= 0; i--) {
                bits.push((codeword >> i) & 1);
            }
        }

        const remainderCount = REMAINDER_BITS[version];
        for (let i = 0; i < remainderCount; i++) {
            bits.push(0);
        }

        const { matrix, reserved, size } = buildFunctionPatterns(version);
        placeDataModules(matrix, reserved, size, bits);

        const maskPattern = selectBestMask(matrix, reserved, size);
        const maskedMatrix = applyMask(matrix, reserved, size, maskPattern);

        placeFormatInfo(maskedMatrix, size, eccLevel, maskPattern);
        placeVersionInfo(maskedMatrix, size, version);

        return {
            matrix: maskedMatrix,
            version,
            size,
            eccLevel,
            maskPattern,
            mode,
            dataLength
        };
    }

    // ============================================================
    // RENDERING
    // ============================================================

    function render(canvas, qrData, moduleSize = 8) {
        const { matrix, size } = qrData;
        const quietZone = 4;
        const totalSize = (size + quietZone * 2) * moduleSize;

        canvas.width = totalSize;
        canvas.height = totalSize;

        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, totalSize, totalSize);

        ctx.fillStyle = '#000000';
        for (let i = 0; i < size; i++) {
            for (let j = 0; j < size; j++) {
                if (matrix[i][j] === 1) {
                    ctx.fillRect(
                        (j + quietZone) * moduleSize,
                        (i + quietZone) * moduleSize,
                        moduleSize,
                        moduleSize
                    );
                }
            }
        }
    }

    // Public API
    return {
        generate,
        render,

        // Expose for testing
        _internal: {
            detectMode,
            encodeNumeric,
            encodeAlphanumeric,
            encodeByte,
            calculateECC,
            evaluateMask,
            MASK_PATTERNS,
            BYTE_CAPACITY,
            ECC_TABLE,
            FORMAT_INFO,
            VERSION_INFO,
            ALIGNMENT_PATTERNS
        }
    };
})();

// Export for Node.js/CommonJS environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QRCode;
}

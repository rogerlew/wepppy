import fs from 'node:fs/promises';
import path from 'node:path';

// CRITICAL: Must use 'test-results' NOT 'playwright-report'
// Playwright's HTML reporter (configured in playwright.config.mjs) outputs to 'playwright-report/'
// and recreates/cleans that directory on each run, which deletes any custom artifacts we write there.
// Using 'test-results/' avoids this conflict since Playwright only cleans test-specific subdirectories.
const DEFAULT_REPORT_DIR = path.join('test-results', 'theme-metrics');

export async function extractThemeIds(page) {
  const values = await page.evaluate(() => {
    const selectors = document.querySelectorAll('[data-theme-select] option');
    if (!selectors.length) {
      return ['default'];
    }
    return Array.from(selectors, (opt) => opt.value || 'default');
  });
  return Array.from(new Set(values));
}

export async function readContrastTargets(page) {
  const locator = page.locator('#themeContrastTargets');
  await locator.waitFor({ state: 'attached' });
  const payload = await locator.textContent();
  if (!payload) {
    throw new Error('themeContrastTargets payload missing');
  }
  let data;
  try {
    data = JSON.parse(payload);
  } catch (err) {
    throw new Error(`Failed to parse themeContrastTargets JSON: ${err.message}`);
  }
  if (!Array.isArray(data)) {
    throw new Error('themeContrastTargets must be an array');
  }
  return data;
}

export async function measureTarget(page, target) {
  const actionErrors = [];
  if (Array.isArray(target.actions) && target.actions.length) {
    for (const action of target.actions) {
      try {
        await executeAction(page, action);
      } catch (err) {
        actionErrors.push(`Action ${action.type} ${action.target || ''} failed: ${err.message}`);
      }
    }
  }

  const pairResults = [];
  for (const pair of target.pairs || []) {
    const sample = await samplePairColors(page, pair);
    const errors = [...actionErrors];
    let ratio = null;
    if (sample.error) {
      errors.push(sample.error);
    }
    if (!sample.foreground) {
      errors.push(`Missing foreground element (${pair.foreground})`);
    }
    if (!sample.background) {
      errors.push(`Missing background element (${pair.background || pair.foreground})`);
    }

    if (sample.foreground && sample.background) {
      ratio = computeContrast(sample.foreground, sample.background);
    }

    pairResults.push({
      targetId: target.id,
      targetLabel: target.label,
      pairName: pair.name,
      threshold: typeof target.threshold === 'number' ? target.threshold : null,
      ratio,
      passed:
        typeof target.threshold === 'number' && ratio !== null
          ? ratio >= target.threshold
          : null,
      foreground: sample.foreground
        ? {
            rgba: sample.foreground,
            hex: colorToHex(sample.foreground),
          }
        : null,
      background: sample.background
        ? {
            rgba: sample.background,
            hex: colorToHex(sample.background),
          }
        : null,
      errors,
    });
  }

  return pairResults;
}

async function executeAction(page, action) {
  if (!action || !action.type || !action.target) {
    throw new Error('Invalid action descriptor');
  }
  const locator = page.locator(action.target).first();
  await locator.waitFor({ state: 'attached', timeout: 5000 });
  switch (action.type) {
    case 'click':
      await locator.click({ force: true });
      return;
    case 'set_checked':
      await locator.setChecked(Boolean(action.value), { force: true });
      return;
    default:
      throw new Error(`Unsupported action type: ${action.type}`);
  }
}

async function samplePairColors(page, pair) {
  try {
    return await page.evaluate((descriptor) => {
      const parseColorString = (value) => {
        if (!value) return null;
        const normalized = value.trim().toLowerCase();
        if (normalized === 'transparent') {
          return { r: 0, g: 0, b: 0, a: 0 };
        }
        if (normalized.startsWith('color(')) {
          const parsed = parseColorFunction(normalized);
          if (parsed) {
            return parsed;
          }
        }
        if (normalized.startsWith('#')) {
          return parseHex(normalized);
        }
        if (normalized.startsWith('rgb')) {
          return parseRgb(normalized);
        }
        const probe = document.createElement('span');
        probe.style.color = normalized;
        probe.style.position = 'absolute';
        probe.style.left = '-9999px';
        document.body.appendChild(probe);
        const computed = getComputedStyle(probe).color;
        probe.remove();
        return parseRgb(computed);
      };

      const parseColorFunction = (value) => {
        const start = value.indexOf('(');
        const end = value.lastIndexOf(')');
        if (start === -1 || end === -1 || end <= start + 1) {
          return null;
        }
        const payload = value.slice(start + 1, end).trim();
        if (!payload.startsWith('srgb')) {
          return null;
        }
        let rest = payload.slice(4).trim();
        let alpha = 1;
        if (rest.includes('/')) {
          const segments = rest.split('/');
          rest = segments[0].trim();
          alpha = Number.parseFloat(segments[1].trim());
        }
        const parts = rest.split(/\s+/).filter(Boolean);
        if (parts.length < 3) {
          return null;
        }
        const toByte = (token) => {
          const value = Number.parseFloat(token);
          if (Number.isNaN(value)) return 0;
          const clamped = Math.max(0, Math.min(1, value));
          return Math.round(clamped * 255);
        };
        return {
          r: toByte(parts[0]),
          g: toByte(parts[1]),
          b: toByte(parts[2]),
          a: clampAlpha(alpha),
        };
      };

      const parseHex = (value) => {
        let hex = value.replace('#', '');
        if (hex.length === 3) {
          hex = hex
            .split('')
            .map((c) => c + c)
            .join('');
        }
        if (hex.length === 4) {
          hex = hex
            .split('')
            .map((c) => c + c)
            .join('');
        }
        if (hex.length === 6) {
          hex += 'ff';
        }
        if (hex.length !== 8) return null;
        const intVal = Number.parseInt(hex, 16);
        return {
          r: (intVal >> 24) & 0xff,
          g: (intVal >> 16) & 0xff,
          b: (intVal >> 8) & 0xff,
          a: Number(((intVal & 0xff) / 255).toFixed(4)),
        };
      };

      const parseRgb = (value) => {
        const body = value.slice(value.indexOf('(') + 1, value.lastIndexOf(')'));
        const parts = body
          .replace(/\//g, ' ')
          .split(/[\s,]+/)
          .filter(Boolean);
        if (parts.length < 3) return null;
        const [r, g, b, alpha] = parts;
        const toByte = (token) =>
          token.includes('%')
            ? Math.round((parseFloat(token) / 100) * 255)
            : Number.parseFloat(token);
        const toAlpha = (token) =>
          token === undefined
            ? 1
            : token.includes('%')
            ? Number(parseFloat(token) / 100)
            : Number.parseFloat(token);
        return {
          r: clampByte(toByte(r)),
          g: clampByte(toByte(g)),
          b: clampByte(toByte(b)),
          a: clampAlpha(toAlpha(alpha)),
        };
      };

      const clampByte = (value) => {
        if (Number.isNaN(value)) return 0;
        return Math.max(0, Math.min(255, Math.round(value)));
      };

      const clampAlpha = (value) => {
        if (Number.isNaN(value)) return 1;
        return Math.max(0, Math.min(1, Number(value)));
      };

      const resolveBackground = (element) => {
        let current = element;
        while (current) {
          const style = getComputedStyle(current);
          const parsed = parseColorString(style.backgroundColor);
          if (parsed && parsed.a > 0) {
            return parsed;
          }
          current = current.parentElement;
        }
        const bodyColor = parseColorString(getComputedStyle(document.body).backgroundColor);
        if (bodyColor) {
          return bodyColor.a > 0 ? bodyColor : { r: 255, g: 255, b: 255, a: 1 };
        }
        return { r: 255, g: 255, b: 255, a: 1 };
      };

      const resolveForeground = (element, mode) => {
        if (!element) return null;
        const style = getComputedStyle(element);
        const borderColor = parseColorString(style.borderTopColor);
        if (mode === 'border') {
          if (borderColor && borderColor.a > 0) {
            return borderColor;
          }
        }
        let referenceColor = style.color;
        if (element.matches('input[type="checkbox"], input[type="radio"]') && style.accentColor) {
          referenceColor = style.accentColor;
        }
        let parsed = parseColorString(referenceColor);
        if (parsed && parsed.a > 0) {
          return parsed;
        }
        return borderColor || parsed;
      };

      const getElement = (selector) => {
        if (!selector) return null;
        return document.querySelector(selector);
      };

      const foregroundEl = getElement(descriptor.foreground);
      const backgroundEl = descriptor.background ? getElement(descriptor.background) : foregroundEl;
      const foregroundMode = descriptor.foreground_mode || descriptor.foregroundMode || null;

      return {
        foreground: resolveForeground(foregroundEl, foregroundMode),
        background: resolveBackground(backgroundEl || foregroundEl),
        missingForeground: !foregroundEl,
        missingBackground: Boolean(descriptor.background && !backgroundEl),
      };
    }, pair);
  } catch (err) {
    return { error: err.message };
  }
}

export function computeContrast(foreground, background) {
  const lumA = relativeLuminance(foreground);
  const lumB = relativeLuminance(background);
  const [lighter, darker] = lumA >= lumB ? [lumA, lumB] : [lumB, lumA];
  return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(3));
}

function relativeLuminance(color) {
  const toLinear = (channel) => {
    const normalized = channel / 255;
    return normalized <= 0.03928
      ? normalized / 12.92
      : Math.pow((normalized + 0.055) / 1.055, 2.4);
  };
  return (
    0.2126 * toLinear(color.r) +
    0.7152 * toLinear(color.g) +
    0.0722 * toLinear(color.b)
  );
}

function colorToHex(color) {
  const toHex = (value) => value.toString(16).padStart(2, '0');
  return `#${toHex(color.r)}${toHex(color.g)}${toHex(color.b)}`;
}

export async function writeContrastReport(results, { baseUrl, outputDir } = {}) {
  const dir = outputDir || DEFAULT_REPORT_DIR;
  const absoluteDir = path.resolve(process.cwd(), dir);
  await fs.mkdir(absoluteDir, { recursive: true });
  
  const jsonPayload = {
    generated_at: new Date().toISOString(),
    base_url: baseUrl || null,
    results,
  };
  
  const jsonPath = path.join(absoluteDir, 'theme-contrast.json');
  await fs.writeFile(jsonPath, JSON.stringify(jsonPayload, null, 2), 'utf8');

  const markdownPath = path.join(absoluteDir, 'theme-contrast.md');
  await fs.writeFile(markdownPath, renderMarkdown(results), 'utf8');
  
  console.log(`[theme-metrics] Reports written to ${absoluteDir}/`);
  console.log(`[theme-metrics] - JSON: ${results.length} measurements`);
  console.log(`[theme-metrics] - Markdown: ${Object.keys(results.reduce((acc, r) => ({...acc, [r.theme]: 1}), {})).length} themes`);
}

function renderMarkdown(results) {
  if (!results.length) {
    return '# Theme Contrast Metrics\n\n_No data collected._\n';
  }
  const lines = [
    '# Theme Contrast Metrics',
    '',
    '| Theme | Target | Pair | Ratio | Threshold | Status | Notes |',
    '|-------|--------|------|-------|-----------|--------|-------|',
  ];
  for (const entry of results) {
    const status = entry.passed === null ? 'n/a' : entry.passed ? '✅' : '⚠️';
    const notes = entry.errors?.length ? entry.errors.join('<br>') : '';
    const ratioText = entry.ratio === null ? 'n/a' : entry.ratio.toFixed(3);
    const thresholdText = entry.threshold === null ? 'n/a' : entry.threshold.toFixed(2);
    lines.push(
      `| ${entry.theme} | ${entry.targetLabel || entry.targetId} | ${entry.pairName || '(default)'} | ${ratioText} | ${thresholdText} | ${status} | ${notes} |`
    );
  }
  return `${lines.join('\n')}\n`;
}

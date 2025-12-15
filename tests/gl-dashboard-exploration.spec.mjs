/**
 * GL Dashboard exploration script for documentation purposes.
 * This script exercises the dashboard to capture behavior for specification.
 * 
 * Usage:
 *   export BASE_URL=http://localhost:8080
 *   export RUNID=<your-runid>
 *   export CONFIG=<your-config>
 *   npx playwright test tests/gl-dashboard-exploration.spec.mjs --headed
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';
const RUNID = process.env.RUNID || 'test-run';
const CONFIG = process.env.CONFIG || 'dev_unit_1';

test.describe('GL Dashboard Documentation Exploration', () => {
  test('explore dashboard structure and interactions', async ({ page }) => {
    // Navigate to the dashboard
    const dashboardUrl = `${BASE_URL}/runs/${RUNID}/${CONFIG}/gl-dashboard`;
    console.log(`Navigating to: ${dashboardUrl}`);
    
    await page.goto(dashboardUrl, { waitUntil: 'networkidle', timeout: 60000 });
    
    // Wait for map container to appear
    await page.waitForSelector('#gl-dashboard-map', { timeout: 30000 });
    console.log('✓ Map container loaded');
    
    // Wait for layer list
    await page.waitForSelector('#gl-layer-list', { timeout: 10000 });
    console.log('✓ Layer list rendered');
    
    // Capture initial page structure
    const layerStructure = await page.evaluate(() => {
      const layerList = document.getElementById('gl-layer-list');
      if (!layerList) return null;
      
      const details = layerList.querySelectorAll('.gl-layer-details');
      const structure = [];
      
      details.forEach((detail) => {
        const summary = detail.querySelector('summary');
        const items = detail.querySelectorAll('.gl-layer-item input');
        structure.push({
          category: summary?.textContent?.trim() || 'Unknown',
          itemCount: items.length,
          items: Array.from(items).map(input => ({
            id: input.id,
            checked: input.checked,
            label: input.nextElementSibling?.textContent?.trim() || ''
          }))
        });
      });
      
      return structure;
    });
    
    console.log('Layer structure:', JSON.stringify(layerStructure, null, 2));
    
    // Capture legend state
    const legendState = await page.evaluate(() => {
      const legendContent = document.getElementById('gl-legends-content');
      const legends = legendContent?.querySelectorAll('.gl-legend-item');
      return Array.from(legends || []).map(legend => ({
        title: legend.querySelector('h5')?.textContent?.trim() || 'Unknown',
        visible: legend.style.display !== 'none'
      }));
    });
    
    console.log('Initial legend state:', JSON.stringify(legendState, null, 2));
    
    // Test layer toggles (Landuse)
    const landuseCheckbox = await page.$('input[id^="layer-Landuse-"]');
    if (landuseCheckbox) {
      console.log('Testing landuse layer toggle...');
      await landuseCheckbox.click();
      await page.waitForTimeout(1000); // Allow layer to render
      
      const landuseLegendsAfter = await page.evaluate(() => {
        const legendContent = document.getElementById('gl-legends-content');
        const legends = legendContent?.querySelectorAll('.gl-legend-item');
        return Array.from(legends || []).filter(l => 
          l.querySelector('h5')?.textContent?.includes('Landuse')
        ).map(l => ({
          title: l.querySelector('h5')?.textContent?.trim(),
          visible: l.style.display !== 'none'
        }));
      });
      console.log('Landuse legends after toggle:', landuseLegendsAfter);
    }
    
    // Test graph panel state
    const graphPanel = await page.$('#gl-graph');
    if (graphPanel) {
      const graphState = await page.evaluate(() => {
        const panel = document.getElementById('gl-graph');
        const modeButtons = document.querySelectorAll('[data-graph-mode]');
        return {
          collapsed: panel?.classList.contains('is-collapsed'),
          currentMode: Array.from(modeButtons).find(btn => 
            btn.classList.contains('is-active')
          )?.dataset.graphMode || 'unknown',
          modesAvailable: Array.from(modeButtons).map(btn => btn.dataset.graphMode)
        };
      });
      console.log('Graph panel state:', graphState);
      
      // Test graph mode switching
      const splitButton = await page.$('[data-graph-mode="split"]');
      if (splitButton) {
        console.log('Testing graph mode switch to split...');
        await splitButton.click();
        await page.waitForTimeout(500);
        
        const afterModeSwitch = await page.evaluate(() => {
          const panel = document.getElementById('gl-graph');
          return {
            collapsed: panel?.classList.contains('is-collapsed'),
            hasFocus: document.querySelector('.gl-main')?.classList.contains('graph-focus')
          };
        });
        console.log('After mode switch:', afterModeSwitch);
      }
    }
    
    // Test year slider visibility
    const yearSlider = await page.$('#gl-year-slider');
    if (yearSlider) {
      const sliderState = await page.evaluate(() => {
        const slider = document.getElementById('gl-year-slider');
        const input = document.getElementById('gl-year-slider-input');
        return {
          visible: slider?.classList.contains('is-visible'),
          min: input?.min,
          max: input?.max,
          value: input?.value
        };
      });
      console.log('Year slider state:', sliderState);
    }
    
    // Test RAP layer activation (if available)
    const rapCheckbox = await page.$('input[id^="layer-RAP-"]');
    if (rapCheckbox) {
      console.log('Testing RAP layer activation...');
      await rapCheckbox.click();
      await page.waitForTimeout(2000); // Allow data fetch and render
      
      const afterRapActivation = await page.evaluate(() => {
        const slider = document.getElementById('gl-year-slider');
        const graphPanel = document.getElementById('gl-graph');
        const graphCanvas = document.getElementById('gl-graph-canvas');
        return {
          sliderVisible: slider?.classList.contains('is-visible'),
          graphExpanded: !graphPanel?.classList.contains('is-collapsed'),
          canvasRendered: graphCanvas && graphCanvas.width > 0
        };
      });
      console.log('After RAP activation:', afterRapActivation);
    }
    
    // Test WEPP Yearly layer (if available)
    const weppYearlyCheckbox = await page.$('input[id^="layer-WEPP-Yearly-"]');
    if (weppYearlyCheckbox) {
      console.log('Testing WEPP Yearly layer activation...');
      await weppYearlyCheckbox.click();
      await page.waitForTimeout(2000);
      
      const afterWeppYearly = await page.evaluate(() => {
        const slider = document.getElementById('gl-year-slider');
        const legends = document.getElementById('gl-legends-content');
        return {
          sliderVisible: slider?.classList.contains('is-visible'),
          legendCount: legends?.querySelectorAll('.gl-legend-item:not([style*="display: none"])').length || 0
        };
      });
      console.log('After WEPP Yearly activation:', afterWeppYearly);
    }
    
    // Test Omni graph (if available)
    const omniGraphRadio = await page.$('input[id^="graph-omni-"]');
    if (omniGraphRadio) {
      console.log('Testing Omni graph activation...');
      await omniGraphRadio.click();
      await page.waitForTimeout(2000);
      
      const afterOmniGraph = await page.evaluate(() => {
        const graphPanel = document.getElementById('gl-graph');
        const graphTitle = document.querySelector('#gl-graph h4');
        const canvas = document.getElementById('gl-graph-canvas');
        return {
          graphExpanded: !graphPanel?.classList.contains('is-collapsed'),
          graphTitle: graphTitle?.textContent?.trim(),
          canvasWidth: canvas?.width || 0,
          graphFocus: document.querySelector('.gl-main')?.classList.contains('graph-focus')
        };
      });
      console.log('After Omni graph activation:', afterOmniGraph);
    }
    
    // Capture console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error('Browser console error:', msg.text());
      } else if (msg.text().includes('gl-dashboard')) {
        console.log('Dashboard log:', msg.text());
      }
    });
    
    // Take screenshots
    await page.screenshot({ 
      path: '/tmp/gl-dashboard-exploration.png',
      fullPage: true 
    });
    console.log('✓ Screenshot saved to /tmp/gl-dashboard-exploration.png');
    
    console.log('\n=== Exploration Complete ===');
  });
});

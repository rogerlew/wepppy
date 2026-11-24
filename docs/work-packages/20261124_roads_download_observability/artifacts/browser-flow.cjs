const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const {chromium} = require("playwright");

(async () => {
    const browser = await chromium.launch();
    try {
        const page = await browser.newPage();
        await page.goto(process.argv[2]);
        const button = page.getByRole("button", {name:"Download OpenStreetMap roads"});
        const status = page.locator("#roads_osm_status");
        const downloaded = page.waitForEvent("download");
        await button.click();
        const file = await downloaded;
        const data = JSON.parse(await fs.readFile(await file.path()));
        assert.equal(data.features[0].properties.osm_id, "17");
        console.log("502 then 200: downloaded feature", data.features[0].properties.osm_id);
        for (const pattern of [/HTTP 502.*2 attempts.*Reference:/, /Timed out waiting for OpenStreetMap.*1 attempt.*Reference:/]) {
            await button.click();
            await page.waitForFunction(() => !document.querySelector("[data-roads-action=download-osm]").disabled);
            const message = await status.innerText();
            assert.match(message, pattern);
            console.log(message);
        }
        await page.evaluate(() => { window.url_for_run = () => "/stalled-body"; });
        await button.click();
        await page.waitForFunction(() => !document.querySelector("[data-roads-action=download-osm]").disabled, null, {timeout:35000});
        const message = await status.innerText();
        assert.match(message, /Your browser timed out after 30 seconds/);
        console.log(message);
    } finally {
        await browser.close();
    }
})().catch(error => {console.error(error);process.exitCode=1;});

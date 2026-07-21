/**
 * @jest-environment jsdom
 */

const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

const templatePath = resolve(globalThis.process.cwd(), "../templates/user/runs2.html");
const templateSource = readFileSync(templatePath, "utf-8");
const buildRunRowMatch = templateSource.match(
    /\s{2}function buildRunRow\(run\) \{[\s\S]*?\n\s{2}\}\n\n\s{2}function getTotalPages/
);

function loadBuildRunRow() {
    if (!buildRunRowMatch) {
        throw new Error("Unable to locate buildRunRow in the Runs template");
    }
    const buildRunRowSource = buildRunRowMatch[0].replace(/\n\n\s{2}function getTotalPages$/, "");
    return new Function(
        "formatOptionalValue",
        "runsTtlDeletionHelpUrl",
        "showOwner",
        "sitePrefix",
        "updateDeleteState",
        `${buildRunRowSource}\nreturn buildRunRow;`
    )(
        (value) => (value === null || value === undefined || value === "" ? "—" : String(value)),
        "/weppcloud/usersum/doc/usersum.weppcloud.run_ttl_deletion",
        false,
        "/weppcloud",
        () => {}
    );
}

describe("Runs lifecycle cell", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
    });

    test("renders an active TTL expiry and the configured Usersum link", () => {
        const buildRunRow = loadBuildRunRow();
        const row = buildRunRow({
            runid: "active-run",
            config: "cfg",
            date_created: "2026-07-01T00:00:00Z",
            ttl_deletion_at: "2026-12-31T00:00:00Z"
        });
        const lifecycleCell = row.children[6];

        expect(lifecycleCell.textContent).toBe("TTL Deletion: 2026-12-31T00:00:00Z Learn More");
        expect(lifecycleCell.querySelector("time").dateTime).toBe("2026-12-31T00:00:00Z");
        expect(lifecycleCell.querySelector("a").getAttribute("href")).toBe(
            "/weppcloud/usersum/doc/usersum.weppcloud.run_ttl_deletion"
        );
    });

    test("renders Last Modified without a policy link when TTL is inactive", () => {
        const buildRunRow = loadBuildRunRow();
        const row = buildRunRow({
            runid: "disabled-run",
            config: "cfg",
            date_created: "2026-07-01T00:00:00Z",
            last_modified: "2026-07-20T00:00:00Z",
            ttl_deletion_at: null
        });
        const lifecycleCell = row.children[6];

        expect(lifecycleCell.textContent).toBe("Last Modified: 2026-07-20T00:00:00Z");
        expect(lifecycleCell.querySelector("time").dateTime).toBe("2026-07-20T00:00:00Z");
        expect(lifecycleCell.querySelector("a")).toBeNull();
    });

    test("keeps the help URL deployment-prefix-aware in Jinja", () => {
        expect(templateSource).toContain(
            "url_for('usersum.view_doc', doc_id='usersum.weppcloud.run_ttl_deletion')"
        );
    });
});

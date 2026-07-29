/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const templatePath = path.resolve(
    __dirname,
    "../../routes/readme_md/templates/readme_editor.htm"
);

function inlineScript() {
    const source = fs.readFileSync(templatePath, "utf8");
    const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    return scripts.at(-1)[1]
        .replace("{{ runid | tojson }}", JSON.stringify("run-1"))
        .replace("{{ config | tojson }}", JSON.stringify("cfg"))
        .replace("{{ editor_client_uuid | tojson }}", JSON.stringify("a".repeat(32)))
        .replace("{{ (ron.name or '') | tojson }}", JSON.stringify("Initial name"))
        .replace("{{ (ron.scenario or '') | tojson }}", JSON.stringify("Initial scenario"))
        .replace(
            "{{ url_for_run('readme.readme_save', runid=runid, config=config) | tojson }}",
            JSON.stringify("/runs/run-1/cfg/readme/save")
        )
        .replace(
            "{{ url_for_run('readme.readme_preview', runid=runid, config=config) | tojson }}",
            JSON.stringify("/runs/run-1/cfg/readme/preview")
        )
        .replace(
            "{{ url_for_run('readme.readme_raw', runid=runid, config=config) | tojson }}",
            JSON.stringify("/runs/run-1/cfg/readme/raw")
        );
}

function installDom() {
    document.head.innerHTML = "<title></title>";
    document.body.innerHTML = `
      <textarea id="readme-editor"># Initial</textarea>
      <article id="readme-preview"></article>
      <div id="readme-lock-overlay" hidden></div>
      <button id="readme-lock-reload" type="button"></button>
    `;
    window.commandProject = {
        _notifyCommandBar: jest.fn(),
        set_name: jest.fn(),
        set_scenario: jest.fn(),
    };
    window.Project = {
        getInstance: jest.fn(() => window.commandProject),
    };
}

async function settle() {
    for (let index = 0; index < 16; index += 1) {
        await Promise.resolve();
    }
}

describe("README editor inline contract", () => {
    beforeEach(() => {
        jest.useFakeTimers();
        installDom();
        window.fetch = jest.fn();
        delete window.location.reload;
    });

    afterEach(() => {
        jest.useRealTimers();
        jest.restoreAllMocks();
        delete window.Project;
        delete window.commandProject;
    });

    test("parses and previews then saves the exact Markdown with one UUID", async () => {
        window.fetch
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ html: "<h1>Changed</h1>" }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ronUpdate: { name: "Updated name", scenario: "Updated scenario" },
                }),
            });

        window.eval(inlineScript());
        const editor = document.querySelector("#readme-editor");
        editor.value = "# Changed";
        editor.dispatchEvent(new Event("input"));

        jest.advanceTimersByTime(600);
        await settle();
        expect(window.fetch).toHaveBeenNthCalledWith(
            1,
            "/runs/run-1/cfg/readme/preview",
            expect.objectContaining({
                method: "POST",
                body: JSON.stringify({
                    markdown: "# Changed",
                    uuid: "a".repeat(32),
                }),
            })
        );
        expect(document.querySelector("#readme-preview").innerHTML).toBe("<h1>Changed</h1>");

        jest.advanceTimersByTime(1400);
        await settle();
        expect(window.fetch).toHaveBeenNthCalledWith(
            2,
            "/runs/run-1/cfg/readme/save",
            expect.objectContaining({
                method: "POST",
                body: JSON.stringify({
                    markdown: "# Changed",
                    uuid: "a".repeat(32),
                    revision: 1,
                }),
            })
        );
        expect(document.title).toContain("Updated name");
        expect(window.commandProject.set_name).toHaveBeenCalledWith("Updated name");
        expect(window.commandProject.set_scenario).toHaveBeenCalledWith("Updated scenario");
    });

    test("invalidates a stale tab from the save conflict response", async () => {
        window.fetch
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ html: "<p>Preview</p>" }),
            })
            .mockResolvedValueOnce({
                ok: false,
                status: 409,
                json: async () => ({ invalidated: true, reason: "lock_mismatch" }),
            });

        window.eval(inlineScript());
        document.querySelector("#readme-editor").dispatchEvent(new Event("input"));
        jest.advanceTimersByTime(2000);
        await settle();

        expect(document.querySelector("#readme-editor").disabled).toBe(true);
        expect(document.querySelector("#readme-lock-overlay").hidden).toBe(false);
    });

    test("invalidates a stale tab from lock polling", async () => {
        window.fetch.mockResolvedValue({
            ok: true,
            json: async () => ({ markdown: "# Current", locked_out: true }),
        });

        window.eval(inlineScript());
        jest.advanceTimersByTime(5000);
        await settle();

        expect(window.fetch).toHaveBeenCalledWith(
            "/runs/run-1/cfg/readme/raw",
            { headers: { "X-Readme-Client": "a".repeat(32) } }
        );
        expect(document.querySelector("#readme-editor").disabled).toBe(true);
    });
});

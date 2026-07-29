/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const template = fs.readFileSync(
    path.resolve(__dirname, "../../templates/user/runs2.html"),
    "utf8"
);

function renderedScript({ admin = false } = {}) {
    let script = template.match(/<script>([\s\S]*?)<\/script>/)[1];
    const replacements = new Map([
        ["{{ site_prefix | default('', true) | tojson }}", '"/weppcloud"'],
        ["{{ show_owner | tojson }}", "false"],
        [
            "{{ is_admin_runs_viewer | default(false, true) | tojson }}",
            admin ? "true" : "false"
        ],
        ["{{ current_user_alias | default('', true) | tojson }}", '"7"'],
        ["{{ selected_alias | default('', true) | tojson }}", '""'],
        ["{{ sort | default('last_modified', true) | tojson }}", '"last_modified"'],
        ["{{ direction | default('desc', true) | tojson }}", '"desc"'],
        ["{{ per_page | default(25, true) | tojson }}", "25"],
        ["{{ url_for('user.runs_catalog') | tojson }}", '"/runs/catalog"'],
        ["{{ url_for('user.runs_map_data') | tojson }}", '"/runs/map-data"'],
        ["{{ url_for('user.runs_users') | tojson }}", '"/runs/users"'],
        [
            "{{ url_for('usersum.view_doc', doc_id='usersum.weppcloud.run_ttl_deletion') | tojson }}",
            '"/docs/run-ttl"'
        ]
    ]);
    replacements.forEach((value, source) => {
        script = script.split(source).join(value);
    });
    return script;
}

function installDom({ admin = false } = {}) {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-value">';
    document.body.innerHTML = `
      <button id="runs-tab-table"></button>
      <button id="runs-tab-map"></button>
      <div id="runs-table-view"></div>
      <div id="runs-map-view" hidden></div>
      <input id="runs_search_input">
      <button id="runs_search_clear" disabled></button>
      <button id="runs_search_go"></button>
      <button id="delete_runs_button" disabled></button>
      <div id="runs-delete-status"></div>
      <table id="runs_table"><tbody id="runs_table_body">
        <tr id="runs_empty_row" data-empty-row="true"><td>Loading runs...</td></tr>
      </tbody></table>
      <nav id="runs-pagination"></nav>
      <div id="runs-map-status"></div>
      <div id="runs-map-canvas"></div>
      ${admin ? `
        <input id="runs_admin_user_search">
        <button id="runs_admin_apply_scope" disabled></button>
        <button id="runs_admin_reset_scope"></button>
        <div id="runs_admin_user_suggestions" hidden></div>
        <div id="runs_admin_scope_status"></div>
      ` : ""}
    `;
}

async function flushPromises() {
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("Runs catalog actual inline contract", () => {
    beforeEach(() => {
        window.history.replaceState({}, "", "/runs");
        window.confirm = jest.fn(() => true);
        window.open = jest.fn();
        global.fetch = jest.fn();
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    test("renders hostile catalog values safely and deletes exact encoded identity", async () => {
        installDom();
        fetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    runs: [{
                        runid: "run /?x",
                        config: "cfg /",
                        name: "<img src=x onerror=alert(1)>",
                        scenario: "<b>scenario</b>",
                        readonly: false,
                        date_created: "2026-01-01",
                        last_modified: "2026-01-02"
                    }]
                })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ Content: { job_id: "job/1" } })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: "finished" })
            });

        window.eval(renderedScript());
        await flushPromises();

        const row = document.querySelector('tr[data-run-row="true"]');
        expect(row.textContent).toContain("<img src=x onerror=alert(1)>");
        expect(row.querySelector("img")).toBeNull();
        expect(row.querySelector("b")).toBeNull();
        expect(row.querySelector("a").getAttribute("href")).toBe(
            "/weppcloud/runs/run%20%2F%3Fx/cfg%20%2F/"
        );

        const checkbox = row.querySelector('input[type="checkbox"]');
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        await window.deleteRuns();
        await flushPromises();

        expect(fetch).toHaveBeenNthCalledWith(
            2,
            "/weppcloud/runs/run%20%2F%3Fx/cfg%20%2F/tasks/delete/",
            {
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": "csrf-value" }
            }
        );
        expect(fetch).toHaveBeenNthCalledWith(
            3,
            "/rq-engine/api/jobstatus/job%2F1",
            { credentials: "same-origin" }
        );
        expect(document.querySelector('tr[data-run-row="true"]')).toBeNull();
        expect(document.querySelector("#runs-delete-status").textContent).toBe(
            "Delete complete (1/1)."
        );
    });

    test("keeps readonly rows unselectable", async () => {
        installDom();
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                runs: [{
                    runid: "readonly-run",
                    config: 0,
                    readonly: true
                }]
            })
        });
        window.eval(renderedScript());
        await flushPromises();

        const checkbox = document.querySelector('tr[data-run-row="true"] input');
        expect(checkbox.dataset.config).toBe("0");
        expect(checkbox.disabled).toBe(true);
        expect(document.querySelector("#delete_runs_button").disabled).toBe(true);
    });

    test("keeps a row and reports a terminal delete failure", async () => {
        installDom();
        fetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    runs: [{
                        runid: "failed-run",
                        config: "cfg",
                        readonly: false
                    }]
                })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ Content: { job_id: "job-failed" } })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ status: "failed" })
            });
        window.eval(renderedScript());
        await flushPromises();

        const checkbox = document.querySelector('tr[data-run-row="true"] input');
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        await window.deleteRuns();
        await flushPromises();

        expect(document.querySelector('tr[data-run-row="true"]')).not.toBeNull();
        expect(document.querySelector("#runs-delete-status").textContent).toBe(
            "Delete finished with 1 error."
        );
        expect(document.querySelector("#runs-delete-status").className)
            .toContain("wc-text-danger");
    });

    test("loads protected users and applies exact admin alias to catalog", async () => {
        installDom({ admin: true });
        fetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    users: [{
                        id: 42,
                        alias: "42",
                        name: "Other User",
                        email: "other@example.test",
                        label: "Other User <other@example.test>",
                        search_index: "other user other@example.test"
                    }]
                })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ runs: [] })
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ runs: [] })
            });
        window.eval(renderedScript({ admin: true }));
        await flushPromises();

        const input = document.querySelector("#runs_admin_user_search");
        input.value = "other@example.test";
        input.dispatchEvent(new Event("input"));
        document.querySelector("#runs_admin_apply_scope").click();
        await flushPromises();

        expect(fetch.mock.calls[2][0]).toContain("/runs/catalog?");
        expect(fetch.mock.calls[2][0]).toContain("alias=42");
        const status = document.querySelector("#runs_admin_scope_status");
        expect(status.textContent).toContain("Other User <other@example.test>");
        expect(status.querySelector("*")).toBeNull();
    });
});

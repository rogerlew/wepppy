/**
 * @jest-environment jsdom
 */

describe("controlBase job status error handling", () => {
    let base;
    let button;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <button id="btn_run" type="button">Run</button>
            <div id="rq_job"></div>
            <div id="stacktrace"></div>
        `;

        await import("../control_base.js");

        base = window.controlBase();
        button = document.getElementById("btn_run");

        base.command_btn_id = "btn_run";
        base.rq_job = document.getElementById("rq_job");
        base.stacktrace = document.getElementById("stacktrace");
        base.schedule_stacktrace_backfill = jest.fn();
        base.schedule_job_status_poll = jest.fn();
        base.stop_job_status_polling = jest.fn();
        base.should_continue_polling = jest.fn(() => true);
    });

    afterEach(() => {
        delete window.controlBase;
        document.body.innerHTML = "";
        jest.clearAllMocks();
    });

    test("re-enables command button when job status poll returns 502", () => {
        base.rq_job_id = "job-1";

        base.update_command_button_state(base);
        expect(button.disabled).toBe(true);

        base.handle_job_status_error(base, { status: 502, statusText: "Bad Gateway" });

        expect(base._job_status_error).toContain("502");
        expect(base.should_disable_command_button(base)).toBe(false);
        expect(button.disabled).toBe(false);
    });

    test("keeps command button disabled for non-502 job status errors", () => {
        base.rq_job_id = "job-1";

        base.update_command_button_state(base);
        expect(button.disabled).toBe(true);

        base.handle_job_status_error(base, { status: 500, statusText: "Internal Server Error" });

        expect(base._job_status_error).toContain("500");
        expect(base.should_disable_command_button(base)).toBe(true);
        expect(button.disabled).toBe(true);
    });
});

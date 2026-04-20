/**
 * @jest-environment jsdom
 */

describe("controlBase job status error handling", () => {
    let base;
    let button;
    const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <button id="btn_run" type="button">Run</button>
            <div id="rq_job"></div>
            <div id="info"></div>
            <div id="stacktrace"></div>
        `;

        await import("../control_base.js");

        base = window.controlBase();
        button = document.getElementById("btn_run");

        base.command_btn_id = "btn_run";
        base.rq_job = document.getElementById("rq_job");
        base.info = document.getElementById("info");
        base.stacktrace = document.getElementById("stacktrace");
        base.schedule_stacktrace_backfill = jest.fn();
        base.schedule_job_status_poll = jest.fn();
        base.stop_job_status_polling = jest.fn();
        base.should_continue_polling = jest.fn(() => true);
    });

    afterEach(() => {
        delete window.controlBase;
        delete window.url_for_run;
        delete window.site_prefix;
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

    test("renders error detail in job status panel", () => {
        base.rq_job_id = "job-1";

        base.handle_job_status_error(base, {
            status: 401,
            statusText: "Unauthorized",
            detail: "Authentication required."
        });

        expect(base.rq_job.innerHTML).toContain("Authentication required.");
    });

    test("set_rq_job_id mirrors canonical controller job_id", () => {
        base.fetch_job_status = jest.fn();
        base.render_job_status = jest.fn();
        base.render_job_hint = jest.fn();
        base.update_command_button_state = jest.fn();
        base.manage_status_stream = jest.fn();
        base.reset_status_spinner = jest.fn();

        base.set_rq_job_id(base, "job-42");
        expect(base.job_id).toBe("job-42");
        expect(base.rq_job_id).toBe("job-42");

        base.set_rq_job_id(base, null);
        expect(base.job_id).toBeNull();
        expect(base.rq_job_id).toBeNull();
    });

    test("set_rq_job_id mirrors normalized job id values", () => {
        base.fetch_job_status = jest.fn();
        base.render_job_status = jest.fn();
        base.render_job_hint = jest.fn();
        base.update_command_button_state = jest.fn();
        base.manage_status_stream = jest.fn();
        base.reset_status_spinner = jest.fn();

        base.set_rq_job_id(base, "  job-42  ");
        expect(base.job_id).toBe("job-42");
        expect(base.rq_job_id).toBe("job-42");

        base.set_rq_job_id(base, "   ");
        expect(base.job_id).toBeNull();
        expect(base.rq_job_id).toBeNull();
    });

    test("set_rq_job_id same-id fast path keeps mirrored job_id synced", () => {
        base.fetch_job_status = jest.fn();
        base.render_job_status = jest.fn();
        base.render_job_hint = jest.fn();
        base.update_command_button_state = jest.fn();
        base.manage_status_stream = jest.fn();
        base.reset_status_spinner = jest.fn();

        base.set_rq_job_id(base, "job-fast");
        base.fetch_job_status.mockClear();

        base.set_rq_job_id(base, "job-fast");
        expect(base.job_id).toBe("job-fast");
        expect(base.rq_job_id).toBe("job-fast");
        expect(base.fetch_job_status).toHaveBeenCalledTimes(1);
    });

    test("retries polling with session token after 401 and reuses auth mode", async () => {
        const unauthenticatedError = {
            name: "HttpError",
            status: 401,
            statusText: "Unauthorized",
            detail: "Authentication required."
        };

        const getJsonMock = jest.fn().mockRejectedValueOnce(unauthenticatedError);
        const requestWithSessionTokenMock = jest.fn()
            .mockResolvedValueOnce({ body: { status: "started" } })
            .mockResolvedValueOnce({ body: { status: "finished" } });

        window.WCHttp = {
            request: jest.fn(),
            getJson: getJsonMock,
            requestWithSessionToken: requestWithSessionTokenMock
        };

        base.should_continue_polling = jest.fn(() => false);
        base.rq_job_id = "job-1";

        base.fetch_job_status(base);
        await flushPromises();
        await flushPromises();

        expect(getJsonMock).toHaveBeenCalledTimes(1);
        expect(requestWithSessionTokenMock).toHaveBeenCalledTimes(1);
        expect(requestWithSessionTokenMock).toHaveBeenCalledWith(
            "/rq-engine/api/jobstatus/job-1",
            expect.objectContaining({
                method: "GET",
                params: expect.objectContaining({ _: expect.any(Number) })
            })
        );
        expect(base._job_status_poll_use_auth).toBe(true);
        expect(base.rq_job_status.status).toBe("started");

        base.fetch_job_status(base);
        await flushPromises();
        await flushPromises();

        expect(getJsonMock).toHaveBeenCalledTimes(1);
        expect(requestWithSessionTokenMock).toHaveBeenCalledTimes(2);
        expect(base.rq_job_status.status).toBe("finished");
    });

    test("pushResponseStacktrace writes exception message into summary panel", () => {
        base.pushResponseStacktrace(base, {
            error: { message: "Job failed." },
            stacktrace: [
                "Traceback (most recent call last):",
                "  File \"/workdir/wepppy/wepppy/soils/ssurgo/ssurgo.py\", line 339, in _makeSOAPrequest",
                "    raise SsurgoRequestError(message) from exc",
                "wepppy.soils.ssurgo.ssurgo.SsurgoRequestError: https://sdmdataaccess.nrcs.usda.gov SSURGO API is not available. Try again later."
            ]
        });

        expect(document.getElementById("info").textContent).toBe(
            "https://sdmdataaccess.nrcs.usda.gov SSURGO API is not available. Try again later."
        );
        expect(document.getElementById("stacktrace").textContent).toContain(
            "wepppy.soils.ssurgo.ssurgo.SsurgoRequestError"
        );
    });

    test("pushResponseStacktrace links clearing-lock docs with site prefix from url_for_run", () => {
        const urlForRun = jest.fn(() => "/weppcloud/usersum/doc/usersum.weppcloud.clearing_locks");
        window.url_for_run = urlForRun;

        base.pushResponseStacktrace(base, {
            error: { message: "Job failed." },
            stacktrace: [
                "Traceback (most recent call last):",
                "lock() called on an already locked nodb"
            ]
        });

        expect(urlForRun).toHaveBeenCalledWith("usersum/doc/usersum.weppcloud.clearing_locks", { runId: "", config: "" });
        expect(document.getElementById("stacktrace").innerHTML).toContain(
            'href="/weppcloud/usersum/doc/usersum.weppcloud.clearing_locks"'
        );
    });
});

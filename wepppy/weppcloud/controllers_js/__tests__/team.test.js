/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Team controller", () => {
    let requestMock;
    let postJsonMock;
    let baseInstance;
    let statusStreamMock;
    let triggerEventMock;
    let team;

    const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="team_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="team_status_panel"></div>
                <div id="team_stacktrace_panel"></div>
                <input id="adduser-email"
                       name="adduser-email"
                       data-team-field="email"
                       value="">
                <button id="btn_adduser" type="button" data-team-action="invite"></button>
                <div id="team-info"></div>
                <p id="hint_run_team"></p>
            </form>
        `;

        global.runid = "run-123";
        global.config = "cfg";
        global.site_prefix = "/weppcloud";

        triggerEventMock = jest.fn();
        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            triggerEvent: triggerEventMock,
            stacktrace: document.getElementById("stacktrace")
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        global.StatusStream = undefined;

        requestMock = jest.fn(() => Promise.resolve({ body: "<p>initial roster</p>" }));
        postJsonMock = jest.fn(() => Promise.resolve({ body: { Success: true, Content: { user_id: 2 } } }));

        global.WCHttp = {
            request: requestMock,
            postJson: postJsonMock,
            isHttpError: jest.fn(() => false)
        };

        await import("../dom.js");
        await import("../forms.js");
        await import("../events.js");

        global.url_for_run = jest.fn((path) => path);

        await import("../team.js");

        team = window.Team.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Team;
        delete global.WCHttp;
        delete global.controlBase;
        delete global.StatusStream;
        delete global.runid;
        delete global.config;
        delete global.site_prefix;
        delete global.url_for_run;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        document.body.innerHTML = "";
    });

    test("initializes and loads collaborator list", async () => {
        const handler = jest.fn();
        team.events.on("team:list:loaded", handler);
        team.bootstrap({ user: { isAuthenticated: true } });

        await flushPromises();

        expect(global.url_for_run).toHaveBeenCalledWith("report/users/");
        expect(requestMock).toHaveBeenCalledWith("report/users/", expect.objectContaining({ method: "GET" }));
        expect(document.querySelector("#team-info").innerHTML).toContain("initial roster");
        await team.refreshMembers({ silentStatus: true });
        expect(handler).toHaveBeenCalled();
        expect(handler.mock.calls.pop()[0]).toEqual(expect.objectContaining({ html: "<p>initial roster</p>" }));
    });

    test("inviteCollaborator posts email payload and refreshes roster", async () => {
        await flushPromises();
        requestMock.mockClear();

        const inviteHandler = jest.fn();
        team.events.on("team:invite:sent", inviteHandler);

        const result = team.inviteCollaborator(" collaborator@example.com ");
        await result;

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/adduser/",
            { email: "collaborator@example.com" },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(triggerEventMock).toHaveBeenCalledWith(
            "TEAM_ADDUSER_TASK_COMPLETED",
            expect.objectContaining({ email: "collaborator@example.com" })
        );
        expect(inviteHandler).toHaveBeenCalledWith(
            expect.objectContaining({ email: "collaborator@example.com" })
        );
        expect(requestMock).toHaveBeenCalledTimes(1);
        expect(document.getElementById("adduser-email").value).toBe("");
    });

    test("removeMemberById posts collaborator id and emits events", async () => {
        await flushPromises();
        requestMock.mockClear();
        postJsonMock.mockResolvedValueOnce({ body: { Success: true, Content: { user_id: 77 } } });

        const removedHandler = jest.fn();
        team.events.on("team:member:removed", removedHandler);

        await team.removeMemberById(77);

        expect(postJsonMock).toHaveBeenCalledWith(
            "tasks/removeuser/",
            { user_id: 77 },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(removedHandler).toHaveBeenCalledWith(
            expect.objectContaining({ userId: 77 })
        );
        expect(triggerEventMock).toHaveBeenCalledWith(
            "TEAM_REMOVEUSER_TASK_COMPLETED",
            expect.objectContaining({ user_id: 77 })
        );
    });

    test("inviteCollaborator surfaces errors through stacktrace", async () => {
        await flushPromises();
        requestMock.mockClear();

        const error = new Error("boom");
        error.detail = { Error: "Failed" };
        global.WCHttp.isHttpError.mockReturnValueOnce(true);
        postJsonMock.mockRejectedValueOnce(error);

        const failedHandler = jest.fn();
        team.events.on("team:invite:failed", failedHandler);

        await expect(team.inviteCollaborator("user@example.com")).rejects.toEqual(
            expect.objectContaining({ Error: "Failed" })
        );
        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalled();
        expect(failedHandler).toHaveBeenCalledWith(
            expect.objectContaining({ error: expect.objectContaining({ Error: "Failed" }) })
        );
        expect(triggerEventMock).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "team:adduser" })
        );
        expect(document.getElementById("btn_adduser").disabled).toBe(false);
    });
});

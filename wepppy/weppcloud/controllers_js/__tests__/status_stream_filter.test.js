/** @jest-environment jsdom */

test("filtered status messages cannot append, trigger, or enrich stale details", async () => {
    await import("../status_stream.js");
    document.body.innerHTML = `
        <div id="panel"><div data-status-log></div></div>
        <details id="errors"><div data-stacktrace-body></div></details>
    `;
    const socket = { close: jest.fn() };
    window.WCHttp = { createStreamConnection: jest.fn(() => socket) };
    let selected = "old";
    let finishDetails;
    const fetchJobInfo = jest.fn(() => new Promise(resolve => { finishDetails = resolve; }));
    const onTrigger = jest.fn();
    const onAppend = jest.fn();
    const panel = document.getElementById("errors");
    const body = panel.querySelector("[data-stacktrace-body]");
    const stream = window.StatusStream.attach({
        element: "#panel", channel: "climate",
        stacktrace: { element: panel, body, fetchJobInfo },
        filterMessage: message => message.startsWith(`rq:${selected} `),
        onTrigger, onAppend,
    });
    const send = message => socket.onmessage({ data: JSON.stringify({ type: "status", data: message }) });

    send("rq:another TRIGGER climate CLIMATE_BUILD_TASK_COMPLETED");
    expect(onAppend).not.toHaveBeenCalled();
    expect(onTrigger).not.toHaveBeenCalled();
    send("rq:old EXCEPTION old job");
    expect(fetchJobInfo).toHaveBeenCalledWith("old");
    selected = "new";
    body.textContent = "Current diagnostics";
    finishDetails("Old details");
    await Promise.resolve();
    expect(body.textContent).toBe("Current diagnostics");

    send("rq:new TRIGGER climate CLIMATE_BUILD_TASK_COMPLETED");
    expect(onTrigger).toHaveBeenCalledTimes(1);
    stream.disconnect();
    delete window.WCHttp;
});

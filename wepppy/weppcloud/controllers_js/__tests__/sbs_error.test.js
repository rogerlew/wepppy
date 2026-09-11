/** @jest-environment jsdom */
describe("SBS error Details", () => {
    let controller;
    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = '<form><div id="info"><table><tr><td>Accepted map</td></tr></table></div><p data-job-hint></p><details data-stacktrace-panel hidden><div id="stacktrace"></div></details></form>';
        controller = {form:document.querySelector("form"),stacktrace:{text:jest.fn()},pushResponseStacktrace:jest.fn()};
        await import("../sbs_error.js");
    });
    afterEach(() => { delete window.WCSbsError; document.body.innerHTML = ""; });
    const failure = body => ({body,response:{headers:{get:()=>"text/html; charset=utf-8"}}});
    test("renders gateway HTML only in Details and reveals the panel", () => {
        window.WCSbsError.show(controller, {}, failure('<html><body><h1>504 Gateway Time-out</h1><p>Server timed out.</p></body></html>'));
        expect(document.querySelector("#stacktrace h1").textContent).toBe("504 Gateway Time-out");
        expect(document.querySelector("details").open).toBe(true);
        expect(document.querySelector("details").hidden).toBe(false);
        expect(document.querySelector("#info table").textContent).toBe("Accepted map");
        expect(document.querySelector("[data-job-hint]").textContent).toBe("");
    });
    test("discards active, foreign, custom and resource subtrees and all attributes", () => {
        const html='<h1 id="clobber" onclick="evil()" style="color:red">Error</h1><script>evil()</script><img src="https://invalid.test/pixel"><iframe srcdoc="bad"></iframe><svg><text>foreign</text></svg><form><p>form content</p></form><x-evil><p>custom content</p></x-evil><table><tbody><tr><td onmouseover="evil()">Detail</td></tr></tbody></table>';
        window.WCSbsError.show(controller,{},failure(html));
        const details=document.querySelector("#stacktrace");
        expect(details.querySelector("script,img,iframe,svg,form,x-evil")).toBeNull();
        expect(details.textContent).toBe("ErrorDetail");
        Array.from(details.querySelectorAll("*")).forEach(node=>expect(node.attributes).toHaveLength(0));
        expect(details.querySelector("table td").textContent).toBe("Detail");
    });
    test.each([["map", "summary"], ["summary", "map"]])("a successful %s request retains the %s error", (success, failed) => {
        window.WCSbsError.show(controller, {}, failure("<h1>" + failed + " failed</h1>"), failed);
        expect(window.WCSbsError.clear(controller, success)).toBe(false);
        expect(document.querySelector("#stacktrace h1").textContent).toBe(failed + " failed");
        expect(window.WCSbsError.clear(controller, failed)).toBe(true);
        expect(document.querySelector("details").hidden).toBe(true);
    });
    test("JSON markup uses the normal text renderer without Summary targets", () => {
        const payload={error:{message:"<h1>literal diagnostic</h1>"}};
        window.WCSbsError.show(controller,payload,{body:payload,response:{headers:{get:()=>"application/json"}}});
        expect(controller.pushResponseStacktrace).toHaveBeenCalledWith({stacktrace:controller.stacktrace},payload);
        expect(document.querySelector("#stacktrace h1")).toBeNull();
        expect(document.querySelector("#info").textContent).toBe("Accepted map");
    });
});

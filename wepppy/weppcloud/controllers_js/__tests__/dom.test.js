/**
 * @jest-environment jsdom
 */

beforeAll(async () => {
    await import("../dom.js");
});

describe("WCDom helpers", () => {
    let WCDom;

    beforeAll(() => {
        WCDom = window.WCDom;
    });

    beforeEach(() => {
        document.body.innerHTML = `
            <div id="root">
                <button class="btn" type="button">Tap</button>
                <div class="panel hidden" hidden></div>
                <ul class="list">
                    <li class="item">One</li>
                    <li class="item">Two</li>
                </ul>
            </div>
        `;
    });

    test("qs resolves selector strings to elements", () => {
        const button = WCDom.qs(".btn");
        expect(button).not.toBeNull();
        expect(button.tagName).toBe("BUTTON");
        expect(WCDom.qs("#missing")).toBeNull();
    });

    test("qsa returns arrays, including from NodeList inputs", () => {
        const list = WCDom.qs(".list");
        const itemsFromSelector = WCDom.qsa(".item", list);
        expect(Array.isArray(itemsFromSelector)).toBe(true);
        expect(itemsFromSelector).toHaveLength(2);

        const nodeList = list.querySelectorAll(".item");
        const itemsFromNodeList = WCDom.qsa(nodeList);
        expect(itemsFromNodeList).toHaveLength(2);
        expect(itemsFromNodeList[0].textContent).toBe("One");
    });

    test("delegate handles bubbling events and unsubscribes cleanly", () => {
        const root = WCDom.qs("#root");
        const handler = jest.fn((event, matched) => {
            expect(event).toBeInstanceOf(Event);
            expect(matched).toBeInstanceOf(Element);
            expect(matched.classList.contains("item")).toBe(true);
        });

        const unsubscribe = WCDom.delegate(root, "click", ".item", handler);
        const target = WCDom.qs(".item");

        target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(handler).toHaveBeenCalledTimes(1);

        unsubscribe();
        target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        expect(handler).toHaveBeenCalledTimes(1);
    });

    test("toggleClass honours force argument and visibility helpers", () => {
        const panel = WCDom.qs(".panel");
        WCDom.toggleClass(panel, "hidden", false);
        expect(panel.classList.contains("hidden")).toBe(false);

        WCDom.hide(panel);
        expect(panel.hidden).toBe(true);

        WCDom.show(panel);
        expect(panel.hidden).toBe(false);
    });
});

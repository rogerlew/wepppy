/* global __dirname */
/** @jest-environment jsdom */
const fs = require('fs');
const path = require('path');

describe('post-fire preflight navigation', () => {
    let update;
    beforeEach(() => {
        document.body.innerHTML = '<a href="#rusle">RUSLE</a><a href="#postfire-debris-flow">Post-fire debris flow</a><a href="#debris-flow">Debris Flow</a>';
        window.readonly = false;
        window.tocTaskEmojis = {'#postfire-debris-flow': '🌋', '#debris-flow': '🪨'};
        const source = fs.readFileSync(path.resolve(__dirname, '../../static/js/preflight.js'), 'utf8');
        update = new Function(source + '\nreturn updateUI;')();
    });
    afterEach(() => {
        delete window.readonly;
        delete window.tocTaskEmojis;
    });
    test('uses shared emoji metadata and preserves labels through invalidation', () => {
        const anchor = document.querySelector('a[href="#postfire-debris-flow"]');
        update({postfire_debris_flow: true, debris: false});
        expect(anchor.getAttribute('data-toc-emoji')).toBe('🌋');
        expect(anchor.textContent).toBe('Post-fire debris flow');
        expect(document.querySelector('a[href="#debris-flow"]').getAttribute('data-toc-emoji')).toBe('');
        update({postfire_debris_flow: false});
        expect(anchor.getAttribute('data-toc-emoji')).toBe('');
        expect(anchor.textContent).toBe('Post-fire debris flow');
    });
    test('retains the shared read-only indicator behavior', () => {
        window.readonly = true;
        update({postfire_debris_flow: true});
        expect(document.querySelector('a[href="#postfire-debris-flow"]').getAttribute('data-toc-emoji')).toBe('');
    });
});

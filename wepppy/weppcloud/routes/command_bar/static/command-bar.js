// wepppy/weppcloud/routes/command_bar/static/js/command-bar.js
//
// Developer notes live in `wepppy/weppcloud/routes/command_bar/README.md`. See that document for quick-start
// guidance on registering commands, server routes, and hover previews.
(() => {
    'use strict';

    const KEY_TRIGGER = ':';
    const TIP_DEFAULT = "Tip: Press ':' to activate the command bar. :help for commands.";
    const TIP_ACTIVE = 'Command mode - press Enter to run, Esc to cancel';
    const INSTANCE_DATA_KEY = '__commandBarInstance';
    const GLOBAL_INSTANCE_KEY = '__wepppyCommandBarInstance';
    const STAY_ACTIVE_COMMANDS = new Set(['help', 'status']);
    const SET_HELP_LINES = [
        "set units <si|english>    - Switch global unit preferences",
        "set name <project name>   - Update the project name",
        "set scenario <name>       - Update the project scenario",
        "set outlet                - Use cursor location for outlet delineation",
        "set readonly <true|false> - Toggle project readonly mode",
        "set public <true|false>   - Toggle project public visibility",
        "set loglevel <debug|info|warning|error|critical> - Update project log verbosity",
        "set channel_critical_shear <value> - Add a custom channel critical shear option"
    ];
    const CLEAR_HELP_LINES = [
        'clear locks         - Clear NoDb locks',
        'clear nodb_cache    - Clear Redis NoDb cache entries'
    ];

    class CommandBar {
        constructor(container) {
            this.container = container;
            this.tipEl = container.querySelector('[data-command-tip]');
            this.resultEl = container.querySelector('[data-command-result]');
            this.inputWrapperEl = container.querySelector('[data-command-input-wrapper]');
            this.inputEl = container.querySelector('[data-command-input]');
            this.handleBeforeUnload = null;
            this.handlePageHide = null;
            this.handlePageShow = null;
            this.handleVisibilityChange = null;

            this.active = false;
            this.commandHistory = [];
            this.historyIndex = 0;
            this.historySnapshot = '';
            this.projectBaseUrl = this.getProjectBaseUrl();
            this.getCommandHandlers = this.createGetCommandHandlers();
            this.runCommandHandlers = this.createRunCommandHandlers();
            this.commands = this.createCommands();
            this.commandChannelSocket = null;
            this.commandChannelReconnectTimer = null;
            this.commandChannelReconnectDelayMs = 2000;
            this.commandChannelUrl = this.getCommandChannelUrl();
            this.commandChannelShouldReconnect = false;
            this.destroyed = false;

            this.handleDocumentKeyDown = this.handleDocumentKeyDown.bind(this);
            this.handleInputKeyDown = this.handleInputKeyDown.bind(this);
            this.handleCommandChannelOpen = this.handleCommandChannelOpen.bind(this);
            this.handleCommandChannelMessage = this.handleCommandChannelMessage.bind(this);
            this.handleCommandChannelClose = this.handleCommandChannelClose.bind(this);
            this.handleCommandChannelError = this.handleCommandChannelError.bind(this);
            this.onBeforeUnload = this.onBeforeUnload.bind(this);
            this.onPageHide = this.onPageHide.bind(this);
            this.onPageShow = this.onPageShow.bind(this);
            this.onVisibilityChange = this.onVisibilityChange.bind(this);
        }

        init() {
            if (!this.tipEl || !this.resultEl || !this.inputWrapperEl || !this.inputEl) {
                console.warn('CommandBar: Missing required elements in the template.');
                return;
            }

            this.tipEl.textContent = TIP_DEFAULT;
            this.hideResult();
            this.deactivate();

            document.addEventListener('keydown', this.handleDocumentKeyDown);
            this.inputEl.addEventListener('keydown', this.handleInputKeyDown);

            this.connectCommandChannel();
            this.handleBeforeUnload = this.onBeforeUnload;
            window.addEventListener('beforeunload', this.handleBeforeUnload, { once: true });

            this.handlePageHide = this.onPageHide;
            this.handlePageShow = this.onPageShow;
            window.addEventListener('pagehide', this.handlePageHide);
            window.addEventListener('pageshow', this.handlePageShow);

            this.handleVisibilityChange = this.onVisibilityChange;
            document.addEventListener('visibilitychange', this.handleVisibilityChange);
        }

        destroy() {
            if (this.destroyed) {
                return;
            }
            this.destroyed = true;

            document.removeEventListener('keydown', this.handleDocumentKeyDown);
            if (this.inputEl) {
                this.inputEl.removeEventListener('keydown', this.handleInputKeyDown);
            }

            if (this.handleBeforeUnload) {
                window.removeEventListener('beforeunload', this.handleBeforeUnload);
                this.handleBeforeUnload = null;
            }

            if (this.handlePageHide) {
                window.removeEventListener('pagehide', this.handlePageHide);
                this.handlePageHide = null;
            }

            if (this.handlePageShow) {
                window.removeEventListener('pageshow', this.handlePageShow);
                this.handlePageShow = null;
            }

            if (this.handleVisibilityChange) {
                document.removeEventListener('visibilitychange', this.handleVisibilityChange);
                this.handleVisibilityChange = null;
            }

            this.commandChannelShouldReconnect = false;
            this.clearCommandChannelReconnect();
            this.disconnectCommandChannel();

            if (this.container && this.container[INSTANCE_DATA_KEY] === this) {
                delete this.container[INSTANCE_DATA_KEY];
            }

            if (window[GLOBAL_INSTANCE_KEY] === this) {
                delete window[GLOBAL_INSTANCE_KEY];
            }

            this.container = null;
            this.tipEl = null;
            this.resultEl = null;
            this.inputWrapperEl = null;
            this.inputEl = null;
        }

        onBeforeUnload() {
            this.disconnectCommandChannel();
        }

        onPageHide() {
            this.disconnectCommandChannel();
        }

        onPageShow(event) {
            if (event && event.persisted) {
                window.requestAnimationFrame(() => this.connectCommandChannel());
                return;
            }
            this.connectCommandChannel();
        }

        onVisibilityChange() {
            if (document.visibilityState === 'hidden') {
                this.disconnectCommandChannel();
                return;
            }
            if (document.visibilityState === 'visible') {
                this.connectCommandChannel();
            }
        }

        focusInput(selectAll = false) {
            if (!this.inputEl) {
                return;
            }

            const applyFocus = () => {
                try {
                    this.inputEl.focus({ preventScroll: true });
                } catch (error) {
                    this.inputEl.focus();
                }

                if (selectAll) {
                    if (typeof this.inputEl.select === 'function') {
                        this.inputEl.select();
                    }
                }
            };

            applyFocus();

            if (document.activeElement !== this.inputEl) {
                window.requestAnimationFrame(applyFocus);
            }
        }

        createGetCommandHandlers() {
            return {
                loadavg: {
                    description: 'Show server load averages (1, 5, 15 minute windows)',
                    handler: (args) => this.routeGetLoadAvg(args)
                },
                locks: {
                    description: 'Show active NoDb file locks for this run',
                    handler: (args) => this.routeGetLocks(args)
                },
                query_engine_mcp_token: {
                    description: 'Generate a short-lived Query Engine MCP token with setup instructions',
                    handler: (args) => this.routeGetQueryEngineMcpToken(args)
                }
            };
        }

        createRunCommandHandlers() {
            return {
                interchange_migration: {
                    description: 'Queue an interchange migration job for this run (optional subpath)',
                    handler: (args) => this.routeRunInterchangeMigration(args)
                }
            };
        }

        createCommands() {
            return {
                help: {
                    description: 'Show available commands',
                    action: () => this.showHelp()
                },
                get: {
                    description: 'Run GET utility commands (e.g., loadavg)',
                    action: (args) => this.handleGetCommand(args)
                },
                run: {
                    description: 'Run project automation tasks (e.g., interchange_migration)',
                    action: (args) => this.handleRunCommand(args)
                },
                usersum: {
                    description: '',
                    action: (args) => this.routeUsersum(args)
                },
                map: {
                    description: 'Navigate to Map',
                    action: () => this.navigateToSelector('a[href^="#map"]')
                },
                sbs: {
                    description: 'Navigate to Soil Burn Severity',
                    action: () => this.navigateToSelector('a[href^="#soil-burn-severity-optional"]')
                },
                set: {
                    description: '',
                    action: (args) => this.handleSetCommand(args)
                },
                channels: {
                    description: 'Navigate to Channel Delineation',
                    action: () => this.navigateToSelector('a[href="#channel-delineation"]')
                },
                outlet: {
                    description: 'Navigate to Outlet',
                    action: () => this.navigateToSelector('a[href="#outlet"]')
                },
                subcatchments: {
                    description: 'Navigate to Subcatchments Delineation',
                    action: () => this.navigateToSelector('a[href="#subcatchments-delineation"]')
                },
                landuse: {
                    description: 'Navigate to Landuse Options',
                    action: () => this.navigateToSelector('a[href="#landuse-options"]')
                },
                soils: {
                    description: 'Navigate to Soil Options',
                    action: () => this.navigateToSelector('a[href="#soil-options"]')
                },
                climate: {
                    description: 'Navigate to Climate Options',
                    action: () => this.navigateToSelector('a[href="#climate-options"]')
                },
                rap_ts: {
                    description: 'Navigate to RAP Time Series Acquisition',
                    action: () => this.navigateToSelector('a[href="#rap-time-series-acquisition"]')
                },
                wepp: {
                    description: 'Navigate to WEPP',
                    action: () => this.navigateToSelector('a[href="#wepp"]')
                },
                observed: {
                    description: 'Navigate to Observed Data Model Fit',
                    action: () => this.navigateToSelector('a[href="#observed-data-model-fit"]')
                },
                debris: {
                    description: 'Navigate to Debris Flow Analysis',
                    action: () => this.navigateToSelector('a[href="#debris-flow-analysis"]')
                },
                watar: {
                    description: 'Navigate to Wildfire Ash Transport and Risk (WATAR)',
                    action: () => this.navigateToSelector('a[href="#wildfire-ash-transport-and-risk-watar"]')
                },
                dss_export: {
                    description: 'Navigate to Partitioned DSS Export for HEC',
                    action: () => this.navigateToSelector('a[href="#partitioned-dss-export-for-hec"]')
                },
                browse: {
                    description: 'Go to the project file browser (optionally jump to a resource)',
                    action: (args) => this.navigateToProjectBrowse(args)
                },
                clear: {
                    description: 'Clear run resources (locks, cache)',
                    action: (args) => this.handleClearCommand(args)
                }
            };
        }

        shouldIgnoreTriggerTarget(target) {
            if (!target) {
                return false;
            }
            const tagName = target.tagName;
            return target.isContentEditable || tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT';
        }

        isPrintableKey(event) {
            if (!event || typeof event.key !== 'string') {
                return false;
            }

            if (event.ctrlKey || event.metaKey || event.altKey) {
                return false;
            }

            return event.key.length === 1 && event.key !== 'Unidentified';
        }

        insertPrintableKey(key) {
            if (!this.inputEl || typeof key !== 'string') {
                return;
            }

            const { selectionStart, selectionEnd, value } = this.inputEl;

            if (selectionStart === null || selectionEnd === null) {
                this.inputEl.value = `${value}${key}`;
                return;
            }

            const start = Math.min(selectionStart, selectionEnd);
            const end = Math.max(selectionStart, selectionEnd);
            const before = value.slice(0, start);
            const after = value.slice(end);

            this.inputEl.value = `${before}${key}${after}`;
            const newCaretPosition = before.length + key.length;
            if (typeof this.inputEl.setSelectionRange === 'function') {
                this.inputEl.setSelectionRange(newCaretPosition, newCaretPosition);
            }
        }

        handleDocumentKeyDown(event) {
            if (this.active) {
                if (event.key === 'Escape') {
                    event.preventDefault();
                    this.deactivate();
                    return;
                }

                if (event.target === this.inputEl || this.shouldIgnoreTriggerTarget(event.target)) {
                    return;
                }

                if (this.isPrintableKey(event)) {
                    event.preventDefault();
                    this.focusInput();
                    this.insertPrintableKey(event.key);
                } else {
                    this.focusInput();
                }
                return;
            }

            if (event.key === KEY_TRIGGER && !this.shouldIgnoreTriggerTarget(event.target)) {
                event.preventDefault();
                this.activate();
            }

            if (!event.shiftKey) {
                return;
            }

            if (this.shouldIgnoreTriggerTarget(event.target)) {
                return;
            }

            // Use a switch statement for different key presses
            switch (event.key.toUpperCase()) {
            case 'G':
                event.preventDefault(); // Prevent any default browser action
                window.scrollTo(0, document.body.scrollHeight);
                break;
            case 'T':
                event.preventDefault(); // Prevent any default browser action
                window.scrollTo(0, 0);
                break;
            case 'U':
                event.preventDefault();
                // Scroll up by 90% of the window's height for context overlap
                window.scrollBy(0, -window.innerHeight * 0.9);
                break;
            case 'H':
                event.preventDefault();
                // Scroll down by 90% of the window's height
                window.scrollBy(0, window.innerHeight * 0.9);
                break;
            }
        }

        handleInputKeyDown(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const enteredCommand = this.inputEl.value.trim();
                if (enteredCommand) {
                    this.rememberCommand(enteredCommand);
                }
                this.executeCommand(enteredCommand);
                this.resetHistoryNavigation();
            } else if (event.key === 'Escape') {
                event.preventDefault();
                this.deactivate();
                this.hideResult();
            } else if (event.key === 'ArrowUp') {
                if (this.commandHistory.length > 0) {
                    event.preventDefault();
                    this.navigateHistory(-1);
                }
            } else if (event.key === 'ArrowDown') {
                if (this.commandHistory.length > 0) {
                    event.preventDefault();
                    this.navigateHistory(1);
                }
            }
        }

        activate() {
            this.active = true;
            this.inputWrapperEl.hidden = false;
            this.tipEl.textContent = TIP_ACTIVE;
            this.inputEl.value = '';
            this.focusInput();
            this.resetHistoryNavigation();
        }

        deactivate() {
            this.active = false;
            this.inputWrapperEl.hidden = true;
            this.tipEl.textContent = TIP_DEFAULT;
            this.inputEl.value = '';
            if (document.activeElement === this.inputEl) {
                this.inputEl.blur();
            }
            this.resetHistoryNavigation();
        }

        executeCommand(fullCommand) {
            if (!fullCommand) {
                this.deactivate();
                return;
            }

            if (fullCommand.startsWith(KEY_TRIGGER)) {
                fullCommand = fullCommand.slice(1).trim();
            }
            
            const [commandName, ...rawArgs] = fullCommand.split(/\s+/);
            const command = this.commands[commandName.toLowerCase()];

            if (!command) {
                this.showResult(`Error: Command not found "${commandName}"`);
                this.deactivate();
                return;
            }

            try {
                const result = command.action(rawArgs);
                if (result instanceof Promise) {
                    result.catch((error) => {
                        console.error('CommandBar error:', error);
                        this.showResult(`Error: ${error.message || 'Unknown error'}`);
                    });
                }
            } catch (error) {
                console.error('CommandBar error:', error);
                this.showResult(`Error: ${error.message || 'Unknown error'}`);
            }

            if (!STAY_ACTIVE_COMMANDS.has(commandName.toLowerCase())) {
                this.deactivate();
            }
        }

        showResult(message) {
            this.resultEl.hidden = false;
            this.resultEl.textContent = '';
            if (message && typeof message === 'object' && 'nodeType' in message) {
                this.resultEl.appendChild(message);
                return;
            }
            const pre = document.createElement('pre');
            pre.textContent = String(message ?? '');
            this.resultEl.appendChild(pre);
        }

        hideResult() {
            this.resultEl.hidden = true;
            this.resultEl.textContent = '';
        }

        rememberCommand(commandText) {
            if (!commandText) {
                return;
            }

            this.commandHistory.push(commandText);
            this.resetHistoryNavigation();
        }

        navigateHistory(direction) {
            if (!this.inputEl) {
                return;
            }

            if (this.historyIndex === this.commandHistory.length) {
                this.historySnapshot = this.inputEl.value;
            }

            const nextIndex = this.historyIndex + direction;

            if (nextIndex < 0) {
                this.historyIndex = 0;
            } else if (nextIndex > this.commandHistory.length) {
                this.historyIndex = this.commandHistory.length;
            } else {
                this.historyIndex = nextIndex;
            }

            if (this.historyIndex === this.commandHistory.length) {
                this.inputEl.value = this.historySnapshot;
            } else {
                this.inputEl.value = this.commandHistory[this.historyIndex] || '';
            }

            this.focusInput(true);
        }

        resetHistoryNavigation() {
            this.historyIndex = this.commandHistory.length;
            this.historySnapshot = '';
        }

        showHelp() {
            const lines = Object.entries(this.commands)
                .filter(([, meta]) => !(meta && meta.description === ''))
                .map(([name, meta]) => {
                    const description = meta && meta.description ? ` - ${meta.description}` : '';
                    return `${name.padEnd(10)}${description}`;
                })
                .join('\n');
            const setHelp = SET_HELP_LINES.map((line) => `  ${line}`).join('\n');
            const clearHelp = CLEAR_HELP_LINES.map((line) => `  ${line}`).join('\n');
            const keyboardShortcuts = 'Navigation shortcuts:\n   Shift+G go to bottom  |  Shift+T go to top  |  Shift+U page up  |  Shift+H page down';
            const getHelpLines = this.buildGetCommandHelpLines();
            const runHelpLines = this.buildRunCommandHelpLines();
            const usersumUsage = [
                'usersum command usage:',
                '  usersum <parameter> - concise description',
                '  usersum <parameter> -e or --extended - include extended details',
                '  usersum -k <keyword> - keyword search across parameters'
            ].join('\n');

            const sections = [
                `Available Commands:\n${lines}`,
                `Clear command usage:\n${clearHelp}`,
                `Set command usage:\n${setHelp}`,
                usersumUsage
            ];

            if (getHelpLines.length) {
                sections.push(`Get command usage:\n${getHelpLines.join('\n')}`);
            }
            if (runHelpLines.length) {
                sections.push(`Run command usage:\n${runHelpLines.join('\n')}`);
            }

            sections.push(keyboardShortcuts);

            this.showResult(sections.join('\n\n'));
        }

        getProjectBaseUrl() {
            const match = window.location.pathname.match(/^(?:\/weppcloud)?\/runs\/[^\/]+\/[^\/]+\//);
            return match ? match[0] : null;
        }

        getRunContextFromPath() {
            const match = window.location.pathname.match(/^(?:\/weppcloud)?\/runs\/([^\/]+)\/([^\/]+)\//);
            if (!match) {
                return null;
            }
            return {
                runId: match[1],
                config: match[2]
            };
        }

        getCommandChannelUrl() {
            const context = this.getRunContextFromPath();
            if (!context || !context.runId) {
                return null;
            }
            const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const host = window.location.host;
            return `${protocol}://${host}/weppcloud-microservices/status/${context.runId}:command`;
        }

        connectCommandChannel() {
            if (!this.commandChannelUrl) {
                return;
            }
            if (typeof window.WebSocket !== 'function') {
                console.warn('CommandBar: WebSocket is not supported in this environment.');
                return;
            }
            this.commandChannelShouldReconnect = true;
            if (this.commandChannelSocket &&
                (this.commandChannelSocket.readyState === WebSocket.OPEN ||
                this.commandChannelSocket.readyState === WebSocket.CONNECTING)) {
                return;
            }

            this.clearCommandChannelReconnect();

            try {
                this.commandChannelSocket = new WebSocket(this.commandChannelUrl);
            } catch (error) {
                console.warn('CommandBar: Unable to open command channel socket:', error);
                this.scheduleCommandChannelReconnect();
                return;
            }

            this.commandChannelSocket.addEventListener('open', this.handleCommandChannelOpen);
            this.commandChannelSocket.addEventListener('message', this.handleCommandChannelMessage);
            this.commandChannelSocket.addEventListener('close', this.handleCommandChannelClose);
            this.commandChannelSocket.addEventListener('error', this.handleCommandChannelError);
        }

        disconnectCommandChannel() {
            this.clearCommandChannelReconnect();
            this.commandChannelShouldReconnect = false;
            if (this.commandChannelSocket) {
                try {
                    this.commandChannelSocket.removeEventListener('open', this.handleCommandChannelOpen);
                    this.commandChannelSocket.removeEventListener('message', this.handleCommandChannelMessage);
                    this.commandChannelSocket.removeEventListener('close', this.handleCommandChannelClose);
                    this.commandChannelSocket.removeEventListener('error', this.handleCommandChannelError);
                    this.commandChannelSocket.close();
                } catch (error) {
                    console.warn('CommandBar: Error closing command channel socket:', error);
                }
                this.commandChannelSocket = null;
            }
        }

        scheduleCommandChannelReconnect() {
            this.clearCommandChannelReconnect();
            this.commandChannelReconnectTimer = window.setTimeout(() => {
                this.commandChannelReconnectTimer = null;
                this.connectCommandChannel();
            }, this.commandChannelReconnectDelayMs);
        }

        clearCommandChannelReconnect() {
            if (this.commandChannelReconnectTimer !== null) {
                window.clearTimeout(this.commandChannelReconnectTimer);
                this.commandChannelReconnectTimer = null;
            }
        }

        handleCommandChannelOpen() {
            this.commandChannelReconnectDelayMs = 2000;
            if (this.commandChannelSocket && this.commandChannelSocket.readyState === WebSocket.OPEN) {
                try {
                    this.commandChannelSocket.send(JSON.stringify({ type: 'init' }));
                } catch (error) {
                    console.warn('CommandBar: Unable to send init message on command channel:', error);
                }
            }
        }

        handleCommandChannelMessage(event) {
            const processed = this.processCommandChannelPayload(event && event.data);
            if (!processed) {
                return;
            }
            const { message } = processed;
            if (typeof message === 'string' && message.trim().length > 0) {
                this.showResult(message.trim());
            }
        }

        handleCommandChannelClose() {
            this.commandChannelSocket = null;
            if (!this.commandChannelShouldReconnect) {
                return;
            }
            this.commandChannelReconnectDelayMs = Math.min(this.commandChannelReconnectDelayMs * 2, 30000);
            this.scheduleCommandChannelReconnect();
        }

        handleCommandChannelError(event) {
            console.warn('CommandBar: Command channel socket error:', event);
            if (this.commandChannelSocket) {
                try {
                    this.commandChannelSocket.close();
                } catch (error) {
                    console.warn('CommandBar: Error closing command channel socket after error:', error);
                }
            }
        }

        processCommandChannelPayload(rawData) {
            if (rawData === undefined || rawData === null) {
                return null;
            }

            if (typeof rawData === 'string') {
                const trimmed = rawData.trim();
                if (!trimmed) {
                    return null;
                }

                if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
                    const parsed = this.tryParseJson(trimmed);
                    if (parsed) {
                        return this.handleStructuredCommandPayload(parsed);
                    }
                }

                const legacyMessage = this.stripCommandBarMarker(trimmed);
                if (!legacyMessage) {
                    return null;
                }
                return { message: legacyMessage };
            }

            if (rawData instanceof Blob) {
                // Unsupported payload; skip but warn.
                console.warn('CommandBar: Received unsupported Blob message from command channel.');
                return null;
            }

            if (typeof rawData === 'object') {
                const handled = this.handleStructuredCommandPayload(rawData);
                if (handled) {
                    return handled;
                }
                try {
                    const message = JSON.stringify(rawData);
                    return { message };
                } catch (error) {
                    console.warn('CommandBar: Unable to stringify command channel payload:', error);
                    return null;
                }
            }

            return { message: String(rawData) };
        }

        handleStructuredCommandPayload(payload) {
            if (!payload || typeof payload !== 'object') {
                return null;
            }

            const type = typeof payload.type === 'string' ? payload.type.toLowerCase() : '';
            if (!type) {
                return null;
            }

            if (type === 'ping') {
                if (this.commandChannelSocket && this.commandChannelSocket.readyState === WebSocket.OPEN) {
                    try {
                        this.commandChannelSocket.send(JSON.stringify({ type: 'pong' }));
                    } catch (error) {
                        console.warn('CommandBar: Unable to send pong response:', error);
                    }
                }
                return { message: '' };
            }

            if (type === 'status') {
                const data = this.stringifyCommandData(payload.data);
                return { message: data };
            }

            // Treat non-status types as handled with no visual output for now.
            return { message: '' };
        }

        stripCommandBarMarker(message) {
            if (!message) {
                return '';
            }
            const marker = 'COMMAND_BAR_RESULT';
            const markerIndex = message.indexOf(marker);
            if (markerIndex !== -1) {
                return message.substring(markerIndex + marker.length).trim();
            }
            return message;
        }

        stringifyCommandData(data) {
            if (data === undefined || data === null) {
                return '';
            }
            if (typeof data === 'string') {
                return data.trim();
            }
            try {
                return JSON.stringify(data);
            } catch (error) {
                console.warn('CommandBar: Unable to stringify command data payload:', error);
                return String(data);
            }
        }

        tryParseJson(raw) {
            try {
                return JSON.parse(raw);
            } catch (error) {
                return null;
            }
        }

        navigateToProjectPage(subpath) {
            if (this.projectBaseUrl) {
                window.location.href = this.projectBaseUrl + subpath;
            } else {
                this.showResult('Error: This command is only available on a project page.');
            }
        }

        navigateToProjectBrowse(args = []) {
            if (!this.projectBaseUrl) {
                this.showResult('Error: The browse command is only available on a project page.');
                return;
            }
            
            let url = window.location.href;
            let baseUrl = this.projectBaseUrl;
            if (typeof pup_relpath === 'string' && pup_relpath && url.indexOf('pup=') !== -1) {
                const normalizedRelPath = pup_relpath.endsWith('/') ? pup_relpath : `${pup_relpath}/`;
                baseUrl += `browse/_pups/${normalizedRelPath}`;
            } else {
                baseUrl += 'browse/';
            }

            const resource = Array.isArray(args) ? args.join(' ').trim() : '';

            if (!resource) {
                window.location.href = baseUrl;
                this.hideResult();
                return;
            }

            const cleanedResource = resource.replace(/^\/+/, '');
            const targetUrl = baseUrl + cleanedResource;

            const newWindow = window.open(targetUrl, '_blank', 'noopener');
            if (!newWindow) {
                window.location.href = targetUrl;
            }
            this.hideResult();
        }


        handleClearCommand(args = []) {
            const normalizedArgs = Array.isArray(args)
                ? args.map((value) => String(value || '').trim()).filter((value) => value.length > 0)
                : [];
            if (normalizedArgs.length > 1) {
                this.showResult([
                    'Error: Too many arguments for clear command.',
                    'Expected one of:',
                    ...CLEAR_HELP_LINES.map((line) => `  ${line}`)
                ].join('\n'));
                return;
            }
            const target = (normalizedArgs[0] || 'locks').toLowerCase();

            if (!this.projectBaseUrl) {
                this.showResult('Error: The clear command is only available on a project page.');
                return;
            }

            switch (target) {
            case '':
            case 'lock':
            case 'locks':
                return this.clearLocks();
            case 'cache':
            case 'nodb_cache':
            case 'nodb-cache':
                return this.clearNodbCache();
            default:
                this.showResult([
                    'Available clear commands:',
                    ...CLEAR_HELP_LINES.map((line) => `  ${line}`)
                ].join('\n'));
            }
        }


        clearLocks() {
            if (!this.projectBaseUrl) {
                this.showResult('Error: The clear command is only available on a project page.');
                return;
            }
            const targetUrl = this.projectBaseUrl + 'tasks/clear_locks';

            return fetch(targetUrl, { method: 'GET', cache: 'no-store', headers: { 'Accept': 'application/json' } })
                .then((response) => response.json().catch(() => ({})).then((data) => ({ response, data })))
                .then(({ response, data }) => {
                    if (!response.ok) {
                        const message = (data && (data.Error || data.error)) || `Could not clear locks. HTTP ${response.status}`;
                        throw new Error(message);
                    }

                    if (data && data.Success === false) {
                        const message = (data && (data.Error || data.error)) || 'Unable to clear locks.';
                        throw new Error(message);
                    }

                    this.showResult('Success: Cleared NoDb locks.');
                })
                .catch((error) => {
                    console.error('Error clearing locks:', error);
                    this.showResult(`Error: ${error.message || error}`);
                });
        }


        clearNodbCache() {
            if (!this.projectBaseUrl) {
                this.showResult('Error: The clear command is only available on a project page.');
                return;
            }
            const targetUrl = this.projectBaseUrl + 'tasks/clear_nodb_cache';

            return fetch(targetUrl, { method: 'GET', cache: 'no-store', headers: { 'Accept': 'application/json' } })
                .then((response) => response.json().catch(() => ({})).then((data) => ({ response, data })))
                .then(({ response, data }) => {
                    if (!response.ok) {
                        const message = (data && (data.Error || data.error)) || `Could not clear NoDb cache. HTTP ${response.status}`;
                        throw new Error(message);
                    }

                    if (data && data.Success === false) {
                        const message = (data && (data.Error || data.error)) || 'Unable to clear NoDb cache.';
                        throw new Error(message);
                    }

                    const clearedEntries = (data && data.Content && Array.isArray(data.Content.cleared_entries))
                        ? data.Content.cleared_entries
                        : [];

                    if (clearedEntries.length === 0) {
                        this.showResult('Success: No cached NoDb entries were present.');
                    } else {
                        const details = clearedEntries.map((entry) => `  ${entry}`).join('\n');
                        this.showResult(`Success: Cleared NoDb cache entries:\n${details}`);
                    }
                })
                .catch((error) => {
                    console.error('Error clearing NoDb cache:', error);
                    this.showResult(`Error: ${error.message || error}`);
                });
        }

        navigateToSelector(selector) {
            if (!selector) {
                return;
            }
            const anchorLink = document.querySelector(selector);
            if (anchorLink) {
                anchorLink.click();
                this.hideResult();
                return;
            }
            this.showResult('Error: Could not find the specified section on this page.');
        }

        handleRunCommand(args = []) {
            if (!Array.isArray(args) || args.length === 0) {
                const helpLines = this.buildRunCommandHelpLines();
                if (helpLines.length === 0) {
                    this.showResult('No run commands are available yet.');
                    return;
                }

                const messageParts = [
                    'Usage:',
                    '  run <command>',
                    '',
                    'Available run commands:',
                    ...helpLines
                ];
                this.showResult(messageParts.join('\n'));
                return;
            }

            const [subcommandRaw, ...rest] = args;
            const subcommand = (subcommandRaw || '').toLowerCase();
            const handlerEntry = this.runCommandHandlers[subcommand];

            if (!handlerEntry) {
                const helpLines = this.buildRunCommandHelpLines();
                const details = helpLines.length ? `\nAvailable run commands:\n${helpLines.join('\n')}` : '';
                this.showResult(`Error: Unknown run command "${subcommand}".${details}`);
                return;
            }

            return handlerEntry.handler(rest);
        }

        handleGetCommand(args = []) {
            if (!Array.isArray(args) || args.length === 0) {
                const helpLines = this.buildGetCommandHelpLines();
                if (helpLines.length === 0) {
                    this.showResult('No get commands are available yet.');
                    return;
                }

                const messageParts = [
                    'Usage:',
                    '  get <command>',
                    '',
                    'Available get commands:',
                    ...helpLines
                ];
                this.showResult(messageParts.join('\n'));
                return;
            }

            const [subcommandRaw, ...rest] = args;
            const subcommand = (subcommandRaw || '').toLowerCase();
            const handlerEntry = this.getCommandHandlers[subcommand];

            if (!handlerEntry) {
                const helpLines = this.buildGetCommandHelpLines();
                const details = helpLines.length ? `\nAvailable get commands:\n${helpLines.join('\n')}` : '';
                this.showResult(`Error: Unknown get command "${subcommand}".${details}`);
                return;
            }

            return handlerEntry.handler(rest);
        }

        buildGetCommandHelpLines() {
            return Object.entries(this.getCommandHandlers).map(([name, meta]) => {
                const description = (meta && meta.description) || '';
                const label = `get ${name}`;
                if (!description) {
                    return `  ${label}`;
                }
                const padded = label.padEnd(18);
                return `  ${padded}- ${description}`;
            });
        }

        buildRunCommandHelpLines() {
            return Object.entries(this.runCommandHandlers).map(([name, meta]) => {
                const description = (meta && meta.description) || '';
                const label = `run ${name}`;
                if (!description) {
                    return `  ${label}`;
                }
                const padded = label.padEnd(25);
                return `  ${padded}- ${description}`;
            });
        }

        handleSetCommand(args = []) {
            if (!Array.isArray(args) || args.length === 0) {
                this.showResult('Usage:\n' + SET_HELP_LINES.join('\n'));
                return;
            }

            const [subcommandRaw, ...rest] = args;
            const subcommand = (subcommandRaw || '').toLowerCase();

            switch (subcommand) {
                case 'units':
                    this.routeSetUnits(rest);
                    break;
                case 'name':
                    this.routeSetName(rest);
                    break;
                case 'scenario':
                    this.routeSetScenario(rest);
                    break;
                case 'outlet':
                    this.routeSetOutlet(rest);
                    break;
                case 'loglevel':
                    return this.routeSetLogLevel(rest);
                case 'readonly':
                    this.routeSetReadonly(rest);
                    break;
                case 'public':
                    this.routeSetPublic(rest);
                    break;
                case 'channel_critical_shear':
                    this.handleSetChannelCriticalShear(rest);
                    break;
                default:
                    this.showResult(`Error: Unknown set option "${subcommandRaw}"`);
            }
        }

        handleSetChannelCriticalShear(args = []) {
            if (!Array.isArray(args) || args.length === 0) {
                this.showResult('Usage: set channel_critical_shear <value>');
                return;
            }

            const rawValue = args.join(' ').trim();
            if (!rawValue) {
                this.showResult('Usage: set channel_critical_shear <value>');
                return;
            }

            const numericValue = Number(rawValue);
            if (!Number.isFinite(numericValue)) {
                this.showResult(`Error: channel_critical_shear requires a numeric value, received "${rawValue}".`);
                return;
            }

            const globalWepp = (typeof window !== 'undefined' && window.Wepp)
                ? window.Wepp
                : (typeof Wepp !== 'undefined' ? Wepp : undefined);

            if (!globalWepp || typeof globalWepp.getInstance !== 'function') {
                this.showResult('Error: WEPP module is not available on this page.');
                return;
            }

            const weppInstance = globalWepp.getInstance();
            if (!weppInstance || typeof weppInstance.addChannelCriticalShear !== 'function') {
                this.showResult('Error: Unable to update channel critical shear at this time.');
                return;
            }

            weppInstance.addChannelCriticalShear(rawValue);
            this.showResult(`Channel critical shear set to ${rawValue}.`);
        }

        routeGetLoadAvg(args = []) {
            if (Array.isArray(args) && args.length > 0) {
                this.showResult('Usage: get loadavg');
                return;
            }

            const jsonUrl = '/getloadavg';

            return fetch(jsonUrl, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json'
                }
            }).then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status} fetching ${jsonUrl}`);
                }
                return response.json();
            }).then((jsonData) => {
                const values = Array.isArray(jsonData) ? jsonData : [];
                const joined = values.map((value) => String(value)).join(' ');
                const messageLines = [
                    'Load average (1m, 5m, 15m):',
                    `  ${joined || '(no data)'}`
                ];
                this.showResult(messageLines.join('\n'));
            }).catch((error) => {
                console.error('Error fetching load average:', error);
                this.showResult(`Error: Unable to fetch load average. ${error.message || error}`);
            });
        }

        routeGetLocks(args = []) {
            if (Array.isArray(args) && args.length > 0) {
                this.showResult('Usage: get locks');
                return;
            }

            if (!this.projectBaseUrl) {
                this.showResult('Error: This command is only available on a project page.');
                return;
            }

            const targetUrl = `${this.projectBaseUrl}command_bar/locks`;

            return fetch(targetUrl, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json'
                }
            }).then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status} fetching ${targetUrl}`);
                }
                return response.json();
            }).then((data) => {
                if (!data || data.Success !== true) {
                    const message = (data && (data.Error || data.error)) || 'Unexpected response while fetching lock statuses.';
                    throw new Error(message);
                }

                const lockedFiles = Array.isArray(data.Content && data.Content.locked_files)
                    ? data.Content.locked_files
                    : [];

                if (lockedFiles.length === 0) {
                    this.showResult('No locked files.');
                    return;
                }

                const messageLines = [
                    'Locked files:',
                    ...lockedFiles.map((filename) => `  ${filename}`)
                ];
                this.showResult(messageLines.join('\n'));
            }).catch((error) => {
                console.error('Error fetching lock statuses:', error);
                this.showResult(`Error: Unable to fetch lock statuses. ${error.message || error}`);
            });
        }

        buildQueryEngineTokenCard(content) {
            const token = content && typeof content.token === 'string' ? content.token : '';
            const expiresAt = typeof content.expires_at === 'number' ? content.expires_at : null;
            const scopes = Array.isArray(content.scopes) ? content.scopes : [];
            const instructions = Array.isArray(content.instructions) ? content.instructions : [];
            const specUrl = content && typeof content.spec_url === 'string' ? content.spec_url : '';
            const instructionsPath = content && typeof content.instructions_path === 'string' ? content.instructions_path : '';

            const card = document.createElement('div');
            card.className = 'command-bar-token-card';

            const title = document.createElement('div');
            title.className = 'command-bar-token-card__title';
            title.textContent = 'Query Engine API token';
            card.appendChild(title);

            if (!token) {
                const failure = document.createElement('p');
                failure.className = 'command-bar-token-card__note';
                failure.textContent = 'Token response did not include a token. Please try again.';
                card.appendChild(failure);
                return card;
            }

            const secretRow = document.createElement('div');
            secretRow.className = 'command-bar-token-card__secret-row';

            const tokenInput = document.createElement('input');
            tokenInput.type = 'password';
            tokenInput.readOnly = true;
            tokenInput.className = 'command-bar-token-card__secret-input';
            tokenInput.value = token;
            tokenInput.setAttribute('aria-label', 'Query Engine API token');

            const buttonsWrapper = document.createElement('div');
            buttonsWrapper.className = 'command-bar-token-card__actions';

            let revealed = false;
            const toggleButton = document.createElement('button');
            toggleButton.type = 'button';
            toggleButton.className = 'command-bar-token-card__button';

            const updateVisibility = () => {
                tokenInput.type = revealed ? 'text' : 'password';
                toggleButton.textContent = revealed ? 'Hide token' : 'Show token';
            };
            updateVisibility();

            toggleButton.addEventListener('click', () => {
                revealed = !revealed;
                updateVisibility();
            });

            const copyButton = document.createElement('button');
            copyButton.type = 'button';
            copyButton.className = 'command-bar-token-card__button';
            copyButton.textContent = 'Copy';

            const withFeedback = (button, label) => {
                const original = button.dataset.originalLabel || button.textContent;
                button.dataset.originalLabel = original;
                button.disabled = true;
                button.textContent = label;
                window.setTimeout(() => {
                    button.disabled = false;
                    button.textContent = button.dataset.originalLabel;
                }, 1600);
            };

            copyButton.addEventListener('click', async () => {
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(token);
                    } else {
                        const previousType = tokenInput.type;
                        tokenInput.type = 'text';
                        tokenInput.select();
                        document.execCommand('copy');
                        tokenInput.type = previousType;
                        tokenInput.blur();
                    }
                    withFeedback(copyButton, 'Copied');
                } catch (error) {
                    console.warn('CommandBar: copy failed', error);
                    withFeedback(copyButton, 'Copy failed');
                }
            });

            const downloadButton = document.createElement('button');
            downloadButton.type = 'button';
            downloadButton.className = 'command-bar-token-card__button';
            downloadButton.textContent = 'Download';
            downloadButton.addEventListener('click', () => {
                try {
                    const blob = new Blob([token], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const anchor = document.createElement('a');
                    anchor.href = url;
                    const suffix = new Date().toISOString().replace(/[:.]/g, '-');
                    anchor.download = `weppcloud-query-engine-token-${suffix}.txt`;
                    document.body.appendChild(anchor);
                    anchor.click();
                    document.body.removeChild(anchor);
                    URL.revokeObjectURL(url);
                    withFeedback(downloadButton, 'Saved');
                } catch (error) {
                    console.warn('CommandBar: download failed', error);
                    withFeedback(downloadButton, 'Failed');
                }
            });

            buttonsWrapper.appendChild(toggleButton);
            buttonsWrapper.appendChild(copyButton);
            buttonsWrapper.appendChild(downloadButton);

            secretRow.appendChild(tokenInput);
            secretRow.appendChild(buttonsWrapper);
            card.appendChild(secretRow);

            const headerExample = document.createElement('pre');
            headerExample.className = 'command-bar-token-card__header-example';
            headerExample.textContent = 'Authorization: Bearer <token>';
            card.appendChild(headerExample);

            const note = document.createElement('p');
            note.className = 'command-bar-token-card__note';
            note.textContent = 'Copy or download this token now. It will not be shown again once you close the command bar.';
            card.appendChild(note);

            if (instructionsPath) {
                const pathNote = document.createElement('p');
                pathNote.className = 'command-bar-token-card__note';
                pathNote.textContent = `Instructions stored in: ${instructionsPath}`;
                card.appendChild(pathNote);
            }

            if (specUrl) {
                const specNote = document.createElement('p');
                specNote.className = 'command-bar-token-card__note';
                const specLink = document.createElement('a');
                specLink.href = specUrl;
                specLink.target = '_blank';
                specLink.rel = 'noopener noreferrer';
                specLink.textContent = 'Download the MCP OpenAPI spec';
                specNote.appendChild(specLink);
                card.appendChild(specNote);
            }

            const metaList = document.createElement('ul');
            metaList.className = 'command-bar-token-card__meta';

            if (expiresAt) {
                const expiresItem = document.createElement('li');
                const expiryDate = new Date(expiresAt * 1000);
                expiresItem.textContent = `Expires: ${expiryDate.toISOString()}`;
                metaList.appendChild(expiresItem);
            }

            if (scopes.length > 0) {
                const scopesItem = document.createElement('li');
                scopesItem.textContent = `Scopes: ${scopes.join(', ')}`;
                metaList.appendChild(scopesItem);
            }

            if (metaList.childElementCount > 0) {
                card.appendChild(metaList);
            }

            if (instructions.length > 0) {
                const instructionsTitle = document.createElement('div');
                instructionsTitle.className = 'command-bar-token-card__subtitle';
                instructionsTitle.textContent = 'Suggested workflows';
                card.appendChild(instructionsTitle);

                const instructionsList = document.createElement('ol');
                instructionsList.className = 'command-bar-token-card__instructions';
                instructions.forEach((line) => {
                    const item = document.createElement('li');
                    item.textContent = line;
                    instructionsList.appendChild(item);
                });
                card.appendChild(instructionsList);
            }

            return card;
        }

        routeGetQueryEngineMcpToken(args = []) {
            if (!this.projectBaseUrl) {
                this.showResult('Error: This command is only available on a project page.');
                return;
            }

            if (Array.isArray(args) && args.length > 0) {
                this.showResult('Usage: get query_engine_mcp_token');
                return;
            }

            const targetUrl = `${this.projectBaseUrl}command_bar/query_engine_mcp_token`;

            return fetch(targetUrl, {
                method: 'POST',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })
                .then((response) => response.json().catch(() => ({})).then((data) => ({ response, data })))
                .then(({ response, data }) => {
                    if (!response.ok || !data || data.Success !== true) {
                        const message = (data && (data.Error || data.error || data.message)) || `HTTP ${response.status}`;
                        throw new Error(message);
                    }

                    const content = data.Content || {};
                    const card = this.buildQueryEngineTokenCard(content);
                    this.showResult(card);
                })
                .catch((error) => {
                    console.error('Error generating Query Engine token:', error);
                    this.showResult(`Error: Unable to generate Query Engine MCP token. ${error.message || error}`);
                });
        }

        routeRunInterchangeMigration(args = []) {
            if (!this.projectBaseUrl) {
                this.showResult('Error: The run command is only available on a project page.');
                return;
            }

            const normalizedArgs = Array.isArray(args)
                ? args.map((value) => String(value || '').trim()).filter((value) => value.length > 0)
                : [];

            const subpath = normalizedArgs.length > 0 ? normalizedArgs.join(' ').trim() : null;

            const targetUrl = `${this.projectBaseUrl}tasks/interchange/migrate`;
            const payload = subpath ? { wepp_output_subpath: subpath } : {};

            return fetch(targetUrl, {
                method: 'POST',
                cache: 'no-store',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload)
            }).then((response) => response.json().catch(() => ({})).then((data) => ({ response, data })))
                .then(({ response, data }) => {
                    if (!response.ok) {
                        const message = (data && (data.Error || data.error || data.message)) || `HTTP ${response.status}`;
                        throw new Error(message);
                    }

                    if (!data || data.Success !== true) {
                        const message = (data && (data.Error || data.error || data.message)) || 'Unknown error';
                        throw new Error(message);
                    }
                    const jobId = data.job_id || (data.Content && data.Content.job_id);
                    const suffix = jobId ? ` (job ${jobId})` : '';
                    const targetDetail = subpath ? ` for "${subpath}"` : '';
                    this.showResult(`Success: Interchange migration queued${targetDetail}${suffix}.`);
                })
                .catch((error) => {
                    console.error('Error starting interchange migration:', error);
                    this.showResult(`Error: Unable to queue interchange migration. ${error.message || error}`);
                });
        }

        routeUsersum(args = []) {
            if (!Array.isArray(args)) {
                this.showResult('Usage: usersum <parameter> [-e|--extended]\n       usersum -k <keyword>');
                return;
            }

            const normalizedArgs = args
                .map((value) => String(value || '').trim())
                .filter((value) => value.length > 0);

            if (normalizedArgs.length === 0) {
                this.showResult('Usage: usersum <parameter> [-e|--extended]\n       usersum -k <keyword>');
                return;
            }

            const firstArg = normalizedArgs[0].toLowerCase();

            if (firstArg === '-k' || firstArg === '--apropos') {
                const keyword = normalizedArgs.slice(1).join(' ').trim();
                if (!keyword) {
                    this.showResult('Usage: usersum -k <keyword>');
                    return;
                }

                const params = new URLSearchParams({ q: keyword });
                const targetUrl = `/usersum/api/keyword?${params.toString()}`;
                return this.fetchUsersumData(targetUrl);
            }

            const parameterName = normalizedArgs[0];
            let includeExtended = false;
            const unknownFlags = [];

            for (let i = 1; i < normalizedArgs.length; i += 1) {
                const flag = normalizedArgs[i].toLowerCase();
                if (flag === '-e' || flag === '--extended') {
                    includeExtended = true;
                } else {
                    unknownFlags.push(normalizedArgs[i]);
                }
            }

            if (unknownFlags.length > 0) {
                this.showResult(`Error: Unknown usersum option "${unknownFlags[0]}"`);
                return;
            }

            const params = new URLSearchParams({ name: parameterName });
            if (includeExtended) {
                params.set('extended', '1');
            }

            const targetUrl = `/usersum/api/parameter?${params.toString()}`;
            return this.fetchUsersumData(targetUrl);
        }

        fetchUsersumData(targetUrl) {
            return fetch(targetUrl, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json'
                }
            }).then((response) => {
                if (!response.ok) {
                    return response.json().catch(() => ({})).then((data) => {
                        const message = data.error || data.Error || `HTTP ${response.status}`;
                        throw new Error(message);
                    });
                }
                return response.json();
            }).then((data) => {
                if (!data || !data.success) {
                    throw new Error((data && (data.error || data.Error)) || 'Unknown error');
                }

                const lines = Array.isArray(data.lines) ? data.lines : [];
                const message = lines.join('\n').trim();
                this.showResult(message || 'No usersum data available.');
            }).catch((error) => {
                console.error('Usersum command failed:', error);
                this.showResult(`Error: ${error.message || error}`);
            });
        }

        routeSetUnits(args = []) {
            if (args.length === 0) {
                this.showResult('Usage: set units <si|english>');
                return;
            }

            const unitType = (args[0] || '').toLowerCase();
            if (unitType !== 'si' && unitType !== 'english') {
                this.showResult('Error: Unit type must be "si" or "english".');
                return;
            }

            if (typeof window.setGlobalUnitizerPreference !== 'function') {
                this.showResult('Error: setGlobalUnitizerPreference is not available.');
                return;
            }

            try {
                if (unitType === 'si') {
                    window.setGlobalUnitizerPreference(0);
                } else {
                    window.setGlobalUnitizerPreference(1);
                }
                Project.getInstance().unitChangeEvent();
                this.hideResult();
            } catch (error) {
                console.error('Error setting unit preference:', error);
                this.showResult(`Error: Unable to set units. ${error.message || error}`);
            }
        }

        routeSetName(args = []) {
            const name = args.join(' ').trim();
            if (!name) {
                this.showResult('Usage: set name <project name>');
                return;
            }

            try {
                Project.getInstance().setName(name);
            } catch (error) {
                console.error('Error setting project name:', error);
                this.showResult(`Error: Unable to set project name. ${error.message || error}`);
            }
        }

        routeSetScenario(args = []) {
            const scenario = args.join(' ').trim();
            if (!scenario) {
                this.showResult('Usage: set scenario <name>');
                return;
            }

            try {
                Project.getInstance().setScenario(scenario);
            } catch (error) {
                console.error('Error setting project scenario:', error);
                this.showResult(`Error: Unable to set project scenario. ${error.message || error}`);
            }
        }

        routeSetReadonly(args = []) {
            if (args.length === 0) {
                this.showResult('Usage: set readonly <true|false>');
                return;
            }

            const desiredState = this.parseBooleanFlag(args[0]);
            if (desiredState === null) {
                this.showResult('Error: readonly state must be true or false.');
                return;
            }

            try {
                Project.getInstance().set_readonly(desiredState);
            } catch (error) {
                console.error('Error setting readonly state:', error);
                this.showResult(`Error: Unable to set readonly state. ${error.message || error}`);
            }
        }

        routeSetPublic(args = []) {
            if (args.length === 0) {
                this.showResult('Usage: set public <true|false>');
                return;
            }

            const desiredState = this.parseBooleanFlag(args[0]);
            if (desiredState === null) {
                this.showResult('Error: public state must be true or false.');
                return;
            }

            try {
                Project.getInstance().set_public(desiredState);
            } catch (error) {
                console.error('Error setting public state:', error);
                this.showResult(`Error: Unable to set public state. ${error.message || error}`);
            }
        }

        routeSetOutlet(args = []) {
            if (Array.isArray(args) && args.length > 0) {
                this.showResult('Usage: set outlet');
                return;
            }

            const outlet = Outlet.getInstance()
            outlet.setCursorSelection(!outlet.cursorSelectionOn);
            if (outlet.cursorSelectionOn === true){
                this.showResult('Cursor selection for outlet is now active. Click on the map to set the outlet location.');
            } else {
                this.showResult('Cursor selection for outlet is now deactivated.');
            }
        }

        routeSetLogLevel(args = []) {
            if (args.length === 0) {
                this.showResult('Usage: set loglevel <debug|info|warning|error|critical>');
                return;
            }

            const level = (args[0] || '').toLowerCase();
            const allowedLevels = new Set(['debug', 'info', 'warning', 'error', 'critical']);
            if (!allowedLevels.has(level)) {
                this.showResult('Error: Log level must be one of debug, info, warning, error, critical.');
                return;
            }

            if (!this.projectBaseUrl) {
                this.showResult('Error: The loglevel command is only available on a project page.');
                return;
            }

            const targetUrl = `${this.projectBaseUrl}command_bar/loglevel`;
            return fetch(targetUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ level })
            }).then((response) => {
                if (!response.ok) {
                    return response.json().catch(() => ({})).then((data) => {
                        const message = data.Error || `HTTP ${response.status}`;
                        throw new Error(message);
                    });
                }
                return response.json();
            }).then((data) => {
                if (!data || !data.Success) {
                    throw new Error((data && data.Error) || 'Unknown error');
                }

                const content = data.Content || {};
                const levelLabel = content.log_level || level;
                const levelValue = content.log_level_value;
                const formatted = levelValue !== undefined ? `${levelLabel} (${levelValue})` : levelLabel;
                this.showResult(`Log level set to ${formatted}.`);
            }).catch((error) => {
                console.error('Error setting log level:', error);
                this.showResult(`Error: Unable to set log level. ${error.message || error}`);
            });
        }

        parseBooleanFlag(value) {
            const normalized = String(value || '').trim().toLowerCase();
            if (['true', '1', 'yes', 'on', 'enable', 'enabled'].includes(normalized)) {
                return true;
            }
            if (['false', '0', 'no', 'off', 'disable', 'disabled'].includes(normalized)) {
                return false;
            }
            return null;
        }

        async fetchStatus() {
            if (!this.projectBaseUrl) {
                this.showResult('Error: Cannot check status outside of a project page.');
                return;
            }

            try {
                const response = await fetch(`${this.projectBaseUrl}status.json`, { cache: 'no-store' });
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                const data = await response.json();
                this.showResult(JSON.stringify(data, null, 2));
            } catch (error) {
                console.error('Error fetching status:', error);
                this.showResult(`Error: Could not fetch status. ${error.message || error}`);
            }
        }
    }

    // Attach a single hover listener that turns any element with `data-usersum="<param>"`
    // into a lightweight preview trigger. The span markup is added by the browse blueprint
    // (and can be reused elsewhere). We cache the preview text on the element so repeated
    // hovers do not spam `/usersum/api/parameter`.
    function attachUsersumHover(root, commandBar) {
        if (!root || !commandBar) {
            return;
        }
        if (root.__usersumHoverAttached) {
            return;
        }
        root.__usersumHoverAttached = true;

        root.addEventListener('mouseover', (event) => {
            const target = event.target.closest('[data-usersum]');
            if (!target) {
                return;
            }

            const parameterName = target.dataset.usersum;
            if (!parameterName) {
                return;
            }

            const cachedPreview = target.dataset.usersumPreview;
            if (cachedPreview) {
                commandBar.showResult(cachedPreview);
                return;
            }

            if (target.dataset.usersumPending === '1') {
                return;
            }

            target.dataset.usersumPending = '1';

            const params = new URLSearchParams({ name: parameterName });
            const targetUrl = `/usersum/api/parameter?${params.toString()}`;

            fetch(targetUrl, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json'
                }
            }).then((response) => {
                if (!response.ok) {
                    return response.json().catch(() => ({})).then((data) => {
                        const message = data.error || data.Error || `HTTP ${response.status}`;
                        throw new Error(message);
                    });
                }
                return response.json();
            }).then((data) => {
                if (!data || !data.success) {
                    throw new Error((data && (data.error || data.Error)) || 'Unknown error');
                }

                const lines = Array.isArray(data.lines) ? data.lines : [];
                const preview = lines.length > 0 ? lines[0] : `No description available for ${parameterName}`;
                target.dataset.usersumPreview = preview;
                commandBar.showResult(preview);
            }).catch((error) => {
                console.error('Usersum hover lookup failed:', error);
                const message = `Error: ${error.message || error}`;
                target.dataset.usersumPreview = message;
                commandBar.showResult(message);
            }).finally(() => {
                delete target.dataset.usersumPending;
            });
        }, { passive: true });
    }


    function initializeCommandBar(root = document) {
        const container = root.querySelector('[data-command-bar]');
        const existing = window[GLOBAL_INSTANCE_KEY];

        if (!container) {
            if (existing && typeof existing.destroy === 'function') {
                existing.destroy();
            }
            delete window[GLOBAL_INSTANCE_KEY];
            return null;
        }

        if (existing) {
            if (existing.container === container) {
                if (!container[INSTANCE_DATA_KEY]) {
                    container[INSTANCE_DATA_KEY] = existing;
                }
                return existing;
            }
            if (typeof existing.destroy === 'function') {
                existing.destroy();
            }
            delete window[GLOBAL_INSTANCE_KEY];
        }

        if (container[INSTANCE_DATA_KEY]) {
            window[GLOBAL_INSTANCE_KEY] = container[INSTANCE_DATA_KEY];
            return container[INSTANCE_DATA_KEY];
        }

        const commandBar = new CommandBar(container);
        commandBar.init();
        container[INSTANCE_DATA_KEY] = commandBar;
        window[GLOBAL_INSTANCE_KEY] = commandBar;
        attachUsersumHover(root, commandBar);
        return commandBar;
    }


    window.initializeCommandBar = initializeCommandBar;

    document.addEventListener('DOMContentLoaded', () => {
        initializeCommandBar();
    });
})();

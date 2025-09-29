// wepppy/weppcloud/routes/command_bar/static/js/command-bar.js
//
// Developer notes live in `dev-notes/command-bar.md`. See that document for quick-start
// guidance on registering commands, server routes, and hover previews.
(() => {
    'use strict';

    const KEY_TRIGGER = ':';
    const TIP_DEFAULT = "Tip: Press ':' to activate the command bar. :help for commands.";
    const TIP_ACTIVE = 'Command mode - press Enter to run, Esc to cancel';
    const INSTANCE_DATA_KEY = '__commandBarInstance';
    const STAY_ACTIVE_COMMANDS = new Set(['help', 'status']);
    const SET_HELP_LINES = [
        "set units <si|english>    - Switch global unit preferences",
        "set name <project name>   - Update the project name",
        "set scenario <name>       - Update the project scenario",
        "set outlet                - Use cursor location for outlet delineation",
        "set readonly <true|false> - Toggle project readonly mode",
        "set public <true|false>   - Toggle project public visibility",
        "set loglevel <debug|info|warning|error|critical> - Update project log verbosity"
    ];

    class CommandBar {
        constructor(container) {
            this.container = container;
            this.tipEl = container.querySelector('[data-command-tip]');
            this.resultEl = container.querySelector('[data-command-result]');
            this.inputWrapperEl = container.querySelector('[data-command-input-wrapper]');
            this.inputEl = container.querySelector('[data-command-input]');

            this.active = false;
            this.projectBaseUrl = this.getProjectBaseUrl();
            this.getCommandHandlers = this.createGetCommandHandlers();
            this.commands = this.createCommands();

            this.handleDocumentKeyDown = this.handleDocumentKeyDown.bind(this);
            this.handleInputKeyDown = this.handleInputKeyDown.bind(this);
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
                    description: 'Clear the NoDb locks',
                    action: () => this.clearLocks()
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

        handleDocumentKeyDown(event) {
            if (this.active) {
                if (event.key === 'Escape') {
                    event.preventDefault();
                    this.deactivate();
                    return;
                }

                if (event.target !== this.inputEl && !this.shouldIgnoreTriggerTarget(event.target)) {
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
                this.executeCommand(this.inputEl.value.trim());
            } else if (event.key === 'Escape') {
                event.preventDefault();
                this.deactivate();
                this.hideResult();
            }
        }

        activate() {
            this.active = true;
            this.inputWrapperEl.hidden = false;
            this.tipEl.textContent = TIP_ACTIVE;
            this.inputEl.value = '';
            this.focusInput();
        }

        deactivate() {
            this.active = false;
            this.inputWrapperEl.hidden = true;
            this.tipEl.textContent = TIP_DEFAULT;
            this.inputEl.value = '';
            if (document.activeElement === this.inputEl) {
                this.inputEl.blur();
            }
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
            const pre = document.createElement('pre');
            pre.textContent = message;
            this.resultEl.appendChild(pre);
        }

        hideResult() {
            this.resultEl.hidden = true;
            this.resultEl.textContent = '';
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
            const keyboardShortcuts = 'Navigation shortcuts:\n   Shift+G go to bottom  |  Shift+T go to top  |  Shift+U page up  |  Shift+H page down';
            const getHelpLines = this.buildGetCommandHelpLines();
            const usersumUsage = [
                'usersum command usage:',
                '  usersum <parameter> - concise description',
                '  usersum <parameter> -e or --extended - include extended details',
                '  usersum -k <keyword> - keyword search across parameters'
            ].join('\n');

            const sections = [
                `Available Commands:\n${lines}`,
                `Set command usage:\n${setHelp}`,
                usersumUsage
            ];

            if (getHelpLines.length) {
                sections.push(`Get command usage:\n${getHelpLines.join('\n')}`);
            }

            sections.push(keyboardShortcuts);

            this.showResult(sections.join('\n\n'));
        }

        getProjectBaseUrl() {
            const match = window.location.pathname.match(/^(?:\/weppcloud)?\/runs\/[^\/]+\/[^\/]+\//);
            return match ? match[0] : null;
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


        clearLocks() {
            if (!this.projectBaseUrl) {
                this.showResult('Error: The browse command is only available on a project page.');
                return;
            }
            const targetUrl = this.projectBaseUrl + 'tasks/clear_locks';

            fetch(targetUrl, { method: 'GET', cache: 'no-store' })
                .then((response) => {
                    if (response.ok) {
                        this.showResult('Success: Cleared NoDb locks.');
                    } else {
                        this.showResult(`Error: Could not clear locks. HTTP ${response.status}`);
                    }
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
                default:
                    this.showResult(`Error: Unknown set option "${subcommandRaw}"`);
            }
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
        if (!container) {
            return null;
        }

        if (container[INSTANCE_DATA_KEY]) {
            return container[INSTANCE_DATA_KEY];
        }

        const commandBar = new CommandBar(container);
        commandBar.init();
        container[INSTANCE_DATA_KEY] = commandBar;
        attachUsersumHover(root, commandBar);
        return commandBar;
    }


    window.initializeCommandBar = initializeCommandBar;

    document.addEventListener('DOMContentLoaded', () => {
        initializeCommandBar();
    });
})();

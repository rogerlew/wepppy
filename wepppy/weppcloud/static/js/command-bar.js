// static/js/command-bar.js
(() => {
    'use strict';

    const KEY_TRIGGER = ':';
    const TIP_DEFAULT = "Tip: Press ':' to activate the command bar";
    const TIP_ACTIVE = 'Command mode - press Enter to run, Esc to cancel';
    const INSTANCE_DATA_KEY = '__commandBarInstance';
    const STAY_ACTIVE_COMMANDS = new Set(['help', 'status', 'clear']);

    class CommandBar {
        constructor(container) {
            this.container = container;
            this.tipEl = container.querySelector('[data-command-tip]');
            this.resultEl = container.querySelector('[data-command-result]');
            this.inputWrapperEl = container.querySelector('[data-command-input-wrapper]');
            this.inputEl = container.querySelector('[data-command-input]');

            this.active = false;
            this.projectBaseUrl = this.getProjectBaseUrl();
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
        createCommands() {
            return {
                help: {
                    description: 'Show available commands',
                    action: () => this.showHelp()
                },
                map: {
                    description: 'Navigate to Map',
                    action: () => this.navigateToSelector('a[href^="#map"]')
                },
                sbs: {
                    description: 'Navigate to Soil Burn Severity',
                    action: () => this.navigateToSelector('a[href^="#soil-burn-severity-optional"]')
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
                    description: 'Go to the project file browser',
                    action: () => this.navigateToProjectPage('browse/')
                },
                clear: {
                    description: 'Clear the command bar result',
                    action: () => this.hideResult()
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
                }
                return;
            }

            if (event.key === KEY_TRIGGER && !this.shouldIgnoreTriggerTarget(event.target)) {
                event.preventDefault();
                this.activate();
            }
        }

        handleInputKeyDown(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                this.executeCommand(this.inputEl.value.trim());
            } else if (event.key === 'Escape') {
                event.preventDefault();
                this.deactivate();
            }
        }

        activate() {
            this.active = true;
            this.inputWrapperEl.hidden = false;
            this.tipEl.textContent = TIP_ACTIVE;
            this.inputEl.value = '';
            this.inputEl.focus();
        }

        deactivate() {
            this.active = false;
            this.inputWrapperEl.hidden = true;
            this.tipEl.textContent = TIP_DEFAULT;
            this.inputEl.value = '';
        }

        executeCommand(fullCommand) {
            if (!fullCommand) {
                this.deactivate();
                return;
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
                .map(([name, meta]) => `${name.padEnd(10)} - ${meta.description}`)
                .join('\n');
            this.showResult(`Available Commands:\n${lines}`);
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
        return commandBar;
    }

    window.initializeCommandBar = initializeCommandBar;

    document.addEventListener('DOMContentLoaded', () => {
        initializeCommandBar();
    });
})();

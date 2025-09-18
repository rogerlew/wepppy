// static/js/command-bar.js

class CommandBar {
    static instance;

    constructor() {
        // DOM elements
        this.container = document.querySelector('.command-bar-container');
        this.span = document.getElementById('command-bar');
        this.result_span = document.getElementById('command-bar-result');

        // State
        this.is_active = false;
        this.input_field = null;
        this.project_base_url = null;
        
        // Command definitions
        this._commands = {
            'help': {
                description: 'Show available commands',
                action: (args) => {
                    const command_list = Object.keys(this._commands)
                        .map(cmd => `  ${cmd.padEnd(10)} - ${this._commands[cmd].description}`)
                        .join('\n');
                    this._show_result(`Available Commands:\n${command_list}`);
                }
            },
            'home': {
                description: 'Go to the wepp.cloud homepage',
                action: () => window.location.href = '/weppcloud'
            },
            'report': {
                description: 'Go to the project report page',
                action: () => this._navigate_to_project_page('report/')
            },
            'browse': {
                description: 'Go to the project file browser',
                action: () => this._navigate_to_project_page('browse/')
            },
            'view': {
                description: 'Go to the project map view',
                action: () => this._navigate_to_project_page('view/')
            },
            'status': {
                description: 'Check the project run status',
                action: async () => {
                    if (!this.project_base_url) {
                        this._show_result('Error: Cannot check status, not on a project page.');
                        return;
                    }
                    try {
                        const response = await fetch(`${this.project_base_url}status.json`);
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        const data = await response.json();
                        const formatted_json = JSON.stringify(data, null, 2);
                        this._show_result(formatted_json);

                    } catch (error) {
                        console.error('Error fetching status:', error);
                        this._show_result(`Error: Could not fetch status. ${error.message}`);
                    }
                }
            },
            'clear': {
                description: 'Clear the command bar result',
                action: () => this._hide_result()
            }
        };
    }

    /**
     * Singleton pattern to ensure only one instance of CommandBar exists.
     */
    static getInstance() {
        if (!CommandBar.instance) {
            CommandBar.instance = new CommandBar();
        }
        return CommandBar.instance;
    }
    
    /**
     * Extracts the project base URL from the window's current path.
     * The pattern matches /weppcloud/runs/<run_id>/<cfg>/.
     * @returns {string|null} The base URL if found, otherwise null.
     */
    _get_project_base_url() {
        const regex = /^(?:\/weppcloud)?\/runs\/[^\/]+\/[^\/]+\//;
        const match = window.location.pathname.match(regex);
        return match ? match[1] : null;
    }
    
    /**
     * Helper function to navigate to a sub-page of the current project.
     * @param {string} subpath - The path to append to the project base URL.
     */
    _navigate_to_project_page(subpath) {
        if (this.project_base_url) {
            window.location.href = this.project_base_url + subpath;
        } else {
            this._show_result('Error: This command is only available on a project page.');
        }
    }

    /**
     * Initializes the command bar, sets up listeners, and finds the base URL.
     */
    init() {
        // Determine the project context on initialization
        this.project_base_url = this._get_project_base_url();
        
        document.addEventListener('keydown', (e) => this._handle_key_down(e));
        console.log("CommandBar initialized.");
        if (this.project_base_url) {
            console.log(`Project context set to: ${this.project_base_url}`);
        }
    }

    _handle_key_down(e) {
        if (e.key === ':' && !this.is_active && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            this._activate();
        } else if (e.key === 'Escape' && this.is_active) {
            e.preventDefault();
            this._deactivate();
        } else if (e.key === 'Enter' && this.is_active) {
            e.preventDefault();
            this._execute_command();
        }
    }

    _activate() {
        this.is_active = true;
        this.span.innerHTML = '<input type="text" id="command-bar-input" class="form-control form-control-sm" placeholder="Enter command...">';
        this.input_field = document.getElementById('command-bar-input');
        this.input_field.focus();
    }

    _deactivate() {
        this.is_active = false;
        this.span.textContent = 'Tip: Press \':\' to activate the command bar';
        this._hide_result();
    }

    _execute_command() {
        const full_command = this.input_field.value.trim();
        if (!full_command) {
            this._deactivate();
            return;
        }

        const [command, ...args] = full_command.split(/\s+/);
        const command_obj = this._commands[command.toLowerCase()];

        if (command_obj) {
            command_obj.action(args);
        } else {
            this._show_result(`Error: Command not found "${command}"`);
        }

        if (command.toLowerCase() !== 'help' && command.toLowerCase() !== 'status' && command.toLowerCase() !== 'clear') {
            this._deactivate();
        }
    }

    _show_result(message) {
        // To display JSON nicely, we wrap it in <pre> tags
        if (message.trim().startsWith('{') || message.trim().startsWith('[')) {
            this.result_span.innerHTML = `<pre>${message}</pre>`;
        } else {
            this.result_span.innerHTML = `<pre>${message}</pre>`;
        }
        this.result_span.style.display = 'block';
    }

    _hide_result() {
        this.result_span.style.display = 'none';
        this.result_span.innerHTML = '';
    }
}
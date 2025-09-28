/* ----------------------------------------------------------------------------
 * WebSocketManager
 * ----------------------------------------------------------------------------
 */

function WSClient(formId, channel) {
    // global runid
    this.formId = formId;
    this.channel = channel;
    this.wsUrl = "wss://" + window.location.host + "/weppcloud-microservices/status/" + runid + ":" + channel;
    this.ws = null;
    this.shouldReconnect = true;
    this.spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
    this.spinnerIndex = 0;
    //    this.connect();
}

WSClient.prototype.connect = function () {
    if (this.ws) {
        return; // If already connected, do nothing
    }

    this.shouldReconnect = true;
    this.ws = new WebSocket(this.wsUrl);
    this.ws.onopen = () => {
        this.pushCommandBarResult(`Connecting to ${this.channel}...`);
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ "type": "init" }));
            this.pushCommandBarResult(`Connected to ${this.channel}`);
        } else {
            this.pushCommandBarResult(`WebSocket is not in OPEN state: ${this.ws.readyState}`);
        }
    };

    this.ws.onmessage = (event) => {
        var payload = JSON.parse(event.data);
        if (payload.type === "ping") {
            this.ws.send(JSON.stringify({ "type": "pong" }));
        } else if (payload.type === "hangup") {
            this.disconnect();
        } else if (payload.type === "status") {
            var data = payload.data;
            this.advanceSpinner();
            var lines = data.split('\n');
            if (lines.length > 1) {
                data = lines[0] + '...';
            }

            if (data.includes("EXCEPTION")) {
                var stacktrace = $("#" + this.formId + " #stacktrace");

                stacktrace.show();
                stacktrace.text("");
                stacktrace.append("<h6>Error</h6>");
                stacktrace.append(`<p>${data}</p>`);

                var job_id = data.split(' ')[0].slice(3);
                var job_url = `https://${window.location.host}/weppcloud/rq/api/jobinfo/${job_id}`;

                // need a short delay here to avoid race condition
                setTimeout(function () {
                    $.get(job_url, function (job_info, status) {
                        if (status === 'success') {
                            stacktrace.append(`<pre><small class="text-muted">${job_info.exc_info}</small></pre>`);
                        }
                    });
                }, 500);
            }

            if (data.includes("COMMAND_BAR_RESULT")) {
                const marker = 'COMMAND_BAR_RESULT';
                const markerIndex = data.indexOf(marker);
                let commandMessage = data;
                if (markerIndex !== -1) {
                    commandMessage = data.substring(markerIndex + marker.length).trim();
                }
                $("#" + this.formId + " #status").html(commandMessage);
                this.pushCommandBarResult(commandMessage);
            }

            if (data.includes("TRIGGER")) {
                const tokens = data.trim().split(/\s+/);
                const event = tokens.length > 0 ? tokens[tokens.length - 1] : null;
                const controller = tokens.length > 1 ? tokens[tokens.length - 2] : null;

                if (controller && controller === this.channel) {
                    if (this._parentControl && typeof this._parentControl.triggerEvent === 'function') {
                        try {
                            this._parentControl.triggerEvent(event, { tokens: tokens, raw: data });
                        } catch (err) {
                            console.warn('WSClient triggerEvent error:', err);
                        }
                    } else if (this._parentControl && this._parentControl.form && typeof this._parentControl.form.trigger === 'function') {
                        this._parentControl.form.trigger(event);
                    }

                    if (typeof event === 'string' && event.toUpperCase().includes('COMPLETE')) {
                        this.resetSpinner();
                    }
                }
            } else {
                if (data.length > 120) {
                    data = data.substring(0, 120) + '...';
                }
                $("#" + this.formId + " #status").html(data);
            }
        }
    };

    this.ws.onerror = (error) => {
        console.log("WebSocket Error: ", error);
        this.ws = null;
    };

    this.ws.onclose = () => {
        //        $("#" + this.formId + " #status").html("Connection Closed");
        this.ws = null;
        if (this.shouldReconnect) {
            setTimeout(() => { this.connect(); }, 5000);
        }
    };
};

WSClient.prototype.disconnect = function () {
    if (this.ws) {
        this.shouldReconnect = false;
        this.ws.close();
        this.ws = null;
    }
};

WSClient.prototype.advanceSpinner = function () {
    if (!Array.isArray(this.spinnerFrames) || this.spinnerFrames.length === 0) {
        return;
    }

    var $braille = $("#" + this.formId + " #braille");
    if ($braille.length === 0) {
        return;
    }

    var frame = this.spinnerFrames[this.spinnerIndex];
    $braille.text(frame);
    this.spinnerIndex = (this.spinnerIndex + 1) % this.spinnerFrames.length;
};

WSClient.prototype.resetSpinner = function () {
    this.spinnerIndex = 0;
    var $braille = $("#" + this.formId + " #braille");
    if ($braille.length) {
        $braille.text("");
    }
};

WSClient.prototype.pushCommandBarResult = function (message) {
    if (typeof window.initializeCommandBar !== 'function') {
        return;
    }

    try {
        var commandBar = window.initializeCommandBar();
        if (commandBar && typeof commandBar.showResult === 'function') {
            commandBar.showResult(message);
        }
    } catch (error) {
        console.warn('Unable to update command bar result:', error);
    }
};

WSClient.prototype.attachControl = function (control) {
    this._parentControl = control || null;
};

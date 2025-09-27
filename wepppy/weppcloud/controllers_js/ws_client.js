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
        $("#preflight_status").html("Connected");
        if (this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ "type": "init" }));
        } else {
            console.error("WebSocket is not in OPEN state: ", this.ws.readyState);
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
            if (data.length > 100) {
                data = data.substring(0, 100) + '...';
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

            if (data.includes("TRIGGER")) {
                // need to parse the trigger command and execute it
                // second to last argument is the controller
                // last argument is the event
                var trigger = data.split(' ');
                var controller = trigger[trigger.length - 2];
                var event = trigger[trigger.length - 1];

                if (controller == this.channel) {
                    $("#" + this.formId).trigger(event);
                    if (typeof event === 'string' && event.toUpperCase().includes('COMPLETE')) {
                        this.resetSpinner();
                    }
                }

            }
            else {
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

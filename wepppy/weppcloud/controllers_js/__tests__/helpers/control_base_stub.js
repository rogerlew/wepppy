/* eslint-env node */

module.exports = function createControlBaseStub(overrides) {
    require("../../control_base.js");
    const realBase = global.controlBase ? global.controlBase() : {};
    const statusStreamMock = {
        append: jest.fn(),
        connect: jest.fn(),
        disconnect: jest.fn(),
        clear: jest.fn()
    };

    const base = Object.assign({}, realBase, {
        statusStream: null,
        attach_status_stream: jest.fn(function (self) {
            if (self) {
                self.statusStream = statusStreamMock;
            }
            return statusStreamMock;
        }),
        detach_status_stream: jest.fn(),
        connect_status_stream: jest.fn(),
        disconnect_status_stream: jest.fn(),
        reset_status_spinner: jest.fn(),
        clear_status_messages: jest.fn(),
        append_status_message: jest.fn(),
        reset_panel_state: jest.fn(),
        pushResponseStacktrace: jest.fn(),
        pushErrorStacktrace: jest.fn(),
        set_rq_job_id: jest.fn(),
        render_job_status: jest.fn(),
        update_command_button_state: jest.fn(),
        stop_job_status_polling: jest.fn(),
        schedule_job_status_poll: jest.fn(),
        fetch_job_status: jest.fn(),
        manage_status_stream: jest.fn(),
        should_disable_command_button: jest.fn(() => false),
        triggerEvent: jest.fn()
    }, overrides || {});

    return { base, statusStreamMock };
};

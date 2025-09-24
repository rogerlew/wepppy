"""Backend endpoints for the command bar.

The command bar is a run specific UI compoent with vim style command entry. It
can be opened with the `:` key when the focus is not in a text input. It is a power user
feature for various functions. It expedients tasks for advanced users. And provides a
simple method of adding features without implementing a full UI. 

Many of the commands can use existing endpoints, but some need new ones. This serves
as a home for those endpoints that are command bar specific and don't belong elsewhere.
The `static/js/command-bar.js` is the companion frontend code.

Keep endpoints small and focused. Here are some guidelines:
1. Validate payload + authorization, always call `authorize()`
2. Delegate work to existing NoDB helpers or service objects (as needed)
3. Return `{Success, Content?, Error?}` JSON for the command bar to display

"""

import logging

from flask import Blueprint, jsonify, request

from wepppy.nodb.base import LogLevel, try_redis_get_log_level, try_redis_set_log_level
from wepppy.weppcloud.utils.helpers import authorize


command_bar_bp = Blueprint('command_bar', __name__)

_ALLOWED_LEVELS = {level.name.lower(): level for level in LogLevel}


@command_bar_bp.route('/runs/<string:runid>/<config>/command_bar/loglevel', methods=['POST'])
def set_log_level(runid, config):
    authorize(runid, config)

    payload = request.get_json(silent=True) or {}
    level = payload.get('level')

    if not level:
        return jsonify({'Success': False, 'Error': 'Missing "level" parameter.'}), 400

    level_key = str(level).lower()
    if level_key not in _ALLOWED_LEVELS:
        expected = ', '.join(sorted(_ALLOWED_LEVELS))
        return jsonify({'Success': False, 'Error': f'Invalid log level "{level}". Expected one of {expected}.'}), 400

    try:
        try_redis_set_log_level(runid, level_key)
        effective_value = try_redis_get_log_level(runid)
    except Exception as exc:
        logging.error('Unexpected error setting log level for %s: %s', runid, exc)
        return jsonify({'Success': False, 'Error': 'Failed to update log level. Please try again.'}), 500

    try:
        effective_label = LogLevel(effective_value).name.lower()
    except ValueError:
        effective_label = str(effective_value)

    return jsonify({
        'Success': True,
        'Content': {
            'log_level': effective_label,
            'log_level_value': effective_value
        }
    })

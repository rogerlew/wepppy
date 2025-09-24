import logging

from flask import Blueprint, jsonify, request

from wepppy.nodb.base import LogLevel, try_redis_get_log_level, try_redis_set_log_level
from wepppy.weppcloud.utils.helpers import authorize


command_prompt_bp = Blueprint('command_prompt', __name__)

_ALLOWED_LEVELS = {level.name.lower(): level for level in LogLevel}


@command_prompt_bp.route('/runs/<string:runid>/<config>/command_prompt/loglevel', methods=['POST'])
def set_log_level(runid, config):
    authorize(runid, config, require_owner=True)

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

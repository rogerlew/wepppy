
import os
import socket

_TRUTHY = {'1', 'true', 'yes', 'on'}

def config_app(app, logger=None):
    if logger is None:
        logger = app.logger
        
    _hostname = socket.gethostname()
    logger.info(f"Hostname detected as {_hostname}")

    try:
        from wepppy.weppcloud.configuration import config_app as _config_app
        logger.info("Using environment-driven configuration")
    except ImportError as exc:
        logger.error("Failed to import wepppy.weppcloud.configuration: %s", exc)
        raise

    assert _config_app is not None, "Could not determine configuration"
    logger.info(f"Configuring app")
    
    _config_app(app)

    # Batch runner feature flag defaults
    flag_raw = os.getenv('BATCH_RUNNER_ENABLED')
    if flag_raw is None:
        app.config.setdefault('BATCH_RUNNER_ENABLED', True)
    else:
        app.config['BATCH_RUNNER_ENABLED'] = flag_raw.strip().lower() in _TRUTHY

    if 'BATCH_GEOJSON_MAX_MB' not in app.config:
        raw_limit = os.getenv('BATCH_GEOJSON_MAX_MB')
        try:
            app.config['BATCH_GEOJSON_MAX_MB'] = int(raw_limit) if raw_limit else 10
        except (TypeError, ValueError):
            app.config['BATCH_GEOJSON_MAX_MB'] = 10

    app.config.setdefault('PROFILE_RECORDER_ENABLED', True)
    if 'PROFILE_DATA_ROOT' not in app.config:
        app.config['PROFILE_DATA_ROOT'] = os.getenv('PROFILE_DATA_ROOT', '/workdir/wepppy-test-engine-data')
    if 'PROFILE_RECORDER_GLOBAL_ROOT' not in app.config:
        app.config['PROFILE_RECORDER_GLOBAL_ROOT'] = os.getenv('PROFILE_RECORDER_GLOBAL_ROOT')
    app.config.setdefault(
        'PROFILE_RECORDER_ASSEMBLER_ENABLED',
        app.config.get('PROFILE_RECORDER_ENABLED', True),
    )

    coverage_flag = os.getenv('ENABLE_PROFILE_COVERAGE')
    if coverage_flag is None:
        app.config.setdefault('PROFILE_COVERAGE_ENABLED', False)
    else:
        app.config['PROFILE_COVERAGE_ENABLED'] = coverage_flag.strip().lower() in _TRUTHY

    app.config.setdefault(
        'PROFILE_COVERAGE_DIR',
        os.getenv('PROFILE_COVERAGE_DIR', '/workdir/wepppy-test-engine-data/coverage'),
    )

    coverage_config_path = os.getenv('PROFILE_COVERAGE_CONFIG')
    if coverage_config_path:
        app.config['PROFILE_COVERAGE_CONFIG'] = coverage_config_path
    else:
        app.config.setdefault(
            'PROFILE_COVERAGE_CONFIG',
            os.path.join(app.root_path, 'coverage.profile-playback.ini'),
        )

    app.config.setdefault(
        'PROFILE_COVERAGE_CONTEXT_PREFIX',
        os.getenv('PROFILE_COVERAGE_CONTEXT_PREFIX', 'profile'),
    )

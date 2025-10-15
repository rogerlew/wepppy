
import os
import socket

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
        app.config['BATCH_RUNNER_ENABLED'] = flag_raw.strip().lower() in {'1', 'true', 'yes', 'on'}

    if 'BATCH_GEOJSON_MAX_MB' not in app.config:
        raw_limit = os.getenv('BATCH_GEOJSON_MAX_MB')
        try:
            app.config['BATCH_GEOJSON_MAX_MB'] = int(raw_limit) if raw_limit else 10
        except (TypeError, ValueError):
            app.config['BATCH_GEOJSON_MAX_MB'] = 10

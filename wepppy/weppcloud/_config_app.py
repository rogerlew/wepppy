
import socket

def config_app(app, logger=None):
    if logger is None:
        logger = app.logger
        
    _hostname = socket.gethostname()
    logger.info(f"Hostname detected as {_hostname}")

    _config_app = None
    if 'wepp1' in _hostname or 'forest' in _hostname:
        try:
            from wepppy.weppcloud.wepp1_config import config_app as _config_app
            logger.info("Using wepp1 configuration")
        except:
            pass
    elif 'wepp2' in _hostname:
        from wepppy.weppcloud.wepp2_config import config_app as _config_app
        logger.info("Using wepp2 configuration")

    if _config_app is None:
        from wepppy.weppcloud.standalone_config import config_app as _config_app
        logger.info("Using standalone configuration")

    assert _config_app is not None, "Could not determine configuration"
    logger.info(f"Configuring app")
    
    _config_app(app)

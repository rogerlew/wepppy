"""Immutable, process-owned source metadata; never resolved secret values."""
from dataclasses import replace

from .safe_traceback import SecretSourceProfile, SecretSourceSpec


def _sources(*names):
    return tuple(SecretSourceSpec(name, name + '_FILE') for name in names)


REDIS = (SecretSourceSpec('REDIS_PASSWORD', 'REDIS_PASSWORD_FILE', decoder='redis'),
         SecretSourceSpec('REDIS_URL', decoder='url'),
         SecretSourceSpec('RQ_REDIS_URL', decoder='url', fallback_for=('REDIS_URL',)),
         SecretSourceSpec('SESSION_REDIS_URL', decoder='url', fallback_for=('REDIS_URL', 'RQ_REDIS_URL')))
SESSION_REDIS = (SecretSourceSpec('SESSION_REDIS_URL', decoder='url'),)
DATABASE = (SecretSourceSpec('POSTGRES_PASSWORD', 'POSTGRES_PASSWORD_FILE',
                             fallback_for=('SQLALCHEMY_DATABASE_URI', 'DATABASE_URL')),
            SecretSourceSpec('SQLALCHEMY_DATABASE_URI', decoder='database-url'),
            SecretSourceSpec('DATABASE_URL', decoder='database-url', fallback_for=('SQLALCHEMY_DATABASE_URI',)))
FLASK = _sources('SECRET_KEY', 'SECURITY_PASSWORD_SALT')
MAIL_OAUTH = (*_sources('ZOHO_NOREPLY_EMAIL_PASSWORD', 'OAUTH_GITHUB_CLIENT_SECRET',
                       'OAUTH_GOOGLE_CLIENT_SECRET', 'OAUTH_ORCID_CLIENT_SECRET'),
              *(SecretSourceSpec(name) for name in ('GITHUB_OAUTH_CLIENT_SECRET', 'GITHUB_OAUTH_SECRET_KEY',
                                                   'GOOGLE_OAUTH_CLIENT_SECRET', 'ORCID_OAUTH_CLIENT_SECRET',
                                                   'ORCID_OAUTH_SECRET_KEY')))
DISCORD = (SecretSourceSpec(None, package_file=('weppcloud2', 'discord_bot/.bot_token')),)
FLASK_INIT = (*DISCORD, *REDIS, *SESSION_REDIS, *DATABASE, *FLASK, *_sources('AGENT_JWT_SECRET'), *MAIL_OAUTH)
AUTH = (*_sources('WEPP_AUTH_JWT_SECRET'),
        SecretSourceSpec('WEPP_AUTH_JWT_SECRETS', 'WEPP_AUTH_JWT_SECRETS_FILE', decoder='comma'))
MODEL = _sources('OPENTOPOGRAPHY_API_KEY', 'CLIMATE_ENGINE_API_KEY', 'OPENET_API_KEY', 'WC_TOKEN')
WEB = SecretSourceProfile('web', (*(replace(spec, required=True) if spec.setting in {'SECRET_KEY', 'SECURITY_PASSWORD_SALT'} else spec for spec in FLASK_INIT), *AUTH, *_sources('CAP_SECRET'), *MODEL))
RQ_ENGINE = SecretSourceProfile('rq-engine', (*FLASK_INIT, *AUTH, *_sources('CAP_SECRET'), *MODEL))
BROWSE = SecretSourceProfile('browse', (*FLASK_INIT, *AUTH, *_sources('DTALE_INTERNAL_TOKEN')))
DOWNLOAD = SecretSourceProfile('download', (*FLASK_INIT, *AUTH))
QUERY = SecretSourceProfile('query', (*FLASK_INIT, *AUTH, *_sources('WEPP_MCP_JWT_SECRET')))
DTALE = SecretSourceProfile('dtale', (*FLASK_INIT, *_sources('DTALE_INTERNAL_TOKEN')))
REDIS_ONLY = SecretSourceProfile('redis-only', REDIS)
WORKER = SecretSourceProfile('worker', (*FLASK_INIT, *MODEL))
BATCH_WORKER = SecretSourceProfile('batch-worker', (*WORKER.sources,
    SecretSourceSpec(None, 'WEPPCLOUDR_K8S_IDENTITY_TOKEN_FILE')))
ARCHIVE_WORKER = SecretSourceProfile('archive-worker', (*REDIS, *DISCORD))
ARCHIVE_POSTGRES_WORKER = SecretSourceProfile('archive-postgres-worker', (*REDIS, *DATABASE, *DISCORD))
SCHEDULER = SecretSourceProfile('scheduler', (*REDIS, *DATABASE, *DISCORD))
CONTROL_PLANE = SecretSourceProfile('control-plane', (*REDIS,
    SecretSourceSpec(None, 'WEPPCLOUDR_CONTROL_PLANE_TOKEN_FILE', required=True),
    SecretSourceSpec(None, 'WEPPCLOUDR_TLS_KEY_FILE', required=True, decoder='pem'),
    SecretSourceSpec('kubernetes-service-account', required=True,
                     path='/var/run/secrets/kubernetes.io/serviceaccount/token')))
SHAPE = SecretSourceProfile('shape')
PLAYBACK = SecretSourceProfile('profile-playback', (*FLASK_INIT, *_sources('ADMIN_PASSWORD')))


def worker_profile(queues=()):
    """Select from explicit worker queues and existing project-commit mode."""
    import os
    names = {getattr(queue, 'name', queue) for queue in queues}
    if 'batch' in names:
        return BATCH_WORKER
    if names == {'fork-archive'}:
        return ARCHIVE_POSTGRES_WORKER if os.getenv('WEPPPY_PROJECT_COMMIT_MODE', 'disabled') == 'postgres' else ARCHIVE_WORKER
    return WORKER

WOJAK = SecretSourceProfile('wojak-bootstrap', tuple(SecretSourceSpec(name) for name in ('AGENT_JWT_TOKEN', 'AGENT_JWT_SECRET')))

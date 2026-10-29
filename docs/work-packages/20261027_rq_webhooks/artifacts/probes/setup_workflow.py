"""Prepare disposable copies and secrets for the local workflow acceptance stack."""
from pathlib import Path
import json
import zipfile
import secrets
import shutil

repo = Path(__file__).resolve().parents[5]
root = repo / '.pytest_cache/webhook-workflows'
if root.exists():
    raise SystemExit('Disposable workflow directory already exists; inspect before reusing.')
(root / 'private').mkdir(parents=True)
(root / 'private/jwt').write_text(secrets.token_urlsafe(48))
(root / 'private/jwt').chmod(0o600)
# Run prepare_model_copies.py inside the fixture after configuring managed roots.
(root / 'runs').mkdir()
(root / 'wc1').mkdir()
shutil.copyfile('/wc1/culverts/76af29b8-3729-4061-b1ed-3155a82680e8/payload.zip', root / 'culvert-payload.zip')
# Controlled domain failure inputs; all source artifacts remain read-only.
with zipfile.ZipFile(root / 'culvert-payload.zip') as source, zipfile.ZipFile(root / 'culvert-domain-failure.zip', 'w', zipfile.ZIP_DEFLATED) as target:
    for name in source.namelist():
        data = source.read(name)
        if name == 'culverts/culvert_points.geojson':
            points = json.loads(data)
            for point in points['features']:
                point['geometry']['coordinates'][0] += 1000000
            data = json.dumps(points).encode()
        target.writestr(name, data)
    for name in ('landuse/nlcd_30m.tif', 'soils/ssurgo_30m.tif'):
        target.write('/wc1/culverts/76af29b8-3729-4061-b1ed-3155a82680e8/' + name, name)
(root / 'runtime.env').write_text('''REDIS_HOST=redis
REDIS_URL=redis://redis:6379/9
WEPPPY_PROJECT_COMMIT_MODE=disabled
WEPPCLOUD_RUN_CATALOG_WRITE_MODE=timestamp_only
WEPPCLOUD_RUN_CATALOG_READ_MODE=legacy
ENABLE_PROFILE_COVERAGE=false
WEPP_AUTH_JWT_SECRET_FILE=/acceptance/private/jwt
WEPP_AUTH_JWT_ISSUER=webhook-local-acceptance
PROFILE_PLAYBACK_RUN_ROOT=/acceptance/runs
PROFILE_PLAYBACK_USE_CLONE=true
CULVERTS_ROOT=/acceptance/culverts
QUERY_CATALOG_ROOTS_JSON=[{"path":"/acceptance/runs","namespace":"acceptance:runs","coordination":"/acceptance/catalog-locks","layout":"flat"},{"path":"/acceptance/culverts","namespace":"acceptance:culverts","coordination":"/acceptance/catalog-locks","layout":"culverts"}]
RQ_WEBHOOK_ENVIRONMENT=disposable-workflow-acceptance
RQ_WEBHOOK_ADMISSION=enabled
RQ_WEBHOOK_INSTRUMENTATION=rq-wh-01
RQ_WEBHOOK_DISPATCH=enabled
SSL_CERT_FILE=/tls/cert.pem
MPLCONFIGDIR=/tmp/matplotlib
WEPPPY_NCPU=2
WBT_MAX_PROCS=2
''')
print('Prepared owned fixture roots and copied upload; prepare model copies and arm the disposable Redis identity before dispatch.')

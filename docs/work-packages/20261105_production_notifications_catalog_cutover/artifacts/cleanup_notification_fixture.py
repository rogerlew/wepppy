"""Remove only the owned notification fixture; retain every production notice."""
if not __debug__:
 raise RuntimeError("Optimized Python is prohibited for fixture cleanup")
from pathlib import Path
import os,json,shutil,hashlib
import sqlalchemy as sa
from wepppy.weppcloud.app import app,db,Run
from wepppy.weppcloud.user_preferences import RunRegistrationReceipt,delete_registered_run
from wepppy.weppcloud.notifications.schema import notifications as n,recipients as r
from wepppy.query_engine.catalog_refresh import catalog_lifecycle_guard,invalidate_catalog_incarnation
assert os.environ['EXTERNAL_HOST']=='wepp.cloud'
root=Path('/cutover/acceptance');f=json.loads((root/'forest-fixture.json').read_text());wd=Path(f['wd'])
assert f['runid']=='notifications-fixture-4c1128b95b' and f['registration_id']==59273 and f['user_id']==5445
assert not (root/'notification-fixture-cleanup.json').exists()
with catalog_lifecycle_guard(wd),app.app_context():
 assert wd==Path('/wc1/runs/no')/f['runid'] and wd.resolve()==wd and not wd.is_symlink()
 assert hashlib.sha256((wd/'TTL').read_bytes()).hexdigest()==f['ttl_sha256']
 run=db.session.get(Run,f['registration_id']);assert run and run.runid==f['runid'] and run.owner_id==str(f['user_id']) and run.config=='disturbed9002-10m'
 with db.engine.begin() as c:
  seeded=list(c.execute(sa.select(n.c.id,n.c.source_key).where(n.c.id.in_(f['notice_ids']))))
  assert len(seeded)==100 and {row.source_key for row in seeded}=={'acceptance:'+f['runid']+':'+str(i) for i in range(100)}
  ids=list(c.scalars(sa.select(n.c.id).where(sa.or_(n.c.id.in_(f['notice_ids']),sa.and_(n.c.subject_type=='run',n.c.subject_id==f['registration_id'])))))
  assert len(ids)==101 and set(c.scalars(sa.select(r.c.user_id).where(r.c.notification_id.in_(ids))))=={f['user_id']}
  unrelated=set(c.scalars(sa.select(n.c.id).where(~n.c.id.in_(ids))))
  assert len(unrelated)>=4992
  c.execute(n.delete().where(n.c.id.in_(ids)))
  assert unrelated<=set(c.scalars(sa.select(n.c.id)))
 delete_registered_run(RunRegistrationReceipt(f['registration_id'],f['runid'],'disturbed9002-10m',f['user_id']))
 assert db.session.execute(sa.select(Run.id).where(Run.id==f['registration_id'])).scalar_one_or_none() is None
 invalidate_catalog_incarnation(wd,recursive=True)
 shutil.rmtree(wd)
 with db.engine.connect() as c:
  assert c.scalar(sa.select(sa.func.count()).select_from(r).where(r.c.user_id==f['user_id']))==0
  assert unrelated<=set(c.scalars(sa.select(n.c.id)))
  remaining=c.scalar(sa.select(sa.func.count()).select_from(n))
receipt={'fixture_registration_removed':f['registration_id'],'fixture_notifications_removed':101,'fixture_directory_removed':not wd.exists(),'nonfixture_notifications_retained':remaining,'all_preexisting_nonfixture_ids_preserved':True,'accounts_retained_for_model_acceptance':True}
p=root/'notification-fixture-cleanup.json';p.write_text(json.dumps(receipt,indent=2));p.chmod(0o600);print(json.dumps(receipt))

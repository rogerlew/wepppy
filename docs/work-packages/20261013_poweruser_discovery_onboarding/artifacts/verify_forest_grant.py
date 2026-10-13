"""Read persisted Forest onboarding state independently of the browser receipt."""
from pathlib import Path
import json
import sqlalchemy as sa
from wepppy.weppcloud.app import app, db, User, Run
from wepppy.weppcloud.utils.feature_access_schema import acceptances, memberships
from wepppy.weppcloud.utils.feature_access_store import FeatureAccessStore
from wepppy.weppcloud.utils.feature_access_web import INTERNAL_STATEMENT_VERSION, POWERUSER_STATEMENT_VERSION

root = Path(__file__).parent
credentials = json.loads(Path('/workdir/wepppy/docker/secrets/puux-browser.json').read_text())
with app.app_context():
    store = FeatureAccessStore(db.engine)
    states = {}
    for label, credential in credentials.items():
        user_id = credential['id']
        user = db.session.get(User, user_id)
        state = store.account_status(user_id, INTERNAL_STATEMENT_VERSION,
                                      poweruser_statement_version=POWERUSER_STATEMENT_VERSION)
        with db.engine.connect() as conn:
            count = conn.scalar(sa.select(sa.func.count()).select_from(acceptances).where(
                acceptances.c.user_id == user_id, acceptances.c.statement_kind == 'poweruser'))
        states[label] = {'id':user_id,'roles': sorted(r.name for r in user.roles),
                         'poweruser':state['poweruser'],'poweruser_acceptances':count,
                         'internal_acknowledged':state['acknowledged'],
                         'internal_memberships':len(state['memberships']), 'runs':len(user.runs)}
    assert states['ordinary']['poweruser'] == {'has_role':True,'accepted':True}
    assert states['ordinary']['poweruser_acceptances'] == 1
    assert states['ordinary']['roles'] == ['PowerUser','User']
    assert states['ordinary']['runs'] == 0
    assert states['legacy']['poweruser'] == {'has_role':True,'accepted':False}
    assert states['populated']['runs'] == 1 and states['populated']['poweruser']['has_role'] is False
    assert all(v['internal_memberships']==0 and not v['internal_acknowledged'] for v in states.values())
    receipt = {'states':states,'duplicate_grant_did_not_duplicate_acceptance':True,
               'statement_version':POWERUSER_STATEMENT_VERSION,'database_readback':'real Forest account database'}
    (root/'forest-grant-readback.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

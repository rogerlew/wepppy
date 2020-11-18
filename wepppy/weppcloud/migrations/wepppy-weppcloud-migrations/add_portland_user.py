import sys

from os.path import exists
from os.path import join as _join

from wepppy.weppcloud.app import *

wss = [
    {"runid": "portland_BRnearMultnoma_CurCond.202009.cl532.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_CurCond.202009.cl532.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_CurCond.202009.cl532.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_CurCond.202009.cl532.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_CurCond.202009.cl532.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_CurCond.202009.cl532.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_CurCond.202009.cl532.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BRnearMultnoma_CurCond.202009.cl532_gridmet.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_CurCond.202009.cl532_gridmet.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_CurCond.202009.cl532_gridmet.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_CurCond.202009.cl532_gridmet.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_CurCond.202009.cl532_gridmet.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_CurCond.202009.cl532_gridmet.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_CurCond.202009.cl532_gridmet.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BRnearMultnoma_CurCond.202009.cl532_future.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_CurCond.202009.cl532_future.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_CurCond.202009.cl532_future.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_CurCond.202009.cl532_future.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_CurCond.202009.cl532_future.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_CurCond.202009.cl532_future.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_CurCond.202009.cl532_future.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BRnearMultnoma_SimFire_Eagle.202009.cl532.chn_cs200", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_FirCreek_SimFire_Eagle.202009.cl532.chn_cs150", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_LittleSandy_SimFire_Eagle.202009.cl532.chn_cs110", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_NorthFork_SimFire_Eagle.202009.cl532.chn_cs140", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_SouthFork_SimFire_Eagle.202009.cl532.chn_cs160", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_CedarCreek_SimFire_Eagle.202009.cl532.chn_cs150", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_BlazedAlder_SimFire_Eagle.202009.cl532.chn_cs50", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_BRnearMultnoma_SimFire_Norse.202009.cl532.chn_cs200", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_FirCreek_SimFire_Norse.202009.cl532.chn_cs150", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_LittleSandy_SimFire_Norse.202009.cl532.chn_cs110", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_NorthFork_SimFire_Norse.202009.cl532.chn_cs140", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_SouthFork_SimFire_Norse.202009.cl532.chn_cs160", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_CedarCreek_SimFire_Norse.202009.cl532.chn_cs150", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_BlazedAlder_SimFire_Norse.202009.cl532.chn_cs50", "cfg": "portland-simfire-eagle-snow"},
    {"runid": "portland_BRnearMultnoma_HighSevS.202009.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_HighSevS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_HighSevS.202009.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_HighSevS.202009.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_HighSevS.202009.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_HighSevS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_HighSevS.202009.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BRnearMultnoma_ModSevS.202009.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_ModSevS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_ModSevS.202009.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_ModSevS.202009.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_ModSevS.202009.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_ModSevS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_ModSevS.202009.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BRnearMultnoma_LowSevS.202009.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_LowSevS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_LowSevS.202009.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_LowSevS.202009.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_LowSevS.202009.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_LowSevS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_LowSevS.202009.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BRnearMultnoma_PrescFireS.202009.chn_cs200", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_FirCreek_PrescFireS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_LittleSandy_PrescFireS.202009.chn_cs110", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_NorthFork_PrescFireS.202009.chn_cs140", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_SouthFork_PrescFireS.202009.chn_cs160", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_CedarCreek_PrescFireS.202009.chn_cs150", "cfg": "portland-wepp_bd16b69_snow"},
    {"runid": "portland_BlazedAlder_PrescFireS.202009.chn_cs50", "cfg": "portland-wepp_bd16b69_snow"}
]
if __name__ == "__main__":
    email = sys.argv[-1]
    user = User.query.filter(User.email == email.lower()).first()
    portland_group = Role.query.filter(Role.name == 'PortlandGroup').first()

    if not user.has_role(portland_group) == portland_group:
        user_datastore.add_role_to_user(user, portland_group)

    for ws in wss:
        runid = ws['runid']
        cfg = ws['cfg']
        print(runid, cfg)
        run = Run.query.filter(Run.runid == runid).first()
        assert run is not None
        user_datastore.add_run_to_user(user, run)

from wepppy.rq.project_rq_fork import prepare_fork_run
from wepppy.io_wait import wait_for_paths
from wepppy.nodb.core import Ron, Landuse, Soils
from wepppy.nodb.mods.disturbed import Disturbed
prepare_fork_run('chemotherapeutic-scope','century-investigation',undisturbify=False,status_channel='local',publish_status=lambda channel,message:print(message,flush=True),get_wd=lambda _: '/wc1/runs/ch/chemotherapeutic-scope',get_primary_wd=lambda _: '/workdir/wepp-century-investigation-20261021/project-fork',wait_for_paths=wait_for_paths,ron_cls=Ron,disturbed_cls=Disturbed,landuse_cls=Landuse,soils_cls=Soils,initialize_ttl=None)

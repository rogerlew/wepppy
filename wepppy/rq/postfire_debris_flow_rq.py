"""Tracked workers for immutable Staley M1 upload and model attempts."""
import logging
from rq import get_current_job
from wepppy.nodb.status_messenger import StatusMessenger
from wepppy.rq.exception_logging import with_exception_logging
from pathlib import Path

from wepppy.weppcloud.utils.helpers import get_wd
from wepppy.nodb.mods.postfire_debris_flow import production
from wepppy.nodb.mods.postfire_debris_flow.dnbr import DnbrError
from wepppy.nodb.mods.postfire_debris_flow.m1_inputs import M1Error
from wepppy.nodb.mods.postfire_debris_flow.rainfall_io import RainfallError

logger = logging.getLogger(__name__)


def _execute(runid, identity, kind):
    wd = get_wd(runid)
    job = get_current_job()
    if job:
        StatusMessenger.publish(f"{runid}:postfire_debris_flow", f"rq:{job.id} STARTED {kind}({runid})")
    try:
        if kind == 'upload_attempt':
            production.execute_upload(wd, identity)
        else:
            from whitebox_tools import WhiteboxTools
            tool = WhiteboxTools()
            production.execute_model(wd, identity, Path(tool.exe_path)/tool.exe_name)
    except (DnbrError, M1Error, RainfallError, production.WorkflowError) as exc:
        code = exc.code
        phase = 'needs_scale' if code == 'ambiguous_encoding' else ('superseded' if code=='superseded' else 'failed')
        message = ('Could not determine the dNBR value scale. Choose the scale used by your map.'
                   if phase=='needs_scale' else 'The operation could not finish. Check the project inputs and job log.')
        production.update_attempt(wd,kind,identity,phase=phase,error={'code':code,'message':message},retryable=True)
        logger.exception('Postfire operation failed: %s %s',runid,identity)
        if phase!='needs_scale':raise RuntimeError(f'Postfire operation failed ({code}). See protected run logs.') from None
    except Exception:  # Worker boundary: persist terminal failure; expose a sanitized RQ error.
        logger.exception('Unexpected postfire failure: %s %s',runid,identity)
        production.update_attempt(wd,kind,identity,phase='failed',error={'code':'operation_failed','message':'The operation could not finish. See the job log.'},retryable=True)
        raise RuntimeError('Postfire operation failed. See protected run logs.') from None
    if job:
        StatusMessenger.publish(f'{runid}:postfire_debris_flow', f'rq:{job.id} COMPLETED {kind}({runid})')
    return {'message': 'Upload processed.' if kind=='upload_attempt' else 'Model run complete.'}


@with_exception_logging
def upload_dnbr_rq(runid, identity):
    return _execute(runid, identity, 'upload_attempt')


@with_exception_logging
def run_m1_rq(runid, identity):
    return _execute(runid, identity, 'run_attempt')

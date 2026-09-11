"""Authenticated, bounded transport for the production M1 control."""
from contextlib import asynccontextmanager
import hashlib
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import uuid

import redis
from redis.exceptions import RedisError
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException
import stat
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.core import Ron
from wepppy.nodb.redis_prep import RedisPrep
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.rq.postfire_debris_flow_rq import upload_dnbr_rq, run_m1_rq, run_m3_rq
from wepppy.rq.submission_recovery import rq_submission_lock, enqueue_tracked_rq_job, RqSubmissionConflict, RqEnqueueVerificationError
from wepppy.weppcloud.utils.helpers import get_wd
from rq import Queue
from .auth import AuthError, authorize_run_access, require_jwt
from .responses import error_response
from .openapi import agent_route_responses, rq_operation_id

router = APIRouter()
logger = logging.getLogger(__name__)
PREFIX = '/runs/{runid}/{config}/postfire-debris-flow'
LIMIT = 100*1024*1024
REQUEST_LIMIT = 201*1024*1024


@asynccontextmanager
async def upload_form(request):
    parser = MultiPartParser(request.headers, request.stream(), max_files=2, max_fields=3)
    try:
        form = await parser.parse()
        yield form
    finally:
        # Own the parser lifetime: Starlette only cleans up MultiPartException.
        # Closing SpooledTemporaryFiles also covers cancellation and disconnect.
        for handle in parser._files_to_close_on_error:
            handle.close()


class DownloadResponse(StreamingResponse):
    def __init__(self, handle, **kwargs):
        self.handle = handle
        super().__init__(self.chunks(), **kwargs)

    def chunks(self):
        while chunk := self.handle.read(65536):
            yield chunk

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.handle.close()


def context(request, runid, config, write=False, export=False):
    claims = require_jwt(request, required_scopes=['rq:export' if export else 'rq:enqueue' if write else 'rq:status'])
    authorize_run_access(claims,runid)
    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    if config.removesuffix('.cfg') != ron.config_stem.removesuffix('.cfg'):
        raise p.WorkflowError('config_mismatch','The project configuration changed. Reload the page.',409)
    if write and ron.readonly:
        raise p.WorkflowError('readonly','This project is read-only.',403)
    return wd


def pairs_unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise p.WorkflowError('invalid_payload','Duplicate request field.')
        result[key]=value
    return result


async def json_body(request):
    body=bytearray()
    async for chunk in request.stream():
        if len(body)+len(chunk)>4096:raise p.WorkflowError('resource_limit','Request is too large.',413)
        body.extend(chunk)
    if request.headers.get('content-type','').split(';')[0]!='application/json':
        raise p.WorkflowError('invalid_payload','Expected a JSON request.')
    try:
        data=json.loads(body,object_pairs_hook=pairs_unique,parse_constant=lambda value: invalid('Nonfinite request value.'))
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise p.WorkflowError('invalid_payload','Invalid JSON request.') from exc
    if not isinstance(data,dict):invalid('Expected an object request.')
    return data


def invalid(message):
    raise p.WorkflowError('invalid_payload',message)


def encoding(data):
    mode=data.get('scale_mode','auto')
    if mode not in ('auto','normalized','scaled_1000','custom'):invalid('Choose a supported dNBR value scale.')
    factor,offset=None,0.
    if mode=='custom':
        from wepppy.nodb.mods.postfire_debris_flow.dnbr import _encoding
        factor,offset=_encoding(data.get('scale_factor'),data.get('add_offset'))
    elif 'scale_factor' in data or 'add_offset' in data:invalid('Custom scale fields require Custom scale.')
    return {'mode':mode,'factor':factor,'offset':offset}


def new_attempt(wd, kind, snapshot, **extra):
    from wepppy.nodb.mods.postfire_debris_flow.observability import require_visible_storage, write_json
    require_visible_storage(wd)
    identity=uuid.uuid4().hex
    path=p.directory(wd,identity)
    path.mkdir(parents=True,mode=0o770)
    record={'id':identity,'job_id':None,'phase':'staged','created_at':p.now(),'error':None,
            'retryable':False,'snapshot':snapshot,'job_key':'postfire_upload_rq' if kind=='upload_attempt' else 'postfire_m1_rq',**extra}
    write_json(p.safe(wd,path/'status.json',exists=False), {'schema_version':1,'kind':kind,'attempt':record})
    return record,path


def enqueue(q,wd,runid,kind,record):
    def save_receipt(job_id):
        record['job_id'] = job_id
        record['phase'] = 'queued'
        def apply(state):
            state[kind] = record
            if kind == 'run_attempt':
                state['frequency_source'] = record['snapshot']['frequency']
                state['model'] = record.get('model', 'M1')
        p.mutable(wd).change(apply)
    prep=RedisPrep.getInstance(wd)
    try:
        job=enqueue_tracked_rq_job(q,upload_dnbr_rq if kind=='upload_attempt' else run_m3_rq if record.get('model') == 'M3' else run_m1_rq,
                    prep=prep,job_key=record['job_key'],runid=runid,args=(runid,record['id']),on_job_id=save_receipt,
                    timeout=int(os.getenv('RQ_ENGINE_RQ_TIMEOUT','216000')))
    except (RedisError,RqEnqueueVerificationError):
        p.update_attempt(wd,kind,record['id'],phase='enqueue_unknown')
        raise
    except RqSubmissionConflict:
        p.update_attempt(wd,kind,record['id'],phase='failed',retryable=True)
        raise
    # The worker can start before enqueue returns; all producer state is saved above.
    return JSONResponse({'job_id':job.id,'result':{'attempt_id':record['id']}})


def ensure_idle(state,kind):
    attempt=state[kind]
    if attempt and attempt['phase'] in p.ACTIVE:
        raise p.WorkflowError('busy','An operation is already running.',409)


def boundary_error(exc):
    if isinstance(exc,AuthError):return error_response(exc.message,status_code=exc.status_code,code=exc.code)
    if isinstance(exc,p.WorkflowError):return error_response(str(exc),status_code=exc.status,code=exc.code)
    if isinstance(exc,(RqSubmissionConflict,NoDbAlreadyLockedError)):return error_response('An operation is already running.',status_code=409,code='busy')
    if isinstance(exc,HTTPException):return error_response(str(exc.detail),status_code=413 if "size limit" in str(exc.detail) else 400,code="invalid_payload")
    if isinstance(exc,MultiPartException):return error_response(str(exc),status_code=413,code='resource_limit')
    from wepppy.nodb.mods.postfire_debris_flow.dnbr import DnbrError
    if isinstance(exc,DnbrError):return error_response(str(exc),status_code=400,code=exc.code)
    logger.exception('Postfire boundary failure')
    return error_response('The operation could not finish. Check the project data and job log.',status_code=503,code='operation_failed')


@router.get(PREFIX+'/state', summary='Read Staley model readiness and accepted files',
    description='Requires Bearer rq:status and authorized run access. See the model selection contract.',
    tags=['rq-engine','runs'], operation_id=rq_operation_id('postfire_state'),
    responses=agent_route_responses(success_code=200, success_description='Operation succeeded.',
        extra={400:'Invalid request.',404:'No accepted file or retained candidate.',409:'Busy or changed project data.',413:'Upload limit exceeded.',422:'Required project data unavailable.',503:'Service unavailable.'}))
async def state(runid:str,config:str,request:Request):
    try:
        return JSONResponse({'result':p.get_state(context(request,runid,config),config)})
    except (AuthError,p.WorkflowError,OSError,ValueError,RedisError) as exc:
        return boundary_error(exc)


@router.post(PREFIX+'/upload-dnbr', summary='Upload a dNBR raster',
    description='Requires Bearer rq:enqueue and authorized run access. See the production M1 contract.',
    tags=['rq-engine','runs'], operation_id=rq_operation_id('postfire_upload_dnbr'),
    responses=agent_route_responses(success_code=200, success_description='Operation succeeded.',
        extra={400:'Invalid request.',404:'No accepted file or retained candidate.',409:'Busy or changed project data.',413:'Upload limit exceeded.',422:'Required project data unavailable.',503:'Service unavailable.'}))
async def upload(runid:str,config:str,request:Request):
    record = None
    copying = False
    try:
        wd=context(request,runid,config,True)
        if not p.get_state(wd,config,reconcile=False)['upload_ready']:raise p.WorkflowError('missing_prerequisite','Delineate an eligible watershed before uploading dNBR.',422)
        count=0
        async def receive():
            nonlocal count
            message=await request.receive()
            count+=len(message.get('body',b''))
            if count>REQUEST_LIMIT:raise MultiPartException('Upload exceeds the request size limit.')
            return message
        bounded=Request(request.scope,receive)
        async with upload_form(bounded) as form:
            data=pairs_unique(form.multi_items())
            if set(data)-{'file','companion','scale_mode','scale_factor','add_offset'}:invalid('Unexpected upload field.')
            values={k:v for k,v in data.items() if k not in ('file','companion')}
            if any(not isinstance(v,str) or len(v.encode())>256 for v in values.values()):invalid('Invalid upload option.')
            selected=encoding(values)
            file=data.get('file');companion=data.get('companion')
            if not isinstance(file,UploadFile) or not file.filename:invalid('Choose a dNBR raster file.')
            uploads=[file]
            if companion is not None:
                if not isinstance(companion,UploadFile) or Path(file.filename).suffix.lower()!='.vrt':invalid('Referenced raster is only valid with a VRT.')
                uploads.append(companion)
            for item in uploads:
                name=item.filename
                if not name or len(name.encode())>255 or any(ord(c)<32 for c in name) or name!=Path(name).name or '\\' in name or name.startswith('.') or Path(name).suffix.lower() not in ('.tif','.tiff','.img','.vrt'):invalid('Upload a GeoTIFF, self-contained IMG or supported VRT raster.')
            if len({item.filename for item in uploads})!=len(uploads):invalid('Uploaded filenames must differ.')
            with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
                with rq_submission_lock(conn,f'{runid}:postfire-admission',lifecycle_key=runid):
                    context(request,runid,config,True)
                    if not p.get_state(wd,config,reconcile=False)['upload_ready']:
                        raise p.WorkflowError('missing_prerequisite','Delineate an eligible watershed before uploading dNBR.',422)
                    ensure_idle(p.reconcile_attempts(wd,p.state_at(wd),conn,persist=True),'upload_attempt')
                    record,path=new_attempt(wd,'upload_attempt',p.sources(wd,rainfall=False)[4],filename=file.filename,encoding=selected)
                    copying = True
                    record['source_id']=record['id'];record['source_sha256']={};dest=path/'source';dest.mkdir(mode=0o770)
                    for item in uploads:
                        checksum=hashlib.sha256()
                        size=0;cap=65536 if Path(item.filename).suffix.lower()=='.vrt' else LIMIT
                        with (dest/item.filename).open('xb') as output:
                            while chunk:=await item.read(65536):
                                size+=len(chunk)
                                if size>cap:raise p.WorkflowError('resource_limit','Raster exceeds its upload size limit.',413)
                                output.write(chunk)
                                checksum.update(chunk)
                        if not size:invalid('Uploaded raster is empty.')
                        record['source_sha256'][str((dest/item.filename).relative_to(Path(wd)))]=checksum.hexdigest()
                    copying = False
                    return enqueue(Queue(connection=conn),wd,runid,'upload_attempt',record)
    except (AuthError,p.WorkflowError,OSError,ValueError,RedisError,RqEnqueueVerificationError,RqSubmissionConflict,NoDbAlreadyLockedError,MultiPartException,HTTPException,ClientDisconnect) as exc:
        if copying and record is not None:
            # Retain a failed transfer independently of the prior accepted NoDb state.
            from wepppy.nodb.mods.postfire_debris_flow.observability import write_json, record_error
            record.update(phase='failed', ended_at=p.now(), error={'code':'upload_incomplete',
                          'message':'The upload did not finish.'})
            try:
                record_error(wd, record['id'])
                write_json(p.safe(wd,path/'status.json',exists=False),
                           {'schema_version':1,'kind':'upload_attempt','attempt':record})
            except (OSError, ValueError):
                logger.exception('Could not retain failed upload record: %s', record['id'])
        return boundary_error(exc)


@router.post(PREFIX+'/retry-dnbr', summary='Correct a retained dNBR scale',
    description='Requires Bearer rq:enqueue and authorized run access. See the production M1 contract.',
    tags=['rq-engine','runs'], operation_id=rq_operation_id('postfire_retry_dnbr'),
    responses=agent_route_responses(success_code=200, success_description='Operation succeeded.',
        extra={400:'Invalid request.',404:'No accepted file or retained candidate.',409:'Busy or changed project data.',413:'Upload limit exceeded.',422:'Required project data unavailable.',503:'Service unavailable.'}))
async def retry(runid:str,config:str,request:Request):
    try:
        wd=context(request,runid,config,True);data=await json_body(request)
        if set(data)-{'candidate_id','scale_mode','scale_factor','add_offset'}:invalid('Unexpected retry field.')
        selected=encoding(data)
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
            with rq_submission_lock(conn,f'{runid}:postfire-admission',lifecycle_key=runid):
                context(request,runid,config,True)
                state=p.reconcile_attempts(wd,p.state_at(wd),conn,persist=True);ensure_idle(state,'upload_attempt')
                identity=data.get('candidate_id');p.directory(wd,identity)
                previous=next((v for v in (state['active_dnbr'],state['upload_attempt']) if v and v['id']==identity),None)
                if previous is None:raise p.WorkflowError('missing_candidate','Upload is no longer available.',404)
                if previous is not state['active_dnbr'] and (datetime.now(timezone.utc)-datetime.fromisoformat(previous['created_at'])).total_seconds()>86400:
                    raise p.WorkflowError('expired_candidate','Upload expired. Choose the file again.',409)
                if not p.get_state(wd,config,reconcile=False)['upload_ready']:raise p.WorkflowError('missing_prerequisite','Delineate the watershed before uploading dNBR.',422)
                record,path=new_attempt(wd,'upload_attempt',p.sources(wd,rainfall=False)[4],filename=previous['filename'],source_id=previous['source_id'],source_sha256=previous['source_sha256'],encoding=selected)
                return enqueue(Queue(connection=conn),wd,runid,'upload_attempt',record)
    except (AuthError,p.WorkflowError,OSError,ValueError,RedisError,RqEnqueueVerificationError,RqSubmissionConflict,NoDbAlreadyLockedError) as exc:
        return boundary_error(exc)


@router.post(PREFIX+'/run', summary='Run the selected Staley model', operation_id=rq_operation_id('postfire_run'),
    tags=['rq-engine','runs'], responses=agent_route_responses(success_code=200, success_description='Job admitted.',
        extra={400:'Invalid model or rainfall request.',409:'Busy or changed project data.',413:'Request too large.',422:'Required project data unavailable.',503:'Service unavailable.'}))
@router.post(PREFIX+'/run-m1', summary='Run watershed M1 likelihood calculations',
    description='Requires Bearer rq:enqueue and authorized run access. See the production M1 contract.',
    tags=['rq-engine','runs'], operation_id=rq_operation_id('postfire_run_m1'),
    responses=agent_route_responses(success_code=200, success_description='Operation succeeded.',
        extra={400:'Invalid request.',404:'No accepted file or retained candidate.',409:'Busy or changed project data.',413:'Upload limit exceeded.',422:'Required project data unavailable.',503:'Service unavailable.'}))
async def run(runid:str,config:str,request:Request):
    try:
        wd=context(request,runid,config,True);data=await json_body(request)
        legacy = request.url.path.endswith('/run-m1')
        if set(data) - ({'frequency_source'} if legacy else {'model', 'frequency_source'}):invalid('Unexpected model option.')
        model = 'M1' if legacy else data.get('model')
        if model not in ('M1', 'M3'):invalid('Choose M1 or M3.')
        frequency=data.get('frequency_source','cli')
        if frequency not in ('cli','noaa'):invalid('Choose project climate or NOAA rainfall.')
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
            with rq_submission_lock(conn,f'{runid}:postfire-admission',lifecycle_key=runid):
                context(request,runid,config,True)
                state=p.reconcile_attempts(wd,p.state_at(wd),conn,persist=True)
                snapshot={'inputs':p.sources(wd,frequency=frequency,model=model)[4],'dnbr':state['active_dnbr']['id'] if model == 'M1' and state['active_dnbr'] else None,'frequency':frequency}
                attempt=state['run_attempt']
                if attempt and attempt['phase'] in p.ACTIVE:
                    if attempt.get('model', 'M1') == model and attempt['snapshot']==snapshot and attempt['job_id']:
                        return JSONResponse({'job_id':attempt['job_id'],'result':{'attempt_id':attempt['id']}})
                    raise p.WorkflowError('busy','A model run is already active.',409)
                if not p.get_state(wd,config,frequency=frequency,model=model,reconcile=False)['run_ready']:raise p.WorkflowError('missing_prerequisite','Prepare the required project data before running the model.',422)
                if model == 'M1' and not p.artifacts_current(wd,state['active_dnbr']):
                    raise p.WorkflowError('changed_source','Uploaded files changed. Upload the map again.',409)
                record,path=new_attempt(wd,'run_attempt',snapshot,model=model,frequency_source=frequency,job_key='postfire_m3_rq' if model == 'M3' else 'postfire_m1_rq')
                return enqueue(Queue(connection=conn),wd,runid,'run_attempt',record)
    except (AuthError,p.WorkflowError,OSError,ValueError,RedisError,RqEnqueueVerificationError,RqSubmissionConflict,NoDbAlreadyLockedError) as exc:
        return boundary_error(exc)

__all__=['router']


@router.get(PREFIX+'/files/{attempt_id}/{name}', summary='Download an accepted M1 file',
    description='Requires Bearer rq:export and authorized run access. See the production M1 contract.',
    tags=['rq-engine','runs'], operation_id=rq_operation_id('postfire_download'),
    responses=agent_route_responses(success_code=200, success_description='Operation succeeded.',
        extra={400:'Invalid request.',404:'No accepted file or retained candidate.',409:'Busy or changed project data.',413:'Upload limit exceeded.',422:'Required project data unavailable.',503:'Service unavailable.'}))
async def download(runid:str,config:str,attempt_id:str,name:str,request:Request):
    handle=None
    try:
        wd=context(request,runid,config,export=True)
        if name not in p.FILES:raise p.WorkflowError('missing_file','Model file not found.',404)
        root=p.directory(wd,attempt_id)
        accepted=p.state_at(wd)['last_successful_run']
        if not accepted or accepted['id']!=attempt_id:raise p.WorkflowError('missing_file','Model file not found.',404)
        path=p.safe(wd,root/'results'/name,exists=False)
        if not path.is_file():raise p.WorkflowError('changed_file','Model files changed. Run the model again.',409)
        expected=accepted['artifacts'].get(str(path.relative_to(Path(wd))))
        handle=path.open('rb');st=os.fstat(handle.fileno())
        actual=[str(path.relative_to(Path(wd))),st.st_size,st.st_mtime_ns,st.st_ctime_ns]
        if expected and len(expected)==5:
            checksum=hashlib.file_digest(handle, 'sha256').hexdigest()
            handle.seek(0)
            actual.append(checksum)
        if not stat.S_ISREG(st.st_mode) or expected!=actual:raise p.WorkflowError('changed_file','Model files changed. Run the model again.',409)
        return DownloadResponse(handle,media_type='application/octet-stream',headers={'Content-Disposition':f'attachment; filename="{name}"'})
    except (AuthError,p.WorkflowError,OSError,ValueError,RedisError) as exc:
        if handle is not None:handle.close()
        return boundary_error(exc)


@router.post(PREFIX+'/selection', summary='Save Staley model and rainfall selection',
             operation_id=rq_operation_id('postfire_selection'), tags=['rq-engine','runs'],
             responses=agent_route_responses(success_code=200, success_description='Selection saved.',
                 extra={400:'Invalid model or rainfall request.',409:'Busy or changed project data.',413:'Request too large.',422:'Ineligible project.',503:'Service unavailable.'}))
async def selection(runid: str, config: str, request: Request):
    try:
        wd = context(request, runid, config, True)
        data = await json_body(request)
        if set(data) != {'model', 'frequency_source'} or data['model'] not in ('M1', 'M3') or data['frequency_source'] not in ('cli', 'noaa'):
            invalid('Choose M1 or M3 and project climate or NOAA rainfall.')
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
            with rq_submission_lock(conn, f'{runid}:postfire-admission', lifecycle_key=runid):
                context(request, runid, config, True)
                if not p.sources(wd, rainfall=False)[0]:
                    raise p.WorkflowError('missing_prerequisite', 'Post-fire debris flow requires a WBT project in the continental US.', 422)
                p.mutable(wd).change(lambda state: state.update(model=data['model'], frequency_source=data['frequency_source']))
                return JSONResponse({'result': p.get_state(wd, config, reconcile=False)})
    except (AuthError, p.WorkflowError, OSError, ValueError, RedisError, RqSubmissionConflict, NoDbAlreadyLockedError) as exc:
        return boundary_error(exc)

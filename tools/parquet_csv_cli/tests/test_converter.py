"""Real binary, real subprocess and generated-content acceptance tests."""
import asyncio
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import signal
import struct
import subprocess
import sys
import time

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

TOOL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL))
from wepppy.microservices.parquet_csv import ConversionError, Converter as RuntimeConverter, Limits
from wepppy.microservices.parquet_csv.provenance import generate as runtime_generate, inventory as runtime_inventory, strict_json
from wepppy.microservices.parquet_csv.runner import _result

def Converter(*args, **kwargs):
    return RuntimeConverter(*args, source_root=TOOL, **kwargs)


def generate(binary, sidecar):
    return runtime_generate(binary, sidecar, TOOL)


def inventory(root=TOOL):
    return runtime_inventory(root)


SPEC = importlib.util.spec_from_file_location('csv_oracle', TOOL / 'oracle.py')
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


@pytest.fixture
def binary():
    path = TOOL / 'rust/target/release/parquet_csv_cli'
    assert path.is_file(), 'Build the exact release binary before tests'
    return path


@pytest.fixture
def converter(tmp_path, binary):
    sidecar = tmp_path / 'binary.json'
    generate(binary, sidecar)
    return Converter(binary, sidecar, tmp_path / 'scratch')


def write(tmp_path, table, **kwargs):
    path = tmp_path / 'source.parquet'
    pq.write_table(table, path, compression='snappy', **kwargs)
    return path


def oracle(path):
    f = pq.ParquetFile(path)
    buf = io.StringIO()
    writer = ORACLE.make_csv_writer(buf)
    wrote = False
    for batch in f.iter_batches(batch_size=65536):
        projected = ORACLE.project_table_for_output(pa.Table.from_batches([batch]), source_schema=f.schema_arrow, include_units=True)
        ORACLE.write_table_to_csv_writer(projected, writer, include_header=not wrote)
        wrote = True
    if not wrote:
        table = ORACLE.project_table_for_output(pa.Table.from_batches([], schema=f.schema_arrow), include_units=True)
        ORACLE.write_table_to_csv_writer(table, writer, include_header=True)
    return buf.getvalue().encode()


def convert(converter, path):
    return asyncio.run(converter.convert(path))


@pytest.mark.parametrize('kind', [pa.int8(),pa.int16(),pa.int32(),pa.int64(),pa.uint8(),pa.uint16(),pa.uint32(),pa.uint64(),pa.float32(),pa.float64(),pa.bool_(),pa.string(),pa.large_string()])
def test_all_supported_types(tmp_path, converter, kind):
    if pa.types.is_integer(kind):
        vals = [0,1,None, 2**(kind.bit_width-1)-1]
        if pa.types.is_signed_integer(kind):
            vals += [-2**(kind.bit_width-1)]
    elif pa.types.is_floating(kind):
        vals = [0.0,-0.0,None,float('nan'),float('inf'),float('-inf'),1e-5,1e16,1.234567890123]
    elif pa.types.is_boolean(kind):
        vals = [True,False,None]
    else:
        vals = ['',None,'x,y','x"y','x\ny','x\ry','é🌲','\r\n']
    path = write(tmp_path, pa.table({'value':pa.array(vals, type=kind)}))
    with convert(converter,path) as artifact:
        assert artifact.path.read_bytes() == oracle(path)
        assert artifact.rows == len(vals)
        assert artifact.peak_rss_kib > 0
        assert artifact.cpu_seconds >= 0
    assert not list(converter.root.glob('slot-[01]'))


def test_random_float_byte_parity(tmp_path, converter):
    rng = random.Random(718)
    values = [struct.unpack('<d', rng.randbytes(8))[0] for _ in range(20000)]
    values += [10.0**i for i in range(-300,301)]
    path = write(tmp_path,pa.table({'v':pa.array(values, type=pa.float64())}),use_dictionary=False)
    with convert(converter,path) as artifact:
        assert artifact.path.read_bytes() == oracle(path)


@pytest.mark.parametrize('empty',[False,True])
def test_units_indices_and_empty(tmp_path,converter,empty):
    schema=pa.schema([pa.field('x',pa.float64(),metadata={b'units':b' mm '}),pa.field('idx',pa.int64()),pa.field('y (m)',pa.int64(),metadata={b'units':b'm'})],metadata={b'pandas':json.dumps({'index_columns':['idx']}).encode()})
    path=write(tmp_path,pa.Table.from_arrays([pa.array([] if empty else [1.5],type=f.type) for f in schema],schema=schema))
    with convert(converter,path) as artifact:
        assert artifact.path.read_bytes()==oracle(path)


@pytest.mark.parametrize('metadata',[None,{b'pandas':b'not json'},{b'pandas':b'{"index_columns":[]}'},{b'pandas':b'{"index_columns":[{"name":"idx"}]}'}])
def test_metadata(tmp_path,converter,metadata):
    t=pa.table({'v':[1], 'idx':[2]}).replace_schema_metadata(metadata)
    path=write(tmp_path,t)
    with convert(converter,path) as artifact:
        assert artifact.path.read_bytes()==oracle(path)


@pytest.mark.parametrize('kind',[pa.date32(),pa.decimal128(10,2),pa.list_(pa.int64())])
def test_unsupported_types(tmp_path,converter,kind):
    path=write(tmp_path,pa.table({'v':pa.array([None],type=kind)}))
    with pytest.raises(ConversionError,match='input_rejected'):
        convert(converter,path)
    assert not list(converter.root.glob('slot-[01]'))


def test_duplicate_projected_labels_preserved(tmp_path,converter):
    schema=pa.schema([pa.field('x',pa.int64(),metadata={b'units':b'm'}),pa.field('x (m)',pa.int64())])
    path=write(tmp_path,pa.Table.from_arrays([pa.array([1]),pa.array([2])],schema=schema))
    assert oracle(path)==b'x (m),x (m)\n2,2\n'
    with convert(converter,path) as artifact:
        assert artifact.path.read_bytes()==oracle(path)


@pytest.mark.parametrize('corrupt',['magic','footer','arrow','gzip','nested'])
def test_malformed_or_excluded(tmp_path,converter,corrupt):
    path=write(tmp_path,pa.table({'x':[1,2,3]}))
    if corrupt=='magic':path.write_bytes(b'not-parquet-file')
    elif corrupt=='footer':
        b=bytearray(path.read_bytes());b[-8:-4]=(2**31).to_bytes(4,'little');path.write_bytes(b)
    elif corrupt=='arrow':
        raw=pq.ParquetFile(path).metadata.metadata[b'ARROW:schema']
        path.write_bytes(path.read_bytes().replace(raw,b'!'*len(raw)))
    elif corrupt=='gzip':pq.write_table(pa.table({'x':[1]}),path,compression='gzip')
    else:pq.write_table(pa.table({'x':[[1,2]]}),path)
    with pytest.raises(ConversionError):convert(converter,path)


def test_missing_symlink_and_nonregular(tmp_path,converter):
    real=write(tmp_path,pa.table({'v':[1]}));link=tmp_path/'link';link.symlink_to(real)
    fifo=tmp_path/'fifo';os.mkfifo(fifo)
    for source in [tmp_path/'missing',link,fifo,tmp_path]:
        with pytest.raises(ConversionError,match='source_rejected'):convert(converter,source)
    assert not list(converter.root.glob('slot-[01]'))


def test_limits_and_output_cleanup(tmp_path,converter):
    path=write(tmp_path,pa.table({'value':['x'*1000]*100}))
    c=Converter(converter.binary,converter.provenance,converter.root,Limits(output_bytes=100))
    with pytest.raises(ConversionError,match='resource_limit|child_failed'):convert(c,path)
    assert not list(c.root.glob('slot-[01]'))
    c=Converter(converter.binary,converter.provenance,converter.root,Limits(memory_bytes=32*1024*1024))
    with pytest.raises(ConversionError):convert(c,path)
    assert not list(c.root.glob('slot-[01]'))


def test_provenance_failure(tmp_path,converter):
    path=write(tmp_path,pa.table({'v':[1]}))
    v=json.loads(converter.provenance.read_text());v['binary_sha256']='0'*64;converter.provenance.write_text(json.dumps(v))
    with pytest.raises(ConversionError,match='provenance_invalid'):convert(converter,path)
    assert not list(converter.root.glob("slot-[01]"))


def fake(tmp_path,script,limits=Limits()):
    binary=tmp_path/'fake';binary.write_text(f'#!{sys.executable}\n'+script);binary.chmod(0o700)
    sidecar=tmp_path/'fake.json';generate(binary,sidecar)
    return Converter(binary,sidecar,tmp_path/'scratch',limits)


@pytest.mark.parametrize('script,code',[("print('not json')",'protocol_error'),("print('x'*5000)",'diagnostic_overflow'),("import time;time.sleep(30)",'timeout')])
def test_actual_child_failures(tmp_path,script,code):
    c=fake(tmp_path,script,Limits(wall_seconds=.2));path=write(tmp_path,pa.table({'v':[1]}))
    with pytest.raises(ConversionError,match=code):convert(c,path)
    assert not list(c.root.glob('slot-[01]'))


def test_repeated_cancellation_kills_group(tmp_path):
    marker=tmp_path/'pids'
    script=f'''import os,subprocess,time
child=subprocess.Popen([{sys.executable!r},'-c','import time;time.sleep(60)'])
open({str(marker)!r},'w').write(str(os.getpid())+' '+str(child.pid))
time.sleep(60)
'''
    c=fake(tmp_path,script);path=write(tmp_path,pa.table({'v':[1]}))
    async def exercise():
        task=asyncio.create_task(c.convert(path))
        for _ in range(200):
            if marker.exists():break
            await asyncio.sleep(.01)
        assert marker.exists()
        task.cancel();await asyncio.sleep(0);task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(exercise())
    for pid in map(int,marker.read_text().split()):
        status=Path(f'/proc/{pid}/stat')
        assert not status.exists() or status.read_text().split()[2]=='Z'
    assert not list(c.root.glob('slot-[01]'))


def test_artifact_lifetime_admission_and_cross_process(tmp_path,converter):
    path=write(tmp_path,pa.table({'v':[1]}))
    a=convert(converter,path);b=convert(converter,path)
    try:
        code=f'''import asyncio,sys
sys.path.insert(0,{str(TOOL)!r})
from wepppy.microservices.parquet_csv import Converter,ConversionError
from pathlib import Path
try: asyncio.run(Converter(Path({str(converter.binary)!r}),Path({str(converter.provenance)!r}),Path({str(converter.root)!r}), source_root=Path({str(TOOL)!r})).convert(Path({str(path)!r})))
except ConversionError as e: print(e.code)
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=True)
        assert result.stdout.strip()=='busy'
    finally:a.cleanup();b.cleanup()
    with convert(converter,path):pass


def test_strict_protocol_rejects_invalid_metrics(tmp_path):
    path=tmp_path/'output.csv';path.write_bytes(b'x\n');path.chmod(0o600)
    value={'version':2,'status':'ok','rows':0,'bytes':2,'input_sha256':'0'*64,'peak_rss_kib':1,'cpu_seconds':0.0}
    for key,bad in [('peak_rss_kib',True),('cpu_seconds',True),('cpu_seconds',float('nan')),('cpu_seconds',-1),('rows',True)]:
        mutated=value|{key:bad}
        with pytest.raises(ConversionError,match='protocol_error'):_result(json.dumps(mutated).encode(),b'',0,path,'0'*64,Limits())
    with pytest.raises(ValueError):strict_json('{"a":1,"a":2}')


def test_cli_output_collision_preserves_file(tmp_path,binary):
    root=tmp_path/'request';root.mkdir(mode=0o700)
    pq.write_table(pa.table({'v':[1]}),root/'input.parquet')
    output=root/'output.csv';output.write_bytes(b'preserve')
    request=root/'request.json';request.write_text('{"version":2,"filter":null}');request.chmod(0o600)
    with (tmp_path/'lease').open('w') as lease:
        p=subprocess.run([str(binary),'--request-root',str(root),'--max-memory-bytes',str(1024**3),'--max-cpu-seconds','120','--max-output-bytes',str(2*1024**3), '--max-wall-seconds','120','--parent-pid',str(os.getpid()),'--admission-fd',str(lease.fileno())],capture_output=True,pass_fds=(lease.fileno(),))
    assert p.returncode==5
    assert output.read_bytes()==b'preserve'


@pytest.mark.parametrize('codec',['snappy','gzip'])
def test_empty_codec_validation(tmp_path,converter,codec):
    path=tmp_path/'empty.parquet';pq.write_table(pa.table({'v':pa.array([],type=pa.int64())}),path,compression=codec)
    if codec=='snappy':
        with convert(converter,path) as a:assert a.path.read_bytes()==oracle(path)
    else:
        with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)


def test_mixed_empty_groups_and_all_null_column(tmp_path,converter):
    path=tmp_path/'mixed.parquet';schema=pa.schema([('v',pa.int64()),('nulls',pa.float64())])
    with pq.ParquetWriter(path,schema) as writer:
        writer.write_table(pa.Table.from_arrays([pa.array([],type=f.type) for f in schema],schema=schema))
        writer.write_table(pa.table({'v':[1,2],'nulls':pa.array([None,None],type=pa.float64())}))
    with convert(converter,path) as a:assert a.path.read_bytes()==oracle(path)


@pytest.mark.parametrize('metadata',[{b'pandas':b'\xff'},{b'pandas':b'[]'},{b'pandas':b'{"index_columns":null}'}])
def test_excluded_metadata(tmp_path,converter,metadata):
    path=write(tmp_path,pa.table({'v':[1]}).replace_schema_metadata(metadata))
    with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)


def test_units_python_whitespace(tmp_path,converter):
    schema=pa.schema([pa.field('v',pa.int64(),metadata={b'units':b'\x1cmm\x1c'})])
    path=write(tmp_path,pa.Table.from_arrays([pa.array([1])],schema=schema))
    with convert(converter,path) as a:assert a.path.read_bytes()==oracle(path)


def test_non_utf8_units_rejected(tmp_path,converter):
    schema=pa.schema([pa.field('v',pa.int64(),metadata={b'units':b'm\xffm'})])
    path=write(tmp_path,pa.Table.from_arrays([pa.array([1])],schema=schema))
    with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)


@pytest.mark.parametrize('kind',['fifo','directory','oversize','duplicate'])
def test_provenance_paths_are_bounded(tmp_path,converter,kind):
    source=write(tmp_path,pa.table({'v':[1]}));converter.provenance.unlink()
    if kind=='fifo':os.mkfifo(converter.provenance)
    elif kind=='directory':converter.provenance.mkdir()
    elif kind=='oversize':converter.provenance.write_bytes(b' '*65537)
    else:converter.provenance.write_bytes(b'{"version":1,"version":1}')
    started=time.monotonic()
    with pytest.raises(ConversionError,match='provenance_invalid'):convert(converter,source)
    assert time.monotonic()-started<2


def test_root_file_and_missing_success_output_are_typed(tmp_path,converter):
    path=write(tmp_path,pa.table({'v':[1]}));converter.root.write_text('occupied')
    with pytest.raises(ConversionError,match='io_error'):convert(converter,path)
    converter.root.unlink()
    code=f'''import hashlib,json,pathlib,sys
root=pathlib.Path(sys.argv[sys.argv.index('--request-root')+1])
h=hashlib.sha256((root/'input.parquet').read_bytes()).hexdigest()
print(json.dumps(dict(version=2,status='ok',rows=1,bytes=2,input_sha256=h,peak_rss_kib=100,cpu_seconds=0.0)))
'''
    c=fake(tmp_path,code)
    with pytest.raises(ConversionError,match='output_invalid'):convert(c,path)
    assert not list(c.root.glob('slot-[01]'))


def test_spawn_cancellation_drains_owned_process(tmp_path,monkeypatch):
    marker=tmp_path/'pid';c=fake(tmp_path,f'import os,time\nopen({str(marker)!r},"w").write(str(os.getpid()))\ntime.sleep(30)')
    path=write(tmp_path,pa.table({'v':[1]}));real=asyncio.create_subprocess_exec
    async def exercise():
        spawned=asyncio.Event();release=asyncio.Event()
        async def delayed(*args,**kwargs):
            process=await real(*args,**kwargs);spawned.set();await release.wait();return process
        monkeypatch.setattr(asyncio,'create_subprocess_exec',delayed)
        task=asyncio.create_task(c.convert(path));await spawned.wait();task.cancel();await asyncio.sleep(.02)
        assert not task.done();release.set()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(exercise());assert not list(c.root.glob('slot-[01]'))


def test_staging_cancellation_and_mutation(tmp_path,converter,monkeypatch):
    import wepppy.microservices.parquet_csv.runner as runner
    path=write(tmp_path,pa.table({'v':range(10000)}));real_sleep=asyncio.sleep
    mutated = False
    async def mutate(delay):
        nonlocal mutated
        if not mutated:
            with path.open('ab') as stream:stream.write(b'x')
            mutated = True
        await real_sleep(delay)
    monkeypatch.setattr(runner.asyncio,'sleep',mutate)
    with pytest.raises(ConversionError,match='source_changed'):convert(converter,path)
    assert not list(converter.root.glob('slot-[01]'))
    async def cancel(_):raise asyncio.CancelledError()
    monkeypatch.setattr(runner.asyncio,'sleep',cancel)
    with pytest.raises(asyncio.CancelledError):convert(converter,path)
    assert not list(converter.root.glob('slot-[01]'))


def test_cleanup_failure_retains_capacity(tmp_path,converter,monkeypatch):
    import wepppy.microservices.parquet_csv.runner as runner
    path=write(tmp_path,pa.table({'v':[1]}));artifact=convert(converter,path);real=runner.shutil.rmtree
    def fail(_):raise PermissionError('injected cleanup boundary failure')
    monkeypatch.setattr(runner.shutil,'rmtree',fail)
    with pytest.raises(ConversionError,match='cleanup_failed'):artifact.cleanup()
    assert artifact._slot is not None
    monkeypatch.setattr(runner.shutil,'rmtree',real);artifact.cleanup()


def test_cpu_signal_and_descendant_drain(tmp_path):
    c=fake(tmp_path,'import resource\nresource.setrlimit(resource.RLIMIT_CPU,(1,1))\nwhile True: pass',Limits(wall_seconds=5))
    path=write(tmp_path,pa.table({'v':[1]}))
    with pytest.raises(ConversionError,match='child_failed'):convert(c,path)
    assert not list(c.root.glob('slot-[01]'))


@pytest.mark.parametrize('kind',[pa.date32()])
@pytest.mark.parametrize('index_name',['__index_level_0__','metadata_index'])
def test_omitted_columns_are_still_untrusted(tmp_path,converter,kind,index_name):
    t=pa.table({'value':[1],index_name:pa.array([None],type=kind)})
    if index_name=='metadata_index':t=t.replace_schema_metadata({b'pandas':b'{"index_columns":["metadata_index"]}'})
    path=write(tmp_path,t)
    with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)


def test_omitted_extension_column_is_rejected(tmp_path,converter):
    schema=pa.schema([pa.field('v',pa.int64()),pa.field('__index_level_0__',pa.int64(),metadata={b'ARROW:extension:name':b'untrusted'})])
    path=write(tmp_path,pa.Table.from_arrays([pa.array([1]),pa.array([2])],schema=schema))
    with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)


def test_oversized_metric_and_limit_integers(tmp_path):
    path=tmp_path/'out';path.write_bytes(b'x\n');path.chmod(0o600)
    value={'version':2,'status':'ok','rows':0,'bytes':2,'input_sha256':'0'*64,'peak_rss_kib':1,'cpu_seconds':10**400}
    with pytest.raises(ConversionError,match='protocol_error'):_result(json.dumps(value).encode(),b'',0,path,'0'*64,Limits())
    for field in ['wall_seconds','staging_seconds']:
        with pytest.raises(ValueError):Limits(**{field:10**400})


def test_private_request_creation_failure_is_typed(tmp_path,converter):
    path=write(tmp_path,pa.table({'v':[1]}))
    with convert(converter,path):pass
    converter.root.chmod(0o500)
    try:
        with pytest.raises(ConversionError,match='io_error'):convert(converter,path)
    finally:converter.root.chmod(0o700)
    with convert(converter,path):pass


def test_output_limit_exact_and_one_less(tmp_path,converter):
    path=write(tmp_path,pa.table({'v':[1,2,3]}));size=len(oracle(path))
    for limit in [size,size-1]:
        c=Converter(converter.binary,converter.provenance,converter.root,Limits(output_bytes=limit))
        if limit==size:
            with convert(c,path) as a:assert a.bytes==size
        else:
            with pytest.raises(ConversionError,match='resource_limit'):convert(c,path)
    assert not list(converter.root.glob('slot-[01]'))


@pytest.mark.parametrize('label',[False,True])
@pytest.mark.parametrize('mutation',['page_expansion','dictionary_count','snappy_length','arrow_vector'])
def test_generated_label_never_bypasses_validation(tmp_path,converter,label,mutation):
    # Mutate the actual compact header of a known-valid small dictionary page.
    t=pa.table({'v':[1,2,3]})
    if label:t=t.replace_schema_metadata({b'created_by':b'WEPPpy trusted generated interchange'})
    path=write(tmp_path,t);f=pq.ParquetFile(path);raw=bytearray(path.read_bytes())
    def vint(number):
        result=bytearray()
        while number>=128:result.append((number&127)|128);number>>=7
        result.append(number);return result
    start=f.metadata.row_group(0).column(0).dictionary_page_offset
    if mutation=='page_expansion':
        # Field1=type (i32), field2=uncompressed_page_size (i32); one-byte
        # values in this tiny fixture. Replace field2's zigzag integer.
        assert raw[start]==0x15 and raw[start+2]==0x15
        raw[start+3:start+4]=vint((8*1024*1024+1)*2)
    elif mutation=='dictionary_count':
        marker=raw.index(bytes([0x4c,0x15]),start)
        raw[marker+2:marker+3]=vint(100001*2)
    elif mutation=='snappy_length':
        # Compact PageHeader ends with nested/root STOP bytes; alter the first
        # Snappy body varint without changing the enclosing page sizes.
        end=raw.index(b'\x00\x00',start)+2
        raw[end]=0x7f
    else:
        import base64
        encoded=f.metadata.metadata[b'ARROW:schema'];blob=bytearray(base64.b64decode(encoded))
        blob[8:12]=b'\xff'*4
        replacement=base64.b64encode(blob)
        assert len(replacement)==len(encoded)
        raw=raw.replace(encoded,replacement)
    path.write_bytes(raw)
    with pytest.raises(ConversionError):convert(converter,path)
    assert not list(converter.root.glob('slot-[01]'))


@pytest.mark.parametrize('empty',[False,True])
def test_external_column_reference_is_never_opened(tmp_path,converter,empty):
    import ctypes
    canary=tmp_path/'external.parquet';canary.write_bytes(b'do not open')
    path=write(tmp_path,pa.table({'v':pa.array([] if empty else [1,2],type=pa.int64())}))
    raw=path.read_bytes();length=int.from_bytes(raw[-8:-4],'little')
    metadata=pq.read_metadata(path);metadata.set_file_path(str(canary))
    buffer=io.BytesIO();metadata.write_metadata_file(buffer);replacement=buffer.getvalue()
    new_length=int.from_bytes(replacement[-8:-4],'little')
    path.write_bytes(raw[:-8-length]+replacement[-8-new_length:])
    libc=ctypes.CDLL(None,use_errno=True);fd=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
    assert fd>=0
    try:
        assert libc.inotify_add_watch(fd,os.fsencode(canary),0x20)>=0  # IN_OPEN
        with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)
        with pytest.raises(BlockingIOError):os.read(fd,4096)
    finally:os.close(fd)
    assert canary.read_bytes()==b'do not open'


@pytest.mark.parametrize('mutation',['negative','outside','overlap','near_alias'])
def test_untrusted_offsets_are_rejected(tmp_path,converter,mutation):
    path=write(tmp_path,pa.table({'a':[1,2,3],'b':[4,5,6]}))
    metadata=pq.read_metadata(path);first=metadata.row_group(0).column(0);second=metadata.row_group(0).column(1)
    raw=path.read_bytes();length=int.from_bytes(raw[-8:-4],'little');footer=bytearray(raw[-8-length:-8])
    def vint(value):
        n=((value<<1)^(value>>63))&((1<<64)-1);result=bytearray()
        while n>=128:result.append((n&127)|128);n>>=7
        result.append(n);return result
    def replace(old,new):
        nonlocal footer
        pattern=b'\x26'+vint(old)
        assert footer.count(pattern)==1
        footer=footer.replace(pattern,b'\x26'+vint(new))
    if mutation=='negative':replace(first.data_page_offset,-1)
    elif mutation=='outside':replace(first.data_page_offset,len(raw)+1)
    elif mutation=='near_alias':replace(first.data_page_offset,first.dictionary_page_offset+1)
    else:
        replace(second.data_page_offset,first.data_page_offset)
        replace(second.dictionary_page_offset,first.dictionary_page_offset)
    path.write_bytes(raw[:-8-length]+footer+len(footer).to_bytes(4,'little')+b'PAR1')
    with pytest.raises(ConversionError,match='input_rejected'):convert(converter,path)


def test_integer_and_float_extremes(tmp_path,converter):
    path=write(tmp_path,pa.table({'u':pa.array([2**64-1,0,2**63],type=pa.uint64()),'f':pa.array([5e-324,1.7976931348623157e308,-5e-324],type=pa.float64())}))
    with convert(converter,path) as a:assert a.path.read_bytes()==oracle(path)


def test_sparse_oversized_source_rejected_before_copy(tmp_path,converter):
    source=tmp_path/'too-large.parquet'
    with source.open('wb') as f:f.truncate(512*1024*1024+1)
    with pytest.raises(ConversionError,match='input_too_large'):convert(converter,source)
    assert not list(converter.root.glob('slot-[01]'))


def test_proc_stat_disappears_between_open_and_read(monkeypatch):
    import subprocess
    from wepppy.microservices.parquet_csv.runner import _group_alive
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], start_new_session=True)
    stat_path = Path(f'/proc/{child.pid}/stat')
    original = Path.read_text
    observed = []
    try:
        assert _group_alive(child.pid)
        def read_after_exit(path, *args, **kwargs):
            if path == stat_path:
                with path.open() as stream:
                    child.terminate()
                    child.wait(timeout=5)
                    try:
                        return stream.read()
                    except ProcessLookupError:
                        observed.append('ESRCH')
                        raise
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, 'read_text', read_after_exit)
        assert not _group_alive(child.pid)
        assert observed == ['ESRCH']
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def test_proc_observation_error_fails_closed(monkeypatch):
    from wepppy.microservices.parquet_csv.runner import _group_alive
    original = Path.iterdir
    def denied(path):
        if path == Path('/proc'):
            raise PermissionError('injected proc enumeration denial')
        return original(path)
    monkeypatch.setattr(Path, 'iterdir', denied)
    with pytest.raises(ConversionError) as error:
        _group_alive(os.getpid())
    assert error.value.code == 'cleanup_failed'


@pytest.mark.parametrize('payload', [
    b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}',
    b'{"a":1} {"b":2}', b'\xef\xbb\xbf{"a":1}',
    '{"a":1}'.encode('utf-16'), '{"a":1}'.encode('utf-32'),
    b'[' * 30000 + b'0' + b']' * 30000,
])
def test_strict_json_wire_rejections(payload):
    with pytest.raises(ValueError):
        strict_json(payload)


def test_deep_provenance_rejects_with_typed_error(tmp_path, binary):
    side = tmp_path / 'deep.json'
    side.write_bytes(b'[' * 30000 + b'0' + b']' * 30000)
    c = Converter(binary, side, tmp_path / 'scratch')
    path = write(tmp_path, pa.table({'v': [1]}))
    with pytest.raises(ConversionError, match='provenance_invalid'):
        convert(c, path)


def test_actual_child_utf16_json_is_protocol_error(tmp_path):
    c = fake(tmp_path, "import sys; sys.stderr.buffer.write('{\"version\":1,\"status\":\"error\",\"code\":\"input_rejected\"}'.encode('utf-16')); sys.exit(3)")
    path = write(tmp_path, pa.table({'v': [1]}))
    with pytest.raises(ConversionError, match='protocol_error'):
        convert(c, path)
    assert not list(c.root.glob('slot-[01]'))


@pytest.mark.parametrize('kind,values', [
    (pa.null(), [None, None, None]),
    (pa.binary(), [b"'quote\"\x00\n\xff", b'plain', None]),
    (pa.timestamp('ns'), [-1, 1000, 123456789]),
    (pa.timestamp('us'), [-1, 1000, 123456789]),
])
@pytest.mark.parametrize('codec', ['snappy', 'zstd'])
def test_integration_types_and_codecs(tmp_path, converter, kind, values, codec):
    path = tmp_path / 'extended.parquet'
    pq.write_table(pa.table({'value': pa.array(values, type=kind)}), path, compression=codec)
    with convert(converter, path) as artifact:
        assert artifact.path.read_bytes() == oracle(path)


def test_wkb_annotation_and_all_index_projection(tmp_path, converter):
    schema = pa.schema([pa.field('geometry', pa.binary(), metadata={b'ARROW:extension:name': b'geoarrow.wkb'})])
    path = write(tmp_path, pa.Table.from_arrays([pa.array([b'\x01\x00'])], schema=schema))
    with convert(converter, path) as artifact:
        assert artifact.path.read_bytes() == oracle(path)
    path = write(tmp_path, pa.table({'__index_level_0__': [1, 2]}))
    with convert(converter, path) as artifact:
        assert artifact.path.read_bytes() == oracle(path) == b'\n'
        assert artifact.rows == 0


def condition(field, operator, value):
    try:
        number = float(value)
        if not __import__('math').isfinite(number):
            number = None
    except ValueError:
        number = None
    return {'kind': 'condition', 'field': field, 'operator': operator, 'value': value, 'number': number}


@pytest.mark.parametrize('field,operator,value', [
    ('i', 'Equals', '9007199254740992'), ('i', 'GreaterThan', '１２'),
    ('i', 'LessThan', '1_000'), ('f', 'Contains', 'nan'),
    ('f', 'GreaterThan', '1'), ('f', 'NotEquals', '1'),
    ('f32', 'Contains', '0.1'), ('b', 'Equals', 'true'),
    ('b', 'Contains', 'TR'), ('text', 'Contains', 'i'),
    ('text', 'Contains', 'οσ'), ('__index_level_0__', 'Equals', '2'),
])
def test_filter_matches_duckdb_oracle(tmp_path, converter, field, operator, value):
    from wepppy.microservices.parquet_filters import compile_filter, query_export
    table = pa.table({'i': [9007199254740993, 12, 999, None],
                      'f': [float('nan'), float('inf'), -float('inf'), None],
                      'f32': pa.array([.1, 1e-6, 1e16, None], type=pa.float32()),
                      'b': [True, False, True, None], 'text': ['İ', 'ΟΣ', 'ok', None],
                      '__index_level_0__': [1, 2, 3, 4]})
    path = write(tmp_path, table)
    node = condition(field, operator, value)
    compiled = compile_filter({k: v for k, v in node.items() if k != 'number'}, table.schema)
    expected = ORACLE.project_table_for_output(query_export(path, compiled, max_rows=2_000_000),
                                               source_schema=table.schema, include_units=True)
    with asyncio.run(converter.convert(path, node)) as artifact:
        assert artifact.path.read_bytes() == ORACLE.table_to_csv_bytes(expected)


@pytest.mark.parametrize('names', [['x', 'x'], ['x', 'x', 'x_1'], ['x', 'x_1', 'x']])
def test_filtered_physical_duplicates(tmp_path, converter, names):
    from wepppy.microservices.parquet_filters import compile_filter, query_export
    table = pa.Table.from_arrays([pa.array([i+1, i+2]) for i in range(len(names))], names=names)
    path = write(tmp_path, table)
    node = condition('x', 'GreaterThan', '0')
    compiled = compile_filter({k: v for k, v in node.items() if k != 'number'}, table.schema)
    expected = ORACLE.project_table_for_output(query_export(path, compiled, max_rows=2_000_000),
                                               source_schema=table.schema, include_units=True)
    with asyncio.run(converter.convert(path, node)) as artifact:
        assert artifact.path.read_bytes() == ORACLE.table_to_csv_bytes(expected)


def test_filter_errors_and_empty_schema(tmp_path, converter):
    path = write(tmp_path, pa.table({'v': pa.array([], type=pa.int64())}))
    for node, code in [(condition('missing', 'Equals', '1'), 'validation_error'),
                       (condition('v', 'Equals', 'nan'), 'validation_error'),
                       (condition('v', 'Equals', '1'), 'no_rows_matched_filter')]:
        with pytest.raises(ConversionError, match=code):
            asyncio.run(converter.convert(path, node))


def test_inherited_high_descriptor_and_stale_recovery(tmp_path, converter):
    import fcntl
    path = write(tmp_path, pa.table({'v': [1]}))
    descriptors = []
    try:
        while not descriptors or descriptors[-1] < 100:
            descriptors.append(os.open('/dev/null', os.O_RDONLY))
        with convert(converter, path) as artifact:
            assert artifact._slot > 63
            assert artifact.path.read_bytes() == oracle(path)
        stale = converter.root / 'slot-0'
        stale.mkdir(mode=0o700)
        (stale / 'output.csv').write_bytes(b'never reuse stale bytes')
        with convert(converter, path) as artifact:
            assert artifact.path.read_bytes() == oracle(path)
    finally:
        for fd in descriptors:
            os.close(fd)


@pytest.mark.parametrize('unit', ['ms', 'us'])
def test_hostile_timestamp_range_has_strict_error(tmp_path, converter, unit):
    path = write(tmp_path, pa.table({'time': pa.array([2**63-1], type=pa.timestamp(unit))}))
    with pytest.raises(ConversionError, match='input_rejected'):
        convert(converter, path)


def test_owned_io_preserves_cancellation_after_late_failure():
    import threading
    from wepppy.microservices.parquet_csv.runner import _owned_thread
    entered = threading.Event()
    release = threading.Event()
    def blocked():
        entered.set()
        release.wait()
        raise OSError('late I/O failure')
    async def exercise():
        task = asyncio.create_task(_owned_thread(blocked))
        while not entered.is_set():
            await asyncio.sleep(.001)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(exercise())


def test_parent_sigkill_preserves_child_lease_and_recovers(tmp_path, converter):
    import fcntl
    path = write(tmp_path, pa.table({'v': ['x' * 1000] * 100_000}))
    marker = tmp_path / 'child.pid'
    script = f'''import asyncio,os,signal
from pathlib import Path
from wepppy.microservices.parquet_csv import Converter
real=asyncio.create_subprocess_exec
async def stopped(*args,**kwargs):
    child=await real(*args,**kwargs)
    os.kill(child.pid,signal.SIGSTOP)
    Path({str(marker)!r}).write_text(str(child.pid))
    await asyncio.Event().wait()
asyncio.create_subprocess_exec=stopped
c=Converter(Path({str(converter.binary)!r}),Path({str(converter.provenance)!r}),Path({str(converter.root)!r}),source_root=Path({str(TOOL)!r}))
asyncio.run(c.convert(Path({str(path)!r})))
'''
    parent = subprocess.Popen([sys.executable, '-c', script])
    child_pid = None
    try:
        for _ in range(500):
            if marker.exists():
                break
            assert parent.poll() is None
            time.sleep(.01)
        assert marker.exists()
        child_pid = int(marker.read_text())
        parent.kill()
        parent.wait(timeout=5)
        status = Path(f'/proc/{child_pid}/stat')
        with (converter.root / 'slot-0.lock').open('r+') as lease:
            if status.exists() and status.read_text().rpartition(') ')[2].split()[0] not in ('Z', 'X'):
                with pytest.raises(BlockingIOError):
                    fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                os.kill(child_pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
            for _ in range(500):
                try:
                    fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(.01)
            else:
                pytest.fail('Child did not release inherited admission after parent death')
        # A new holder removes abandoned state before producing fresh output.
        small = write(tmp_path, pa.table({'v': [42]}))
        with convert(converter, small) as artifact:
            assert artifact.path.read_bytes() == b'v\n42\n'
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait()
        if child_pid is not None:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_rejected_scratch_is_not_deleted(tmp_path, converter):
    converter.root.mkdir(mode=0o700)
    invalid = converter.root / 'slot-0'
    invalid.mkdir(mode=0o755)
    canary = invalid / 'canary'
    canary.write_bytes(b'preserve')
    source = write(tmp_path, pa.table({'v': [1]}))
    with pytest.raises(ConversionError, match='cleanup_failed'):
        convert(converter, source)
    assert canary.read_bytes() == b'preserve'


@pytest.mark.parametrize('values', [[True, False], [' 2 ', '3'], ['1_000', '1__2']])
def test_filtered_mixed_type_duplicates_match_duckdb(tmp_path, converter, values):
    from wepppy.microservices.parquet_filters import compile_filter, query_export
    table = pa.Table.from_arrays([pa.array(values), pa.array([1, 2])], names=['x', 'x'])
    path = write(tmp_path, table)
    node = condition('x', 'GreaterThan', '0')
    compiled = compile_filter({k: v for k, v in node.items() if k != 'number'}, table.schema)
    expected = ORACLE.project_table_for_output(query_export(path, compiled, max_rows=2_000_000),
                                               source_schema=table.schema, include_units=True)
    with asyncio.run(converter.convert(path, node)) as artifact:
        assert artifact.path.read_bytes() == ORACLE.table_to_csv_bytes(expected)


def test_scratch_io_error_is_not_input_rejection(tmp_path):
    from wepppy.microservices.parquet_csv.runner import _stage
    source = write(tmp_path, pa.table({'v': [1]}))
    destination = tmp_path / 'directory'
    destination.mkdir()
    with pytest.raises(ConversionError, match='io_error'):
        asyncio.run(_stage(source, destination, time.monotonic() + 30))


def test_nanosecond_nat_sentinel_matches_csv_oracle(tmp_path, converter):
    path = write(tmp_path, pa.table({'time': pa.array([-2**63, -1, 0, 1], type=pa.timestamp('ns'))}))
    with convert(converter, path) as artifact:
        assert artifact.path.read_bytes() == oracle(path)
        assert b'NaT\n' in artifact.path.read_bytes()


@pytest.mark.parametrize('upper,lower', [('\u1c89', '\u1c8a'), ('\ua7cb', '\u0264')])
def test_filter_uses_pinned_unicode_mapping(tmp_path, converter, upper, lower):
    import duckdb
    assert duckdb.connect().execute('select lower(?)', [upper]).fetchone()[0] == upper
    path = write(tmp_path, pa.table({'x': [upper]}))
    with pytest.raises(ConversionError, match='no_rows_matched_filter'):
        asyncio.run(converter.convert(path, condition('x', 'Contains', lower)))


@pytest.mark.parametrize('names', [['', 'x'], ['', 'C0', 'x'], ['C1', '', 'x']])
def test_filtered_empty_physical_names(tmp_path, converter, names):
    from wepppy.microservices.parquet_filters import compile_filter, query_export
    table = pa.Table.from_arrays([pa.array([i+1]) for i in range(len(names))], names=names)
    path = write(tmp_path, table)
    node = condition('x', 'GreaterThan', '0')
    compiled = compile_filter({k: v for k, v in node.items() if k != 'number'}, table.schema)
    if len(names) > 2:
        import duckdb
        with pytest.raises(duckdb.BinderException):
            query_export(path, compiled, max_rows=2_000_000)
        with pytest.raises(ConversionError, match='input_rejected'):
            asyncio.run(converter.convert(path, node))
    else:
        expected = ORACLE.project_table_for_output(query_export(path, compiled, max_rows=2_000_000),
                                                   source_schema=table.schema, include_units=True)
        with asyncio.run(converter.convert(path, node)) as artifact:
            assert artifact.path.read_bytes() == ORACLE.table_to_csv_bytes(expected)


def test_metadata_resource_failure_never_drops_index_projection(tmp_path, converter):
    raw = b'{"index_columns":["idx"],"extra":' + b'[' * 150 + b'0' + b']' * 150 + b'}'
    table = pa.table({'x': [1], 'idx': [123]}).replace_schema_metadata({b'pandas': raw})
    path = write(tmp_path, table)
    assert oracle(path) == b'x\n1\n'
    with pytest.raises(ConversionError, match='input_rejected'):
        convert(converter, path)


def test_hostile_zstd_frame_size_is_bounded(tmp_path, converter):
    path = tmp_path / 'hostile.parquet'
    pq.write_table(pa.table({'v': list(range(1000))}), path, compression='zstd', use_dictionary=False)
    raw = bytearray(path.read_bytes())
    frame = raw.index(b'\x28\xb5\x2f\xfd')
    # Claim a single-segment frame with an eight-byte maximal content size,
    # without changing the Parquet page/footer length declarations.
    raw[frame + 4] = 0xe0
    raw[frame + 5:frame + 13] = b'\xff' * 8
    path.write_bytes(raw)
    started = time.monotonic()
    with pytest.raises(ConversionError, match='input_rejected|resource_limit|child_failed'):
        convert(converter, path)
    assert time.monotonic() - started < 10
    assert not list(converter.root.glob('slot-[01]'))


def test_filtered_cap_does_not_limit_unfiltered_export(tmp_path, converter):
    path = write(tmp_path, pa.table({'v': pa.repeat(pa.scalar(1, type=pa.int8()), 2_000_001)}))
    with pytest.raises(ConversionError, match='parquet_filter_row_limit_exceeded'):
        asyncio.run(converter.convert(path, condition('v', 'Equals', '1')))
    with convert(converter, path) as artifact:
        assert artifact.rows == 2_000_001
        assert artifact.bytes == 4_000_004


def test_nested_filter_and_native_validation(tmp_path, converter):
    path = write(tmp_path, pa.table({'v': [1, 2, 3, 4, None]}))
    node = {'kind': 'group', 'logic': 'OR', 'children': [condition('v', 'LessThan', '2'),
            {'kind': 'group', 'logic': 'AND', 'children': [condition('v', 'GreaterThan', '3')]}]}
    with asyncio.run(converter.convert(path, node)) as artifact:
        assert artifact.path.read_bytes() == b'v\n1\n4\n'
    for invalid in [{'kind': 'group', 'logic': 'OR', 'children': []},
                    condition('v', 'Equals', '1') | {'number': True},
                    condition('v', 'Equals', '1') | {'unexpected': 1}]:
        with pytest.raises(ConversionError, match='validation_error'):
            asyncio.run(converter.convert(path, invalid))


@pytest.mark.parametrize('payload', [b'{"version":2,"version":2,"filter":null}',
                                    b'{"version":2.0,"filter":null}',
                                    b'\xef\xbb\xbf{"version":2,"filter":null}',
                                    b'{"version":2,"filter":NaN}', b'[' * 1000,
                                    b'{"version":2,"filter":null,"extra":1}',
                                    b'{"version":2,"filter":null} trailing'])
def test_native_request_is_strict_json(tmp_path, binary, payload):
    root = tmp_path / 'request'
    root.mkdir(mode=0o700)
    pq.write_table(pa.table({'v': [1]}), root / 'input.parquet')
    request = root / 'request.json'
    request.write_bytes(payload)
    request.chmod(0o600)
    with (tmp_path / 'lease').open('w') as lease:
        result = subprocess.run([str(binary), '--request-root', str(root),
            '--max-memory-bytes', str(1024**3), '--max-cpu-seconds', '100',
            '--max-output-bytes', str(2*1024**3), '--max-wall-seconds', '120',
            '--parent-pid', str(os.getpid()), '--admission-fd', str(lease.fileno())],
            capture_output=True, pass_fds=(lease.fileno(),), timeout=10)
    assert result.returncode == 3
    assert result.stdout == b''
    assert strict_json(result.stderr) == {'version': 2, 'status': 'error', 'code': 'input_rejected'}
    assert not (root / 'output.csv').exists()

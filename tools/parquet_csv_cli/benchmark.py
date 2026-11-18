"""Reproducible standalone comparison; immutable inputs, subprocess per sample."""
import argparse
import asyncio
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def worker(method, source, output, sidecar):
    source, output = Path(source), Path(output)
    if method == 'rust':
        from harness import Converter
        async def run():
            converter=Converter(ROOT/'rust/target/release/parquet_csv_cli',Path(sidecar),output.parent/'scratch')
            with await converter.convert(source) as artifact:
                return {'seconds':artifact.wall_seconds,'child_peak_rss_kib':artifact.peak_rss_kib,'child_cpu_seconds':artifact.cpu_seconds,'output_bytes':artifact.bytes,'output_sha256':digest(artifact.path),'rows':artifact.rows}
        result=asyncio.run(run())
        result['parent_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['aggregate_peak_upper_bound_kib']=result['parent_peak_rss_kib']+result['child_peak_rss_kib']
    else:
        import pyarrow as pa
        import pyarrow.csv as pc
        import pyarrow.parquet as pq
        spec=importlib.util.spec_from_file_location('oracle',ROOT.parents[1]/'wepppy/microservices/browse/parquet_tables.py')
        oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
        started=time.monotonic(); f=pq.ParquetFile(source)
        if method=='python':
            buffer=io.StringIO();writer=oracle.make_csv_writer(buffer);wrote=False
            for batch in f.iter_batches(batch_size=65536):
                table=oracle.project_table_for_output(pa.Table.from_batches([batch]),source_schema=f.schema_arrow,include_units=True)
                oracle.write_table_to_csv_writer(table,writer,include_header=not wrote);wrote=True
            if not wrote:
                table=oracle.project_table_for_output(pa.Table.from_batches([],schema=f.schema_arrow),source_schema=f.schema_arrow,include_units=True)
                oracle.write_table_to_csv_writer(table,writer,include_header=True)
            output.write_bytes(buffer.getvalue().encode())
        else:
            writer=None
            for batch in f.iter_batches(batch_size=65536):
                table=oracle.project_table_for_output(pa.Table.from_batches([batch]),source_schema=f.schema_arrow,include_units=True)
                if writer is None:writer=pc.CSVWriter(output,table.schema)
                writer.write_table(table)
            if writer:writer.close()
        result={'seconds':time.monotonic()-started,'rows':f.metadata.num_rows,'output_bytes':output.stat().st_size}
        result['output_sha256']=digest(output)
        result['parent_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result['aggregate_peak_upper_bound_kib']=result['parent_peak_rss_kib']
        result['cpu_seconds']=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime
        output.unlink()
    result.update(method=method,file=source.name,python=sys.version.split()[0])
    print(json.dumps(result),flush=True)


def main():
    if len(sys.argv)>1 and sys.argv[1]=='worker':
        worker(*sys.argv[2:]);return
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--repetitions',type=int,default=3);parser.add_argument('--methods',nargs='+',choices=['python','native','rust'],default=['python','native','rust'])
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from harness.provenance import generate
    binary=ROOT/'rust/target/release/parquet_csv_cli';sidecar=args.output/'binary.json';generate(binary,sidecar)
    env={'host':platform.node(),'platform':platform.platform(),'python':sys.version,'binary_sha256':digest(binary),'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'cache':'warm repetitions; independent advisory first-touch run recorded separately','cpu_count':os.cpu_count()}
    (args.output/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    with (args.output/'results.jsonl').open('a') as records:
        for source in sorted(args.corpus.glob('*.parquet')):
            for method in args.methods:
                for rep in range(args.repetitions):
                    command=[sys.executable,__file__,'worker',method,str(source),str(args.output/'temporary.csv'),str(sidecar)]
                    started=time.monotonic();p=subprocess.run(command,capture_output=True,text=True)
                    if p.returncode:
                        failure={'method':method,'file':source.name,'repetition':rep,'returncode':p.returncode,'stderr':p.stderr[:8192]}
                        (args.output/'failure.json').write_text(json.dumps(failure,indent=2)+'\n')
                        raise RuntimeError(f"benchmark worker failed: {failure}")
                    result=json.loads(p.stdout);result.update(repetition=rep,process_wall_seconds=time.monotonic()-started,input_sha256=digest(source))
                    records.write(json.dumps(result)+'\n');records.flush();print(json.dumps(result),flush=True)

if __name__=='__main__':main()

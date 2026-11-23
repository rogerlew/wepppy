import asyncio,json,os,pathlib,sys,time,hashlib,resource
sys.path.insert(0,'/tmp/parquet-csv-next/tools/parquet_csv_cli')
from harness import Converter,Limits,ConversionError
from harness.provenance import generate
root=pathlib.Path('/tmp/parquet-csv-evaluation');binary=pathlib.Path('/tmp/parquet-csv-next/tools/parquet_csv_cli/rust/target/release/parquet_csv_cli');side=root/'lifecycle-binary.json';generate(binary,side)
results=[];large=root/'corpus/H.wat.parquet'
async def main():
 for name,limits,expected in [('cpu',Limits(cpu_seconds=1),'child_failed'),('wall',Limits(wall_seconds=.01),'timeout'),('staging',Limits(staging_seconds=.000001),'staging_timeout'),('output',Limits(output_bytes=100),'resource_limit')]:
  scratch=root/('probe-'+name);c=Converter(binary,side,scratch,limits);started=time.monotonic()
  try:
   a=await c.convert(large);a.cleanup();raise AssertionError('unexpected success')
  except ConversionError as e:
   assert e.code==expected,(name,e.code)
   assert not list(scratch.glob('request-*'))
   results.append(dict(case=name,code=e.code,seconds=time.monotonic()-started,cleanup=True))
 c=Converter(binary,side,root/'concurrent-scratch');start=time.monotonic();tasks=[asyncio.create_task(c.convert(large)) for _ in range(2)]
 outputs=await asyncio.gather(*tasks)
 try:
  hashes=[hashlib.file_digest(a.path.open('rb'),'sha256').hexdigest() for a in outputs]
  assert len(set(hashes))==1
  try:await c.convert(large);raise AssertionError('admission not held')
  except ConversionError as e:assert e.code=='busy'
  results.append(dict(case='two_concurrent',seconds=time.monotonic()-start,rows=[a.rows for a in outputs],child_rss_kib=[a.peak_rss_kib for a in outputs],parent_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,output_sha256=hashes[0],third='busy'))
 finally:
  for a in outputs:a.cleanup()
 with large.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
 c=Converter(binary,side,root/'advisory-cold')
 with await c.convert(large) as a:results.append(dict(case='advisory_cold_rust',hint='POSIX_FADV_DONTNEED; no guaranteed physical eviction',seconds=a.wall_seconds,child_rss_kib=a.peak_rss_kib,rows=a.rows,output_sha256=hashlib.file_digest(a.path.open('rb'),'sha256').hexdigest()))
asyncio.run(main());(root/'lifecycle-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

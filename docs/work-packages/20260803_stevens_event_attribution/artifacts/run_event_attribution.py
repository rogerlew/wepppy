#!/usr/bin/env python3
"""Run paired Stevens PMET traces and summarize the focal event."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
SOURCE = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
BINARY = Path("/tmp/stevens-event-attribution-source-worktree/src/wepp_hill")
WORK = Path("/wc1/ablation/stevens-event-attribution-runs-20260804")
HILLS = tuple(range(49, 62))
AREAS = {49:22.50,50:80.10,51:140.22,52:210.33,53:81.90,54:64.71,
         55:73.44,56:82.62,57:176.94,58:256.68,59:83.07,60:2.34,61:4.68}
SIDECARS = ("gwcoeff.txt","snow.txt","wepp_ui.txt","chntyp.txt","tc.txt","chan.inp","pmetpara.txt")
TRACE_COLUMNS = ("year","day","plane","crop","etorc","kcb","rawp","kcbadj",
 "kcbcon","lai","root_depth","effective_root_depth","taw","raw","root_water",
 "plant_stress","ep","es","etke","etkr","eaj","kcmax","kecon","surface_water",
 "tew","rew","resint","fin","potes","bpotes")
WAT_COLUMNS = ("ofe","day","year","P","RM","Q","Ep","Es","Er","Dp","UpStrmQ",
 "SubRIn","latqcc","soil_water","frozen_water","snow_water","QOFE","tile",
 "irrigation","area","soil_water_total","profile_depth","porosity_capacity",
 "field_capacity","wilting_point","interception_storage")

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def disable_graphics(path):
    lines=path.read_text().splitlines()
    grph=next(i for i,line in enumerate(lines) if line.endswith(".grph.dat"))
    if lines[grph-1]=="Yes":
        lines[grph-1]="No"
        lines.pop(grph)
    lines=[line.replace(f"H{path.stem[1:]}.pass.dat",f"H{path.stem[1:]}.hbp") for line in lines]
    path.write_text("\n".join(lines)+"\n")

def numeric_rows(path, width):
    rows=[]
    for line in path.read_text().splitlines():
        fields=line.split()
        if len(fields)!=width: continue
        try: rows.append([float(x) for x in fields])
        except ValueError: pass
    return np.asarray(rows)

def run_case(scenario, hill, observe=True):
    lane=WORK/f"{scenario}_h{hill}"
    runs=lane/"runs"; output=lane/"output"
    runs.mkdir(parents=True); output.mkdir()
    src=SOURCE/scenario/"wepp"/"runs"
    try:
        for ext in ("run","man","slp","cli","sol"):
            shutil.copy2(src/f"p{hill}.{ext}",runs/f"p{hill}.{ext}")
        for name in SIDECARS: shutil.copy2(src/name,runs/name)
        disable_graphics(runs/f"p{hill}.run")
        if observe: (runs/"stevens_pmet_observe.on").write_text("")
        with (runs/f"p{hill}.run").open("rb") as stdin:
            p=subprocess.run([str(BINARY)],cwd=runs,stdin=stdin,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,check=False)
        if p.returncode or p.stderr.strip():
            raise RuntimeError(f"{scenario} H{hill} rc={p.returncode} {p.stderr[-500:]!r}")
        wat_path=output/f"H{hill}.wat.dat"
        if not wat_path.exists():
            raise RuntimeError(p.stdout[-3000:].decode(errors="replace"))
        wat=numeric_rows(wat_path,len(WAT_COLUMNS))
        if wat.shape!=(36525,len(WAT_COLUMNS)) or not np.isfinite(wat).all():
            sample="\n".join((output/f"H{hill}.wat.dat").read_text().splitlines()[-8:])
            raise ValueError(f"water table {wat.shape}:\n{sample}\nstdout:\n{p.stdout[-2000:].decode(errors='replace')}")
        target=wat[(wat[:,2]==34)&(wat[:,1]>=173)&(wat[:,1]<=203)]
        if not observe: return sha(output/f"H{hill}.wat.dat"), []
        trace=np.loadtxt(runs/"wepp_observe_pmet.csv",delimiter=",")
        if trace.shape!=(36525,len(TRACE_COLUMNS)) or not np.isfinite(trace).all(): raise ValueError(trace.shape)
        trace=trace[(trace[:,0]==34)&(trace[:,1]>=173)&(trace[:,1]<=203)]
        if trace.shape!=(31,len(TRACE_COLUMNS)): raise ValueError(trace.shape)
        rows=[]
        for tr,wa in zip(trace,target,strict=True):
            row={"scenario":scenario,"hill":hill}
            row.update(zip(TRACE_COLUMNS,tr,strict=True))
            for field in ("P","RM","Q","soil_water","soil_water_total","field_capacity","wilting_point"):
                row[field]=wa[WAT_COLUMNS.index(field)]
            rows.append(row)
        return sha(wat_path),rows
    finally: shutil.rmtree(lane,ignore_errors=True)

def aggregate(rows):
    out=[]
    for scenario in ("burned","undisturbed"):
      for day in range(173,204):
        subset=[r for r in rows if r["scenario"]==scenario and int(r["day"])==day]
        weights=np.array([AREAS[int(r["hill"])] for r in subset]); weights/=weights.sum()
        row={"scenario":scenario,"day":day}
        for field in TRACE_COLUMNS[4:]+("P","RM","Q","soil_water","soil_water_total","field_capacity","wilting_point"):
            row[field]=float(np.average([r[field] for r in subset],weights=weights))
        out.append(row)
    return out

def constrained_proxy(etorc,etke,etkr,eaj,kcmax):
    return etorc*min(etke*etkr,eaj*kcmax)

def shapley_day(b,u):
    names=("etorc","etke","etkr","exposure")
    def value(bits):
        vals={}
        for i,n in enumerate(names):
            src=u if bits&(1<<i) else b
            vals[n]=src[n] if n!="exposure" else src["eaj"]*src["kcmax"]
        return vals["etorc"]*min(vals["etke"]*vals["etkr"],vals["exposure"])
    phi={n:0. for n in names}; n=len(names)
    import math
    for i,name in enumerate(names):
      for bits in range(1<<n):
        if bits&(1<<i): continue
        k=bits.bit_count(); w=math.factorial(k)*math.factorial(n-k-1)/math.factorial(n)
        phi[name]+=w*(value(bits|(1<<i))-value(bits))
    phi["total_proxy_change"]=value((1<<n)-1)-value(0)
    phi["burned_proxy"]=value(0); phi["undisturbed_proxy"]=value((1<<n)-1)
    return phi

def write_csv(path,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n"); w.writeheader(); w.writerows(rows)

def main():
    if WORK.exists(): shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    try:
      # Observation must not change model output.
      off_hash,_=run_case("burned",59,False)
      all_rows=[]
      observed_hashes={}
      with ThreadPoolExecutor(max_workers=min(8,os.cpu_count() or 1)) as ex:
        futures={ex.submit(run_case,s,h,True):(s,h) for s in ("burned","undisturbed") for h in HILLS}
        for i,f in enumerate(as_completed(futures),1):
            wat_hash,rows=f.result(); all_rows.extend(rows); observed_hashes[futures[f]]=wat_hash
            print(f"completed {i}/26",flush=True)
      parity=off_hash==observed_hashes[("burned",59)]
      agg=aggregate(all_rows)
      paired=[]
      for day in range(173,204):
        b=next(r for r in agg if r["scenario"]=="burned" and r["day"]==day)
        u=next(r for r in agg if r["scenario"]=="undisturbed" and r["day"]==day)
        sh=shapley_day(b,u); sh.update({"day":day,"actual_es_change_u_minus_b":u["es"]-b["es"]})
        paired.append(sh)
      write_csv(HERE/"event-trace-area-weighted.csv",agg)
      write_csv(HERE/"pmet-proxy-shapley.csv",paired)
      b203=next(r for r in agg if r["scenario"]=="burned" and r["day"]==203)
      u203=next(r for r in agg if r["scenario"]=="undisturbed" and r["day"]==203)
      prior=lambda s,f:sum(r[f] for r in agg if r["scenario"]==s and 173<=r["day"]<=202)
      summary={"observation_off_byte_parity":parity,"binary_sha256":sha(BINARY),
       "base_commit":"2f65506d239b449bbb73c6820ff9cb949fa55158",
       "prior30":{s:{f:prior(s,f) for f in ("P","RM","ep","es","fin")} for s in ("burned","undisturbed")},
       "day203":{s:{f:r[f] for f in ("Q","es","ep","etorc","etke","etkr","eaj","kcmax","kecon","surface_water","lai","root_depth","soil_water","field_capacity")}
                 for s,r in (("burned",b203),("undisturbed",u203))},
       "prior30_shapley_sums":{k:sum(r[k] for r in paired[:-1]) for k in ("etorc","etke","etkr","exposure","total_proxy_change")}}
      (HERE/"results.json").write_text(json.dumps(summary,indent=2)+"\n")
      days=np.arange(173,204)
      fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True,constrained_layout=True)
      for s,c in (("burned","#d95f02"),("undisturbed","#1b9e77")):
        x=[r for r in agg if r["scenario"]==s]
        axes[0].plot(days,[r["es"] for r in x],label=f"{s} Es",color=c)
        axes[0].plot(days,[r["ep"] for r in x],label=f"{s} Ep",color=c,ls="--")
        axes[1].plot(days,[r["surface_water"] for r in x],label=f"{s} PMET surface water",color=c)
      axes[0].set_ylabel("Flux (mm/day)"); axes[1].set_ylabel("Available water (mm)")
      axes[1].set_xlabel("Julian day, simulation year 34")
      for ax in axes: ax.grid(alpha=.2); ax.legend(ncol=2,fontsize=8)
      fig.savefig(HERE/"event-pmet-state.png",dpi=200); plt.close(fig)
      print(json.dumps(summary,indent=2))
    finally: shutil.rmtree(WORK,ignore_errors=True)

if __name__=="__main__": main()

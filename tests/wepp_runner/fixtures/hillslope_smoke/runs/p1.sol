9003
# 
# WEPPcloud v.0.1.0 (c) University of Idaho
# 
# Build Date: 2026-03-31 17:26:13.087411
# Source Data: Surgo
# 
# Mukey: 2108969
# Major Component: 26663480 (comppct_r = 50.0)
# Texture: sand loam
# 
# Chkey   hzname  mask hzdepb_r  ksat_r fraggt10_r frag3to10_r dbthirdbar_r    clay    sand     vfs      om
# ------------------------------------------------------------------------------------------------------------
# 79608129   Oi     X        3.0   300.0        0.0         0.0          0.5    15.0    35.0     5.0    85.0
# 79608130   A               8.0   28.22        0.0        20.0          1.5    10.0    70.0    12.3     1.0
# 79608122   E              28.0   28.22        0.0        20.0         1.48     6.0    70.0    13.0     0.5
# 79608123   EB1            51.0   28.22        6.0        24.0          1.5     8.0    72.0    12.5     0.5
# 79608124   EB2            62.0   28.22        5.0        35.0          1.5     8.0    72.0    12.5     0.5
# 79608128   E and Bt          82.0   28.22       33.0        28.0         1.48    12.0    65.0    10.3     0.5
# 79608125   E and Bt         102.0    9.17       33.0        27.0         1.53    22.0    65.0    14.8     0.5
# 79608126   C             125.0   28.22       33.0        22.0         1.51    15.0    70.0    11.0     0.0
# 79608127   R      R      150.0    0.05         -           -        1.5196     7.0    66.8    10.0     7.0
# 
# Restricting Layer:
# ksat threshold: 2.00000
# type: Lithic bedrock
# ksat: 0.05000
# 
# defaults applied to missing chorizon data:
# sandtotal_r  ->      66.800
# claytotal_r  ->       7.000
# om_r         ->       7.000
# cec7_r       ->      11.300
# sandvf_r     ->      10.000
# smr          ->      55.500
# 
# Build Notes:
# 79608130::wilt_pt estimated from wfifteenbar_r and rock
# 79608130::field_cap estimated from wthirdbar_r and rock
# 79608122::wilt_pt estimated from wfifteenbar_r and rock
# 79608122::field_cap estimated from wthirdbar_r and rock
# 79608123::wilt_pt estimated from wfifteenbar_r and rock
# 79608123::field_cap estimated from wthirdbar_r and rock
# 79608124::wilt_pt estimated from wfifteenbar_r and rock
# 79608124::field_cap estimated from wthirdbar_r and rock
# 79608128::wilt_pt estimated from wfifteenbar_r and rock
# 79608128::field_cap estimated from wthirdbar_r and rock
# 79608125::wilt_pt estimated from wfifteenbar_r and rock
# 79608125::field_cap estimated from wthirdbar_r and rock
# 79608126::wilt_pt estimated from wfifteenbar_r and rock
# 79608126::field_cap estimated from wthirdbar_r and rock
# 79608127::using default rock content of 55.5%
# 79608127::wilt_pt estimated from rosetta2
# 79608127::field_cap estimated from rosetta2
# 79608127::bd estimated from sand, vfs, and clay
# res_lyr_i 8
# 
# THIS FILE AND THE CONTAINED DATA IS PROVIDED BY THE UNIVERSITY OF IDAHO
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UNIVERSITY OF IDAHO
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHERE IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS FILE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# 
# If you change the original contexts of this file please
# indicate it by putting an 'X' in the box here -> [ ]
# 
# 
# 
# wepppy.wepp.soils.utils.WeppSoilUtil::9003.0migration
# Build Date: 2026-03-31 17:26:27.066343
# Source File: :/wc1/runs/de/delicate-game/soils/2108969.sol
# 
# Replacements
# --------------------------
# luse -> forest low sev fire
# stext -> sand loam
# ki -> 400000
# kr -> 0.00012
# shcrit -> 2
# avke -> 20
# ksflag -> 0
# ksatadj -> 0
# ksatfac -> 1.3
# ksatrec -> 0.3
# pmet_kcb -> 0.95
# pmet_rawp -> 0.8
# rdmax -> 0.3
# xmxlai -> 4
# keffflag -> 1
# lkeff -> 10
# plant.data.decfct ->
# plant.data.dropfc ->
# 
# h0_min_depth = None
# h0_max_om = None
# 
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.75)
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast(kslast=0.001)
# wepppy.wepp.soils.utils.WeppSoilUtil::clip_soil_depth(max_depth=395)
Any comments:
1 0
0	 'forest low sev fire'	 301	 'sand loam'	 10
'Bullwark-Catamount families-Rock outcrop complex, 40 to 150 percent slopes'	 'CBV-SL'	 4	 0.16	 0.75	 400000	 0.00012	 2
	80.0	 1.5	 20	 10.0	 0.2212	 0.0981	 70.0	 10.0	 1.0	 7.3	 48.0	 0.06431	 0.3769	 0.01745	 1.516	 49.99	 0.08202	 0.1885
	200.0	 1.48	 20	 10.0	 0.164	 0.054	 70.0	 6.0	 0.5	 4.5	 54.4	 0.05772	 0.3731	 0.01768	 1.562	 65.73	 0.07139	 0.1712
	280.0	 1.48	 101.592	 10.0	 0.164	 0.054	 70.0	 6.0	 0.5	 4.5	 54.4	 0.05772	 0.3731	 0.01768	 1.562	 65.73	 0.07139	 0.1712
	395	 1.5	 101.592	 1.0	 0.14	 0.052	 72.0	 8.0	 0.5	 5.6	 67.8	 0.06073	 0.3741	 0.01854	 1.558	 61.72	 0.07427	 0.175
1 10000.0 0.001

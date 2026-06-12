9002
# 
# WEPPcloud v.0.1.0 (c) University of Idaho
# 
# Build Date: 2026-05-28 16:53:55.238968
# Source Data: Surgo
# 
# Mukey: 620333
# Major Component: 27227457 (comppct_r = 50.0)
# Texture: loam
# 
# Chkey   hzname  mask hzdepb_r(cm) ksat_r(um/s) fraggt10_r frag3to10_r dbthirdbar_r    clay    sand     vfs      om
# ------------------------------------------------------------------------------------------------------------
# 81295703   Oi     X        5.0   350.0        0.0         0.0          0.2     7.0    66.8    10.0    75.0
# 81295704   A              15.0    10.0        0.0         0.0         1.47    20.0    40.0    11.5    1.25
# 81295705   Bt1            38.0     3.0        0.0         0.0         1.39    30.0    35.0    10.4    1.25
# 81295706   Bt2            81.0     3.0        0.0         0.0         1.52    30.0    35.0    10.4     0.4
# 81295707   Bt3           100.0    30.0        0.0         0.0         1.62    15.0    55.0     9.0    0.15
# 81295708   R      R      150.0     0.4         -           -        1.5196     7.0    66.8    10.0     7.0
# 
# Restricting Layer:
# ksat threshold (um/s): 2.00000
# type: Lithic bedrock
# ksat (um/s): 0.40000
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
# 81295704::wilt_pt estimated from wfifteenbar_r and rock
# 81295704::field_cap estimated from wthirdbar_r and rock
# 81295705::wilt_pt estimated from wfifteenbar_r and rock
# 81295705::field_cap estimated from wthirdbar_r and rock
# 81295706::wilt_pt estimated from wfifteenbar_r and rock
# 81295706::field_cap estimated from wthirdbar_r and rock
# 81295707::wilt_pt estimated from wfifteenbar_r and rock
# 81295707::field_cap estimated from wthirdbar_r and rock
# 81295708::using default rock content of 55.5%
# 81295708::wilt_pt estimated from rosetta2
# 81295708::field_cap estimated from rosetta2
# 81295708::bd estimated from sand, vfs, and clay
# res_lyr_i 5
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
# wepppy.wepp.soils.utils.WeppSoilUtil::9002.0migration
# Build Date: 2026-05-28 16:53:57.270720
# Source File: :/wc1/runs/ho/honeyed-marathoner/_pups/omni/scenarios/undisturbed/soils/620333.sol
# 
# Replacements
# --------------------------
# luse -> forest
# stext -> loam
# ki -> 400000
# kr -> 3.00E-05
# shcrit -> 1
# avke -> 50
# bd ->
# ksflag -> 0
# ksatadj -> 0
# ksatfac -> 1.5
# ksatrec -> 0.3
# pmet_kcb -> 0.45
# pmet_rawp -> 0.8
# rdmax -> 2
# xmxlai -> 14
# keffflag -> 0
# lkeff -> -9999
# plant.data.decfct -> 1
# plant.data.dropfc -> 1
# 
# h0_min_depth = None
# h0_max_om = None
# 
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.75)
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast(kslast=100.0)
Any comments:
1 0
0	 'forest'	 'loam'	 1.5 	 0.3
'Ericson-Nooney families, association, 15 to 60 percent slopes, Broadly Defined'	 'L'	 5	 0.16	 0.75	 400000	 3e-05	 1
	150.0	 1.47	 50	 10.0	 0.2978	 0.1407	 40.0	 20.0	 1.25	 11.3	 9.0	 0.08466	 0.3877	 0.007674	 1.4	 12.33	 0.1301	 0.2471
	200.0	 1.39	 50	 10.0	 0.3518	 0.2072	 35.0	 30.0	 1.25	 24.1	 17.0	 0.1029	 0.4263	 0.007532	 1.361	 12.64	 0.1617	 0.2852
	380.0	 1.39	 10.8	 10.0	 0.3518	 0.2072	 35.0	 30.0	 1.25	 24.1	 17.0	 0.1029	 0.4263	 0.007532	 1.361	 12.64	 0.1617	 0.2852
	810.0	 1.52	 10.8	 1.0	 0.3512	 0.2107	 35.0	 30.0	 0.4	 23.1	 16.0	 0.1017	 0.3934	 0.007908	 1.333	 6.756	 0.1611	 0.2807
	1000.0	 1.62	 108.0	 1.0	 0.2129	 0.1106	 55.0	 15.0	 0.15	 11.9	 15.0	 0.07179	 0.351	 0.01289	 1.375	 12.79	 0.1105	 0.2259
1 10000.0 100.0

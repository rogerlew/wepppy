9002
# 
# WEPPcloud v.0.1.0 (c) University of Idaho
# 
# Build Date: 2026-07-27 23:29:12.875545
# Source Data: Surgo
# 
# Mukey: 469952
# Major Component: 27419474 (comppct_r = 35.0)
# Texture: loam
# 
# Chkey   hzname  mask hzdepb_r(cm) ksat_r(um/s) fraggt10_r frag3to10_r dbthirdbar_r    clay    sand     vfs      om
# ------------------------------------------------------------------------------------------------------------
# 81885770   A              18.0     9.0        0.0         0.0          1.5    19.5    42.4    12.2    0.75
# 81885769   Cr     X       43.0    0.03        0.0         0.0       1.5336     0.0    66.8    10.0     0.0
# 
# Restricting Layer:
# ksat threshold (um/s): 2.00000
# type: -
# ksat: -
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
# 81885770::wilt_pt estimated from wfifteenbar_r and rock
# 81885770::field_cap estimated from wthirdbar_r and rock
# res_lyr_i None
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
# Build Date: 2026-07-27 23:29:20.987079
# Source File: :/wc1/runs/ha/hand-to-mouth-drought/soils/469952.sol
# 
# Replacements
# --------------------------
# luse -> shrub moderate sev fire
# stext -> loam
# ki -> 1000000
# kr -> 8.00E-05
# shcrit -> 1
# avke -> 20
# bd ->
# ksflag -> 0
# ksatadj -> 0
# ksatfac -> 1.3
# ksatrec -> 0.3
# pmet_kcb -> 0.95
# pmet_rawp -> 0.8
# rdmax -> 0.2
# xmxlai -> 2
# keffflag -> 1
# lkeff -> 1
# plant.data.decfct ->
# plant.data.dropfc ->
# 
# h0_min_depth = None
# h0_max_om = None
# 
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_initial_sat(initial_sat=0.75)
# wepppy.wepp.soils.utils.WeppSoilUtil::modify_kslast(kslast=0.0)
Any comments:
1 0
0	 'shrub moderate sev fire'	 'loam'	 9.3 	 0.3
'Chumash-Boades-Malibu association, 30 to 75 percent slopes'	 'GR-L'	 2	 0.23	 0.80	 1000000	 8e-05	 1
	200.0	 1.5	 20	 10.0	 0.3132	 0.1421	 42.4	 19.5	 0.75	 16.0	 24.0	 0.08311	 0.3806	 0.008357	 1.391	 11.67	 0.1281	 0.2451
	400.0	 1.5	 32.4	 10.0	 0.3132	 0.1421	 42.4	 19.5	 0.75	 16.0	 24.0	 0.08311	 0.3806	 0.008357	 1.391	 11.67	 0.1281	 0.2451
1 10 0.0000108

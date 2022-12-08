7778
# 
# WEPPcloud v.0.1.0 (c) University of Idaho
# 
# Build Date: 2022-08-18 15:31:55.004470
# Source Data: Surgo
# 
# Mukey: 1652127
# Major Component: 14517950 (comppct_r = 50.0)
# Texture: sand loam
# 
# Chkey   hzname  mask hzdepb_r  ksat_r fraggt10_r frag3to10_r dbthirdbar_r    clay    sand     vfs      om
# ------------------------------------------------------------------------------------------------------------
# 41807921   Oi     X        3.0   400.0       57.0        13.0         0.05     7.0    66.8    10.0    80.0
# 41807923   A              23.0    50.0        0.0         0.0          1.1     3.0    79.0     9.1     5.0
# 41807924   AC             33.0    40.0        0.0         0.0         1.29     3.0    79.0     9.1     2.0
# 41807925   C              69.0    40.0        0.0         0.0         1.39     3.0    90.6     5.5    0.86
# 41807922   Cr     R       94.0     1.0         -           -           1.4     7.0    66.8    10.0     7.0
# 
# Restricting Layer:
# ksat threshold: 2.00000
# type: Paralithic bedrock
# ksat: 1.00000
# 
# defaults applied to missing chorizon data:
# sandtotal_r  ->      66.800
# claytotal_r  ->       7.000
# om_r         ->       7.000
# cec7_r       ->      11.300
# sandvf_r     ->      10.000
# ksat_r       ->      28.000
# dbthirdbar_r ->       1.400
# smr          ->      55.500
# field_cap    ->       0.242
# wilt_pt      ->       0.115
# 
# Build Notes:
# initial assumed ksat = 0.750
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
# wepppy.wepp.soils.utils.WeppSoilUtil 7778disturbed migration
#   Build Date: 2022-08-18 15:32:00.526707
#   Source File: :Test_Watershed_15/soils/1652127.sol
# 
#   Replacements
#   --------------------------
#   luse -> forest
#   stext -> sand loam
#   ki -> 400000
#   kr -> 8.00E-05
#   shcrit -> 2
#   avke -> 60
# 
#   h0_min_depth = None
#   h0_max_om = None
# 
Any comments:
1 1
'Cagwin Rock outcrop complex, 30 to 50 percent slopes, extremely stony'	 'GR-LCOS'	 3	 0.16	 0.75	 400000	 8.00E-05	 2
	230.0	 1.1	 60	 10.0	 0.2207	 0.0914	 79.0	 3.0	 5.0	 11.0	 42.0
	330.0	 1.29	 144.0	 10.0	 0.1631	 0.0523	 79.0	 3.0	 2.0	 7.2	 35.0
	800.0	 1.39	 144.0	 1.0	 0.1161	 0.0357	 90.6	 3.0	 0.86	 4.0	 44.0
1 10000.0 3.6
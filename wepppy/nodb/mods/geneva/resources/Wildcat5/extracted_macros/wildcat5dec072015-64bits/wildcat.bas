Attribute VB_Name = "wildcat"
Const M2Ft = 1 / 0.3048, Ha2Acre = 2.4709661, MM2In = 1 / 25.4



'               ** INITIALIZE VARIABLES **

 Const maxcoordinate = 5000, maxhru = 37, maxcust = 100, unknow = -1, C$ = "±"
 Const SCSNUM = 13, FFNUM = 11, UNUM = 2
 'Dim q0(6), H(14), S0(14), t(101), p1(20), P2(20), p(101), qf(maxhru)
 Dim q0(7), H(300), S0(300), T(102), P2(21), P(102), qf(maxhru + 1)
 Dim T2(12), b$(6), t3(13), P3(3), t4(maxcust + 1), p4(maxcust + 1), fct(maxhru + 1), ip(30)
 Dim hru(maxhru + 1, 3), Ia(maxhru + 1), iaa(maxhru + 1)

 
 Dim MethodRainfallE As Byte   'Rainfall Excess (CN 0.2, CN0.5,Phi, mu, F)
 Dim MethodTc As Byte
 Dim MethodUH As Byte
 Dim MethodUHsub As Byte
 Dim LenLChan As Double
 Dim AvLndSI As Double
 Dim s As Double
 
 Dim WSAREA1 As Double
 Dim WSAREA2 As Double
 Dim CN As Double
 Dim CN5 As Double
 Dim NumHRU As Integer
 Dim UseTC As Boolean
 Dim OKTimeTc As Boolean
 
 Dim TimeCon As Double  'Time of Concentration
 Dim TimeLag As Double  'Time to Lag
 Dim InAbs As Double
 Dim DeltaT As Double
 Dim DeltaTUH As Double
 Dim NumLines As Integer
 Dim StrmType As Byte 'Storm Type
 Dim StrmDur As Double 'Storm Duration
 Dim StrmRain As Double 'Storm Rainfall
 Dim TotRoaf As Double 'Total Runoff
 
 Dim NUMDist As Integer
 Dim NumCust As Integer 'Number of values for custom storm
 Dim NumHData As Integer 'Number of elements in the Unit Hydrograph
 
 Dim QCHK As Boolean
 
 Dim SCSB_T As Variant
 Dim SCSB_P As Variant
 Dim FarmerF_T As Variant
 Dim FarmerF_P As Variant
 Dim Uniform_T As Variant
 Dim Uniform_P As Variant
 
 Dim Ar, WCN, P1, Q  As Double
 Dim T1 As Double
 Dim Contlast As Double
 Dim Contrib As Double
 Dim HSteps As Integer
 
 Dim imin As Single
 Dim imax As Single
 Dim itmax As Single
 Dim usingCN As Boolean
 
 Dim Mu As Double 'Distributed Infiltration Capacities
 Dim PHI As Double 'Infiltration velocity phi Index
 Dim LinFracC As Double 'Linear Fraction C
 Dim CumQ As Double
 Dim MaxContribArea As Double
 Dim myImax As Double
 Dim ReportTime As String
 Dim TP_UH As Double
 Dim TB_UH As Double
 Dim ComplacentA As Double
 Dim ComplacentB1 As Double
 Dim ComplacentB2 As Double
 Dim isMetricOUT As Boolean
 Dim isMetricIN As Boolean
 
 

 Function getval(SName, R)
   getval = Worksheets(SName).Range(R).value
 End Function

 Function setUSOUT(value, metricfactor)
  If (isMetricOUT = False) Then
    setUSOUT = value
   Else
    setUSOUT = value * metricfactor
  End If
 End Function


Sub take_sheet_data()

Dim SName As String
Dim I As Integer
Dim Count As Integer
Dim AreaSum As Double
Dim Val1 As Variant
Dim Val2 As Variant

  MethodUH = Worksheets("UnitH").Range("BA3").value
  MethodUHsub = Worksheets("UnitH").Range("AX21").value
  MethodRainfallE = Worksheets("tmpData").Range("E3").value
  usingCN = ((MethodRainfallE = 1) Or (MethodRainfallE = 2))
  
  Mu = Worksheets("tmpData").Range("E7").value
  PHI = Worksheets("tmpData").Range("E10").value
  LinFracC = Worksheets("tmpData").Range("E11").value
  
  ComplacentB1 = Worksheets("tmpData").Range("E12").value
  ComplacentB2 = Worksheets("tmpData").Range("E13").value
  ComplacentA = Worksheets("tmpData").Range("E14").value

  SName = "tmpData"
  I = getval(SName, "E18") 'Tc Input option
  If (I = 1) Then
     UseTC = True
     TimeCon = getval(SName, "E19")
  Else
    UseTC = False
    MethodTc = getval(SName, "E20")
    AvLndSI = getval(SName, "E23")
    LenLChan = getval(SName, "E24")
    
    If (I = 3) Then MethodTc = 3 'SIMMAS
    
  End If
  
  TimeLag = getval(SName, "I20")
  
  
  If (isMetricIN = True) Then
   Mu = Mu * MM2In
   PHI = PHI * MM2In
   ComplacentA = ComplacentA * MM2In
   LenLChan = LenLChan * M2Ft
  End If
  
  
  If (usingCN = True) Then
    SName = "CNS"
    Count = 0
    For I = 1 To 20
      Val1 = Worksheets(SName).Cells(I + 5, 5).value
      Val2 = Worksheets(SName).Cells(I + 5, 7).value
      If IsNumeric(Val1) And IsNumeric(Val2) Then
       If (Val1 > 0) And (Val2 > 0) Then
        Count = Count + 1
        If (isMetricIN = True) Then
         hru(Count, 1) = Val1 * Ha2Acre 'area
        Else
         hru(Count, 1) = Val1  'area
        End If
        hru(Count, 2) = Val2  'CN
        End If
      End If
    Next I
    NumHRU = Count
  End If
  
  If (MethodRainfallE = 3) Then
    SName = "DistriF"
    Count = 0
    For I = 1 To 34
      Val1 = Worksheets(SName).Cells(I + 5, 6).value
      Val2 = Worksheets(SName).Cells(I + 5, 5).value
      If IsNumeric(Val1) And IsNumeric(Val2) Then
      If (Val1 > 0) Then
        Count = Count + 1
        If (isMetricIN = True) Then
        hru(Count, 1) = Val1 * Ha2Acre  'area
        hru(Count, 2) = Val2 * MM2In 'F
        Else
        hru(Count, 1) = Val1  'area
        hru(Count, 2) = Val2  'F
        End If
      End If
      End If
    Next I
    NumHRU = Count
  End If
  
  
  SName = "tmpData"
  StrmDur = getval(SName, "R5")
  StrmRain = getval(SName, "R6")
  StrmType = getval(SName, "R7")
  
  If (isMetricIN = True) Then
   StrmRain = StrmRain * MM2In
  End If
  
  If (StrmType = 4) Then
    'Count elements for custom storm
    SName = "cstorm"
    Count = 0
    For I = 1 To 100
      Val1 = Worksheets(SName).Cells(I + 11, 5).value
      Val2 = Worksheets(SName).Cells(I + 11, 6).value
      If (IsNumeric(Val1) And IsNumeric(Val2)) Then
      tmp1 = "" & Val1
      tmp2 = "" & Val2
      If (Len(tmp1) > 0) And (Len(tmp2) > 0) Then
      If (Val1 >= 0) And (Val2 >= 0) Then
        Count = Count + 1
        t4(Count) = Val1
        p4(Count) = Val2
      End If
      End If
      End If
    Next I
    NumCust = Count
  End If 'custom storm
  
  
  If (StrmType = 5) Then
    SName = "tmpData"
   imin = Worksheets(SName).Range("N5").value
   imax = Worksheets(SName).Range("N6").value
   itmax = Worksheets(SName).Range("N7").value
  End If 'generic storm
  
  
  
  
  'MsgBox "UH = " & MethodUH & "UHSub = " & MethodUHsub
End Sub


Sub set_arrays_storm()
 SCSB_T = Array(0, 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6)
 SCSB_P = Array(0, 0, 3.5, 8, 13.5, 23, 60, 70, 78, 83.5, 88.5, 92.5, 96, 100)

 FarmerF_T = Array(0, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
 FarmerF_P = Array(0, 0, 36.5, 61.5, 76.5, 83.9, 88, 90.8, 93.2, 95.2, 97.7, 100)

 Uniform_T = Array(0, 0, 100)
 Uniform_P = Array(0, 0, 100)
End Sub


Function GetTimeCon() As Double
Dim v As Double

 If (MethodTc = 1) Then
  v = (0.0078 * (LenLChan ^ 0.77) / ((AvLndSI / 100) ^ 0.385)) / 60
 Else
  v = ((LenLChan ^ 0.8) * ((s + 1) ^ 0.7) / (1900 * (AvLndSI ^ 0.5))) / 0.6
 End If
  GetTimeCon = v
End Function


Function GetS(CN As Double) As Double
 GetS = (1000 / CN) - 10
End Function

Function GetS2(P As Double, Q As Double) As Double
 Dim Inside As Double
 
  Inside = (4 * Q ^ 2) + (5 * P * Q)
  GetS2 = 5 * ((P + 2 * Q) - (Inside ^ 0.5))
End Function

Function GetCN_S(s As Double) As Double
 GetCN_S = 1000 / (s + 10)
End Function

Function GetCN_PQ(P As Double, Qin) As Double
  Dim CN As Double
  Dim s As Double
  Dim Q As Double
  Q = Qin
  
  CN = 0
  If P > 0 Then
   If (Q > 0 And P > Q) Then
     s = GetS2(P, Q)
     CN = GetCN_S(s)
   End If
  End If
 GetCN_PQ = CN
End Function

Function GetCN5(CN) As Double
Dim S2 As Double
Dim S5 As Double

  If (CN < 96) Then
  S2 = 1000 / CN - 10
  S5 = 1.33 * S2 ^ (1.15)
  GetCN5 = 1000 / (10 + S5)
  Else
  
   GetCN5 = CN
  End If
  
End Function

Function GetCN5_QP(Q, P) As Double
Dim CN5 As Double
Dim S5 As Double


  S5 = 20 * (P + 9.5 * Q - (90.25 * Q * Q + 20 * Q * P) ^ (0.5))
  CN5 = 1000 / (10 + S5)
  'If (CN5 > 100) Then CN5 = 100
  
  GetCN5_QP = CN5
  
End Function

Function GetCN2After(P As Double, CN As Double) As Double
' CN after the Event
Dim s As Double
Dim S2 As Double
Dim CN2 As Double
Dim PStar As Double
Dim J As Double


 s = GetS(CN)
 If (P > 0) Then
  PStar = P / s
  If (P < (0.2 * s)) Then
   S2 = 1 - PStar / 1.2
   CN2 = (1200 * CN) / (1200 - P * CN)
  ElseIf (P = 0.2 * s) Then
   'P=0.2S
   S2 = 1 / 1.2
   CN2 = (600 * CN) / (CN + 500)
  Else
   '0<0.2S<P
   S2 = 25 / (30 * P + 24)
   J = (100 / CN) - 1
   CN2 = (100 * (3 * P + 24 * J)) / (3 * P + 24 * J + 25 * J * J)
  End If
 
 Else
  S2 = 1 / 1.2
  CN2 = 1200 / (1200 / CN)
 End If
 
  GetCN2After = CN2
End Function
'Compute Watershed/Storm parameters

Sub Initial_Parameters_CN()
 Dim I As Integer
 
 WSAREA1 = 0
 CN = 0
 CN5 = 0
 For I = 1 To NumHRU
   WSAREA1 = WSAREA1 + (hru(I, 1) / 640)
 Next I
 
 For I = 1 To NumHRU
   CN = CN + (hru(I, 2) * ((hru(I, 1) / 640) / WSAREA1))
   CN5 = CN5 + (GetCN5(hru(I, 2)) * ((hru(I, 1) / 640) / WSAREA1))
 Next I
 
 WSAREA2 = 640 * WSAREA1 'hacer la transformacion
 
 s = GetS(CN)
 If MethodRainfallE = 1 Then
   InAbs = (200 / CN) - 2
 Else
  InAbs = 0.05 * (1.33 * s ^ (1.15))
 End If
End Sub


Sub GetTc_fromTL()
 Dim tp As Double
 If MethodUH = 1 Then tp = 9 / 11 * TimeLag
 If MethodUH = 2 Then
   If (MethodUHsub = 1) Then tp = TimeLag '2
   If (MethodUHsub = 2) Then tp = 3 / 3.35 * TimeLag '2.5
   If (MethodUHsub = 3) Then tp = 9 / 11 * TimeLag  '2.667
   If (MethodUHsub = 4) Then tp = 3 / 4 * TimeLag  '3
   'If (MethodUHsub = 5) Then tp = 3 / 4.33333333 * TimeLag '3.33
   'If (MethodUHsub = 6) Then tp = 3 / 4.66666667 * TimeLag '3.67
   
   If (MethodUHsub = 5) Then tp = 9 / 13 * TimeLag '3.33
   If (MethodUHsub = 6) Then tp = 9 / 14 * TimeLag '3.67
   
   If (MethodUHsub = 7) Then tp = 3 / 5 * TimeLag '4
   If (MethodUHsub = 8) Then tp = 3 / 6 * TimeLag '5
 End If
 
 If MethodUH = 3 Then tp = 0.7762 * TimeLag 'Curvilinear
 If MethodUH = 4 Then tp = 0.5745 * TimeLag 'broken Triangle
 TimeCon = 5 / 3 * tp
 
End Sub

Sub Initial_Parameters()
 
  If (usingCN = True) Then
     Initial_Parameters_CN
    Else
      InAbs = 0
      WSAREA2 = Worksheets("tmpData").Range("E28").value 'get from somewhere
      If (isMetricIN = True) Then WSAREA2 = WSAREA2 * Ha2Acre
      WSAREA1 = WSAREA2 / 640
    End If
      
  'for any method
  If (UseTC = False) Then
  
   If (MethodTc = 3) Then
     'SIMAS
      GetTc_fromTL
   Else
     TimeCon = GetTimeCon
   End If
  End If
End Sub


Function GetN_UHSteps() As Integer
'Number of steps in the UH


 If MethodUH = 1 Then N = 14
 If MethodUH = 2 Then
   iter_array = Array(10, 10, 13, 14, 15, 17, 19, 20, 25, 30)
   'iter_array = Array(11, 11, 13, 15, 16, 18, 20, 21, 26, 31)
    N = iter_array(MethodUHsub)
 End If
 

 'DeltaT = 2 * TimeCon / (HSteps + 1)
 If MethodUH = 3 Then N = 33 'Curvilinear
 If MethodUH = 4 Then N = 25 'broken Triangle
 
 GetN_UHSteps = N
End Function

Sub Set_UHData_original()
Dim I As Byte
Dim T7 As Double
Dim T0 As Double


 'original procedure
  T0 = 0
  T7 = 5 * DeltaT 'Time to Peak
  Worksheets("testing").Range("C4").value = T7
  
  For I = 1 To 6
   H(I) = 3 * T0 / (4 * T7 ^ 2)
   H(I) = H(I) / 1.002
   T0 = T0 + DeltaT
   Worksheets("testing").Cells(10 + I, 5).value = T0
   Worksheets("testing").Cells(10 + I, 6).value = H(I)
  Next I
 
  For I = 7 To 14
   H(I) = 3 / (4 * T7) * (1 - 0.6 * (T0 - T7) / T7)
   H(I) = H(I) / 1.002
   If H(I) < 0 Then H(I) = 0
   T0 = T0 + DeltaT
   Worksheets("testing").Cells(10 + I, 5).value = T0
  Worksheets("testing").Cells(10 + I, 6).value = H(I)
  Next I
 
  TP_UH = T7
  TB_UH = 8 / 3 * T7
End Sub


Sub Watershed_Storm_Parameters()
Dim cadena As String

Worksheets("testing").Range("C2").value = TimeCon

 'DeltaT = 2 * TimeCon / 15
 DeltaT = 2 * TimeCon / (HSteps + 1)
 DeltaTUH = DeltaT
 Worksheets("testing").Range("C3").value = DeltaT
 
 'replace thus 14 with the new number of steps for the uh
 'NumLines = Round(StrmDur / DeltaT + 2) + 14
 NumLines = Round(StrmDur / DeltaT + 2) + HSteps
 OKTimeTc = True
 
 If (NumLines > maxcoordinate) Then
   OKTimeTc = False
   cadena = "Tc = " & TimeCon & "Use a longer time of concentration"
   MsgBox cadena
 End If
 
 
 If (MethodUH = 1) Then Set_UHData_original
 If (MethodUH = 2) Then get_UHbyType 'variations of the triangular
 If (MethodUH = 3) Then get_CurvilinearUH
 If (MethodUH = 4) Then get_brokenUH
  
End Sub


Function getH(tp, TimeX, b)

If (TimeX <= tp) Then
 getH = TimeX / tp
Else
 getH = (1 + b - TimeX / tp) / b
End If

End Function

Function GetH_broken(tp, TimeX)

 If (TimeX <= tp) Then
  GetH_broken = TimeX / tp '* 5 / 9
 ElseIf (TimeX < 2 * tp) Then
  GetH_broken = (1.6 - 0.6 * TimeX / tp) '* 5 / 9
 Else
  GetH_broken = (0.6667 - 0.1333 * TimeX / tp) '* 5 / 9
 End If
End Function

Sub set_array_SCS_curvilinear()

 TA = Array(0, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.2, 2.4, 2.6, 2.8, 3, 3.2, 3.4, 3.6, 3.8, 4, 4.5, 5)
 HA = Array(0, 0, 0.03, 0.1, 0.19, 0.31, 0.47, 0.66, 0.82, 0.93, 0.99, 1, 0.99, 0.93, 0.86, 0.78, 0.68, 0.56, 0.46, 0.39, 0.33, 0.28, 0.207, 0.147, 0.107, 0.077, 0.055, 0.04, 0.029, 0.015, 0.011, 0.005, 0)

End Sub

Function GetH_Curvilinear(tp, TimeX) As Double
 Dim found As Boolean
 Dim I As Integer
 Dim N As Integer
 Dim Time, Time2
 Dim HA_Value As Double
 Dim DHA As Double
 Dim DTA As Double
 
 HA_Value = 0
 TA = Array(0, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.2, 2.4, 2.6, 2.8, 3, 3.2, 3.4, 3.6, 3.8, 4, 4.5, 5)
 HA = Array(0, 0, 0.03, 0.1, 0.19, 0.31, 0.47, 0.66, 0.82, 0.93, 0.99, 1, 0.99, 0.93, 0.86, 0.78, 0.68, 0.56, 0.46, 0.39, 0.33, 0.28, 0.207, 0.147, 0.107, 0.077, 0.055, 0.04, 0.029, 0.015, 0.011, 0.005, 0)

 
 found = False
 N = 33
 I = 1
 Do While (I < N And found = False)
   Time = TA(I - 1)
   Time2 = TA(I)
   If (TimeX >= Time And TimeX <= Time2) Then
    DHA = HA(I) - HA(I - 1)
    DTA = TA(I) - TA(I - 1)
    DX = TimeX - Time
    If (DTA) > 0 Then HA_Value = (DX * DHA / DTA) + HA(I - 1)
    found = True
   End If
   I = I + 1
 Loop
 
  GetH_Curvilinear = HA_Value
End Function


Function Interpol3(TimeX, Tb, tp, Qp) As Double

 If (TimeX <= tp) Then
  DX = tp
  DY = Qp
  DX2 = TimeX
  DY2 = DX2 * DY / DX
 Else
  DX = Tb - tp
  DY = Qp
  DX2 = Tb - TimeX
  DY2 = DX2 * DY / DX
 End If

 Interpol3 = DY2
End Function

'For the variations of the original
Sub get_CurvilinearUH()

Dim I As Integer
Dim TimeX As Double
Dim tp  As Double
Dim TT As Double
Dim mySum As Double
Dim timefactor As Double
 
 
tp = 5 * DeltaT
TT = 1
TP_UH = tp
TB_UH = 5 * tp
  
Worksheets("testing").Range("C3").value = DeltaT
Worksheets("testing").Range("C4").value = tp
Worksheets("testing").Range("C5").value = TT
 TimeX = 0
 I = 0
 mySum = 0
 timefactor = 5 / TT
 Do While TimeX <= TT
  I = I + 1
  H(I) = GetH_Curvilinear(tp, TimeX * timefactor)
  If (H(I) < 0) Then H(I) = 0
  If (I > 1) Then mySum = mySum + (H(I - 1) + H(I)) / 2 * DeltaT
  Worksheets("testing").Cells(10 + I, 5).value = TimeX
  Worksheets("testing").Cells(10 + I, 6).value = H(I)
  TimeX = TimeX + DeltaT
 Loop
 
 
 myfactor = 1 / mySum
 
 TimeX = 0
 I = 0
 Do While TimeX <= TT
  I = I + 1
  H(I) = GetH_Curvilinear(tp, TimeX * timefactor) * myfactor
  If (H(I) < 0) Then H(I) = 0
  'Worksheets("testing").Cells(10 + i, 5).Value = TimeX
  'Worksheets("testing").Cells(10 + i, 6).Value = H(i)
  TimeX = TimeX + DeltaT
 Loop
 
 HSteps = I
 
End Sub

Sub get_brokenUH()
Dim I As Integer
Dim TimeX As Double
Dim tp  As Double
Dim TT As Double
Dim mySum As Double

tp = 5 * DeltaT
TT = 5 * tp
TP_UH = tp
TB_UH = 5 * tp
  
'Worksheets("testing").Range("C3").value = DeltaT
'Worksheets("testing").Range("C4").value = TP
'Worksheets("testing").Range("C5").value = TT
 TimeX = 0
 I = 0
 mySum = 0
 Do While TimeX <= TT
  I = I + 1
  H(I) = GetH_broken(tp, TimeX)
  If (H(I) < 0) Then H(I) = 0
  If (I > 1) Then mySum = mySum + (H(I - 1) + H(I)) / 2 * DeltaT
  'Worksheets("testing").Cells(10 + i, 5).value = TimeX
  'Worksheets("testing").Cells(10 + i, 6).value = H(i)
  TimeX = TimeX + DeltaT
 Loop
 
 myfactor = 1 / mySum
 
 TimeX = 0
 I = 0
 Do While TimeX <= TT
  I = I + 1
  H(I) = GetH_broken(tp, TimeX) * myfactor
  If (H(I) < 0) Then H(I) = 0
  'Worksheets("testing").Cells(10 + i, 5).Value = TimeX
  'Worksheets("testing").Cells(10 + i, 6).Value = H(i)
  TimeX = TimeX + DeltaT
 Loop
 
 HSteps = I
 
End Sub

'For the variations of the original
Sub get_UHbyType()

 Dim I As Integer
 Dim TimeX As Double
 Dim b As Double
 Dim tp As Double
 Dim Qp As Double
 Dim Tb As Double
 
 b_array = Array(1, 1, 3 / 2, 5 / 3, 2, 7 / 3, 2, 7 / 3, 8 / 3, 3, 4, 5)
 qpf_array = Array(1, 1, 4 / 5, 3 / 4, 2 / 3, 3 / 5, 6 / 11, 1 / 2, 2 / 5, 1 / 3)
 
 tb_tp_array = Array(1, 2, 2.5, 2.67, 3, 3.33, 3.67, 4, 5, 6)
 
 id = MethodUHsub
 b = b_array(id)
 Qp = qpf_array(id)
 'DeltaT = (1 + b) / 5
 
 'added today
 DeltaT = 2 * TimeCon / (HSteps + 1)
 DeltaTUH = DeltaT
 
 tp = 5 * DeltaT
 
 TimeX = 0
 'I = 0
 'Do While TimeX <= b
 ' I = I + 1
 'Tb = DeltaT * HSteps
 Tb = tb_tp_array(id) * tp
 
 'Tb = b + 1
 'Qp = 2 / (b + 1)
 Qp = 2 / Tb
 For I = 1 To HSteps + 1
  'H(I) = getH(TP, TimeX, b) * Qp
  H(I) = Interpol3(TimeX, Tb, tp, Qp)
  ' Modify here
  
  If (MethodUH = 1) Then H(I) = H(I) / 1.002 'SCS Triangle
  If (MethodUH = 2) Then
   If (MethodUHsub = 2) Then H(I) = H(I) / 1.002666666 'tr/tp= 3/2
   If (MethodUHsub = 3) Then H(I) = H(I) / 1.002 'tr/tp= 5/3
   If (MethodUHsub = 5) Then H(I) = H(I) / 1.0012 'tr/tp= 7/3
   If (MethodUHsub = 6) Then H(I) = H(I) / 1.0009090909 'tr/tp= 8/3
  End If
  
  
  If (H(I) < 0) Then H(I) = 0
  'Worksheets("testing").Cells(10 + i, 5).value = TimeX
  'Worksheets("testing").Cells(10 + i, 6).value = H(i)
  TimeX = TimeX + DeltaT
 Next I
 'Loop
 'HSteps = I
 
 TP_UH = tp
 TB_UH = Tb
End Sub




'***** Precipitation Rutines START  ****


'SCS Type-B Storm
Sub SCS_TypeB()
  Dim I As Integer

  For I = 1 To SCSNUM
   P(I) = SCSB_P(I) / 100 * StrmRain
   T(I) = SCSB_T(I) / 6 * StrmDur
  Next I
  NUMDist = SCSNUM
End Sub

'Farmer-Fletcher
Sub Farmer_Fletcher()
Dim I As Integer

 For I = 1 To FFNUM
   P(I) = FarmerF_P(I) / 100 * StrmRain
   T(I) = FarmerF_T(I) / 100 * StrmDur
 Next I
 NUMDist = FFNUM
End Sub

'Uniform
Sub Uniform_Storm()
Dim I As Integer

 For I = 1 To UNUM
   P(I) = Uniform_P(I) / 100 * StrmRain
   T(I) = Uniform_T(I) / 100 * StrmDur
 Next I
NUMDist = UNUM
End Sub


'Custom (Storm Type 4)
 Sub Custom_Storm()
  Dim I As Integer
  
    For I = 1 To NumCust
     P(I) = (p4(I) / 100) * StrmRain
     T(I) = (t4(I) / 100) * StrmDur
    Next I
    NUMDist = NumCust
  End Sub

'Generic (Storm Type 5)

Sub Generic_Storm()

 Dim ix, io, tx, N, dint, tend, np1, F1, t_ As Double
 Dim I As Integer
 
  '{generic storm.. does NOT calculate the general ordinates for t5() and p5()
  'its not really needed here..}
  ix = imax / 100
  io = imin / 100
  tx = itmax / 100

  If tx = 0 Then tx = 0.000001
  If tx = 1 Then tx = 0.999999
  '{ n:= (ix - 1!) / (1! - io);}
   F1 = 1 '{1!}
  N = (ix - F1) / (F1 - io)
  dint = ix - io
  tend = 1 - tx
  np1 = N + 1

  For I = 1 To 101
    t_ = (I - 1) / 100
    T(I) = t_ * StrmDur
    If t_ <= tx Then
      '{ t<tmax  rising storm --------------rising storm leg}

      P(I) = t_ * (io + (dint / np1) * (t_ / tx) ^ N) * StrmRain
      '{ t>tmax  falling storm -------------falling storm leg}
    Else
      ' {p[I]:= 1! - (1! - t) * (io + (dint / np1) * ((1! - t) / tend) ^ n): p(I%) = p(I%) * StrmRain}
      P(I) = F1 - (F1 - t_) * (io + (dint / np1) * ((F1 - t_) / tend) ^ N)
      P(I) = P(I) * StrmRain
    End If
  Next I

  NUMDist = 101
End Sub


Function Interpolate_P(xTime As Double) As Double
 'given an array of Precip distribution
 'interpolat P @ specific time
 
 'NUMDist: is the max number of elements in array
 'P(): precipitation array
 'T(): time array
 
 Dim P1 As Double
 Dim I As Integer
 
 
 P1 = P(NUMDist)
 If xTime < T(NUMDist) Then
    I = 1
    Do While (T(I) < xTime)
      I = I + 1
    Loop
    If I > 1 Then 'This was added just for me
      P1 = P(I - 1) + (P(I) - P(I - 1)) * (xTime - T(I - 1)) / (T(I) - T(I - 1))
    Else
     P1 = 0
    End If
 End If
 
  Interpolate_P = P1
End Function


Function Get_PIntensity(xTime As Double) As Double
 Dim P1 As Double
 Dim P2 As Double
 Dim TPrev As Double
 
 TPrev = xTime - DeltaT
 P1 = Interpolate_P(TPrev)
 P2 = Interpolate_P(xTime)
 
 Get_PIntensity = (P2 - P1) / DeltaT
End Function


'***** Precipitation Rutines END  ****


Function GetQ_fromP_Ia(P, Ia) As Double
Dim Q As Double

 If P < Ia Then
   Q = 0
 Else
   If MethodRainfallE = 1 Then
     Q = (P - Ia) ^ 2 / (P + 4 * Ia)
    Else
     Q = (P - Ia) ^ 2 / (P + 19 * Ia)
    End If
   
 End If
 
  GetQ_fromP_Ia = Q
End Function

'Partial Area CN and Q and Contrib Area
Sub WtCNQ(xTime, xPrecip)
 
 Dim J As Integer
 Dim SumQ As Double
 Dim Ia_ As Double
 Dim qpart As Double
 
 SumQ = 0
 
 Contrib = 0
 p_ = P1
 For J = 1 To NumHRU
  Ia_ = Ia(J)
  If p_ <= Ia_ Then
   qpart = 0
  Else
   qpart = GetQ_fromP_Ia(p_, Ia_)
   
   SumQ = SumQ + qpart * fct(J)
   Contrib = Contrib + fct(J)
  End If
 Next J
 
 Q = SumQ
 
 
 'for intensity calculations
 Dim Intensity As Double
 Dim P0 As Double
 Dim TPrev  As Double
 
 TPrev = xTime - DeltaT
 If (TPrev >= 0) Then
    P0 = Interpolate_P(TPrev)
    Intensity = (xPrecip - P0) / DeltaT
    If (Intensity > myImax) Then myImax = Intensity
 End If
 
End Sub


Sub MU_GetQ_Contrib(xTime, xPrecip)
  Dim Intensity As Double
  Dim P0 As Double
  Dim TPrev  As Double
  Dim F As Double
  Dim deltaQ As Double
  
  Contrib = 0
  deltaQ = 0
  TPrev = xTime - DeltaT
  If (TPrev >= 0) Then
    P0 = Interpolate_P(TPrev)
    Intensity = (xPrecip - P0) / DeltaT
    If (Intensity > myImax) Then myImax = Intensity
    F = Mu * (1 - Exp(-1 * Intensity / Mu))
    If (Intensity > F) Then
      deltaQ = (Intensity - F) * DeltaT
      Else
      deltaQ = 0
    End If
    Contrib = 1 - Exp(-1 * Intensity / Mu)
  End If
  Q = CumQ + deltaQ
End Sub


Sub PHI_GetQ_Contrib(xTime, xPrecip)
  Dim Intensity As Double
  Dim P0 As Double
  Dim TPrev  As Double
  Dim F As Double
  Dim deltaQ As Double
  
  Contrib = 0
  deltaQ = 0
  TPrev = xTime - DeltaT
  If (TPrev >= 0) Then
    P0 = Interpolate_P(TPrev)
    Intensity = (xPrecip - P0) / DeltaT
    If (Intensity > myImax) Then myImax = Intensity
    If (Intensity > PHI) Then
      deltaQ = (Intensity - PHI) * DeltaT
      Contrib = 1
    End If
  End If
  Q = CumQ + deltaQ
End Sub

Sub FDist_GetQ_Contrib(xTime, xPrecip)
  Dim Intensity As Double
  Dim P0 As Double
  Dim TPrev  As Double
  Dim deltaQ As Double
  Dim J As Integer
  Dim SumQ As Double
  
  Contrib = 0
  deltaQ = 0
  
  TPrev = xTime - DeltaT
  If (TPrev >= 0) Then
    P0 = Interpolate_P(TPrev)
    Intensity = (xPrecip - P0) / DeltaT
     If (Intensity > myImax) Then myImax = Intensity
  End If
  
  For J = 1 To NumHRU
    If xPrecip > hru(J, 2) Then
     qpart = fct(J) * (xPrecip - hru(J, 2))
     Contrib = Contrib + fct(J)
    Else
      qpart = 0
    End If
    deltaQ = deltaQ + qpart
  Next J
   
  Q = deltaQ
End Sub

Sub Violent_GetQ_Contrib(xTime, xPrecip)
  Dim Intensity As Double
  Dim P0 As Double
  Dim TPrev  As Double
  Dim F As Double
  Dim deltaQ As Double
  
  Contrib = 0
  deltaQ = 0
  TPrev = xTime - DeltaT
  If (TPrev >= 0) Then
    P0 = Interpolate_P(TPrev)
    Intensity = (xPrecip - P0) / DeltaT
    If (Intensity > myImax) Then myImax = Intensity
    
    If (xPrecip <= ComplacentA) Then
      deltaQ = ComplacentB1 * xPrecip
      Contrib = ComplacentB1
    Else
      deltaQ = ComplacentA * ComplacentB1 + ComplacentB2 * (xPrecip - ComplacentA)
      Contrib = ComplacentB2
    End If
    
  End If
  Q = deltaQ
End Sub

Sub LinearC_GetQ_Contrib(xTime, xPrecip)
  Dim Intensity As Double
  Dim P0 As Double
  Dim TPrev  As Double
  Dim F As Double
  Dim deltaQ As Double
  
  Contrib = 0
  deltaQ = 0
  TPrev = xTime - DeltaT
  If (TPrev >= 0) Then
    P0 = Interpolate_P(TPrev)
    Intensity = (xPrecip - P0) / DeltaT
    If (Intensity > myImax) Then myImax = Intensity
    
    deltaQ = LinFracC * xPrecip
    Contrib = 1
  End If
  Q = deltaQ
End Sub

Sub Calculate_Q_ContribArea(xTime, xPrecip)

   Contlast = Contrib
   If (usingCN = True) Then
    WtCNQ xTime, xPrecip
    Else
     If (MethodRainfallE = 5) Then MU_GetQ_Contrib xTime, xPrecip 'Infiltration capacities MU
     If (MethodRainfallE = 4) Then PHI_GetQ_Contrib xTime, xPrecip 'Infiltration PHI index
     If (MethodRainfallE = 3) Then FDist_GetQ_Contrib xTime, xPrecip ' F distribution
     If (MethodRainfallE = 7) Then LinearC_GetQ_Contrib xTime, xPrecip ' Constant C
     If (MethodRainfallE = 8) Then Violent_GetQ_Contrib xTime, xPrecip ' Constant C
    End If
End Sub



Sub Calculate_Ia_fraction()
Dim J As Integer
Dim s As Double

 For J = 1 To NumHRU
   s = 1000 / hru(J, 2) - 10 'S
   If MethodRainfallE = 1 Then
    'ia(J) = 200 / hru(J, 2) - 2
     Ia(J) = 0.2 * s
   Else
    s = 1.33 * s ^ (1.15)
    Ia(J) = 0.05 * s
  End If
  
  fct(J) = hru(J, 1) / WSAREA2
 Next J
End Sub

'For F Distribution Method of Rainfall Excess
Sub Calculate_fct_fraction()
Dim J As Integer
Dim myArea As Double

 myArea = 0
 For J = 1 To NumHRU
   myArea = myArea + hru(J, 1)
 Next J
 
 For J = 1 To NumHRU
  fct(J) = hru(J, 1) / myArea
 Next J
End Sub



Sub AddBorder_CNTable()

    Sheets("SummaryTable").Select
    Range("B48:H48").Select
    Selection.Borders(xlDiagonalDown).LineStyle = xlNone
    Selection.Borders(xlDiagonalUp).LineStyle = xlNone
    Selection.Borders(xlEdgeLeft).LineStyle = xlNone
    With Selection.Borders(xlEdgeTop)
        .LineStyle = xlContinuous
        .ColorIndex = 0
        .TintAndShade = 0
        .Weight = xlThin
    End With
    Selection.Borders(xlEdgeBottom).LineStyle = xlNone
    Selection.Borders(xlEdgeRight).LineStyle = xlNone
    Selection.Borders(xlInsideVertical).LineStyle = xlNone
    Selection.Borders(xlInsideHorizontal).LineStyle = xlNone
    Range("B49:H49").Select
    Selection.Borders(xlDiagonalDown).LineStyle = xlNone
    Selection.Borders(xlDiagonalUp).LineStyle = xlNone
    Selection.Borders(xlEdgeLeft).LineStyle = xlNone
    Selection.Borders(xlEdgeTop).LineStyle = xlNone
    With Selection.Borders(xlEdgeBottom)
        .LineStyle = xlContinuous
        .ColorIndex = 0
        .TintAndShade = 0
        .Weight = xlThin
    End With
    Selection.Borders(xlEdgeRight).LineStyle = xlNone
    Selection.Borders(xlInsideVertical).LineStyle = xlNone
    Selection.Borders(xlInsideHorizontal).LineStyle = xlNone
    Range("F48:H48").Select
    Selection.Borders(xlDiagonalDown).LineStyle = xlNone
    Selection.Borders(xlDiagonalUp).LineStyle = xlNone
    Selection.Borders(xlEdgeLeft).LineStyle = xlNone
    With Selection.Borders(xlEdgeTop)
        .LineStyle = xlContinuous
        .ColorIndex = 0
        .TintAndShade = 0
        .Weight = xlThin
    End With
    With Selection.Borders(xlEdgeBottom)
        .LineStyle = xlContinuous
        .ColorIndex = 0
        .TintAndShade = 0
        .Weight = xlThin
    End With
    Selection.Borders(xlEdgeRight).LineStyle = xlNone
    Selection.Borders(xlInsideVertical).LineStyle = xlNone
    Selection.Borders(xlInsideHorizontal).LineStyle = xlNone
    Range("A3").Select
End Sub


Sub Out_CN_HR()
Dim J As Integer
Dim SName As String
Dim zzz As Double
Dim zzz1 As Double
Dim p_ As Double
Dim Q As Double
Dim d As Double
Dim fc As Double
Dim Rs As Integer

Rs = 49 'Row Start
SName = "SummaryTable"
 
 
 Worksheets(SName).Range("B48").value = "CN"
 Worksheets(SName).Range("C48").value = "CN"
 'Worksheets(SName).Range("D48").value = "Ia"
 Worksheets(SName).Range("D48").value = "HU"
 
 Worksheets(SName).Range("E48").value = "Area"
 Worksheets(SName).Range("G48").value = "Event Runoff"
 Worksheets(SName).Range("B49").value = "'(0.20)"
 Worksheets(SName).Range("C49").value = "'(0.05)"
 'Worksheets(SName).Range("D49").value = "(in)"
 Worksheets(SName).Range("D49").value = "(Desc)"
 Worksheets(SName).Range("E49").value = "(acres)"
 Worksheets(SName).Range("F49").value = "Source (in)"
 Worksheets(SName).Range("G49").value = "(Ac-ft)"
 Worksheets(SName).Range("H49").value = "(Pct)"
 AddBorder_CNTable
 
 p_ = StrmRain
 'q = q0(3)
 'd = q / p_
 
  For J = 1 To NumHRU
    qf(J) = GetQ_fromP_Ia(p_, Ia(J))
    
    If p_ < Ia(J) Then qf(J) = 0
    zzz = qf(J) * hru(J, 1) / 12
    zzz1 = zzz * 100 / TotRoaf
    
    Worksheets(SName).Cells(Rs + J, 2).value = hru(J, 2)
    Worksheets(SName).Cells(Rs + J, 3).value = GetCN5(hru(J, 2))
    'Worksheets(SName).Cells(Rs + J, 4).value = Ia(J)
    Worksheets(SName).Cells(Rs + J, 4).value = Worksheets("CNS").Cells(5 + J, 6).value
    
    Worksheets(SName).Cells(Rs + J, 5).value = hru(J, 1)
    Worksheets(SName).Cells(Rs + J, 6).value = qf(J)
    Worksheets(SName).Cells(Rs + J, 7).value = zzz
    Worksheets(SName).Cells(Rs + J, 8).value = zzz1

  Next J
    J = J + 1
    Worksheets(SName).Cells(Rs + J, 2).value = CN
    Worksheets(SName).Cells(Rs + J, 3).value = CN5
    Worksheets(SName).Cells(Rs + J, 5).value = WSAREA2
    Worksheets(SName).Cells(Rs + J, 7).value = TotRoaf
    Worksheets(SName).Cells(Rs + J, 8).value = "100.0"
  
End Sub



Function Generate_Synthetic_RunOff() As Boolean
 Dim J, k, I, I1 As Integer
 Dim Q1, Q2, Q3, S1, S2 As Double
 Dim CharX As String
 Dim SName As String
 Dim stable As String
 Dim rowsdata As Integer
 Dim IniRow As Integer
 Dim CO_in As Double
 Dim CO_acft As Double
 Dim tmpval As Double
 Dim firstQ As Boolean
 Dim TimeRunoff_Start As Double
 Dim TimeRunoff_End As Double
 Dim Runoff_Started As Boolean
 Dim TimeRE_Start As Double
 Dim TimeRE_End As Double
 Dim RE_Started As Boolean
 Dim RE2 As Double '2nd option how to calculate Rainfall Excess Duration
 Dim CumOutflow As Double
 Dim MaxTransient As Double
 Dim TimeMaxTrans As Double
 
 
 Dim Ia_catch_time As Double
 Dim Ia_catch_value As Double
 Dim Ia_catch_found As Boolean
 Dim previusP As Double
 
 Dim xfc As Double
 
 xfc = 1 ' 1 / 1.00198
 
 
 previousP = 0
 Ia_catch_time = 0
 Ia_catch_value = 0
 Ia_catch_found = False
 
 
 
 IniRow = 9 'Where to start putting data

 firstQ = False
 CumQ = 0
 MaxContribArea = 0
 
 CO_in = 0
 CO_acft = 0
 myImax = 0
 Runoff_Started = False
 TimeRunoff_Start = 0
 TimeRunoff_End = 0
 DTWROFF = 0 'DeltaT with Runoff
 RE_Started = False
 TimeRE_Start = 0
 TimeRE_End = 0
 RE2 = 0
 CumOutflow = 0
 MaxTransient = 0
 TimeMaxTrans = 0
 
 SName = "table"
 stable = "SummaryTable"
 Worksheets(SName).Range("B10:J10").value = 0
 rowsdata = 0
 
 CharX = ","
 If (usingCN = True) Then Calculate_Ia_fraction
 If (MethodRainfallE = 3) Then Calculate_fct_fraction
 
 
 For k = 1 To 6
  q0(k) = 0
 Next k
 
 PHYDCFS = 0
 PHYDTIM = 0
 ORDCNT = 0
 I1 = 0
 T1 = 0
 Contrib = 0
 
 Do While (I1 < (NumLines + 1)) And (QCHK = True)
  P1 = Interpolate_P(T1)
  Q = 0
  'Get_PIntensity(xtime As Double) As Double
  Calculate_Q_ContribArea T1, P1 'For any method, it returns Q and Contrib
  If (Contrib > MaxContribArea) Then MaxContribArea = Contrib
  
  Q1 = Q - q0(3)
  q0(4) = Q1
  Q2 = 0
  S1 = Q1
  CumQ = CumQ + Q1
  
  'J=14
  J = HSteps
  'old If (I1 <= 14) Then J = I1
  If (I1 <= HSteps) Then J = I1
  'If (J < 2) Then J = 2
  For I = 1 To J
    S2 = S1
    Q2 = Q2 + H(I) * S2
    S1 = S0(I)
    S0(I) = S2
  Next I
  Q3 = WSAREA2 * Q2
  ORDCNT = ORDCNT + 1
  'QTIM(ORDCNT) = q0(1) 'Time hr
  'QPIN(ORDCNT) = q0(2) 'P in
  'QRIN(ORDCNT) = q0(3) 'R in
  'QIPH(ORDCNT) = q0(5) 'Q in/h
  'QCFS(ORDCNT) = q0(6) 'Q cfs
  
  q0(1) = T1
  q0(2) = P1
  q0(3) = Q
  q0(5) = Q2
  q0(6) = Q3
  
  
  'If Q <> 0 Then
    'Output data
   If (Q > 0) Then firstQ = True
   
  
   If (q0(4) > 0.00005) Then RE2 = RE2 + 1
   
   'If (firstQ = True) Then
    rowsdata = rowsdata + 1
    'Worksheets(SName).Cells(IniRow + rowsdata, 2).Value = q0(1) 'time
    Worksheets(SName).Cells(IniRow + rowsdata, 2).value = T1 'time
    
    'Worksheets(SName).Cells(IniRow + rowsdata, 3).Value = q0(2) 'Cum rainfall
    Worksheets(SName).Cells(IniRow + rowsdata, 3).value = setUSOUT(P1, 25.4) 'Cum rainfall
    
    'Worksheets(SName).Cells(IniRow + rowsdata, 4).Value = q0(3) 'Cum rainfall excess
    Worksheets(SName).Cells(IniRow + rowsdata, 4).value = setUSOUT(CumQ, 25.4) 'Cum rainfall excess
    
    Worksheets(SName).Cells(IniRow + rowsdata, 5).value = Contlast * 100  'Contributing area
    Worksheets(SName).Cells(IniRow + rowsdata, 6).value = setUSOUT(q0(4), 25.4) 'incremental runoff
    tmpval = q0(5) * DeltaT 'outflow rate (iph) to convert to inches
    'tmpval = tmpval + Worksheets(SName).Cells(10 + rowsdata - 1, 7).Value 'to make it cumulative
    CumOutflow = CumOutflow + tmpval
    
    Worksheets(SName).Cells(IniRow + rowsdata, 7).value = setUSOUT(CumOutflow, 25.4) 'cum outflow in inches
    tmpval = CumOutflow * WSAREA1 * 640 / 12
    Worksheets(SName).Cells(IniRow + rowsdata, 8).value = setUSOUT(tmpval, 0.123353) 'cum outflow in acre ft
    Worksheets(SName).Cells(IniRow + rowsdata, 9).value = setUSOUT(q0(5) * xfc, 25.4) 'outflow rate (iph)
    Worksheets(SName).Cells(IniRow + rowsdata, 10).value = setUSOUT(q0(6) * 1.008333, 0.3048 ^ 3) 'outflow rate (cfs)
    
    If ((CumQ > 0) And (Ia_catch_found = False)) Then
      Ia_catch_found = True
      Ia_catch_time = T1
      Ia_catch_value = (P1 + previousP) / 2
    End If
    
    previousP = P1
    
    'Transient storage in inches
    tmpval = CumQ - CumOutflow
    If (tmpval > MaxTransient) Then
      MaxTransient = tmpval
      TimeMaxTrans = T1
    End If
    
    If (q0(6) > 0) Then
     DTWROFF = DTWROFF + 1
     If (Runoff_Started = False) Then
       TimeRunoff_Start = q0(1)
       Runoff_Started = True
     End If
    Else
      If (Runoff_Started = True And TimeRunoff_End = 0) Then
       TimeRunoff_End = q0(1)
      End If
    End If
  'End If
  'If Not (q0(6) < PHYDCFS) Then
  If (q0(6) > PHYDCFS) Then
    PHYDCFS = q0(6)
    PHYDTIM = T1 'q0(1)
    PHYDIPH = q0(5)
   
  End If
  'q0(1) = T1
  'q0(2) = P1
  'q0(3) = Q
  'q0(5) = Q2
  'q0(6) = Q3
  
  T1 = T1 + DeltaT
  I1 = I1 + 1
 Loop
 QCHK = True
 TotRoaf = q0(3) * 640 / 12 * WSAREA1
 
 
 Worksheets("tmpData").Range("C35").value = rowsdata
 Worksheets("tmpData").Range("C36").value = DeltaT
 Worksheets("tmpData").Range("C37").value = PHYDCFS
 Worksheets("tmpData").Range("C38").value = TotRoaf
 Worksheets("tmpData").Range("C39").value = StrmRain
 Worksheets("tmpData").Range("C40").value = StrmDur
 
 Worksheets(SName).Cells(IniRow + rowsdata + 2, 6).value = " * * * *  END OF RUNOFF HYDROGRAPH RESULTS  * * * * "
 
 
 Worksheets(stable).Range("E13").value = WSAREA1 * 640
 
 'Worksheets(stable).Range("P18").Value = CN5
 Worksheets(stable).Range("E15").value = TimeCon
 Worksheets(stable).Range("E16").value = DeltaTUH
 Worksheets(stable).Range("E17").value = TP_UH

 Worksheets(stable).Range("E18").value = TB_UH
 Worksheets(stable).Range("G18").value = TB_UH * 60
 
 
 Dim tmpValue As Double
 Worksheets(stable).Range("E23").value = q0(3) 'total runoff
 tmpValue = q0(3) * 25.4 'total run off in mm
 Worksheets(stable).Range("G23").value = tmpValue
 Worksheets(stable).Range("E24").value = TotRoaf
 tmpValue = tmpValue * 10 * WSAREA1 * 640 / 2.47105 'm^3
 Worksheets(stable).Range("G24").value = TotRoaf * 0.123353 'm^3
 
 'temporary
 PHYDCFS = 1.008333 * PHYDIPH * WSAREA2
 Worksheets(stable).Range("E25").value = PHYDCFS 'Peak flow
 Worksheets(stable).Range("G25").value = PHYDCFS * 0.3048 ^ 3
 Worksheets(stable).Range("E26").value = PHYDIPH
 Worksheets(stable).Range("G26").value = PHYDIPH * 25.4
 Worksheets(stable).Range("E27").value = PHYDTIM
 If (PHYDIPH <= 0) Then
   Worksheets(stable).Range("E32").value = -1
   Else
 Worksheets(stable).Range("E32").value = q0(3) / (T1 * PHYDIPH) 'hydrograph shape factor
 End If
 
 
 If (myImax = 0) Then myImax = 1
 Worksheets(stable).Range("E28").value = PHYDIPH / myImax 'CFactor
 Worksheets(stable).Range("E29").value = q0(3) / StrmRain 'Runoff ratio
 
 If (q0(3) > 0) Then
 tmpValue = GetCN_PQ(StrmRain, q0(3)) 'CN is calculated backwards
 Worksheets(stable).Range("E30").value = tmpValue ' Effective CN
 Dim CNAfter As Double
 CNAfter = GetCN2After(StrmRain, tmpValue)
 
 Worksheets(stable).Range("E31").value = CNAfter
 Worksheets(stable).Range("H31").value = GetCN5(CNAfter)
 
 'tmpValue = GetCN5(tmpValue)
 tmpValue = GetCN5_QP(q0(3), StrmRain)
 Worksheets(stable).Range("H30").value = tmpValue ' Effective CN 0.05
 Else
  Worksheets(stable).Range("E30").value = "N/A"
  Worksheets(stable).Range("H30").value = "N/A"
  Worksheets(stable).Range("E31").value = "N/A"
 End If
 Worksheets(stable).Range("E33").value = RE2 * DeltaT
 'Worksheets(stable).Range("E32").Value = TimeRE_End - TimeRE_Start 'Duration of Rainfall Excess
 'Worksheets(stable).Range("G32").Value = TimeRE_Start
 'Worksheets(stable).Range("H32").Value = TimeRE_End
 
 Worksheets(stable).Range("E34").value = DTWROFF * DeltaT 'TimeRunoff_End - TimeRunoff_Start 'Duration of Runoff
 Worksheets(stable).Range("E35").value = (StrmRain - q0(3)) / StrmDur 'Effective Loss Rate (P-Q)/storm duration
 
 Worksheets(stable).Range("E41").value = MaxContribArea * 100 'Max Contrib Area
 Worksheets(stable).Range("E42").value = MaxContribArea * WSAREA1 * 640 'Acres
 Worksheets(stable).Range("G42").value = MaxContribArea * WSAREA1 * 640 / 2.4710538147 'Ha
 
 
 Worksheets(stable).Range("E38").value = MaxTransient 'Maximum transient storage (in)
 Worksheets(stable).Range("G38").value = MaxTransient * 25.4 'in (mm)
 Worksheets(stable).Range("E39").value = TimeMaxTrans  'time of max
 
 
 Worksheets("table").Range("I4").value = ReportTime
 
 If (usingCN = True) Then
   'Worksheets(stable).Range("E21").Value = CN
   Worksheets(stable).Range("E22").value = InAbs
   Out_CN_HR
 End If
 
 If (MethodRainfallE = 4) Then 'for PhiIndex Method
   Worksheets(stable).Range("E22").value = Ia_catch_value
 End If
 
 
 If (rowsdata > 1) Then
   Change_Plot1 rowsdata, isMetricOUT
   Sheet4.Update_Transient
   Generate_Synthetic_RunOff = True
 Else
   Generate_Synthetic_RunOff = False
 End If
End Function


Function GetIa_DistributedInfil()
Dim F As Double
Dim MinF As Double

MinF = 100
 
 For I = 6 To 39
  F = Worksheets("DistriF").Cells(I, 5).value
  If (F > 0) Then
   If (F < MinF) Then
     MinF = F
    End If
  End If
 Next I
 
  
 If (MinF = 100) Then
  MinF = 0
 End If
  
GetIa_DistributedInfil = MinF
End Function

Sub Display_methods()
Dim Cad As String
Dim stable As String
stable = "SummaryTable"
  
  'Operator
  Worksheets(stable).Range("H4").value = ReportTime
  Worksheets(stable).Range("G5").value = "Operator: " & Worksheets("main").Range("N3").value
  Worksheets("table").Range("J5").value = "Operator: " & Worksheets("main").Range("N3").value
  
  If (usingCN = True) Then
   Worksheets(stable).Range("H45").value = ReportTime
   Worksheets(stable).Range("H46").value = "Operator: " & Worksheets("main").Range("N3").value
  End If
  
  'Rainfall Excess
  Cad = "Curve Number, Average CN(0.20)= " & Format(CN, "#,##0.00")
  
  
  
  If MethodRainfallE = 2 Then Cad = "Curve Number (.05), Average CN0.5= " & Format(CN5, "#,##0.00")
  If MethodRainfallE = 4 Then
   Cad = "Constant Loss Rate Phi-Index, phi=" & Format(PHI, "#,##0.00") & " in/hr (" & Format((PHI * 25.4), "#,##0.00") & " mm/hr)"
  End If
  If MethodRainfallE = 3 Then Cad = "Distributed Loss (depth)"
  If MethodRainfallE = 5 Then
    Cad = "Infiltration Distributed Capacities mu=" & Format(Mu, "#,##0.00") & " in/hr (" & Format((Mu * 25.4), "#,##0.00") & " mm/hr)"
  End If
  If MethodRainfallE = 6 Then Cad = "Green-Ampt"
  If MethodRainfallE = 7 Then
    Cad = "Constant Fraction C =" & LinFracC
  End If
  If MethodRainfallE = 8 Then
    Cad = "Complacet-Violent b1=" & ComplacentB1 & "  b2=" & ComplacentB2 & " a=" & ComplacentA & " in/hr"
  End If
  Worksheets(stable).Range("E7").value = Cad
  
  
  'Rainfall
  Worksheets(stable).Range("E8").value = StrmRain
  Worksheets(stable).Range("G8").value = (StrmRain * 25.4)
  Worksheets(stable).Range("E9").value = StrmDur
  
  'Storm Distribution
  Worksheets(stable).Range("C11:K11").value = ""
  Cad = "NEH4B"
  If (StrmType = 2) Then Cad = "Farmer-Fletcher"
  If (StrmType = 3) Then Cad = "Uniform"
  If (StrmType = 4) Then Cad = "Custom " & Worksheets("cstorm").Range("E6").value
  If (StrmType = 5) Then
    Worksheets(stable).Range("D11").value = "imin (% of mean) : "
    Worksheets(stable).Range("E11").value = imin
    Worksheets(stable).Range("G11").value = "imax (% of mean) : "
    Worksheets(stable).Range("H11").value = imax
    Worksheets(stable).Range("I11").value = "time imax : "
    Worksheets(stable).Range("J11").value = itmax
    Cad = "Generic " & Worksheets("tmpData").Range("N4").value
  End If
  Worksheets(stable).Range("E10").value = Cad
  
  'Unit Hydrograph
  Cad = "Simple Triangular Unit Hydrograph"
  If (MethodUH = 2) Then
   Cad = "Variable Triangular Unit Hydrograph - HF= "
   If MethodUHsub = 1 Then Cad2 = "645.33"
   If MethodUHsub = 2 Then Cad2 = "516.27"
   If MethodUHsub = 3 Then Cad2 = "484"
   If MethodUHsub = 4 Then Cad2 = "430.22"
   If MethodUHsub = 5 Then Cad2 = "387.20"
   If MethodUHsub = 6 Then Cad2 = "352"
   If MethodUHsub = 7 Then Cad2 = "322.67"
   If MethodUHsub = 1 Then Cad2 = "258.13"
   If MethodUHsub = 1 Then Cad2 = "215.11"
   Cad = Cad & Cad2
  End If
  
  If (MethodUH = 4) Then Cad = "Broken Triangle"
  If (MethodUH = 3) Then Cad = "SCS Dimensionless Curvilinear"
  Worksheets(stable).Range("E12").value = Cad
  
 
  'Area
  Worksheets(stable).Range("G13").value = "=(SummaryTable!E13)/ 2.4710538147"
  
  
  'Time of Concentration
  Cad = "Given"
  If (UseTC = False) Then
    Cad = Module1.getName_Tc & " Equation"
    If (MethodTc = 3) Then
    Cad = Cad & " (Time Lag = " & Format(TimeLag, "#,##0.00") & " hr )"
    End If
  End If
  Worksheets(stable).Range("E14").value = Cad
  Worksheets(stable).Range("F15").value = "hrs"
  Worksheets(stable).Range("G15").value = TimeCon * 60
  
  'Output
  TmpIa = 0
  
  If (MethodRainfallE = 3) Then
   'Distributed F
    TmpIa = GetIa_DistributedInfil()
  End If
  
  If (MethodRainfallE = 8) Then
   'violent
   If (ComplacentB1 = 0) Then
   TmpIa = ComplacentA
   End If
  End If
  
 ' Worksheets(stable).Range("E22").value = "0" 'Ia
  Worksheets(stable).Range("E22").value = TmpIa
  
  Worksheets(stable).Range("G22").value = "=(SummaryTable!E22)* 25.4"
  
  
  'Set Labels for Big Table
  stable = "table"
  Dim UnitLabelL As String
  Dim UnitLabelR As String
  Dim UnitLabelAL As String
  Dim UnitLabelR2 As String
  
  
  If (isMetricOUT = True) Then
   UnitLabelL = "(mm)"
   UnitLabelAL = "(ha-m)"
   UnitLabelR = "(mm/h)"
   UnitLabelR2 = "(cms)"
  Else
   UnitLabelL = "(in)"
   UnitLabelAL = "(acre-ft)"
   UnitLabelR = "iph"
   UnitLabelR2 = "(cfs)"
  End If
  
  Worksheets(stable).Range("C9").value = UnitLabelL
  Worksheets(stable).Range("D9").value = UnitLabelL
  Worksheets(stable).Range("F9").value = UnitLabelL
  Worksheets(stable).Range("G9").value = UnitLabelL
  Worksheets(stable).Range("H9").value = UnitLabelAL 'acre ft
  Worksheets(stable).Range("I9").value = UnitLabelR 'rate
  Worksheets(stable).Range("J9").value = UnitLabelR2 'cfs
End Sub



'Main SubRoutine
Function RunHydrograph() As Boolean
Dim isOK As Boolean

isOK = False
  'isMetricIN = (Worksheets("main").Range("F11").value = 1)
  'isMetricOUT = (Worksheets("main").Range("F12").value = 1)
   isMetricOUT = Module1.isMetric_OUT()
   isMetricIN = Module1.isMetric_IN()
   
  
  Worksheets("table").Range("B10:K2500").value = "" 'Table calculations
  Worksheets("SummaryTable").Range("A44:I100").value = ""   'Curve Number Summary
  Sheets("SummaryTable").Select
  Range("B44:H53").Select
    Selection.Borders(xlDiagonalDown).LineStyle = xlNone
    Selection.Borders(xlDiagonalUp).LineStyle = xlNone
    Selection.Borders(xlEdgeLeft).LineStyle = xlNone
    Selection.Borders(xlEdgeTop).LineStyle = xlNone
    Selection.Borders(xlEdgeBottom).LineStyle = xlNone
    Selection.Borders(xlEdgeRight).LineStyle = xlNone
    Selection.Borders(xlInsideVertical).LineStyle = xlNone
    Selection.Borders(xlInsideHorizontal).LineStyle = xlNone
    Selection.ClearContents
  
  
  'add cleaning for summary
  ReportTime = Now()
  Sheets("output").Range("G2").value = ReportTime
  GotoWait ReportTime
  take_sheet_data
  set_arrays_storm
  HSteps = GetN_UHSteps 'depending on Unit Triangular Shape
  
  
 
  If (StrmType = 1) Then SCS_TypeB
  If (StrmType = 2) Then Farmer_Fletcher
  If (StrmType = 3) Then Uniform_Storm
  If (StrmType = 4) Then Custom_Storm
  If (StrmType = 5) Then Generic_Storm


 QCHK = True
 Initial_Parameters
 If CN = 0 Then CN = 0.1
 Watershed_Storm_Parameters
 If (OKTimeTc = True) Then
   Display_methods
   isOK = Generate_Synthetic_RunOff
 End If
 
 RunHydrograph = isOK
End Function

Sub RunAnalysis()
 If (RunHydrograph = True) Then
    'Module1.GotoSummaryTable
    'Module1.GotoOutput
   Else
     Module1.GotoMain
  End If
End Sub



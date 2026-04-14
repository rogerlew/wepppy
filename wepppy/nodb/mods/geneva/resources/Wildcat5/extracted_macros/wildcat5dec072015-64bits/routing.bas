Attribute VB_Name = "routing"
'Routing Module
Const M2Ft = 1 / 0.3048, Ha2Acre = 2.4709661, MM2In = 1 / 25.4


Dim SpillCoeff As Double
Dim SpillLength As Double
Dim ReservoirArea As Double
Dim Sinterp As Double
Dim Qinterp As Double

Dim DQ, DDT, QOP, HP, QPP, TotRoaf, StrmRain, StrmDur, DT
Dim LH(2000), QT(2000), ST(2000), QR(2000), H(2000)
Dim NumberData As Integer
Dim AdditionalIters As Integer

Dim isThisMetric As Boolean


Function export_hyd(FName)
  Dim SName As String
  Dim NRows As Integer
  Dim myDeltaT
  Dim myQCFS
  Dim found As Boolean
  Dim StrmRain
  Dim StrmDur
  Dim TotRoaf
  Dim NHyd As Integer
  
  
  
  SName = "table"
  NumberData = Worksheets("storm").Range("AR1").value
  DDT = Worksheets("storm").Range("AR2").value 'Delta T
  DT = DDT * 3600
  
  QPP = Worksheets("storm").Range("AR3").value 'QPFS
  TotRoaf = Worksheets("storm").Range("AR4").value
  StrmRain = Worksheets("storm").Range("AR5").value
  StrmDur = Worksheets("storm").Range("AR6").value
  
  Open FName For Output As #1
  NHyd = 0
  
  found = False
  For I = 2 To NumberData + 2
   myDeltaT = Worksheets(SName).Cells(7 + I, 2).value
   myQCFS = Worksheets(SName).Cells(7 + I, 8).value
   If (myQCFS > 0 And found = False) Then
    found = True
    NHyd = NumberData - I
    Write #1, NHyd
    Write #1, myDeltaT
    Write #1, 0
   End If
   
   If (found) Then
    Write #1, myQCFS
   End If
  Next I
  
  Write #1, StrmRain, StrmDur
  Close #1
End Function



Function GetH_Spillway(Q) As Double
 If Q >= 0 Then
 GetH_Spillway = (Q / (SpillCoeff * SpillLength)) ^ (2 / 3)
 Else
  GetH_Spillway = 0
 End If
End Function

Sub Build_Storage_Table()
 Dim Hx As Double
 Dim J As Integer
 DQ = QPP / 50
 For J = 1 To 53
   QT(J) = (J - 1) * DQ
   Hx = GetH_Spillway(QT(J))
   ST(J) = Hx * ReservoirArea
   LH(J) = ST(J) / DT + QT(J) / 2
 Next J
End Sub

Sub Interpolation(xvalue As Double)
Dim PROP As Double
Dim k As Integer

 
  If xvalue > 0 Then
    k = 2
    Do While (xvalue >= LH(k))
     k = k + 1
    Loop
     PROP = (xvalue - LH(k - 1)) / (LH(k) - LH(k - 1))
     Qinterp = QT(k - 1) + PROP * DQ
     Sinterp = ST(k - 1) + PROP * (ST(k) - ST(k - 1))
  Else
    Qinterp = 0
    Sinterp = 0
  End If
End Sub
  
    
Sub ReadHData()
  Dim SName As String
  Dim NRows As Integer
  Dim Multiplier As Double
  
  SName = "table"
  NumberData = Worksheets("tmpData").Range("C35").value
  DDT = Worksheets("tmpData").Range("C36").value 'Delta T
  DT = DDT * 3600
  
  QPP = Worksheets("tmpData").Range("C37").value 'QPFS
  TotRoaf = Worksheets("tmpData").Range("C38").value
  StrmRain = Worksheets("tmpData").Range("C39").value
  StrmDur = Worksheets("tmpData").Range("C40").value
  
  Multiplier = 1
  If (isThisMetric = True) Then
   'To tranform from Metric to English
   ' The values of Outflow Rate (m^3/s) to (ft^3/s)
   Multiplier = M2Ft ^ 3
  End If
   
  
  QR(1) = 0
  For I = 2 To NumberData + 2
   QR(I) = Worksheets(SName).Cells(8 + I, 10).value * Multiplier
  Next I
  
End Sub


Sub routgraph(xRows)
Dim xrange As String
Dim y1range As String
Dim y2range As String
Dim isMetricOUT As Boolean

Dim FlowUnits As String
Dim DepthUnits As String
Dim AreaUnits As String


 If (isThisMetric = True) Then
  FlowUnits = "m" + Chr(179) + "/s" ' "m^3/s"
  DepthUnits = " m"
  AreaUnits = "ha"
 
 Else
  FlowUnits = "ft" + Chr(179) + "/s" ' "ft^3/s"
  DepthUnits = "ft"
  AreaUnits = "Acres"
 End If

SName = "routable"
Worksheets(SName).Range("E3").value = AreaUnits 'Area Units
Worksheets(SName).Range("E4").value = DepthUnits 'Depth Units
Worksheets(SName).Range("C9").value = FlowUnits 'Inflow Units
Worksheets(SName).Range("D9").value = FlowUnits 'Outflow Units
Worksheets(SName).Range("E9").value = DepthUnits 'Depth Units

Worksheets(SName).Range("F1").value = Worksheets("table").Range("I4").value
Worksheets(SName).Range("G2").value = Worksheets("table").Range("J5").value


xrange = "=routable!R10C2:R" & (9 + xRows) & "C2"
y1range = "=routable!R10C3:R" & (9 + xRows) & "C3"
y2range = "=routable!R10C4:R" & (9 + xRows) & "C4"

Worksheets("routing").Range("M3").value = FlowUnits
Worksheets("routing").Range("P3").value = DepthUnits


Sheets("routing").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Q (" & FlowUnits & ")"
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).Name = "=""Inflow"""
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y1range
    ActiveChart.SeriesCollection(2).Name = "=""Outflow"""
    ActiveChart.SeriesCollection(2).XValues = xrange
    ActiveChart.SeriesCollection(2).Values = y2range
    Range("B2").Select


 Sheets("graph4").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Q (" & FlowUnits & ")"
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).Name = "=""Inflow"""
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y1range
    ActiveChart.SeriesCollection(2).Name = "=""Outflow"""
    ActiveChart.SeriesCollection(2).XValues = xrange
    ActiveChart.SeriesCollection(2).Values = y2range
    Range("C1").Select
End Sub



Sub Routing_And_MaximumQ()
Dim S1, Q1, S2, Q2, I1, I2, T, HW As Double
Dim value As Double
Dim J As Integer
Dim SName As String
Dim Multi1 As Double
Dim Multi2 As Double
Dim Multi3 As Double


Multi1 = 1
Multi2 = 1
Multi3 = 1
If (isThisMetric = True) Then
 'from ft^3/s to m^3/s
 Multi1 = (1 / M2Ft) ^ 3
 
 'From ft to m
 Multi2 = 1 / M2Ft
 
 'From ft2 to has
 Multi3 = 1 / Ha2Acre
End If

'At this point everything is in English system

SName = "routable"
Worksheets(SName).Range("B10:E1000").value = ""
Worksheets(SName).Range("D3").value = (ReservoirArea / 43560) * Multi3
Worksheets(SName).Range("D4").value = SpillLength * Multi2
Worksheets(SName).Range("D5").value = SpillCoeff


  QOP = 0
  S1 = 0
  Q1 = 0
  J = 2
  I1 = QR(1)
  Do While J <= NumberData + AdditionalIters
     If J > NumberData Then QR(J) = 0
     I2 = QR(J)
     T = (J - 2) * DDT
     value = (I1 + I2 - Q1) / 2 + (S1 / DT)
     Interpolation value
     HW = GetH_Spillway(Qinterp)
     'Save_Row;
     Worksheets(SName).Cells(J + 8, 2).value = T
     Worksheets(SName).Cells(J + 8, 3).value = I2 * Multi1
     Worksheets(SName).Cells(J + 8, 4).value = Qinterp * Multi1
     Worksheets(SName).Cells(J + 8, 5).value = HW * Multi2
     
     If Qinterp >= QOP Then
         QOP = Qinterp
         HP = HW
     End If
     Q1 = Qinterp
     S1 = Sinterp
     I1 = I2
     J = J + 1
  Loop
   
  routgraph (J)
End Sub


Sub RunRouting(xArea, xLength, xcoeff, xniters)

  
  'the output units of hydrograph are the INPUT/OUPUT units for Routing
  isThisMetric = Module1.isMetric_OUT()
  
  SpillCoeff = xcoeff
  SpillLength = xLength
  ReservoirArea = xArea * 43560 'Area is converted to Square feet
  
  If (Module1.isMetric_IN() = True) Then
   'Units are converted to Metric
   SpillLength = SpillLength * M2Ft
   ReservoirArea = ReservoirArea * Ha2Acre
  End If
  
  
  AdditionalIters = xniters
  ReadHData
  Build_Storage_Table
  Routing_And_MaximumQ
  Module1.SetResetRouting (False)
  Sheets("routing").Select
  Range("C1").Select
  ActiveCell.FormulaR1C1 = "."
End Sub





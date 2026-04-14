Attribute VB_Name = "funcs"


Sub CopyData(Dir As Byte, page1 As String, cellname1 As String, page2 As String, cellname2 As String)
 If (Dir = 0) Then
    Worksheets(page2).Range(cellname2).value = Worksheets(page1).Range(cellname1).value
  Else
    Worksheets(page1).Range(cellname1).value = Worksheets(page2).Range(cellname2).value
 End If
End Sub


Function get1Value(isMetric As Boolean, Val1, Val2)
 If (isMetric = True) Then
  get1Value = Val1
  Else
  get1Value = Val2
  End If
End Function

Sub setValueatCell(page As String, CellName As String, value)
 Worksheets(page).Range(CellName).value = value
End Sub


Sub ChangeLabelUnitsIn()
 Dim isMetric As Boolean
 Dim page As String
 page = "tmpData"
 'IsMetric = Module1.isMetric_OUT()
 
 'setValueatCell Page, "I35", get1Value(IsMetric, "mm", "in")
 'setValueatCell Page, "I35", get1Value(IsMetric, "mm", "in")
 'setValueatCell Page, "I35", get1Value(IsMetric, "mm", "in")
 'setValueatCell Page, "I35", get1Value(IsMetric, "mm", "in")
 'setValueatCell Page, "I35", get1Value(IsMetric, "mm", "in")
 
End Sub


Function GetTcMethod_SlopeTitle(iMethod) As String
Dim Cad As String
 
 If (iMethod = 1) Then
   Cad = "Channel Slope (%) "
   Else
   Cad = "Average Land Slope (%) "
  End If

  GetTcMethod_SlopeTitle = Cad
End Function

Function CalcTimeCon(MethodTc, LenLChan, AvLndSI, s) As Double
Dim v As Double
Dim isMetric As Boolean

isMetric = Module1.isMetric_IN()
If (isMetric = True) Then
 'meters are transformed to feet
 LenLChan = LenLChan / 0.3048
End If

'check this formulas !
 If (MethodTc = 1) Then
  'a = LenLChan ^ 0.77
  'b = (AvLndSI / 100) ^ 0.385
   v = (0.0078 * (LenLChan ^ 0.77) / ((AvLndSI / 100) ^ 0.385)) / 60
 Else
  v = ((LenLChan ^ 0.8) * ((s + 1) ^ 0.7) / (1900 * (AvLndSI ^ 0.5))) / 0.6
 End If
  CalcTimeCon = v
End Function
Sub checkTcValue()
 a = CalcTimeCon(1, 15900, 14.1, 0.5)
End Sub
Function GetS(CN) As Double
 GetS = (1000 / CN) - 10
End Function


Function show_Tc(TcOpt, MOpt, Slope, ChanelL, CN)
 'Dim cad As String
 Dim s As Double
 Cad = "Given"
 
 If (TcOpt > 1) Then
 
  s = GetS(CN)
  Cad = CalcTimeCon(MOpt, ChanelL, Slope, s)
  
 End If
 
 show_Tc = Cad
End Function

Function Calc_SIMAS_Tl(Width, Slope, CN)
Dim s As Double
Dim isMetric As Boolean

isMetric = Module1.isMetric_IN()
If (isMetric = True) Then
 'meters are transformed to feet
 Width = Width / 0.3048
End If
  s = GetS(CN)
  Slope = Slope / 100 'it is ft/ft
  Calc_SIMAS_Tl = 0.0051 * Width ^ (0.5937) * Slope ^ (-0.1505) * s ^ (0.3131)
End Function


Function GetValueTo_CN5(CN As Variant) As Variant

Dim S2 As Double
Dim S5 As Double
Dim valor As Double

  If (CN > 0 And CN <= 100) Then
   valor = CN
   If (CN < 96) Then
     S2 = 1000 / CN - 10
     S5 = 1.33 * S2 ^ (1.15)
     valor = 1000 / (10 + S5)
    End If
    GetValueTo_CN5 = valor
  Else
   GetValueTo_CN5 = ""
  End If
End Function


Function Weighted_CN(SumArea, SumCN) As Double

Dim I As Integer
Dim tmpCN As Double
Dim tmpAreas As Double
Dim CNW As Double
Dim Val1 As Variant
Dim Val2 As Variant


CNW = 0
 For I = 1 To 20
  Val1 = Worksheets("CNS").Cells(5 + I, 5).value
  Val2 = Worksheets("CNS").Cells(5 + I, 7).value
  
  'tmpArea = Worksheets("CNS").Cells(5 + i, 5).Value
  'tmpCN = Worksheets("CNS").Cells(5 + i, 6).Value
  
  If (IsNumeric(Val1) And IsNumeric(Val2)) Then
   tmpArea = Val1
   tmpCN = Val2
   If ((tmpCN > 0) And (tmpArea > 0) And (SumArea > 0)) Then
     CNW = CNW + (tmpCN * tmpArea / SumArea)
   End If
  End If
 Next I
 
 Weighted_CN = CNW
End Function


Function Enable_StormType(SType)
Dim Como As Boolean

 Como = True
 If SType < 4 Then Como = False
 
 'Sheet3.Storm_EnableButton Como
 
 
  Enable_StormType = Como
End Function

Function Set_GenericStorm(MinP, MaxP, TimeP, SName)
Dim page As String
  page = "tmpData"
  Worksheets(page).Range("N5").value = MinP
  Worksheets(page).Range("N6").value = MaxP
  Worksheets(page).Range("N7").value = TimeP
  Worksheets(page).Range("N4").value = SName
End Function

Function Set_StormData(xName, duration, rainfall, StrmType)
 Worksheets("storm").Range("F5").value = xName
 Worksheets("storm").Range("F7").value = duration
 Worksheets("storm").Range("F9").value = rainfall
 Worksheets("storm").Range("F11").value = StrmType
End Function

Sub Clear_StormData()
 Set_StormData "", "", "", 1
 Set_GenericStorm "", "", "", ""
 Worksheets("cstorm").Range("E12:F101").value = ""
End Sub

Sub Change_Plot1(NRows, isMetricOUT As Boolean)
' Q in iph
Dim xrange As String
Dim y1range As String
Dim y2range As String
Dim y3range As String

'xrange = "=table!$B$9:$B$" & (9 + NRows - 1)
xrange = "=table!R10C2:R" & (10 + NRows) & "C2"
'y1range = "=table!$G$9:$G$" & (9 + NRows + 1)
y1range = "=table!R10C9:R" & (10 + NRows) & "C9"
'y2range = "=table!$H$9:$H$" & (9 + NRows + 1)
y2range = "=table!R10C10:R" & (10 + NRows) & "C10"

'=table!R9C2:R22C2"

    Sheets("output").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    If (isMetricOUT = True) Then
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "q(mm/h)"
     Else
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "q(in/h)"
    End If
    ActiveChart.PlotArea.Select
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y1range
    ActiveChart.Deselect
    Range("B2").Select
    
    Sheets("graph1").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    If (isMetricOUT = True) Then
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "q(mm/h)"
     Else
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "q(in/h)"
    End If
    ActiveChart.PlotArea.Select
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y1range
    Range("C1").Select
    
    
    Sheets("graph2").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    If (isMetricOUT = True) Then
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "q (cms)"
     Else
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "q (cfs)"
    End If
    ActiveChart.PlotArea.Select
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y2range
    Range("C1").Select
    
    'y1range = "=table!$C$9:$C$" & (9 + NRows + 1)
    y1range = "=table!R10C3:R" & (10 + NRows) & "C3"
    'y2range = "=table!$D$9:$D$" & (9 + NRows + 1)
    y2range = "=table!R10C4:R" & (10 + NRows) & "C4"
    y3range = "=table!R10C7:R" & (10 + NRows) & "C7"
    
    Sheets("graph3").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    If (isMetricOUT = True) Then
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Depth (mm)"
     Else
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Depth (in)"
    End If
    ActiveChart.PlotArea.Select
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y1range
    ActiveChart.SeriesCollection(2).Select
    ActiveChart.SeriesCollection(2).XValues = xrange
    ActiveChart.SeriesCollection(2).Values = y2range
    ActiveChart.SeriesCollection(3).Select
    ActiveChart.SeriesCollection(3).XValues = xrange
    ActiveChart.SeriesCollection(3).Values = y3range
    Range("C1").Select

'Rainfall
    xrange = "=table!R10C3:R" & (10 + NRows) & "C3"
    y1range = "=table!R10C4:R" & (10 + NRows) & "C4"
    y2range = "=table!R10C7:R" & (10 + NRows) & "C7"
    
    Sheets("graph5").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    If (isMetricOUT = True) Then
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Q (mm)"
      ActiveChart.Axes(xlCategory, xlPrimary).AxisTitle.Text = "P (mm)"
     Else
      ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Q (in)"
      ActiveChart.Axes(xlCategory, xlPrimary).AxisTitle.Text = "P (in)"
    End If
    
    ActiveChart.PlotArea.Select
    ActiveChart.SeriesCollection(1).Select
    ActiveChart.SeriesCollection(1).XValues = xrange
    ActiveChart.SeriesCollection(1).Values = y1range
    ActiveChart.SeriesCollection(2).Select
    ActiveChart.SeriesCollection(2).XValues = xrange
    ActiveChart.SeriesCollection(2).Values = y2range
    Range("C1").Select
    
    Sheets("output").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.Deselect
    Range("B2").Select
    
    
End Sub

Sub hidetabs()
 ActiveWindow.DisplayWorkbookTabs = True
End Sub

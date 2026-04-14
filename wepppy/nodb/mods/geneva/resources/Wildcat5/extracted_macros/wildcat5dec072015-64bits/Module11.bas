Attribute VB_Name = "Module11"
Sub Macro17()
Attribute Macro17.VB_ProcData.VB_Invoke_Func = " \n14"
'
' Macro17 Macro
'

'
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.PlotArea.Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.Axes(xlValue).AxisTitle.Select
    Range("D1").Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.Axes(xlValue).AxisTitle.Select
    ActiveSheet.ChartObjects("Chart 1").Activate
    ActiveChart.Axes(xlValue, xlPrimary).AxisTitle.Text = "Q (ft^3/2)"
End Sub
Sub Macro18()
Attribute Macro18.VB_ProcData.VB_Invoke_Func = " \n14"
'
' Macro18 Macro
'

'
    Range("C1").Select
    ActiveCell.FormulaR1C1 = "."
    With ActiveCell.Characters(Start:=1, Length:=1).Font
        .Name = "Arial"
        .FontStyle = "Regular"
        .Size = 10
        .Strikethrough = False
        .Superscript = False
        .Subscript = False
        .OutlineFont = False
        .Shadow = False
        .Underline = xlUnderlineStyleNone
        .ColorIndex = xlAutomatic
        .TintAndShade = 0
        .ThemeFont = xlThemeFontNone
    End With
    Range("C2").Select
End Sub

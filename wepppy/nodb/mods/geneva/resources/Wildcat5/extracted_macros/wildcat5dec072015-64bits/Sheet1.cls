Attribute VB_Name = "Sheet1"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton2, 2, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 3, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 4, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton6, 8, 4, MSForms, CommandButton"
Attribute VB_Control = "CommandButton7, 9, 5, MSForms, CommandButton"
Attribute VB_Control = "CommandButton8, 10, 6, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 21, 7, MSForms, CommandButton"
Attribute VB_Control = "CommandButton9, 139, 8, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 1690, 9, MSForms, CommandButton"

Private Function AddValues(label, value, Label2)
 AddValues = Chr(13) & label & "  " & value & " " & Label2
End Function

Private Function GetV(celda)
 GetV = Worksheets("tmpData").Range(celda).value
End Function

Private Sub CommandButton1_Click()
 'Help button for Units
 Module1.W5Help "W5Metric.pdf"
End Sub

Private Function Show_ReviewData()
' Module1.GotoProject

Dim Cad As String
Dim tmpCad As String
Dim isMetricIN As Boolean
Dim TcMethod As Integer

isMetric = Module1.isMetric_IN()

'Cad = "WildCat5 Input Summary:" & Chr(13) & Chr(13)
Cad = ""
Cad = Cad & AddValues("Storm Name:", GetV("R4"), "")
Cad = Cad & AddValues("Rainfall:", GetV("R6"), GetV("I35")) & AddValues("Storm Duration", GetV("R5"), "hr")
tmpCad = getName_StormDist
Cad = Cad & AddValues("Storm Distribution:", tmpCad, "")
Cad = Cad & Chr(13) & AddValues("Watershed Area:", GetV("E28"), GetV("I38"))
TcMethod = GetV("E18")
If (TcMethod = 3) Then
 'SIMAS
  tmpCad = Format(GetV("I20"), "#,##0.00")
  Cad = Cad & AddValues("SIMAS TL:", tmpCad, " hr") & Chr(13)
Else
  If (TcMethod = 2) Then
    tmpCad = Format(GetV("E25"), "#,##0.000") & " hr (" & getName_Tc & ")"
  Else
   tmpCad = GetV("E19") & " hr (" & getName_Tc & ")"
  End If
  
  Cad = Cad & AddValues("Tc:", tmpCad, "")
End If
tmpCad = getName_RainfallExcess(True)
Cad = Cad & AddValues("Rainfall Excess:", tmpCad, "")

tmpCad = getName_UnitHyd
Cad = Cad & AddValues("Unit Hydrograph:", tmpCad, "")


'MsgBox Cad, vbInformation

'Module1.SummaryDLG Cad

 Dim OptSummary As Integer

 Load frSummary
 OptSummary = frSummary.Set_Summary(Cad)
 Unload frSummary
 
 If (OptSummary = 2) Then
  'Display next time is disabled
   Module1.DSummary (True)
 End If

 Show_ReviewData = (OptSummary > 0)
End Function

Private Sub CommandButton10_Click()
 Module1.GotoProject
End Sub

Private Sub CommandButton2_Click()
 Module1.GotoWatershed
End Sub

Private Sub CommandButton3_Click()
 Module1.GotoStorm
End Sub

Private Sub CommandButton4_Click()
Dim DS As Boolean

 Module1.SetResetRouting (True)
 DS = Module1.DSummary(False)
 If (DS = True) Then
    If (Show_ReviewData = True) Then
      wildcat.RunAnalysis
    End If
 Else
   wildcat.RunAnalysis
 End If
 
 
End Sub

Private Sub CommandButton5_Click()
 Module1.GotoUH
End Sub

Private Sub CommandButton6_Click()
 'Module1.GotoAbout
 Module1.W5Help "W5About.pdf"
End Sub

Private Sub CommandButton7_Click()
 Module1.W5Help "W5Disclaimer.pdf"
 'Module1.GotoDisclaimer
End Sub



Private Sub CommandButton8_Click()
 Module1.ExitWildcat
End Sub

Private Sub CommandButton9_Click()
Module1.GotoRainfallExcess
End Sub

Private Sub Worksheet_Activate()

End Sub

Private Sub Worksheet_SelectionChange(ByVal Target As Range)

End Sub

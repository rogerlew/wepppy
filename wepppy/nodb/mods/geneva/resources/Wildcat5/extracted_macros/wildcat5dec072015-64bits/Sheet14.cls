Attribute VB_Name = "Sheet14"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton1, 19, 0, MSForms, CommandButton"
Attribute VB_Control = "ButtonF, 24, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 258, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 261, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 262, 4, MSForms, CommandButton"
Attribute VB_Control = "CommandButton6, 263, 5, MSForms, CommandButton"
Attribute VB_Control = "CommandButton7, 264, 6, MSForms, CommandButton"
Attribute VB_Control = "CommandButton8, 265, 7, MSForms, CommandButton"
Attribute VB_Control = "ButtonCN, 415, 8, MSForms, CommandButton"
Attribute VB_Control = "ButtonCN5, 416, 9, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 476, 10, MSForms, CommandButton"
Attribute VB_Control = "CommandButton9, 501, 11, MSForms, CommandButton"
Attribute VB_Control = "CommandButton10, 542, 12, MSForms, CommandButton"
Attribute VB_Control = "CommandButton11, 543, 13, MSForms, CommandButton"
Attribute VB_Control = "ButtonMu, 545, 14, MSForms, CommandButton"


Private Function GetREMethod()
  GetREMethod = Range("G4").value
End Function


Private Sub ButtonCN_Click()
  Module1.Goto_CNS 1
End Sub

Private Sub ButtonCN5_Click()
 Module1.Goto_CNS 2
End Sub

Private Sub ButtonF_Click()
 Module1.Goto_DistributeF
End Sub




Private Sub Copy_Temporal_Data(Dir As Byte)
 Dim page1 As String
 Dim page2 As String
 
 page1 = "rainfallex"
 page2 = "tmpData"
 
 CopyData Dir, page1, "G4", page2, "E3" 'Method
 CopyData Dir, page1, "H16", page2, "E7" 'mhu
 CopyData Dir, page1, "H31", page2, "E10" 'Phi
 CopyData Dir, page1, "H35", page2, "E11" 'c fraction
 CopyData Dir, page1, "H40", page2, "E12" 'b1
 CopyData Dir, page1, "H42", page2, "E13" 'b2
 CopyData Dir, page1, "H44", page2, "E14" 'a
End Sub


Sub AcceptRE_Method(emtyvar)
 Dim ReMethod As Byte
 
  ReMethod = GetREMethod
  Worksheets("tmpData").Range("E3").value = ReMethod
End Sub

Private Sub ButtonMu_Click()
 Dim XMu As Double
Dim UMetric As Boolean

UMetric = Module1.isMetric_IN()

 Load frCover
 XMu = frCover.CoverDlg(UMetric)
 Unload frCover
 If (XMu > 0 And XMu <= 1) Then Range("H16").value = Format(XMu, "#,##0.000")
End Sub

Private Sub CommandButton1_Click()
Dim ReMethod As Byte
Dim xvalue As Double
Dim isOK As Boolean
isOK = True

ReMethod = GetREMethod
If ReMethod = 5 Then
  'Mu
  xvalue = Range("H16").value
  If (xvalue <= 0 Or xvalue >= 100) Then
   isOK = False
   MsgBox "Error in Mu value" & Chr(13) & "Range: 0< Mu <10"
  End If
End If

If ReMethod = 4 Then
  'Phi
  xvalue = Range("H31").value
  If (xvalue <= 0 Or xvalue >= 100) Then
   isOK = False
   MsgBox "Error in Phi Index value" & Chr(13) & "Range: 0< Phi <10"
  End If
End If

If ReMethod = 7 Then
  'Constant c
  xvalue = Range("H35").value
  If (xvalue <= 0 Or xvalue >= 1) Then
   isOK = False
   MsgBox "Error in C value" & Chr(13) & "Range: 0< C <1"
  End If
End If

 If (isOK) Then
  Copy_Temporal_Data 0
  Module1.GotoMain
 End If
End Sub

Private Sub CommandButton10_Click()
CommandButton1_Click
End Sub

Private Sub CommandButton11_Click()
Module1.GotoMain
End Sub

Private Sub CommandButton12_Click()

End Sub

Private Sub CommandButton2_Click()
 Module1.GotoMain
End Sub

Private Sub CommandButton3_Click()
 Module1.W5Help "W5CN.pdf"
End Sub

Private Sub CommandButton4_Click()
 Module1.W5Help "W5CN05.pdf"
End Sub

Private Sub CommandButton5_Click()
 Module1.W5Help "W5DistCF.pdf"
End Sub

Private Sub CommandButton6_Click()
 Module1.W5Help "W5DistF.pdf"
End Sub

Private Sub CommandButton7_Click()
 Module1.W5Help "W5PhiIndex.pdf"
End Sub

Private Sub CommandButton8_Click()
 Module1.W5Help "W5Fraction.pdf"
End Sub

Sub Change_myRainfallExcess()
 Dim ReMethod As Byte
 ReMethod = GetREMethod
 
 ButtonCN.Enabled = (ReMethod = 1)
 ButtonCN5.Enabled = (ReMethod = 2)
 ButtonF.Enabled = (ReMethod = 3)
 ButtonMu.Enabled = (ReMethod = 5)
End Sub

Private Sub ChangeLabelUnits()
Dim isMetricIN As Boolean
Dim page As String

page = "rainfallex"

isMetricIN = Module1.isMetric_IN()
 If (isMetricIN = True) Then
  Worksheets(page).Range("I16").value = "mm/hr"
  Worksheets(page).Range("I31").value = "mm/hr"
  Worksheets(page).Range("G44").value = "a (mm) ="
 Else
  Worksheets(page).Range("I16").value = "in/hr"
  Worksheets(page).Range("I31").value = "in/hr"
  Worksheets(page).Range("G44").value = "a (in) ="
 End If

End Sub

Private Sub CommandButton9_Click()
 Module1.W5Help "W5CompViol.pdf"
End Sub

Private Sub Worksheet_Activate()
 'ChangeLabelUnits
 Copy_Temporal_Data 1
 Change_myRainfallExcess
End Sub


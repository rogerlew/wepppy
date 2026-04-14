Attribute VB_Name = "Sheet16"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton1, 2, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 971, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 974, 2, MSForms, CommandButton"




Private Sub CommandButton1_Click()
  CopyToTMP
  Sheet14.AcceptRE_Method "accept"
  Module1.GotoMain
End Sub

Private Sub CommandButton2_Click()
 Range("E6:F39").Select
 Selection.ClearContents
 Range("E6").Select
End Sub

Private Sub CommandButton3_Click()
 Module1.GotoRainfallExcess
End Sub

Private Sub CopyFromTMP()
'Get a Copy of Data from tmpData
 Worksheets("DistriF").Range("E6:F39").value = Worksheets("tmpData").Range("AA5:AB38").value
End Sub

Private Sub CopyToTMP()
'Places a Copy of Data at tmpData
 Worksheets("tmpData").Range("AA5:AB38").value = Worksheets("DistriF").Range("E6:F39").value
End Sub

Private Sub Worksheet_Activate()
 CopyFromTMP
End Sub

Private Sub Worksheet_SelectionChange(ByVal Target As Range)

End Sub

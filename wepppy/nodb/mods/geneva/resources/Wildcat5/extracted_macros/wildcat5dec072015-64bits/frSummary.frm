Attribute VB_Name = "frSummary"
Attribute VB_Base = "0{19E0006A-3608-4F61-A927-D5EE53E31AFD}{3B1B8905-8603-467D-A1C2-AB2EB3A89E9B}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Dim WhatOption As Integer


Private Sub CommandButton1_Click()
 Dim ShowSummary As Double
 
 ShowSummary = frSummary.CheckBox1.value
 
 If (ShowSummary = True) Then
  WhatOption = 1
 Else
  WhatOption = 2
 End If
 frSummary.Hide
End Sub

Function Set_Summary(cadena As String)
 WhatOption = 0
 frSummary.Label2.Caption = cadena
 'frSummary.CheckBox1.value = ShowSummary
 frSummary.Show
  Set_Summary = WhatOption
End Function

Private Sub CommandButton2_Click()
 WhatOption = 0
 frSummary.Hide
End Sub

Attribute VB_Name = "Sheet13"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton1, 1, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 2, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 4, 2, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Module1.GotoRouting
End Sub

Private Sub CommandButton2_Click()
 Module1.GotoOutput
End Sub

Sub SaveRoutingTableFile(NFile As String)
Dim StormName As String
Dim Area As String
Dim Spillway As String
Dim SpillCoef As String

Dim NumRows As Integer
Dim page As String
Dim unitstxt As String


page = "routable"

WatershedName = "Watershed Name: " & Range("D2")
Area = "Area: " & Range("D3") & " " & Range("E3")
Spillway = "Spillway Length: " & Range("D4") & " " & Range("E4")
SpillCoef = "Spillway Coefficient: " & Range("D5")

unitstxt = Range("B9") & "         " & Range("C9") & "         " & Range("D9") & "         " & Range("E9")

Open NFile For Output As #1
Print #1, "Wildcat 5, Routing Output"
Print #1, WathershedName
Print #1, Area
Print #1, Spillway
Print #1, SpillCoef
Print #1, " TIME        INFLOW       OUTFLOW       DEPTH"
Print #1, unitstxt

 NumRows = 1000
 For I = 10 To NumRows
      Vtime = Worksheets(page).Cells(I, 2).value
      Viflow = Worksheets(page).Cells(I, 3).value
      Voflow = Worksheets(page).Cells(I, 4).value
      Vdepth = Worksheets(page).Cells(I, 5).value
      
      If (Vtime > 0) Then
      
       's = Format(Vtime, "#,##0.00") & " " & Format(Viflow, "#,##0.00") & " " & Format(Voflow, "#,##0.00") & " " & Format(Vdepth, "#,##0.000")
       'Write #1, s
       'Write #1, Vtime, Viflow, Voflow, Vdepth
       Print #1, Format(Vtime, "#,##0.00"), Format(Viflow, "#,##0.00"), Format(Voflow, "#,##0.00"), Format(Vdepth, "#,##0.000")
       
      End If
 Next I

Close #1

End Sub



Private Sub CommandButton3_Click()
 Dim FileName As String
 Dim LabelName As String
 Dim WatershedName As String
 
 WatershedName = Range("D2")
 
 FileName = "WC5_Routing_" & WatershedName & ".txt"
 
 LabelName = "Routing Output Table (*.txt), *.txt"
 
 FileName = Module1.SaveFileDialog(FileName, LabelName)
 If (FileName <> "") Then
  SaveRoutingTableFile FileName
 End If
End Sub


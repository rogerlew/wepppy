Attribute VB_Name = "Sheet4"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton1, 1, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 2, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 51, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 52, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 56, 4, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Module1.GotoOutput
End Sub

Private Sub CommandButton2_Click()
 Module1.GotoMain
End Sub

Sub Update_Transient()

 Dim NRows As Integer
 Dim XRow As Integer
 Dim PutTransient As Boolean
 Dim I As Integer
 Dim Cad As String
 Dim xvalue As Double
 
 PutTransient = (Worksheets("tmpData").Range("B46").value = 1)
 NRows = Worksheets("tmpData").Range("C35").value
 
 If (PutTransient = True) Then
 ' Calculate
  Worksheets("table").Range("K7").value = "TRANSIENT"
  Worksheets("table").Range("K8").value = "STORAGE"
  Worksheets("table").Range("K9").value = "=D9"
  For I = 1 To NRows
   XRow = 9 + I
   Cad = "K" & XRow
   xvalue = Worksheets("table").Range("D" & XRow).value - Worksheets("table").Range("G" & XRow).value
   If (xvalue < 0) Then xvalue = 0
   'Worksheets("table").Range(Cad).Formula = "=D" & XRow & "-G" & XRow
   Worksheets("table").Range(Cad).value = xvalue
  Next I
 
 Else
 ' Clean
  Worksheets("table").Range("K7:K2500").value = ""
 End If

End Sub

Private Sub CommandButton3_Click()
 Dim LRow As Integer
 
 LRow = Worksheets("tmpData").Range("C35").value + 10
 
 Range("B" & LRow).Select
End Sub

Private Sub CommandButton4_Click()
 Range("B10").Select
End Sub



Sub SaveTableFile(NFile As String)
Dim MyProject As String
Dim StormName As String
Dim MyDate As String
Dim Operator As String

Dim NumRows As Integer
Dim page As String
Dim unitstxt As String


page = "table"

MyProject = "Project: " & Range("D3")
WatershedName = "Watershed Name: " & Range("D4")
MyDate = "Date: " & Range("I4")
Operator = "Operator: " & Range("J5")


unitstxt = Range("B9") & "         " & Range("C9") & "         " & Range("D9") & "           " & Range("E9") & "           " & Range("F9")
unitstxt = unitstxt & "         " & Range("G9") & "         " & Range("H9") & "         " & Range("I9") & "         " & Range("J9")

Open NFile For Output As #1
Print #1, "Wildcat 5, RUNOFF HYDROGRAPH TABLE"
Print #1, MyProject
Print #1, WatershedName
Print #1, MyDate
Print #1, Operator
Print #1, "              CUMULATIVE RAINFAL                       INCR         CUMULATIVE    CUMULATIVE       OUTFLOW       OUTFLOW"
Print #1, " TIME        DEPTH       EXCESS(Q)       CONTRIB       RUNOFF        OUTFLOW       OUTFLOW         RATE          RATE"
Print #1, unitstxt

 NumRows = 1200
 For I = 10 To NumRows
      Vtime = Worksheets(page).Cells(I, 2).value
      C1 = Worksheets(page).Cells(I, 3).value
      C2 = Worksheets(page).Cells(I, 4).value
      C3 = Worksheets(page).Cells(I, 5).value
      C4 = Worksheets(page).Cells(I, 6).value
      C5 = Worksheets(page).Cells(I, 7).value
      C6 = Worksheets(page).Cells(I, 8).value
      C7 = Worksheets(page).Cells(I, 9).value
      C8 = Worksheets(page).Cells(I, 10).value
      
      If (Vtime > 0 Or I = 10) Then
      
       Print #1, Format(Vtime, "#,##0.00"), Format(C1, "#,##0.00"), Format(C2, "#,##0.00"), Format(C3, "#,##0.000"), Format(C4, "#,##0.000"), Format(C5, "#,##0.000"), Format(C6, "#,##0.000"), Format(C7, "#,##0.000"), Format(C8, "#,##0.000")
       
      End If
 Next I

Close #1

End Sub



Private Sub CommandButton5_Click()
 Dim FileName As String
 Dim LabelName As String
 Dim WatershedName As String
 
 WatershedName = Range("D4")
 
 FileName = "WC5_Runoff_" & WatershedName & ".txt"
 
 LabelName = "Runoff Hydrograph Output Table (*.txt), *.txt"
 
 FileName = Module1.SaveFileDialog(FileName, LabelName)
 If (FileName <> "") Then
  SaveTableFile FileName
 End If
End Sub

Attribute VB_Name = "frUnits"
Attribute VB_Base = "0{F34C0136-B375-42DE-9933-8D37C7330BB4}{4AA96B3E-3CBE-494A-B393-91532CAF3876}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Dim CurrentIsMetric As Boolean

Private Sub ChangeC(xpage As String, xrange As String, factorM)
 Dim value
 value = Worksheets(xpage).Range(xrange).value
 If (CurrentIsMetric = True) Then
  Worksheets(xpage).Range(xrange).value = value * factorM
 Else
  Worksheets(xpage).Range(xrange).value = value / factorM
 End If
End Sub



Private Sub ChangeCRange(xpage As String, IniRow As Integer, EndRow As Integer, XCol As Integer, factorM, xrange As String)
Dim I As Integer
Dim valueX
Dim SumX

 SumX = 0

    For I = IniRow To EndRow
      valueX = Worksheets(xpage).Cells(I, XCol).value
      If IsNumeric(valueX) Then
       If (valueX > 0) Then
         If (CurrentIsMetric = True) Then
            valueX = valueX * factorM
         Else
           valueX = valueX / factorM
         End If
         SumX = SumX + valueX
         Worksheets(xpage).Cells(I, XCol).value = valueX
       End If
      End If
    Next I

 If (Len(xrange) > 0) Then
  Worksheets(xpage).Range(xrange).value = SumX
 End If
End Sub

Private Sub ConvertUnits()
Dim page As String

 page = "tmpData"

 ChangeC page, "R6", 25.4 'Storm Rainfall
 
 ChangeC page, "E7", 25.4 'mu
 ChangeC page, "E10", 25.4 'phi
 ChangeC page, "E14", 25.4 'a complacent
 
 ChangeC page, "E24", 0.3048 'Channel length
 
 Dim tmpArea
 tmpArea = Worksheets(page).Range("E28").value 'Area
 
 ChangeCRange page, 5, 24, 23, 1 / 2.4709661, "E28" 'UH Areas
 If (Worksheets(page).Range("E3").value > 2) Then
  'Excess Method is not curve number
   Worksheets(page).Range("E28").value = tmpArea
   ChangeC page, "E28", 1 / 2.4709661 'Area
 End If

ChangeCRange page, 5, 38, 27, 25.4, "E28" 'Distributed F, F
ChangeCRange page, 5, 38, 28, 1 / 2.4709661, "" 'Distributed F, Area

'Routing
ChangeC page, "N16", 1 / 2.4709661 'Area
ChangeC page, "N17", 0.3048 'Spillway length

End Sub



Private Sub CommandButton1_Click()
  
End Sub

Private Sub CommandButton2_Click()
 frUnits.Hide
End Sub

Sub ShowMensaje(isMetric As Boolean)
 CurrentIsMetric = isMetric
 If (isMetric = True) Then
   Label4.Caption = "METRIC SYSTEM"
  Else
   Label4.Caption = "ENGLISH SYSTEM"
 End If
 
 ConvertUnits
 frUnits.Show
End Sub

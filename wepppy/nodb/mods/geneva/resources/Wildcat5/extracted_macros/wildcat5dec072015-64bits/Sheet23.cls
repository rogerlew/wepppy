Attribute VB_Name = "Sheet23"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton1, 1, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 2, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 3, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 4, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 5, 4, MSForms, CommandButton"
Dim ComeFrom As Byte
'0=from Watershed, 1=from Rainfall Excess 0.2, 2=Rainfall Excess 0.05

Sub SetFrom_Origin(id As Byte)
 ComeFrom = id
End Sub

Private Function Check_CNValues() As Boolean
Dim isOK As Boolean
Dim isGoodRow As Boolean
Dim page As String
Dim NRows As Integer
Dim Val1
Dim Val2
Dim Cad As String

Cad = ""
isOK = True
page = "CNS"
NRows = 0

  For I = 1 To 20
      Val1 = Worksheets(page).Cells(5 + I, 5).value
      Val2 = Worksheets(page).Cells(5 + I, 7).value
      If (Val1 <> "" Or Val2 <> "") Then
        isGoodRow = True
        If (IsNumeric(Val1) And IsNumeric(Val2)) Then
           If (Val1 <= 0) Then
             Cad = Cad & Chr(13) & "Check Area at row # " & I
             isOK = False
             isGoodRow = False
           End If
           
           If (Val2 <= 1 Or Val2 > 100) Then
             Cad = Cad & Chr(13) & "Check CN Value at row # " & I
             isOK = False
             isGoodRow = False
           End If
           
          Else
           Cad = Cad & Chr(13) & "Check Values at row # " & I
           isOK = False
           isGoodRow = False
        End If
        
        If (isGoodRow = True) Then NRows = NRows + 1
      End If 'there is something
 Next I
 
 If (NRows < 1) Then
   Cad = "You must input correct data" & Chr(13) & Cad
   isOK = False
 End If
 
 If (isOK = False) Then MsgBox Cad, vbExclamation
 
 Check_CNValues = isOK
End Function

Private Function GetHowMany() As Integer
Dim page As String
Dim NRows As Integer
Dim Val1
Dim Val2

page = "CNS"
NRows = 0

  For I = 1 To 20
      Val1 = Worksheets(page).Cells(5 + I, 5).value
      Val2 = Worksheets(page).Cells(5 + I, 7).value
      If (IsNumeric(Val1) And IsNumeric(Val2)) Then
      If (Val1 > 0) And (Val2 > 0) Then
        NRows = NRows + 1
      End If
      End If
 Next I
 
 GetHowMany = NRows
End Function


Private Sub CopyFromTMP()
'Get a Copy of Data from tmpData
 Worksheets("CNS").Range("E6:G25").value = Worksheets("tmpData").Range("W5:Y24").value
End Sub

Private Sub CopyToTMP()
'Places a Copy of Data at tmpData
 Worksheets("tmpData").Range("W5:Y24").value = Worksheets("CNS").Range("E6:G25").value
End Sub

Private Sub AcceptData()
Dim page As String
Dim NRows As Integer

 NRows = GetHowMany
 
 page = "tmpData"
 If (NRows > 0) Then
 Worksheets(page).Range("E27").value = Range("L17").value 'CN
 Worksheets(page).Range("E28").value = Range("L15").value 'Area
 CopyToTMP
 If (ComeFrom > 0) Then
   Sheet14.AcceptRE_Method "accept"
   Module1.GotoMain
 Else
  GotoWatershed1 False
 End If
Else
  MsgBox "You must input some information", vbInformation
End If
End Sub


Private Sub CommandButton1_Click()

Dim isOK As Boolean
 
isOK = Check_CNValues
If (isOK = True) Then AcceptData
End Sub

Sub ReadUHFile(NFile As String)

Dim NumUH As Integer
Dim Area As Double
Dim CN As Double
Dim page As String

page = "CNS"
Worksheets(page).Range("E6:G25").value = ""

Open NFile For Input As #1
Input #1, NumUH
For I = 1 To NumUH
   Input #1, Area, CN
   Worksheets(page).Cells(5 + I, 5).value = Area
   Worksheets(page).Cells(5 + I, 7).value = CN
 Next I
Close #1
End Sub


Sub SaveUHFile(NFile As String, NRows As Integer)

Dim page As String
Dim Val1 As Variant
Dim Val2 As Variant

page = "CNS"

Open NFile For Output As #1
Write #1, NRows

For I = 1 To 20
     Val1 = Worksheets(page).Cells(5 + I, 5).value
     Val2 = Worksheets(page).Cells(5 + I, 7).value
            
      If (IsNumeric(Val1) And IsNumeric(Val2)) Then
      If (Val1 >= 0) And (Val2 >= 0) Then
        Write #1, Val1, Val2
      End If
      End If
 Next I

Close #1

End Sub





Private Sub CommandButton2_Click()
 Module1.W5OpenFile_UH
End Sub

Private Sub CommandButton3_Click()
Dim NRows As Integer

 If (Check_CNValues = True) Then
 NRows = GetHowMany
 If (NRows > 0) Then
  Module1.W5SaveFile_UH NRows
 Else
  MsgBox "There is not information to save", vbExclamation
 End If
 End If
End Sub

Private Sub CommandButton4_Click()
'Cancel

If (ComeFrom > 0) Then
 Module1.GotoRainfallExcess
 Else
 Module1.GotoWatershed1 False
End If
End Sub



Private Sub CommandButton5_Click()
Dim CN
Dim R As Integer
Dim C As Integer

C = ActiveCell.Column
R = ActiveCell.Row

If (R >= 6 And R <= 25) Then

  Load frCN
  CN = frCN.GetCNTable()
  Unload frCN

  If (CN > -1) Then
   Cells(R, 7).value = CN
  End If
 End If
End Sub

Private Sub Worksheet_Activate()
 CopyFromTMP
End Sub

Private Sub Worksheet_SelectionChange(ByVal Target As Range)
  
End Sub

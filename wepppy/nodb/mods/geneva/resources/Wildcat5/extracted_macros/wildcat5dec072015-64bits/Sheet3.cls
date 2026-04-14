Attribute VB_Name = "Sheet3"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton1, 2, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 4, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 5, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 6, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 1379, 4, MSForms, CommandButton"
Attribute VB_Control = "CommandButton6, 2079, 5, MSForms, CommandButton"
Const STRM_CUSTOM = 4
Const STRM_GENERIC = 5

Private Function GetStormId()
 GetStormId = Worksheets("storm").Range("F11").value
End Function

Private Sub CommandButton1_Click()
Dim SType As Integer
 SType = GetStormId
 If SType = STRM_CUSTOM Then
   Module1.Goto_CustomStorm
 End If
 
 If SType = STRM_GENERIC Then
   Module1.GotoGenericStorm
 End If
End Sub



Private Sub Copy_Temporal_Data(Dir As Byte)
 Dim page1 As String
 Dim page2 As String
 
 page1 = "storm"
 page2 = "tmpData"
 
 CopyData Dir, page1, "F11", page2, "R7" 'Method
 CopyData Dir, page1, "F5", page2, "R4" 'Name
 CopyData Dir, page1, "F7", page2, "R5" 'Duration
 CopyData Dir, page1, "F9", page2, "R6" 'Rainfall
End Sub


Private Sub CommandButton2_Click()
Dim isOK As Boolean
isOK = True

Dim duration As Double
Dim rainfall As Double
Dim Cad As String
Cad = "Error, please check:" & Chr(13) & Chr(13)

duration = Range("F7").value
If (duration <= 0 Or duration > 500) Then
  Cad = Cad & "Storm Duration Value" & Chr(13)
  isOK = False
End If

rainfall = Range("F9").value
If (rainfall <= 0 Or rainfall > 500) Then
  Cad = Cad & "Storm Rainfall Value"
  isOK = False
End If

If (isOK) Then
 Copy_Temporal_Data 0
 Module1.GotoMain
Else
  MsgBox Cad, vbExclamation
End If
End Sub

Private Sub CommandButton3_Click()
 Dim FName As String
 Dim StrmType As Integer
 Dim FileFilter As String
 
 
 ' From Combobox
 StrmType = GetStormId
 
 'default filter
 FileFilter = "Storm data file (*.stm), *.stm ,Generic Storm (*.gst),*.gst,Custom Storm (*.cst), *.cst"
 
 If (StrmType = STRM_GENERIC) Then FileFilter = "Generic Storm (*.gst),*.gst,Storm data file (*.stm), *.stm ,Custom Storm (*.cst), *.cst"
 If (StrmType = STRM_CUSTOM) Then FileFilter = "Custom Storm (*.cst),*.cst,Storm data file (*.stm), *.stm ,Generic Storm (*.gst),*.gst"
 
 FName = Module1.OpenFileDialog(FileFilter)
 If (FName <> "") Then
   ReadStormFile FName
 End If
End Sub

Private Sub CommandButton4_Click()
 Dim FileName As String
 Dim LabelName As String
 FileName = Range("F5").value
 
 LabelName = "Storm data file (*.stm), *.stm"
 StrmType = GetStormId
 If (StrmType = STRM_GENERIC) Then LabelName = "Generic Storm data file (*.gst), *.gst"
 If (StrmType = STRM_CUSTOM) Then LabelName = "Custom Storm data file (*.cst), *.cst"
 
 FileName = Module1.SaveFileDialog(FileName, LabelName)
 If (FileName <> "") Then
  SaveStormFile FileName
 End If
End Sub


Sub ReadStormFile(NFile As String)
Dim StormName As String
Dim duration As Double
Dim rainfall As Double
Dim StrmType As Integer
Dim NumCust As Integer
Dim TimeX, PreX
'llll

funcs.Clear_StormData
Open NFile For Input As #1
Input #1, StormName, duration, rainfall, StrmType

If StrmType = STRM_GENERIC Then
  Input #1, imin, imax, tmax
  funcs.Set_GenericStorm imin, imax, tmax, StormName
End If

If StrmType = STRM_CUSTOM Then
 Input #1, NumCust
 For I = 1 To NumCust
   Input #1, TimeX, PreX
   Worksheets("cstorm").Cells(11 + I, 5).value = TimeX
   Worksheets("cstorm").Cells(11 + I, 6).value = PreX
 Next I
End If
Close #1
funcs.Set_StormData StormName, duration, rainfall, StrmType
Storm_EnableButton -1
End Sub


Private Function Count_CustomItems()
Dim SName As String

    SName = "cstorm"
    Count = 0
    For I = 1 To 100
      Val1 = Worksheets(SName).Cells(I + 11, 5).value
      Val2 = Worksheets(SName).Cells(I + 11, 6).value
      
      tmp1 = "" & Val1
      tmp2 = "" & Val2
      If (Len(tmp1) > 0) And (Len(tmp2) > 0) Then
      If (Val1 >= 0) And (Val2 >= 0) Then
        Count = Count + 1
      End If
      End If
    Next I
   Count_CustomItems = Count
End Function


Sub SaveStormFile(NFile As String)
Dim StormName As String
Dim duration As Double
Dim rainfall As Double
Dim StrmType As Integer
Dim NumCust As Integer
Dim page As String

StormName = Range("F5")
duration = Range("F7")
rainfall = Range("F9")
StrmType = GetStormId

Open NFile For Output As #1
Write #1, StormName, duration, rainfall, StrmType

If StrmType = STRM_GENERIC Then
  
  Dim imin As Double
  Dim imax As Double
  Dim tmax As Double
  
  page = "tmpData"
  imin = Worksheets(page).Range("N5").value
  imax = Worksheets(page).Range("N6").value
  tmax = Worksheets(page).Range("N7").value
  Write #1, imin, imax, tmax
End If

If StrmType = STRM_CUSTOM Then
 NumCust = Count_CustomItems
 Write #1, NumCust
 page = "cstorm"
 
 For I = 1 To 100
      Val1 = Worksheets(page).Cells(I + 11, 5).value
      Val2 = Worksheets(page).Cells(I + 11, 6).value
      
      tmp1 = "" & Val1
      tmp2 = "" & Val2
      If (Len(tmp1) > 0) And (Len(tmp2) > 0) Then
      If (Val1 >= 0) And (Val2 >= 0) Then
        Write #1, Val1, Val2
      End If
      End If
 Next I
End If
Close #1

End Sub


Sub Storm_EnableButton(xOption As Integer)
Dim Como As Boolean
 If (xOption < 0) Then xOption = GetStormId

 CommandButton1.Enabled = (xOption > 3)
End Sub

Private Sub CommandButton5_Click()
 Module1.GotoMain
End Sub

Private Sub CommandButton6_Click()
  Module1.W5Help "W5StormDistribution.pdf"
End Sub

Private Sub Worksheet_Activate()
 Copy_Temporal_Data 1
 Storm_EnableButton -1
End Sub


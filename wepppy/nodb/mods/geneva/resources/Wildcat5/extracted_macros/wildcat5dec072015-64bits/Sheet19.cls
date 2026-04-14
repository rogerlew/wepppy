Attribute VB_Name = "Sheet19"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton2, 6, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 7, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 8, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 9, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 10, 4, MSForms, CommandButton"
Const KIRPICH_TC = 1
Const KENT_TC = 2

Private Function checkdata()
 Dim isOK As Boolean
 Dim Cad As String
 Dim Area As Double
 Dim TcOption As Byte
 Dim TcMethod As Byte
 Dim CN As Double
 
 Cad = "Error, please check:" & Chr(13) & Chr(13)
 isOK = True
 Area = Range("F6").value
 If (Area <= 0) Then
   isOK = False
   Cad = Cad & "Total drainage area " & Chr(13)
 End If
 
 TcOption = Range("K13").value
 If (TcOption = 1) Then
   Tc = Range("F9").value
 Else
   TcMethod = Range("K16").value
   If (TcMethod = KENT_TC) Then
     CN = Range("I17").value
     If (CN < 1 Or CN > 100) Then
      isOK = False
      Cad = Cad & "Curver Number Value"
     End If
   End If
   Tc = Range("I19").value
   
 End If
 
 If (Tc <= 0 Or Tc > 50) Then
   isOK = False
   Cad = Cad & "Time of concentration " & Chr(13)
 End If
 
 If (isOK = False) Then MsgBox Cad, vbExclamation
 
 checkdata = isOK
End Function

Private Sub CommandButton1_Click()
 Module1.GotoMain
End Sub

Private Sub CommandButton2_Click()
 Dim FName As String
 'FName = Module1.W5OpenFile_Watershed(1)
 FName = Module1.OpenFileDialog("Watershed Timing data file (*.wt), *.wt")
 If (FName <> "") Then
   ReadWatershedFile FName
 End If
End Sub


Sub ReadWatershedFile(NFile As String)
Dim Slope As Double
Dim Channel As Double
Dim Area As Double
Dim CN As Double
Dim Tc As Double
Dim D1, D2, D3
Dim WName As String
Dim MethodTc As Integer

'Open NFile For Input As #1
'Input #1, WName
'Input #1, Slope, Channel, Tc, MethodTc
'Input #1, Area, CN
'Close #1

ModuleIO.ReadWatershedInfo NFile, WName, Slope, Channel, Tc, MethodTc, Area, CN

Range("F4").value = WName
Range("I13").value = Slope
Range("I15").value = Channel
Range("F9").value = Tc

Range("F6").value = Area
Range("I17").value = CN
Range("K13").value = MethodTc
End Sub

Private Sub SaveWatershedFile(NFile As String)
Dim Slope As Double
Dim Channel As Double
Dim Area As Double
Dim CN As Double
Dim Tc As Double
Dim D1, D2, D3
Dim WName As String
Dim MethodTc As Integer

WName = Range("F4").value
Slope = Range("I13").value
Channel = Range("I15").value
Tc = Range("F9").value
Area = Range("F6").value
CN = Range("I17").value
MethodTc = Range("K13").value

ModuleIO.SaveWatershedInfo NFile, WName, Slope, Channel, Tc, MethodTc, Area, CN

'Open NFile For Output As #1
'Write #1, WName
'Write #1, Slope, Channel, Tc, MethodTc
'Write #1, Area, CN
'Close #1
End Sub


Private Sub CommandButton3_Click()
 Dim FileName As String
 FileName = Range("F4").value
 FileName = Module1.SaveFileDialog(FileName, "Watershed Timing data file (*.wt), *.wt")
 If (FileName <> "") Then
  SaveWatershedFile FileName
 End If
End Sub


Private Sub Copy_Temporal_Data(Dir As Byte)
 Dim page1 As String
 Dim page2 As String
 
 page1 = "watershed2"
 page2 = "tmpData"
 
 CopyData Dir, page1, "F4", page2, "E16" 'Name
 CopyData Dir, page1, "F6", page2, "E28" 'Total Area
 CopyData Dir, page1, "F9", page2, "E19" 'TC given value
 CopyData Dir, page1, "K13", page2, "E18" 'TC Method (Given or Calculated)
 CopyData Dir, page1, "K16", page2, "E20" 'TC Formula for calculation
 CopyData Dir, page1, "I13", page2, "E23" 'Slope
 CopyData Dir, page1, "I15", page2, "E24" 'Length Channel
 CopyData Dir, page1, "I17", page2, "E27" 'CN
 
 'SIMAS Method
 CopyData Dir, page1, "I24", page2, "I18" 'Width
 CopyData Dir, page1, "I26", page2, "I19" 'Slope
 If (Dir = 0) Then
  CopyData Dir, page1, "I30", page2, "I20" 'TL
  CopyData Dir, page1, "I19", page2, "E25" 'TL
 End If
 
End Sub


Private Sub CommandButton4_Click()

 If (checkdata = True) Then
  Copy_Temporal_Data 0
 Module1.GotoMain
 End If
End Sub


Private Sub CommandButton5_Click()
 Module1.W5Help "W5Tc.pdf"
End Sub

Private Sub CommandButton6_Click()
 Load frSIMAS
 frSIMAS.Show
 Unload frSIMAS
End Sub

Private Sub Worksheet_Activate()
  Copy_Temporal_Data 1
End Sub

Private Sub Worksheet_SelectionChange(ByVal Target As Range)

End Sub

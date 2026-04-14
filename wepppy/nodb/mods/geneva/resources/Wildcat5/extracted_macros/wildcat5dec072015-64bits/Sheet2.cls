Attribute VB_Name = "Sheet2"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton2, 7, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 8, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 9, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 11, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 12, 4, MSForms, CommandButton"
Attribute VB_Control = "CommandButton6, 13, 5, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Module1.GotoMain
End Sub

Private Sub CommandButton2_Click()
 Dim FName As String
 FName = Module1.OpenFileDialog("Watershed Timing data file (*.wt), *.wt")
 If (FName <> "") Then
   ReadWatershedFile FName
 End If
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
 
 page1 = "watershed"
 page2 = "tmpData"
 
 CopyData Dir, page1, "F4", page2, "E16" 'Name
 CopyData Dir, page1, "F9", page2, "E19" 'TC given value
 CopyData Dir, page1, "K15", page2, "E18" 'TC Method (Given or Calculated)
 CopyData Dir, page1, "K18", page2, "E20" 'TC Formula for calculation
 CopyData Dir, page1, "I13", page2, "E23" 'Slope
 CopyData Dir, page1, "I15", page2, "E24" 'Length Channel
 
 'SIMAS Method
 CopyData Dir, page1, "I22", page2, "I18" 'Width
 CopyData Dir, page1, "I24", page2, "I19" 'Slope
 If (Dir = 0) Then
 CopyData Dir, page1, "I26", page2, "I20" 'TL
 CopyData Dir, page1, "I17", page2, "E25" 'TC calculated
 End If
End Sub

Private Sub CommandButton4_Click()

'Transfer data to common place
 Copy_Temporal_Data 0
 Module1.GotoMain
End Sub

Private Sub ReadWatershedFile(NFile As String)
Dim Slope As Double
Dim Channel As Double
Dim Area As Double
Dim CN As Double
Dim Tc As Double
Dim D1, D2, D3
Dim WName As String
Dim MethodTc As Integer

ModuleIO.ReadWatershedInfo NFile, WName, Slope, Channel, Tc, MethodTc, Area, CN

Range("F4").value = WName
Range("I13").value = Slope
Range("I15").value = Channel
Range("F9").value = Tc
Range("K15").value = MethodTc
'Range("F6").Value = Area
'Range("I17").Value = CN

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
Slope = Range("I11").value
Channel = Range("I13").value
Tc = Range("F7").value
Area = Worksheets("tmpData").Range("K15").value
CN = Worksheets("tmpData").Range("K17").value
MethodTc = Range("K13").value

ModuleIO.SaveWatershedInfo NFile, WName, Slope, Channel, Tc, MethodTc, Area, CN
End Sub


Private Sub Clear_Data()
 
End Sub

Private Sub CommandButton5_Click()
  Module1.W5Help "W5Tc.pdf"
End Sub

Private Sub CommandButton6_Click()
 Module1.Goto_CNS 0
End Sub

Private Sub Worksheet_Activate()
 Copy_Temporal_Data 1
End Sub

Private Sub Worksheet_SelectionChange(ByVal Target As Range)

End Sub

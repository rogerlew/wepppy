Attribute VB_Name = "ModuleIO"


Sub SaveWatershedInfo(NFile As String, WName As String, Slope As Double, Channel As Double, Tc As Double, MethodTc As Integer, Area As Double, CN As Double)
Dim isProject As Boolean

isProject = (NFile = "")
  
  If (isProject = False) Then
   Open NFile For Output As #1
  End If
  Write #1, WName
  Write #1, Slope, Channel, Tc, MethodTc
  Write #1, Area, CN
  If (isProject = False) Then Close #1
End Sub

Sub ReadWatershedInfo(NFile As String, ByRef WName As String, ByRef Slope As Double, ByRef Channel As Double, ByRef Tc As Double, ByRef MethodTc As Integer, ByRef Area As Double, ByRef CN As Double)
Dim isProject As Boolean

isProject = (NFile = "")
If (isProject = False) Then
  Open NFile For Input As #1
End If
Input #1, WName
Input #1, Slope, Channel, Tc, MethodTc
Input #1, Area, CN
If (isProject = False) Then Close #1
End Sub

Sub SaveMyProject()
 'SaveWatershedInfo "testfile.txt", "watershed1", 19, 3000, 0.4, 1, 1000, 84
 Open "demo2.txt" For Output As #1
 SaveWatershedInfo "", "watershed1", 19, 3000, 0.4, 1, 1000, 84
 Close #1
End Sub

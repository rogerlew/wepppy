Attribute VB_Name = "Module1"

#If VBA7 Then
Private Declare PtrSafe Function ShellExecute Lib "shell32.dll" Alias "ShellExecuteA" _
(ByVal hwnd As Long, ByVal lpOperation As String, ByVal lpFile As String, _
ByVal lpParameters As String, ByVal lpDirectory As String, ByVal nShowCmd As Long) As Long

Public Declare PtrSafe Function SetCurrentDirectory Lib "kernel32" Alias "SetCurrentDirectoryA" _
(ByVal lpPathName As String) As Long

#Else
Private Declare Function ShellExecute Lib "shell32.dll" Alias "ShellExecuteA" _
(ByVal hwnd As Long, ByVal lpOperation As String, ByVal lpFile As String, _
ByVal lpParameters As String, ByVal lpDirectory As String, ByVal nShowCmd As Long) As Long

Public Declare Function SetCurrentDirectory Lib "kernel32" Alias "SetCurrentDirectoryA" _
(ByVal lpPathName As String) As Long

#End If


Dim DisplaySummary As Boolean


Option Explicit

Public Enum PathReturn
    GetPath = 1
    GetFile = 0
End Enum

Public Function StripFileOrPath(FullPath As String, _
    ReturnType As PathReturn) As String
     '   =====================================================================
     '   Returns either the FileName or the Path from a given Full FileName
     '   1st Arg = Pass a files full name (C:\Example\MyFile.xls)
     '   2nd Arg = What to return (either the file name or the path
     '             Enumerated for easier selection
     '   =====================================================================
    Dim szPathSep As String
    szPathSep = Application.PathSeparator
     
    Dim szCut As String
    szCut = CStr(Empty)
     
    Dim I As Long
    I = Len(FullPath)
     
    Dim szPath As String
    Dim szFile As String
     
    If I > 0 Then
         
        Do While szCut <> szPathSep
             
            szCut = Mid$(FullPath, I, 1)
             
            If szCut = szPathSep Then
                 
                szPath = Left$(FullPath, I)
                szFile = Right$(FullPath, Len(FullPath) - I)
                 
            End If
             
            I = I - 1
        Loop
         
        Select Case ReturnType
        Case GetPath
            StripFileOrPath = szPath
        Case GetFile
            StripFileOrPath = szFile
        End Select
         
    Else
         
        StripFileOrPath = CStr(Empty)
         
    End If
     
End Function

Sub W5Help(FName As String)
Dim FileName As String
FileName = StripFileOrPath(ThisWorkbook.FullName, GetPath) & "\" & FName

'Filename = Application.DefaultFilePath & "\" & fname
'MsgBox FileName
ShellExecute 0, "Open", FileName, "", "", vbNormalNoFocus
End Sub


Sub InitVars()
 ' Only happens when file is opened
 
 DisplaySummary = True
End Sub

Function DSummary(Change As Boolean) As Boolean
  
  If (Change = True) Then
    DisplaySummary = False
  End If
  
  DSummary = DisplaySummary
End Function

Sub GotoMain()
Attribute GotoMain.VB_Description = "Macro recorded 10/18/2007 by abm"
Attribute GotoMain.VB_ProcData.VB_Invoke_Func = " \n14"
   Sheets("main").Select
    Range("L3").Select
End Sub
Sub GotoWC5_Message()
    Sheets("W5Message").Select
    Range("B2").Select
End Sub
Sub ExitWildcat()
  GotoWC5_Message
  ActiveWorkbook.Close True
  Application.Quit
End Sub
Sub GotoWatershed()
Attribute GotoWatershed.VB_Description = "Macro recorded 10/18/2007 by abm"
Attribute GotoWatershed.VB_ProcData.VB_Invoke_Func = " \n14"
Dim Rexcess_option As Byte

    Rexcess_option = Worksheets("tmpData").Range("E3").value
    If (Rexcess_option > 2) Then
      Sheets("watershed2").Select
      Range("F4").Select
     Else
      GotoWatershed1 True
    End If
    
End Sub
Sub GotoWatershed1(flag)
 Sheets("watershed").Select
 Range("F4").Select
End Sub
Sub GotoStorm()
Attribute GotoStorm.VB_Description = "Macro recorded 10/18/2007 by abm"
Attribute GotoStorm.VB_ProcData.VB_Invoke_Func = " \n14"
    Sheets("storm").Select
    Range("F5").Select
End Sub
Sub GotoUH()
    Sheets("UnitH").Select
    Range("B1").Select
End Sub
Sub GotoRainfallExcess()
    Sheets("rainfallex").Select
    Range("B2").Select
End Sub
Sub Goto_CustomStorm()
    Sheets("cstorm").Select
    Range("C1").Select
End Sub
Sub Storm_DisableButton()
 Sheet3.Storm_EnableButton -1
End Sub
Sub GotoOutput()
Attribute GotoOutput.VB_Description = "Macro recorded 10/18/2007 by abm"
Attribute GotoOutput.VB_ProcData.VB_Invoke_Func = " \n14"
    Sheets("output").Select
    Range("B2").Select
End Sub

Sub GotoSummaryTable()
    Sheets("SummaryTable").Select
    Range("A1").Select
End Sub
Sub GotoTable()
Attribute GotoTable.VB_Description = "Macro recorded 10/18/2007 by abm"
Attribute GotoTable.VB_ProcData.VB_Invoke_Func = " \n14"

    Sheets("table").Select
    Range("B10").Select
End Sub
Sub GotoGraph1()
Attribute GotoGraph1.VB_Description = "Macro recorded 10/18/2007 by abm"
Attribute GotoGraph1.VB_ProcData.VB_Invoke_Func = " \n14"
    Sheets("graph1").Select
    Range("C1").Select
End Sub

Sub GotoGraph2()
    Sheets("graph2").Select
    Range("C1").Select
End Sub

Sub GotoGraph3()
    Sheets("graph3").Select
    Range("C1").Select
End Sub
Sub GotoGraph5()
    Sheets("graph5").Select
    Range("C1").Select
End Sub
Sub GotoRouting()
    Sheets("routing").Select
    Range("C1").Select
End Sub

Sub GotoRout_table()
    Sheets("routable").Select
    Range("C1").Select
End Sub

Sub Goto_DistributeF()
    Sheets("DistriF").Select
    Range("E6").Select
End Sub
Sub Goto_CNS(id As Byte)
    'id=0, from Watershed, id=1 from RainfallExcess
    Sheets("CNS").Select
    Sheet23.SetFrom_Origin id
    Range("E6").Select
End Sub
Sub GotoRout_graph()
    Sheets("graph4").Select
    Range("C1").Select
End Sub
Sub GotoProject()
Dim IOption As Integer
 Load frproject
 IOption = frproject.GetProjectI
 Unload frproject
 
 If IOption = 2 Then
  W5OpenFile_Project
 End If
 
 If IOption = 3 Then
  W5SaveFile_Project
 End If
End Sub

Sub ChangeToUH()
 Worksheets("UnitH").Range("BA3").value = 2
End Sub

Sub ChangeRainfallExcess()
  Sheet14.Change_myRainfallExcess
End Sub

Sub GotoAbout()
 Load frAbout
 frAbout.Show
 Unload frAbout
End Sub

Sub GotoDisclaimer()
 Load frDisclaimer
 frDisclaimer.Show
 Unload frDisclaimer
End Sub


Sub GotoGenericStorm()
 Load frGeneric
 frGeneric.Show
 Unload frGeneric
End Sub
Sub ShowHelp(Topic)
 Load frHelp
 frHelp.Show_Help_Start Topic, ""
 Unload frHelp
End Sub

Sub GotoWait(xTime)
    Sheets("wait").Select
    Sheets("wait").Range("G7").value = xTime
    Range("C3").Select
End Sub


Function OpenFileDialog(zFilter As String) As String
 Dim filex As String
 Dim wildcatpath As String
 
 wildcatpath = ThisWorkbook.Path
 SetCurrentDirectory (wildcatpath)
 filex = Application.GetOpenFilename(FileFilter:=zFilter, Title:="Open File", MultiSelect:=False)

 If filex = "False" Then filex = ""
  
  OpenFileDialog = filex
End Function

Function SaveFileDialog(zFname As String, zFilter As String) As String
Dim filex As String
Dim wildcatpath As String
Dim oldstate As Boolean


 wildcatpath = ThisWorkbook.Path
 SetCurrentDirectory (wildcatpath)
 
 oldstate = Application.DisplayAlerts
 Application.DisplayAlerts = True
  filex = Application.GetSaveAsFilename(InitialFileName:=zFname, FileFilter:=zFilter, Title:="Save File")
 Application.DisplayAlerts = oldstate
 
 If filex = "False" Then filex = ""
 SaveFileDialog = filex
End Function


Function W5OpenFile(zFilter As String) As String
 Dim filex As String

 filex = Application.GetOpenFilename(FileFilter:="watershed file (*.wcp), *.wcp", _
   Title:="Open File", MultiSelect:=False)

  filex = Application.GetOpenFilename(FileFilter:="watershed file (*.wcp), *.wcp", _
   Title:="Open File", MultiSelect:=False)


If filex <> False Then
 'mname = Dir(filex)
'wkb.SaveAs Filename:=hpath & mname
End If
End Function






Function W5OpenFile_Watershed(id)
Dim filex As String
   
   
  filex = Application.GetOpenFilename(FileFilter:="Watershed Timing data file (*.wt), *.wt", _
   Title:="Open File", MultiSelect:=False)
     
  If filex = "False" Then filex = ""
   W5OpenFile_Watershed = filex
End Function


Sub W5OpenFile_Project()
Dim filex As String
  filex = OpenFileDialog("WildCat5 Project (*.w5p), *.w5p")
  
End Sub

Sub W5SaveFile_Project()
Dim filex As String
 filex = SaveFileDialog("", "WildCat5 Project (*.w5p), *.w5p")
  
End Sub

Function W5SaveFile_Watershed(id) As String
Dim filex As String
  filex = Application.GetSaveAsFilename(FileFilter:="Watershed Timing file (*.wt), *.wt", _
   Title:="Save File")
   
 If filex = "False" Then filex = ""
 W5SaveFile_Watershed = filex
End Function



Sub W5OpenFile_UH()
Dim filex As String
  filex = Application.GetOpenFilename(FileFilter:="Storm data file (*.uh), *.uh", _
   Title:="Open File", MultiSelect:=False)
   
  If filex <> "False" Then
   Sheet23.ReadUHFile filex
  End If
End Sub

Sub W5SaveFile_UH(NRows As Integer)
Dim filex As String
  Application.DisplayAlerts = True
  filex = Application.GetSaveAsFilename(InitialFileName:="", FileFilter:="Storm data file (*.uh), *.uh", _
   Title:="Save File")
  If filex <> "False" Then Sheet23.SaveUHFile filex, NRows
   
End Sub




Sub W5SaveFile_HYD()
Dim filex As String
  filex = Application.GetSaveAsFilename(FileFilter:="Hydrograph file (*.hyd), *.hyd", _
   Title:="Save File")
   If filex <> "False" Then
   routing.export_hyd filex
   End If
End Sub



Function getName_RainfallExcess(valor As Boolean)
 Dim Cad As String
 Dim Method As Byte
 Dim page As String
 Dim CadUnits As String
 Dim UMetric As Boolean
 
 
 UMetric = isMetric_IN()
 If (UMetric = True) Then
  CadUnits = "mm/hr"
 Else
  CadUnits = "in/hr"
 End If
 
 page = "tmpData"
  Method = Worksheets(page).Range("E3").value
  Cad = ""
  If (Method = 1) Then
    Cad = "Curve Number ="
    Cad = Cad & "  " & Format(Worksheets(page).Range("E27").value, "#,##0.00")
  End If
  If (Method = 2) Then
   Cad = "Curve Number (S0.05)"
  End If
  If (Method = 3) Then Cad = "Distributed Infiltrations"
  If (Method = 4) Then
   Cad = "Phi Index"
   Cad = Cad & " " & Worksheets(page).Range("E10").value & CadUnits
  End If
  If (Method = 5) Then
   Cad = "Infiltration mu"
   Cad = Cad & " " & Worksheets(page).Range("E7").value & CadUnits
  End If
  If (Method = 6) Then Cad = "Green Ampt"
  If (Method = 7) Then
    Cad = "Linear Fraction"
    Cad = Cad & " " & Worksheets(page).Range("E11").value
  End If
  If (Method = 8) Then Cad = "Complacent - Violent"
  getName_RainfallExcess = Cad
End Function


Function getName_StormDist()
 Dim Cad As String
 Dim Method As Byte
  Method = Worksheets("tmpData").Range("R7").value
  Cad = ""
  If (Method = 1) Then Cad = "NEH4B"
  If (Method = 2) Then Cad = "Farmer - Fletcher"
  If (Method = 3) Then Cad = "Uniform"
  If (Method = 4) Then Cad = "Custom"
  If (Method = 5) Then Cad = "Generic"
  
  getName_StormDist = Cad
End Function

Function getName_Tc()
 Dim Cad As String
 Dim Method As Byte
 Dim MethodInput As Byte
 
 Cad = ""
 
  MethodInput = Worksheets("tmpData").Range("E18").value
  If (MethodInput = 1) Then
   Cad = "Given"
  ElseIf (MethodInput = 3) Then
    Cad = "SIMAS TL "
   Else
    Method = Worksheets("tmpData").Range("E20").value
    If (Method = 1) Then Cad = "Kirpich's"
    If (Method = 2) Then Cad = "Kent's"
  End If
  
  getName_Tc = Cad
End Function


Function getName_UnitHyd()
 Dim Cad As String
 Dim Method As Byte
 Dim Method2 As Byte
 
  Method = Worksheets("UnitH").Range("BA3").value
  Cad = ""
  If (Method = 1) Then Cad = "Simple Triangular UH (HF=484)"
  If (Method = 2) Then
   Cad = "Triangular Variable HF = "
   Method2 = Worksheets("UnitH").Range("AX21").value
   If (Method2 = 1) Then Cad = Cad & "645.33"
   If (Method2 = 2) Then Cad = Cad & "516.27"
   If (Method2 = 3) Then Cad = Cad & "484"
   If (Method2 = 4) Then Cad = Cad & "430.22"
   If (Method2 = 5) Then Cad = Cad & "387.20"
   If (Method2 = 6) Then Cad = Cad & "252"
   If (Method2 = 7) Then Cad = Cad & "322.67"
   If (Method2 = 8) Then Cad = Cad & "258.13"
   If (Method2 = 9) Then Cad = Cad & "215.11"
  End If
  If (Method = 4) Then Cad = "Broken Triangle (HF=358.52)"
  If (Method = 3) Then Cad = "SCS Dimensionless Curvilinear (HF=484)"
  
  getName_UnitHyd = Cad
End Function



Function isMetric_OUT()

  isMetric_OUT = (Worksheets("main").Range("F15").value = 1)
End Function

Function isMetric_IN()
isMetric_IN = (Worksheets("main").Range("F14").value = 1)
End Function

Sub ChangeMetricINLabels()
 Dim UMetric As Boolean
 Dim page As String
 Dim X As Byte
 page = "tmpData"
 UMetric = isMetric_IN()
 X = 0
 If (UMetric = False) Then X = 1
 
 Worksheets(page).Cells(35, 9).value = Worksheets(page).Cells(35, 7 + X)
 Worksheets(page).Cells(36, 9).value = Worksheets(page).Cells(36, 7 + X)
 Worksheets(page).Cells(37, 9).value = Worksheets(page).Cells(37, 7 + X)
 Worksheets(page).Cells(38, 9).value = Worksheets(page).Cells(38, 7 + X)
 Worksheets(page).Cells(39, 9).value = Worksheets(page).Cells(39, 7 + X)
 Worksheets(page).Cells(40, 9).value = Worksheets(page).Cells(40, 7 + X)
 Worksheets(page).Cells(41, 9).value = Worksheets(page).Cells(41, 7 + X)
 Worksheets(page).Cells(42, 9).value = Worksheets(page).Cells(42, 7 + X)
 Worksheets(page).Cells(43, 9).value = Worksheets(page).Cells(43, 7 + X)
 Worksheets(page).Cells(44, 9).value = Worksheets(page).Cells(44, 7 + X)
 
 Load frUnits
 frUnits.ShowMensaje UMetric
 Unload frUnits
 
End Sub

Sub SetResetRouting(how As Boolean)
If (how = True) Then
  Worksheets("tmpData").Range("C42").value = "0"
 Else
  Worksheets("tmpData").Range("C42").value = "1"
 End If

End Sub

Function GetResetRouting() As Boolean
Dim xvalue
 xvalue = Worksheets("tmpData").Range("C42").value
 GetResetRouting = (xvalue = "0")
End Function

Sub RoutingDLG(forceIt As Boolean)
Dim RunIt As Boolean

  If (forceIt = True) Then
   RunIt = True
  Else
   RunIt = GetResetRouting()
  End If
  
  If (RunIt = True) Then
   Load frRouting
   frRouting.routing False
   Unload frRouting
  
  Else
   'go directly to results
   
   Sheets("routing").Select
   Range("C1").Select
   ActiveCell.FormulaR1C1 = "."
  End If
  
End Sub


Sub SummaryDLG(cadena As String)
  Load frSummary
  frSummary.Set_Summary cadena
  Unload frSummary
End Sub

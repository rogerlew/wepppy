Attribute VB_Name = "Sheet5"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton2, 2, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 1, 1, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Worksheets("tmpdata").Range("R4").value = Range("E6").value
 Worksheets("tmpdata").Range("R7").value = 4
 Module1.GotoStorm
End Sub

Private Sub CommandButton2_Click()
 Module1.W5Help "W5CustomStorm.pdf"
End Sub

Private Sub Worksheet_Activate()
Dim StormName As String
 StormName = Worksheets("storm").Range("F5").value
 Range("E6").value = StormName
End Sub



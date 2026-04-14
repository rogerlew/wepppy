Attribute VB_Name = "Sheet8"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton5, 4780, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 4778, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 5, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 4777, 4, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Module1.GotoMain
End Sub


Private Sub CommandButton2_Click()
 Module1.W5Help "W5TRIUHYD.pdf"
End Sub

Private Sub CommandButton3_Click()
Module1.W5Help "W5BrokenTUH.pdf"
End Sub



Private Sub CommandButton5_Click()
Module1.W5Help "W5CurvyUH.pdf"
End Sub

Attribute VB_Name = "Sheet11"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton6, 10, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 1, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 2, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 5, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 8, 4, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 9, 5, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Module1.GotoRout_table
End Sub

Private Sub CommandButton2_Click()
 Module1.GotoRout_graph
End Sub

Private Sub CommandButton3_Click()
Module1.GotoMain
End Sub

Private Sub CommandButton4_Click()
 Module1.RoutingDLG (True)
 Range("B1").Select
End Sub

Private Sub CommandButton5_Click()
 Module1.GotoOutput
End Sub

Private Sub CommandButton6_Click()
 Module1.W5Help "W5Routing.pdf"
End Sub

Attribute VB_Name = "Sheet10"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Attribute VB_Control = "CommandButton8, 1284, 0, MSForms, CommandButton"
Attribute VB_Control = "CommandButton7, 1283, 1, MSForms, CommandButton"
Attribute VB_Control = "CommandButton6, 1282, 2, MSForms, CommandButton"
Attribute VB_Control = "CommandButton1, 1023, 3, MSForms, CommandButton"
Attribute VB_Control = "CommandButton2, 1024, 4, MSForms, CommandButton"
Attribute VB_Control = "CommandButton3, 1279, 5, MSForms, CommandButton"
Attribute VB_Control = "CommandButton4, 1280, 6, MSForms, CommandButton"
Attribute VB_Control = "CommandButton5, 1281, 7, MSForms, CommandButton"
Private Sub CommandButton1_Click()
 Module1.GotoOutput
End Sub

Private Sub CommandButton2_Click()
 Module1.GotoMain
End Sub

Private Sub CommandButton3_Click()
Module1.GotoGraph1
End Sub

Private Sub CommandButton4_Click()
Module1.GotoGraph2
End Sub

Private Sub CommandButton5_Click()
Module1.GotoGraph5
End Sub

Private Sub CommandButton6_Click()
 Module1.GotoTable
End Sub

Private Sub CommandButton7_Click()
 Module1.GotoSummaryTable
End Sub

Private Sub CommandButton8_Click()
 Module1.RoutingDLG (False)
End Sub

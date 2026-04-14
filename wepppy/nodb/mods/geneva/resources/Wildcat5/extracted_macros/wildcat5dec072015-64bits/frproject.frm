Attribute VB_Name = "frproject"
Attribute VB_Base = "0{6709727C-B5EA-492E-8874-F7D9B23B12C9}{8B8B8A7A-69D2-4301-B328-DF31438733F8}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Dim IOption As Integer


Private Sub CommandButton1_Click()
End Sub

Private Sub CommandButton2_Click()
 IOption = 2
 frproject.Hide
End Sub

Private Sub CommandButton3_Click()
 IOption = 3
 frproject.Hide
End Sub

Private Sub CommandButton4_Click()
 IOption = 0
 frproject.Hide
End Sub


Function GetProjectI() As Integer
 frproject.Show
 
 GetProjectI = IOption
End Function

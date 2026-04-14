Attribute VB_Name = "frHelp"
Attribute VB_Base = "0{384690AB-B1AD-4144-8D60-A151C90C5D0A}{E3B0D2E3-13D8-4451-AA5C-E511609C71EF}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Private Sub CommandButton1_Click()
 frHelp.Hide
End Sub

Sub help_DIF()

Dim Cad As String

Cad = "Distributed infiltration capacity:   Parameter Selection and Background"
Cad = Cad & "Parameter Selection   Responsible selection of muf  for use in the"
Cad = Cad & "model here is a choice left to the judgment and"
Cad = Cad & "experience of the user, as well as local conditions."
Cad = Cad & "There are no formally developed  authoritative tables for muf ;"
Cad = Cad & "use of the technique here is developmental. However, as an average,"
Cad = Cad & "steady-state infiltration velocity it is related to point equilibrium rates found elsewhere."
Cad = Cad & "In this light, the following are offered for suggestions, guide, and perspective only."
Cad = "Ks is the saturated hydraulic conductivity, or the steady-state rate found in some ideal"

 TextBox1.Text = Cad
End Sub

Sub Show_Help_Start(Topic, TxtHelp)
  Label1.Caption = Topic
  help_DIF
  frHelp.Show
  
End Sub

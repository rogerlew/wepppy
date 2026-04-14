Attribute VB_Name = "frGeneric"
Attribute VB_Base = "0{EBF77A33-60E9-4285-84F8-EA72E510680A}{A1FC376C-7CE2-4504-B7DA-5B686143E654}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Private Sub CommandButton1_Click()
Dim MinValue As Double
Dim MaxValue As Double

 MinValue = TextBox1.value
 If (MinValue > 0) Then
   MaxValue = TextBox3.value
  If (MaxValue > 0 And MaxValue < 100) Then
   Worksheets("storm").Range("F5").value = TextBox4.value
   Set_GenericStorm TextBox1.value, TextBox2.value, TextBox3.value, TextBox4.value
   frGeneric.Hide
  Else
   MsgBox "Maximumn Storm Intensity value incorrect"
  End If
 Else
  MsgBox "Mininum Storm Intensity value must be greater than zero"
 End If
End Sub

Private Sub CommandButton2_Click()
 frGeneric.Hide
End Sub

Private Sub CommandButton3_Click()
 TextBox1.value = 1
 TextBox2.value = 500
 TextBox3.value = 50
 TextBox4.value = "Example Generic Storm"
End Sub

Private Sub CommandButton4_Click()
 Module1.W5Help "W5GenericStorm.pdf"
End Sub

Private Sub UserForm_Initialize()
 'get stored values
 Dim SName As String
 SName = "tmpData"
 TextBox1.value = Worksheets(SName).Range("N5").value
 TextBox2.value = Worksheets(SName).Range("N6").value
 TextBox3.value = Worksheets(SName).Range("N7").value
 TextBox4.value = Worksheets(SName).Range("N4").value
End Sub

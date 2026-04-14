Attribute VB_Name = "frCover"
Attribute VB_Base = "0{678DD3BA-F466-40DE-8421-91D2AEBBE097}{8BB628FB-F071-441A-9D31-BAEED9F7AFFE}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False

Private isUMetric As Boolean
Private XMu As Double

Private Sub SetVegetative(value As Double, isEnabled As Boolean)
  TextBox1.value = value
  TextBox1.Enabled = isEnabled
  If (isEnabled = True) Then
  TextBox1.BackColor = &H80000005
  Else
  TextBox1.BackColor = &HE0E0E0
  End If
  
End Sub


Private Sub Calculate()
 Dim CG As Double
 Dim CC As Double
 Dim Keb As Double
 Dim Ke As Double
 
 Dim Vegetative As Double
 Dim Clay As Double
 Dim Mu As Double
 Dim ErrorList As String
 
 ErrorList = ""
 
 Vegetative = TextBox1.value
 If (Vegetative < 0 Or Vegative > 1) Then ErrorList = "Vegetative Fraction"
 
 CG = TextBox2.value
 If (CG < 0 Or CG > 1) Then ErrorList = ErrorList + Chr(13) + "Ground Cover Fraction"
 CC = TextBox3.value
 If (CC < 0 Or CC > 1) Then ErrorList = ErrorList + Chr(13) + "Canopy Cover Fraction"
 Clay = TextBox4.value
 If (Clay < 0 Or Clay > 1) Then ErrorList = ErrorList + Chr(13) + "Clay Fraction"
 
 
 If (ErrorList = "") Then
  Keb = 0.174 - 1.45 * Clay + 2.975 * CG + 0.923 * CC
  Keb = (1 / 3) * Exp(Keb)
  Ke = Keb * Vegetative
  Mu = 8 * Exp(0.0912 * Ke)
  CommandButton2.Enabled = True
  
  TextBox5.value = Format(Keb, "#,##0.000")
  TextBox8.value = Format(Keb / 25.4, "#,##0.000")
  TextBox6.value = Format(Ke, "#,##0.000")
  TextBox9.value = Format(Ke / 25.4, "#,##0.000")
  TextBox7.value = Format(Mu, "#,##0.000")
  TextBox10.value = Format(Mu / 25.4, "#,##0.000")
  
  If (isUMetric = True) Then
   XMu = Mu
  Else
   XMu = Mu / 25.4
  End If
 Else
  CommandButton2.Enabled = False
  ErrorList = "Please check the following values: " + Chr(13) + ErrorList
  MsgBox ErrorList
 End If
 

End Sub

Private Sub CommandButton1_Click()
  Calculate
End Sub

Private Sub CommandButton2_Click()
 frCover.Hide
 
End Sub

Private Sub CommandButton3_Click()
 XMu = -1
 frCover.Hide
End Sub

Private Sub CommandButton4_Click()
Module1.W5Help "W5Cover.pdf"
End Sub

Private Sub OptionButton1_Click()
  SetVegetative 0.8, False
End Sub

Private Sub OptionButton2_Click()
 SetVegetative 1, False
End Sub

Private Sub OptionButton3_Click()
 SetVegetative 1.2, False
End Sub

Private Sub OptionButton4_Click()
 SetVegetative 1, True
End Sub




Private Sub UserForm_Initialize()
 OptionButton1_Click
 CommandButton2.Enabled = False
End Sub

 Function CoverDlg(isMetric As Boolean)
  isUMetric = isMetric
  frCover.Show
  CoverDlg = XMu
End Function

Attribute VB_Name = "frCN"
Attribute VB_Base = "0{1373BBA4-B04A-4F82-8764-B9DFF6E8C319}{5DB1DBBC-31AA-46F8-BFC8-22C5FC317BAE}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Dim CNA, CNB, CNC, CND, CNSelected


Private Sub SetVals(a, b, C, d)
 CNA = a
 CNB = b
 CNC = C
 CND = d
End Sub

Private Sub getCNS(index)
  If (index = 0) Then SetVals 77, 86, 91, 94
  If (index = 1) Then SetVals 72, 81, 88, 91
  If (index = 2) Then SetVals 67, 78, 85, 89
  If (index = 3) Then SetVals 70, 79, 84, 88
  If (index = 4) Then SetVals 65, 75, 82, 86
  If (index = 5) Then SetVals 66, 74, 80, 82
  If (index = 6) Then SetVals 62, 71, 78, 81
  If (index = 7) Then SetVals 65, 76, 84, 88
  If (index = 8) Then SetVals 63, 75, 83, 87
  If (index = 9) Then SetVals 63, 74, 82, 85
  If (index = 10) Then SetVals 61, 73, 81, 84
  If (index = 11) Then SetVals 61, 72, 79, 82
  If (index = 12) Then SetVals 59, 70, 78, 81
  If (index = 13) Then SetVals 66, 77, 85, 89
  If (index = 14) Then SetVals 58, 72, 81, 85
  If (index = 15) Then SetVals 58, 72, 81, 85
  If (index = 16) Then SetVals 64, 75, 83, 85
  If (index = 17) Then SetVals 55, 69, 78, 83
  If (index = 18) Then SetVals 63, 73, 80, 83
  If (index = 19) Then SetVals 68, 79, 86, 89
  If (index = 20) Then SetVals 49, 69, 79, 84
  If (index = 21) Then SetVals 39, 61, 74, 80
  If (index = 22) Then SetVals 47, 67, 81, 88
  If (index = 23) Then SetVals 25, 59, 75, 83
  If (index = 24) Then SetVals 6, 35, 70, 79
  If (index = 25) Then SetVals 30, 58, 71, 78
  If (index = 26) Then SetVals 45, 66, 77, 83
  If (index = 27) Then SetVals 36, 60, 73, 79
  If (index = 28) Then SetVals 25, 55, 70, 77
  If (index = 29) Then SetVals 59, 74, 82, 86
  If (index = 30) Then SetVals 72, 82, 87, 89
  If (index = 31) Then SetVals 74, 84, 90, 92
End Sub

Private Function getCNCad(index)
Dim Cad As String
  getCNS index
  getCNCad = "      " & CNA & "  " & CNB & "  " & CNC & "  " & CND
End Function

Private Sub CommandButton1_Click()
Dim index As Integer

 index = ListBox1.ListIndex
 getCNS index
 
 If (OptionButton1.value = True) Then CNSelected = CNA
 If (OptionButton2.value = True) Then CNSelected = CNB
 If (OptionButton3.value = True) Then CNSelected = CNC
 If (OptionButton4.value = True) Then CNSelected = CND
 
 frCN.Hide
End Sub

Private Sub CommandButton2_Click()
 CNSelected = -1
 frCN.Hide
End Sub

Private Sub UserForm_Initialize()
 ListBox1.AddItem "Fallow               Straight row    --- " & getCNCad(0)
 ListBox1.AddItem "Row crops            ''              Poor" & getCNCad(1)
 ListBox1.AddItem "                     ''              Good" & getCNCad(2)
 ListBox1.AddItem "                     Contoured       Poor" & getCNCad(3)
 ListBox1.AddItem "                     ''              Good" & getCNCad(4)
 ListBox1.AddItem "                     and terraced    Poor" & getCNCad(5)
 ListBox1.AddItem "                     ''              Good" & getCNCad(6)
 ListBox1.AddItem "Small grain          Straight row    Poor" & getCNCad(7)
 ListBox1.AddItem "                     ''              Good" & getCNCad(8)
 ListBox1.AddItem "                     Contoured       Poor" & getCNCad(9)
 ListBox1.AddItem "                     ''              Good" & getCNCad(10)
 ListBox1.AddItem "                     and terraced    Poor" & getCNCad(11)
 ListBox1.AddItem "                     ''              Good" & getCNCad(12)
 ListBox1.AddItem "Close-seeded legumes Straight row    Poor" & getCNCad(13)
 ListBox1.AddItem "or rotation meadow   ''              Good" & getCNCad(14)
 ListBox1.AddItem "                     Contoured       Poor" & getCNCad(15)
 ListBox1.AddItem "                     ''              Good" & getCNCad(16)
 ListBox1.AddItem "                     and terraced    Poor" & getCNCad(17)
 ListBox1.AddItem "                     ''              Good" & getCNCad(18)
 ListBox1.AddItem "Pasture or Range                     Poor" & getCNCad(19)
 ListBox1.AddItem "                                     Fair" & getCNCad(20)
 ListBox1.AddItem "                                     Good" & getCNCad(21)
 ListBox1.AddItem "                     Contoured       Poor" & getCNCad(22)
 ListBox1.AddItem "                     ''              Fair" & getCNCad(23)
 ListBox1.AddItem "                     ''              Good" & getCNCad(24)
 ListBox1.AddItem "Meadow                               Good" & getCNCad(25)
 ListBox1.AddItem "Woods                                Poor" & getCNCad(26)
 ListBox1.AddItem "                                     Fair" & getCNCad(27)
 ListBox1.AddItem "                                     Good" & getCNCad(28)
 ListBox1.AddItem "Farmsteads                           --- " & getCNCad(29)
 ListBox1.AddItem "Roads (dirt)                         --- " & getCNCad(30)
 ListBox1.AddItem " (hard surface)                      --- " & getCNCad(31)
End Sub

Function GetCNTable()
 CNSelected = -1
 frCN.Show
 GetCNTable = CNSelected
End Function

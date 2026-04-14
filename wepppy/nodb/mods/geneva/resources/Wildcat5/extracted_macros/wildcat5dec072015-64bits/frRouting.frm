Attribute VB_Name = "frRouting"
Attribute VB_Base = "0{DB8974B5-3D01-42BF-9D48-C9C9D84BEEB0}{428DA49E-8138-473F-8C72-656A7D7E75B4}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Dim IsRoutingfile As Boolean


Private Sub CommandButton1_Click()

Const M2Ft = 1 / 0.3048, Ha2Acre = 2.4709661

Dim xArea As Double
Dim xLength As Double
Dim xcoeff As Double
Dim xniters As Integer
Dim page As String
Dim isMetricIN As Boolean


page = "tmpData"

 xArea = TextBox1.value
 xLength = TextBox2.value
 xcoeff = TextBox3.value
 xniters = 10
 
 Worksheets(page).Range("N16").value = xArea
 Worksheets(page).Range("N17").value = xLength
 Worksheets(page).Range("N18").value = xcoeff
 Worksheets(page).Range("N19").value = xniters
 
 isMetricIN = Module1.isMetric_IN()
 
 If (isMetricIN = True) Then
  xArea = xArea * Ha2Acre
  xLength = xLength * M2Ft
 End If
 
 If (xLength > 0 And xArea > 0 And xcoeff > 0) Then
  RunRouting xArea, xLength, xcoeff, xniters
  frRouting.Hide
 Else
  MsgBox "Input Data is Incorrect"
 End If
End Sub

Private Sub CommandButton2_Click()
 frRouting.Hide
End Sub


Sub routing(isFile As Boolean)
  IsRoutingfile = isFile
  frRouting.Show
End Sub

Private Sub CommandButton3_Click()
 Module1.W5Help "W5Routing.pdf"
End Sub

Private Sub UserForm_Activate()
 Dim page As String
 page = "tmpData"
 Label4.Caption = Worksheets(page).Range("I38").value
 Label5.Caption = Worksheets(page).Range("I36").value
 TextBox1.value = Worksheets(page).Range("N16").value
 TextBox2.value = Worksheets(page).Range("N17").value
 TextBox3.value = Worksheets(page).Range("N18").value
End Sub


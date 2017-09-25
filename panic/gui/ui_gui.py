"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

from utils import Qt, QtCore, QtGui
from utils import getThemeIcon

class Ui_AlarmList(object):
    def setupUi(self, Form):
        self.Form=Form
        Form.setObjectName("Form")
        #Form.resize(QtCore.QSize(900, 900))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, 
                                       QtGui.QSizePolicy.Expanding)
        #sizePolicy.setHorizontalStretch(100)
        #sizePolicy.setVerticalStretch(100)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setMinimumSize(QtCore.QSize(250, 250))
        Form.setSizeIncrement(QtCore.QSize(1, 1))
        
        #self.splitWidget = Qt.QSplitter(Form)
        
        self.leftWidget = Qt.QWidget(Form)#self.splitWidget)
        
        #self.rightWidget = Qt.QWidget(self.splitWidget)
        #sForm.setBaseSize(QtCore.QSize(200, 200))
        
        self.horizontalLayout_3 = QtGui.QHBoxLayout(Form)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.Form.setLayout(self.horizontalLayout_3)
        
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.frame = QtGui.QFrame(Form)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.frame.setMinimumSize(QtCore.QSize(300, 200))
#------------------------------------------------------------------------------
        self.leftGridLayout = QtGui.QGridLayout(self.frame)
        self.leftGridLayout.setObjectName("leftGridLayout")
        self.comboLabel = QtGui.QLabel(self.frame)
        self.comboLabel.setObjectName("comboLabel")
        #self.comboLabel.setMaximumSize(QtCore.QSize(50, 30))
        self.comboLabel.hide()
        self.leftGridLayout.addWidget(self.comboLabel, 0,0,1,1) #<-------------
        self.contextComboBox = QtGui.QComboBox(self.frame)
        self.contextComboBox.setObjectName("contextComboBox")
        self.leftGridLayout.addWidget(self.contextComboBox,0,1,1,5) #<---------
        #self.comboButton = QtGui.QPushButton(self.frame)
        #self.comboButton.setObjectName("comboButton")
        #self.leftGridLayout.addWidget(self.comboButton,0,5,1,1)
        #self.comboButton2 = QtGui.QPushButton(self.frame)
        #self.comboButton2.setObjectName("comboButton2")
        #self.leftGridLayout.addWidget(self.comboButton2,0,6,1,1)

        self.infoLabel0_1 = QtGui.QLabel(self.frame)
        self.infoLabel0_1.setObjectName("infoLabel0_1")
        #self.infoLabel0_1.setMinimumWidth(60)
        self.leftGridLayout.addWidget(self.infoLabel0_1, 1,0,1,1) #<-------------
        self.infoLabel0_1.hide()
        self.comboBoxx = QtGui.QComboBox(self.frame)
        self.comboBoxx.setObjectName("comboBoxx")
        self.leftGridLayout.addWidget(self.comboBoxx, 1,1,1,5) #<-------------
        self.comboBoxx.hide()
        self.infoLabel1_1 = QtGui.QLabel(self.frame)
        self.infoLabel1_1.setObjectName("infoLabel1_1")
        self.leftGridLayout.addWidget(self.infoLabel1_1, 2,0,1,1) #<-------------
        self.infoLabel1_1.hide()
        self.infoLabel1_2 = QtGui.QLabel(self.frame)
        self.infoLabel1_2.setObjectName("infoLabel1_2")
        self.leftGridLayout.addWidget(self.infoLabel1_2, 2,1,1,5) #<-------------
        self.infoLabel1_2.hide()

        #self.regExGridLayout = QtGui.QGridLayout()
        self.regExLabel = QtGui.QLabel(self.frame)
        self.regExLabel.setObjectName("regExLabel")
        self.regExLabel.setText('Filter:')
        self.leftGridLayout.addWidget(self.regExLabel, 3,0,1,1)
        self.regExLine = QtGui.QLineEdit(self.frame)
        self.regExLine.setObjectName("regExLine")
        self.leftGridLayout.addWidget(self.regExLine, 3,1,1,3)
        self.regExUpdate = QtGui.QPushButton(self.frame)
        self.regExUpdate.setObjectName("regExUpdate")
        self.regExUpdate.setText("Update")
        self.regExSave = QtGui.QPushButton(self.frame)
        self.regExSave.setObjectName("regExSave")
        self.regExSave.setText("Save As")
        self.regExSave.setToolTip("Save in Tango Database")
        self.leftGridLayout.addWidget(self.regExUpdate, 3,4,1,1)
        self.leftGridLayout.addWidget(self.regExSave, 3,5,1,1)
        #self.leftGridLayout.addLayout(self.regExGridLayout, 3,0,1,6) #<-------------

        self.gridFilterLayout = QtGui.QGridLayout()
        #self.gridFilterLayout.addWidget(Qt.QLabel('Severities:'), 2,0,1,1)
        
        #self.sevAlarmLabel = QtGui.QLabel(self.frame)
        #self.sevAlarmLabel.setObjectName("sevAlarmLabel")
        #self.sevAlarmLabel.setText('Alarm')
        ##self.sevAlarmLabel.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.sevAlarmLabel, 1,1,1,1)
        #self.sevErrorLabel = QtGui.QLabel(self.frame)
        #self.sevErrorLabel.setObjectName("sevErrorLabel")
        #self.sevErrorLabel.setText('Error')
        ##self.sevErrorLabel.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.sevErrorLabel, 1,2,1,1)
        #self.sevWarningLabel = QtGui.QLabel(self.frame)
        #self.sevWarningLabel.setObjectName("sevWarningLabel")
        #self.sevWarningLabel.setText('Warning')
        ##self.sevWarningLabel.setAlignment(Qt.Qt.AlignHCenter)        
        #self.gridFilterLayout.addWidget(self.sevWarningLabel, 1,3,1,1)
        #self.sevDebugLabel = QtGui.QLabel(self.frame)
        #self.sevDebugLabel.setObjectName("sevDebugLabel")
        #self.sevDebugLabel.setText('Debug')
        ##self.sevDebugLabel.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.sevDebugLabel, 1,4,1,1)

        #self.sevAlarmCheckBox = QtGui.QCheckBox()
        #self.sevAlarmCheckBox.setObjectName("sevAlarmCheckBox")
        #self.sevAlarmCheckBox.setChecked(True)
        ##self.sevAlarmCheckBox.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.sevAlarmCheckBox, 2,1,1,1)
        #self.sevErrorCheckBox = QtGui.QCheckBox()
        #self.sevErrorCheckBox.setObjectName("sevErrorCheckBox")
        #self.sevErrorCheckBox.setChecked(True)
        ##self.sevErrorCheckBox.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.sevErrorCheckBox, 2,2,1,1)
        #self.sevWarningCheckBox = QtGui.QCheckBox()
        #self.sevWarningCheckBox.setObjectName("sevWarningCheckBox")
        #self.sevWarningCheckBox.setChecked(True)
        ##self.sevWarningCheckBox.setAlignment(Qt.Qt.AlignHCenter)        
        #self.gridFilterLayout.addWidget(self.sevWarningCheckBox, 2,3,1,1)
        #self.sevDebugCheckBox = QtGui.QCheckBox()
        #self.sevDebugCheckBox.setObjectName("sevDebugCheckBox")
        #self.sevDebugCheckBox.setChecked(False)
        ##self.sevDebugCheckBox.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.sevDebugCheckBox, 2,4,1,1)

        ##self.formLayout.addItem(self.gridFilterLayout)
        #self.leftGridLayout.addLayout(self.gridFilterLayout, 4,0,1,6) #<-------------

        #self.verticalLayout_3.addLayout(self.formLayout)
        
        self.activeLabel = QtGui.QLabel(self.frame)
        self.activeLabel.setObjectName("activeLabel")
        self.activeLabel.setText('Show Active Only')
        self.activeLabel.setAlignment(Qt.Qt.AlignRight)
        #self.gridFilterLayout.addWidget(self.activeLabel, 1,5,1,1)
        self.gridFilterLayout.addWidget(self.activeLabel,0,0,1,2)
        
        self.activeCheckBox = QtGui.QCheckBox()
        self.activeCheckBox.setObjectName("activeCheckBox")
        self.activeCheckBox.setChecked(False)
        #self.gridFilterLayout.addWidget(self.activeCheckBox, 2,5,1,1)
        self.gridFilterLayout.addWidget(self.activeCheckBox,0,2,1,1)       
        
        self.selectLabel = QtGui.QLabel(self.frame)
        self.selectLabel.setObjectName("selectLabel")
        self.selectLabel.setText('Select All/None')
        self.selectLabel.setAlignment(Qt.Qt.AlignRight)
        #self.gridFilterLayout.addWidget(self.selectLabel, 1,0,1,1)
        self.gridFilterLayout.addWidget(self.selectLabel, 0,3,1,1) #<-------------
        self.selectCheckBox = QtGui.QCheckBox()
        self.selectCheckBox.setObjectName("selectCheckBox")
        self.selectCheckBox.setChecked(False)
        #self.selectCheckBox.setAlignment(Qt.Qt.AlignHCenter)
        #self.gridFilterLayout.addWidget(self.selectCheckBox, 2,0,1,1)
        self.gridFilterLayout.addWidget(self.selectCheckBox, 0,4,1,1) #<-------------    
        
        self.leftGridLayout.addLayout(self.gridFilterLayout, 4,0,1,6)
        
        self.listWidget = QtGui.QListWidget(self.frame)
        self.listWidget.setObjectName("listWidget")
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.leftGridLayout.addWidget(self.listWidget, 5,0,1,6) #<-------------
        
        self.statusLabel = QtGui.QLabel('Loading ...')
        self.leftGridLayout.addWidget(self.statusLabel,6,0,1,2) #<-------------
        

                
#----------------------------------------------------------------------------------------------

        self.verticalLayout_2.addWidget(self.frame)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")

        self.refreshButton = QtGui.QPushButton(Form)
        self.refreshButton.setObjectName("refreshButton")
        self.horizontalLayout_2.addWidget(self.refreshButton)
        self.refreshButton.hide()
        self.newButton = QtGui.QPushButton(Form)
        self.newButton.setObjectName("newButton")
        self.horizontalLayout_2.addWidget(self.newButton)
        self.newButton.hide()
        self.deleteButton = QtGui.QPushButton(Form)
        self.deleteButton.setObjectName("deleteButton")
        self.horizontalLayout_2.addWidget(self.deleteButton)
        self.deleteButton.hide()
        self.customButton3 = QtGui.QPushButton(Form)
        self.customButton3.setObjectName("customButton3")
        self.horizontalLayout_2.addWidget(self.customButton3)
        self.customButton3.hide()
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        
        #self.horizontalLayout_3.addLayout(self.verticalLayout_2)
        self.leftWidget.setLayout(self.verticalLayout_2)

        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        #self.horizontalLayout_5 = QtGui.QHBoxLayout()
        #self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        #self.tableLabel = QtGui.QLabel(Form)
        #self.tableLabel.setObjectName("tableLabel")
        #self.horizontalLayout_5.addWidget(self.tableLabel)
        #self.tableLabel.hide()
        #self.tableLabel.setText("tableLabel")
        #self.viewComboBox = QtGui.QComboBox(Form)
        #self.viewComboBox.setObjectName("viewComboBox")
        #self.horizontalLayout_5.addWidget(self.viewComboBox)
        #self.viewComboBox.setLayoutDirection(QtCore.Qt.RightToLeft)
        #self.viewComboBox.addItem("Table View")
        #self.viewComboBox.addItem("Live View")
        #self.viewComboBox.addItem("Compare View")
        #self.viewComboBox.setMaximumWidth(115)
        #self.viewComboBox.hide()
        #self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.frame_2 = QtGui.QFrame(Form)
        self.frame_2.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtGui.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.frame_2.setMinimumSize(QtCore.QSize(300, 200))
        self.gridLayout = QtGui.QGridLayout(self.frame_2)
        self.gridLayout.setObjectName("gridLayout")
        #self.tableWidget = QtGui.QTableWidget(self.frame_2)
        #self.tableWidget.setObjectName("tableWidget")
        #self.tableWidget.setColumnCount(0)
        #self.tableWidget.setRowCount(0)
        #self.gridLayout.addWidget(self.tableWidget)
        #self.tableWidget.hide()
        self.frame_2.hide()
        self.verticalLayout.addWidget(self.frame_2)

        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        #self.customButton4 = QtGui.QPushButton(Form)
        #self.customButton4.setObjectName("customButton4")
        #self.horizontalLayout.addWidget(self.customButton4)
        #self.customButton4.hide()
        #self.customButton5 = QtGui.QPushButton(Form)
        #self.customButton5.setObjectName("customButton5")
        #self.horizontalLayout.addWidget(self.customButton5)
        #self.customButton5.hide()
        self.buttonClose = QtGui.QPushButton(Form)
        self.buttonClose.setObjectName("buttonClose")
        self.buttonClose.setText(QtGui.QApplication.translate("Form", "Close", None, QtGui.QApplication.UnicodeUTF8))
        self.buttonClose.setToolTip(QtGui.QApplication.translate("Form", "Close Application", None, QtGui.QApplication.UnicodeUTF8))
        self.icon_close = getThemeIcon(":/actions/process-stop.svg")
        self.buttonClose.setIcon(self.icon_close)
        self.buttonClose.hide()
        self.horizontalLayout.addWidget(self.buttonClose)
        self.verticalLayout.addLayout(self.horizontalLayout)
        
        #self.horizontalLayout_3.addLayout(self.verticalLayout)
        #self.rightWidget.setLayout(self.verticalLayout)
        
        #self.splitWidget.addWidget(self.leftWidget)
        #self.splitWidget.addWidget(self.rightWidget)
        self.horizontalLayout_3.addWidget(self.leftWidget)#splitWidget)
        
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        
        self.actionExpert = Qt.QAction(None)
        self.actionExpert.setText('Expert View')
        self.actionExpert.setCheckable(True)
        self.actionExpert.setChecked(False)

        
        Form.setWindowTitle("Alarms")

        self.comboLabel.setText("Sort:")
        #self.comboButton.setText("View")

        self.refreshButton.setText("Refresh/Sort List")
        self.refreshButton.setIcon(getThemeIcon("view-refresh"))
        self.newButton.setText("New")
        self.newButton.setIcon(getThemeIcon("window-new"))
        self.deleteButton.setText("Delete")
        self.deleteButton.setIcon(getThemeIcon("edit-clear"))

        self.comboLabel.show()
        self.refreshButton.show()
        self.newButton.show()
        self.deleteButton.show()
        self.comboBoxx.show()
        self.infoLabel0_1.show()
        self.infoLabel1_1.show()

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.infoLabel0_1.setText(QtGui.QApplication.translate("Form", "Attribute", None, QtGui.QApplication.UnicodeUTF8))

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    Form = QtGui.QWidget()
    ui = Ui_AlarmList()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

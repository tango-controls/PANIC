"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import sys, panic, traceback
from utils import Qt, QtCore, QtGui
from utils import getThemeIcon
from utils import iValidatedWidget

class PhoneBook(QtGui.QWidget):
    def __init__(self,parent=None,container=None):
        QtGui.QWidget.__init__(self,parent)
        self._bwi = PhoneBookUi()
        self._bwi.phonebookSetupUi(self)
        self._kontainer = container
        self.buildList()

    def buildList(self):
        self._bwi.buildList()

    def show(self):
        QtGui.QWidget.show(self)

class PhoneBookEntry(iValidatedWidget,object):
    def __init__(self, phoneBook):
        self.pB = phoneBook
        self.api = self.pB.api

    def addSetupUi(self, addForm):
        self._Form=addForm
        addForm.setObjectName("addForm")
        self.addGridLayout = QtGui.QGridLayout(addForm)
        self.addGridLayout.setObjectName("addGridLayout")

        self.sectionLabel = QtGui.QLabel()
        self.sectionLabel.setObjectName("sectionLabel")
        self.sectionLabel.setText("section:")
        #self.addGridLayout.addWidget(self.sectionLabel, 0, 0, 1, 1)
        self.sectionCombo = QtGui.QComboBox()
        self.sectionCombo.setObjectName("sectionCombo")
        sections=['','CONTROLS', 'VACUUM', 'FRONTENDS', 'BEAMLINES', 'On Call']
        for s in sections:
            self.sectionCombo.addItem(s)
        #self.addGridLayout.addWidget(self.sectionCombo, 0, 1, 1, 1)

        self.nameLabel = QtGui.QLabel(addForm)
        self.nameLabel.setObjectName("emailLabel")
        self.nameLabel.setText("name:")
        self.addGridLayout.addWidget(self.nameLabel, 1, 0, 1, 1)
        self.nameLine = QtGui.QLineEdit(addForm)
        self.nameLine.setObjectName("nameLine")
        self.addGridLayout.addWidget(self.nameLine, 1, 1, 1, 1)

        self.emailLabel = QtGui.QLabel(addForm)
        self.emailLabel.setObjectName("emailLabel")
        self.emailLabel.setText("email:")
        self.addGridLayout.addWidget(self.emailLabel, 2, 0, 1, 1)
        self.emailLine = QtGui.QLineEdit(addForm)
        self.emailLine.setObjectName("emailLine")
        self.addGridLayout.addWidget(self.emailLine, 2, 1, 1, 1)

        self.smsHorizontalLayout = QtGui.QHBoxLayout()
        self.smsHorizontalLayout.setObjectName("smsHorizontalLayout")
        self.smsCheckBox = QtGui.QCheckBox()
        self.smsCheckBox.setObjectName("smsCheckBox")
        self.smsHorizontalLayout.addWidget(self.smsCheckBox)
        self.smsLabel = QtGui.QLabel(addForm)
        self.smsLabel.setObjectName("smsLabel")
        self.smsLabel.setText("sms ?")
        self.smsLabel.setEnabled(False)
        self.smsHorizontalLayout.addWidget(self.smsLabel)
        self.smsLine = QtGui.QLineEdit(addForm)
        self.smsLine.setObjectName("emailLine")
        self.smsHorizontalLayout.addWidget(self.smsLine)
        self.smsLine.setEnabled(False)
        self.addGridLayout.addLayout(self.smsHorizontalLayout, 3, 0, 1, 2)

        self.addHorizontalLayout = QtGui.QHBoxLayout()
        self.addHorizontalLayout.setObjectName("addHorizontalLayout")
        self.addButton = QtGui.QPushButton(addForm)
        self.addButton.setObjectName("addButton")
        self.addHorizontalLayout.addWidget(self.addButton)
        self.cancelButton = QtGui.QPushButton(addForm)
        self.cancelButton.setObjectName("cancelButton")
        self.addHorizontalLayout.addWidget(self.cancelButton)
        self.addGridLayout.addLayout(self.addHorizontalLayout, 4, 0, 1, 2)

        self.addRetranslateUi(addForm)
        QtCore.QMetaObject.connectSlotsByName(addForm)

    def addRetranslateUi(self, addForm):
        addForm.setWindowTitle(QtGui.QApplication.translate("addForm", "Add Recipient", None, QtGui.QApplication.UnicodeUTF8))
        self.addButton.setText(QtGui.QApplication.translate("addForm", "Add", None, QtGui.QApplication.UnicodeUTF8))
        self.addButton.setIcon(getThemeIcon("list-add"))
        self.addButton.setToolTip("Add person to the list")
        self.cancelButton.setText(QtGui.QApplication.translate("addForm", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.cancelButton.setIcon(getThemeIcon("process-stop"))
        self.cancelButton.setToolTip("Cancel")
        addForm.resize(250, 150)

        QtCore.QObject.connect(self.addButton,QtCore.SIGNAL("clicked()"), self.onAdd)
        QtCore.QObject.connect(self.cancelButton,QtCore.SIGNAL("clicked()"), self.onCancel)
        QtCore.QObject.connect(self.smsCheckBox,QtCore.SIGNAL("stateChanged(int)"), self.onCheckStateChanged)

    def onAdd(self):
        try:
            section = str(self.sectionCombo.currentText())
            name = str(self.nameLine.text()).upper()
            name = '%'+name if not name.startswith('%') else name
            email = str(self.emailLine.text())
            if not self.validate('Phonebook.onAdd(%s,%s,%s)'%(section,name,email)):
                return
            if self.smsCheckBox.isChecked(): 
                number = str(self.smsLine.text())
                number =  'SMS:'+number if not number.startswith('SMS:') else number
                if number: email+=','+number
            if (not name):
                message='Type name\n'
                raise Exception(message)
            elif (not email and not number):
                message='Type email address\n'
                raise Exception(message)
            else:
                print 'onAdd.edit_phoneBook(%s,%s,(%s))'%(name,email,section)
                self.api.edit_phonebook(name,email,section)
        except Exception:
            Qt.QMessageBox.critical(None,"Error", traceback.format_exc())
            return
        self.onCancel()
        self.pB.onRefresh()
        Qt.QMessageBox.information(None,"Phonebook","%s added succesfully!"%name)

    def onCancel(self):
        self._Form.close()

    def onCheckStateChanged(self, state):
        if state==0:
            self.smsLabel.setEnabled(False)
            self.smsLine.setEnabled(False)
        else:
            self.smsLabel.setEnabled(True)
            self.smsLine.setEnabled(True)

class PhoneBookUi(object):
    api=None
    def __init__(self,api=None):
        type(self).api = api or self.api or panic.current()
        object.__init__(self)

    def phonebookSetupUi(self, Form):
        Form.setObjectName("Form")
        self.diffGridLayout = QtGui.QGridLayout(Form)
        self.diffGridLayout.setObjectName("diffGridLayout")
        self.tableWidget = QtGui.QTableWidget(Form)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.diffGridLayout.addWidget(self.tableWidget, 0, 0, 1, 1)
        self.lowerHorizontalLayout = QtGui.QHBoxLayout()
        self.lowerHorizontalLayout.setObjectName("lowerHorizontalLayout")
        self.addButton = QtGui.QPushButton(Form)
        self.addButton.setObjectName("addButton")
        self.lowerHorizontalLayout.addWidget(self.addButton)
        self.removeButton = QtGui.QPushButton(Form)
        self.removeButton.setObjectName("removeButton")
        self.lowerHorizontalLayout.addWidget(self.removeButton)
        self.refreshButton = QtGui.QPushButton(Form)
        self.refreshButton.setObjectName("refreshButton")
        self.lowerHorizontalLayout.addWidget(self.refreshButton)
        self.diffGridLayout.addLayout(self.lowerHorizontalLayout, 1, 0, 1, 2)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Phonebook", None, QtGui.QApplication.UnicodeUTF8))
        self.addButton.setText(QtGui.QApplication.translate("Form", "Add", None, QtGui.QApplication.UnicodeUTF8))
        self.addButton.setIcon(getThemeIcon("list-add"))
        self.addButton.setToolTip("Add person to the list")
        self.removeButton.setText(QtGui.QApplication.translate("Form", "Remove", None, QtGui.QApplication.UnicodeUTF8))
        self.removeButton.setIcon(getThemeIcon("list-remove"))
        self.removeButton.setToolTip("Remove person from list")
        self.refreshButton.setText(QtGui.QApplication.translate("Form", "Refresh", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setIcon(getThemeIcon("view-refresh"))
        self.refreshButton.setToolTip("Refresh list")

        QtCore.QObject.connect(self.tableWidget, QtCore.SIGNAL("itemDoubleClicked(QTableWidgetItem *)"), self.onEdit)
        QtCore.QObject.connect(self.addButton,QtCore.SIGNAL("clicked()"), self.onAdd)
        QtCore.QObject.connect(self.removeButton,QtCore.SIGNAL("clicked()"), self.onRemove)
        QtCore.QObject.connect(self.refreshButton,QtCore.SIGNAL("clicked()"), self.onRefresh)
        Form.resize(430, 800)

    def buildList(self):
        data=self.api.get_phonebook()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setRowCount(len(data))
        #self.tableWidget.setHorizontalHeaderLabels(["",""])
        #print data
        i = 0
        for name,value in sorted(data.items()):
            for k in (name,value):
                item = QtGui.QTableWidgetItem(k)
                #if k.split('#')[0].strip():
                    #item.setFlags(QtCore.Qt.ItemIsEnabled)
                if not (i/2)%2:
                    item.setBackgroundColor(QtGui.QColor(225,225,225))
                self.tableWidget.setItem(int(i/2),i%2,item)
                i+=1
            self.tableWidget.resizeColumnsToContents()

    def onEdit(self):
        ##pid=self.tableWidget.currentRow()-1
        ##alter=(str(self.tableWidget.item(pid,1).text()))
        ##self.api.edit_phonebook(alter)
        #self.buildList()
        name,value = map(str,(self.tableWidget.item(self.tableWidget.currentRow(),0).text(),self.tableWidget.item(self.tableWidget.currentRow(),1).text()))
        print 'PhoneBook.onEdit(%s,%s)'%(name,value)
        try:
            self.prompt = Qt.QWidget()
            self.promptUi = PhoneBookEntry(self)
            self.promptUi.addSetupUi(self.prompt)
            self.promptUi.nameLine.setText(name)
            self.promptUi.emailLine.setText(value)
            self.prompt.show()
        except:
            print traceback.format_exc()

    def onAdd(self):
        try:
            self.prompt = Qt.QWidget()
            self.promptUi = PhoneBookEntry(self)
            self.promptUi.addSetupUi(self.prompt)
            self.prompt.show()
        except:
            print traceback.format_exc()

    def onRemove(self):
        name,value = map(str,(self.tableWidget.item(self.tableWidget.currentRow(),0).text(),self.tableWidget.item(self.tableWidget.currentRow(),1).text()))
        reply=Qt.QMessageBox.question(None,"Remove","Do You Want to Remove %s?"%name, Qt.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
        if reply == QtGui.QMessageBox.Yes:
            try:
                self.api.remove_phonebook(name)
                self.onRefresh()
                Qt.QMessageBox.information(None,"Remove","%s Removed"%name)
            except:
                print traceback.format_exc()
                Qt.QMessageBox.critical(None,"Problem", "Could not remove selected person<br>")

    def onRefresh(self):
        self.buildList()

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    form = PhoneBook()
    form.show()
    sys.exit(app.exec_())

from PyQt4 import Qt, QtCore, QtGui
from taurus.qt.qtgui.resource import getThemeIcon
import panic, fandango
from widgets import iLDAPValidatedWidget


class dacWidget(QtGui.QWidget):
    def __init__(self,parent=None,container=None,device=None):
        QtGui.QWidget.__init__(self,parent)
        self._dacwi = devattrchangeForm()
        self._dacwi.devattrchangeSetupUi(self)
        self._kontainer = container
        self.setDevCombo(device)

    def setDevCombo(self,device=None):
        #self._dacwi.setComboBox(True,self._dacwi.api.devices)
        self._dacwi.setDevCombo(device)

    def show(self):
        QtGui.QWidget.show(self)
        
class devattrchangeForm(iLDAPValidatedWidget,object):
    api=None
    def __init__(self,api=None):
        print 'creating devattrchangeForm ...'
        type(self).api = api or self.api or panic.current()
        object.__init__(self)
    
    def devattrchangeSetupUi(self, Form):
        self.Form = Form
        Form.setObjectName("Form")
        self.GridLayout = QtGui.QGridLayout(Form)
        self.GridLayout.setObjectName("GridLayout")
        self.deviceCombo = QtGui.QComboBox(Form)
        self.deviceCombo.setObjectName("deviceCombo")
        self.GridLayout.addWidget(self.deviceCombo, 0, 0, 1, 1)
        self.tableWidget = QtGui.QTableWidget(Form)
        self.tableWidget.setObjectName("tableWidget")
        self.GridLayout.addWidget(self.tableWidget, 1, 0, 1, 1)
        self.refreshButton = QtGui.QPushButton(Form)
        self.refreshButton.setObjectName("refreshButton")
        self.GridLayout.addWidget(self.refreshButton, 2, 0, 1, 1)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "PyAlarm Device Configuration", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setText(QtGui.QApplication.translate("Form", "Refresh", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setIcon(getThemeIcon("view-refresh"))
        self.refreshButton.setToolTip("Refresh list")

        QtCore.QObject.connect(self.tableWidget, QtCore.SIGNAL("itemChanged(QTableWidgetItem *)"), self.onEdit)
        QtCore.QObject.connect(self.deviceCombo, QtCore.SIGNAL("currentIndexChanged(QString)"), self.buildList)
        QtCore.QObject.connect(self.refreshButton, QtCore.SIGNAL("clicked()"), self.buildList)
        Form.resize(430, 600)

    def setDevCombo(self,device=None):
        self.deviceCombo.clear()
        devList=self.api.devices
        [self.deviceCombo.addItem(QtCore.QString(d)) for d in self.api.devices]
        self.deviceCombo.model().sort(0, Qt.Qt.AscendingOrder)
        print 'setDevCombo(%s)'%device
        if device in self.api.devices: 
            i = self.deviceCombo.findText(device)
            print '\t%s at %s'%(device,i)
            self.deviceCombo.setCurrentIndex(i)
        else:
            print '\t%s not in AlarmsAPI!'%device

    def buildList(self,device=None):
        self.tableWidget.blockSignals(True)
        index = -1 if device is None else self.deviceCombo.findText(device)
        if index<0:
            device = str(self.deviceCombo.currentText())
        else:
            self.deviceCombo.setCurrentIndex(index)
        device = str(device)
        data=self.api.devices[device].get_config(True) #get_config() already manages extraction and default values replacement
        print '%s properties: %s' % (device,data)
        rows=len(data)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setRowCount(rows)
        self.tableWidget.setHorizontalHeaderLabels(["Attribute Name", "Attribute Value"])
        for row,prop in enumerate(sorted(panic.ALARM_CONFIG)):
            for col in (0,1):
                if not col:
                    item=QtGui.QTableWidgetItem("%s" % prop)
                    item.setFlags(QtCore.Qt.ItemIsEnabled)
                else:
                    item=QtGui.QTableWidgetItem("%s" % data[prop])
                if row%2==0:
                    item.setBackgroundColor(QtGui.QColor(225,225,225))
                self.tableWidget.setItem(row, col, item)
        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.blockSignals(False)

    def onEdit(self):
        try:
            row=self.tableWidget.currentRow()
            dev=self.api.devices[str(self.deviceCombo.currentText())]
            if not self.validate('onEditDeviceProperties(%s)'%dev):
                return
            prop=str(self.tableWidget.item(row,0).text())
            value=str(self.tableWidget.item(row,1).text())
            print 'DeviceAttributeChanger.onEdit(%s,%s = %s)'%(dev,prop,value)
            ptype=fandango.device.cast_tango_type(panic.PyAlarmDefaultProperties[prop][0]).__name__
            if(value):
                dev.put_property(prop, value)
                dev.init()
            else:
                raise Exception('%s must have a value!'%prop)
        except Exception,e:
            Qt.QMessageBox.warning(self.Form,"Warning",'Exception: %s'%e)
        finally:
            self.buildList()

if __name__ == "__main__":
    import sys
    app=QtGui.QApplication(sys.argv)
    Form=QtGui.QWidget()
    ui=devattrchangeForm()
    ui.devattrchangeSetupUi(Form)
    Form.show()
    ui.setDevCombo()
    sys.exit(app.exec_())
from utils import Qt, QtCore, QtGui, getThemeIcon

import panic, fandango, taurus

class htmlviewForm(object):
    def __init__(self,alarm_api=None):
        if not hasattr(htmlviewForm,'panicApi'):
            htmlviewForm.panicApi=alarm_api or panic.AlarmAPI()
        pass

    def htmlviewSetupUi(self, Form):
        self._Form=Form
        Form.setObjectName("Form")
        self.GridLayout=QtGui.QGridLayout(Form)
        self.GridLayout.setObjectName("GridLayout")
        self.textWidget=QtGui.QTextEdit(Form)
        self.textWidget.setObjectName("textWidget")
        #self.textWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.GridLayout.addWidget(self.textWidget, 0, 0, 1, 2)
        self.refreshButton=QtGui.QPushButton(Form)
        self.refreshButton.setObjectName("refreshButton")
        self.GridLayout.addWidget(self.refreshButton, 2, 0, 1, 2)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Details", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setText(QtGui.QApplication.translate("Form", "Refresh", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setIcon(getThemeIcon("view-refresh"))
        self.refreshButton.setToolTip("Refresh list")

        QtCore.QObject.connect(self.refreshButton, QtCore.SIGNAL("clicked()"), self.onRefresh)

    def onRefresh(self):
        print('refresh')

    def buildReport(self, alarm):
        report = taurus.Device(self.panicApi[alarm].device).command_inout('GenerateReport',[alarm])[0]
        self.displayReport(report)

    def displayReport(self, report):
        self.textWidget.setReadOnly(True)
        self.textWidget.setText(report) #html

if __name__ == "__main__":
    import sys
    app=QtGui.QApplication(sys.argv)
    Form=QtGui.QWidget()
    ui=htmlviewForm()
    ui.htmlviewSetupUi(Form)
    Form.show()
    sys.exit(app.exec_())

"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import panic, fandango
from utils import *
from operator import itemgetter

class ahWidget(QtGui.QWidget):
    def __init__(self,parent=None,container=None):
        QtGui.QWidget.__init__(self,parent)
        self._ah = alarmhistoryForm()
        self._kontainer = container
        self._ah.alarmhistorySetupUi(self)

    def setAlarmCombo(self, alarm=None):
        print('ahWidget.setAlarmCombo(%s)' % str(alarm))
        self._ah.setAlarmCombo(alarm=alarm or 'All')

    def show(self):
        #self._ah.alarmhistorySetupUi(self)
        QtGui.QWidget.show(self)
        self.setAlarmCombo(alarm='All')
        
class snapWidget(QtGui.QWidget):
  
    def __init__(self,parent=None,container=None):
        print('>>>> snapWidget()')
        QtGui.QWidget.__init__(self,parent)
        import PyTangoArchiving.widget.snaps as snaps
        self._swi = snaps.SnapForm()
        self._swi.setupUi(self,load=False)
        self._kontainer=container

    def initContexts(self,attrlist=[], sid=None):
        self._swi.initContexts(attrlist, sid)

    def onContextChanged(self, pos):
        self._swi.onContextChanged(pos)

    def show(self):
        QtGui.QWidget.show(self)

class alarmhistoryForm(object):
  
    def __init__(self,alarm_api=None,snap_api=None):

        print('>>>> alarmhistoryForm()')
        self._ready = False
        if not hasattr(alarmhistoryForm,'panicApi'):
            alarmhistoryForm.panicApi = alarm_api or panic.AlarmAPI()
            alarmhistoryForm.snapApi = None #snap_api or get_snap_api()

    def alarmhistorySetupUi(self, Form):
        if self._ready: return
        self._Form=Form
        Form.setObjectName("Form")
        self.GridLayout=QtGui.QGridLayout(Form)
        self.GridLayout.setObjectName("GridLayout")
        self.alarmCombo=QtGui.QComboBox(Form)
        self.alarmCombo.setObjectName("alarmCombo")
        self.alarmCombo.setToolTip("Choose an Alarm")
        self.GridLayout.addWidget(self.alarmCombo, 0, 0, 1, 2)
        self.tableWidget=QtGui.QTableWidget(Form)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tableWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.GridLayout.addWidget(self.tableWidget, 1, 0, 1, 2)
        self.viewButton=QtGui.QPushButton(Form)
        self.viewButton.setObjectName("viewButton")
        self.GridLayout.addWidget(self.viewButton, 2, 0, 1, 1)
        self.refreshButton=QtGui.QPushButton(Form)
        self.refreshButton.setObjectName("refreshButton")
        self.GridLayout.addWidget(self.refreshButton, 2, 1, 1, 1)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        #self._Form.resize(self._Form.sizeHint().width()+150, 500)
        self._Form.setFixedWidth(800) #, 500)
        self._Form.setFixedHeight(600)
        self._ready = True

    def retranslateUi(self, Form):
      
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Alarm History Viewer", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setText(QtGui.QApplication.translate("Form", "Refresh", None, QtGui.QApplication.UnicodeUTF8))
        self.refreshButton.setIcon(getThemeIcon("view-refresh"))
        self.refreshButton.setToolTip("Refresh list")
        self.viewButton.setText(QtGui.QApplication.translate("Form", "Open Snapshot", None, QtGui.QApplication.UnicodeUTF8))
        self.viewButton.setIcon(getThemeIcon("face-glasses"))
        self.viewButton.setToolTip("Open Snapshot")
        QtCore.QObject.connect(self.alarmCombo, QtCore.SIGNAL("currentIndexChanged(QString)"), self.buildList)
        QtCore.QObject.connect(self.refreshButton, QtCore.SIGNAL("clicked()"), self.onRefresh)
        QtCore.QObject.connect(self.viewButton, QtCore.SIGNAL("clicked()"), self.onOpen)
        QtCore.QObject.connect(self.tableWidget, QtCore.SIGNAL("itemDoubleClicked(QTableWidgetItem *)"), self.onDouble)
        QtCore.QObject.connect(self.tableWidget, QtCore.SIGNAL("customContextMenuRequested(const QPoint&)"), self.onContextMenu)

    def setAlarmCombo(self, alarm=None):
        print('In alarmHistoryForm.setAlarmCombo(%s)' % str(alarm))
        self.alarmCombo.blockSignals(True)
        pos=self.alarmCombo.currentIndex()
        self.alarmCombo.clear()
        self.alarms=self.panicApi.alarms
        for a in self.alarms.items():
            self.alarmCombo.addItem(self.alarms[a[0]].tag+': '+self.alarms[a[0]].formula)
        self.alarmCombo.model().sort(0, Qt.Qt.AscendingOrder)
        self.alarmCombo.insertItem(0,QtCore.QString('All'))
        if alarm:
            pos=self.alarmCombo.findText(QtCore.QString(alarm), QtCore.Qt.MatchStartsWith)
            self.alarmCombo.setCurrentIndex(pos)
        elif pos>=0: 
            self.alarmCombo.setCurrentIndex(pos)
        self.buildList()
        self.alarmCombo.blockSignals(False)
        #self._Form.resize(self._Form.sizeHint().width()+150, 500)

    def buildList(self):
        self.tableWidget.blockSignals(True)
        try:
            if SNAP_ALLOWED and self.snapApi is None:
              self.snapApi = get_snap_api()
            if not self.snapApi:
              v = QtGui.QMessageBox.warning(None,'Snap!', \
                'Snaps not available',QtGui.QMessageBox.Ok)
              return
              
            alarm=str(self.alarmCombo.currentText())
            if (alarm=='All'):
                ctxs=[]
                self.alarms=self.panicApi.alarms
                for a in self.alarms.items():
                    if(self.snapApi.db.search_context(self.alarms[a[0]].tag)):
                        ctx=self.snapApi.db.search_context(self.alarms[a[0]].tag)
                        for c in ctx: ctxs.append(c)
            else:
                ctxs=self.snapApi.db.search_context(alarm.split(':',1)[0])
            cids=[]
            for c in ctxs:
                if (c['reason']=='ALARM'):
                    cids.append(c['id_context'])
            data=[]
            for cid in cids:
                ctx=self.snapApi.get_context(cid)
                snaps=ctx.get_snapshots().values()
                for s in snaps:
                    data.append([s[0],ctx.name,s[1]])
            data.sort(key=itemgetter(0), reverse=True)
            rows=len(data)
            self.tableWidget.setRowCount(rows if rows else 1)
            self.tableWidget.setColumnCount(3 if rows else 1)
            self.tableWidget.clear()
            if rows: self.tableWidget.setHorizontalHeaderLabels(["Date", "Alarm", "Comment"])
            else: self.tableWidget.setHorizontalHeaderLabels([""])
            if rows>0:
                for row in range(0, rows):
                    for col in range(0, 3):
                        item=QtGui.QTableWidgetItem("%s" % data[row][col])
                        item.setFlags(QtCore.Qt.ItemIsSelectable)
                        if row%2!=0:
                            item.setBackgroundColor(QtGui.QColor(225,225,225))
                        self.tableWidget.setItem(row, col, item)
                if not self.viewButton.isEnabled():
                    self.viewButton.setEnabled(True)
                    self.refreshButton.setEnabled(True)
            else:
                item=QtGui.QTableWidgetItem("%s" % QtCore.QString('No Data!'))
                item.setFlags(QtCore.Qt.ItemIsSelectable)
                self.tableWidget.setItem(0, 0, item)
                if self.viewButton.isEnabled():
                    self.viewButton.setEnabled(False)
                    self.refreshButton.setEnabled(False)
        except:
            traceback.print_exc()
        self.tableWidget.blockSignals(False)
        self.tableWidget.resizeColumnsToContents()

    def onContextMenu(self, point):
        self.popMenu=QtGui.QMenu()
        self.popMenu.addAction("Open Snapshot",self.onOpen)
        self.popMenu.addSeparator()
        self.popMenu.addAction("Refresh LIst",self.onRefresh)
        self.popMenu.exec_(self.tableWidget.mapToGlobal(point))
        
    def onDouble(self):
        self.onOpen()

    def onOpen(self):
        SnapApp=snapWidget(container=self._Form)
        self.snap=SnapApp.show
        row=self.tableWidget.currentRow()
        item = self.tableWidget.item(row,1)
        if item is None:
            QtGui.QMessageBox.warning(None,'No row selected', \
                'Select a Row first!',QtGui.QMessageBox.Ok)            
        else:
            try:
                self.ctx_name=str(item.text())
                self.snap_date=str(self.tableWidget.item(row,0).text())
                res=self.snapApi.db.search_context(self.ctx_name)
                for c in res:
                    if c['reason']=='ALARM':
                        self.ctx_id=c['id_context']
                        break
                self.ctx=self.snapApi.get_context(self.ctx_id)
                res=sorted(self.ctx.get_snapshots().items(), reverse=True)
                pos=0;
                for s in res:
                    if str(s[1][0])==self.snap_date: break
                    pos+=1
                print(self.ctx)
                print(self.ctx_id)
                print(res)
                print(pos)                    
                SnapApp.initContexts(self.ctx_id, pos)
                self.snap()
            except:
                QtGui.QMessageBox.warning(None,'Error!', \
                    traceback.format_exc(),QtGui.QMessageBox.Ok)     

    def onRefresh(self):
        row=self.tableWidget.currentRow()
        self.panicApi.load()
        self.setAlarmCombo()
        self.tableWidget.setCurrentCell(row,1)

if __name__ == "__main__":
    import sys
    app=QtGui.QApplication(sys.argv)
    Form=QtGui.QWidget()
    ui=alarmhistoryForm()
    ui.alarmhistorySetupUi(Form)
    Form.show()
    ui.onRefresh()
    sys.exit(app.exec_())

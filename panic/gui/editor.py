import sys, re
import panic
from PyQt4 import QtCore, QtGui, Qt
from ui_data import Ui_Data,Ui_ReceiversLine
from ui_data import uiBodyForm,uiRowForm
from taurus.qt.qtgui.resource import getThemeIcon
from widgets import AlarmValueLabel,setCheckBox,getAlarmReport,get_user,trace
from widgets import AttributesPreview,AlarmPreview,iLDAPValidatedWidget
from fandango.excepts import Catched

#AlarmFormula widget is added to the editor in the ui_data.py file

try:
    from alarmhistory import *
except Exception,e:
    #print 'UNABLE TO LOAD SNAP ... HISTORY VIEWER DISABLED: ',str(e)
    SNAP_ALLOWED=False

#get_next_index = lambda d: max([0]+list(d))+1

###########################################################################################
# AlarmEditor forms

FormParentClass = Qt.QDialog

class AlarmForm(FormParentClass,iLDAPValidatedWidget): #(QtGui.QWidget):
    
    __pyqtSignals__ = ("valueChanged",)
    
    def __init__(self,parent=None):
        FormParentClass.__init__(self,parent)
        self._message = QtGui.QMessageBox(self)
        self._wi = Ui_Data()
        self._wi.setupUi(self)
        self.setMinimumWidth(500)
        self._dataWidget = self
        self.fromAlarmGUI()
        self.api = panic.current()
        self.setCurrentAlarm(None)
        self.enableEditForm(False)
        self._parent = parent
            
    def setCurrentAlarm(self,alarm=None):
        if isinstance(alarm,panic.Alarm):
            self._currentAlarm = alarm
        elif not alarm or alarm not in self.api:
            self._currentAlarm = panic.Alarm('')
        else:
            self._currentAlarm = self.api[alarm]
        print 'AlarmForm.setCurrentAlarm(%s)'%self._currentAlarm
        try: self._wi.formulaTextEdit.setModel(self._currentAlarm)
        except: traceback.print_exc()
        return self._currentAlarm
        
    def getCurrentAlarm(self,update=False):
        return self._currentAlarm
    
    def fromAlarmGUI(self):
        self.formulaeditor=FormulaEditor(self._dataWidget)#self._dataWidget._wi.frame)
        self._receiversLine=ReceiversForm()
        self.prepareLineWidget()
        #self._ui.gridLayout.addWidget(self._dataWidget)
        self._dataWidget._wi.formulaStacked.addWidget(self.formulaeditor)
        
        QtCore.QObject.connect(self._receiversLine._wi.okButton, QtCore.SIGNAL("clicked(bool)"), self.onPlusOk) # Add
        QtCore.QObject.connect(self.formulaeditor._ui.rowEditButton, QtCore.SIGNAL("clicked(bool)"), self.onRowEdit)
        
        QtCore.QObject.connect(self._dataWidget._wi.addReceiversButton, QtCore.SIGNAL("clicked(bool)"), self.onPlus)
        QtCore.QObject.connect(self._dataWidget._wi.previewButton, QtCore.SIGNAL("clicked()"), self.showAlarmPreview)
        QtCore.QObject.connect(self._dataWidget._wi.cancelButton, QtCore.SIGNAL("clicked()"), self.onCancel) # "Cancel"
        QtCore.QObject.connect(self._dataWidget._wi.saveButton, QtCore.SIGNAL("clicked()"), self.onSave) # "Save"
        QtCore.QObject.connect(self._dataWidget._wi.editButton, QtCore.SIGNAL("clicked()"), self.onEdit) # "Edit"
        QtCore.QObject.connect(self._dataWidget._wi.disabledCheckBox, QtCore.SIGNAL("stateChanged(int)"), self.onDisStateChanged)
        QtCore.QObject.connect(self._dataWidget._wi.ackCheckBox, QtCore.SIGNAL("stateChanged(int)"), self.onAckStateChanged)
        QtCore.QObject.connect(self._dataWidget._wi.deviceConfig, QtCore.SIGNAL("clicked()"), self.onDeviceConfig)
        
        self._dataWidget._wi.nameLineEdit.setClickHook(self.onEdit)
        self._dataWidget._wi.deviceLineEdit.setClickHook(self.onEdit)
        self._dataWidget._wi.severityLineEdit.setClickHook(self.onEdit)
        self._dataWidget._wi.receiversLineEdit.setClickHook(self.onEdit)
        self._dataWidget._wi.descriptionTextEdit.setClickHook(self.onEdit)
        self._dataWidget._wi.formulaTextEdit.setClickHook(self.onEdit)
        
    def showAlarmPreview(self):
        self.preview = AlarmPreview(tag=self.getCurrentAlarm().tag,formula=self._wi.formulaTextEdit.toPlainText(),parent=self.parent())
        self.preview.connect(self.preview.upperPanel,Qt.SIGNAL('onSave'),
            lambda obj,s=self:(s.enableEditForm(False),s.setAlarmData(obj)))
        from widgets import WindowManager
        WindowManager.addWindow(self.preview)
        self.preview.show()
        
    def showAlarmReport(self):
        #qd = Qt.QDialog(self.parent())
        self.report = getAlarmReport(alarm=self.getCurrentAlarm(),parent=self.parent())
        self.report.setModal(True)
        #form.setParent(qd)
        self.report.exec_()
        
    def onSettingExpert(self):
        self.clearAlarmData()
        self.enableEditForm(False)
        
    def onDeviceConfig(self):
        from widgets import dacWidget
        self.dac = dacWidget(device=self.getCurrentAlarm().device)
        self.dac.show()
        
    ###########################################################################
    # AlarmEditor

    def onEdit(self,alarm=None):
        if alarm: self.setCurrentAlarm(alarm)
        alarm = self.getCurrentAlarm()
        print "AlarmForm.onEdit(%s)"%alarm
        
        self.setAlarmData(alarm)
        self.enableEditForm(True)
        
    def onNew(self):
        print'onNew()'
        self.clearAlarmData()
        self.enableEditForm(True)
        self._tvl.updateStyle()

    def onSave(self):
        print'onSave()'+'<'*80
        if self.checkEmptyFields() and self.validate('onSave',self._currentAlarm.tag):
            old_name = self.getCurrentAlarm().tag
            self.saveData(old_name = old_name) #<- it will save data and will remove unused alarm rows
            self.enableEditForm(False)
        else:
            self._message.critical(self, "Critical", "Alarm not saved!")
        self.valueChanged()

    def onCancel(self):
        print'onCancel()'
        self.formulaeditor.Clr()
        self.setAlarmData()
        self.enableEditForm(not(self.getCurrentAlarm() and self.getCurrentAlarm().tag))
    
    def onPlus(self):
        self._receiversLine.show()

    def onRowEdit(self, bool):
        self.formulaeditor._ui.formulaLineEdit.setReadOnly(bool)

    def onPlusOk(self):
        text = self._dataWidget._wi.receiversLineEdit.text()
        newText = self._receiversLine._wi.receiversCombo.currentText()
        if text:
            newText = ','.join([str(text), str(newText)])
        self._dataWidget._wi.receiversLineEdit.setText(newText)
        
    def ResetAlarm(self,alarm=None):
        prompt,cmt=QtGui.QInputDialog,''
        alarms = [self.getCurrentAlarm()]
        msg = 'The following alarms will be reseted:\n\t'+'\n\t'.join([t.tag for t in alarms])
        print 'In AlarmGUI.ResetAlarm(): %s'%msg
        while len(cmt)==0:
            cmt, ok=prompt.getText(self,'Input dialog',msg+'\n\n'+'Must type a comment to continue:')
            if not ok: return
        comment=get_user()+': '+cmt
        for alarm in alarms:
            try: alarm.reset(comment) #It also tries to reset hidden alarms
            except: print traceback.format_exc()
        self.valueChanged()

    def AcknowledgeAlarm(self):
        """THIS METHOD IS NEVER CALLED!?!?!?!?!?!?!"""
        alarm = self.getCurrentAlarm()
        print 'In AlarmForm.AcknowledgeAlarm(%s)' % (alarm.tag)
        comment, ok = QtGui.QInputDialog.getText(self,'Input dialog','Type a comment to continue:')
        comment = get_user()+': '+comment
        if ok and len(str(comment)) != 0:
            try:
                alarm.reset(comment) #... Why it resets instead of Acknowledge?
                #taurus.Device(alarm.device).command_inout('Acknowledge',[tag, comment])
            except:
                print traceback.format_exc()
            self.valueChanged()
        elif ok and len(str(comment)) < 3:
            self.AcknowledgeAlarm()
            
    def valueChanged(self):
        print 'AlarmForm.valueChanged()'
        self.emit(Qt.SIGNAL('valueChanged'))
        
    ###########################################################################

    def prepareLineWidget(self):
        #Setup of the State/Details/Reset line in the editor widget
        self.w = Qt.QWidget()
        self.w.setLayout(Qt.QHBoxLayout())
        self._tvl = AlarmValueLabel(self.w)
        self._tvl.setShowQuality(False)
        self._detailsButton = Qt.QPushButton(self.w)
        self._detailsButton.setText('Last Report')
        self._detailsButton.setIcon(getThemeIcon("edit-find"))
        self._detailsButton.connect(self._detailsButton,Qt.SIGNAL("clicked()"),self.showAlarmReport)
        self._detailsButton.setEnabled(False)
        self._resetButton = Qt.QPushButton(self.w)
        self._resetButton.setText('Reset')
        self._resetButton.setIcon(getThemeIcon("edit-undo"))
        self._resetButton.connect(self._resetButton,Qt.SIGNAL("clicked()"),self.ResetAlarm)
        self._resetButton.setEnabled(False)
        self.w.layout().addWidget(self._tvl)
        self.w.layout().addWidget(self._detailsButton)
        self.w.layout().addWidget(self._resetButton)
        self._dataWidget._wi.horizontalLane.addWidget(self.w)

    def clearAlarmData(self):
        print "AlarmForm.clearAlarmData()"
        self.setCurrentAlarm()
        self._dataWidget._wi.nameLineEdit.clear()
        self._dataWidget._wi.deviceLineEdit.clear()
        self._dataWidget._wi.descriptionTextEdit.clear()
        self._dataWidget._wi.receiversLineEdit.clear()
        self._dataWidget._wi.severityLineEdit.clear()
        self._dataWidget._wi.formulaTextEdit.clear()
        self.formulaeditor.Clr()
        
    def setComboBox(self, comboBox, values, sort=False):
#        print "setRecData"
        comboBox.clear()
        [comboBox.addItem(QtCore.QString(i)) for i in values]
        if sort: comboBox.model().sort(0, Qt.Qt.AscendingOrder)

    def setAlarmData(self,alarm=None):
        #This method is called from listWidget.currentRowChanged() event
        
        if alarm: self.setCurrentAlarm(alarm)
        print 'AlarmForm.setAlarmData(%s)'%(self.getCurrentAlarm())
        self.setWindowTitle('ALARM: %s'%self.getCurrentAlarm().tag)

        #print 'PanicGUI.setAlarmData(%d,%s@%s): %s-%s since %s,dis:%s,ack:%s'%(
            #i,self.alarm.tag,self.alarm.device,row.value,row.quality,time.ctime(self.alarm.active),row.alarmDisabled,row.alarmAcknowledged)
            
        alarm = self.getCurrentAlarm()

        self._dataWidget._wi.nameLineEdit.setText(alarm.tag)
        self._dataWidget._wi.deviceLineEdit.setText(alarm.device)
        self._dataWidget._wi.descriptionTextEdit.setText(alarm.description)
        self._dataWidget._wi.severityLineEdit.setText(alarm.severity)
        self._dataWidget._wi.receiversLineEdit.setText(alarm.receivers)
        self._dataWidget._wi.formulaTextEdit.setText(alarm.formula)

        self._tvl.setModel(alarm.device+'/'+alarm.get_attribute())
        self._dataWidget._wi.previewButton.setEnabled(True)
        self._dataWidget._wi.editButton.setEnabled(True)
        if alarm.get_active():
            self._detailsButton.setEnabled(True)
            self._resetButton.setEnabled(True)
        else: 
            self._detailsButton.setEnabled(False)
            self._resetButton.setEnabled(False)
        setCheckBox(self._dataWidget._wi.disabledCheckBox,not alarm.get_enabled())
        setCheckBox(self._dataWidget._wi.ackCheckBox,alarm.acknowledged)
        return
        
    def enableDelete(self, tmp):
#        print "activeDelete"
        self._ui.deleteButton.setEnabled(tmp>=0)
        return tmp>=0

    def enableEditForm(self, b):
        """
        This method prepares the widget to be editable
        """
        #Enables writing of data widgets
        #self._ui.deleteButton.setEnabled(not b)
        self._dataWidget._wi.nameLineEdit.setReadOnly(not b)
        self._dataWidget._wi.descriptionTextEdit.setReadOnly(not b)
        self._dataWidget._wi.receiversLineEdit.setReadOnly(not b)
        self._dataWidget._wi.addReceiversButton.setEnabled(b)
        self._dataWidget._wi.editButton.setEnabled(not b)
        self._dataWidget._wi.cancelButton.setEnabled(b)
        self._dataWidget._wi.saveButton.setEnabled(b)
        self._dataWidget._wi.disabledCheckBox.setEnabled(not b)
        self._dataWidget._wi.ackCheckBox.setEnabled(not b)
        if b:
            #self._dataWidget._wi.formulaStacked.setCurrentIndex(1)
            self._dataWidget._wi.formulaTextEdit.onEdit(True)
            self._dataWidget._wi.deviceStackedLayout.setCurrentIndex(0)
            self._dataWidget._wi.severityStackedLayout.setCurrentIndex(0)
            
            #def prepareDataWidget(self)
            alarm = self.getCurrentAlarm()
            #Puts the widget in edit mode
            print 'In prepareDataWidget(%s)'%alarm.tag
            
            for i in range(self._dataWidget._wi.severityCombo.count()):
                if str(self._dataWidget._wi.severityCombo.itemText(i)).lower()==(self.getCurrentAlarm().severity or 'WARNING').lower():
                    self._dataWidget._wi.severityCombo.setCurrentIndex(i)
                    break
            self.setComboBox(self._dataWidget._wi.deviceCombo,values=['']+self.api.devices.keys(),sort=True)
            if self.getCurrentAlarm().device:
                for i in range(self._dataWidget._wi.deviceCombo.count()):
                    if str(self._dataWidget._wi.deviceCombo.itemText(i)).lower()==self.getCurrentAlarm().device.lower():
                        self._dataWidget._wi.deviceCombo.setCurrentIndex(i)
                        break
                    
            self.setComboBox(self._receiversLine._wi.receiversCombo,self.api.phonebook.keys(),sort=True)
            self._tvl.updateStyle()
            #End of prepareDataWidget(self)
            
            #self.formulaeditor._ui.formulaLineEdit.setText(alarm.formula) #self._dataWidget._wi.formulaTextEdit.toPlainText())
            #self.formulaeditor.expand_expression()
            #self.formulaeditor._ui.formulaLineEdit.setEnabled(True)
        else:
            #self._dataWidget._wi.formulaStacked.setCurrentIndex(0)
            self._dataWidget._wi.formulaTextEdit.onEdit(False)
            self._dataWidget._wi.deviceStackedLayout.setCurrentIndex(1)
            self._dataWidget._wi.severityStackedLayout.setCurrentIndex(1)
        return b

    ###########################################################################
    
    def getDataFields(self):
        widget,alarm = self._dataWidget,self.formulaeditor
        data = dict((k,str(s).strip()) for k,s in [
            ('tag',widget._wi.nameLineEdit.text()),
            ('description',widget._wi.descriptionTextEdit.toPlainText()),
            ('device',widget._wi.deviceCombo.currentText()),
            ('receivers',widget._wi.receiversLineEdit.text()),
            #('formula',str(alarm._ui.formulaLineEdit.text()).strip() or str(widget._wi.formulaTextEdit.toPlainText()).strip()),
            ('formula',str(widget._wi.formulaTextEdit.toPlainText()).strip()),
            ('severity',str(widget._wi.severityCombo.currentText())),
            ])
        print 'getDataFields(%s): %s'%(data['tag'],data)
        return data

    def checkEmptyFields(self):
        data = self.getDataFields()
        if all(data.values()): 
            return True
        else:
            self._message.warning(self, "Warning", "Fill these fields: %s" % ','.join(k for k,v in data.items() if not v))
            return False

    def saveData(self, old_name=None):
        print 'In saveData(%s)'%old_name
        data = self.getDataFields()
        widget = self._dataWidget
        widget._wi.deviceLineEdit.setText(data['device'])
        widget._wi.formulaTextEdit.setText(data['formula'])
        widget._wi.severityLineEdit.setText(data['severity'])
        tag,device = data['tag'],data['device']
        alarm = self.api.alarms.get(tag,None)
        
        if not old_name or old_name not in self.api:
            print "\tAlarm doesn't exist... creating new"
            try:
                self.api.add(**data)
            except Exception,e:
                Qt.QMessageBox.critical(self,"Error!",str(e), QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)
                print traceback.format_exc()
        
        elif old_name == tag:
            print "\tAlarm exists ... modifying fields (%s)"%str(data.values())
            if device!=self.api[tag].device:
                self.api.rename(tag,tag,new_device=device)
                alarm = self.api[tag]
                self._tvl.setModel(alarm.device+'/'+alarm.get_attribute())
                self.valueChanged()
                #setAlarmModel() moved to AlarmGUI
                #self.AlarmRows[tag].setAlarmModel(self.api[tag])
            alarm.setup(write=True,**data)

        elif tag in self.api:
            Qt.QMessageBox.critical(self,"Error!",'%s already exists!'%tag, QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)
            
        else:
            print "\tAlarm renamed (%s -> %s)"%(old_name,tag)
            if device: self.api.rename(old_name,new_tag=tag,new_device=device)
            else: self.api.rename(old_name,new_tag=tag)
            alarm = self.api[tag]
            self._tvl.setModel(alarm.device+'/'+alarm.get_attribute())
            alarm.setup(write=True,**data)
            self.setAlarmData(alarm)
            # Renamed alarms will not appear until the next onReload() call
            if SNAP_ALLOWED:
                try:
                    print('\tRenaming Alarm context %s to %s'%(old_name,tag))
                    snapi = snap.snapAPI()
                    self.ctx_list = snapi.get_contexts()
                    for cid in self.ctx_list:
                        if (self.ctx_list[cid].name.lower()==old_name.lower() and self.ctx_list[cid].reason=='ALARM'):
                            snapi.db.rename_context(cid, tag.lower())
                            break
                except: print 'Renaming context: Failed!\n%s'%traceback.format_exc()
        
        self.setAlarmData(tag)
        print 'Out of saveNewData()'
    
    ###########################################################################
    # AlarmActions,object

    @Catched
    def onAckStateChanged(self,checked=False):
        if not self.validate('onAcknowledge(%s)'%checked,self._currentAlarm.tag):
            setCheckBox(self._dataWidget._wi.AcknowledgedCheckBox,int(not self._dataWidget._wi.AcknowledgedCheckBox.isChecked()))
            return
        print 'onAckStateChanged(%s,%s)'%(self.getCurrentAlarm().tag,checked)
        if checked:
            prompt=QtGui.QInputDialog
            cmt, reply=prompt.getText(self,'Input dialog','This will prevent reminders from being sent..\nType a comment to continue:')
            comment=get_user()+': '+str(cmt)
            #reply=Qt.QMessageBox.question(self,"Warning!","Alarm will be Acknowledged.\nDo you want to continue?\n"+
                    #self.getCurrentAlarm().tag,QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
            if reply == QtGui.QMessageBox.Yes:
                try:
                    print('\tacknowledge '+self.getCurrentAlarm().tag)
                    taurus.Device(self.getCurrentAlarm().device).command_inout('Acknowledge',[str(self.getCurrentAlarm().tag), str(comment)])
                except: print traceback.format_exc()
                setCheckBox(self._dataWidget._wi.ackCheckBox,True)
            else: #Clean up the checkbox
                setCheckBox(self._dataWidget._wi.ackCheckBox,not self.getCurrentAlarm().get_enabled())
        else:
            try:
                print('\trenounce '+self.getCurrentAlarm().tag)
                taurus.Device(self.getCurrentAlarm().device).command_inout('Renounce',str(self.getCurrentAlarm().tag))
            except: print traceback.format_exc()
            setCheckBox(self._dataWidget._wi.ackCheckBox,False)
        self.valueChanged()
        
    #def onAckStateChanged(self,checked=False):
        #items = self.getSelectedRows(extend=True)
        #if not len([i.alarmAcknowledged for i in items]) in (len(items),0):
            ##if not target: 
            #print 'onAckStateChanged(%s): nothing to do ...'%len([i.alarmAcknowledged for i in items])
            #return
        #print 'onAckStateChanged(%s)'%[r.get_alarm_tag() for r in items]
        #waiting=threading.Event()
        #checked = not all([i.alarmAcknowledged for i in items])
        #if checked:
            #prompt=QtGui.QInputDialog
            #cmt, ok=prompt.getText(self,'Input dialog','This will prevent reminders from sending.\nType a comment to continue:')
            #comment=get_user()+': '+cmt
            #if ok and len(str(cmt)) != 0:
                #for a in items:
                    #try:
                        #print('\tacknowledging '+a.get_alarm_tag())
                        #taurus.Device(a.get_alarm_object().device).command_inout('Acknowledge',[str(a.get_alarm_tag()), str(comment)])
                        #waiting.wait(0.2)
                    #except: print traceback.format_exc()
                #setCheckBox(self._dataWidget._wi.ackCheckBox,True)
            #elif ok and len(str(cmt)) < 3: self.onAckStateChanged()
            #else: #Clean up the checkbox
                #setCheckBox(self._dataWidget._wi.ackCheckBox,items[0].alarmAcknowledged)
        #else:
            #for a in items:
                #try:
                    #print('\trenouncing '+a.get_alarm_tag())
                    #taurus.Device(a.get_alarm_object().device).command_inout('Renounce',str(a.get_alarm_tag()))
                    #waiting.wait(0.2)
                #except: print traceback.format_exc()
            #setCheckBox(self._dataWidget._wi.ackCheckBox,False)
        #[o.get_acknowledged(force=True) for o in items]
        #self.valueChanged()

    @Catched
    def onDisStateChanged(self,checked=False):
        if not self.validate('onDisable(%s)'%checked,self._currentAlarm.tag):
            setCheckBox(self._dataWidget._wi.disabledCheckBox,int(not self._dataWidget._wi.disabledCheckBox.isChecked()))
            return
        print 'onDisStateChanged(%s,%s)'%(self.getCurrentAlarm().tag,checked)
        if checked:
            reply=Qt.QMessageBox.question(self,"Warning!","Alarm will be disabled.\nDo you want to continue?\n"+self.getCurrentAlarm().tag,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
            if reply == QtGui.QMessageBox.Yes:
                comment='DISABLED by '+get_user()
                try:
                    print('\tdisabling '+self.getCurrentAlarm().tag)
                    taurus.Device(self.getCurrentAlarm().device).command_inout('Disable',[str(self.getCurrentAlarm().tag), str(comment)])
                except: print traceback.format_exc()
                setCheckBox(self._dataWidget._wi.disabledCheckBox,True)
            else: #Clean up the checkbox
                setCheckBox(self._dataWidget._wi.disabledCheckBox,not self.getCurrentAlarm().get_enabled())
        else:
            try:
                print('\tenabling '+self.getCurrentAlarm().tag)
                taurus.Device(self.getCurrentAlarm().device).command_inout('Enable',str(self.getCurrentAlarm().tag))
            except: print traceback.format_exc()
            setCheckBox(self._dataWidget._wi.disabledCheckBox,False)
        self.valueChanged()

class ReceiversForm(QtGui.QWidget):
    def __init__(self, parent=None):

        QtGui.QWidget.__init__(self, parent)
        self._wi = Ui_ReceiversLine()
        self._wi.setupUi(self)
        
###########################################################################################
# Formula editor widgets

class MyRow(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self._wi = uiRowForm()
        self._wi.setupUi(self)

    def GetText(self):
        return self._wi.variableCombo.currentText() + " " + self._wi.valueCombo.currentText() + " " + self._wi.operatorCombo.currentText()

    def CreateText(self):
        self.newText = self.GetText()
        self.emit(QtCore.SIGNAL('textChanged(QString)'),self.newText)
        return self.newText

class MyRelation(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self.gridLayout = QtGui.QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")
        self.comboBox = QtGui.QComboBox(self)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem(QtCore.QString(""))
        self.comboBox.addItem(QtCore.QString("("))
        self.comboBox.addItem(QtCore.QString(")"))
        self.comboBox.addItem(QtCore.QString("OR"))
        self.comboBox.addItem(QtCore.QString("AND"))
        self.comboBox.addItem(QtCore.QString("XOR"))
        self.comboBox.addItem(QtCore.QString("NOT"))
        self.gridLayout.addWidget(self.comboBox, 0, 0, 1, 1)
        self.pushButton = QtGui.QPushButton(self)
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setIcon(getThemeIcon("go-up"))
        self.gridLayout.addWidget(self.pushButton, 0, 2, 1, 1)
        self.pushButton_2 = QtGui.QPushButton(self)
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.setIcon(getThemeIcon("go-down"))
        self.gridLayout.addWidget(self.pushButton_2, 0, 3, 1, 1)
        self.pushButton_3 = QtGui.QPushButton(self)
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.setIcon(getThemeIcon("list-remove"))
        self.gridLayout.addWidget(self.pushButton_3, 0, 5, 1, 1)
        self.spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(self.spacerItem, 0, 1, 1, 1)
        self.spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(self.spacerItem1, 0, 4, 1, 1)
        QtCore.QObject.connect(self.comboBox, QtCore.SIGNAL("currentIndexChanged(QString)"), self.CreateText)

    def GetText(self):
        return self.comboBox.currentText()

    def CreateText(self):
        self.newText = self.GetText()
        self.emit(QtCore.SIGNAL('textChanged(QString)'),self.newText)
        return self.newText

#class SaveMessage(QtGui.QWidget):
    #def __init__(self,parent=None):
        #QtGui.QWidget.__init__(self,parent)
        #self.msgBox = QtGui.QMessageBox(self)
        #self.msgBox.setWindowTitle("Warning")

    #def modifiedMessage(self):
        #"""
        #This method is never called?
        #"""
        #print 'SaveMessage.modifiedMessage()'
##        open_icon = getThemeIcon("dialog-warning")
        #self.msgBox.setText("The document has been modified.")
        #self.msgBox.setIcon(QtGui.QMessageBox.Warning)
        #self.msgBox.setInformativeText("Do you want to save your changes?")
        #self.msgBox.setStandardButtons(QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
        #self.msgBox.setDefaultButton(QtGui.QMessageBox.Save)
        #self.msgBox.setDetailedText("DetailedText")
        #self.ret = self.msgBox.exec_()
        #self.selectedButton()
##        self.msgBox.warning()
##        self.msgBox.information()
##        self.msgBox.critical()
##        self.msgBox.question()

    #def selectedButton(self):
        #if self.ret == QtGui.QMessageBox.Save:
            #print "Save"
        #elif self.ret == QtGui.QMessageBox.Discard:
            #print "Discard"
        #elif self.ret == QtGui.QMessageBox.Cancel:
            #print "Cancel"
        #else:
            #print "Something else"

class FormulaEditor(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self._ui = uiBodyForm()
        self._ui.setupUi(self)
        self.exampleRow = MyRow() #czy potrzebuje tego tutaj
        self._rowList=[] # create list
        self.booleans = ['OR','AND','XOR','NOT','(',')']
        self.operators = ['==','>=','>','<=','<','!=']
        self._widgetList=[]
        QtCore.QObject.connect(self._ui.clearButton, QtCore.SIGNAL("clicked()"), self.Clr)
        QtCore.QObject.connect(self._ui.addExpressionButton, QtCore.SIGNAL("clicked()"), self.Add)
        QtCore.QObject.connect(self._ui.addRelationButton, QtCore.SIGNAL("clicked()"), self.addRelation)

    def clickedClose(self):
        self.Clr()
        self.close()

    def firstList(self, widget):
        self._rowList.append(widget)

    def lengthList(self):
        return len(self._rowList)

    def Add(self, edit=None):
        """Add expressions"""
        self.exampleRow = MyRow()
        self.firstList(self.exampleRow)
        QtCore.QObject.connect(self.exampleRow._wi.removeButton, QtCore.SIGNAL("clicked()"), self.Rm)
        self._ui.scrollAreaWidgetContents.layout().addWidget(self.exampleRow)
        if edit:
            self.exampleRow._wi.variableCombo.addItem(QtCore.QString(edit[0]))
            self.exampleRow._wi.valueCombo.setItemText(0, edit[1])
            self.exampleRow._wi.operatorCombo.addItem(QtCore.QString(edit[2]))
        self.connect(self.exampleRow,QtCore.SIGNAL('textChanged(QString)'),self.UpdateText)

    def addRelation(self, edit=False):
        self.relation = MyRelation(self)
        self.firstList(self.relation)
        self._ui.scrollAreaWidgetContents.layout().addWidget(self.relation)
        if edit:
            self.relation.comboBox.setItemText(0, edit)
        self.connect(self.relation,QtCore.SIGNAL('textChanged(QString)'),self.UpdateText)
        QtCore.QObject.connect(self.relation.pushButton, QtCore.SIGNAL("clicked()"), self.UpRelation)
        QtCore.QObject.connect(self.relation.pushButton_2, QtCore.SIGNAL("clicked()"), self.DownRelation)
        QtCore.QObject.connect(self.relation.pushButton_3, QtCore.SIGNAL("clicked()"), self.Rm)

    def UpRelation(self):
        self.widget = self.sender().parent()
        i = self._rowList.index(self.widget)
        j = self.lengthList()
        if j != 1 and i != 0:
            self.object = self._rowList.pop(i)
            self._rowList.insert(i-1, self.object)
            self.widget.setParent(None)   
            self.widget.close()
            self._ui.scrollAreaWidgetContents.layout().insertWidget(i-1,self.object)
        else:
            print "widget is already first"
            Qt.QMessageBox.warning(self,"Warning","What you are about to do is impossible.")
        self.UpdateText()

    def DownRelation(self):
        self.widget = self.sender().parent()
        i = self._rowList.index(self.widget)
        j = self.lengthList()
        if i < (j-1):
            self.object = self._rowList.pop(i)
            self._rowList.insert(i+1, self.object)
            self.widget.setParent(None)
            self.widget.close()
            self._ui.scrollAreaWidgetContents.layout().insertWidget(i+1,self.object)
        else:
            print "widget is already first"
            Qt.QMessageBox.warning(self,"Warning","What you are about to do is impossible.")
        self.UpdateText()

    def Clr(self):
        """Cleaning"""
        print 'clearing form ...'
        self.widgets, self._rowList = self._rowList, []
        for w in self.widgets:
            #lay.removeWidget(w)
            w.setParent(None)
            w.close()
        self.UpdateText()
        self._ui.formulaLineEdit.clear()

    def Rm(self):
        """Remove widget"""
        self.i = self.sender().parent()
        Qt.QObject().connect(self, Qt.SIGNAL("usunMnie"), self.onUsunMnie)
        self.emit(Qt.SIGNAL("usunMnie"), self.i)
        self.UpdateText()

    def onUsunMnie(self, i):
        """this is the help comment"""
        Qt.QObject.disconnect(self, Qt.SIGNAL("usunMnie"), self.onUsunMnie)
        self._rowList.remove(i)
        i.setParent(None)
        i.close()

    def PrintText(self): # just egzample
        self.rows = self._rowList
        print "PRINT"
        for i in self.rows:
            print "childrens: ", self.rows[i]
            self.targets = ('variableCombo','valueCombo','operatorCombo')
            for t in self.targets:
                print "childrens: ", self.rows[i].children()
                print getattr(self.rows[i].children(),t,None) or 'Attr_%s_not_found'%t

    def UpdateText(self,unused_text=''):
        self.text = ' '.join([str(row.GetText()) for row in self._rowList])
        self._ui.formulaLineEdit.setText(self.text)

###################################### EDIT ALARMS ##################################
    def get_expressions(self, expression):
        self.booleans = ['OR','AND','XOR','NOT','\(','\)','or','and','xor','not']
        return re.split('|'.join(self.booleans),expression),re.findall('|'.join(self.booleans),expression)

    def get_variables(self, expression):
        return re.split('|'.join(self.operators),expression),re.findall('|'.join(self.operators),expression)

    def expand_expression(self):
        """ This method is called from onEdit() """
        self.exp = str(self._ui.formulaLineEdit.text())
        mainexp=self.exp
        if self.exp:
            self.reas=[]
            self.exps,self.ops = self.get_expressions(self.exp)
            for i,self.exp in enumerate(self.exps):
                self.content, self.operator = self.get_variables(self.exp)
                if self.exp:
                    if (len(self.content)==2):
                        if (self.content[0] and self.operator[0] and self.content[1]):
                            self.reas.extend([self.content[0], self.operator[0], self.content[1]])
                        if i<len(self.ops):
                            self.reas.append(self.ops[i])
                elif i<len(self.ops):
                    self.reas.append(self.ops[i])
            reasexp=("".join(self.reas))
            if reasexp == mainexp:
                self.exps,self.ops = self.get_expressions(mainexp)
                for i,self.exp in enumerate(self.exps):
                    self.content, self.operator = self.get_variables(self.exp)
                    if self.exp:
                        if (len(self.content)==2):
                            if (self.content[0] and self.operator[0] and self.content[1]):
                                self.data=[self.content[0].strip(), self.operator[0], self.content[1].strip()]
                                self.Add(self.data)
                            if i<len(self.ops):
                                self.addRelation(self.ops[i])
                    elif i<len(self.ops):
                        self.addRelation(self.ops[i])
            else:
                self._ui.formulaLineEdit.setEnabled(True)            
        else:
            Qt.QMessageBox.warning(self,"Warning","No data to edit!")

############################################################################################

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = AlarmForm()
    if sys.argv[1:]: myapp.setAlarmData(*sys.argv[1:])
    else: myapp.onNew()
    myapp.show()
    sys.exit(app.exec_())
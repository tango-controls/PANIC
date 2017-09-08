import sys, re, os, traceback, time
import PyTango, fandango
from fandango.functional import *
from fandango import Catched
import taurus, taurus.qt.qtgui.base
from taurus.core import TaurusEventType
from taurus.qt.qtgui.base import TaurusBaseComponent
import panic
from panic.gui.utils import *
from panic.gui.utils import WindowManager #Order of imports matters!
from panic.gui.editor import AlarmForm

#from htmlview import *

class QAlarmManager(object): #QAlarm):
  
    @Catched
    def onContextMenu(self, point):
        self.popMenu = QtGui.QMenu(self)
        view = getattr(self,'view')
        items = self.getSelectedRows(extend=False)
        print('In onContextMenu(%s)'%items)
        row = self._ui.listWidget.currentItem()
        alarm = self.getCurrentAlarm(row)
        #self.popMenu.addAction(getThemeIcon("face-glasses"), "Preview Attr. Values",self.onSelectAll)

        act = self.popMenu.addAction(getThemeIcon("face-glasses"),
                                     "See Alarm Details",self.onView) 
        act.setEnabled(len(items)==1)
        act = self.popMenu.addAction(getThemeIcon("accessories-calculator"),
                                     "Preview Formula/Values",
            lambda s=self:WindowManager.addWindow(s.showAlarmPreview()))
        act.setEnabled(len(items)==1)
        self.popMenu.addAction(getThemeIcon("view-refresh"), 
                               "Sort/Update List",self.onSevFilter)

        act = self.popMenu.addAction(getThemeIcon("office-calendar"), 
                                     "View History",self.viewHistory)
        act.setEnabled(SNAP_ALLOWED and len(items)==1) 
            # and row.get_alarm_tag() in self.ctx_names)
            
        sevMenu = self.popMenu.addMenu('Change Severity')
        for S in ('ERROR','ALARM','WARNING','DEBUG'):
            action = sevMenu.addAction(S)
            self.connect(action, QtCore.SIGNAL("triggered()"), 
                lambda ks=items,s=S: 
                  self.setSeverity([k.get_alarm_tag() for k in ks],s))
        
        # Reset / Acknowledge options
        act = self.popMenu.addAction(getThemeIcon("edit-undo"), 
                        "Reset Alarm(s)",lambda s=self:ResetAlarm(s))

        items = [view.get_alarm_from_text(i.text(),obj=True) for i in items]
        print('oncontextMenu(%s)'%items)
            
        act.setEnabled(any(i.active for i in items))

        if len([i.acknowledged for i in items]) in (len(items),0):
            self.popMenu.addAction(getThemeIcon("media-playback-pause"), 
                "Acknowledge/Renounce Alarm(s)",
                lambda s=self:AcknowledgeAlarm(s))

        if len([i.disabled for i in items]) in (len(items),0):
            self.popMenu.addAction(getThemeIcon("dialog-error"), 
                "Disable/Enable Alarm(s)",
                lambda s=self:ChangeDisabled(s))
            
        # Edit options
        if self.expert:
            self.popMenu.addSeparator()
            act = self.popMenu.addAction(
                getThemeIcon("accessories-text-editor"), 
                "Edit Alarm",self.onEdit)
            act.setEnabled(len(items)==1)
            act = self.popMenu.addAction(getThemeIcon("edit-copy"), 
                                         "Clone Alarm",self.onClone)
            act.setEnabled(len(items)==1)
            act = self.popMenu.addAction(getThemeIcon("edit-clear"), 
                                         "Delete Alarm",self.onDelete)
            act.setEnabled(len(items)==1)
            self.popMenu.addAction(getThemeIcon("applications-system"), 
                                   "Advanced Config",self.onConfig)
            self.popMenu.addSeparator()
            act = self.popMenu.addAction(
                getThemeIcon("accessories-text-editor"), "TestDevice",
                lambda d=alarm.device:os.system('tg_devtest %s &'%d))
            
            act.setEnabled(len(items)==1)
            
        #self.popMenu.addSeparator()
        #self.popMenu.addAction(getThemeIcon("process-stop"), "close App",self.close)
        self.popMenu.exec_(self._ui.listWidget.mapToGlobal(point))

    def onEdit(self,edit=True):
        alarm = self.getCurrentAlarm()
        print "AlarmGUI.onEdit(%s)"%alarm
        forms = [f for f in WindowManager.WINDOWS 
            if isinstance(f,AlarmForm) and f.getCurrentAlarm().tag==alarm.tag] 
        
        if forms: #Bring existing forms to focus
            form = forms[0]
            form.enableEditForm(edit)
            form.hide()
            form.show()
        else: #Create a new form
            form = WindowManager.addWindow(AlarmForm(self.parent()))
            #form.connect(form,Qt.SIGNAL('valueChanged'),self.hurry)
            if edit: form.onEdit(alarm)
            else: form.setAlarmData(alarm)
        form.show()
        return form
        
    def onView(self):
        return self.onEdit(edit=False)
        
    def onNew(self):
        try:
            trace('onNew()')
            if not self.api.devices:
                v = Qt.QMessageBox.warning(self,'Warning','You should create a PyAlarm device first (using jive or config panel)!',Qt.QMessageBox.Ok)
                return
            if self._ui.listWidget.currentItem():
                self._ui.listWidget.currentItem().setSelected(False)
            form = AlarmForm(self.parent())
            trace('form')
            #form.connect(form,Qt.SIGNAL('valueChanged'),self.hurry)
            form.onNew()
            form.show()
            return form
        except:
            traceback.print_exc()
        
    def onConfig(self):
        self.dac = dacWidget(device=self.getCurrentAlarm().device)
        self.dac.show()
        
    def onClone(self):
        alarm = self.getCurrentAlarm().tag
        trace("onClone(%s)"%alarm)
        new_tag,ok = Qt.QInputDialog.getText(self,'Input dialog','Please provide tag name for cloned alarm.',Qt.QLineEdit.Normal,alarm)
        if (ok and len(str(new_tag)) > 3):
            try:
                obj = self.api[alarm]
                self.api.add(str(new_tag), obj.device, formula=obj.formula, description=obj.description, receivers=obj.receivers, severity=obj.severity)
                self.onReload()
            except Exception,e:
                Qt.QMessageBox.critical(self,"Error!",str(e), QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)
                trace(traceback.format_exc())

    def onDelete(self,tag=None,ask=True):
        tags = tag and [tag] or [getattr(r,'tag',r) 
                                 for r in self.getSelectedAlarms(extend=False)]
        if ask:
            v = QtGui.QMessageBox.warning(None,'Pending Changes',\
                'The following alarms will be deleted:\n\t'+'\n\t'.join(tags),\
                QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel)
            if v == QtGui.QMessageBox.Cancel: 
                return

            self.setAllowedUsers(self.api.get_admins_for_alarm(
                                    len(tags)==1 and tags[0]))
            if not self.validate('onDelete(%s)'%([a for a in tags])):
                return
            
        if len(tags)>1:
            [self.onDelete(tag,ask=False) for tag in tags]
        else:
            tag = tags[0]
            trace('onDelete(%s)'%tag)
            self.removeAlarmRow(tag)
            self.api.remove(tag)
            self.onReload()
            try:
                [f.close() for f in WindowManager.WINDOWS 
                    if isinstance(f,AlarmForm) and f.getCurrentAlarm().tag==tag] 
            except: pass

    ###############################################################################

    def viewHistory(self):
        alarm = self.getCurrentTag()

        if SNAP_ALLOWED and not self.snapi: 
          self.snapi = get_snap_api()

        if self.snapi:
          self.ctx_names=[c.name for c in self.snapi.get_contexts().values()]

        if alarm in self.ctx_names: 
          self.ahApp = ahWidget()
          self.ahApp.show()
          #self.ahApp.setAlarmCombo(alarm=str(self._ui.listWidget.currentItem().text().split('|')[0]).strip(' '))
          self.ahApp.setAlarmCombo(alarm=alarm)
        else:
          v = QtGui.QMessageBox.warning(None,'Not Archived', \
              'This alarm has not recorded history',QtGui.QMessageBox.Ok)
          return
        
        
    def showAlarmPreview(self):
        form = AlarmPreview(tag=self.getCurrentAlarm(),parent=self.parent())
        form.show()
        return form
    
##############################################################################

def getTargetAlarms(obj,alarms=None,active=False):
    if alarms is None:
        if isinstance(obj,AlarmForm):
            alarms = [obj.getCurrentAlarm()]
        elif hasattr(obj,'getSelectedAlarms'):
            alarms = [t for t in obj.getSelectedAlarms() 
                        if (not active or t.active)]
    elif not isSequence(alarms):
        alarms = [alarms]
    return alarms

def emitValueChanged(self):
    if hasattr(self,'emitValueChanged'):
        self.emitValueChanged()
    elif hasattr(self,'valueChanged'):
        self.valueChanged()        
    #[o.get_acknowledged(force=True) for o in items]
    #[f.setAlarmData() for f in WindowManager.WINDOWS 
            #if isinstance(f,AlarmForm)]
    #self.onFilter()        
                
def ResetAlarm(parent=None,alarm=None):
    try:
        self = parent
        prompt,cmt=QtGui.QInputDialog,''
        alarms = getTargetAlarms(parent,alarm,active=True)
        action = 'RESET'
        text = 'The following alarms will be %s:\n\t'%action\
                +'\n\t'.join([t.tag for t in alarms])
        trace('In ResetAlarm(): %s'%text)
        text += '\n\n'+'Must type a comment to continue:'
        
        
        self.setAllowedUsers(self.api.get_admins_for_alarm(len(alarms)==1 
                    and alarms[0].tag))
        if not self.validate('%s(%s)'%(action,[a.tag for a in alarms])):
            raise Exception('Invalid login or password!')
        
        comment, ok = QtGui.QInputDialog.getText(self,'Input dialog',text)
        if not ok:
            return
        elif ok and len(str(comment)) < 4:
            raise Exception('comment was too short')
        comment = get_user()+': '+str(comment)
        for alarm in alarms:
            alarm.reset(comment)
            
        emitValueChanged(self)
    except:
        msg = traceback.format_exc()
        v = QtGui.QMessageBox.warning(self,'Warning',msg,QtGui.QMessageBox.Ok)

def AcknowledgeAlarm(parent,alarm=None):
    try:        
        self = parent
        prompt,cmt=QtGui.QInputDialog,''
        alarms = getTargetAlarms(parent,alarm,active=True)
        acks = len([a for a in alarms if a.acknowledged])
        action = 'ACKNOWLEDGED' if acks!=len(alarms) else 'RENOUNCED'
        text = 'The following alarms will be %s,\n\t'%action\
                +'\n\t'.join([t.tag for t in alarms])
        trace('In %s(): %s'%(action,text))
        text += '\n\n'+'Must type a comment to continue:'        
        
        self.setAllowedUsers(self.api.get_admins_for_alarm(len(alarms)==1 
                    and alarms[0].tag))
        if not self.validate('%s(%s)'%(action,[a.tag for a in alarms])):
            raise Exception('Invalid login or password!')       
            

        comment, ok = QtGui.QInputDialog.getText(self,'Input dialog',text)
        if not ok:
            return
        elif ok and len(str(comment)) < 4:
            raise Exception('comment was too short')
        
        comment = str(get_user()+': '+str(comment))

        for alarm in alarms:
            if not alarm.acknowledged and action == 'ACKNOWLEDGED':
                alarm.acknowledge(comment)
            elif alarm.acknowledged:
                alarm.renounce(comment)
                
        emitValueChanged(self)
    except:
        msg = traceback.format_exc()
        v = QtGui.QMessageBox.warning(self,'Warning',msg,QtGui.QMessageBox.Ok)
    
def ChangeDisabled(parent,alarm=None):
    try:        
        self = parent
        prompt,cmt=QtGui.QInputDialog,''
        alarms = getTargetAlarms(parent,alarm,active=False)
        check = len([a for a in alarms if not a.disabled])
        action = 'ENABLED' if check!=len(alarms) else 'DISABLED'
        text = 'The following alarms will be %s,\n\t'%action\
                +'\n\t'.join([t.tag for t in alarms])
        trace('In %s(): %s'%(action,text))
        text += '\n\n'+'Must type a comment to continue:'        
        
        self.setAllowedUsers(self.api.get_admins_for_alarm(len(alarms)==1 
                    and alarms[0].tag))
        if not self.validate('%s(%s)'%(action,[a.tag for a in alarms])):
            raise Exception('Invalid login or password!')
            
        comment, ok = QtGui.QInputDialog.getText(self,'Input dialog',text)
        if not ok:
            return
        elif ok and len(str(comment)) < 4:
            raise Exception('comment was too short')
        comment = get_user()+': '+str(comment)
        
        for alarm in alarms:
            if not alarm.disabled and action == 'DISABLED':
                print('Disabling %s'%alarm.tag)
                alarm.disable(comment)
            elif alarm.disabled:
                print('Enabling %s'%alarm.tag)
                alarm.enable(comment)

        emitValueChanged(self)
    except:
        msg = traceback.format_exc()
        v = QtGui.QMessageBox.warning(self,'Warning',msg,QtGui.QMessageBox.Ok)

  



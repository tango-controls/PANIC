"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import sys, os, taurus, fandango, PyTango, getpass, traceback, time
import fandango as fd
from fandango.qt import Qt, QtCore, QtGui, DoubleClickable

from taurus.qt.qtgui.base.taurusbase import TaurusBaseComponent
from taurus.qt.qtgui.base.taurusbase import TaurusBaseWidget

try:
  from taurus.qt.qtgui.display.taurusvaluelabel import TaurusValueLabel
except:
  from taurus.qt.qtgui.display.tauruslabel import TaurusLabel as TaurusValueLabel

from taurus.qt.qtgui.container import TaurusMainWindow
from taurus.qt.qtgui.panel import TaurusForm
import panic
from panic import AlarmAPI, AlarmView

try: 
  #if available, this module will try to load the full AlarmGUI
  from panic.gui import AlarmGUI
except: AlarmGUI = None

###############################################################################

def getThemeIcon(icon):
    if 3 == int(taurus.Release().version_info[0]):
        from taurus.qt.qtgui import resource
        if ':' in icon:
            icon = resource.getIcon(icon)
        else:
            icon = resource.getThemeIcon(icon)
    else:
        if ':' in icon:
            icon = icon.replace('/',':').strip(':')
            icon = Qt.QIcon(icon)
        else:
            icon = Qt.QIcon.fromTheme(icon)
    return icon
  
def getIconForAlarm(alarm):
    state,severity = alarm.get_state(),alarm.severity
    
    if state == 'ERROR':
        return "dialog-error" #icon = "emblem-noread"
      
    elif state == 'OOSRV':
        return "stop" #"media_stop"
    elif state == 'DSUPR':
        #return "stop" #"media_stop"
        return "actions:player_pause.svg"
    elif state == 'SHLVD':
        #return "media_pause" #"media_playback_stop"
        return "actions:appointment.svg"
      
    elif state == 'ACKED': 
        return "applications-development" #"media_playback_pause"
    elif state == 'RTNUN':
        return "stock_down"
      
    elif state in ('ACTIVE','UNACK'):
        if severity in ('ALARM','ERROR'):
            return "software-update-urgent"
        elif severity == 'WARNING':
            return "emblem-important"
    
    # state == NORM
    return "emblem-system"
        

###############################################################################

class GuiWidget(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)
        self._gui = AlarmGUI()
        self._gui.setRowModels()

    def editAlarm(self, alarm):
        item=self._gui._ui.listWidget.findItems(alarm, QtCore.Qt.MatchStartsWith)
        item[0].setSelected(True)
        pos=self._gui._ui.listWidget.row(item[0])
        self._gui.setAlarmData(pos)
        self._gui.onEdit()

    def show(self):
        self._gui.show()
        self._gui.raise_()
        self._gui.activateWindow()

##############################################################################
        
class AlarmValueLabel(Qt.QLabel):#TaurusValueLabel):
    
    def setModel(self,model):
        print('AlarmValueLabel.setModel(%s(%s))'
              %(type(model),str(model)))
        if fandango.isString(model) and '/' not in model:
            model = str(model)
            self.alarm = panic.AlarmAPI(model)[model]
        if isinstance(model,panic.Alarm):
            self.alarm = model
            #model = model.device + '/' + model.get_attribute()
        self.model = self.alarm.get_model()
        #TaurusValueLabel.setModel(self,model)
            
    def updateStyle(self,extra=''):
        self.setAlignment(QtCore.Qt.AlignCenter)
        obj = getattr(self,'alarm',None)
        #print('AlarmValueLabel.updateStyle(%s,%s)'%(type(obj),obj))
        if hasattr(obj,'active'):
            value = obj.active
        elif hasattr(obj,'rvalue'):
            value = obj.rvalue
        else:
            value = getattr(obj,'value',None)
        if value:
            self.ss = "background-color:red; color:black;"
            self.setText(getattr(obj,'state',"ALARM"))
        elif value is None or value<0:
            self.ss = "background-color:grey; color:black;"
            self.setText(getattr(obj,'state',"UNKNOWN"))
        else:
            state = getattr(obj,'state',"OK")
            if state in ('DSUPR','SHLVD'):
                self.ss = "background-color:white; color:black;"
            elif state in ('OOSRV','ERROR',):
                self.ss = "background-color:white; color:red;"                
            else:
                self.ss = "background-color:lightgreen; color:black;"
            self.setText(state)
        self.setStyleSheet(self.ss)
        self.alarmUpdated()
        #TaurusBaseWidget.updateStyle(self)

    def alarmUpdated(self):
        #print('AlarmValueLabel.alarmUpdated()')
        self.emit(Qt.SIGNAL('alarmUpdated'))        
        
        
###############################################################################

class ToolbarActionButton(TaurusBaseComponent, Qt.QPushButton):
    SHOW_FAILED_ALARMS = False
    LEDS = {
        'OFF':':/leds/images24/ledblueoff.png',
        'OK':':/leds/images24/ledgreen.png',
        'ALARM':':/leds/images24/ledred.png',
        'WARNING':':/leds/images24/ledorange.png',
        'DEBUG':':/leds/images24/ledyellow.png',
        'ERROR':':/leds/images24/ledredoff.png',
        'CHANGING':':/leds/images24/ledblue.png'
    }

    def __init__(self,gui,api,parent=None):
        TaurusBaseComponent.__init__(self,parent)
        Qt.QPushButton.__init__(self,parent)
        self.guiApp = gui
        self.api = api
        self.value = None
        self.setIconSize(Qt.QSize(25,25))
        
    def setAlarmModel(self,tag):
        attr = self.api[tag].get_attribute(full=True)
        print('In PanicToolbarAction.setAlarmModel(%s = %s)'%(tag,attr))
        self.tag = tag
        self.setModel(attr)

    def setModel(self,model):
        print('In PanicToolbarAction.setModel(%s)'%model)
        TaurusBaseComponent.setModel(self,model)
        self.setIcon(self.getIcon('OFF'))

    def getIcon(self,url):
        print "ToolbarAction.getIcon(%s)"%url
        if url in self.LEDS: url = self.LEDS[url]
        icon = taurus.qt.qtgui.resource.getIcon(url)
        return icon

    def handleEvent(self,evt_src,evt_type,evt_value):
        print('In PanicToolbarAction.handleEvent(%s)'%self.getModel())
        TaurusBaseComponent.handleEvent(self, evt_src, evt_type, evt_value)
        if all(hasattr(evt_value,a) for a in ('value','quality')):
            self.value = evt_value.value
            self.api[self.tag].active = (time.time() if evt_value.value else 0)
            if evt_value.quality == PyTango.AttrQuality.ATTR_INVALID:
                self.setIcon(getThemeIcon("software-update-urgent"))
            elif not evt_value.value:
                self.setIcon(self.getIcon('OK'))
            elif evt_value.quality == PyTango.AttrQuality.ATTR_VALID:
                self.setIcon(getThemeIcon("applications-development"))
            elif evt_value.quality == PyTango.AttrQuality.ATTR_WARNING:
                self.setIcon(getThemeIcon("emblem-important"))
            elif evt_value.quality == PyTango.AttrQuality.ATTR_ALARM:
                self.setIcon(getThemeIcon("software-update-urgent"))
            elif evt_value.quality == PyTango.AttrQuality.ATTR_CHANGING:
                self.setIcon(self.getIcon('CHANGING'))
        else:
            self.setIcon(getThemeIcon("dialog-error"))
            self.setVisible(self.SHOW_FAILED_ALARMS) #!!!
        pass

    def buildMenu(self):
        self.popMenu = Qt.QMenu()
        tooltip = str(self.toolTip())
        name,date = tuple(tooltip.split('\n')[:2]) if '\n' in tooltip else (tooltip,'')
        q0 = Qt.QAction(name,self.popMenu)
        f =q0.font()
        f.setBold(True)
        q0.setFont(f)
        self.popMenu.addAction(q0)
        if date:
            q1 = Qt.QAction(date,self.popMenu)
            q1.setFont(f)
            self.popMenu.addAction(q1)
        self.popMenu.addAction(getThemeIcon("media-playback-pause"), "Acknowledge",self.onAcknowledge)
        self.popMenu.addAction(getThemeIcon("dialog-error"), "Disable",self.onDisable)
        self.popMenu.addAction(getThemeIcon("edit-undo"), "Reset Alarm",self.onReset)
        self.popMenu.addAction(getThemeIcon("accessories-text-editor"), "Edit Alarm",self.onEdit)
        self.popMenu.addAction(getThemeIcon("office-calendar"), "View History",self.onHistory)
        self.setMenu(self.popMenu)

    def onAcknowledge(self):
        print('onAcknowledge')
        self.name=str(self.getModel().split('/')[-1]).strip(' ')
        print(self.name)
        if not taurus.Device(self.getModel().rsplit('/',1)[0]).command_inout('CheckAcknowledged',str(self.name)):
            prompt=QtGui.QInputDialog
            comment, ok=prompt.getText(self,'Input dialog','This will prevent reminders from sending.\nType a comment to continue:')
            if ok and len(str(comment)) > 3:
                try:
                    comment=str(getpass.getuser())+': '+comment
                    print('acknowledging %s with comment: %s !' %(self.name, comment))
                    taurus.Device(self.getModel().rsplit('/',1)[0]).command_inout('Acknowledge',[str(self.name), str(comment)])
                except:
                    print traceback.format_exc()
            else:
                Qt.QMessageBox.critical(self,"Error!",'Comment too short.\nAlarm not acknowledged.', QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)
        elif not ok:
            pass
        else:
            Qt.QMessageBox.information(self,"Info!",'Alarm already acknowldged.', QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)

    def onDisable(self):
        print('onDisable')
        self.name=str(self.getModel().split('/')[-1]).strip(' ')
        print(self.name)
        if not taurus.Device(self.getModel().rsplit('/',1)[0]).command_inout('CheckDisabled',str(self.name)):
            reply=Qt.QMessageBox.question(self,"Warning!","Alarm will be disabled.\nDo you want to continue?", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
            if reply == QtGui.QMessageBox.Yes:
                print('disable %s !' %self.name)
                comment='DISABLED by '+str(getpass.getuser())
                taurus.Device(self.getModel().rsplit('/',1)[0]).command_inout('Disable', [str(self.name), str(comment)])
        else:
            Qt.QMessageBox.information(self,"Info!",'Alarm already disabled.', QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)

    def onReset(self):
        print('onReset')
        self.name=str(self.getModel().split('/')[-1]).strip(' ')
        print(self.name)
        prompt=QtGui.QInputDialog
        comment, ok=prompt.getText(self,'Input dialog','This will reset the alarm.\nType a comment to continue:')
        if ok and len(str(comment)) > 3:
            try:
                comment=str(getpass.getuser())+': '+comment
                print('reseting %s with comment: %s !' %(self.name, comment))
                taurus.Device(self.getModel().rsplit('/',1)[0]).command_inout('ResetAlarm',[str(self.name), str(comment)])
            except:
                print traceback.format_exc()
        elif not ok:
            pass
        else:
            Qt.QMessageBox.critical(self,"Error!",'Comment too short.\nAlarm not reseted.', QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)

    def onEdit(self):
        print('onEdit')
        self.name=str(self.getModel().split('/')[-1]).strip(' ')
        if self.guiApp is None: self.parent().showGui()
        self.guiApp.editAlarm(self.name)
        self.guiApp.show()

    def onHistory(self):
        print('onHistory')
        from panic.gui.alarmhistory import ahWidget
        self.name=str(self.getModel().split('/')[-1]).strip(' ')
        self.ahApp = ahWidget()
        self.ahApp.setAlarmCombo(alarm=self.name)
        self.ahApp.show()

class PanicToolbar(TaurusBaseWidget, Qt.QToolBar):

    def __init__(self,parent=None,container=None,filters=None,max_visible=16,refresh=10000):
        Qt.QToolBar.__init__(self,parent)
        self.api = None
        self.filters = filters
        self.max_visible = max_visible
        self.filters = filters or []
        self.buttons = {}
        self.setIconSize(Qt.QSize(25,25))
        self.gui = None 
        self.setup()
        self.refresh()
        self.refreshTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.refreshTimer, QtCore.SIGNAL("timeout()"), self.refresh)
        self.refreshTimer.start(refresh)

    def setRefresh(self,interval):
        self.refreshTimer.setInterval(interval)
        
    def _get_alarm_date(self, device, alarm):
        res=''
        try:
            attr = taurus.Attribute(device+'/ActiveAlarms').read().value
            for line in attr:
                if line.startswith(alarm+':'):
                    res = line.split(':')
                    break
        except Exception,e:
            print ('Cant get the alarm date!')
        return res
            
    def showGui(self):
          try:
            if self.gui is None: self.gui = GuiWidget()
            self.gui.show()
          except:
            print traceback.format_exc()
            print 'AlarmGUI not available in PYTHONPATH'
            import os
            os.system('panic &')
          return self.gui 

    def setup(self,filters=None,api=None):#, alarms=None):
        print "In PanicToolbar.setup(%s)"%filters
        self.setMovable(True)
        self.setFloatable(True)
        filters = filters or self.filters
        
        if not self.api: self.api = api or AlarmAPI(filters)
        else: self.api.load(filters)
        
        self.alarms = [] #dict((a,) for a in self.api) #Alarms must be set here and not in refresh; 
        #We should never clear this list again
        
        if filters and filters not in self.filters:
            if isinstance(filters,basestring): self.filters.append(filters)
            else: self.filters.extend(filters)

        self.filter_alarms()
        return
            
    def filter_alarms(self):
        te = fandango.TangoEval()
        for alarm in self.api:
            if alarm in self.alarms: continue
            try:
                if not self.filters: 
                    self.alarms.append(alarm) 
                else:
                    attrs = ['%s/%s'%(v[0],v[1]) for v in te.parse_variables(self.api[alarm].formula)]
                    tags = [alarm]+self.api.parse_alarms(self.api[alarm].formula)
                    if any(fandango.functional.matchCl(f,a) for f in self.filters for a in (attrs if '/' in f else tags)):
                        self.alarms.append(alarm)
            except:
                print 'In PanicToolbar.filter_alarms(): Unable to parse %s:\n%s'%(alarm,traceback.format_exc())
                
        if self.alarms: print 'In PanicToolbar.refresh(): %d alarms out of %d matches filters'%(len(self.alarms),len(self.api.keys()))
        else: print 'In PanicToolbar.refresh(): no Alarm matches %s'%self.filters
        
        return self.alarms

    def refresh(self):
        print 'In PanicToolbar.refresh(): filters = %s'%self.filters
        
        if not self.filters: #(alarms!='*'):
            self.filters=[]
            factory = taurus.Factory()
            for a in factory.getExistingAttributes():
                self.filters.append(str(a).split('/',1)[1])
            self.filter_alarms()
        
        visible=0
        def sorter(obj):
            print '%s -> %s' % (obj.tag, obj.active)
            quality = self.api[obj.tag].get_quality()
            
            #full_attr_name = obj.device+'/'+obj.get_attribute()
            #try:
                #quality = taurus.Attribute(full_attr_name).read().quality
            #except:
                #quality = PyTango.AttrQuality.ATTR_INVALID

            if quality==PyTango.AttrQuality.ATTR_ALARM:
                return '%d,%d,%s'%(1-bool(obj.active), 0, obj.tag)
            elif quality==PyTango.AttrQuality.ATTR_WARNING:
                return '%d,%d,%s'%(1-bool(obj.active), 1, obj.tag)
            elif quality==PyTango.AttrQuality.ATTR_VALID:
                return '%d,%d,%s'%(1-bool(obj.active), 2, obj.tag)
            elif quality==PyTango.AttrQuality.ATTR_INVALID:
                return '%d,%d,%s'%(1-bool(obj.active), 3, obj.tag)

        l = [(a,self.api[a]) for a in self.alarms]
        print('Sorting ...')
        qualities = dict((k,sorter(x)) for k,x in l)
        ordered = sorted(l,key=(lambda k: qualities[k[0]]))
        
        [v.setModel('') for v in self.buttons.values()]
        self.buttons.clear()
        self.clear()
        
        label = Qt.QLabel("Alarms:")
        self.addWidget(label)
        self.setToolTip("PanicToolbar: %s"%str(self.filters))
        url = os.path.dirname(panic.__file__)+'/'+"panic-icon.gif"
        print '\t%s'%url
        self.addAction(Qt.QIcon(url),'',self.showGui)

        for a,alarm in ordered:
            if (visible>=self.max_visible): break
            if a in self.buttons: continue
            print 'In PanicToolbar.refresh(): adding %s'%alarm
            self.buttons[a] = ToolbarActionButton(self.gui,self.api)
            model = alarm.device+'/'+alarm.get_attribute()
            self.buttons[a].setAlarmModel(a)
            taurus.Attribute(model).changePollingPeriod(60000)
            if self._get_alarm_date(alarm.device, alarm.tag):
                tip = self._get_alarm_date(alarm.device, alarm.tag)
                delimiter=':'
                tooltip=tip[0]+':'+alarm.severity+'\n'+delimiter.join(tip[1:4])+'\n'+tip[4]
            else:
                tooltip=alarm.tag
            self.buttons[a].setToolTip(str(tooltip))
            self.buttons[a].buildMenu()
            self.addWidget(self.buttons[a])
            visible=visible+1
                    
        return
    

        
if __name__ == '__main__':
    qapp = Qt.QApplication([])
    
    if '--panel' in sys.argv:
        import panic.gui.panel
        from panic.gui.panel import QAlarmPanel
        QAlarmPanel.main(*[a for a in sys.argv[1:] if not a.startswith('-')])
    
    if '--toolbar' in sys.argv:
        
        devices = sys.argv[1:]
        if any('/' in d for d in devices):
            filters = None
            attr_list = ['%s/%s'%(d,a) for d in devices for a in PyTango.DeviceProxy(d).get_attribute_list()]
        else:
            filters = devices
            attr_list = []
        if attr_list:
            import taurus
            taurus.setLogLevel('WARNING')
            tmw = TaurusMainWindow()
            taurusForm = TaurusForm(tmw)
            taurusForm.setModel(attr_list)
            tmw.setCentralWidget(taurusForm)
            tmw.statusBar().showMessage('Ready')
            tmw.show()
            s=tmw.splashScreen()
            s.finish(tmw)
        else:
            tmw = Qt.QMainWindow()
            label = Qt.QLabel('Select any alarm from the toolbar')
            tmw.setCentralWidget(label)
            tmw.show()
        tmw.setMinimumWidth(600)
        print '*'*80
        tmw.setWindowTitle('Alarm Toolbar')
        toolbar = PanicToolbar(tmw,filters=filters)
        tmw.addToolBar(toolbar)

        sys.exit(qapp.exec_())

try:
    from fandango.doc import get_fn_autodoc
    __doc__ = get_fn_autodoc(__name__,vars())
except:
    import traceback
    traceback.print_exc()

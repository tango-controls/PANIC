import sys, re, os, traceback, time
import threading
from PyQt4 import QtCore, QtGui, Qt

import PyTango, fandango, taurus, taurus.qt.qtgui.base
import panic,Queue,fandango.qt
from fandango.excepts import Catched
from taurus.qt.qtgui import container
from taurus.qt.qtgui.panel import TaurusForm
from taurus.qt.qtgui.resource import getThemeIcon
from taurus.core import AttributeNameValidator

from row import AlarmRow
from widgets import *
from editor import FormulaEditor,AlarmForm
from core import Ui_AlarmList
#from htmlview import *

OPEN_WINDOWS = []

try:
    from alarmhistory import *
except Exception,e:
    #print 'UNABLE TO LOAD SNAP ... HISTORY VIEWER DISABLED: ',str(e)
    SNAP_ALLOWED=False

PARENT_CLASS = QtGui.QWidget
class AlarmGUI(PARENT_CLASS,iLDAPValidatedWidget):
    REFRESH_TIME = 10000 #Default period between list order updates
    RELOAD_TIME = 60000 #Default period between database reloads
    MAX_REFRESH = 3 #Controls the new interval set by hurry()
    MAX_ALARMS = 30 #AlarmRow.use_list will be enabled only if number of alarms is higher than this number
    USE_EVENT_REFRESH = False #Controls if alarm events will hurry buildList()
    __pyqtSignals__ = ("valueChanged",)
    
    def __init__(self, parent=None, filters='*', options=None, mainwindow=None):
        print '>'*80
        options = options or {}
        if not fandango.isDictionary(options):
            options = dict((o.replace('--','').split('=')[0],o.split('=',1)[-1]) for o in options)
        trace( 'In AlarmGUI(%s): %s'%(filters,options))
        PARENT_CLASS.__init__(self,parent)
        self._ui = Ui_AlarmList()
        self._ui.setupUi(self)
        self.last_reload = 0
        self.filters = filters
        self.mainwindow = mainwindow

        self._ordered=[] #Alarms list ordered
        self.AlarmRows = {}
        self.timeSortingEnabled=None
        self.changed = True
        self.expert = False
        self.tools = {} #Widgets dictionary
        try:
            px = QtGui.QPixmap('/homelocal/sicilia/applications/Panic/PanicBanner.gif')
            self.splash = QtGui.QSplashScreen(px)
            self.splash.showMessage('initializing application...')
            self.splash.show()
            print 'showing splash ... %s'%px.size()
        except: print traceback.format_exc()

        self._message = QtGui.QMessageBox(self)
        self._message.setWindowTitle("Empty fields")
        self._message.setIcon(QtGui.QMessageBox.Critical)

        self.api = panic.AlarmAPI()
        self.default_regEx=options.get('filter',None) or filters or None
        self.regEx = self.default_regEx
        if self.regEx and str(self.regEx)!=os.getenv('PANIC_DEFAULT'): 
            print 'Setting RegExp filter: %s'%self.regEx
            self._ui.regExLine.setText(str(self.regEx))
        self.severities=['alarm', 'error', 'warning', 'debug', '']
        self.setExpertView(False)
        self.setExpertView(True) #checked=('expert' in options))
        
        if self.mainwindow:
            #self.mainwindow.setWindowTitle(str(os.getenv('TANGO_HOST')).split(':',1)[0]+' Alarm Widget (%s)'%self.filters)
            self.mainwindow.setWindowTitle('PANIC (%s@%s)'%(self.filters or self.regEx or '',str(os.getenv('TANGO_HOST')).split(':',1)[0]))
            
        try:
            assert SNAP_ALLOWED
            self.snapi=snap.SnapAPI()
            self.ctx_names=[c.name for c in self.snapi.get_contexts().values()]
        except:
            self.snapi = None
            self.ctx_names = []

        if not self.api.keys(): trace('NO ALARMS FOUND IN DATABASE!?!?')
        AlarmRow.TAG_SIZE = 1+max([len(k) for k in self.api] or [40])
        N = len(self.getAlarms())
        if N<150: 
            self._ui.sevDebugCheckBox.setChecked(True)
            self._ui.activeCheckBox.setChecked(False)
            self.REFRESH_TIME = 5000
            AlarmRow.REFRESH_TIME = 5000
        else:
            self._ui.sevDebugCheckBox.setChecked(False)
            self._ui.activeCheckBox.setChecked(True)
            self.severities.remove('debug')
        if N<=self.MAX_ALARMS: self.USE_EVENT_REFRESH = True

        #self.connectAll()
        #self.buildList()
        self._connected = False
        self.modelsQueue = Queue.Queue()
        self.modelsThread = fandango.qt.TauEmitterThread(parent=self,queue=self.modelsQueue,method=self.setAlarmRowModel)
        self.modelsThread.start()
        #TIMERS (to reload database and refresh alarm list).
        self.reloadTimer = QtCore.QTimer()
        self.refreshTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.refreshTimer, QtCore.SIGNAL("timeout()"), self.onRefresh)
        QtCore.QObject.connect(self.reloadTimer, QtCore.SIGNAL("timeout()"), self.onReload)
        self.reloadTimer.start(5000.)
        self.refreshTimer.start(2*self.REFRESH_TIME)
        
        self.source = "" #Value in first comboBox
        self.setFirstCombo()
        self.setSecondCombo()
        self._ui.infoLabel0_1.setText(self._ui.contextComboBox.currentText())
        self.updateStatusLabel()
        print('__init__ done')
        
        #if not SNAP_ALLOWED:
            #Qt.QMessageBox.critical(self,"Unable to load SNAP",'History Viewer Disabled!', QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)
        #print "******************** out of AlarmGUI.__init__() ****************************"
        
    def getAlarms(self):
        #It returns a list with all alarm objects matching the filter provided at startup
        return self.api.filter_alarms(self.filters)
    
    def getCurrents(self):
        return self._ordered
        
    def saveToFile(self):
        filename = str(QtGui.QFileDialog.getSaveFileName(self.mainwindow,'File to save','.','*.csv'))
        self.api.export_to_csv(filename,alarms=self.getCurrents())
        return filename
        
    def loadFromFile(self,default='*.csv',ask=True):
        try:
            errors = []
            if ask or '*' in default:
                if '/' in default: d,f = default.rsplit('/',1)
                else: d,f = '.',default
                filename = Qt.QFileDialog.getOpenFileName(self.mainwindow,'Import file',d,f)
            else:
                filename = default
            if filename:
                if not self.validate('LoadFromFile(%s)'%filename): return
                alarms = self.api.load_from_csv(filename,write=False)
                selected = AlarmsSelector(sorted(alarms.keys()),text='Choose alarms to import')
                devs = set()
                for tag in selected:
                    v = alarms[tag]
                    if v['device'] not in self.api.devices: errors.append('PyAlarm %s does not exist!!!'%v['device'])
                    else:
                        devs.add(v['device'])
                        if tag not in self.api: self.api.add(**v)
                        else: self.api.modify(**v)
                [self.api.devices[d].init() for d in devs]
            if errors: QtGui.QMessageBox.warning(self.mainwindow,'Error','\n'.join(errors),QtGui.QMessageBox.Ok)
            return filename
        except:
            import traceback
            QtGui.QMessageBox.warning(self.mainwindow,'Error',traceback.format_exc(),QtGui.QMessageBox.Ok)
            
    def editFile(self):
        filename = self.saveToFile()
        editor,ok = QtGui.QInputDialog.getText(self.mainwindow,'Choose your editor',"Type your editor choice, you'll have to call 'Import CSV' after editing",QtGui.QLineEdit.Normal,'oocalc %s'%filename)
        if ok:
            os.system('%s &'%str(editor))
            v = QtGui.QMessageBox.warning(None,'Load from file', \
                '%s file may have been modified, do you want to load your changes?'%filename, \
                QtGui.QMessageBox.Yes|QtGui.QMessageBox.No);
            if v == QtGui.QMessageBox.Yes:
                self.loadFromFile(filename,ask=False)
            return filename
            
    def setViewMenu(self,action=None):
        print 'In AlarmGUI.setViewMenu(%s)'%action
        self.mainwindow.viewMenu.clear()
        windows = WindowManager.getWindowsNames()
        print windows
        for w in windows:
            self.mainwindow.viewMenu.addAction(w,lambda x=w:WindowManager.putOnTop(x))
        self.mainwindow.viewMenu.addAction('Close All',lambda : WindowManager.closeAll())
        return
        
    def setExpertView(self,checked=None):
        checked = checked or self._ui.actionExpert.isChecked()
        if checked:
            self._ui.newButton.show()
            self._ui.deleteButton.show()
            #self._ui.buttonClose.show()
            #self._ui.frame_2.show()
            
            #self.clearAlarmData()
            ##self._dataWidget._wi.disabledCheckBox.setEnabled(False)
            ##self._dataWidget._wi.ackCheckBox.setEnabled(False)
            #self._ui.splitWidget.setSizes([1,1])
            #self._ui.splitWidget.setHandleWidth(20)
            #self._ui.splitWidget.setChildrenCollapsible(True)
            #if self.mainwindow and not self.expert: 
                #self.mainwindow.resize(Qt.QSize(1400,self.mainwindow.size().height()))
            #self.enableEditForm(False)
        else:
            #self._ui.newButton.hide()
            #self._ui.deleteButton.hide()
            #self._ui.buttonClose.hide()
            #self._ui.frame_2.hide()
            #self._ui.splitWidget.setSizes([1,0])
            #self._ui.splitWidget.setHandleWidth(0)
            #self._ui.splitWidget.setChildrenCollapsible(False)
            #if self.mainwindow and self.expert: 
                #self.mainwindow.resize(Qt.QSize(800,self.mainwindow.size().height()))
            pass
        self.expert = checked
        return
        
    def setModel(self,model):
        # THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        try:
            if model!= self.regEx:
                print('AlarmGUI.setModel(%s)'%model)
                self._ui.regExLine.setText(model or self.default_regEx)
                self.onRegExUpdate()
        except:
            print traceback.format_exc()

    def setAlarmRowModel(self,nr,obj,alarm,use_list):
        #print '%d/%d rows, %d models' % (nr,len(self.AlarmRows),len(taurus.Factory().tango_attrs.keys()))
        obj.setAlarmModel(alarm,use_list)
        self.updateStatusLabel()

    def connectAll(self):
        trace('connecting')
        #QtCore.QObject.connect(self.refreshTimer, QtCore.SIGNAL("timeout()"), self.onRefresh)
        if self.USE_EVENT_REFRESH: QtCore.QObject.connect(self,QtCore.SIGNAL("valueChanged"),self.hurry)
        #Qt.QObject.connect(self._ui.actionExpert,Qt.SIGNAL("changed()"),self.setExpertView)
        
        QtCore.QObject.connect(self._ui.contextComboBox, QtCore.SIGNAL("currentIndexChanged(QString)"), self._ui.infoLabel0_1.setText)
        QtCore.QObject.connect(self._ui.refreshButton, QtCore.SIGNAL("clicked()"), self.onReload) # "Refresh"
        QtCore.QObject.connect(self._ui.contextComboBox, QtCore.SIGNAL("currentIndexChanged(int)"), self.setSecondCombo)
        QtCore.QObject.connect(self._ui.comboBoxx, QtCore.SIGNAL("currentIndexChanged(QString)"), self.onFilter)
        
        QtCore.QObject.connect(self._ui.listWidget, QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'), self.onContextMenu)
        QtCore.QObject.connect(self, QtCore.SIGNAL('setfontsandcolors'),AlarmRow.setFontsAndColors)
        QtCore.QObject.connect(self._ui.selectCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.onSelectAllNone)
        QtCore.QObject.connect(self._ui.sevAlarmCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.onSevFilter)
        QtCore.QObject.connect(self._ui.sevErrorCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.onSevFilter)
        QtCore.QObject.connect(self._ui.sevWarningCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.onSevFilter)
        QtCore.QObject.connect(self._ui.sevDebugCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.onSevFilter)
        
        QtCore.QObject.connect(self._ui.activeCheckBox, QtCore.SIGNAL('stateChanged(int)'), self.onFilter)
        QtCore.QObject.connect(self._ui.regExUpdate, QtCore.SIGNAL("clicked(bool)"), self.onRegExUpdate)
        QtCore.QObject.connect(self._ui.listWidget, QtCore.SIGNAL("itemSelectionChanged()"), self.printRows)
        #if self.expert: 
        QtCore.QObject.connect(self._ui.newButton, QtCore.SIGNAL("clicked()"), self.onNew) # "New"
        QtCore.QObject.connect(self._ui.deleteButton, QtCore.SIGNAL("clicked(bool)"), self.onDelete) # Delete
        QtCore.QObject.connect(self._ui.listWidget, QtCore.SIGNAL("itemSelectionChanged()"), self.onItemSelected)
        QtCore.QObject.connect(self._ui.listWidget, QtCore.SIGNAL("itemDoubleClicked(QListWidgetItem *)"), self.onView) #self.onEdit)
        
        #QtCore.QObject.connect(self._ui.listWidget, QtCore.SIGNAL("currentRowChanged(int)"), self.setAlarmData)
        QtCore.QObject.connect(self._ui.buttonClose,QtCore.SIGNAL("clicked()"), self.close)
        trace('all connected')

    def printRows(self):
        for row in self._ui.listWidget.selectedItems():
          print row.__repr__()
    
    def close(self):
        Qt.QApplication.quit()

    #def show(self):
        #print '---------> show()'
        #PARENT_CLASS.show(self)
    
    def removeAlarmRow(self,alarm_tag):
        #Removing listeners to this alarm attribute
        trace('In removeAlarmRow(%s)'%alarm_tag)
        try:
            row = self.AlarmRows.pop(alarm_tag)
            ta = taurus.Attribute(row.getModel())
            ta.removeListener(row)
            row.setModel(None)
        except:
            trace('Unable to %s.removeListener():\n\t%s'%(alarm_tag,traceback.format_exc()))
    
    ###########################################################################
    # AlarmList
    
    def emitValueChanged(self):
        #trace ('emitValueChanged()')
        self.emit(Qt.SIGNAL("valueChanged"))
        
    def hurry(self):
        """
        on ValueChanged event a refresh will be scheduled in 1 second time
        (so all events received in a single second will be summarized)
        """
        if not self.changed: 
            trace('hurry(), changed = True')
            self.changed = True
            self.reloadTimer.setInterval(self.MAX_REFRESH*1000.)

    @Catched
    def onReload(self):
        # THIS METHOD WILL NOT MODIFY THE LIST IF JUST FILTERS HAS CHANGED; TO UPDATE FILTERS USE onRefresh INSTEAD
        try:
            trace('onReload(%s)'%self.RELOAD_TIME)
            print '+'*80
            now = time.time()
            trace('%s -> AlarmGUI.onReload() after %f seconds'%(now,now-self.last_reload))
            self.last_reload=now
            self.api.load()
            
            if self.api.keys():
                AlarmRow.TAG_SIZE = 1+max(len(k) for k in self.api.keys())
                
            #Removing deleted/renamed alarms
            for tag in self.AlarmRows.keys():
                if tag not in self.api:
                    self.removeAlarmRow(tag)
                    
            #Updating the alarm list
            self.buildList(changed=False)
            if self.changed: self.showList()
            
            #Triggering refresh timers
            self.reloadTimer.setInterval(self.RELOAD_TIME)
            self.refreshTimer.setInterval(self.REFRESH_TIME)

            if not self._connected:
                self._connected = True
                self.connectAll()
        except:
            trace(traceback.format_exc())
    
    @Catched
    def onRefresh(self):
        """Just checks order, no reload, no filters"""
        trace('onRefresh(%s)'%self.REFRESH_TIME)
        self.buildList(changed=False)
        if self.changed: self.showList()
        self.refreshTimer.setInterval(self.REFRESH_TIME)
    
    @Catched
    def onFilter(self,*args):
        """Forces an update of alarm list order and applies filters (do not reload database)."""
        trace('onFilter()')
        self.buildList(changed=True)
        self.showList()
        self.refreshTimer.setInterval(self.REFRESH_TIME)

    def onSevFilter(self):
        # THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        self.getSeverities()
        self.onFilter()

    def onRegExUpdate(self):
        # THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        self.regEx = str(self._ui.regExLine.text()).strip() or self.default_regEx
        self._ui.activeCheckBox.setChecked(False)
        self.onFilter()

    @Catched
    def regExFiltering(self, source):
        alarms,regexp=[],str(self.regEx).lower().strip()
        exclude = regexp.startswith('!')
        if exclude: regexp = regexp.replace('!','').strip()
        for a in source:
            match = fandango.searchCl(regexp, a.receivers.lower()+' '+a.severity.lower()+' '+a.description.lower()+' '+a.tag.lower()+' '+a.formula.lower()+' '+a.device.lower())
            if (exclude and not match) or (not exclude and match): alarms.append(a)
        trace('\tregExFiltering(%d): %d alarms returned'%(len(source),len(alarms)))
        return alarms
            
    def onSelectAllNone(self):
        if self._ui.selectCheckBox.isChecked():
            self._ui.listWidget.selectAll()
        else:
            self._ui.listWidget.clearSelection()

    def setRowModels(self):
        trace('AlarmGUI.setRowModels()')
        for alarm in self.getAlarms():
            self.AlarmRows[alarm.tag].setAlarmModel(alarm)
            
    def setFirstCombo(self):
        self.setComboBox(self._ui.contextComboBox,['Alarm','Time','Devices','Hierarchy','Receiver','Severity'],sort=False)

    def setSecondCombo(self):
        source = str(self._ui.contextComboBox.currentText())
        trace("AlarmGUI.setSecondCombo(%s)"%source)
        if source == self.source: return
        else: self.source = source
        self._ui.comboBoxx.clear()
        self._ui.comboBoxx.show()
        self._ui.infoLabel0_1.show()
        self._ui.comboBoxx.setEnabled(True)
        if source =='Devices':
            r,sort,values = 1,True,sorted(set(a.device for a in self.getAlarms()))
        elif source =='Receiver':
            #r,sort,values = 2,True,list(set(a for a in self.api.phonebook.keys() for l in self.api.values() if a in l.receivers))
            r,sort,values = 2,True,list(set(s for a in self.getAlarms() for s in ['SNAP','SMS']+[r.strip() for r in a.receivers.split(',')]))
        elif source =='Severity':
            r,sort,values = 3,False,['DEBUG', 'WARNING', 'ALARM', 'ERROR']
        elif source =='Hierarchy':
            r,sort,values = 4,False,['ALL', 'TOP', 'BOTTOM']
        elif source =='Time':
            r,sort,values = 5,False,['DESC', 'ASC']
        else: #"Alarm Status"
            r,sort,values = 0,False,['ALL', 'AVAILABLE', 'FAILED','HISTORY']
        self.setComboBox(self._ui.comboBoxx,values=values,sort=sort)
        return r

    def setComboBox(self, comboBox, values, sort=False):
#        print "setRecData"
        comboBox.clear()
        [comboBox.addItem(QtCore.QString(i)) for i in values]
        if sort: comboBox.model().sort(0, Qt.Qt.AscendingOrder)
        
    def setSeverity(self,tag,severity):
        tags = tag if fandango.isSequence(tag) else [tag]
        self.setAllowedUsers(self.api.get_admins_for_alarm(len(tags)==1 and tags[0]))
        if not self.validate('setSeverity(%s,%s)'%(tags,severity)):
            return
        for tag in tags:
            severity = str(severity).upper().strip()
            if severity not in panic.ALARM_SEVERITIES: raise Exception(severity)
            self.AlarmRows[tag].get_alarm_object().setup(severity=severity.upper(),write=True)
        [f.setAlarmData() for f in WindowManager.WINDOWS if isinstance(f,AlarmForm)]
        
    def getSeverities(self):
        self.severities=[]
        if self._ui.sevAlarmCheckBox.isChecked(): self.severities.append('alarm')
        if self._ui.sevErrorCheckBox.isChecked(): self.severities.append('error')
        if self._ui.sevWarningCheckBox.isChecked():
            self.severities.append('warning')
            self.severities.append('')
        if self._ui.sevDebugCheckBox.isChecked(): self.severities.append('debug')
        return self.severities
        
    def getCurrentAlarm(self):
        return self._ui.listWidget.currentItem().get_alarm_object()
    
    def getCurrentTag(self):
        return self._ui.listWidget.currentItem().get_alarm_tag()
        
    def getSelectedRows(self,extend=False):
        targets = self._ui.listWidget.selectedItems()
        if extend:
            subs = [a for t in targets for a in self.api.parse_alarms(t.alarm.formula)]
            targets.extend(self.AlarmRows.get(a) for a in subs if a in self.AlarmRows and not any(t.tag==a for t in targets))
        return targets

    def findListSource(self, dev=None):
        combo1, combo2 = str(self._ui.contextComboBox.currentText()), str(self._ui.comboBoxx.currentText())
        #print "findListSource(%s,%s), filtering ..."%(combo1,combo2)
        self.timeSortingEnabled=None
        self.source = combo1
        alarms = self.getAlarms()
        if self.source == "Devices":
            self._alarmsList = self.api.get(device=combo2,alarms=alarms) if combo2 else []
        elif self.source == 'Receiver':
            self._alarmsList = self.api.get(receiver=combo2,alarms=alarms) if combo2 else []
        elif self.source == 'Severity':
            self._alarmsList = self.api.filter_severity(combo2,alarms=alarms)
        elif self.source == 'Hierarchy':
            self._alarmsList = self.api.filter_hierarchy(combo2,alarms=alarms)
        elif self.source == 'Time':
            self.timeSortingEnabled=combo2
        else:
            self._alarmsList = alarms

        self.api.servers.states()
        failed = [s.lower() for s in self.api.servers if self.api.servers[s].state is None]
        if failed:
            pass #trace('findListSource(%s,%s): %d servers are not running: %s'%(combo1, combo2,len(failed),failed))
        
        #timeSorting Filter moved to showList() method
        #self._alarmsList = [a for a in self._alarmsList if not self.timeSortingEnabled or self.api.servers.get_device_server(a.device).lower() not in failed]
        #print '\tfiltering done, returning %d/%d alarms'%(len(self._alarmsList),len(self.api.alarms.keys()))
        return self._alarmsList

    def filterByState(self, source):
        result=[]
        stateFilter=self._ui.comboBoxx.currentText()
        for a in source:
            if stateFilter=='AVAILABLE':
                if a.tag in self.AlarmRows and (str(self.AlarmRows[a.tag].quality) in ['ATTR_VALID', 'ATTR_ALARM', 'ATTR_CHANGING', 'ATTR_WARNING']): result.append(a)
            elif stateFilter=='FAILED':
                if a.tag not in self.AlarmRows or (str(self.AlarmRows[a.tag].quality) == 'ATTR_INVALID'): result.append(a)
            elif stateFilter=='HISTORY':
                if SNAP_ALLOWED and a.tag in self.ctx_names: result.append(a)
            else:
                result.append(a)
        trace('filterByState(%d): %d alarms returned'%(len(source),len(result)))
        return result

    def alarmSorter(self,obj):
        """obj is a panic.Alarm object """
        #Quality/Value should be managed by EventReceived, not read here!
        quality = obj.get_quality()
        if obj.tag in self.AlarmRows and self.AlarmRows[obj.tag].alarm is not None:
            row =  self.AlarmRows[obj.tag]
            if row.alarm.active!=obj.active:
                print '>'*80
                trace('ALARM API NOT UPDATED? : %s vs %s ' %(obj,row.alarm))
                print '>'*80
            acknowledged,disabled,active = row.alarmAcknowledged,row.alarmDisabled,row.alarm.active
            if self.AlarmRows[obj.tag].quality == PyTango.AttrQuality.ATTR_INVALID: #It will update only INVALID ones, the rest will keep DB severity
                quality = PyTango.AttrQuality.ATTR_INVALID
        else: acknowledged,disabled,active,quality = False,False,False,PyTango.AttrQuality.ATTR_INVALID #Not updated will be invalid

        ACT = 0 if disabled else (-2 if (acknowledged and active) else (-1 if obj.active else 1))

        if self.timeSortingEnabled:
            #Ordered by active first, then time ASC, then name
            sorting = self._ui.comboBoxx.currentText()
            date = self.AlarmRows[obj.tag].get_alarm_time()
            return (-1*date if sorting=='DESC' else date, obj.tag)
        else:
            #Ordered by active first, then severity, then active time, then name
            if quality==PyTango.AttrQuality.ATTR_ALARM:
                return (ACT, 0, obj.active, obj.tag)
            elif quality==PyTango.AttrQuality.ATTR_WARNING:
                return (ACT, 1, obj.active, obj.tag)
            elif quality==PyTango.AttrQuality.ATTR_VALID:
                return (ACT, 2, obj.active, obj.tag)
            elif quality==PyTango.AttrQuality.ATTR_INVALID:
                return (ACT, 3, obj.active, obj.tag)

    @Catched
    def buildList(self,changed=False):
        self._ui.listWidget.blockSignals(True)
        self.changed = changed or self.changed
        trace('buildList(%s)'%self.changed)
        #print "%s -> AlarmGUI.buildList(%s)"%(time.ctime(), ['%s=%s'%(s,getattr(self,s,None)) for s in ('regEx','severities','timeSortingEnabled','changed',)])
        try:
            l = [a for a in self.findListSource() if a.severity.lower() in self.severities]
            l = [getattr(self.AlarmRows.get(a.tag,None),'alarm',None) or a for a in l]
            if (self.regEx!=None): 
                trace('\tFiltering by regEx: %s'%self.regEx)
                l=self.regExFiltering(l)
            if str(self._ui.comboBoxx.currentText()) != 'ALL': 
                l=self.filterByState(l)
            
            #print '\tSorting %d alarms ...'%len(l)
            qualities = dict((x,self.alarmSorter(x)) for x in l)
            ordered = filter(bool,sorted(l,key=(lambda x: qualities[x])))
            if len(ordered)!=len(self._ordered): 
                print('Length of alarm list changed; changed = True')
                self.changed = True
            #print '\tAlarms in list are:\n'+'\n'.join(('\t\t%s;%s'%(x,qualities[x])) for x in ordered)
            
            #Updating alarms from api
            for nr, alarm in list(enumerate(ordered)):
                if not self.changed and self._ordered[nr]!=alarm: 
                    trace('\tRow %s moved; changed = True'%alarm.tag)
                    self.changed = True
                if alarm is None:
                    trace('\tEmpty alarm found at %d'%nr)
                    continue
                if alarm.tag not in self.AlarmRows:
                    #print '\t%s,%s,%s: Creating AlarmRow ...'%(alarm.tag,bool(alarm.active),alarm.get_quality())
                    row = self.AlarmRows[alarm.tag] = AlarmRow(api=self.api,qtparent=self)
                    trace('\tNew alarm: %s; changed = True'%alarm.tag)
                    try: 
                        self.modelsQueue.put((nr,row,alarm,(len(ordered)>self.MAX_ALARMS)))
                        #self.AlarmRows[alarm.tag].setAlarmModel(alarm,use_list=(len(self.ordered)>MAX_ALARMS))
                        self.changed = True
                    except Exception,e: trace('===> AlarmRow.setModel(%s) FAILED!: %s' %(alarm.tag,e))
                else:
                    row = self.AlarmRows[alarm.tag]
                    model = AttributeNameValidator().getParams(row.getModel())
                    olddev = model['devicename'] if model else None
                    if alarm.device != olddev:
                        trace('\t%s device changed: %s => %s; changed = True'%(alarm.tag,alarm.device,olddev))
                        self.modelsQueue.put((nr,row,alarm,(len(ordered)>self.MAX_ALARMS)))
                        self.changed = True
            if self.changed: self._ordered = ordered
            if self.modelsQueue.qsize(): 
                self.modelsThread.next()
        except:
            trace('AlarmGUI.buildList(): Failed!\n%s'%traceback.format_exc())
        #if not self.changed: print '\tAlarm list not changed'
        self._ui.listWidget.blockSignals(False)
        #print '*'*80

    @Catched
    def showList(self):
        """
        This method just redraws the list keeping the currently selected items
        """
        trace('%s -> AlarmGUI.showList()'%time.ctime())
        #self._ui.listWidget.blockSignals(True)
        currents = self._ui.listWidget.selectedItems()
        trace('\t\t%d items selected'%len(currents))
        trace('\t\tremoving objects from the list ...')
        while self._ui.listWidget.count():
            delItem = self._ui.listWidget.takeItem(0)
            #del delItem
        trace('\t\tdisplaying the list ...')
        ActiveCheck = self._ui.activeCheckBox.isChecked() or self.timeSortingEnabled
        for alarm in self._ordered:
            obj = self.AlarmRows[alarm.tag]
            if not ActiveCheck or (obj.alarm and not obj.alarmAcknowledged and (obj.alarm.active or (not self.timeSortingEnabled and str(obj.quality) == 'ATTR_INVALID'))):
                self._ui.listWidget.addItem(obj)
            obj.updateIfChanged()
        try:
            #THIS SHOULD BE DONE EMITTING A SIGNAL!
            if currents is not None and len(currents):
                self._ui.listWidget.setCurrentItem(currents[0])
                for current in currents:
                    trace('\t\tselecting %s item'%current.tag)
                    #self._ui.listWidget.setCurrentItem(current)
                    current.setSelected(True)
                #if self.expert: self.setAlarmData(current) #Not necessary
        except:
            print traceback.format_exc()
        self.changed = False
        trace('\t\tshowList(): %d alarms added to listWidget.'%self._ui.listWidget.count())
        self.updateStatusLabel()
        #self._ui.listWidget.blockSignals(False)
        
    def updateStatusLabel(self):
        nones = len([v for v in self.AlarmRows.values() if v.alarm is None])
        added = self._ui.listWidget.count()
        size = len(self.getAlarms())
        if nones or not self._connected: self._ui.statusLabel.setText('Loading %s ... %d / %d'%(self.filters,size-nones,size))
        else: 
            self._ui.statusLabel.setText('Showing %d %s alarms, %d in database.'%(added,self.filters,size))
            if self.splash:
                try: 
                    print 'closing splash ...'
                    self.splash.finish(None)
                    self.splash = None
                except: print traceback.format_exc()
        return
            
    ###############################################################################
    
    @Catched
    def onContextMenu(self, point):
        self.popMenu = QtGui.QMenu(self)
        items = self.getSelectedRows(extend=False)
        print('In onContextMenu(%s)'%items)
        row = self._ui.listWidget.currentItem()
        #self.popMenu.addAction(getThemeIcon("face-glasses"), "Preview Attr. Values",self.onSelectAll)

        act = self.popMenu.addAction(getThemeIcon("face-glasses"),"See Alarm Details",self.onView) 
        act.setEnabled(len(items)==1)
        act = self.popMenu.addAction(getThemeIcon("accessories-calculator"),"Preview Formula/Values",
            lambda s=self:WindowManager.addWindow(s.showAlarmPreview()))
        act.setEnabled(len(items)==1)
        self.popMenu.addAction(getThemeIcon("view-refresh"), "Sort/Update List",self.onSevFilter)
        if SNAP_ALLOWED and row.get_alarm_tag() in self.ctx_names:
            act = self.popMenu.addAction(getThemeIcon("office-calendar"), "View History",self.viewHistory)
            act.setEnabled(len(items)==1)
            
        sevMenu = self.popMenu.addMenu('Change Severity')
        for S in ('ERROR','ALARM','WARNING','DEBUG'):
            action = sevMenu.addAction(S)
            self.connect(action, QtCore.SIGNAL("triggered()"), 
                lambda ks=items,s=S: self.setSeverity([k.get_alarm_tag() for k in ks],s))
        
        # Reset / Acknowledge options
        act = self.popMenu.addAction(getThemeIcon("edit-undo"), "Reset Alarm(s)",self.ResetAlarm)
        act.setEnabled(any(i.alarm.active for i in items))

        if len([i.alarmAcknowledged for i in items]) in (len(items),0):
            self.popMenu.addAction(getThemeIcon("media-playback-pause"), "Acknowledge/Renounce Alarm(s)",self.onAckStateChanged)
            #(lambda checked=not row.alarmAcknowledged:self.onAckStateChanged(checked)))
        if len([i.alarmDisabled for i in items]) in (len(items),0):
            self.popMenu.addAction(getThemeIcon("dialog-error"), "Disable/Enable Alarm(s)",self.onDisStateChanged)
            
        # Edit options
        if self.expert:
            self.popMenu.addSeparator()
            act = self.popMenu.addAction(getThemeIcon("accessories-text-editor"), "Edit Alarm",self.onEdit)
            act.setEnabled(len(items)==1)
            act = self.popMenu.addAction(getThemeIcon("edit-copy"), "Clone Alarm",self.onClone)
            act.setEnabled(len(items)==1)
            act = self.popMenu.addAction(getThemeIcon("edit-clear"), "Delete Alarm",self.onDelete)
            act.setEnabled(len(items)==1)
            self.popMenu.addAction(getThemeIcon("applications-system"), "Advanced Config",self.onConfig)
            self.popMenu.addSeparator()
            act = self.popMenu.addAction(getThemeIcon("accessories-text-editor"), "TestDevice",lambda d=row.alarm.device:os.system('tg_devtest %s &'%d))
            act.setEnabled(len(items)==1)
        #self.popMenu.addSeparator()
        #self.popMenu.addAction(getThemeIcon("process-stop"), "close App",self.close)
        self.popMenu.exec_(self._ui.listWidget.mapToGlobal(point))

    def onEdit(self,edit=True):
        alarm = self.getCurrentAlarm()
        print "AlarmGUI.onEdit(%s)"%alarm
        forms = [f for f in WindowManager.WINDOWS if isinstance(f,AlarmForm) and f.getCurrentAlarm().tag==alarm.tag] 
        if forms: 
            form = forms[0]
            form.enableEditForm(edit)
            form.hide()
            form.show()
        else:
            form = WindowManager.addWindow(AlarmForm(self.parent()))
            form.connect(form,Qt.SIGNAL('valueChanged'),self.hurry)
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
            form.connect(form,Qt.SIGNAL('valueChanged'),self.hurry)
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
        tags = tag and [tag] or [getattr(r,'tag',r) for r in self.getSelectedRows(extend=False)]
        if ask:
            v = QtGui.QMessageBox.warning(None,'Pending Changes', \
                'The following alarms will be deleted:\n\t'+'\n\t'.join(tags), \
                QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel)
            if v == QtGui.QMessageBox.Cancel: 
                return

            self.setAllowedUsers(self.api.get_admins_for_alarm(len(tags)==1 and tags[0]))
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
                [f.close() for f in WindowManager.WINDOWS if isinstance(f,AlarmForm) and f.getCurrentAlarm().tag==tag] 
            except: pass

    ###############################################################################

    def viewHistory(self):
        self.ahApp = ahWidget()
        self.ahApp.show()
        #self.ahApp.setAlarmCombo(alarm=str(self._ui.listWidget.currentItem().text().split('|')[0]).strip(' '))
        self.ahApp.setAlarmCombo(alarm=str(self._ui.listWidget.currentItem().get_alarm_tag()))
        
    def showAlarmPreview(self):
        form = AlarmPreview(tag=self.getCurrentAlarm(),parent=self.parent())
        form.show()
        return form
                
    def ResetAlarm(self,alarm=None):
        prompt,cmt=QtGui.QInputDialog,''
        if alarm is None:
            alarms = [t.alarm or api[t.tag] for t in self.getSelectedRows(extend=True) if not t.alarm or t.alarm.active]
        else:
            alarms = [alarm]
        msg = 'The following alarms will be reseted:\n\t'+'\n\t'.join([t.tag for t in alarms])
        trace('In AlarmGUI.ResetAlarm(): %s'%msg)
        while len(cmt)==0:
            cmt, ok=prompt.getText(self,'Input dialog',msg+'\n\n'+'Must type a comment to continue:')
            if not ok: return
        comment=get_user()+': '+cmt
        for alarm in alarms:
            try: alarm.reset(comment) #It also tries to reset hidden alarms
            except: trace(traceback.format_exc())
        self.emitValueChanged()
        self.onFilter()

    def AcknowledgeAlarm(self,alarm=None):
        """THIS METHOD IS NEVER CALLED!?!?!?!?!?!?!"""
        alarm = alarm or self._currentAlarm
        trace('In AlarmGUI.AcknowledgeAlarm(%s)' % (alarm.tag))
        comment, ok = QtGui.QInputDialog.getText(self,'Input dialog','Type a comment to continue:')
        comment = get_user()+': '+comment
        if ok and len(str(comment)) != 0:
            try:
                alarm.reset(comment) #... Why it resets instead of Acknowledge?
                #taurus.Device(alarm.device).command_inout('Acknowledge',[tag, comment])
            except:
                trace(traceback.format_exc())
            self.onFilter()
        elif ok and len(str(comment)) < 3:
            self.AcknowledgeAlarm()
        [f.setAlarmData() for f in WindowManager.WINDOWS if isinstance(f,AlarmForm)]
            
    ###########################################################################
    # AlarmActions
    
    def enableDelete(self, tmp):
#        print "activeDelete"
        self._ui.deleteButton.setEnabled(int(tmp)>=0)
        return tmp>=0
    
    def onItemSelected(self):
        try:
            items = self.getSelectedRows(extend=False)
            if len(items)==1:
                a = items[0]
                tags = a.tag.split('_')
                self.emit(Qt.SIGNAL('alarmSelected'),a.tag)
                models = self.api.parse_attributes(a.alarm.formula)
                devices = sorted(set(fandango.tango.parse_tango_model(m)['device'] for m in models))
                print 'onItemSelected(%s): %s'%(a,devices)
                self.emit(Qt.SIGNAL('devicesSelected'),'|'.join(devices+tags))
        except: traceback.print_exc()
    
    def checkBoxMultiSel(self):
        items = self.getSelectedRows(extend=False)
        if not len(items): return
        if len(items)>1:
            #Qt.QMessageBox.information(self.parent(),
            print '\n\n'
            trace("Warning","Multiple rows selected, multiple acknowledgement is temporarily disabled")
            print '>'*80
            print '\n\n'

    def onAckStateChanged(self,checked=False):
        items = self.getSelectedRows(extend=False)
        if not len([i.alarmAcknowledged for i in items]) in (len(items),0):
            #if not target: 
            trace('onAckStateChanged(%s): nothing to do ...'%len([i.alarmAcknowledged for i in items]))
            return
        trace('onAckStateChanged(%s)'%[r.get_alarm_tag() for r in items])
        waiting=threading.Event()
        checked = not all([i.alarmAcknowledged for i in items])
        if checked:
            prompt=QtGui.QInputDialog
            while 1:
                cmt, ok=prompt.getText(self,'Input dialog','This will prevent reminders from sending.\nType a comment to continue:')
                if not ok: 
                    #Clean up the checkbox
                    #self.setCheckBox(self._dataWidget._wi.ackCheckBox,items[0].alarmAcknowledged)
                    break
                else:
                    comment=get_user()+': '+cmt
                    if len(str(cmt)) > 0:
                        for a in items:
                            try:
                                trace('\tacknowledging '+a.get_alarm_tag())
                                taurus.Device(a.get_alarm_object().device).command_inout('Acknowledge',[str(a.get_alarm_tag()), str(comment)])
                                waiting.wait(0.2)
                            except: print traceback.format_exc()
                        break
                    #self.setCheckBox(self._dataWidget._wi.ackCheckBox,True)
        else:
            for a in items:
                try:
                    trace('\trenouncing '+a.get_alarm_tag())
                    taurus.Device(a.get_alarm_object().device).command_inout('Renounce',str(a.get_alarm_tag()))
                    waiting.wait(0.2)
                except: trace( traceback.format_exc())
            #self.setCheckBox(self._dataWidget._wi.ackCheckBox,False)
        [o.get_acknowledged(force=True) for o in items]
        [f.setAlarmData() for f in WindowManager.WINDOWS if isinstance(f,AlarmForm)]
        self.onFilter()

    def onDisStateChanged(self,checked=False):
        items = self.getSelectedRows(extend=False)
        trace( 'onDisStateChanged(%s)'%[r.get_alarm_tag() for r in items])
        print list((i.get_alarm_tag(),i.alarmDisabled) for i in items)
        if len(set(bool(i.alarmDisabled) for i in items))!=1:
            q = Qt.QMessageBox.warning(self,"Warning!",'Not all elements selected have the same state')
            return
        waiting=threading.Event()
        checked = not all([i.alarmDisabled for i in items])
        if checked:
            reply=Qt.QMessageBox.question(self,"Warning!","Alarm will be disabled.\nDo you want to continue?\n"+'\n'.join(i.get_alarm_tag() for i in items),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
            if reply == QtGui.QMessageBox.Yes:
                self.setAllowedUsers(self.api.get_admins_for_alarm(len(items)==1 and items[0].get_alarm_tag()))
                if not self.validate('onDisable/Enable(%s,%s)'%(checked,[a.get_alarm_tag() for a in items])):
                    return
                
                comment='DISABLED by '+get_user()
                for a in items:
                    try:
                        trace('\tdisabling '+a.get_alarm_tag())
                        taurus.Device(a.get_alarm_object().device).command_inout('Disable',[str(a.get_alarm_tag()), str(comment)])
                        waiting.wait(0.2)
                    except: trace(traceback.format_exc())
                
            else: return
        else:
            for a in items:
                try:
                    trace('\tenabling '+a.get_alarm_tag())
                    taurus.Device(a.get_alarm_object().device).command_inout('Enable',str(a.get_alarm_tag()))
                    waiting.wait(0.2)
                except: trace(traceback.format_exc())
        [o.get_disabled(force=True) for o in items]
        [f.setAlarmData() for f in WindowManager.WINDOWS if isinstance(f,AlarmForm)]
        self.onFilter()
        
    ###########################################################################            
            
###########################################################################
# GUI Main

def main(args=[]):
    import widgets
    from taurus.qt.qtgui import resource
    from taurus.qt.qtgui.application import TaurusApplication

    opts = [a for a in args if a.startswith('--')]
    args = [a for a in args if not a.startswith('--')]
    URL = 'http://www.cells.es/Intranet/Divisions/Computing/Controls/Help/Alarms/panic'
    
    #uniqueapp = Qt.QApplication([])
    uniqueapp = TaurusApplication(opts)
    
    print '='*80
    trace(' Launching Panic ...')
    print '='*80
    
    if '--calc' in opts:
        args = args or ['']
        form = AlarmPreview(*args)
        form.show()
        uniqueapp.exec_()
        return
    
    tmw = CleanMainWindow()
    tmw.setWindowTitle('PANIC') #str(os.getenv('TANGO_HOST')).split(':',1)[0]+' )
    tmw.menuBar = Qt.QMenuBar(tmw)
    tmw.toolsMenu = Qt.QMenu('Tools',tmw.menuBar)
    tmw.fileMenu = Qt.QMenu('File',tmw.menuBar)
    tmw.viewMenu = Qt.QMenu('View',tmw.menuBar)
    tmw.helpMenu = Qt.QMenu('Help',tmw.menuBar)
    
    trace('\tlaunching AlarmGUI ... %s'%sys.argv)
    alarmApp = AlarmGUI(filters='|'.join(a for a in sys.argv[1:] if not a.startswith('--')),options=opts,mainwindow=tmw)
    tmw.setCentralWidget(alarmApp)

    tmw.setMenuBar(tmw.menuBar)
    [tmw.menuBar.addAction(a.menuAction()) for a in (tmw.fileMenu,tmw.toolsMenu,tmw.helpMenu,tmw.viewMenu)]
    toolbar = Qt.QToolBar(tmw)
    toolbar.setIconSize(Qt.QSize(20,20))
    
    tmw.helpMenu.addAction(getThemeIcon("applications-system"),"Webpage",lambda : os.system('konqueror %s &'%URL))
    tmw.toolsMenu.addAction(getThemeIcon("applications-system"),"Jive",lambda : os.system('jive &'))
    tmw.toolsMenu.addAction(getThemeIcon("applications-system"),"Astor",lambda : os.system('astor &'))
    tmw.fileMenu.addAction(resource.getIcon(":/designer/back.png"),"Export to CSV file",alarmApp.saveToFile)
    tmw.fileMenu.addAction(resource.getIcon(":/designer/forward.png"),"Import from CSV file",alarmApp.loadFromFile)
    tmw.fileMenu.addAction(resource.getIcon(":/designer/filereader.png"),"Use external editor",alarmApp.editFile)
    tmw.fileMenu.addAction(getThemeIcon("applications-system"),"Exit",tmw.close)
    tmw.viewMenu.connect(tmw.viewMenu,Qt.SIGNAL('aboutToShow()'),alarmApp.setViewMenu)
    
    from phonebook import PhoneBook
    alarmApp.tools['bookApp'] = WindowManager.addWindow(PhoneBook(container=tmw))
    tmw.toolsMenu.addAction(getThemeIcon("x-office-address-book"), "PhoneBook", alarmApp.tools['bookApp'].show)
    toolbar.addAction(getThemeIcon("x-office-address-book") ,"PhoneBook",alarmApp.tools['bookApp'].show)
    
    trend_action = (resource.getIcon(":/designer/qwtplot.png"),
        'Trend',
        lambda:WindowManager.addWindow(widgets.get_archive_trend(show=True))
        )
    tmw.toolsMenu.addAction(*trend_action)
    toolbar.addAction(*trend_action)
    
    alarmApp.tools['config'] = WindowManager.addWindow(widgets.dacWidget(container=tmw))
    tmw.toolsMenu.addAction(getThemeIcon("applications-system"),"Advanced Configuration", alarmApp.tools['config'].show)
    toolbar.addAction(getThemeIcon("applications-system") ,"Advanced Configuration",alarmApp.tools['config'].show)
    
    toolbar.setMovable(False)
    toolbar.setFloatable(False)
    tmw.addToolBar(toolbar)
    
    if SNAP_ALLOWED:
        alarmApp.tools['history'] = WindowManager.addWindow(widgets.ahWidget(container=tmw))
        tmw.toolsMenu.addAction(getThemeIcon("office-calendar"),"Alarm History Viewer",alarmApp.tools['history'].show)
        toolbar.addAction(getThemeIcon("office-calendar") ,"Alarm History Viewer",alarmApp.tools['history'].show)
    else:
        trace("Unable to load SNAP",'History Viewer Disabled!')
        
    alarm_preview_action = (getThemeIcon("accessories-calculator"),"Alarm Calculator",
        lambda g=alarmApp:WindowManager.addWindow(AlarmPreview.showEmptyAlarmPreview(g)))
    [o.addAction(*alarm_preview_action) for o in (tmw.toolsMenu,toolbar)]
        
    tmw.show()
    return uniqueapp #.exec_()
  
def main_gui():
    import sys
    n = main(sys.argv[1:] or ([os.getenv('PANIC_DEFAULT')] if os.getenv('PANIC_DEFAULT') else [])).exec_()
    sys.exit(n) 
    
if __name__ == "__main__":
    main_gui()

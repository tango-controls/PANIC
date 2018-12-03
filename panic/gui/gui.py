"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import sys, re, os, traceback, time, json
from pprint import pformat
import threading, Queue

import fandango as fn
import fandango.tango as ft
import fandango.qt

from fandango.functional import *
from fandango.qt import Qt
from fandango.excepts import Catched
from fandango.objects import Cached
from fandango.log import tracer,shortstr,pprint,pformat

import panic
import panic.view


#from row import AlarmRow, QAlarm, QAlarmManager
from panic.properties import *
from panic.alarmapi import unicode2str
from panic.gui.actions import QAlarmManager
from panic.gui.views import ViewChooser
from panic.gui.utils import * #< getThemeIcon, getIconForAlarm imported here
from panic.gui.utils import WindowManager #Order of imports matters!
from panic.gui.editor import FormulaEditor,AlarmForm
from panic.gui.ui_gui import Ui_AlarmList
from panic.gui.alarmhistory import ahWidget
from panic.gui.devattrchange import dacWidget

PANIC_URL = 'http://www.pythonhosted.org/panic'    

HELP = """
Usage:
    > panic [-?/--help] [-v/--attach] f0 f1 f2 [--scope=...] [--default=...]

Without arguments, it will parse defaults from 
PANIC.DefaultArgs property of Tango Database

--scope will constrain the devices accessed by the application, cannot
be changed on runtime.

--default will setup a default regular expression to be applied when 
the search field is empty. It will be overriden by any expression entered
by user

Filters (f0, f1, ...) just initialize the regular expression 
search to a default value (f0|f1|f2|...)



"""

OPEN_WINDOWS = []

import utils as widgets
widgets.TRACE_LEVEL = -1

    ###########################################################################
    
PARENT_CLASS = Qt.QWidget
class QAlarmList(QAlarmManager,PARENT_CLASS):
    """    
    Class for managing the self updating alarm list in AlarmGUI.
    
    Arguments and options explained in gui.HELP and AlarmGUI classes
    
    This is just the graphical part,  update/sorting algorithm 
    is implemented by panic.AlarmView class 
    """
    
    #Default period between list order updates
    REFRESH_TIME = 3000
    #Default period between database reloads
    RELOAD_TIME = 60000 
    # new refresh set by hurry()
    MAX_REFRESH = 500 
    #AlarmRow.use_list will be enabled only if number of alarms > MAX_ALARMS
    MAX_ALARMS = 30 
    #Controls if alarm events will hurry buildList()
    USE_EVENT_REFRESH = False 
    
    ALARM_ROW = ['tag','get_state','get_time','device','description']
    ALARM_LENGTHS = [50,10,20,25,200]
    
    __pyqtSignals__ = ("valueChanged",)
    
    def __init__(self, parent=None, filters='', options=None, mainwindow=None,
                 api=None):
              
        options = options or {}
        if not fn.isDictionary(options):
            options = dict((o.replace('-','').split('=')[0],o.split('=',1)[-1]) 
                for o in options)
            
        trace( 'In AlarmGUI(%s): %s'%(filters,options))

        self.last_reload = 0
        self.AlarmRows = {}
        self.timeSortingEnabled=None
        self.changed = True
        self.severities = [] #List to keep severities currently visible
        
        self.expert = False
        self.tools = {} #Widgets dictionary
        
        self.scope = options.get('scope','*') #filters or '*'
        self.default_regEx = options.get('default',filters or '*')
        self.regEx = self.default_regEx
        self.init_ui(parent,mainwindow) #init_mw is called here
        self.NO_ICON = Qt.QIcon()
        
        refresh = int(options.get('refresh',self.REFRESH_TIME))
        self.REFRESH_TIME = refresh
         #AlarmRow.REFRESH_TIME = refresh
        
        #if self.regEx not in ('','*'): 
            #print 'Setting RegExp filter: %s'%self.regEx
            #self._ui.regExLine.setText(str(self.regEx))
               
        self.api = api or panic.AlarmAPI(self.scope)
        trace('AlarmGUI(%s): api done'%self.scope)

        # @TODO: api-based views are not multi-host
        self.view = panic.view.AlarmView(api=self.api,scope=self.scope,
                refresh = self.REFRESH_TIME/1e3,events=False,verbose=1) 
        trace('AlarmGUI(): view done')
        
        self.snapi = None
        self.ctx_names = []

        if not self.api.keys(): trace('NO ALARMS FOUND IN DATABASE!?!?')
        #AlarmRow.TAG_SIZE = 1+max([len(k) for k in self.api] or [40])
        
        N = len(self.getAlarms())
        trace('AlarmGUI(): %d alarms'%N)
        if 1: #N<150: 
            #self._ui.sevDebugCheckBox.setChecked(True)
            self._ui.activeCheckBox.setChecked(False)
        #else:
            #self._ui.sevDebugCheckBox.setChecked(False)
            #self._ui.activeCheckBox.setChecked(True)
            
        if N<=self.MAX_ALARMS: self.USE_EVENT_REFRESH = True
        

        self.init_timers()
        self.init_filters()        
        
        trace('AlarmGUI(): signals done')
        ## connection of ui signals is delayed until first onRefresh()
        
        self.updateStatusLabel()
                    
        trace('AlarmGUI(): done')
        
        ## TODO: in case of "Dead" Panic devices a message should be shown
        # here
    
    ###########################################################################
        
    @Cached(expire=0.2)
    def getAlarms(self,filtered=True):
        """
        It returns a list with all alarms matching the default View filter
        @TODO: it should ignore the current filters set by user.
        """
        trace('getAlarms(): sorting ...',level=0)
        self.view.sort()
        return self.view.ordered
    
    @Cached(expire=0.2)
    def getCurrents(self):
        """
        It returns only the currently shown alarms matching user filters
        """
        return self.getAlarms() #_ordered
    
    def setModel(self,model):
        """
        Method called when a model is set externally (synoptic of drop event)
        """
        # THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        try:
            if model!= self.regEx:
                print('AlarmGUI.setModel(%s)'%model)
                self._ui.regExLine.setText(model or self.default_regEx)
                self.onRegExUpdate()
        except:
            print traceback.format_exc()

    ###########################################################################
    # AlarmList
    
    def emitValueChanged(self):
        #trace ('emitValueChanged()')
        self.emit(Qt.SIGNAL("valueChanged"))    
    
    def init_timers(self):
        #TIMERS (to reload database and refresh alarm list).
        self.reloadTimer = Qt.QTimer()
        self.refreshTimer = Qt.QTimer()
        Qt.QObject.connect(self.refreshTimer, 
                           Qt.SIGNAL("timeout()"), self.onRefresh)
        Qt.QObject.connect(self.reloadTimer, 
                           Qt.SIGNAL("timeout()"), self.onReload)
        #first fast loading
        self.reloadTimer.start(min((5000,self.REFRESH_TIME/2.))) 
        self.refreshTimer.start(self.REFRESH_TIME)    
        
    def hurry(self):
        """
        on ValueChanged event a refresh will be scheduled in 1 second time
        (so all events received in a single second will be summarized)
        """
        if not self.changed: 
            trace('hurry(), changed = True')
            self.changed = True
            self.reloadTimer.setInterval(self.MAX_REFRESH)

    @Catched
    def onReload(self,clear_selection=False):
        # THIS METHOD WILL NOT MODIFY THE LIST IF JUST FILTERS HAS CHANGED; 
        # TO UPDATE FILTERS USE onRefresh INSTEAD
        try:
            trace('onReload(%s)'%self.RELOAD_TIME)
            print '+'*80
            now = time.time()
            trace('%s -> AlarmGUI.onReload() after %f seconds'%(
              now,now-self.last_reload))
            self.last_reload=now
            self._ui.listWidget.clearSelection()
            self.api.load()
            self.setSecondCombo()
            #self.checkAlarmRows()
                    
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
        trace('onRefresh(%s)'%self.REFRESH_TIME,level=1)
        self.buildList(changed=False)
        #if self.changed: ## Changed to be computed row by row
        self.showList()
        self.refreshTimer.setInterval(self.REFRESH_TIME)
        
    def updateStatusLabel(self):
        #nones = len([v for v in self.AlarmRows.values() if v.alarm is None])
        alarms = self.getCurrents()
        size = len(self.api)
        nones = len([v for v in alarms if not v.updated])
        added = len(alarms) #self._ui.listWidget.count()
        
        if nones or not self._connected: 
            text = 'Loading %s ... %d / %d'%(
              self.scope,size-nones,size)
        else: 
            text = (time2str()+': Showing %d %s alarms,'
              ' %d in database.'%(added,self.scope,size))

        trace(text+', nones = %d'%nones)
        self._ui.statusLabel.setText(text)
        if not nones and self.splash:
            try: 
                print 'closing splash ...'
                self.splash.finish(None)
                self.splash = None
            except: print traceback.format_exc()          
            
        return
      

    ###########################################################################
    # AlarmActions
    
    def onItemSelected(self):
        try:
            items = self.getSelectedItems(extend=False)
            if len(items)==1:
                a = self.view.get_alarm_from_text(items[0])
                tags = a.tag.split('_')
                self.emit(Qt.SIGNAL('alarmSelected'),a.tag)
                models = self.api.parse_attributes(a.formula)
                devices = sorted(set(fn.tango.parse_tango_model(m)['device'] 
                                     for m in models))
                print('onItemSelected(%s) devices: %s'%(a,shortstr(devices)))
                self.emit(Qt.SIGNAL('devicesSelected'),'|'.join(devices+tags))
        except: traceback.print_exc()      
            
    def getCurrentAlarm(self,item=None):
        tag = self.getCurrentTag(item)
        if tag:
            return self.api[tag]
    
    def getCurrentTag(self,item=None):
        row = item or self._ui.listWidget.currentItem()
        if row.text():
            return self.view.get_alarm_from_text(row.text())
      
    def onSelectAllNone(self):
        if self._ui.selectCheckBox.isChecked():
            self._ui.listWidget.selectAll()
        else:
            self._ui.listWidget.clearSelection()
        
    def getSelectedItems(self,extend=False):
        """
        extend=True will add children alarms, be careful
        """
        targets = self._ui.listWidget.selectedItems()
        if extend:
            subs = [a for t in targets 
                    for a in self.api.parse_alarms(t.alarm.formula)]
            targets.extend(self.AlarmRows.get(a) 
                    for a in subs if a in self.AlarmRows and not any(t.tag==a for t in targets))
        return targets
    
    def getSelectedAlarms(self,extend=False):
        rows = self.getSelectedItems(extend)
        sel = filter(bool,(self.getCurrentAlarm(r) for r in rows))
        return [a for a in sel if a.tag in self.api]
      
    def getVisibleRows(self,margin=10):
        ql = self._ui.listWidget
        rows = [i for i in range(ql.count()) if 
                ql.visibleRegion().contains(
                  ql.visualItemRect(ql.item(i)))]
        if rows:
            rows = range(max((0,rows[0]-margin)),
                  min((ql.count(),rows[-1]+margin)))
        return rows
      
    def setScrollHook(self,hook):
        """ Hook must be a callable with an int as argument"""
        self._ui.listWidget.verticalScrollBar.valueChanged.connect(hook)
        
    @staticmethod
    def setFontsAndColors(item,alarm):
      
        state,severity = alarm.get_state(),alarm.severity
        severity = severity or panic.DEFAULT_SEVERITY
        color = Qt.QColor("black")
        background = Qt.QColor("white")
        bold = False
        icon = ""
        
        if state in ('OOSRV',):
            color = Qt.QColor("grey").light()
            background = Qt.QColor("white")
            
        elif state in ('ERROR',):
            color = Qt.QColor("red")
            background = Qt.QColor("white")
            
        elif state in ACTIVE_STATES:
            
            if severity in ('ERROR',):
                color = Qt.QColor("white")
                background = Qt.QColor("red").lighter()            

            elif severity in ('ALARM',):
                background = Qt.QColor("red").lighter()
                
            elif severity == 'WARNING':
                background = Qt.QColor("orange").lighter()
                
            elif severity in ('INFO','DEBUG'):
                background = Qt.QColor("yellow").lighter()
                
        elif state in ('DSUPR','SHLVD'):
            color = Qt.QColor("grey").light()
            background = Qt.QColor("white")
            
        elif state == 'NORM':
            color = Qt.QColor("green").lighter()
            background = Qt.QColor("white")
            
        else:
            raise Exception('UnknownState:%s'%state)
          
        icon = getIconForAlarm(alarm)
            
        if (fandango.now() - alarm.get_time()) < 60:
            bold = True

        alarmicon=getThemeIcon(icon) if icon else None
        #tracer('setFontsAndColors(%s,%s,%s,%s,%s)'
          #%(alarm.tag,state,icon,background,bold))
        item.setIcon(alarmicon or Qt.QIcon())
        item.setTextColor(color)
        item.setBackgroundColor(background)
        f = item.font()
        f.setFixedPitch(True)
        f.setBold(bold)
        item.setFont(f)
        
        status = [
            'Severity: '+alarm.severity,
            'Formula: '+alarm.formula,
            'Description: %s'%alarm.description,
            'Alarm Device: %s'%alarm.device,
            'Archived: %s'%('Yes' if 'SNAP' in alarm.receivers else 'No'),
            ]
        for t in ('last_error','acknowledged','disabled','sortkey'):
            v = getattr(alarm,t,None)
            if v: status.append('%s%s: %s'%(t[0].upper(),t[1:],shortstr(v)))
            
        item.setToolTip('\n'.join(status))
        
        try:
            forms = []
            for f in WindowManager.WINDOWS:
                if isinstance(f,AlarmForm):
                    tag = f.getCurrentAlarm().tag
                    if tag == alarm.tag:
                        forms.append(f)
            if forms:
                #@TODO: these checks will be not needed after full update
                tracer("\tupdating %d %s forms"%(len(forms),alarm))
                [f.valueChanged(forced=True) for f in forms]
            else:
                pass #tracer("no forms open?")
        except:
            tracer(traceback.format_exc())
                
        return item

    @Catched
    def buildList(self,changed=False,block=False):
        if block: self._ui.listWidget.blockSignals(True)
        
        self.changed = changed or self.changed
        trace('buildList(%s)'%self.changed,level=2)

        try:
            self.view.apply_filters(self.getFilters())
        except:
            trace('AlarmGUI.buildList(): Failed!\n%s'%traceback.format_exc())
            
        #if not self.changed: print '\tAlarm list not changed'
        if block: self._ui.listWidget.blockSignals(False)

    @Catched
    def showList(self,delete=False):
        """
        This method just redraws the list keeping the currently selected items
        """
        trace('%s -> AlarmGUI.showList()'%time.ctime(),level=2)
        #self._ui.listWidget.blockSignals(True)
        currents,news = [a.tag for a in self.getSelectedAlarms()],[]
        trace('\t\t%d items selected'%len(currents),level=3)
        
        if delete:
            trace('\t\tremoving objects from the list ...')
            while self._ui.listWidget.count():
                delItem = self._ui.listWidget.takeItem(0)
                #del delItem
            
        trace('\t\tdisplaying the list ...',level=2)
        ActiveCheck = self._ui.activeCheckBox.isChecked() \
                        or self.timeSortingEnabled
        
        data = self.view.sort()
        
        if not data:
            trace('NO ALARMS FOUND!!!',level=1)
        else:
            self.ALARM_LENGTHS[0] = max(len(str(t).split('/')[-1]) 
                                        for t in data)
            self.ALARM_LENGTHS[3] = max(len(str(t).rsplit('/',1)[0]) 
                                        for t in data)
            
        for i in range(len(data)): #self.getVisibleRows():
            t = data[i]
            try:
                data[i] = (self.view.get_alarm(t),
                           self.view.get_alarm_as_text(t,
                              cols=self.ALARM_ROW,
                              lengths=self.ALARM_LENGTHS))
            except:
                traceback.print_exc()

        # data is now a sorted list of alarm,text rows
        for i,t in enumerate(data): #self._ordered:
            #obj = self.AlarmRows[alarm.tag]
            #if not ActiveCheck or (obj.alarm and not obj.alarmAcknowledged 
                                   #and (obj.alarm.active 
                                  #or (not self.timeSortingEnabled 
                                  #and str(obj.quality) == 'ATTR_INVALID'))):
            alarm,text = t
            if i>=self._ui.listWidget.count():
                self._ui.listWidget.addItem("...")
                font = Qt.QFont(Qt.QString("Courier"))
                self._ui.listWidget.item(i).setFont(font)
            
            item = self._ui.listWidget.item(i)
            item.setHidden(False)
            row = str(item.text())
            if text!=row:
                #font = Qt.QFont(Qt.QString("Courier"))
                #self._ui.listWidget.item(i).setFont(font)
                item.setText(text)
                self.setFontsAndColors(item,alarm)

            if alarm.tag in currents:
                try:
                    trace('\tselect %s'%alarm.tag)
                    item.setSelected(True)
                    if alarm.tag == currents[0]:
                        self._ui.listWidget.setCurrentItem(item)
                except: traceback.print_exc()
            else:
                item.setSelected(False)
            
        for i in range(len(data),self._ui.listWidget.count()):
            item = self._ui.listWidget.item(i)
            item.setHidden(True)
            item.setText('')
            item.setBackgroundColor(Qt.QColor('white'))
            item.setIcon(self.NO_ICON)
            
        self.changed = False
        trace('\t\tshowList(): %d alarms match filters.'
              %self._ui.listWidget.count())
        self.updateStatusLabel() #< getAlarms() called again here
        
        #self._ui.listWidget.blockSignals(False)
        
      
    ###########################################################################
    
class QFilterGUI(QAlarmList):
    """
    Class for managing the multiple filter widgets in AlarmGUI
    
    Arguments and options explained in gui.HELP and AlarmGUI classes
    """    
  
    def init_filters(self):
        trace('Setting combos ...')
        self.source = "" #Value in first comboBox
        self.setFirstCombo()
        self.setSecondCombo()
        self._ui.infoLabel0_1.setText(self._ui.contextComboBox.currentText())
        Qt.QObject.connect(self._ui.contextComboBox, 
                           Qt.SIGNAL("currentIndexChanged(QString)"), 
                           self._ui.infoLabel0_1.setText)
        Qt.QObject.connect(self._ui.contextComboBox, 
                           Qt.SIGNAL("currentIndexChanged(int)"), 
                           self.setSecondCombo)
        Qt.QObject.connect(self._ui.comboBoxx, 
                           Qt.SIGNAL("currentIndexChanged(QString)"), 
                           self.onFilter)
        
        Qt.QObject.connect(self._ui.regExUpdate, 
                           Qt.SIGNAL("clicked(bool)"), self.onRegExUpdate)
        Qt.QObject.connect(self._ui.regExSave, 
                           Qt.SIGNAL("clicked(bool)"), self.onRegExSave)        
        Qt.QObject.connect(self._ui.selectCheckBox, 
                           Qt.SIGNAL('stateChanged(int)'), self.onSelectAllNone)
        Qt.QObject.connect(self._ui.activeCheckBox, 
                           Qt.SIGNAL('stateChanged(int)'), self.onFilter)
        
        #@DEPRECATED
        #Qt.QObject.connect(self._ui.sevAlarmCheckBox, 
                           #Qt.SIGNAL('stateChanged(int)'), self.onSevFilter)
        #Qt.QObject.connect(self._ui.sevErrorCheckBox, 
                           #Qt.SIGNAL('stateChanged(int)'), self.onSevFilter)
        #Qt.QObject.connect(self._ui.sevWarningCheckBox, 
                           #Qt.SIGNAL('stateChanged(int)'), self.onSevFilter)
        #Qt.QObject.connect(self._ui.sevDebugCheckBox, 
                           #Qt.SIGNAL('stateChanged(int)'), self.onSevFilter) 
        
        self.regExToolTip = '\n'.join(s.strip() for s in """
        Type a string to filter alarms:
        
          rf : all alarms matching 'rf'
          rf & plc : all alarms matching 'rf' and 'plc'
          rf | eps : all alarms matching 'rf' or 'eps'
          tag=li_* : tag starting with li_
          device=~li/ : device NOT starting with li_
          sr[0-9] : any text matching sr and a digit
          
        """.split('\n'))
        self._ui.regExLine.setToolTip(self.regExToolTip)
        
        
    def getFilters(self):
        """
        Returns a list of dictionaries
        Each key in a dictionary is applied as OR
        Each row in the list is applied as AND
        """
        #TRACE_LEVEL=4
        trace("%s -> AlarmGUI.getFilters(%s)"%(time.ctime(), ['%s=%s'%(
            s,getattr(self,s,None)) for s in 
            ('regEx','severities','timeSortingEnabled','changed',)]),level=2)
        
        filters = []
        device = receiver = formula = state = priority = \
            condition = userfilter = ''
        
        active = self._ui.activeCheckBox.isChecked() \
                        or self.timeSortingEnabled
                    
        combo1 = str(self._ui.contextComboBox.currentText())
        combo2 = str(self._ui.comboBoxx.currentText()).strip()

        if combo1 == 'Time':
            time_sorting = True
        elif combo1 == 'State':
            state = combo2
        elif combo1 == 'Devices': 
            device = combo2
        elif combo1 == 'Domain': 
            device = '^' + combo2 + '/*'
        elif combo1 == 'Family': 
            device = '*/' + combo2 + '/*'         
        elif combo1 == 'Hierarchy': 
            pass
        elif combo1 in ('Annunciator','Receivers'):
            receiver = '*' + re.escape(combo2) + '*'
        elif combo1 == 'Priority':
            priority = combo2     
        elif combo1 == 'PreCondition':
            condition = combo2           
        elif combo1 == 'UserFilters':
            userfilter = combo2
        #elif combo1 == 'Severity': 
            #pass

        #dct = {'tag':regexp or self.default_regEx}
        #if not any(device,r
        if userfilter:
            print('getFilters(%s)'%str(userfilter))
            ff = self.api.get_user_filters()[userfilter]
            filters.extend(ff)
            self._ui.comboBoxx.setToolTip(pformat(ff))
            print(filters)
            
            
        reg_dict = {}
        def parse_regexp(regexp):
            regexp = regexp.strip()
            k,regexp = regexp.split('=') if '=' in regexp else ('',regexp)
            neg = regexp.startswith('~')
            if neg: regexp = regexp[1:].strip()
            #if regexp and not clmatch('^[~\!\*].*',regexp): 
            if not clmatch('.*[\^\$\*].*',regexp):
                s = '.*' if fandango.isRegexp(regexp) else '*'
                regexp = s+regexp.replace(' ',s)+s
            if neg: regexp = '~'+regexp
            if k: reg_dict[k] = regexp
            else: return regexp            
            
        if not any((state,receiver,active,device,priority,
                    self.regEx,userfilter)):
            print('Overriding regexp!')
            self.regEx = self.default_regEx
        if self.regEx:
            #reg_dict updated in parse_regexp
            regexps = [parse_regexp(r) for r in self.regEx.split('&')]
            regexp = ' & '.join(filter(bool,regexps))
            reg_tags = ('tag','device','receivers','formula','state')
            reg_dict.update((k,regexp) for k in reg_tags 
                    if regexp and k not in reg_dict) #keys filtered out!
            filters.append(reg_dict)
        
        if state: filters.append({'state':state})
        if receiver: filters.append({'receivers':receiver})
        if active: filters.append({'active':active})
        if device: filters.append({'device':device})
        if priority: filters.append({'priority':priority})
        if condition: filters.append({'condition':condition})
        
        self._ui.regExUpdate.setToolTip(pformat(filters))
        
        return filters
        
    
    def setFirstCombo(self):
        self.setComboBox(self._ui.contextComboBox,
            #['Alarm','Time','Devices','Hierarchy','Receiver','Severity'],
            ['State','UserFilters','Priority','Devices','PreCondition',
             'Annunciator','Receivers','Domain','Family',],
            sort=False)

    def setSecondCombo(self):
        source = str(self._ui.contextComboBox.currentText())
        trace("AlarmGUI.setSecondCombo(%s)"%source)
        if source == self.source: return
        else: self.source = source
        self._ui.comboBoxx.clear()
        self._ui.comboBoxx.show()
        self._ui.infoLabel0_1.show()
        self._ui.comboBoxx.setEnabled(True)
        devs = sorted(set(a.device for a in self.api.values()))
        if source =='Devices':
            r,sort,values = 1,True,devs
            
        elif source =='PreCondition':
            r,sort,values = 1,True,sorted(set(self.api.devices[d].condition 
                                        for d in devs))
            
        elif source =='Domain':
            r,sort,values = 1,True,sorted(set(d.split('/')[-3] for d in devs))
        elif source =='Family':
            values = sorted(set(d.split('/')[-2] for d in devs if '/' in d))
            r,sort,values = 1,True,values
            
        elif source in ('Annunciator','Receivers'):
            r,sort,values = 2,True,list(set(s for a in self.api.values() 
                    for s in ['SNAP','SMS']+
                    [r.strip() for r in a.receivers.split(',') if r.strip()]))
            
        elif source =='Priority':
            r,sort,values = 3,False,SEVERITIES.keys()
            
        elif source =='UserFilters':
            r,sort,values = 3,False,['']+self.api.get_user_filters().keys()
            
        #@TODO
        #elif source =='Hierarchy':
            #r,sort,values = 4,False,['ALL', 'TOP', 'BOTTOM']
        #elif source =='Time':
            #r,sort,values = 5,False,['DESC', 'ASC']
        #else: #"Alarm Status"
            #r,sort,values = 0,False,['ALL', 'AVAILABLE', 'FAILED','HISTORY']
            
        elif source =='State':
            ss = [''] #empty filter to use default_regEx instead
            ss.append('|'.join(ACTIVE_STATES))
            ss.append('|'.join(DISABLED_STATES))
            ss.extend(AlarmStates.keys())
            r,sort,values = 0,False,ss
            
        self.setComboBox(self._ui.comboBoxx,values=values,sort=sort)
        
        return r

    def setComboBox(self, comboBox, values, sort=False):
#        print "setRecData"
        comboBox.clear()
        [comboBox.addItem(Qt.QString(i)) for i in values]
        if sort: comboBox.model().sort(0, Qt.Qt.AscendingOrder)
        
    #@DEPRECATED
    #def getSeverities(self):
        #self.severities=[]
        #if self._ui.sevAlarmCheckBox.isChecked(): self.severities.append('alarm')
        #if self._ui.sevErrorCheckBox.isChecked(): self.severities.append('error')
        #if self._ui.sevWarningCheckBox.isChecked():
            #self.severities.append('warning')
            #self.severities.append('')
        #if self._ui.sevDebugCheckBox.isChecked(): self.severities.append('debug')
        #return self.severities
      
    ###########################################################################
    
    @Catched
    def onFilter(self,*args):
        """Forces an update of alarm list order and applies filters 
        (do not reload database)."""
        print('onFilter() '+'*'*60)
        print(self.getFilters())
        self.buildList(changed=True)
        self.showList()
        self.refreshTimer.setInterval(self.REFRESH_TIME)

    #@DEPRECATED
    #def onSevFilter(self):
        ## THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        #self.getSeverities()
        #self.onFilter()

    def onRegExUpdate(self):
        # THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        # self.regEx to be updated ONLY if Update is pushed
        self.regEx = str(self._ui.regExLine.text()).lower().strip()
        self._ui.activeCheckBox.setChecked(False)
        self.onFilter()
        
    def onRegExSave(self):
        min_comment,comment_error = 4,'Name too short!'
        try:
            self.onRegExUpdate()
            text = 'Enter a name to save your filter in Tango Database'
            filters = self.api.get_user_filters()
            name, ok = QtGui.QInputDialog.getItem(self,'Save Filter As',
                                        text,['']+filters.keys(),True)
            if not ok: return
            if ok and len(str(name)) < min_comment:
                raise Exception(comment_error)

            name = str(name)
            if name in filters:
                v = QtGui.QMessageBox.warning(None,'Save Filter As',\
                    'Filter %s already exists,\ndo you want to overwrite it?'
                    %name,QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel)
                if v == QtGui.QMessageBox.Cancel: 
                    self.onRegExSave()
            filters.update({name:self.getFilters()})
            self.api.set_user_filters(filters,overwrite=True)
            self.onReload()
        except Exception,e:
            #msg = traceback.format_exc()
            v = QtGui.QMessageBox.warning(self,'Warning',
                                        e.message,QtGui.QMessageBox.Ok)
            if e.message == comment_error: self.onRegExSave()

    @Catched
    def regExFiltering(self, source):
        msg = 'regExFiltering DEPRECATED by AlarmView'
        print(msg)
        raise Exception(msg)
        alarms,regexp=[],str(self.regEx).lower().strip().replace(' ','*')
        exclude = regexp.startswith('!') or regexp.startswith('~')
        if exclude: regexp = regexp.replace('!','').replace('~').strip()
        for a in source:
            match = fn.searchCl(regexp, a.receivers.lower()+' '
                        +a.severity.lower()+' '+a.description.lower()
                        +' '+a.tag.lower()+' '+a.formula.lower()+' '
                        +a.device.lower())
            if (exclude and not match) or (not exclude and match): 
                alarms.append(a)
        trace('\tregExFiltering(%d): %d alarms returned'
              %(len(source),len(alarms)))
        return alarms    

    ###########################################################################      
    
class AlarmGUI(QFilterGUI):
    """
    AlarmGUI, to generate Main window menus and parse OS arguments.

    GUI behaviour is implemented in QFilterGUI and QAlarmList classes.
    
    To see accepted OS arguments run: 

        #python panic/gui/gui.py --help
        
    Summarized:
        
    - PANIC_DEFAULT is a default view, overriden by --view
    - .scope and .default may be defined in the view, and later overriden by arguments
    - --scope="*regexp*" would be the filter to be passed to the panic.api: gui.scope
    - --scope=url1,url2,url3 would be used to open multiple api's
    - --default="*regexp*" would be the default filter for the search bar: gui.default
    - whenever the search bar is empty, .default is used instead
    - args will be joined as gui default
    - gui.current_search: the current contents of the search bar (gui.regEx)
    - gui.current_view: the currently selected view (?)        
    
        
    """
       
    def init_ui(self,parent,mainwindow):
        
        try:
            PARENT_CLASS.__init__(self,parent)
            self._connected = False
            self._ui = Ui_AlarmList()
            self._ui.setupUi(self)
            if mainwindow:
                mainwindow = self.init_mw(mainwindow)
            self.mainwindow = mainwindow
            
            url = os.path.dirname(panic.__file__)+'/gui/icon/panic-6-banner.png'
            trace('... splash ...')
            px = Qt.QPixmap(url)
            self.splash = Qt.QSplashScreen(px)
            self.splash.showMessage('initializing application...')
            self.splash.show()
            trace('showing splash ... %s'%px.size())
            
        except: 
            print traceback.format_exc()
            
        if self.mainwindow:
            
            self.mainwindow.setWindowTitle('PANIC %s (%s[%s]@%s)'%(
                panic.__RELEASE__,self.scope,self.default_regEx,
                fn.get_tango_host().split(':')[0]))
            
            icon = '/gui/icon/panic-6-big.png' #'.svg'
            url = os.path.dirname(panic.__file__)+icon
            px = Qt.QPixmap(url)
            self.mainwindow.setWindowIcon(Qt.QIcon(px))
            
        self.setExpertView(True)

        self._message = Qt.QMessageBox(self)
        self._message.setWindowTitle("Empty fields")
        self._message.setIcon(Qt.QMessageBox.Critical)
        
    def connectAll(self):
        trace('connecting')
        
        #Qt.QObject.connect(self.refreshTimer, Qt.SIGNAL("timeout()"), self.onRefresh)
        if self.USE_EVENT_REFRESH: 
            Qt.QObject.connect(self,Qt.SIGNAL("valueChanged"),self.hurry)
        #Qt.QObject.connect(self, 
            #Qt.SIGNAL('setfontsandcolors'),AlarmRow.setFontsAndColors)
        Qt.QObject.connect(self._ui.listWidget, 
            Qt.SIGNAL("itemSelectionChanged()"), self.onItemSelected)
        Qt.QObject.connect(self._ui.listWidget, 
            Qt.SIGNAL("itemDoubleClicked(QListWidgetItem *)"), self.onView) #self.onEdit)
        #Qt.QObject.connect(self._ui.listWidget, Qt.SIGNAL("currentRowChanged(int)"), self.setAlarmData)
        
        self.connectContextMenu(self._ui.listWidget)
        
        #Qt.QObject.connect(self._ui.actionExpert,
                            #Qt.SIGNAL("changed()"),self.setExpertView)
        Qt.QObject.connect(self._ui.newButton, 
                           Qt.SIGNAL("clicked()"), self.onNew) # "New"
        Qt.QObject.connect(self._ui.deleteButton, 
                           Qt.SIGNAL("clicked(bool)"), self.onDelete) # Delete
        Qt.QObject.connect(self._ui.refreshButton, 
                           Qt.SIGNAL("clicked()"), self.onReload) # "Refresh"        
        Qt.QObject.connect(self._ui.buttonClose,
                           Qt.SIGNAL("clicked()"), self.close)
        
        Qt.QObject.connect(fandango.qt.getApplication(),
                           Qt.SIGNAL("aboutToQuit()"),self.exitThreads)

        trace('all connected')
        
    def init_mw(self,tmw = None):    
        """ 
        Method to initialize main window (menus and frames) 
        """
        t0 = time.time()
        alarmApp = self
        tmw = tmw if isinstance(tmw,Qt.QMainWindow) else CleanMainWindow()
        tmw.setWindowTitle('PANIC')
        tmw.menuBar = Qt.QMenuBar(tmw)
        tmw.toolsMenu = Qt.QMenu('Tools',tmw.menuBar)
        tmw.fileMenu = Qt.QMenu('File',tmw.menuBar)
        tmw.windowMenu = Qt.QMenu('Windows',tmw.menuBar)
        tmw.helpMenu = Qt.QMenu('Help',tmw.menuBar)

        tmw.setMenuBar(tmw.menuBar)
        [tmw.menuBar.addAction(a.menuAction()) 
                for a in (tmw.fileMenu,tmw.toolsMenu,tmw.helpMenu,tmw.windowMenu)]
        toolbar = Qt.QToolBar(tmw)
        toolbar.setIconSize(Qt.QSize(20,20))
        
        tmw.helpMenu.addAction(getThemeIcon("applications-system"),
            "Webpage",lambda : os.system('konqueror %s &'%PANIC_URL))
        tmw.toolsMenu.addAction(getThemeIcon("applications-system"),
            "Jive",lambda : os.system('jive &'))
        tmw.toolsMenu.addAction(getThemeIcon("applications-system"),
            "Astor",lambda : os.system('astor &'))
        tmw.fileMenu.addAction(getThemeIcon(":/designer/back.png"),
            "Export to CSV file",alarmApp.saveToFile)
        tmw.fileMenu.addAction(getThemeIcon(":/designer/forward.png"),
            "Import from CSV file",alarmApp.loadFromFile)
        tmw.fileMenu.addAction(getThemeIcon(":/designer/filereader.png"),
            "Use external editor",alarmApp.editFile)
        tmw.fileMenu.addAction(getThemeIcon("applications-system"),
            "Exit",tmw.close)
        tmw.windowMenu.connect(tmw.windowMenu,
            Qt.SIGNAL('aboutToShow()'),alarmApp.setWindowMenu)
        
        from phonebook import PhoneBook
        alarmApp.tools['bookApp'] = WindowManager.addWindow(
            PhoneBook(container=tmw))
        tmw.toolsMenu.addAction(getThemeIcon("x-office-address-book"), 
            "PhoneBook", alarmApp.tools['bookApp'].show)
        toolbar.addAction(getThemeIcon("x-office-address-book") ,
            "PhoneBook",alarmApp.tools['bookApp'].show)
        
        trend_action = (getThemeIcon(":/designer/qwtplot.png"),
            'Trend',
            lambda:WindowManager.addWindow(widgets.get_archive_trend(show=True))
            )
        tmw.toolsMenu.addAction(*trend_action)
        toolbar.addAction(*trend_action)
        
        alarmApp.tools['config'] = WindowManager.addWindow(
            dacWidget(container=tmw))
        tmw.toolsMenu.addAction(getThemeIcon("applications-system"),
            "Advanced Configuration", alarmApp.tools['config'].show)
        toolbar.addAction(getThemeIcon("applications-system") ,
            "Advanced Configuration",alarmApp.tools['config'].show)
        
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        tmw.addToolBar(toolbar)
        
        if SNAP_ALLOWED:
            alarmApp.tools['history'] = WindowManager.addWindow(
                ahWidget(container=tmw))
            tmw.toolsMenu.addAction(getThemeIcon("office-calendar"),
                "Alarm History Viewer",alarmApp.tools['history'].show)
            toolbar.addAction(getThemeIcon("office-calendar") ,
                "Alarm History Viewer",alarmApp.tools['history'].show)
        else:
            trace("Unable to load SNAP",'History Viewer Disabled!')
            
        alarm_preview_action = (getThemeIcon("accessories-calculator"),
            "Alarm Calculator",lambda g=alarmApp:WindowManager.addWindow(
                AlarmPreview.showEmptyAlarmPreview(g)))
        [o.addAction(*alarm_preview_action) for o in (tmw.toolsMenu,toolbar)]
        
        try:
            import PyTangoArchiving.widget.ArchivingBrowser
            MSW = PyTangoArchiving.widget.ArchivingBrowser.ModelSearchWidget
            alarmApp.tools['finder'] = WindowManager.addWindow(MSW())
            tmw.toolsMenu.addAction(getThemeIcon("system-search"),
                "Attribute Finder",alarmApp.tools['finder'].show)      
            toolbar.addAction(getThemeIcon("system-search"),
                "Attribute Finder",alarmApp.tools['finder'].show) 
        except:
            print('PyTangoArchiving not available')
            #traceback.print_exc()        
            
        import panic.gui.panel
        def showNewAlarmPanel(s=self,a=alarmApp):
            i = len([w for w in WindowManager.getWindowsNames() 
                 if w.startswith('panel')])
            name = 'panel%d'%i
            a.tools[name] = WindowManager.addWindow(
                panic.gui.panel.QAlarmPanel())
            a.tools[name].setModel(s.view)
            a.tools[name].show()
            
        url = os.path.dirname(panic.__file__)+'/gui/icon/panel-view.png'
        panel_icon = Qt.QIcon(Qt.QPixmap(url))
        alarm_panel_action = (panel_icon,"Alarm Panel",showNewAlarmPanel)
        [o.addAction(*alarm_panel_action) for o in (tmw.toolsMenu,toolbar)]
        
        import panic.gui.views
        alarmApp.tools['rawview'] = WindowManager.addWindow(
                panic.gui.views.ViewRawBrowser())
        #url = os.path.dirname(panic.__file__)+'/gui/icon/panel-view.png'
        #panel_icon = Qt.QIcon(Qt.QPixmap(url))
        alarm_panel_action = (getThemeIcon('actions:leftjust.svg'),
            "RawView",lambda s=self:alarmApp.tools['rawview'].setModel(self))
        [o.addAction(*alarm_panel_action) for o in (tmw.toolsMenu,)]          
            
        print('Toolbars created after %s seconds'%(time.time()-t0))
        tmw.setCentralWidget(alarmApp)
        tmw.show()
        return tmw        
            
    ###########################################################################
    # GUI Main

    @staticmethod
    def main(args=[]):
        """Main launcher, load views and stops threads on exit"""
        
        t0 = time.time()
        args = args or ft.get_free_property('PANIC','DefaultArgs')    
        opts = [a for a in args if a.startswith('-')]
        args = [a for a in args if not a.startswith('-')] 
        
        if any(o in opts for o in ('-h','--help','-?')):
            print(HELP)
            return

        from taurus.qt.qtgui.application import TaurusApplication    
        uniqueapp = TaurusApplication([]) #opts)
        
        if '--calc' in opts:
            args = args or ['']
            form = AlarmPreview(*args)
            form.show()
            uniqueapp.exec_()
            return
        
        if '--panel' in opts:
            args = args or ['*']
            import panic.gui.panel
            form = panic.gui.panel.QAlarmPanel()
            form.setModel(args)
            form.show()
            uniqueapp.exec_()
            return

        # ([os.getenv('PANIC_DEFAULT')] if os.getenv('PANIC_DEFAULT') else []))
        
        ## @TODO: Global views (multi-host) to be added
        #if not views:
            #vc = ViewChooser()
            #vc.exec_()
            #views = vc.view
        #if not views or not any(views):
            #sys.exit(-1)

        print '='*80
        trace('launching AlarmGUI ... %s, %s'%(args,opts))
        print '='*80
        alarmApp = AlarmGUI(filters='|'.join(args),
                            options=opts,mainwindow=True)
        print('AlarmGUI created after %s seconds'%(time.time()-t0))    
        #alarmApp.tmw.show()
        n = uniqueapp.exec_()

        print('AlarmGUI exits ...')    

        sys.exit(n) 
        
    
    def close(self):
        print('AlarmGUI.close()')
        Qt.QApplication.quit()        
    
    @staticmethod
    def exitThreads():
        print('In AlarmGUI.exitThreads()')
        # Unsubscribing all event sources
        # @TODO SEEMS NOT NEEDED (not at least for QAlarmPanel)
        import fandango.threads
        import fandango.callbacks
        [s.unsubscribeEvents() for s 
            in fandango.callbacks.EventSource.get_thread().sources]
        fandango.threads.ThreadedObject.kill_all()
        
    ##########################################################################
    
    def printRows(self):
        for row in self._ui.listWidget.selectedItems():
          print row.__repr__()
    
    def saveToFile(self):
        filename = str(Qt.QFileDialog.getSaveFileName(
            self.mainwindow,'File to save','.','*.csv'))
        self.api.export_to_csv(filename,alarms=self.getCurrents())
        return filename
        
    def loadFromFile(self,default='*.csv',ask=True):
        try:
            errors = []
            if ask or '*' in default:
                if '/' in default: d,f = default.rsplit('/',1)
                else: d,f = '.',default
                filename = Qt.QFileDialog.getOpenFileName(self.mainwindow,
                                                          'Import file',d,f)
            else:
                filename = default
            if filename:
                if not self.validate('LoadFromFile(%s)'%filename): return
                alarms = self.api.load_from_csv(filename,write=False)
                selected = AlarmsSelector(sorted(alarms.keys()),
                                          text='Choose alarms to import')
                devs = set()
                for tag in selected:
                    v = alarms[tag]
                    if v['device'] not in self.api.devices: 
                        errors.append('%s does not exist!!!'%v['device'])
                    else:
                        devs.add(v['device'])
                        if tag not in self.api: self.api.add(**v)
                        else: self.api.modify(**v)
                [self.api.devices[d].init() for d in devs]
            if errors: 
                Qt.QMessageBox.warning(self.mainwindow,'Error',
                                       '\n'.join(errors),Qt.QMessageBox.Ok)
            return filename
        except:
            import traceback
            Qt.QMessageBox.warning(self.mainwindow,'Error',
                                   traceback.format_exc(),Qt.QMessageBox.Ok)
            
    def editFile(self):
        filename = self.saveToFile()
        editor,ok = Qt.QInputDialog.getText(self.mainwindow,
                    'Choose your editor',"Type your editor choice, "
                    "you'll have to call 'Import CSV' after editing",
                    Qt.QLineEdit.Normal,'oocalc %s'%filename)
        if ok:
            os.system('%s &'%str(editor))
            v = Qt.QMessageBox.warning(None,'Load from file', \
                    '%s file may have been modified, '
                    'do you want to load your changes?'%filename, \
                    Qt.QMessageBox.Yes|Qt.QMessageBox.No);
            if v == Qt.QMessageBox.Yes:
                self.loadFromFile(filename,ask=False)
            return filename
            
    def setWindowMenu(self,action=None):
        print 'In AlarmGUI.setWindowMenu(%s)'%action
        self.mainwindow.windowMenu.clear()
        windows = WindowManager.getWindowsNames()
        for w in windows:
            if w and WindowManager.getWindow(w).isVisible():
                self.mainwindow.windowMenu.addAction(w,
                    lambda x=w:WindowManager.putOnTop(x))
        self.mainwindow.windowMenu.addAction('Close All',
                            lambda : WindowManager.closeAll())
        return
        
    def setExpertView(self,check=None):
        if check is None: check = self._ui.actionExpert.isChecked()
        self.expert = check
        self._ui.newButton.setEnabled(self.expert) #show()
        self._ui.deleteButton.setEnabled(self.expert) #show()
        self.expert = check
        return
    
    ###########################################################################
    
def main(args):
    AlarmGUI.main(args)
  
if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

try:
    from fandango.doc import get_fn_autodoc
    __doc__ = get_fn_autodoc(__name__,vars())
except:
    #import traceback
    #traceback.print_exc()
    pass

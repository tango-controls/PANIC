#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
##
## This file is part of Tango Control System
##
## http://www.tango-controls.org/
##
## Author: Sergi Rubio Manrique
##
## This is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This software is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
###########################################################################

__doc__ = "panic.view will contain the AlarmView class for managing"\
          "updated views of the panic system state"

import fandango as fn
import panic
from panic import *
from fandango.functional import *
from fandango.threads import ThreadedObject
from fandango.callbacks import EventSource, EventListener
from fandango.excepts import Catched
from fandango.objects import Cached,Struct
from fandango.log import Logger
from fandango.dicts import SortedDict

class FilterStack(SortedDict):
    """
    It is an ordered dictionary of filters
    Filters are applied sequentially
    Each filter has a tag and contains an string or dictionary of key/regexp
    String will be like "key:regexp,key:regexp,key:regexp"
    Regexp uses the fandango Careless extended syntax ('!\ &')
    """
    def add(self,name,s):
        self[name] = str2dict(s)
        
    def match(self,value,strict=False,trace=False):
        is_map = isMapping(value)
        m = None
        f = searchCl if not strict else matchCl
        for k,v in self.items():
            for p,r in v.items():
                t = value.get(p,'') if is_map else getattr(value,p,'')
                m = f(r,t,extend=True)
                if not m: 
                    if trace: print('%s doesnt match %s'%(t,r))
                    return m
        return m
        
    def apply(self,sequence,strict=False):
        return filter(partial(self.match,strict=strict),sequence)
    

class AlarmView(EventListener,Logger):
    #ThreadedObject,
  
    def __init__(self,name='AlarmView',filters={}):

        Logger.__init__(self,name)
        self.setLogLevel('INFO')
        #ThreadedObject.__init__(self,period=1.,nthreads=1,start=True,min_wait=1e-5,first=0)
        EventListener.__init__(self,name)

        if isString(filters):
            if ',' in filters: filters = filters.split(',')
            else: filters = {'regexp':filters}

        if isSequence(filters):
            filters = dict(iif('=' in k,k.split('=',1),(k,True)) 
                        for k in filters)

        # These can be modified using apply_filters
        self.filters = filters
        ## default_filters should never change
        self.defaults = Struct(dict((k,'') for k in 
              ('device','active','severity','regexp','receivers',
               'formula','attribute','history','failed','hierarchy')))
        self.defaults.update(**self.filters)
        
        self.info('AlarmView(%s)'%self.filters)
                
        self.ordered=[] #Alarms list ordered
        self.filtered = []
        self.sources = {} #Dictionary for Alarm sources
        
        self.timeSortingEnabled=None
        self.changed = True
        
        self.api = panic.AlarmAPI()
        if not self.api.keys(): 
            self.warning('NO ALARMS FOUND IN DATABASE!?!?')
            
        self.model = self.api.filter_alarms(filters=self.defaults)
        
        #self.default_regEx=options.get('filter',None) or filters or None
        #self.regEx = self.default_regEx
        #if self.regEx and str(self.regEx)!=os.getenv('PANIC_DEFAULT'): 
            #print 'Setting RegExp filter: %s'%self.regEx
            #self._ui.regExLine.setText(str(self.regEx))
        #self.severities=['alarm', 'error', 'warning', 'debug', '']
        #self.snapi = None
        #self.ctx_names = []

            
        #AlarmRow.TAG_SIZE = 1+max([len(k) for k in self.api] or [40])
        N = len(self.getAlarms())
        if len(self.model)<150: 
            self.REFRESH_TIME = 3000
        else:
            self.REFRESH_TIME = 6000

        if N<=self.MAX_ALARMS: self.USE_EVENT_REFRESH = True
        
        
        self.modelsQueue = Queue.Queue()
        self.modelsThread = fandango.qt.TauEmitterThread(parent=self,queue=self.modelsQueue,method=self.setAlarmRowModel)
        self.modelsThread.start()
        #TIMERS (to reload database and refresh alarm list).
        self.reloadTimer = QtCore.QTimer()
        self.refreshTimer = QtCore.QTimer()
        QtCore.QObject.connect(self.refreshTimer, QtCore.SIGNAL("timeout()"), self.onRefresh)
        QtCore.QObject.connect(self.reloadTimer, QtCore.SIGNAL("timeout()"), self.onReload)
        self.reloadTimer.start(self.REFRESH_TIME/2.)
        self.refreshTimer.start(self.REFRESH_TIME)
          
    def apply_filters(self,**filters):
        """
        valid filters are:
        * device
        * active
        * severity
        * regexp (any place)
        * receiver
        * formula
        * attributes
        * has_history
        * failed
        * hierarchy top
        * hierarchy bottom
        """
        self.filters = filters or self.filters
        return self.filtered
    
    def sort(self,*keys):
        """
        valid keys are:
        * name
        * device
        * active (time desc)
        * severity
        * receivers
        * hierarchy
        * failed
        """
        self.last_keys = keys or self.last_keys
        return self.ordered
    
    def export(self,to_type=list):
        if to_type==list:
            return self.ordered
      
    
    ###########################################################################
            
    def getAlarms(self):
        #It returns a list with all alarm objects matching the filter provided at startup
        return self.api.filter_alarms(self.filters)
    
    def getCurrents(self):
        return self._ordered
        
    def saveToFile(self):
        filename = str(QtGui.QFileDialog.getSaveFileName(self.mainwindow,'File to save','.','*.csv'))
        self.api.export_to_csv(filename,alarms=self.getCurrents())
        return filename
      
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
        
    def printRows(self):
        for row in self._ui.listWidget.selectedItems():
          print row.__repr__()
        
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
                if not self.snapi: 
                  self.snapi = get_snap_api()
                if self.snapi:
                  self.ctx_names = [c.name for c in self.snapi.get_contexts().values()]
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
                    try:
                        model = AttributeNameValidator().getUriGroups(row.getModel())
                        olddev = model['devname'] if model else None
                    except:
                        #Taurus 3
                        #traceback.print_exc()
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
    
    def event_hook(self, src, type_, value):
        """ 
        EventListener.eventReceived will jump to this method
        Method to implement the event notification
        Source will be an object, type a PyTango EventType, evt_value an AttrValue
        """
        src = src.full_name
        value = getAttrValue(value,True)
   
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
import fandango.tango as ft
import panic
from panic import *
from fandango.functional import *
from fandango.tango import parse_tango_model
from fandango.threads import ThreadedObject,Lock,RLock
from fandango.callbacks import EventSource, EventListener, TangoAttribute
from fandango.excepts import Catched
from fandango.objects import Cached,Struct
from fandango.log import Logger
from fandango.dicts import SortedDict,CaselessDict, \
        CaselessSortedDict, CaselessDefaultDict


import fandango.callbacks
fandango.callbacks.EventThread.EVENT_POLLING_RATIO = 1000
ft.check_device_cached.expire = 60.

class FilterStack(SortedDict):
    """
    It is an ordered dictionary of filters
    Filters are applied sequentially
    Each filter has a tag and contains an string or dictionary 
    of key/regexp
    String will be like "key:regexp,key:regexp,key:regexp"
    Regexp uses the fandango Careless extended syntax ('!\ &')
    """
    def __init__(self,filters=None):
        SortedDict.__init__(self)
        if filters:
            print filters
            if isSequence(filters): #It doesn't matter which types
                [self.add(str(i),f) for i,f in enumerate(filters)]
                
            elif isMapping(filters) and isMapping(filters.values()[0]):
                    [self.add(k,v) for k,v in filters.items()]
            
            else:
                self.add('default',filters)
        pass
      
    def add(self,name,s):
        self[name] = str2dict(s) if not isMapping(s) else s
        
    def match(self,value,strict=False,trace=False):
        is_map = isMapping(value)
        m = None
        f = searchCl if not strict else matchCl
        for k,v in self.items():
            if trace: print('apply((%s,%s),%s)'%(k,v,value))
            for p,r in v.items():
                t = value.get(p,'') if is_map else getattr(value,p,'')
                m = f(str(r),str(t),extend=True) if r else True
                if not m: 
                    if trace: print('%s doesnt match %s'%(t,r))
                    return m
        return m
        
    def apply(self,sequence,strict=False,trace=False):
        return filter(partial(self.match,strict=strict,trace=trace),sequence)
    

class AlarmView(EventListener,Logger):
    #ThreadedObject,
    
    sources = CaselessDict() #Dictionary for Alarm sources    
    
    ALARM_FORMATTERS = {
        'tag' : lambda s,l=10: ('{0:<%d}'%(l or 4)).format(s),
        #'time' : lambda s,l=25: ('{:^%d}'%l).format(s),
        'device' : lambda s,l=25: ('{0:^%d}'%(l or 4)).format(s),

        'description' : lambda s,l=50: ('{0:<}').format(s),

        'severity' : lambda s,l=10: ('{0:^%d}'%(l or 4)).format(s),

        'active' : lambda s,l=30: (('{0:^%d}'%(l or 4)).format(
          'FAILED!' if s is None else (
            'Not Active' if not s else (
              s if s in (1,True) else (
                time2str(s)))))),
              
        'formula' : lambda s,l=100: ('{0:^%d}'%(l or 4)).format(s),
        #'tag' : lambda s,l: ('{:^%d}'%l).format(s),
        }
  
    def __init__(self,name='AlarmView',filters={},domain='*',api=None,
                 refresh=3.,asynch=False,verbose=False):

        self.t_init = now()
        self.lock = Lock()
        self.verbose = verbose
        Logger.__init__(self,name)
        self.setLogLevel('INFO')
        
        if isString(filters): filters = {'tag':filters}
        self.filters = FilterStack(filters)
        #if isString(filters):
            #if ',' in filters: filters = filters.split(',')
            #else: filters = {'regexp':filters}

        #if isSequence(filters):
            #filters = dict(iif('=' in k,k.split('=',1),(k,True)) 
                        #for k in filters)

        ## default_filters should never change
        self.defaults = Struct(dict((k,'') for k in 
              ('device','active','severity','regexp','receivers',
               'formula','attribute','history','failed','hierarchy')))
        [self.defaults.update(**f) for f in self.filters.values()]
        self.filters.insert(0,'default',self.defaults.dict())
        
        self.info('AlarmView(%s)'%self.filters)
                
        self.ordered=[] #Alarms list ordered
        self.last_sort = 0
        self.filtered = [] # vs alarms?
        self.values = CaselessDefaultDict(dict)
        
        self.timeSortingEnabled=None
        self.changed = True
        #self.changes = CaselessDefaultDict(int)
        self.info('parent init done, +%s'%(now()-self.t_init))
        self.api = api or panic.AlarmAPI(filters=domain)
        if not self.api.keys():
            self.warning('NO ALARMS FOUND IN DATABASE!?!?')
        self.apply_filters()
        self.info('api init done, +%s'%(now()-self.t_init))
        
        #self.default_regEx=options.get('filter',None) or filters or None
        #self.regEx = self.default_regEx
        #if self.regEx and str(self.regEx)!=os.getenv('PANIC_DEFAULT'): 
            #print 'Setting RegExp filter: %s'%self.regEx
            #self._ui.regExLine.setText(str(self.regEx))
        #self.severities=['alarm', 'error', 'warning', 'debug', '']
        #self.snapi = None
        #self.ctx_names = []

            
        #AlarmRow.TAG_SIZE = 1+max([len(k) for k in self.api] or [40])
        N = len(self.alarms)
        
        ## How often should the ordered list be renewed?
        if len(self.alarms)>150: 
            refresh = max((6.,refresh))
            self.warning('%s alarms on display, polling set to %s'%(
                len(self.alarms),refresh))
        
        self.__asynch = asynch #Unmodifiable once started
        self.__refresh = refresh #Unmodifiable once started?
        self.get_period = lambda s=self: refresh
        #ThreadedObject.__init__(self,target=self.sort,
                                #period=refresh,start=False)
        #ThreadedObject.__init__(self,period=1.,nthreads=1,start=True,min_wait=1e-5,first=0)
        
        EventListener.__init__(self,name)
        self.setLogLevel('INFO')
        
        self.update_sources()
        self.info('event sources updated, +%s'%(now()-self.t_init))
        
        ######################################################################

        #self.start()
        self.info('view init done, +%s'%(now()-self.t_init))
        
    def __del__(self):
        print('AlarmView(%s).__del__()'%self.name)
        self.disconnect()
        
    def get_alarm(self,alarm):
        #self.info('get_alarm(%s)'%alarm)
        alarm = alarm.split('tango://')[-1]
        if alarm in self.api:
            return self.api[alarm]
        a = self.alarms.get(alarm,None)
        if not a:
            m = self.api.get(alarm.split('/')[-1])
            assert len(m)<=1, '%s_MultipleAlarmMatches!'%m
            assert m, '%s_AlarmNotFound!'%m
            a = m[0]
        return a
        
    def get_alarms(self, filters = None):
        """
        It returns a list with all alarm objects matching 
        the filter provided
        Alarms should be returned matching the current sortkey.
        """
        if not self.filtered and not filters:
            r = self.filtered
        else:
            #r = [a.tag for a in #self.api.filter_alarms(filters or self.filters)]
            filters = FilterStack(filters) if filters else self.filters
            r = [a.tag for a in filters.apply(self.api.values())]
        self.info('get_alarms(%s): %d alarms found'%(filters,len(r)))
        return r
      
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
        try:
            #self.lock.acquire()
            filters = FilterStack(filters) if filters else self.filters
            self.info('apply_filters(%s)'%filters)
            self.filtered = self.get_alarms(filters)
            self.filters = filters
            objs = [self.api[f] for f in self.filtered]
            models  = [(a.get_model().split('tango://')[-1],a) for a in objs]
            self.alarms = self.models = CaselessDict(models)
            return self.filtered
        except:
            self.error(traceback.format_exc())
        finally:
            #self.lock.release()
            pass
      
    @staticmethod
    def sortkey(alarm,priority=('Active','Severity')):
        result = []
        for p in priority:
            p = str(p).lower()
            #if p=='active': 
            if hasattr(alarm,p): result.append(getattr(alarm,p))
            if p=='active':
                ## TODO!!! DISABLED SHOULD BE APPLIED HERE AS -2
                result[-1] = alarm.active #get_active()

            if p=='severity':
                if result[-1]=='ERROR': result[-1] = 0
                if result[-1]=='ALARM': result[-1] = 1
                if result[-1]=='WARNING': result[-1] = 2
                if result[-1]=='DEBUG': result[-1] = 3
                
        return result
    
    def sort(self,sortkey = None):
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
        try:
            updated = [a for a in self.alarms.values() if a.updated]
            if len(updated) == len(self.alarms):
                [a.get_active() for a in self.alarms.values() 
                    if a.active in (1,True)]
            else:
                self.info('sort(): %d alarms not updated yet'%(
                  len(self.alarms)-len(updated)))
                
            #self.lock.acquire()
            if not self.ordered or (now()-self.last_sort) > self.get_period():
                #self.last_keys = keys or self.last_keys
                sortkey = sortkey or self.sortkey
                self.ordered = sorted(self.alarms.values(),key=sortkey)
                
            r = list(reversed([a.get_model() for a in self.ordered]))
            self.last_sort = now()
            return r
        except:
            self.error(traceback.format_exc())
        finally:
            #self.lock.release()
            pass
    
    def export(self,keys=('active','severity','device',
                          'tag','description','formula'),to_type=list):
        objs = [self.alarms[a] for a in self.sort()]
        if to_type is list:
            return [[getattr(o,k) for k in keys] for o in objs]
        if to_type is str or isString(to_type):
            to_type = str
            sep = to_type if isString(to_type) else '\t'
            return ['\t'.join(to_type(getattr(o,k)) for k in keys)
                    for o in objs]
          
    def get_alarm_as_text(self,alarm=None,cols=None,
                          formatters=None,lengths=[],sep=' - '):
        alarm = self.get_alarm(alarm)
        cols = cols or ['tag','active','description']
        formatters = formatters or self.ALARM_FORMATTERS
        s = '  '
        try:
            for i,r in enumerate(cols):
                if s.strip(): s+=sep
                args = [getattr(alarm,r)]
                if lengths: args.append(lengths[i])
                s += formatters[r](*args)
            return s
        except:
            print traceback.format_exc()
            return s
          
    def get_alarm_from_text(self,text,cols=None,
                            formatters=None,lengths=[],sep=' - ',obj=True):
        if hasattr(text,'text'): text = text.text()
        cols = cols or ['tag','active','description']
        vals = [t.strip() for t in str(text).split(sep)]
        i = cols.index('tag') if 'tag' in cols else 0
        return vals[i]
    
    
    def get_source(self,alarm):
        try:alarm = self.get_model(alarm)
        except:pass
        
        if alarm not in AlarmView.sources:
            alarm = alarm.replace('tango://','')
            if '/' not in alarm: alarm = '/'+alarm
            match = [s for s in AlarmView.sources if s.endswith(alarm)]
            assert len(match)<2, '%s_MultipleAlarmMatches'%alarm
            if not match:
                #self.debug('No alarm ends with %s'%alarm)
                return None
            alarm = match[0]
          
        return AlarmView.sources[alarm]
      
    def get_value(self,alarm):
        alarm = self.get_model(alarm)
        value = self.values.get(alarm,None)
        if value is None:
            try:
                alarm = self.get_source(alarm).full_name
                value = self.values.get(alarm,None)
            except Exception,e:
                self.warning('get_model(%s): %s'%(alarm,e))
        return value
      
    def get_model(self,alarm):
        alarm = getattr(alarm,'tag',str(alarm))
        try:
            if '/' not in alarm:
                alarm = self.get_alarm(alarm).get_model()
            if ':' not in alarm:
                alarm = ft.get_tango_host()+'/'+alarm

        except Exception,e:
            self.warning('get_model(%s): %s'%(alarm,e))

        return str(alarm).lower()
      
    def get_sources(self):
        return [s for s,v in AlarmView.sources.items()
                if any(l() is self for l in v.listeners)]
      
    def update_sources(self):
        self.info('update_sources(%d)'%len(self.alarms))
        olds = self.get_sources()
        news = [self.get_model(s) for s in self.alarms]
        devs = set(parse_tango_model(s)['device'] for s in news)
        news = [self.api.devices[d].get_model()
                for d in devs] #discard single attributes

        for o in olds:
            if o not in news:
                self.remove_source(o)
                
        for s in news:
            if s not in olds:
                ta = self.add_source(s)

            d = self.api.get_device(parse_tango_model(s)['device'])
            if anyendswith(s,d.get_model()):
                d._actives = self.get_source(s)
        
        return news
      
    def add_source(self,alarm):
        s = self.get_source(alarm)
        if s:
            self.warning('%s already sourced as %s'%(alarm,s))
            return None
        else:
            alarm = self.get_model(alarm)
            self.debug('add_source(%s)'%alarm)
            ta = TangoAttribute(alarm,
                  log_level = 'INFO',
                  #asynchronous attr reading is faster than event subscribing
                  use_events=['CHANGE_EVENT'],
                  tango_asynch = self.__asynch,
                  enable_polling = 1e3*self.__refresh,
                  )
            ta.setLogLevel('WARNING')
            self.sources[ta.full_name] = ta
            self.sources[ta.full_name].addListener(self)
            return ta
            
    def disconnect(self,alarm=None):
        sources = self.sources if alarm is None else [self.get_source(alarm)]
        for s in sources:
            s.removeListener(self)
            if not s.hasListeners():
                AlarmView.sources.pop(s.full_name)
        return
          
    def error_hook(self,src,type_,value):
        pass
      
    def value_hook(self,src,type_,value):
        pass
        
    def event_hook(self, src, type_, value):
        """ 
        EventListener.eventReceived will jump to this method
        Method to implement the event notification
        Source will be an object, type a PyTango EventType, evt_value an AttrValue
        """
        array = {}
        try:
            rvalue = getAttrValue(value,None)
            error = getattr(value,'err',False) or rvalue is None
            self.debug('AlarmView(%s).event_hook(%s,%s,%s)'%(
              self.name,src,type_, rvalue))
            
            #self.lock.acquire()
            if src.simple_name in self.api.alarms:
                av = self.get_alarm(src.full_name)
                alarms = [av.tag]
            else:
                #if anyendswith(src.simple_name,dev.get_model()):
                dev = self.api.get_device(src.device)
                alarms = dev.alarms.keys()
                
            if not getattr(value,'err',False):
                r = rvalue[0] if rvalue else ''
                self.info('AlarmView(%s): rvalue = %s'%(self.name,str(r)))
                splitter = ';' if ';' in r else ':'
                array = dict((l.split(splitter)[0],l) for l in rvalue)
                
            assert len(alarms), 'EventUnprocessed!'
                
            for a in alarms:
              
                av = self.get_alarm(a)
                av.updated = now()

                if error:
                    rvalue = None
                else:
                    try:
                        row = array.get(av.tag,None)
                        av.set_state(row)
                        if not row: 
                            self.warning('%s Not found in %s'%(
                                av.tag,src.full_name))
                        rvalue = av.active
                    except:
                        self.warning(traceback.format_exc())
                        rvalue = None
                
                if av.get_model() not in self.values:
                    self.info('%s has no cache'%(av.get_model()))
                    self.values[av.get_model()] = None
                  
                prev = self.values[av.get_model()]
                last = rvalue

                if last != prev:
                    (self.info if self.verbose else self.debug)(
                      'event_hook(%s,%s): %s => %s'%(
                      av.tag,av.get_state(),prev,last))
                        
                self.values[av.get_model()] = rvalue
                    
        except:
            self.error('AlarmView(%s).event_hook(%s,%s,%s)'%(
              self.name,src,type_, shortstr(value)))
            self.error(traceback.format_exc())
            self.error(array)
        finally:
            #self.lock.release()
            pass
      
    
    ###########################################################################
    
    
#class QAlarmView(AlarmView):
            

    #def getCurrents(self):
        #return self._ordered
        
    #def saveToFile(self):
        #filename = str(QtGui.QFileDialog.getSaveFileName(self.mainwindow,'File to save','.','*.csv'))
        #self.api.export_to_csv(filename,alarms=self.getCurrents())
        #return filename
      
    #def setModel(self,model):
        ## THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        #try:
            #if model!= self.regEx:
                #print('AlarmGUI.setModel(%s)'%model)
                #self._ui.regExLine.setText(model or self.default_regEx)
                #self.onRegExUpdate()
        #except:
            #print traceback.format_exc()

    #def setAlarmRowModel(self,nr,obj,alarm,use_list):
        ##print '%d/%d rows, %d models' % (nr,len(self.AlarmRows),len(taurus.Factory().tango_attrs.keys()))
        #obj.setAlarmModel(alarm,use_list)
        #self.updateStatusLabel()
        
    #def connectAll(self):
        #trace('connecting')
        ##QtCore.QObject.connect(self.refreshTimer, QtCore.SIGNAL("timeout()"), self.onRefresh)
        #if self.USE_EVENT_REFRESH: QtCore.QObject.connect(self,QtCore.SIGNAL("valueChanged"),self.hurry)
        ##Qt.QObject.connect(self._ui.actionExpert,Qt.SIGNAL("changed()"),self.setExpertView)
        
    #def printRows(self):
        #for row in self._ui.listWidget.selectedItems():
          #print row.__repr__()
        
    #def removeAlarmRow(self,alarm_tag):
        ##Removing listeners to this alarm attribute
        #trace('In removeAlarmRow(%s)'%alarm_tag)
        #try:
            #row = self.AlarmRows.pop(alarm_tag)
            #ta = taurus.Attribute(row.getModel())
            #ta.removeListener(row)
            #row.setModel(None)
        #except:
            #trace('Unable to %s.removeListener():\n\t%s'%(alarm_tag,traceback.format_exc()))
    
    #def hurry(self):
        #"""
        #on ValueChanged event a refresh will be scheduled in 1 second time
        #(so all events received in a single second will be summarized)
        #"""
        #if not self.changed: 
            #trace('hurry(), changed = True')
            #self.changed = True
            #self.reloadTimer.setInterval(self.MAX_REFRESH*1000.)

    #@Catched
    #def onReload(self):
        ## THIS METHOD WILL NOT MODIFY THE LIST IF JUST FILTERS HAS CHANGED; TO UPDATE FILTERS USE onRefresh INSTEAD
        #try:
            #trace('onReload(%s)'%self.RELOAD_TIME)
            #print '+'*80
            #now = time.time()
            #trace('%s -> AlarmGUI.onReload() after %f seconds'%(now,now-self.last_reload))
            #self.last_reload=now
            #self.api.load()
            
            #if self.api.keys():
                #AlarmRow.TAG_SIZE = 1+max(len(k) for k in self.api.keys())
                
            ##Removing deleted/renamed alarms
            #for tag in self.AlarmRows.keys():
                #if tag not in self.api:
                    #self.removeAlarmRow(tag)
                    
            ##Updating the alarm list
            #self.buildList(changed=False)
            #if self.changed: self.showList()
            
            ##Triggering refresh timers
            #self.reloadTimer.setInterval(self.RELOAD_TIME)
            #self.refreshTimer.setInterval(self.REFRESH_TIME)

            #if not self._connected:
                #self._connected = True
                #self.connectAll()
        #except:
            #trace(traceback.format_exc())
    
    #@Catched
    #def onRefresh(self):
        #"""Just checks order, no reload, no filters"""
        #trace('onRefresh(%s)'%self.REFRESH_TIME)
        #self.buildList(changed=False)
        #if self.changed: self.showList()
        #self.refreshTimer.setInterval(self.REFRESH_TIME)
    
    #@Catched
    #def onFilter(self,*args):
        #"""Forces an update of alarm list order and applies filters (do not reload database)."""
        #trace('onFilter()')
        #self.buildList(changed=True)
        #self.showList()
        #self.refreshTimer.setInterval(self.REFRESH_TIME)

    #def onSevFilter(self):
        ## THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        #self.getSeverities()
        #self.onFilter()

    #def onRegExUpdate(self):
        ## THIS METHOD WILL CHECK FOR CHANGES IN FILTERS (not only severities)
        #self.regEx = str(self._ui.regExLine.text()).strip() or self.default_regEx
        #self._ui.activeCheckBox.setChecked(False)
        #self.onFilter()

    #@Catched
    #def regExFiltering(self, source):
        #alarms,regexp=[],str(self.regEx).lower().strip()
        #exclude = regexp.startswith('!')
        #if exclude: regexp = regexp.replace('!','').strip()
        #for a in source:
            #match = fandango.searchCl(regexp, a.receivers.lower()+' '+a.severity.lower()+' '+a.description.lower()+' '+a.tag.lower()+' '+a.formula.lower()+' '+a.device.lower())
            #if (exclude and not match) or (not exclude and match): alarms.append(a)
        #trace('\tregExFiltering(%d): %d alarms returned'%(len(source),len(alarms)))
        #return alarms
      
    #def setRowModels(self):
        #trace('AlarmGUI.setRowModels()')
        #for alarm in self.getAlarms():
            #self.AlarmRows[alarm.tag].setAlarmModel(alarm)
            
    #def setFirstCombo(self):
        #self.setComboBox(self._ui.contextComboBox,['Alarm','Time','Devices','Hierarchy','Receiver','Severity'],sort=False)

    #def setSecondCombo(self):
        #source = str(self._ui.contextComboBox.currentText())
        #trace("AlarmGUI.setSecondCombo(%s)"%source)
        #if source == self.source: return
        #else: self.source = source
        #self._ui.comboBoxx.clear()
        #self._ui.comboBoxx.show()
        #self._ui.infoLabel0_1.show()
        #self._ui.comboBoxx.setEnabled(True)
        #if source =='Devices':
            #r,sort,values = 1,True,sorted(set(a.device for a in self.getAlarms()))
        #elif source =='Receiver':
            ##r,sort,values = 2,True,list(set(a for a in self.api.phonebook.keys() for l in self.api.values() if a in l.receivers))
            #r,sort,values = 2,True,list(set(s for a in self.getAlarms() for s in ['SNAP','SMS']+[r.strip() for r in a.receivers.split(',')]))
        #elif source =='Severity':
            #r,sort,values = 3,False,['DEBUG', 'WARNING', 'ALARM', 'ERROR']
        #elif source =='Hierarchy':
            #r,sort,values = 4,False,['ALL', 'TOP', 'BOTTOM']
        #elif source =='Time':
            #r,sort,values = 5,False,['DESC', 'ASC']
        #else: #"Alarm Status"
            #r,sort,values = 0,False,['ALL', 'AVAILABLE', 'FAILED','HISTORY']
        #self.setComboBox(self._ui.comboBoxx,values=values,sort=sort)
        #return r      
      
    #def findListSource(self, dev=None):
        #combo1, combo2 = str(self._ui.contextComboBox.currentText()), str(self._ui.comboBoxx.currentText())
        ##print "findListSource(%s,%s), filtering ..."%(combo1,combo2)
        #self.timeSortingEnabled=None
        #self.source = combo1
        #alarms = self.getAlarms()
        #if self.source == "Devices":
            #self._alarmsList = self.api.get(device=combo2,alarms=alarms) if combo2 else []
        #elif self.source == 'Receiver':
            #self._alarmsList = self.api.get(receiver=combo2,alarms=alarms) if combo2 else []
        #elif self.source == 'Severity':
            #self._alarmsList = self.api.filter_severity(combo2,alarms=alarms)
        #elif self.source == 'Hierarchy':
            #self._alarmsList = self.api.filter_hierarchy(combo2,alarms=alarms)
        #elif self.source == 'Time':
            #self.timeSortingEnabled=combo2
        #else:
            #self._alarmsList = alarms

        #self.api.servers.states()
        #failed = [s.lower() for s in self.api.servers if self.api.servers[s].state is None]
        #if failed:
            #pass #trace('findListSource(%s,%s): %d servers are not running: %s'%(combo1, combo2,len(failed),failed))
        
        ##timeSorting Filter moved to showList() method
        ##self._alarmsList = [a for a in self._alarmsList if not self.timeSortingEnabled or self.api.servers.get_device_server(a.device).lower() not in failed]
        ##print '\tfiltering done, returning %d/%d alarms'%(len(self._alarmsList),len(self.api.alarms.keys()))
        #return self._alarmsList

    #def filterByState(self, source):
        #result=[]
        #stateFilter=self._ui.comboBoxx.currentText()
        #for a in source:
            #if stateFilter=='AVAILABLE':
                #if a.tag in self.AlarmRows and (str(self.AlarmRows[a.tag].quality) in ['ATTR_VALID', 'ATTR_ALARM', 'ATTR_CHANGING', 'ATTR_WARNING']): result.append(a)
            #elif stateFilter=='FAILED':
                #if a.tag not in self.AlarmRows or (str(self.AlarmRows[a.tag].quality) == 'ATTR_INVALID'): result.append(a)
            #elif stateFilter=='HISTORY':
                #if not self.snapi: 
                  #self.snapi = get_snap_api()
                #if self.snapi:
                  #self.ctx_names = [c.name for c in self.snapi.get_contexts().values()]
                  #if SNAP_ALLOWED and a.tag in self.ctx_names: result.append(a)
            #else:
                #result.append(a)
        #trace('filterByState(%d): %d alarms returned'%(len(source),len(result)))
        #return result

    #def alarmSorter(self,obj):
        #"""obj is a panic.Alarm object """
        ##Quality/Value should be managed by EventReceived, not read here!
        #quality = obj.get_quality()
        #if obj.tag in self.AlarmRows and self.AlarmRows[obj.tag].alarm is not None:
            #row =  self.AlarmRows[obj.tag]
            #if row.alarm.active!=obj.active:
                #print '>'*80
                #trace('ALARM API NOT UPDATED? : %s vs %s ' %(obj,row.alarm))
                #print '>'*80
            #acknowledged,disabled,active = row.alarmAcknowledged,row.alarmDisabled,row.alarm.active
            #if self.AlarmRows[obj.tag].quality == PyTango.AttrQuality.ATTR_INVALID: #It will update only INVALID ones, the rest will keep DB severity
                #quality = PyTango.AttrQuality.ATTR_INVALID
        #else: acknowledged,disabled,active,quality = False,False,False,PyTango.AttrQuality.ATTR_INVALID #Not updated will be invalid

        #ACT = 0 if disabled else (-2 if (acknowledged and active) else (-1 if obj.active else 1))

        #if self.timeSortingEnabled:
            ##Ordered by active first, then time ASC, then name
            #sorting = self._ui.comboBoxx.currentText()
            #date = self.AlarmRows[obj.tag].get_alarm_time()
            #return (-1*date if sorting=='DESC' else date, obj.tag)
        #else:
            ##Ordered by active first, then severity, then active time, then name
            #if quality==PyTango.AttrQuality.ATTR_ALARM:
                #return (ACT, 0, obj.active, obj.tag)
            #elif quality==PyTango.AttrQuality.ATTR_WARNING:
                #return (ACT, 1, obj.active, obj.tag)
            #elif quality==PyTango.AttrQuality.ATTR_VALID:
                #return (ACT, 2, obj.active, obj.tag)
            #elif quality==PyTango.AttrQuality.ATTR_INVALID:
                #return (ACT, 3, obj.active, obj.tag)

    #@Catched
    #def buildList(self,changed=False):
        #self._ui.listWidget.blockSignals(True)
        #self.changed = changed or self.changed
        #trace('buildList(%s)'%self.changed)
        ##print "%s -> AlarmGUI.buildList(%s)"%(time.ctime(), ['%s=%s'%(s,getattr(self,s,None)) for s in ('regEx','severities','timeSortingEnabled','changed',)])
        #try:
            #l = [a for a in self.findListSource() if a.severity.lower() in self.severities]
            #l = [getattr(self.AlarmRows.get(a.tag,None),'alarm',None) or a for a in l]
            #if (self.regEx!=None): 
                #trace('\tFiltering by regEx: %s'%self.regEx)
                #l=self.regExFiltering(l)
            #if str(self._ui.comboBoxx.currentText()) != 'ALL': 
                #l=self.filterByState(l)
            
            ##print '\tSorting %d alarms ...'%len(l)
            #qualities = dict((x,self.alarmSorter(x)) for x in l)
            #ordered = filter(bool,sorted(l,key=(lambda x: qualities[x])))
            #if len(ordered)!=len(self._ordered): 
                #print('Length of alarm list changed; changed = True')
                #self.changed = True
            ##print '\tAlarms in list are:\n'+'\n'.join(('\t\t%s;%s'%(x,qualities[x])) for x in ordered)
            
            ##Updating alarms from api
            #for nr, alarm in list(enumerate(ordered)):
                #if not self.changed and self._ordered[nr]!=alarm: 
                    #trace('\tRow %s moved; changed = True'%alarm.tag)
                    #self.changed = True
                #if alarm is None:
                    #trace('\tEmpty alarm found at %d'%nr)
                    #continue
                #if alarm.tag not in self.AlarmRows:
                    ##print '\t%s,%s,%s: Creating AlarmRow ...'%(alarm.tag,bool(alarm.active),alarm.get_quality())
                    #row = self.AlarmRows[alarm.tag] = AlarmRow(api=self.api,qtparent=self)
                    #trace('\tNew alarm: %s; changed = True'%alarm.tag)
                    #try: 
                        #self.modelsQueue.put((nr,row,alarm,(len(ordered)>self.MAX_ALARMS)))
                        ##self.AlarmRows[alarm.tag].setAlarmModel(alarm,use_list=(len(self.ordered)>MAX_ALARMS))
                        #self.changed = True
                    #except Exception,e: trace('===> AlarmRow.setModel(%s) FAILED!: %s' %(alarm.tag,e))
                #else:
                    #row = self.AlarmRows[alarm.tag]
                    #try:
                        #model = AttributeNameValidator().getUriGroups(row.getModel())
                        #olddev = model['devname'] if model else None
                    #except:
                        ##Taurus 3
                        ##traceback.print_exc()
                        #model = AttributeNameValidator().getParams(row.getModel())
                        #olddev = model['devicename'] if model else None
                    #if alarm.device != olddev:
                        #trace('\t%s device changed: %s => %s; changed = True'%(alarm.tag,alarm.device,olddev))
                        #self.modelsQueue.put((nr,row,alarm,(len(ordered)>self.MAX_ALARMS)))
                        #self.changed = True
            #if self.changed: self._ordered = ordered
            #if self.modelsQueue.qsize(): 
                #self.modelsThread.next()
        #except:
            #trace('AlarmGUI.buildList(): Failed!\n%s'%traceback.format_exc())
        ##if not self.changed: print '\tAlarm list not changed'
        #self._ui.listWidget.blockSignals(False)
        ##print '*'*80

    #@Catched
    #def showList(self):
        #"""
        #This method just redraws the list keeping the currently selected items
        #"""
        #trace('%s -> AlarmGUI.showList()'%time.ctime())
        ##self._ui.listWidget.blockSignals(True)
        #currents = self._ui.listWidget.selectedItems()
        #trace('\t\t%d items selected'%len(currents))
        #trace('\t\tremoving objects from the list ...')
        #while self._ui.listWidget.count():
            #delItem = self._ui.listWidget.takeItem(0)
            ##del delItem
        #trace('\t\tdisplaying the list ...')
        #ActiveCheck = self._ui.activeCheckBox.isChecked() or self.timeSortingEnabled
        #for alarm in self._ordered:
            #obj = self.AlarmRows[alarm.tag]
            #if not ActiveCheck or (obj.alarm and not obj.alarmAcknowledged and (obj.alarm.active or (not self.timeSortingEnabled and str(obj.quality) == 'ATTR_INVALID'))):
                #self._ui.listWidget.addItem(obj)
            #obj.updateIfChanged()
        #try:
            ##THIS SHOULD BE DONE EMITTING A SIGNAL!
            #if currents is not None and len(currents):
                #self._ui.listWidget.setCurrentItem(currents[0])
                #for current in currents:
                    #trace('\t\tselecting %s item'%current.tag)
                    ##self._ui.listWidget.setCurrentItem(current)
                    #current.setSelected(True)
                ##if self.expert: self.setAlarmData(current) #Not necessary
        #except:
            #print traceback.format_exc()
        #self.changed = False
        #trace('\t\tshowList(): %d alarms added to listWidget.'%self._ui.listWidget.count())
        #self.updateStatusLabel()
        ##self._ui.listWidget.blockSignals(False)      
    

   

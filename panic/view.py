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

import fandango as fd
import fandango.tango as ft

from fandango.functional import *
from fandango.tango import parse_tango_model, check_device_cached, \
        get_device_info
from fandango.threads import ThreadedObject,Lock,RLock
from fandango.callbacks import EventSource, EventListener, TangoAttribute
from fandango.excepts import Catched
from fandango.objects import Cached,Struct
from fandango.log import Logger
from fandango.dicts import SortedDict,CaselessDict, \
        CaselessSortedDict, CaselessDefaultDict

import fandango.callbacks

import panic

from .alarmapi import *
from .properties import *

def check_multi_host(model,host=None,raise_=False):
    """ returns True if tango_host in model does not match host """
    h0 = (host or fandango.get_tango_host().split(':')[0]).split('.')[0]
    h1 = parse_tango_model(model).host.split('.')[0] 
    r = h0.lower()!= h1.lower()
    assert not r or not raise_,'%s!=%s'%(h1,h0)
    return r

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
            if isSequence(filters): #It doesn't matter which types
                [self.add(str(i),f) for i,f in enumerate(filters)]
                
            elif isMapping(filters) and isMapping(filters.values()[0]):
                    [self.add(k,v) for k,v in filters.items()]
            
            else:
                self.add('default',filters)
        pass
      
    def add(self,name,s):
        self[name] = str2dict(s) if not isMapping(s) else s
        
    def match(self,value,strict=False,verbose=False):
        is_map = isMapping(value)
        m,gm = None,None
        f = searchCl if not strict else matchCl
        # Several keys at same level acts like OR
        # Keys at different levet act like AND
        # An !exclude clause always aborts
        for k,v in self.items():
            if verbose: print('match((%s,%s),%s)'%(k,v,value))
            hits = 0

            for p,r in v.items():
                #get the parameter
                t = value.get(p,'') if is_map else getattr(value,p,'')
                #get the result of the matching method (~! will negate)
                if isString(r):
                    m = f(str(r),str(t),extend=True) if r else True
                elif r in (True,False):
                    m = (r == bool(t))
                else:
                    m = (r == t)

                if m:
                    hits,gm = hits+1,m
                elif fd.re.match('^[!~]',str(r)):
                    #Negated matches exclude the whole element
                    if verbose: print('%s excluded by %s'%(t,r))
                    return False

            if not hits: 
                #print('%s not matched by %s'%(value,v))
                return 0

        return gm if hits else None
        
    def apply(self,sequence,strict=False,verbose=False):
        r = filter(partial(self.match,strict=strict,verbose=verbose),sequence)
        if verbose:
            print('FilterStack.apply(%s,%s): \n\t%s'%(sequence,self.items(),r))        
        return r
      
    def __repr__(self):
        dct = {}
        for k,v in self.items():
            for kk,vv in v.items():
                if vv:
                    dct[k] = dct.get(k,{})
                    dct[k][kk] = vv
        return fd.log.pformat(dct)
    

class AlarmView(EventListener):
    #ThreadedObject,
    
    _LOADED = False
    
    sources = CaselessDict() #Dictionary for Alarm sources    
    

  
    def __init__(self,name='AlarmView',filters={},scope='*',api=None,
                 refresh=3.,events=False,asynch=False,verbose=False):

        self.t_init = now()
        self.lock = Lock()
        self.verbose = verbose if not isNumber(verbose) else (
            {verbose>3:'DEBUG',4>verbose>1:'INFO',verbose<=1:'WARNING'}[True])

        if not AlarmView._LOADED:
            import panic.engine
            panic.engine.init_callbacks()
            AlarmView._LOADED = True
            
        EventListener.__init__(self,name)

        self.setLogLevel(self.verbose or 'WARNING')
        
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
        
        self.info('AlarmView(%s)'%str((filters,scope,refresh,asynch)))
                
        self.ordered=[] #Alarms list ordered
        self.last_sort = 0
        self.filtered = [] # vs alarms?
        self.values = CaselessDefaultDict(dict)
        
        self.timeSortingEnabled=None
        self.changed = True
        #self.info('parent init done, +%s'%(now()-self.t_init))
        
        if not isSequence(scope): scope = [scope]
        if api: 
            self.apis = {scope[0]:api}
        else:
            self.apis = dict()
            for p in scope:
                if not p.split('#')[0]: continue
                k = p.split('@')
                t = first(k[1:] or (None,))
                s = k[0] if ('/' in k[0] or isRegexp(k[0])) else '*%s*'%k[0]
                try:
                    self.info('creating AlarmAPI(%s,%s)'%(s,t))
                    self.apis[p] = panic.AlarmAPI(filters=s,tango_host=t)
                except:
                    traceback.print_exc()
                    self.apis[p] = None
                
        #@TODO: MULTIPLE APIS OBJECTS SHOULD BE MANAGED!!
        self.api = self.apis.values()[0]
        
        if not self.api.keys():
            self.warning('NO ALARMS FOUND IN DATABASE!?!?')


        self.apply_filters()
        self.info('view api init done, +%s'%(now()-self.t_init))
        self.info('%d sources : %s ...'
                  %(len(self.alarms),fd.log.pformat(self.alarms)[:80]))
        
        N = len(self.alarms)
        
        ## How often should the ordered list be renewed?
        if len(self.alarms)>150: 
            refresh = max((6.,refresh))
            self.warning('%s alarms on display, polling set to %s'%(
                len(self.alarms),refresh))
        
        self.__asynch = asynch #Unmodifiable once started
        self.__events = events or False #Unmodifiable once started
        self.__refresh = refresh #Unmodifiable once started?
        self.__dead = 0 #deadtime caused by event hooks
        self.get_period = lambda s=self: refresh
        #ThreadedObject.__init__(self,target=self.sort,
                                #period=refresh,start=False)
        #ThreadedObject.__init__(self,period=1.,nthreads=1,start=True,min_wait=1e-5,first=0)
        
        self.update_sources()
        self.info('event sources updated, +%s'%(now()-self.t_init))
        
        ######################################################################

        #self.start()
        self.info('view init done, +%s'%(now()-self.t_init))
        self.logPrint('info','\n\n')
        
    def __del__(self):
        print('AlarmView(%s).__del__()'%self.name)
        self.disconnect()
        
    @staticmethod
    def __test__(*args):
        t0 = fd.now()
        args = args or ['*value*','20']
        opts = dict.fromkeys(a.strip('-') for a in args if a.startswith('-'))
        args = [a for a in args if a not in opts]
        scope = args[0]
        tlimit = int((args[1:] or ['20'])[0])
        
        if opts:
            opts = dict(o.split('=') if '=' in o else (o,True) 
                        for o in opts)
            opts.update((o,fd.str2type(v)) for o,v in opts.items())
        
        print('AlarmView(Test,\t'
            '\tscope=%s,\n\ttlimit=%s,\n\t**%s)\n'%(scope,tlimit,opts))
        
        if opts.get('d',False):
            th = TangoAttribute.get_thread()
            th.set_period_ms(500)
            th.setLogLevel('DEBUG')     
            
        verbose = opts.get('v',2)
        
        view = AlarmView('Test',scope=scope,
                         verbose=verbose,
                         **opts)
        print('\n'.join('>'*80 for i in range(4)))    
        
        cols = 'sortkey','tag','state','active','time','severity'
        while fd.now()<(t0+tlimit):
            fd.wait(3.)
            print('\n'+'<'*80)
            l = view.sort(as_text={'cols':cols})
            print('\n'.join(l))
            
        print('AlarmView.__test__(%s) finished after %d seconds'
              %(args[0],fd.now()-t0))
        
    def get_alarm(self,alarm):
        #self.info('get_alarm(%s)'%alarm)
        alarm = getattr(alarm,'tag',alarm)
        alarm = alarm.split('tango://')[-1]
        if not alarm: return None
        a = self.alarms.get(alarm,None)
        if a is None:
            alarm = alarm.split('/')[-1]
            #@KEEP, do not remove this first check
            if alarm in self.api:
                return self.api[alarm]
            else:
                m = self.api.get(alarm)
                assert len(m)<=1, str('%s_MultipleAlarmMatches!'%str(m))
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
            r = self.api.keys()[:]
        else:
            if filters:
                self.apply_filters(self,**filters)        
            r = self.filtered

        self.debug('get_alarms(%s): %d alarms found'%(repr(filters),len(r)))
        return r
      
    def apply_filters(self,*args,**filters):
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
            self.ordered = []
            self.filtered = []
            self.last_sort = 0
            filters = filters or (args and args[0])
            if filters and not isinstance(filters,FilterStack):
                filters = FilterStack(filters)
            else:
                filters = filters or self.filters
                
            self.debug('apply_filters(%s)'%repr(filters))
            self.filtered = [a.tag for a in 
                             filters.apply(self.api.values(),verbose=0)]
            self.filters = filters
            
            objs = [self.api[f] for f in self.filtered]
            models  = [(a.get_model().split('tango://')[-1],a) for a in objs]
            self.alarms = self.models = CaselessDict(models)
            self.info('apply_filters: %d -> %d\n'
                      %(len(self.api),len(self.filtered)))
        except:
            self.error(traceback.format_exc())
        finally:
            pass #self.lock.release()

        return self.filtered
      
    @staticmethod
    def sortkey(alarm,priority=None):
        """
        Return alarms ordered from LEAST critical to MOST
        
        This is the REVERSE order of that shown in the GUI
        """
        r = []
        priority = priority or SORT_ORDER
        #print priority
        for p in priority:
            m,p = None,str(p).lower()

            if p == 'error':
                v = alarm.get_state() in ('ERROR',)            
            elif p == 'active':
                v = alarm.is_active()
            else:
                if p in ('time','state'):
                    m = getattr(alarm,'get_'+p,None)

                v = m() if m else getattr(alarm,p,None)
                    
                if p in ('severity','priority'):
                    v = panic.SEVERITIES.get(str(v).upper(),'UNKNOWN')
                
            r.append(v)
        
        setattr(alarm,'sortkey',str(r))
        return r
    
    def sort(self,sortkey = None, as_text=False, filtered=True, keep=True):
        """
        Returns a sorted list of alarm models
        
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
                
            self.debug('%d alarms, %d filtered, %d updated'
                       %tuple(map(len,(self.alarms,updated,self.filtered))))
                
            #self.lock.acquire()
            ordered = self.ordered
            if not keep or not ordered \
                    or (now()-self.last_sort) > self.get_period():
                #self.last_keys = keys or self.last_keys
                sortkey = sortkey or self.sortkey
                if isSequence(sortkey): 
                    sortkey = lambda a,p=sortkey:self.sortkey(a,priority=p)
                if filtered:
                    objs = [self.api[f] for f in self.filtered]
                else:
                    objs = self.alarms.values()

                ordered = sorted(objs,key=sortkey)
                if keep: self.ordered = ordered
                self.debug('sort([%d])'%(len(ordered)))
                
            if as_text:
                kw = fd.isMapping(as_text) and as_text or {}
                r = list(reversed([self.get_alarm_as_text(a,**kw) 
                                   for a in ordered]))
            else:
                r = list(reversed([a.get_model() for a in ordered]))

            self.last_sort = now()
            return r
        except:
            self.error(traceback.format_exc())
        finally:
            #self.lock.release()
            pass
    
    def export(self,keys=('active','severity','device',
                          'tag','description','formula'),
                        to_type=list):
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
        cols = cols or VIEW_FIELDS
        formatters = formatters or FORMATTERS
        s = '  '
        try:
            for i,r in enumerate(cols):
                if s.strip(): s+=sep
                v = getattr(alarm,r)
                args = [v() if fd.isCallable(v) else v]
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
        a = vals[i]
        try:
            return self.get_alarm(a) if obj else a
        except Exception as e:
            print('get_alarm_from_text(%s): %s,%s'%(text,obj,a))
            traceback.print_exc()
    
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
        return dict((s,v) for s,v in AlarmView.sources.items()
                if any(l() is self for l in v.listeners))
      
    def update_sources(self):
        self.info('update_sources(%d)'%len(self.alarms))
        olds = self.get_sources()
        news = [self.get_model(s) for s in self.alarms]
        devs = set(parse_tango_model(s)['devicename'] for s in news)
        news = [self.api.devices[d].get_model()
                for d in devs] #discard single attributes

        for o in olds:
            if o not in news:
                self.remove_source(o)
                
        for s in news:
            if s not in olds:
                ta = self.add_source(s)

            d = self.api.get_device(parse_tango_model(s)['devicename'])
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
            events = self.__events and ['CHANGE_EVENT']
            self.debug('add_source(%s,events=%s)'%(alarm,events))
            ta = TangoAttribute(alarm,
                  log_level = self.getLogLevel(),
                  #asynchronous attr reading is faster than event subscribing
                  use_events=events,
                  tango_asynch = self.__asynch,
                  enable_polling = 1e3*self.__refresh,
                  )
            ta.setLogLevel(self.getLogLevel())
            self.sources[ta.full_name] = ta
            self.sources[ta.full_name].addListener(self,
                use_events=events, use_polling=not events)
            return ta
            
    def disconnect(self,alarm=None):
        sources = self.sources.values() if alarm is None else [self.get_source(alarm)]
        for s in sources:
            if s is not None:
                s.removeListener(self)
                if not s.hasListeners():
                    AlarmView.sources.pop(s.full_name)
        return
          
    def error_hook(self,src,type_,value):
        pass
      
    def value_hook(self,src,type_,value):
        pass
        
    def event_hook(self, src, type_, value, locked=False):
        """ 
        EventListener.eventReceived will jump to this method
        Method to implement the event notification
        Source will be an object, type a PyTango EventType, 
        evt_value an AttrValue
        """
        tt0 = now()
        tsets = 0
        array = {}
        try:
            # convert empty arrays to [] , pass exceptions
            rvalue = getAttrValue(value,Exception)
            error =  (getattr(value,'err',False) 
                or isinstance(rvalue,(type(None),Exception,PyTango.DevError)))
            
            self.info('event_hook(\n\tsrc=%s,\n\ttype=%s)'%(src,type_))
            ## eventReceived already log that
            error = error or check_multi_host(src.full_name,raise_=False)
            
            if locked is True: self.lock.acquire()
            if src.simple_name in self.api.alarms:
                av = self.get_alarm(src.full_name)
                alarms = [av.tag]
            else:
                m = parse_tango_model(src.device)
                d = m['devicename']
                dev = self.api.get_device(d)
                assert dev,('UnknownDevice:\n\n\t%s'%
                            '\n\n\t'.join("%s"%str(s) for s 
                            in (src.device,m,d,dev,self.api.devices.keys())))
                alarms = dev.alarms.keys()
                
            check =  check_device_cached(src.device)
            if check in (None,'UNKNOWN'): #'FAULT',
                error = 'AlarmView[%s] returned %s state'%(src.device,check)
                self.warning(error)
                
            if not error:
                #self.debug('rvalue = %s(%s)'%(type(rvalue),str(rvalue)))
                r = rvalue[0] if rvalue else ''
                splitter = ';' if ';' in r else ':'
                array = dict((l.split(splitter)[0].split('=')[-1],l) 
                             for l in rvalue)
                self.debug('%s.rvalue = %s'%(src,fd.log.pformat(array)))
            else:
                l = self.info #(self.info('ERROR','OOSRV') else self.info)
                #devup = get_device_info(src.device).exported
                devup = check_device_cached(src.device)

                s = ('OOSRV','ERROR')[bool(devup)]    
                if s=='ERROR': 
                    self.warning('%s seems hung!'%(src.device))
                l('event_hook(%s).Error(s=%s,%s): %s'%(src,s,devup,rvalue))                
                
            assert len(alarms), 'EventUnprocessed!'
                
            for a in alarms:
                av = self.get_alarm(a)
                #self.debug('event_hook() %s was %s since %s(%s)'
                            #%(a,av._state,av._time,
                              #time2str(av._time,us=True)))
                av.updated = now()

                if error:
                    #['CantConnectToDevice' in str(rvalue)]
                    s = ('OOSRV','ERROR')[bool(devup)]
                    av.set_state(s)
                    av.last_error = str(rvalue)

                elif isSequence(rvalue):
                    try:
                        EMPTY = ''
                        row = array.get(av.tag,EMPTY)
                        #self.debug('[%s]:\t"%s"'%(av.tag,row or EMPTY))
                        if not row: 
                            # Compatibility with PyAlarm < 6.2
                            if clsearch('activealarms',src.full_name):
                                row = 'NORM' if av.get_enabled() else 'SHLVD'
                            else:
                                self.warning('%s Not found in %s(%s)'%(
                                    av.tag,src.full_name,splitter))
                        ts0 = now()
                        #self.info('%s.set_state(%s)'%(a,row))
                        av.set_state(row)
                        tsets += now()-ts0
                        #if av.active:
                            #self.info('%s active since %s'
                              #%(av.tag,fd.time2str(av.active or 0)))
                    except:
                        error = traceback.format_exc()
                        av.last_error = error
                        av.set_state('ERROR')
                        self.warning(error)
                else:
                    # Not parsing an array value
                    av.set_active((rvalue and av.active) or rvalue)
                
                if av.get_model() not in self.values:
                    self.values[av.get_model()] = None
                    self.debug('%s cache initialized'%(av.get_model()))
                  
                prev = self.values[av.get_model()]
                curr = av.active if not error else -1

                if curr != prev:
                    self.debug(#(self.info if self.verbose else self.debug)(
                      'event_hook(%s,%s): %s => %s'%(
                      av.tag,av.get_state(),prev,curr))
                        
                self.values[av.get_model()] = curr
                
            tt,ts,ta = (1e3*t for t in (now()-tt0,tsets,tsets/len(alarms)))
            self.info('event_hook() done in %.2e ms '
                      '(%.2e in set_state, %.2e per alarm)\n'
                       %(tt,ts,ta))
                    
        except Exception,e:
            self.error('AlarmView(%s).event_hook(%s,%s,%s)'%(
              self.name,src,type_, shortstr(value)))
            self.error(traceback.format_exc())
            self.error(array)
        finally:
            if locked is True: self.lock.release()
            self.__dead += now() - tt0
            pass
    
    ###########################################################################
    
    
if __name__ == '__main__': 
        import sys
        AlarmView.__test__(*sys.argv[1:])
   

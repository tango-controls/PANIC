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

"""
.. panic.py: python API for a PyAlarm based alarms system

:mod:`panic` -- The Package for Alarms and Notification of Incidences from Controls
===================================================================================

.. This package is great.

    .. raw:: html

    <hr/>

    .. rubric:: Usage

    And here some usage examples.

.. raw:: html

   <hr/>

"""

import traceback,re,time,os,sys
import fandango
import fandango as fn

from fandango import first,searchCl,matchCl,isString,isSequence,now
from fandango import isFalse,xor,str2time,time2str,END_OF_TIME
from fandango.tango import CachedAttributeProxy, AttrDataFormat
from fandango.tango import PyTango,get_tango_host

from .properties import *

_TANGO = PyTango.Database()

_proxies = fandango.ProxiesDict()
GetProxy = _proxies.get
SetProxy = _proxies.__setitem__
"""
The _proxies object allows to retrieve either DeviceProxy or DeviceServer objects.

 * GetProxy(a/dev/name) will return a DeviceProxy by default.
 * SetProxy('a/dev/name',object) allows to set a different object to be returned (e.g. a device running in the same process)

"""

SEVERITIES = {'DEBUG':0,'INFO':1,'WARNING':2,'ALARM':3,'ERROR':4,'CONTROL':-1}

AlarmStates = fn.Struct({
  'NORM':0, #Normal state
  'ACTIVE':1, #Active and unacknowledged
  'ACKED':2, #Acknowledged by operator
  'RTNUN':3, #Active but returned to normal
  'ERROR':4, #PyAlarm not working properly  
  'SHLVD':-1, #Silenced, hidden, ignored, (DEBUG), temporary state
  'DSUPR':-2, #Disabled by a process condition, failed not throwed
  'OOSRV':-3, #Unconditionally disabled, Enable = False
  })

def shortstr(msg,maxlen=144,line=';'):
    msg = str(msg).replace('\n',line).replace('\r',line)
    if 4 < len(msg) < maxlen: msg = msg[:maxlen-4]+' ...'
    return msg

def intversion(version):
    try:
        if type(version) in (list,tuple): 
            return map(int,version[:3])
        else:
            return map(int,str(version).split('-')[0].split('.'))
    except:
        return None
    
def intersect(a,b):
    a,b = str(a).lower(),str(b).lower()
    return a in b or b in a

def anyendswith(a,b):
    a,b = str(a).lower(),str(b).lower()
    if '/' not in a: a = '/'+a
    if '/' not in b: b = '/'+b
    return a.endswith(b) or b.endswith(a)

###############################################################################
#@todo: Tango access methods

def getAttrValue(obj,default=None):
    """
    Extracts rvalue in tango/taurus3/4 compatible way
    If default = True, obj is returned
    """
    #r = getattr(obj,'rvalue',
             #getattr(obj,'value',
               #obj if default is True 
                 #else default))
    #print([(m,getattr(obj,m)) for m in dir(obj) if 'value' in m.lower()])
    r,v,d = getattr(obj,'rvalue',None),None,None
    if r is None:
        v = getattr(obj,'value',None)
        if v is None:
            d = obj if default is True else default
    #print('getAttrValue(%s)'%fd.shortstr(obj)
          #+': %s,%s,%s'%(r,v,d))
    r = r or v or d
    if r is None and \
        getattr(obj,'data_format',None) == AttrDataFormat.SPECTRUM \
        and obj.is_empty:
        r = []
    return r

def getAlarmDeviceProperties(device):
    """ Method used in all panic classes """
    props = _TANGO.get_device_property(device,ALARM_TABLES.keys())

    #Updating old property names for backwards compatibility
    if not props['AlarmList']:
        props['AlarmList'] = _TANGO.get_device_property(
                                  device,['AlarmsList'])['AlarmsList']
        if props['AlarmList']:
            print '%s: AlarmsList property renamed to AlarmList'%device
            _TANGO.put_device_property(
                    device,{'AlarmList':props['AlarmList'],'AlarmsList':[]})
            
    return props

def getAlarmDeviceProperty(device, prop):
    """ Gets the value of pointed property from the device """
    return _TANGO.get_device_property(device,[prop])[prop]

def setAlarmDeviceProperty(device, prop, value):
    """ Sets property of the device """
    _TANGO.put_device_property(device,{prop:[value]})
    
###############################################################################
# Alarm object used by API

class Alarm(object):
    """
    Alarm object used by API's to keep the state of alarms
    
    It maintains 3 time variables:
      self.updated : last time that set_active was called (active or not)
      self.active : time at which the alarm was activated (only if active)
      self._time : last time that the alarm state changed

      
      
    """
  
    def __init__(self,tag,device='',formula='',description='',receivers='',config='', severity='',api=None):
        #Info from the database
        self.api = api
        self.setup(tag,device,formula,description,receivers,config,severity,write=False)
        self.clear()
        
    def setup(self,tag=None,device=None,formula=None,description=None,receivers=None,config=None, severity=None,write=False):
        """ Assigns values to Alarm struct """
        notNone = lambda v,default:  default
        setVar = lambda k,v: setattr(self,k,v if v is not None else getattr(self,k,''))
        [setVar(k,v) for k,v in (('tag',tag),('device',device),
              ('formula',formula),('description',description),
              ('receivers',receivers),('config',config),
              ('severity',severity))]
        if write: self.write()
        
    def trace(self,msg):
        print('%s: Alarm(%s): %s'%(fn.time2str(),self.tag,msg))

    def clear(self):
        """ This method just initializes Flags updated from PyAlarm devices, it doesn't reset alarm in devices """
        self._state = None
        self._time = None
        self.counter = 0 #N cycles being active
        self.active = 0 #Last timestamp it was activated
        self.updated = 0 #Last value check
        self.recovered = 0 #Last time it was recovered
        self.acknowledged = 0 #If active no more reminders will be sent
        self.disabled = 0 #If disabled the alarm is not evaluated
        self.sent = 0 #Messages sent
        self.last_sent = 0 #Time when last message was sent

    @staticmethod
    def parse_formula(formula):
        """ Gets "TAG:formula#comment" and returns (tag,formula) """
        try:
            tag,formula = formula.split('#')[0].split(':',1)
        except:
            tag,formula = None,None
        return tag,formula

    def parse_severity(self):
        """ Replaces $TAG and $SEVERITY in Alarm severities """
        return self.severity.replace('$TAG',self.tag).replace('$SEVERITY',self.device)

    def parse_description(self):
        """ Replaces $TAG and $NAME in Alarm descriptions """
        return self.description.replace('$TAG',self.tag).replace('$NAME',self.device)

    def get_attribute(self,full=False):
        """ Gets the boolean attribute associated to this alarm """
        return (self.device+'/' if full else '')+self.tag.replace(' ','_').replace('/','_')
    
    def get_model(self):
        model = self.get_attribute(full=True)
        if ':' not in model: model = self.api.tango_host + '/' + model
        return model

    def get_ds(self):
        """ Gets and AlarmDS object related to this alarm """
        try: return self.api.devices[self.device]
        except: return AlarmDS(self.device,api=self.api)
      
    def set_active(self,value,count=1):
        """
        BE CAREFUL, IT MAY INTERFERE WITH COUNTER MANAGEMENT WITHIN PYALARM
        
        Will increment/decrement counter and set active if
        the count value has been reached
        """
        self.updated = now()
        #print('%s.set_active(%s,%s)'%(self.tag,value,self.counter))
        if value:
            if not self.active: 
                self.counter+=1
        elif self.counter>0:
            self.counter-=1
        
        if value and self.counter>=count and not self.active:
            self.last_sent = self.updated
            self.active = value
            self.set_time(value if value>1 else 0)

        if not value and not self.counter:
            self.active = 0
            self.set_time()
            if not self.recovered:
                #print('%s => %s'%(self.tag,0))
                #self.recovered = self.get_time()
                pass

    def get_active(self):
        """ This method connects to the Device to get the value and timestamp of the alarm attribute """
        try:
            self.active = self.get_time()
        except:
            self.active = None
        return self.active
      
    def set_state(self,state=None):
        o = self._state
        if state is None:
            self.get_state(True)
            
        elif state in AlarmStates:
            self._state = AlarmStates[state]
            
        elif isString(state) and ';' in state:
            tag,state,severity,stamp,desc = state.split(';')
            self._state = AlarmStates[state]
            stamp = stamp or 0
            try: stamp = float(stamp)
            except: stamp = str2time(stamp)
            if state in ('NORM'):
                self.active = 0
                self.recovered = stamp
                self.acknowledged = 0
            if state in ('ACTIVE'): 
                self.active = stamp
                self.recovered = 0
                self.acknowledged = 0
            if state in ('RTNUN'): 
                self.active = stamp-1
                self.counter = 0
                self.recovered = stamp
            if state in ('ACKED'):
                self.active = stamp-1
                self.acknowledged = stamp
            if state in ('DSUPR,OOSRV,SHLVD'):
                self.active = 0
                self.disabled = stamp
            if state in ('ERROR'):
                self.active = None
                
        elif isString(state) and ':' in state:
            tt = self.get_time(True) #array cache reading from ds
            if tt: 
                self.set_state('ACTIVE')
                o = self._state
                self.set_active(tt)
            else:
                self.set_state('NORM')
                o = self._state
                self.set_active(0)
        else:
            self._state = AlarmStates.get_key(state)

        if o != self._state or self._time is None:
            fn.log.tracer('%s state changed!: %s -> %s -> %s'
              %(self.tag,o,state,self._state))
            return self.set_time(self.active)
      
    def get_state(self,force=True):
      
        if force or self._state is None:
          
            if self.disabled:
                if time.time() < self.disabled:
                    self._state = AlarmStates.SHLVD
                elif self.disabled < 0:
                    self._state = AlarmStates.OOSRV
                else:
                    self._state = AlarmStates.DSUPR
                    
            elif self.active:
                if self.recovered > self.active:
                    self._state = AlarmStates.RTNUN
                if self.acknowledged:
                    self._state = AlarmStates.ACKED
                else:
                    self._state = AlarmStates.ACTIVE
                    
            elif self.active is None:
                self._state = AlarmStates.ERROR
                
            else:
                self._state = AlarmStates.NORM
        
        return AlarmStates.get_key(self._state)
      
    state = property(fget=get_state,fset=set_state)
      
    def set_time(self,t=None):
        self._time =  t or time.time()
        #tracer('set_time(%s,%s)'%(self._time,self._state))
        return self._time
    
    def get_time(self,attr_value=None):
        """
        This method extracts alarm activation timestamp from the ActiveAlarms array.
        It returns 0 if the alarm is not active.
        """
        if attr_value is None and self._time is not None:
            return self._time

        ## Parsing ActiveAlarms attribute
        if attr_value in (None,True):
            actives = self.get_ds().get_active_alarms()
        elif isSequence(attr_value):
            actives = self.get_ds().get_active_alarms(attr_value)
        else:
            actives = {self.tag:[attr_value]}
            
        return actives.get(self.tag,0)
      
    time = property(get_time,set_time)
        
    def get_quality(self):
        """ it just translates severity to the equivalent Tango quality, but does NOT get actual attribute quality (which may be INVALID) """
        qualities = {'DEBUG':'VALID','INFO':'VALID','WARNING':'WARNING','ALARM':'ALARM','ERROR':'ALARM'}
        quality = PyTango.AttrQuality.names['ATTR_%s'%qualities.get(self.severity,'WARNING')]
        return quality

    def parse_config(self):
        """ Checks the Alarm config related to this alarm """
        config = self.config
        if isinstance(dict,config):
            return config
        elif config:
            config = str(config)
            try:
                if '=' in config and ':' not in config: config = config.replace('=',':')
                if ';' not in config and config.count(':')>1: config = config.replace(',',';')
                config = dict(s.split(':') for s in config.split(';'))
            except: 
                print 'Alarm(%s): Unable to parse config(%s):\n%s'%(tag,config,traceback.format_exc())
                config = {}
        else:
            config = {}
        return config

    def get_enabled(self):
        try: 
                self.disabled = self.get_ds().get().CheckDisabled(self.tag)
                return not self.disabled
        except: return None

    def enable(self):
        """ Enables alarm evaluation """
        return self.get_ds().get().Enable(self.tag)

    def disable(self, comment='',timeout=''):
        """ Disables evaluation of Alarm in its PyAlarm device """
        args = [self.tag, comment]
        if timeout: args.append(str(timeout))
        result = self.get_ds().get().Disable(args)
        return result
        
    def get_acknowledged(self):
        try: 
                self.acknowledged = not self.get_ds().get().CheckDisabled(self.tag)
                return self.acknowledged
        except: return None        
    
    def reset(self, comment):
        """ Acknowledges and resets the Alarm in its PyAlarm device """
        result = self.get_ds().acknowledge(self.tag, comment)
        self.clear()
        return result

    def write(self,device='',exclude='',update=True):
        """
        Updates the Alarm config for the given device in the database
        :param: update controls whether the device.init() will be called or not, if not the alarm will not be applied yet
        """
        self.device = device or self.device
        if not self.device: 
            raise Exception('DeviceNameRequired')
        props = self.get_ds().get_alarm_properties()

        def update_lines(lines,new_line,exclude):
            new_lines,added = [],False #A copy of the array is needed due to a bug in PyTango!
            tag = new_line.split(':',1)[0]
            for l in lines:
                if l.startswith(tag+':') and l!=new_line:
                    print 'In Alarm(%s).write(): line updated: %s' % (tag,new_line)
                    new_lines.append(new_line)
                    added = True
                elif not (exclude and re.match(exclude, l)) and l not in new_lines:
                    new_lines.append(l)
            if not added and new_line not in new_lines: 
                print 'In Alarm(%s).write(): line added: %s' % (tag,new_line)
                new_lines.append(new_line)
            return new_lines

        new_props = {
            'AlarmList': update_lines(props['AlarmList'],
                                      self.tag+':'+self.formula,exclude),
            'AlarmReceivers': update_lines(props['AlarmReceivers'],
                                      self.tag+':'+self.receivers,exclude),
            'AlarmDescriptions': update_lines(props['AlarmDescriptions'],
                                      self.tag+':'+self.description,exclude),
            'AlarmSeverities': update_lines(props['AlarmSeverities'],
                                      self.tag+':'+self.severity,exclude)
            }
        #print 'New properties of %s are: \n%s' % (self.device,new_props)
        self.api.put_db_properties(self.device,new_props)
        if update: AlarmDS(self.device,api=self.api).init()

    def set_severity(self,new_severity):
        """ Sets the severity of Alarm and writes in DB """
        allowed=['DEBUG', 'WARNING', 'ALARM', 'ERROR']
        if new_severity not in allowed:
            raise Exception('Severity not allowed!')
        else:
            old = self.severity
            self.severity = new_severity
            self.write(exclude=old)

    def rename(self,name):
        """ Renames the Alarm and writes in DB """
        old = self.tag
        self.tag = name
        self.write(exclude=old)
        
    def add_receiver(self,receiver,write=True):
        """ Adds a new receiver """
        self.receivers = ','.join([r for r in self.receivers.split(',') if r.strip()!=receiver]+[receiver])
        if write: self.write()

    def remove_receiver(self,receiver,write=True):
        """ Removes a receiver """
        self.receivers = ','.join([r for r in self.receivers.split(',') if r.strip()!=receiver])
        if write: self.write()

    def replace_receiver(self,old,new,write=True):
        """ Replaces a receiver """
        self.remove_receiver(old,False)
        self.add_receiver(new,write)
        
    def to_dict(self):
        isprivate = lambda k: k.startswith('_') or k=='api'
        return dict((k,v) for k,v in self.__dict__.items() if not isprivate(k))
        
    def to_str(self):
        return str(self.to_dict().items())

    def __repr__(self):
        return 'Alarm(%s:%s:%s)' % (self.tag,self.device,self.active)

class AlarmDS(object):
    """ This Class allows to manage the PyAlarm devices from the AlarmAPI """
    def __init__(self,name,api=None):
        self.name = name
        self.api = api
        self.alarms = {}
        self._actives = None
        self.proxy = None
        self.version = None        
        self.get_config(True)
        
    def get(self,alarm=None):
        """ Returns alarm object or device proxy 
        (for backwards compatibility) """
        return self.alarms.get(alarm) if alarm else self.get_proxy()

    def get_proxy(self):
        """ Returns a device proxy """
        if self.proxy is None:
            self.proxy = self.api.get_ds_proxy(self.name)
        return self.proxy
    
    def get_version(self):
        """ Returns the VersionNumber for this device """
        v = self.config.get('VersionNumber',None)
        self.version = intversion(v)
        return self.version
      
    def ping(self):
        try:
          return self.get().ping()
        except:
          return None
        
    def get_config(self,update=False):
        if not getattr(self,'config',None) or update: 
            props = self.api.get_db_properties(self.name,ALARM_CONFIG)
            for p,v in props.items():
                if v in (False,True):
                    props[p] = v
                elif v and v[0] not in ('',None):
                    props[p] = v[0]
                else: #Using default property value
                    try: 
                        props[p] = (PyAlarmDefaultProperties[p][-1] or [''])[0]
                    except: print traceback.format_exc()
            self.config = props
        return self.config
                    
    def get_property(self,prop):
        if isSequence(prop): return self.api.get_db_properties(self.name,prop)
        else: return self.api.get_db_property(self.name,prop)
        
    def put_property(self,prop,value):
        return self.api.put_db_property(self.name,prop,value)
                    
    def enable(self,tag=None):
        """ If Tag is None, this method will enable the whole device, but individual disables will be kept """
        if tag is None:
                self.api.put_db_property(self.name,'Enabled',True)
                self.init()
                print('%s: Enabled!' %self.name)
        else:
                tags = [a for a in self.alarms if matchCl(tag,a)]
                print('%s: Enabling %d alarms: %s' % (self.name,len(tags),tags))
                [self.get().Enable([str(a)]) for t in tags]
                    
    def disable(self,tag=None,comment=None,timeout=None):
        """ If Tag is None this method disables the whole device """
        if tag is None:
                self.api.put_db_property(self.name,'Enabled',False)
                self.init()
                print('%s: Disabled!' %self.name)
        else:
                tags = [a for a in self.alarms if matchCl(tag,a)]
                print('%s: Disabling %d alarms: %s' % (self.name,len(tags),tags))
                [self.get().Disable([str(a) for a in (t,comment,timeout) if a is not None]) for t in tags]
                    
    def get_alarm_properties(self):
        """ Method used in all panic classes """
        props = self.api.get_db_properties(self.name,ALARM_TABLES.keys())
        #Updating old property names
        if not props['AlarmList']:
            props['AlarmList'] = self.api.get_db_property(self.name,'AlarmsList')
            if props['AlarmList']:
                print('%s: AlarmsList property renamed to AlarmList'%self.name)
                self.api.put_db_properties(self.name,{'AlarmList':props['AlarmList'],'AlarmsList':[]})
        return props
    
    def get_model(self):
        """ 
        Returns the proper alarm summary attribute to subscribe.
        It depends on the PyAlarm version
        """
        if self.get_version() >= intversion('6.1.0'):
            model = self.name+'/alarmlist'
        else:
            model = self.name+'/activealarms'
        return model.lower()
      
    def get_active_alarms(self, value = None):
        """ Returns the list of currently active alarms """
        if self._actives is None:
            self._actives = CachedAttributeProxy(self.name+'/ActiveAlarms',
                                               keeptime=3000.)
        if value is None:
            value = getAttrValue(self._actives.read())
            
        if not value: return {}
      
        #Parsing ActiveAlarms: TAG:DATE[:Formula]
        r = {} 
        for line in value:
            splitter = ';' if ';' in line else ':'
            tag,line = str(line).split(splitter,1)

            if not line:
                r[tag] = 0
                continue
            
            date = ':'.join(line.split(':')[:3])
            try:
                r[tag] = time.mktime(time.strptime(date))
            except:
                try:
                    r[tag] = str2time(date)
                except:
                    self.warning('failed to parse date from %s'%line)
                    r[tag] = END_OF_TIME
        return r

    def state(self):
        """ Returns device state """
        try: return self.get().State()
        except: return None
    
    def status(self):
        """ Returns device status """
        return self.get().Status()

    def read(self,filters='*'):
        """ 
        Updates from the database the Alarms related to this device 
        Only alarms which AlarmList row matches filters will be loaded
        """
        props = self.get_alarm_properties()
        self.alarms = {}
        for line in props['AlarmList']:
            #print('read:',line)
            line = line.split('#',1)[0].strip()
            if not line or not searchCl(filters,line): 
              #print('read:pass')
              continue
            try:
                tag,formula = line.split(':',1)
                self.alarms[tag] = {'formula':formula}
                try: 
                  local_receivers = [r for r in props['AlarmReceivers'] if r.startswith(tag+':')]
                  local_receivers = first(local_receivers or ['']).split(':',1)[-1]
                  #global_receivers = self.api.get_global_receivers(tag)
                  #self.alarms[tag]['receivers'] = ','.join((local_receivers,global_receivers))
                  self.alarms[tag]['receivers'] = local_receivers
                except: 
                  traceback.print_exc()
                  self.alarms[tag]['receivers'] = ''
                try: self.alarms[tag]['description'] = first(r for r in props['AlarmDescriptions'] if r.startswith(tag+':')).split(':',1)[-1]
                except: self.alarms[tag]['description'] = ''
                try: self.alarms[tag]['severity'] = first(r for r in props['AlarmSeverities'] if r.startswith(tag+':')).split(':',1)[-1]
                except: self.alarms[tag]['severity'] = ''
            except:
                print('Unparsable Alarm!: %s' % line)
        #print '%s device manages %d alarms: %s'%(self.name,len(self.alarms),self.alarms.keys())
        return self.alarms

    def init(self):
        """ forces the device to reload its configuration"""
        try:
            self.read()
            self.get().init()
            self.config = None
        except:
            print 'Device %s is not running' % self.name

    def acknowledge(self,alarm,comment):
        """
        Acknowledge of an active Alarm
        Returns True if there's no more active alarms, else returns False
        """
        args=[]
        args.append(str(alarm))
        args.append(str(comment))
        try:
            return (False if self.get().ResetAlarm(args) else True)
        except:
            print 'Device %s is not running' % self.name
            print traceback.format_exc()
            return None
    
    def __repr__(self):
        return 'AlarmDS(%s, %d alarms)' % (self.name,len(self.alarms))

class AlarmAPI(fandango.SingletonMap):
    """
    Panic API is a dictionary-like object
    """
    CURRENT = None
    
    def __init__(self,filters='*',tango_host=None,
                 extended=False,
                 logger=fandango.log.WARNING):
      
        self.__init_logger(logger)
        self.log('In AlarmAPI(%s)'%filters)
        self.alarms = {}
        self.filters = filters
        self.tango_host = tango_host or get_tango_host()
        self._global_receivers = [],0
        
        for method in ['__getitem__','__setitem__','keys',
                       'values','__iter__','items','__len__']:
            setattr(self,method,getattr(self.alarms,method))
            
        self._eval = fandango.TangoEval(cache=2*3,use_tau=False,timeout=10000)
        self.macros = [
            ('GROUP(%s)',self.GROUP_EXP,self.group_macro)
            ]
        [self._eval.add_macro(*m) for m in self.macros]
        
        try: self.servers = fandango.servers.ServersDict(tango_host=tango_host)
        except: self.servers = fandango.servers.ServersDict()
        self.db = self.servers.db
        
        self.load(self.filters,extended=extended)
        
    def __init_logger(self,logger):
        if fandango.isCallable(logger):
            self.log = self.debug = self.info = \
              self.warning = self.error = logger
        elif fandango.isNumber(logger) or fandango.isString(logger):
          self._logger = fandango.log.Logger('PANIC',level=logger)
          for l in fandango.log.LogLevels:
            setattr(self,l.lower(),getattr(self._logger,l.lower()))
          self.log = self.debug

    ## Dictionary-like methods
    def __getitem__(self,*a,**k): return self.alarms.__getitem__(*a,**k)
    def __setitem__(self,k,v): return self.alarms.__setitem__(k,v)
    def __len__(self): return self.alarms.__len__()
    def __iter__(self): return self.alarms.__iter__()
    def __contains__(self,obj): 
        return self.has_tag(obj,False) #return self.alarms.__contains__(obj)
    def keys(self): return self.alarms.keys()
    def values(self): return self.alarms.values()
    def items(self): return self.alarms.items()

    def load(self,filters=None,exported=False,extended=False):
        """
        Reloads all alarm properties from the database
        
        Alarms will be loaded if filters match the device or server name

        If exported, only running devices will be checked.
        
        If extended, other alarms will be loaded if the AlarmList row 
          matches the filter
        
        """
        #Loading alarm devices list
        filters = filters or self.filters or '*'
        if isSequence(filters): filters = '|'.join(filters)
        filters = filters.lower()
        self.devices,all_alarms = fandango.CaselessDict(),{}
        self.log('Loading PyAlarm devices matching %s'%(filters))
        
        t0 = tdevs = time.time()
        dbd = fandango.tango.get_database_device(db=self.db)
        all_devices = map(str.lower,dbd.DbGetDeviceList(['*','PyAlarm']))

        if exported:
            dev_exported = fandango.get_all_devices(
              exported=True,host=self.tango_host)
            all_devices = [d for d in all_devices if d in dev_exported]
        
        all_servers = map(str.lower,dbd.DbGetServerList('PyAlarm/*'))
        
        #If filter is the name of a pyalarm device, only this will be loaded
        if filters in all_devices:
            all_devices = matched = [filters]
            
        elif (filters!='*' and '/' in filters 
                and any(matchCl(filters,s) for s in all_servers)):
            self.servers.load_by_name(filters)
            matched = [d.lower() for d in self.servers.get_all_devices() 
                    if d.lower() in all_devices]
            if filters in self.servers:
                all_devices = matched
            
        else:
            matched = []
            
        tdevs = time.time() - tdevs
        tprops = time.time()

        for d in all_devices:
            self.log('Loading device: %s'%d)
            ad = AlarmDS(d,api=self)
            
            if filters=='*' or d in matched or matchCl(filters,d):
                self.devices[d],all_alarms[d] = ad,ad.read()
            
            elif extended:
                #Parsing also if the filters are referenced in the formula
                #This kind of extended filter exceeds the domain concept
                alarms = ad.read(filters=filters)
                if alarms: self.devices[d],all_alarms[d] = ad,alarms
                
        tprops=(time.time()-tprops)
        self.log('\t%d PyAlarm devices loaded, %d alarms'%(
            len(self.devices),sum(len(v) for v in all_alarms.values())))
        
        ######################################################################

        tcheck = time.time()
        #Loading phonebook
        self.get_phonebook(load=True)
        
        #Verifying that previously loaded alarms still exist
        for k,v in self.alarms.items()[:]:
          found = False
          
          for d,vals in all_alarms.items():
              if d.lower() == v.device.lower():
                  if k in vals:
                      found = True
                  else:
                      self.warning('%s not in %s: %s'%(k,d,vals))
            
          if not found:
            self.warning('AlarmAPI.load(): WARNING!: Alarm %s has been '
              'removed from device %s' % (k,v.device))
            self.alarms.pop(k)
        
        #Updating alarms dictionary
        for d,vals in sorted(all_alarms.items()):
          
            for k,v in vals.items():
                self.log('Loading alarm %s.%s (new=%s): %s'%(
                  d,k,k not in self.alarms,v))
                
                if k in self.alarms: #Updating
                  
                    if self.alarms[k].device.lower()!=d.lower():
                        self.warning('AlarmAPI.load(): WARNING!: Alarm %s '
                          'duplicated in devices %s and %s' % 
                          (k,self.alarms[k].device,d))
                        
                    #ALARM State is not changed here, if the formula changed 
                    # something it will be managed by the 
                    # AutoReset/Reminder/Recovered cycle
                    self.alarms[k].setup(k,device=d,formula=v['formula'],
                        description=v['description'],receivers=v['receivers'],
                        severity=v['severity'])
                    
                else: #Creating a new alarm
                    self.alarms[k] = Alarm(k,api=self,device=d,
                        formula=v['formula'],description=v['description'],
                        receivers=v['receivers'],severity=v['severity'])
                    
        tcheck = time.time()-tcheck
        self.log('AlarmAPI.load(%s): %d alarms loaded'%(
            filters,len(self.alarms)))
        AlarmAPI.CURRENT = self
        
        self.info('%ss dedicated to,\n load devices %s\n load properties %s\n'
          'other checks %s'% (time.time()-t0,tdevs,tprops,tcheck))
        return
    
    CSV_COLUMNS = 'tag,device,description,severity,receivers,formula'.split(',')

    def load_from_csv(self,filename,device=None,write=True):
        #fun.tango.add_new_device('PyAlarm/RF','PyAlarm','SR/RF/ALARMS')
        #DEVICE='sr/rf/alarms'
        #f = '/data/Archiving/Alarms/RF_Alarms_jocampo_20120601.csv')
        alarms = {}
        csv = fandango.CSVArray(filename,header=0,comment='#',offset=1)
        for i in range(len(csv)):
            line = fandango.CaselessDict(csv.getd(i))
            line['tag'] = line.get('tag',line.get('alarm_name'))
            line['device'] = str(device 
                or line.get('device') 
                or '%s/%s/ALARMS'%(line.get('system'),line.get('subsystem') 
                or 'CT')).lower()
            alarms[line['tag']] = dict([('load',False)]
                +[(k,line.get(k)) for k in self.CSV_COLUMNS] )
            
        loaded = alarms.keys()[:]
        for i,tag in enumerate(loaded):
            new,old = alarms[tag],self.alarms.get(tag,None)
            if old and all(new.get(k)==getattr(old,k) 
                           for k in self.CSV_COLUMNS):
                alarms.pop(tag)
            elif write:
                print('%d/%d: Loading %s from %s: %s'%(
                  i,len(loaded),tag,filename,new))
                
        if write:
            devs = set(v['device'] for v in alarms.values())
            for d in devs:
                if d not in self.devices:
                    raise Exception('PyAlarm %s does not exist!'%d)
            for i,(tag,v) in enumerate(alarms.items()):
                if tag not in self:
                    self.add(**v)
                else: 
                    self.modify(**v)
            [self.devices[d].init() for d in devs]
            self.load()
        return alarms
            
    def export_to_csv(self,filename,regexp=None,
                      alarms=None,config=False,states=False):
        """ 
        Saves the alarms currently loaded to a .csv file 
        """
        csv = fandango.CSVArray(header=0,comment='#',offset=1)
        alarms = self.filter_alarms(regexp,alarms=alarms)
        columns = self.CSV_COLUMNS + (['ACTIVE'] if states else [])
        csv.resize(1+len(alarms),len(self.CSV_COLUMNS))
        csv.setRow(0,map(str.upper,self.CSV_COLUMNS))
        
        for i,(d,alarm) in enumerate(sorted((a.device,a) for a in alarms)):
            row = [getattr(alarm,k) for k in self.CSV_COLUMNS]
            if states: row += alarm.get_active()
            csv.setRow(i+1,row)
            
        csv.save(filename)
        return 
      
    def export_to_dict(self,regexp=None,alarms=None,config=True,states=False):
        """
        If config is True, the returned dictionary contains a double key:
         - data['alarms'][TAG] = {alarm config}
         - data['devices'] = {PyAlarm properties}
        """
        alarms = self.filter_alarms(regexp,alarms=alarms)
        data = dict((a.tag,a.to_dict()) for a in alarms)

        if states:
          for a,s in data.items():
            s['active'] = self[a].get_active()
            s['date'] = time2str(s['active'])
            
        if config:
          data = {'alarms':data}
          data['devices'] = dict((d,t.get_config()) 
                                 for d,t in self.devices.items())
          
        return data
        
    def load_configurations(self,filename,regexp=None):
        """
        Updates devices properties values from a .csv file
        """
        csv = fandango.CSVArray(filename,header=0,comment='#',offset=1)
        print 'Loading %s file'%filename
        for i in range(csv.size()[0]):
            l = csv.getd(i)
            if not matchCl(l['Host'],self.tango_host): 
              continue
            
            d = l['Device']
            if (not d or d not in self.devices 
                or regexp and not matchCl(regexp,d)):
                continue
            diff = [k for k,v in self.devices[d].get_config().items() 
                if str(v).lower()!=str(l[k]).lower()]
            if diff:
                print 'Updating %s properties: %s'%(d,diff)
                self.put_db_properties(d,dict((k,[l[k]]) for k in diff))
                self.devices[d].init()
        return
        
    def export_configurations(self,filename,regexp=None):
        """
        Save devices property values to a .csv file
        """
        lines = [['Host','Device']+ALARM_CONFIG]
        for d,v in self.devices.items():
            if regexp and not matchCl(regexp,d): continue
            c = v.get_config()
            lines.append([self.tango_host,d]+[str(c[k]) for k in ALARM_CONFIG])
        open(filename,'w').write('\n'.join('\t'.join(l) for l in lines))
        print '%s devices exported to %s'%(len(lines),filename)
        
    def has_tag(self,tag,raise_=False):
        nt = first((k for k in self.keys() if k.lower()==tag.lower()),None)
        if raise_ and nt is None: raise('TagDoesntExist:%s'%tag)
        return nt

    def save_tag(self,tag):
        """ Shortcut to force alarm update in database """
        self[self.has_tag(tag,True)].write()
        
    def get_device(self,key,full=False):        
        """ Given a device or alarm name returns an AlarmDS object """
        if key in self.alarms:
            return self.devices[self.alarms[key].device]
        if not full and ':' in key:
            key = key.split(':',1)[-1].split('/',1)[1]
        if key in self.devices:
            return self.devices[key]
        return None

    def get_ds_proxy(self,dev):
        try:
            return self.servers.proxies[dev]
        except:
            # If failed, convert into a local tango name
            return self.get_device(dev).get_proxy()
    
    def get_db_properties(self,ref,props):
        if '/' not in ref:
          return self.servers.db.get_property(ref,props)
        elif ref.count('/')>=2:
          return self.servers.db.get_device_property(ref,props)
        else:
          raise Exception,'Unknown %s'%ref      
     
    def get_db_property(self,ref,prop):
        return list(self.get_db_properties(ref,[prop])[prop])
    
    def put_db_properties(self,ref,props):
        if '/' not in ref:
          self.servers.db.put_property(ref,props)
        elif ref.count('/')>=2:
          self.servers.db.put_device_property(ref,props)
        else:
          raise Exception,'Unknown %s'%ref
    
    def put_db_property(self,ref,prop,value):
        if not isSequence(value): value = [value]
        self.put_db_properties(ref,{prop:value})
        
    def get_class_property(self,klass,prop):
        return list(self.servers.db.get_class_property(klass,[prop])[prop])
    
    def put_class_property(self,klass,prop,value):
        if not isSequence(value): value = [value]
        self.servers.db.put_class_property(klass,{prop:value})
        
    def get_phonebook(self,load=True):
        """ gets the phonebook, returns a list """        
        if load or not getattr(self,'phonebook',None):
            ph,prop = {},self.get_class_property('PyAlarm','Phonebook')
            for line in prop:
                line = line.split('#',1)[0]
                if line: ph[line.split(':',1)[0]]=line.split(':',1)[-1]
            #Replacing nested keys
            for k,v in ph.items():
                for s in v.split(','):
                    for x,w in ph.items():
                        if s==x: ph[k] = v.replace(s,w)
            self.phonebook = ph
        return self.phonebook
        
    def parse_phonebook(self,receivers):
        """
        Replaces phonebook entries in a receivers list
        
        The behavior of phonebook parsing is dependent 
        on using '%' to mark phonebook entries.
        
        """
        result,receivers = [],[s.strip() for s in receivers.split(',')]
        for r in receivers:
          if r in self.phonebook: 
            r = self.phonebook[r]
          elif '%' in r:
            for p in self.phonebook:
              #re.split used to discard partial matches
              if p in re.split('[,:;/\)\(]',r):
                r = r.replace(p,self.phonebook[p])
          result.append(r)
        return ','.join(result)

    def remove_phonebook(self, tag):
        """ Removes a person from the phonebook """        
        prop = self.get_class_property('PyAlarm','Phonebook')
        if tag not in str(prop): raise Exception('NotFound:%s'%tag)
        self.save_phonebook([p for p in prop if not p.split(':',1)[0]==tag])

    def edit_phonebook(self, tag, value, section=''):
        """ Adds a person to the phonebook """
        prop = self.get_class_property('PyAlarm','Phonebook')
        name = tag.upper()
        value = '%s:%s'%(name,value)
        lines = [line.strip().split(':',1)[0].upper() for line in prop]
        if name in lines: #Replacing
            index = lines.index(name)
            print('AlarmAPI.edit_phonebook(%s,%s,%s), replacing at [%d]'%(
              tag,value,section,index))
            prop = prop[:index]+[value]+prop[index+1:]
        else: #Adding
            if section and '#' not in section: section = '#%s'%section
            index = len(lines) if not section or section not in lines \
                    else lines.index(section)+1
            print('AlarmAPI.edit_phonebook(%s,%s,%s), adding at [%d]'%(
              tag,value,section,index))
            prop = prop[:index]+[value]+prop[index:]
            
        self.save_phonebook(prop)

    def save_phonebook(self, new_prop):
        """ Saves a new phonebook in the database """
        self.put_class_property('PyAlarm','Phonebook',new_prop)
        self.phonebook = None #Force to reload
        return new_prop
      
    def get_global_receivers(self,tag='',renew=False):
        try:
          if (renew or self._global_receivers[-1]<time.time()-3600):
            prop = self.get_class_property('PyAlarm','GlobalReceivers')
            self._global_receivers = (prop,time.time())
          else:
            prop = self._global_receivers[0]
          if not tag:
            return prop
          else:
            prop = [p.split(':',1) for p in prop]
            rows = []
            for line in prop:
              mask = (line[0] if len(line)>1 else '*').split(',')
              neg = [m[1:] for m in mask if m.startswith('!')]
              if neg and any(matchCl(m,tag) for m in neg):
                continue
              pos = [m for m in mask if not m.startswith('!')]
              if not pos or any(matchCl(m,tag) for m in pos):
                rows.append(line[-1])
            return ','.join(rows)
        except:
          print('>>> Exception at get_global_receivers(%s)'%tag)
          traceback.print_exc()
          return ''
        
    GROUP_EXP = fandango.tango.TangoEval.FIND_EXP.replace('FIND','GROUP')
    
    def group_macro(self,match):
        """
        For usage details see:

          https://github.com/tango-controls/PANIC/
            blob/documentation/doc/recipes/AlarmsHierarchy.rst
        """
        match,cond = match.split(';',1) if ';' in match else (match,'')
        #if '/' not in match and self._eval._locals.get('DEVICE',None): 
          #match = self._eval._locals['DEVICE']+'/'+match

        exps = match.split(',')
        attrs = []
        for e in exps:
          if '/' in e:
              attrs.extend(d+'/'+a 
                  for dev,attr in [e.rsplit('/',1)] 
                  for d,dd in self.devices.items() 
                  for a in dd.alarms 
                  if matchCl(dev,d) and matchCl(attr,a))
          else:
              attrs.extend(self[a].get_attribute(full=True) for a in self if matchCl(e,a))
              
        if not cond: 
          attrs = [m+'.delta' for m in attrs]
          cond = 'x > 0'

        exp = 'any([%s for x in [ %s ]])'%(cond,' , '.join(attrs))
        return exp
      
    def split_formula(self,formula,keep_operators=False):
        f = self[formula].formula if formula in self else formula
        i,count,buff,final = 0,0,'',[]
        while i<len(f):
          s = f[i]
          if s in '([{': count+=1
          if s in ')]}': count-=1
          if not count and s in ' \t':
            if f[i:i+4].strip().lower() == 'or':
              nx = 'or'
              i+=len(nx)+2
            elif f[i:i+5].strip().lower() == 'and':
              nx = 'and'     
              i+=len(nx)+2
            else:
              nx = ''
            if nx:
              final.append(buff.strip())
              if keep_operators:
                final.append(nx)
              buff = ''
              continue
          
          buff+=s   
          i+=1
          nx=''
        return final

    def parse_alarms(self, formula):
        """
        Searches for alarm tags used in the formula
        """
        alnum = '(?:^|[^/a-zA-Z0-9-_])([a-zA-Z0-9-_]+)'#(?:$|[^/a-zA-Z0-9-_])' 
        #It's redundant to check for the terminal character, re already does this
        var = re.findall(alnum,formula)
        #print '\tparse_alarms(%s): %s'%(formula,var)
        return [a for a in self.keys() if a in var]
        
    def replace_alarms(self, formula):
        """
        Replaces alarm tags by its equivalent device/alarm attributes
        """
        try:
            var = self.parse_alarms(formula)
            #print 'replace_alarms(%s): %s'%(formula,var)
            if var:
                for l,a in reversed([(len(s),s) for s in var]):
                    x = '(?:^|[^/a-zA-Z0-9-_])(%s)(?:$|[^/a-zA-Z0-9-_])'%a
                    attr = self[a].device+'/'+a
                    m,new_formula = True,''
                    #print 'replacing %s by %s'%(a,attr)
                    while m:
                        m = re.search(x,formula)
                        if m:
                            start,end = m.start(),m.end()
                            if not formula.startswith(a): start+=1
                            if not formula.endswith(a): end-=1
                            new_formula += formula[:start]+attr
                            formula = formula[end:]
                    formula = new_formula+formula
            return formula
        except:
            print('Exception in replace_alarms():%s'%traceback.format_exc())
            return formula
                        
    def parse_attributes(self, formula, replace = True):
        """ Returns all tango attributes that appear in a formula """
        if formula in self.alarms: formula = self.alarms[formula].formula
        formula = getattr(formula,'formula',formula)
        attributes = self._eval.parse_variables(self.replace_alarms(formula) 
                                                if replace else formula)
        return sorted('%s/%s'%(t[:2]) for t in attributes)
        
    def evaluate(self, formula, device=None,timeout=1000,_locals=None):
        #Returns the result of evaluation on formula
        #Both result and attribute values are kept!, 
        #be careful to not generate memory leaks
        try:
            if formula.strip().lower() in ('and','or'):
                return None
            if device and not fandango.tango.check_device(device):
                device = None
            if device and device in self.devices:
                d = self.devices[device].get()
                t = d.get_timeout_millis()
                d.set_timeout_millis(timeout)
                try:
                  r = d.evaluateFormula(formula)
                  return r
                except Exception,e:
                  raise e
                finally:
                  d.set_timeout_millis(t)
            else:
                self._eval.set_timeout(timeout)
                self._eval.update_locals({'PANIC':self})
                if _locals: self._eval.update_locals(_locals)
                return self._eval.eval(self.replace_alarms(formula))
        except Exception,e:
            return e

    def get(self,tag='',device='',attribute='',receiver='', severity='', 
            alarms = None,limit=0,strict=False):
        """ 
        Gets alarms matching the given filters 
        (tag,device,attribute,receiver,severity) 
        """
        result=[]
        alarms = alarms or self.values()
        if limit==1 and tag in self.alarms:
          found = [self[tag]]
        else:
          filters = {'tag':tag,'device':device,'attribute':attribute,
                   'receivers':receiver,'severity':severity}
          if strict: 
              found = [a for a in alarms if
                     all([getattr(a,f)==v for f,v in filters.items() if v])]
          else:
              found =  self.filter_alarms(filters,alarms)
          
        if not limit: return found
        elif limit==1: return found[0]
        else: return found[:limit]
        
        #if tag and not tag.endswith('$'): tag+='$'
        #if attribute and not attribute.endswith('$'): attribute+='$'
        #if device and not device.endswith('$'): device+='$'
        ##if receiver and not receiver.startswith('%'): receiver='%'+receiver
        #if severity and not severity.endswith('$'): severity+='$'
        #for alarm in (alarms or self.alarms.values()):
            #if  ((not tag or searchCl(tag,alarm.tag)) and
                #(not device or searchCl(device,alarm.device)) and
                #(not attribute or searchCl(attribute,alarm.formula)) and
                #(not receiver or receiver in alarm.receivers) and
                #(not severity or searchCl(severity,alarm.severity))):
                #result.append(alarm)
        #return result
            
    def get_basic_alarms(self):
        """
        Children are those alarms that have no alarms below or have 
        a higher alarm that depends from them.
        """ 
        self.log('Getting Alarm children ...')
        result=[]
        for a,v in self.items():
            children = self.parse_alarms(v.formula)
            if children: 
                result.extend(children)
            else: 
                result.append(a)
        result = set(result)
        return [v for a,v in self.items() if a in result]
      
    def filter_alarms(self, filters, alarms = None):
        """
        filters must be a dictionary: {filter:regexp}
        alarms must be a list of alarm objects
        regexps accept '!' to exclude a certain match
        
        Tries to apply all default filters:
          'tag','name',
          'device','active','severity','regexp','receivers'
          'formula','attribute','history','failed','hierarchy'
        """
        alarms = alarms or self.values()
        filters = filters or {}
        if isString(filters): filters = {'regexp':filters}
        exclude = []
        self.log('AlarmAPI.filter_alarms(%s)'%filters)
        
        for f,r in filters.items():
            if f in ('name','alarm'): f = 'tag'
            if not r: continue
            result = []
            
            for a in alarms:
                ok = False
                if isString(a): a = self[a]
                
                if f == 'regexp':
                    ## Regexp will be used to explicitly reject an alarm
                    regexp = r.split(',')
                    for e in regexp:
                        n,e = '!' in e,e.strip('!')
                        s = str(map(str,a.to_dict().values()))
                        m = searchCl(e,s)
                        if m and n: exclude.append(a.tag)
                        elif m and not n: ok = True
                        elif not m and n and len(regexp)==1: ok = True
                        
                if a.tag in exclude: continue
              
                if f == 'attribute':
                    attrs = self.parse_attributes(a.formula)
                    if any(searchCl(r,t,0,1) for t in attrs): ok = True
                  
                elif f == 'hierarchy':
                    r = r.upper()
                    is_top = self.parse_alarms(a.formula)
                    if not xor(is_top,r == 'TOP'): ok = True
                  
                elif f == 'severity':
                    r,s = r.upper().strip(),a.severity.upper().strip()
                    s = s or 'WARNING'
                    if SEVERITIES[s]>=SEVERITIES[r]: ok = True
                    
                elif f == 'receivers':
                    v = self.parse_phonebook(a.receivers)
                    if searchCl(r,v,0,1): ok = True
                    
                else:
                    v = getattr(a,f,'')
                    if isString(v):
                      if v and searchCl(r,v,0,1): ok = True
                    else: ok = not xor(isFalse(r),isFalse(v))
                    
                if ok: result.append(a)
                        
            alarms = result
            
        return alarms


    def filter_hierarchy(self, rel, alarms = None):
        """
        TOP are those alarms which state is evaluated using other Alarms values.
        BOTTOM are those alarms that have no alarms below or 
        have a TOP alarm that depends from them.
        """ 
        return self.filter_alarms({'hierarchy':rel})

    def filter_severity(self, sev, alarms = None):
        return self.filter_alarms({'severity':sev})

    def get_states(self,tag='',device=''):
        device = device.lower()
        if tag:
            if not tag in self.alarms: return None
            return self.alarms[tag].get_active()
        elif device:
            if device not in self.devices: return {}
            d = self.devices[device]
            try:
                dp = d.get()
                if dp.ping():
                    #return dict((a,self.alarms[a].get_active()) for a in self.devices[device].alarms)
                    als = sorted(self.devices[device].alarms.keys())
                    ats = [self.alarms[a].get_attribute() for a in als]
                    vals = [v.value for v in dp.read_attributes(ats)]
                    return dict((a,t) for a,t in zip(als,vals))
                else:
                    raise Exception('')
            except Exception,e:
                print 'device %s is not running'%device
                traceback.print_exc()
                [setattr(self.alarms[a],'active',None) for a in d.alarms]
                return dict((a,None) for a in d.alarms)
        else:
            vals = dict()
            [vals.update(self.get_states(device=d)) for d in self.devices]
            return vals
        
    def get_configs(self,tag='*'):
        result = {}
        for alarm in self.get(tag):
            reks = self.parse_phonebook(alarm.receivers)
            result[alarm.tag] = {
                'Device':alarm.device,
                'Severity':alarm.severity,
                'Snap':'SNAP' in reks,
                'Email':'@' in reks,
                'Action':'ACTION' in reks,
                'SMS':'SMS' in reks,
                }
            result[alarm.tag].update((k,v) 
                  for k,v in self.devices[alarm.device].get_config().items() 
                  if k in ALARM_CONFIG)
        return result        

    def get_admins_for_alarm(self,alarm=''):
        users = filter(bool,
                self.get_class_property('PyAlarm','PanicAdminUsers'))
        if users:
          if alarm: 
             users = users+[r.strip().split('@')[0] for r in 
                    self.parse_phonebook(self[alarm].receivers).split(',') 
                    if '@' in r]
        return users

    def add(self,tag,device,formula='',description='',receivers='', severity='WARNING', load=True, config=None,overwrite=False):
        """ Adds a new Alarm to the database """
        device,match = device.lower(),self.has_tag(tag)
        if match:
            tag = match
            if not overwrite: 
                raise Exception('TagAlreadyExists:%s'%tag)
            else: 
                self.modify(tag=tag,device=device,formula=formula,
                    description=description,receivers=receivers,
                    severity=severity,load=load,config=config)
                
        if device not in self.devices: 
            raise Exception('DeviceDescriptiondDesntExist:%s'%device)
          
        alarm = Alarm(tag, api=self, device=device, formula=formula, 
              description=description, receivers=receivers, severity=severity)

        if config is not None: 
            self.set_alarm_configuration(tag,device,config)

        alarm.write()
        if load: self.load()
        return tag
        
    def modify(self,tag,device,formula='',description='',receivers='', severity='WARNING', config=None, load=True):
        """ Modfies an Alarm in the database """
        device = device.lower()
        tag = self.has_tag(tag,raise_=True)
        if device not in self.devices: 
            raise Exception('DeviceDescriptiondDoesntExist:%s'%device)
        alarm = self[tag]
        old_device,new_device = alarm.device,device
        alarm.setup(tag=tag,device=old_device,formula=formula,
                    description=description,receivers=receivers,
                    severity=severity,write=False)
        
        if config is not None: self.set_alarm_configuration(tag,device,config)
        self.rename(tag,tag,new_device,load=True)

    def set_alarm_configuration(self,tag,device,config):
        """
        This method is not operative yet, in the future will be used to 
        do customized setups for each alarm.
        """
        self.info('In panic.set_alarm_configuration(%s,%s)'%(device,tag))
        self.error('\tNotImplemented!')
        return 
        props=self.devices[device].get_config(True)
        dictlist=[]
        for key, value in props.iteritems():
            temp = str(key)+'='+str(value[0] if isSequence(value) else value)
            print '%s.%s.%s'%(device,alarm,temp)
            dictlist.append(temp)
            
        l=';'.join(dictlist)
        l=str(tag)+':'+l
        old_props=self.get_db_property(device, 'AlarmConfigurations')
        new_props=str(old_props).strip("]'[")+l+';'
        #return new_props
        try: self.put_device_property(device, 'AlarmConfigurations', new_props)
        except: Exception('Cant append the database!')

    def purge(self,device,tag,load=False):
        """
        Removes any alarm from a device matching the given tag.
        Database must be reloaded afterwards to update the alarm list.
        """
        props = self.devices[device].get_alarm_properties()
        self.put_db_properties(device,  
            {'AlarmList':[p for p in props['AlarmList'] 
                          if not p.startswith(tag+':')],
            'AlarmReceivers':[p for p in props['AlarmReceivers'] 
                              if not p.startswith(tag+':')],
            'AlarmDescriptions':[p for p in props['AlarmDescriptions'] 
                                 if not p.startswith(tag+':')],
            'AlarmSeverities':[p for p in props['AlarmSeverities'] 
                               if not p.startswith(tag+':')],})
        self.devices[device].init()
        if load: self.load()
        return

    def remove(self,tag,load=True):
        """ Removes an alarm from the system. """
        tag = self.has_tag(tag,True)
        val = self.alarms.pop(tag) #Order matters!
        self.purge(val.device,tag)
        if load: self.load()
        return val

    def rename(self,tag,new_tag='',new_device='',load=True):
        """ Renames an existing tag, it also allows to move to a new device. """
        new_device = new_device.lower()
        if new_device and new_device not in self.devices: 
            raise Exception('DeviceDoesntExist:%s'%new_device)
          
        tag = self.has_tag(tag,True)
        alarm = self.remove(tag)
        new_device = new_device or alarm.device
        new_tag = new_tag or alarm.tag
        self.add(new_tag,new_device,alarm.formula,alarm.description,
                 alarm.receivers,alarm.severity,load=load)
        return
        
    def update_servers(self,targets):
        """ Forces PyAlarm devices to reload selected alarms """
        devs = set((self[t].device if t in self.alarms else t) 
                   for t in targets)
        self.warning('re-Initializing devices: %s'%devs)
        [self.devices[d].init() for d in devs]

    def start_servers(self,tag='',device='',host=''):
        """ Starts Alarm Servers matching the filters """
        host = host or self.tango_host
        self.servers.start_servers(set(self.servers.get_device_server(a.device) 
                              for a in self.get_alarms(tag,device)),host=host)

    def stop_servers(self,tag='',device=''):
        """ Stops Alarm Servers matching the filters """
        host = host or self.tango_host
        self.servers.stop_servers(set(self.servers.get_device_server(a.device) 
                              for a in self.get_alarms(tag,device)))

    #def __getitem__(self,key): return self.alarms.__getitem__(key)
    #def __setitem__(self,key,value): return self.alarms.__setitem__(key,value)
    #def __iter__(self): return self.alarms.__iter__()
    #def keys(self): return self.alarms.keys()
    #def values(self): return self.alarms.values()
    #def items(self): return self.alarms.items()

    def __repr__(self): 
        #return '\n'.join(sorted('%s: %s' % (
        # a.tag,a.description) for a in self.values()))
        return 'AlarmAPI(%s,%s,[%d])'%(self.filters,self.tango_host,len(self))

api = AlarmAPI 

def current():
    return AlarmAPI.CURRENT or AlarmAPI()
  
def main():
    import sys,fandango as Fn

try:
    from fandango.doc import get_fn_autodoc
    __doc__ = get_fn_autodoc(__name__,vars())
except:
    #import traceback
    #traceback.print_exc()
    pass
  

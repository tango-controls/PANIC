#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
##
## This file is part of Tango Control System
##
## http://www.tango-controls.org/
##
## (copyleft) Sergi Rubio Manrique / CELLS / ALBA Synchrotron, Bellaterra, Spain
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

import traceback,re
import fandango
import fandango.functional as fun
import PyTango


_TANGO = PyTango.Database()

_proxies = fandango.ProxiesDict()
GetProxy = _proxies.get
SetProxy = _proxies.__setitem__
"""
The _proxies object allows to retrieve either DeviceProxy or DeviceServer objects.

 * GetProxy(a/dev/name) will return a DeviceProxy by default.
 * SetProxy('a/dev/name',object) allows to set a different object to be returned (e.g. a device running in the same process)

"""

ALARM_TABLES = ['AlarmList','AlarmReceivers','AlarmDescriptions', 'AlarmConfigurations', 'AlarmSeverities']
ALARM_CYCLE = ['Enabled','PollingPeriod','AlarmThreshold','AlertOnRecovery','Reminder', 'AutoReset','RethrowState','RethrowAttribute']
ALARM_ARCHIVE = ['UseSnap','CreateNewContexts',]
ALARM_LOGS = ['LogFile','HtmlFolder','FlagFile','FromAddress','MaxAlarmsPerDay','MaxMessagesPerAlarm',]
ALARM_CONTROL = ['EvalTimeout','UseProcess','SMSConfig','LogLevel',]
ALARM_CONFIG = ALARM_CYCLE+ALARM_ARCHIVE+ALARM_LOGS
ALARM_12_ATTS = ALARM_CONFIG
ALARM_SEVERITIES = ['ERROR','ALARM','WARNING','DEBUG']

###############################################################################
#@todo: These methods and AlarmAPI.setAlarmDeviceProperty should be moved to AlarmDS

def getAlarmDeviceProperties(device):
    """ Method used in all panic classes """
    props = _TANGO.get_device_property(device,ALARM_TABLES)
    #Updating old property names
    if not props['AlarmList']:
        props['AlarmList'] = _TANGO.get_device_property(device,['AlarmsList'])['AlarmsList']
        if props['AlarmList']:
            print '%s: AlarmsList property renamed to AlarmList'%device
            _TANGO.put_device_property(device,{'AlarmList':props['AlarmList'],'AlarmsList':[]})
    return props

def getAlarmDeviceProperty(device, prop):
    """ Gets the value of pointed property from the device """
    return _TANGO.get_device_property(device,[prop])[prop]

def setAlarmDeviceProperty(device, prop, value):
    """ Sets property of the device """
    _TANGO.put_device_property(device,{prop:[value]})

###############################################################################

class Alarm(object):
    def __init__(self,tag,device='',formula='',description='',receivers='',config='', severity='',api=None):
        #Info from the database
        self.api = api
        self.setup(tag,device,formula,description,receivers,config,severity,write=False)
        self.clear()

    def setup(self,tag=None,device=None,formula=None,description=None,receivers=None,config=None, severity=None,write=False):
        """ Assigns values to Alarm struct """
        notNone = lambda v,default:  default
        setVar = lambda k,v: setattr(self,k,v if v is not None else getattr(self,k,''))
        [setVar(k,v) for k,v in (('tag',tag),('device',device),('formula',formula),('description',description),('receivers',receivers),('config',config),('severity',severity))]
        if write: self.write()

    def clear(self):
        """ This method just initializes Flags updated from PyAlarm devices, it doesn't reset alarm in devices """
        self.active = 0 #Last timestamp it was activated
        self.recovered = 0 #Last time it was recovered
        self.counter = 0 #N cycles being active
        self.sent = 0 #Messages sent
        self.last_sent = 0 #Time when last message was sent
        self.acknowledged = 0 #If active no more reminders will be sent

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

    def get_ds(self):
        """ Gets and AlarmDS object related to this alarm """
        try: return self.api.devices[self.device]
        except: return AlarmDS(self.device,api=self.api)

    def get_active(self):
        """ This method connect to the Device to get the value of the alarm attribute """
        try:
            self.active = int(self.get_ds().get().read_attribute(self.get_attribute()).value)
        except:
            self.active = None
        return self.active
        
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
            'AlarmList': update_lines(props['AlarmList'],self.tag+':'+self.formula,exclude),
            'AlarmReceivers': update_lines(props['AlarmReceivers'],self.tag+':'+self.receivers,exclude),
            'AlarmDescriptions': update_lines(props['AlarmDescriptions'],self.tag+':'+self.description,exclude),
            'AlarmSeverities': update_lines(props['AlarmSeverities'],self.tag+':'+self.severity,exclude)
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
        self.receivers = ','.join([r for r in self.receivers.split(',') if r!=receiver]+[receiver])
        if write: self.write()

    def remove_receiver(self,receiver,write=True):
        """ Removes a receiver """
        self.receivers = ','.join([r for r in self.receivers.split(',') if r!=receiver])
        if write: self.write()

    def replace_receiver(self,old,new,write=True):
        """ Replaces a receiver """
        self.remove_receiver(old,False)
        self.add_receiver(new,write)

    def __repr__(self):
        return 'Alarm(%s:%s)' % (self.tag,self.description)

class AlarmDS(object):
    """ This Class allows to manage the PyAlarm devices from the AlarmAPI """
    def __init__(self,name,api=None):
        self.name = name
        self.api = api
        self.alarms = {}
        self.get_config(True)
        self.proxy = None

    def get(self):
        """ Returns a device proxy """
        if self.proxy is None:
            self.proxy = self.api.get_ds_proxy(self.name)
        return self.proxy
        
    def get_config(self,update=False):
        if not getattr(self,'config',None) or update: 
            props = self.api.get_db_properties(self.name,ALARM_CONFIG)
            for p,v in props.items():
                if v in (False,True):
                    props[p] = v
                elif v:
                    props[p] = v[0]
                else:
                    try: 
                        import PyAlarm
                        props[p] = (PyAlarm.PyAlarmClass.device_property_list[p][-1] or [''])[0]
                    except: print traceback.format_exc()
            self.config = props
        return self.config
                    
    def get_property(self,prop):
        if fandango.isSequence(prop): return self.api.get_db_properties(self.name,prop)
        else: return self.api.get_db_property(self.name,prop)
        
    def put_property(self,prop,value):
        return self.api.put_db_property(self.name,prop,value)
                    
    def enable(self):
        #This method will enable all alarm notifications from this device
        self.api.put_db_property(self.name,'Enabled',True)
        self.init()
                    
    def disable(self):
        #This method will disable all alarm notifications from this device
        self.api.put_db_property(self.name,'Enabled',False)
        self.init()
                    
    def get_alarm_properties(self):
        """ Method used in all panic classes """
        props = self.api.get_db_properties(self.name,ALARM_TABLES)
        #Updating old property names
        if not props['AlarmList']:
            props['AlarmList'] = self.api.get_db_property(self.name,'AlarmsList')
            if props['AlarmList']:
                print '%s: AlarmsList property renamed to AlarmList'%self.name
                self.api.put_db_properties(self.name,{'AlarmList':props['AlarmList'],'AlarmsList':[]})
        return props

    def state(self):
        """ Returns device state """
        return self.get().State()
    
    def status(self):
        """ Returns device status """
        return self.get().Status()

    def read(self,filters='*'):
        """ Updates from the database the Alarms related to this device """
        props = self.get_alarm_properties()
        self.alarms = {}
        for line in props['AlarmList']:
            line = line.split('#',1)[0].strip()
            if not line or not fun.searchCl(filters,line): continue
            try:
                tag,formula = line.split(':',1)
                self.alarms[tag] = {'formula':formula}
                try: self.alarms[tag]['receivers'] = fun.first(r for r in props['AlarmReceivers'] if r.startswith(tag+':')).split(':',1)[-1]
                except: self.alarms[tag]['receivers'] = ''
                try: self.alarms[tag]['description'] = fun.first(r for r in props['AlarmDescriptions'] if r.startswith(tag+':')).split(':',1)[-1]
                except: self.alarms[tag]['description'] = ''
                try: self.alarms[tag]['severity'] = fun.first(r for r in props['AlarmSeverities'] if r.startswith(tag+':')).split(':',1)[-1]
                except: self.alarms[tag]['severity'] = ''
            except:
                print 'Unparsable Alarm!: %s' % line
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
            return None
    
    def __repr__(self):
        return 'AlarmDS(%s, %d alarms)' % (self.name,len(self.alarms))

class AlarmAPI(fandango.SingletonMap):
    """
    Panic API is a dictionary-like object
    """
    def __init__(self,filters='*',tango_host=None):
        print 'In AlarmAPI(%s)'%filters
        self.alarms = {}
        self.filters = filters
        self.tango_host = tango_host
        for method in ['__getitem__','__setitem__','keys','values','__iter__','items','__len__']:
            setattr(self,method,getattr(self.alarms,method))
        try: self.servers = fandango.servers.ServersDict(tango_host=tango_host)
        except: self.servers = fandango.servers.ServersDict()
        self.load(self.filters)

    ## Dictionary-like methods
    def __getitem__(self,*a,**k): return self.alarms.__getitem__(*a,**k)
    def __setitem__(self,*a,**k): return self.alarms.__setitem__(*a,**k)
    def __len__(self): return self.alarms.__len__()
    def __iter__(self): return self.alarms.__iter__()
    def __containes__(self,obj): return self.alarms.__contains__(obj)
    def keys(self): return self.alarms.keys()
    def values(self): return self.alarms.values()
    def items(self): return self.alarms.items()

    def load(self,filters=None):
        """
        Reloads all alarm properties from the database
        :param filters: is used to specify which devices to be loaded
        """
        #Loading alarm devices list
        filters = filters or self.filters or '*'
        if fun.isSequence(filters): filters = '|'.join(filters)
        self.devices,all_alarms = fandango.CaselessDict(),{}
        import time
        print '%s: Loading PyAlarm devices matching %s'%(time.ctime(),filters)
        self.servers.load_by_name('PyAlarm/*')
        for s,r in self.servers.items():
            for d in r.get_device_list():
                d = d.lower()
                ad = AlarmDS(d,api=self)
                if fun.matchCl(filters,s,terminate=True) or fun.matchCl(filters,d,terminate=True):
                    self.devices[d],all_alarms[d] = ad,ad.read()
                else:
                    alarms = ad.read(filters=filters)
                    if alarms: self.devices[d],all_alarms[d] = ad,alarms
        print '\t%d PyAlarm devices loaded, %d alarms'%(len(self.devices),sum(len(v) for v in all_alarms.values()))

        #Loading phonebook
        self.get_phonebook(load=True)
            
        #Verifying that previously loaded alarms still exist
        for k in self.alarms.keys()[:]:
            if not any(k in vals for vals in all_alarms.values()):
                print 'AlarmAPI.load(): WARNING!: Alarm %s has been removed from device %s' % (k,self.alarms[k].device)
                self.alarms.pop(k)
        #Updating alarms dictionary
        for d,vals in sorted(all_alarms.items()):
            for k,v in vals.items():
                if k in self.alarms: #Updating
                    if self.alarms[k].device.lower()!=d.lower():
                        print 'AlarmAPI.load(): WARNING!: Alarm %s duplicated in devices %s and %s' % (k,self.alarms[k].device,d)
                    #ALARM State is not changed here, if the formula changed something it will be managed by the AutoReset/Reminder/Recovered cycle
                    self.alarms[k].setup(k,device=d,formula=v['formula'],description=v['description'],receivers=v['receivers'],severity=v['severity'])
                else: #Creating a new alarm
                    self.alarms[k] = Alarm(k,api=self,device=d,formula=v['formula'],description=v['description'],receivers=v['receivers'],severity=v['severity'])
        print 'AlarmAPI.load(%s): %d alarms loaded'%(filters,len(self.alarms))
        return
                
    def load_from_csv(self,filename,device=None,write=True):
        #fandango.tango.add_new_device('PyAlarm/RF','PyAlarm','SR/RF/ALARMS')
        #DEVICE='sr/rf/alarms'
        #f = '/data/Archiving/Alarms/RF_Alarms_jocampo_20120601.csv')
        alarms,csv = {},fandango.CSVArray(filename,header=0,comment='#',offset=1)
        #csv.load(f,'#')
        #csv.header = 0
        #csv.xoffset = 1
        #csv.getHeaders()
        #api = panic.AlarmAPI()
        for i in range(len(csv)):
            line = fandango.CaselessDict(csv.getd(i))
            line['tag'] = line.get('tag',line['alarm_name'])
            line['device'] = device or line.get('device') or '%s/%s/ALARMS'%(line['system'],line['subsystem'] or 'CT')
            alarms[line['tag']] = dict([('load',False)]+[(k,line[k]) for k in ('tag','device','description','severity','receivers','formula')] )
        if write:
            devs = set(v['device'] for v in alarms.values())
            for d in devs:
                if d not in self.devices:
                    raise Exception('PyAlarm %s does not exist!'%d)
            [self.add(**v) for v in alarms.values()]
            self.load()
            [self.devices[d].init() for d in devs]
        return alarms

    def save_tag(self,tag):
        """ Shortcut to force alarm update in database """
        if tag not in self.keys(): raise Exception('TagNotFound')
        self[tag].write()
        
    def get_ds_proxy(self,dev):
        return self.servers.proxies[dev]
    
    def get_db_properties(self,ref,props):
        return self.servers.db.get_device_property(ref,props)
     
    def get_db_property(self,ref,prop):
        return self.get_db_properties(ref,[prop])[prop]
    
    def put_db_properties(self,ref,props):
        self.servers.db.put_device_property(ref,props)
        
    def put_db_property(self,ref,prop,value):
        self.put_db_properties(ref,{prop:[value]})
        
    def get_class_property(self,klass,prop):
        return self.servers.db.get_class_property(klass,[prop])[prop]
    
    def put_class_property(self,klass,prop,value):
        self.servers.db.put_class_property(klass,{prop:[value]})
        
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
            return ph
        else: return self.phonebook
        
    def parse_phonebook(self,receivers):
        result,receivers = [],[s.strip() for s in receivers.split(',')]
        for r in receivers:
            if r in self.phonebook: result.append(self.phonebook[r])
            else: result.append(r)
        return ','.join(result)

    def remove_from_phonebook(self, person):
        """ Removes a person from the phonebook """        
        prop = self.get_class_property('PyAlarm','Phonebook')
        new_prop = []
        for line in prop:
            l = line.split(':',1)[0]
            if l!=person:
                new_prop.append(line)
        self.save_phonebook(new_prop)

    def add_to_phonebook(self, person, section):
        """ Adds a person to the phonebook """
        prop = self.get_class_property('PyAlarm','Phonebook')
        new_prop = []
        flag=0
        for line in prop:
            l = line.split(':',1)[0]
            p = person.split(':',1)[0]
            if l==p:
                raise Exception('Person already exists in the database!')
        for line in prop:
            new_prop.append(line)
            if not line.find('#'):
                if line=='#'+section:
                    print(line)
                    new_prop.append(person)
        self.save_phonebook(new_prop)

    def change_in_phonebook(self, new):
        who = new.split(':',1)[0]
        prop = self.get_class_property('PyAlarm','Phonebook')
        new_prop = []
        for line in prop:
            l = line.split(':',1)[0]
            if l==who:
                new_prop.append(new)
            else:
                new_prop.append(line)
        #print(new_prop)l = ' 
        self.save_phonebook(new_prop)

    def save_phonebook(self, new_prop):
        """ Saves a new phonebook in the database """
        self.put_class_property('PyAlarm','Phonebook',new_prop)
        return new_prop

    def findChild(self, att):
        ##@todo : THIS METHOD SHOULD USE PARSE_ALARMS INSTEAD!
        #Gets variables from an string an attribute name, gets device and attribute and checks if it matches an existing alarm attribute
        parsed = fandango.TangoEval().parse_variables(att)
        print 'In findChild(%s): parsed variables are %s' % (att,parsed)
        if parsed and parsed[0]:
            path,variable = parsed[0][:2]
            if str(path+'/'+variable) in [a.device+'/'+a.tag for a in self.get()]:
                return True
        return False

    def children(self):
        """
        Children are those alarms that have no alarms below or have a higher alarm that depends from them.
        """ 
        print 'Getting Alarm children ...'
        result=[]
        for a,v in self.items():
            children = self.parse_alarms(v.formula)
            if children: 
                result.extend(children)
            else: 
                result.append(a)
        result = set(result)
        return [v for a,v in self.items() if a in result]

    def parse_alarms(self, formula):
        """
        Searches for alarm tags used in the formula
        """
        alnum = '(?:^|[^/a-zA-Z0-9-_])([a-zA-Z0-9-_]+)'#(?:$|[^/a-zA-Z0-9-_])' #It's redundant to check for the terminal character, re already does this
        var = re.findall(alnum,formula)
        #print '\tparse_alarms(%s): %s'%(formula,var)
        return [a for a in self.keys() if a in var]
        
    def replace_alarms(self, formula):
        """
        Replaces alarm tags by its equivalent device/alarm attributes
        """
        try:
            var = self.parse_alarms(formula)
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
                        
    def parse_variables(self, formula, replace = True):
        """ Returns all tango attributes that appear in a formula """
        if formula in self.alarms: formula = self.alarms[formula].formula
        formula = getattr(formula,'formula',formula)
        if not getattr(self,'_eval',None): self._eval = fandango.TangoEval()
        return self._eval.parse_variables(self.replace_alarms(formula) if replace else formula)

    def get(self,tag='',device='',attribute='',receiver='', severity=''):
        """ 
        Gets alarms matching the given filters (tag,device,attribute,receiver,severity) 
        """
        result=[]
        if tag and not tag.endswith('$'): tag+='$'
        if attribute and not attribute.endswith('$'): attribute+='$'
        if device and not device.endswith('$'): device+='$'
        #if receiver and not receiver.startswith('%'): receiver='%'+receiver
        if severity and not severity.endswith('$'): severity+='$'
        for k,alarm in self.alarms.items():
            if  ((not tag or fun.searchCl(tag,k)) and
                (not device or fun.searchCl(device,alarm.device)) and
                (not attribute or fun.searchCl(attribute,alarm.formula)) and
                (not receiver or receiver in alarm.receivers) and
                (not severity or fun.searchCl(severity,alarm.severity))):
                result.append(alarm)
        return result

    def filter_hierarchy(self, rel):
        """
        TOP are those alarms which state is evaluated using other Alarms values.
        BOTTOM are those alarms that have no alarms below or have a TOP alarm that depends from them.
        """ 
        print 'AlarmAPI.filter_hierarchy(%s)'%rel
        if rel=='TOP':
            #children = [c.tag for c in self.children()]
            result = [v for a,v in self.items() if self.parse_alarms(v.formula)]#a not in children]
        elif rel=='BOTTOM':
            result = self.children()
        else: result=self.values()
        return result

    def filter_severity(self, sev):
        print 'AlarmAPI.filter_severity(%s)'%sev
        result=[]
        for k,alarm in self.alarms.items():
            if sev=='WARNING':
                if(alarm.severity in ['WARNING', 'ALARM', 'ERROR']): result.append(alarm)
            elif sev=='ALARM':
                if(alarm.severity in ['ALARM', 'ERROR']): result.append(alarm)
            elif sev=='ERROR':
                if(alarm.severity=='ERROR'): result.append(alarm)
            else: result.append(alarm)
        return result

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
            result[alarm.tag].update((k,v) for k,v in self.devices[alarm.device].get_config().items() if k in ALARM_CYCLE+ALARM_ARCHIVE+ALARM_CONTROL)
        return result        

    def add(self,tag,device,formula='',description='',receivers='', severity='WARNING', load=True):
        """ Adds a new Alarm to the database """
        device = device.lower()
        if tag in self.keys(): raise Exception('TagAlreadyExists:%s'%tag)
        if device not in self.devices: raise Exception('DeviceDescriptiondDesntExist:%s'%device)
        alarm = Alarm(tag, api=self, device=device, formula=formula, description=description, receivers=receivers, severity=severity)
        alarm.write()
        self.setAlarmProperties(device, tag)
        if load: self.load()

    def setAlarmProperties(self, device, alarm):
        print 'In panic.setAlarmProperties(%s,%s)'%(device,alarm)
        props=self.devices[device].get_config(True)
        dictlist=[]
        for key, value in props.iteritems():
            temp = str(key)+'='+str(value[0] if fandango.isSequence(value) else value)
            print '%s.%s.%s'%(device,alarm,temp)
            dictlist.append(temp)
        l=';'.join(dictlist)
        l=str(alarm)+':'+l
        old_props=self.get_db_property(device, 'AlarmConfigurations')
        new_props=str(old_props).strip("]'[")+l+';'
        #return new_props
        try:
            self.put_device_property(device, 'AlarmConfigurations', new_props)
        except:
            Exception('Cant append the database!')

    def purge(self,device,tag,load=False):
        """
        Removes any alarm from a device matching the given tag.
        Database must be reloaded afterwards to update the alarm list.
        """
        props = self.devices[device].get_alarm_properties()
        self.put_db_properties(device,  {'AlarmList':[p for p in props['AlarmList'] if not p.startswith(tag+':')],
                                        'AlarmReceivers':[p for p in props['AlarmReceivers'] if not p.startswith(tag+':')],
                                        'AlarmDescriptions':[p for p in props['AlarmDescriptions'] if not p.startswith(tag+':')],
                                        'AlarmSeverities':[p for p in props['AlarmSeverities'] if not p.startswith(tag+':')],})
        self.devices[device].init()
        if load: self.load()
        return

    def remove(self,tag,load=True):
        """ Removes an alarm from the system. """
        if tag not in self.keys(): raise Exception('TagNotFound')
        val = self.alarms.pop(tag) #Order matters!
        self.purge(val.device,tag)
        if load: self.load()
        return val

    def rename(self,tag,new_tag='',new_device='',load=True):
        """ Renames an existing tag, it also allows to move to a new device. """
        new_device = new_device.lower()
        if new_device and new_device not in self.devices: raise Exception('DeviceDoesntExist:%s'%new_device)
        if tag not in self.keys(): raise Exception('TagNotFound:%s'%tag)
        alarm = self.remove(tag)
        new_device = new_device or alarm.device
        new_tag = new_tag or alarm.tag
        self.add(new_tag,new_device,alarm.formula,alarm.description,alarm.receivers,alarm.severity,load=load)
        return
        
    def update_servers(self,targets):
        """ Forces PyAlarm devices to reload selected alarms """
        devs = set((self[t].device if t in self.alarms else t) for t in targets)
        print 're-Initializing devices: %s'%devs
        [self.devices[d].init() for d in devs]

    def start_servers(self,tag='',device='',host=''):
        """ Starts Alarm Servers matching the filters """
        self.servers.start_servers(set(self.servers.get_device_server(a.device) for a in self.get_alarms(tag,device)),host=host)

    def stop_servers(self,tag='',device=''):
        """ Stops Alarm Servers matching the filters """
        self.servers.stop_servers(set(self.servers.get_device_server(a.device) for a in self.get_alarms(tag,device)))

    #def __getitem__(self,key): return self.alarms.__getitem__(key)
    #def __setitem__(self,key,value): return self.alarms.__setitem__(key,value)
    #def __iter__(self): return self.alarms.__iter__()
    #def keys(self): return self.alarms.keys()
    #def values(self): return self.alarms.values()
    #def items(self): return self.alarms.items()

    def __repr__(self): 
        #return '\n'.join(sorted('%s: %s' % (a.tag,a.description) for a in self.values()))
        return 'AlarmAPI(%s,%s,[%d])'%(self.filters,self.tango_host,len(self))

api = AlarmAPI 

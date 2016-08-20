import panic, sys, re, os, traceback, time
import PyTango, fandango, taurus, taurus.qt.qtgui.base
from PyQt4 import QtCore, QtGui, Qt
from taurus.core import TaurusEventType
from taurus.qt.qtgui.base import TaurusBaseComponent
from taurus.qt.qtgui.resource import getThemeIcon
from widgets import getAlarmTimestamp,trace,clean_str
#from htmlview import *

REFRESH_TIME = 10000
DEVICE_TIMEOUT = 250

class AlarmRow(QtGui.QListWidgetItem,TaurusBaseComponent):
    ALL_ROWS = {}
    MAX_ERRORS = 3
    TAG_SIZE = 45
    DATE_SIZE = len('Thu May 24 13:29:50 2012')
    
    def __init__(self,api,qtparent,tauparent=None):
        QtGui.QListWidgetItem.__init__(self)
        TaurusBaseComponent.__init__(self,tauparent)
        self.api = api
        self.qtparent = qtparent
        self.alarm = None
        self.alarmDisabled = None
        self.alarmAcknowledged = None
        self.font=QtGui.QFont(QtCore.QString("Courier"))
        self.font.setPointSize(10)
        self.setFont(self.font)
        self.errors = 0
        self.status = ''
        self.changed = False #This flag should be kept until updateStyle is called!!!
        
        self.quality = None
        self.setTextAlignment(Qt.Qt.AlignLeft)

    def __repr__(self):
        if self.alarm:
          return 'AlarmRow(%s):active=%s;quality=%s;errors=%s'%(self.alarm.tag,self.alarm.active,self.quality,self.errors)
        else:
          return 'AlarmRow(): not initialized'

    def setAlarmModel(self,alarm_object,use_list=True):
        """
        That's the place where you tell taurus to send the events to that object
        """
        #print 'AlarmRow(%s).setAlarmModel(%s)'%(self.getModel(),alarm_object)
        self.device = alarm_object.device
        self.use_list = use_list
        self.setModel(None)
        if use_list: self.model = alarm_object.device+'/'+'ActiveAlarms' 
        else: self.model = alarm_object.device+'/'+alarm_object.get_attribute()
        #print'In AlarmRow(%s).setModel(%s,use_list=%s)'%(alarm_object.tag, self.model,use_list)
        
        self.alarm = alarm_object
        self.tag = alarm_object.tag
        self.alarm.counter = -1
        self.errors = 0
        self.alarm.active = None
        self.quality = None
        AlarmRow.ALL_ROWS[str(self.tag).lower()] = self
        self.setText('  '+self.get_tag_text()+' - loading ...')
        try: taurus.Device(alarm_object.device).set_timeout_millis(DEVICE_TIMEOUT)
        except: print(fandango.log.except2str())
        self.setModel(self.model)
        taurus.Attribute(self.model).changePollingPeriod(REFRESH_TIME)

    def get_alarm_tag(self):
        return self.tag
    
    def get_tag_text(self):
        return ('%'+'%d'%self.TAG_SIZE+'s')%self.alarm.tag[:self.TAG_SIZE]

    def get_alarm_object(self):
        return self.qtparent.api[self.tag]

    def get_acknowledged(self,force=False):
        val = None
        try:
            if not force and self.use_list: 
                if not getattr(self,'ack_attr',None):
                    self.ack_attr = taurus.Attribute(self.device+'/AcknowledgedAlarms')
                    self.ack_attr.changePollingPeriod(REFRESH_TIME)
                val = any([a==self.alarm.tag for a in (self.ack_attr.read().value or [])])
            else: 
                val = taurus.Device(self.alarm.device).command_inout('CheckAcknowledged',self.alarm.tag)
                if force: 
                    self.alarmAcknowledged = val
        except:
            print fandango.log.except2str()
        #print 'In AlarmRow(%s).get_acknowledged(): %s'%(self.alarm.tag,val)
        return val
        
    def get_disabled(self,force=False):
        val = None
        try:
            if not force and self.use_list: 
                if not getattr(self,'dis_attr',None):
                    self.dis_attr = taurus.Attribute(self.device+'/DisabledAlarms')
                    self.dis_attr.changePollingPeriod(REFRESH_TIME)
                val = any(re.split('[: ,;]',a)[0]==self.alarm.tag for a in (self.dis_attr.read().value or []))
            else: 
                val = taurus.Device(self.alarm.device).command_inout('CheckDisabled',self.alarm.tag)
                if force: self.alarmDisabled = val
        except:
            print fandango.log.except2str()
        #print 'In AlarmRow(%s).get_disabled(): %s'%(self.alarm.tag,val)
        return val
        
    def get_alarm_time(self, alarm=None, attr_value=None, null = float('nan')):
        alarm = alarm or self.alarm
        try:
            if not self.alarm.active:
                self.alarm.active = getAlarmTimestamp(alarm)
            #print 'AlarmRow(%s).get_alarm_date(%s)'%(alarm.tag,alarm.active)
            return self.alarm.active if self.alarm.active else 0
        except:
            print traceback.format_exc()
        return fandango.END_OF_TIME if self.alarm.active else 0
        
    def get_alarm_date(self, alarm=None, attr_value=None, null = ' NaN '):
        try:
            return ('%'+str(self.DATE_SIZE)+'s')%fandango.time2str(self.get_alarm_time(alarm,attr_value))
        except:
            print traceback.format_exc()
            return str(null)
            
    def eventReceived(self,evt_src,evt_type,evt_value):
        try:
            debug = 'debug' in str(evt_src).lower()
            now = fandango.time2str()
            evtype = str(TaurusEventType.reverseLookup[evt_type])
            evvalue = getattr(evt_value,'value',None)
            if debug: 
                print '\n'
                #trace('%s: In AlarmRow(%s).eventReceived(%s,%s,%s)'%(fandango.time2str(),self.alarm.tag,evt_src,evtype,evvalue),clean=True)
            disabled,acknowledged,quality,value = self.alarmDisabled,self.alarmAcknowledged,self.quality,bool(self.alarm.active)
            if self.qtparent and getattr(self.qtparent,'api',None): self.alarm = self.qtparent.api[self.tag] #Using common api object
            
            #Ignoring Config Events
            if evt_type==TaurusEventType.Config:
                if debug: trace('%s: AlarmRow(%s).eventReceived(CONFIG): %s' % (now,self.alarm.tag,str(evt_value)[:20]),clean=True)
                return
            #Filtering Error Events
            elif evt_type==TaurusEventType.Error or not hasattr(evt_value,'value'):
                error = True
                self.errors+=1
                if self.errors>=self.MAX_ERRORS: 
                    self.alarm.active,self.quality = None,PyTango.AttrQuality.ATTR_INVALID
                if not self.errors%self.MAX_ERRORS:
                    if 'EventConsumer' not in str(evt_value): 
                        trace('%s: AlarmRow(%s).eventReceived(ERROR): %s' %(now,self.alarm.tag,'ERRORS=%s!:\n\t%s'%(self.errors,fandango.except2str(evt_value,80))),clean=True)
                    #if self.value is None: taurus.Attribute(self.model).changePollingPeriod(5*REFRESH_TIME)
                    if not self.changed and self.errors==self.MAX_ERRORS or 'Exception' not in self.status: 
                        print '%s : %s.emitValueChanged(ERROR!)'%(now,self.alarm.tag)
                        print 'ERROR: %s(%s)' % (type(evt_value),clean_str(evt_value))
                        self.qtparent.emitValueChanged()
                        self.changed = True #This flag is set here, and set to False after updating row style
                        self.updateStyle(event=True,error=fandango.except2str(evt_value)) #It seems necessary to update the row text, color and icon
                else: 
                    if debug: trace('In AlarmRow(%s).eventReceived(%s,%s,%d/%d)' % (self.alarm.tag,evt_src,evtype,self.errors,self.MAX_ERRORS),clean=True)
                    pass
            #Change Events
            elif evt_type==TaurusEventType.Change or evt_type==TaurusEventType.Periodic:
                self.errors = 0
                
                # Refresh period not changed as these lines slows down a lot!!
                #ta = taurus.Attribute(self.model)
                #if self.value is None: ta.changePollingPeriod(5*REFRESH_TIME)
                #elif ta.getPollingPeriod()!=REFRESH_TIME: ta.changePollingPeriod(REFRESH_TIME)
                
                disabled = self.get_disabled()
                acknowledged = self.get_acknowledged()
                if str(self.model).endswith('/ActiveAlarms'):
                    value,quality = any(s.startswith(self.alarm.tag+':') for s in (evt_value.value or [])),self.alarm.get_quality()
                else:
                    value,quality = evt_value.value,evt_value.quality
                
                if debug: trace('In AlarmRow(%s).eventReceived(%s,%s,%s)' % (self.alarm.tag,evt_src,str(TaurusEventType.reverseLookup[evt_type]),evvalue),clean=True)
                if debug: trace('\t%s (%s), dis:%s, ack:%s'%(value,quality,disabled,acknowledged))
                
                if  value!=bool(self.alarm.active) or quality!=self.quality or disabled!=self.alarmDisabled or acknowledged!=self.alarmAcknowledged:
                    if not self.changed: 
                        #print '%s : %s.emitValueChanged(%s)'%(fandango.time2str(),self.alarm.tag,value)
                        self.qtparent.emitValueChanged()
                    self.changed = True #This flag is set here, and set to False after updating row style
                
                self.alarmDisabled = disabled
                self.alarmAcknowledged = acknowledged
                self.quality = quality
                self.alarm.active = getAlarmTimestamp(self.alarm) if value else 0
                
                self.updateStyle(event=True,error=False)
            else: 
                print '\tUnknown event type?!? %s' % evt_type
        except:
            try: print 'Exception in eventReceived(%s,...): \n%s' %(evt_src,fandango.log.except2str())
            except : print 'eventReceived(...)!'*80+'\n'+traceback.format_exc()
        if debug: print '\n'
            
    def updateIfChanged(self):
        if self.changed:
            print 'AlarmRow(%s).updateIfChanged(changed=True)'%(self.alarm.tag)
            self.updateStyle(event=True,error=self.errors>self.MAX_ERRORS)
            self.changed = False

    def updateStyle(self,event=False,error=False):
        #trace('%s -> AlarmRow(%s).updateStyle(event=%s)'%(time.ctime(),self.alarm.tag,event),clean=True)
        if getattr(self.qtparent,'_attributesSignalsBlocked',False):
            #print '\tupdateStyle(): blocked!'
            return
        if event:
            try:
                self.font=QtGui.QFont(QtCore.QString("Courier"))
                self.font.setPointSize(10)
                if error:
                    if self.errors>=self.MAX_ERRORS and not self.errors%self.MAX_ERRORS:
                        self.was_ok = self.alarm.active or self.alarm.recovered
                        self.alarm.active,self.alarm.recovered,self.alarm.counter = 0,0,0
                        self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,None,False,QtGui.QColor("grey").light(),QtGui.QColor("white"))
                        if self.was_ok:
                            self.font.setBold(False)
                        error_text = clean_str(error if isinstance(error,basestring) else 'disabled').split('=',1)[-1].strip()[:40]
                        self.setText('   '+' - '.join((self.get_tag_text(),error_text)))
                        self.status = 'Exception received, check device %s'%self.alarm.device
                elif self.alarm.active is None:
                    #trace('updateStyle(%s): value not received yet' %(self.alarm.tag),clean=True)
                    pass
                else:
                    #trace('Event Received: %s = %s' %(self.alarm.tag,self.value),clean=True)
                    if self.alarm.active and not self.alarmDisabled:
                        if self.quality==PyTango.AttrQuality.ATTR_ALARM:
                            if self.alarmAcknowledged:
                                self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"media-playback-pause",False,QtGui.QColor("black"),QtGui.QColor("red").lighter())
                            else:
                                self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"software-update-urgent",False,QtGui.QColor("black"),QtGui.QColor("red").lighter())
                        elif self.quality==PyTango.AttrQuality.ATTR_WARNING:
                            if self.alarmAcknowledged:
                                self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"media-playback-pause",False,QtGui.QColor("black"),QtGui.QColor("orange").lighter())
                            else:
                                self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"emblem-important",False,QtGui.QColor("black"),QtGui.QColor("orange").lighter())
                        elif self.quality==PyTango.AttrQuality.ATTR_VALID:
                            if self.alarmAcknowledged:
                                self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"media-playback-pause",False,QtGui.QColor("black"),QtGui.QColor("yellow").lighter())
                            else:
                                self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"applications-development",False,QtGui.QColor("black"),QtGui.QColor("yellow").lighter())
                        else: 
                            print '\tUnknown event quality?!? %s' % self.quality
                            
                        if self.alarm.counter<2:
                            self.font.setBold(True)
                        self.alarm.recovered,self.alarm.counter = 0,2

                        #else: self.font.SetBold(False) #Good to keep it, to see what changed
                        self.status = 'Alarm Acknowledged, no more messages will be sent' if self.alarmAcknowledged else 'Alarm is ACTIVE'
                        self.setText(' | '.join((self.get_tag_text(),self.get_alarm_date(), self.alarm.description)))
                        #self.setText('%45s | %30s'%(str(self.alarm.tag)[:45], self.get_alarm_date(), self.alarm.description))

                    elif self.alarm.active in (False,0) and not self.alarmDisabled:
                        if self.alarmAcknowledged:
                            self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"media-playback-pause",False,QtGui.QColor("green").lighter(),QtGui.QColor("white"))
                        else:
                            self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"emblem-system",False,QtGui.QColor("green").lighter(),QtGui.QColor("white"))
                        if not self.alarm.recovered:
                            #trace('\teventReceived(%s): %s => %s' %(self.alarm.tag,self.alarm.active,self.value),clean=True)
                            if self.alarm.counter>1: 
                                self.font.setBold(True)
                            self.alarm.active,self.alarm.recovered,self.alarm.counter = 0,time.time(),1
                        #else: self.font.SetBold(False) #Good to keep it, to see what changed
                        self.status = 'Alarm has NOT been triggered'
                        self.setText(' - '.join((self.get_tag_text(),'Not triggered')))

                    else: #AlarmDisabled or value = None
                        self.status = 'Alarm is Disabled, status will not be updated'
                        self.qtparent.emit(QtCore.SIGNAL('setfontsandcolors'),self.tag,"dialog-error",False,QtGui.QColor("black"),QtGui.QColor("grey").lighter())
                        
                    #if self.qtparent.USE_EVENT_REFRESH: 
                self.setToolTip('\n'.join([
                    self.status,'',
                    'Severity: '+self.alarm.severity,
                    'Formula: '+self.alarm.formula,
                    'Description: %s'%self.alarm.description,
                    'Alarm Device: %s'%self.alarm.device,
                    'Archived: %s'%('Yes' if 'SNAP' in self.alarm.receivers else 'No'),
                    ]))
                self.setFont(self.font)
            except:
                print 'Exception in updateStyle(%s,...): \n%s' %(self.alarm.tag,traceback.format_exc())
        else:
            for klass in type(self).__bases__:
                try: 
                    if hasattr(klass,'updateStyle'): klass.updateStyle(self)
                except: pass
        pass
            
    @classmethod
    def setFontsAndColors(klass,tag,icon,bold,color,background):
        #print 'setFontsAndColors(%s,%s,%s,%s,%s)'%(tag,icon,bold,color.name(),background.name())
        tag = str(tag).lower()
        if tag in klass.ALL_ROWS:
            self = klass.ALL_ROWS[tag]
            self.alarmIcon=getThemeIcon(icon) if icon else None
            self.setIcon(self.alarmIcon or Qt.QIcon())
            self.font.setBold(bold)
            self.setTextColor(color)
            self.setBackgroundColor(background)
        else:
            print 'Tag %s is not in the list of AlarmRows: %s' % (tag,klass.ALL_ROWS.keys())

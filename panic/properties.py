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

__doc__ = """
=================================
PyAlarm Device Default Properties
=================================
"""

from fandango.functional import join,djoin
from fandango.tango import PyTango

__doc__+="""
PANIC_PROPERTIES: This properties will be shared by the whole TANGO_HOST
"""
PANIC_PROPERTIES = {
    'PhoneBook':
        [PyTango.DevVarStringArray,
        "List of receiver aliases, declared like:\n\
        \t%USER:user@accelerator.es;SMS:+34666555666",
        [] ],
    'SMSConfig':
        [PyTango.DevString,
        "Arguments for sendSMS command",
        [ ":" ] ],
    'FromAddress':
        [PyTango.DevString,
        "Address that will appear as Sender in mail and SMS",
        [ "oncall" ] ],
    'AllowedActions':
        [PyTango.DevVarStringArray,
        "List of OS commands that alarms are able to execute.",
        [] ],
    'StartupDelay':
        [PyTango.DevLong,
        "Number of seconds that PyAlarm will wait before starting to evaluate alarms.",
        [ 0 ] ],
    'PanicAdminUsers':
        [PyTango.DevVarStringArray,
        "Users authorized to modify the Alarms (apart of receivers) ",
        [ ] ],
    'PanicUserTimeout':
        [PyTango.DevLong,
         "Number of seconds to keep user login in panic GUI",
         [ 60 ] ],
    'UserValidator':
        [PyTango.DevString,
         "Module.Class to be used to validate admin user/passwords.",
         [ ] ],
    'GlobalReceivers':
        [PyTango.DevVarStringArray,
        "Receivers to be applied globally to all alarms\n\
        Declared as FILTER:receiver,ACTION(MESSAGE:...) like\n\
        \t*VC*:vacuum@cells.es,ACTION(RESET:command,t/t/t/stop)",
        [ 0 ] ],
    }

__doc__+="""
ALARM_TABLES: Properties used to store Alarms declaration in Panic<=6

  This properties will be managed by API; DON'T ACCESS THEM WITH self.$Property from the device
  
"""
ALARM_TABLES = {
    'AlarmList':
        [PyTango.DevVarStringArray,
        "List of alarms to be monitorized. The format is:\n<br>domain/family/member #It simply checks that dev is alive\n<br>domain/family/member/attribute > VALUE\n<br>domain/family/member/State == UNKNOWN\n<br>domain/family/*/Temperature > VALUE\n<br>\n<br>When using wildcards all slash / must be included",
        [] ],
    'AlarmReceivers':
        [PyTango.DevVarStringArray,
        "Users that will be notified for each alarm. The format is:\n<br>[TYPE]:[ADDRESS]:[attributes];...\n<br>\n<br>[TYPE]: MAIL / SMS\n<br>[ADDRESS] : operator@accelerator.es / +34666555444\n<br>[attributes]: domain/family/member/attribute;domain/family/*",
        [] ],
    'AlarmDescriptions':
        [PyTango.DevVarStringArray,
        "Description to be included in emails for each alarm. The format is:\n<br>TAG:AlarmDescription...",
        [] ],
    'AlarmConfigurations':
        [PyTango.DevVarStringArray,
        "Configuration customization appliable to each alarm. The format is:\n<br>TAG:PAR1=Value1;PAR2=Value2;...",
        [] ],
    'AlarmSeverities':
        [PyTango.DevVarStringArray,
        "ALARM:DEBUG/INFO/WARNING/ERROR #DEBUG alarms will not trigger messages",
        [] ],
    }

__doc__+="""
ALARM_CYCLE: Properties to manage the timing of Alarm stages
"""
ALARM_CYCLE = {
    'Enabled':
        [PyTango.DevString,
        "If False forces the device to Disabled state and avoids messaging; if INT then it will last only for N seconds after Startup; if a python formula is written it will be used to enable/disable the device",
        [ '120' ] ],#Overriden by panic.DefaultPyAlarmProperties
    'AlarmThreshold':
        [PyTango.DevLong,
        "Min number of consecutive Events/Pollings that must trigger an Alarm.",
        [ 3 ] ],
    'AlertOnRecovery':
        [PyTango.DevString,
        "It can contain 'email' and/or 'sms' keywords to specify if an automatic message must be sent in case of alarm returning to safe level.",
        [ "false" ] ],
    'PollingPeriod':
        [PyTango.DevFloat,
        "Period in SECONDS in which all attributes not event-driven will be polled.\n \
        @TODO for convenience any value above 300 will be divided by 1000, @DEPRECATE",
        [ 15. ] ],
    'Reminder':
        [PyTango.DevLong,
        "If a number of seconds is set, a reminder mail will be sent while the alarm is still active, if 0 no Reminder will be sent.",
        [ 0 ] ],
    'AutoReset':
        [PyTango.DevFloat,
        "If a number of seconds is set, the alarm will reset if the conditions are no longer active after the given interval.",
        [ 3600. ] ],
    'RethrowState':
        [PyTango.DevBoolean,
        "Whether exceptions in State reading will activate the Alarm.",
        [ True ] ],
    'RethrowAttribute':
        [PyTango.DevBoolean,
        "Whether exceptions in Attribute reading will activate the Alarm.",
        [ False ] ],
    'IgnoreExceptions':
        [PyTango.DevString,
        "Value can be False/True/NaN to return Exception, None or NotANumber in case of read_attribute exception.",
        [ 'True' ] ],#Overriden by panic.DefaultPyAlarmProperties
    }
        
__doc__+="""
ALARM_ARCHIVE: Properties to manage the saving of Alarms
"""
ALARM_ARCHIVE = {
    'UseSnap':
        [PyTango.DevBoolean,
        "If false no snapshots will be trigered (unless specifically added to receivers)",
        [ True ] ],
    'CreateNewContexts':
        [PyTango.DevBoolean,
        "It enables PyAlarm to create new contexts for alarms if no matching context exists in the database.",
        [ False ] ],
    }

__doc__+="""
ALARM_LOGS: Properties to manage the logging of Alarms
"""
ALARM_LOGS = {
    'LogFile':
        [PyTango.DevString,
        """File where alarms are logged, like /tmp/alarm_$NAME.log\n
        Keywords are $DEVICE,$ALARM,$NAME,$DATE\n
        From version 6.0 a FolderDS-like device can be used for remote logging:\n
        \ttango://test/folder/01/$ALARM_$DATE.log""",
        [ "" ] ], 
    'HtmlFolder':
        [PyTango.DevString,
        "File where alarm reports are saved",
        [ "htmlreports" ] ],
    'FlagFile':
        [PyTango.DevString,
        "File where a 1 or 0 value will be written depending if theres active alarms or not.\n<br>This file can be used by other notification systems.",
        [ "/tmp/alarm_ds.nagios" ] ],
    'MaxMessagesPerAlarm':
        [PyTango.DevLong,
        "Max Number of messages to be sent each time that an Alarm is activated/recovered/reset.",
        [ 0 ] ],
    'FromAddress':
        [PyTango.DevString,
        "Address that will appear as Sender in mail and SMS",
        [ "oncall" ] ],
    }
    
__doc__+="""
DEVICE_CONFIG: PyAlarm/PanicDS instance configuration.
"""    
DEVICE_CONFIG = {
    'VersionNumber':
        [PyTango.DevString,
         "API version used (device-managed)",
         [ "?.?" ] ],
    'LogLevel':
        [PyTango.DevString,
        "stdout log filter",
        [ "INFO" ] ],
    'SMSConfig':
        [PyTango.DevString,
        "Arguments for sendSMS command",
        [ ":" ] ],
    'StartupDelay':
        [PyTango.DevLong,
        "Number of seconds that PyAlarm will wait before starting.",
        [ 0 ] ],
    'EvalTimeout':
        [PyTango.DevLong,
        "Timeout for read_attribute calls, in milliseconds .",
        [ 500 ] ],
    'UseProcess':
        [PyTango.DevBoolean,
        "To create new OS processes instead of threads.",
        [ False ] ],
    'UseTaurus':
        [PyTango.DevBoolean,
        "Use Taurus to connect to devices instead of plain PyTango.",
        [ False ] ],
    }
        
TODO_LIST = {
    'PushEvents':
        [PyTango.DevVarStringArray,
         "Events to be pushed by Alarm and AlarmLists attributes",
         [] ] ,
    }
    
PyAlarmDefaultProperties = dict(join(d.items() for d in (ALARM_CYCLE,ALARM_ARCHIVE,ALARM_LOGS,DEVICE_CONFIG)))
DEVICE_PROPERTIES = dict(join(v.items() for v in (PyAlarmDefaultProperties,ALARM_TABLES)))
ALARM_CONFIG = ALARM_CYCLE.keys()+ALARM_ARCHIVE.keys()+ALARM_LOGS.keys()+DEVICE_CONFIG.keys()

ALARM_SEVERITIES = ['ERROR','ALARM','WARNING','DEBUG']

try:
    from fandango.doc import get_fn_autodoc
    __doc__ = get_fn_autodoc(__name__,vars(),
        module_vars=['PANIC_PROPERTIES','DEVICE_CONFIG','ALARM_LOGS',
                     'ALARM_CYCLE','ALARM_TABLES','ALARM_ARCHIVE'])
except:
    import traceback
    traceback.print_exc()

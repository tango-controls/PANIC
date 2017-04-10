====================================
PANIC Receivers, Logging and Actions
====================================

.. contents::

Alarm Receivers
---------------

Allowed receivers are email, sms, action and shell commands.

Global Receivers
----------------

The PyAlarm class property "GlobalReceivers" allows to set receivers that 
will be applied to all Alarms; independently of the device that is managing them.

The syntax is::

  GlobalReceivers
    {regexp}:{receivers}
    .*:oncall@facility.dom
    
Logging
-------

Alarm logging can be managed in three ways: local logs, remote logs via FolderDS or Snapshoting.

All the logging methods support defined variables ($ALARM, $DATE, $DEVICE, $MESSAGE, $VALUES, $...)

Local LogFile
.............

Simply set the LogFile property to your preferred local file path::

  LogFile = /tmp/pyalarm/$NAME_$DATE_$MESSAGE.log

Remote LogFile
..............

You can use the fandango.FolderDS device to specify a remote logfile destination on the LogFile property::

  # LogFile = tango://[folderds/device/name]/[logfile_name]
  LogFile = tango://sys/folder/panic-logs/$NAME_$DATE_$MESSAGE.log
  
You can have both local and remote logging by setting LogFile to a local file and adding an ACTION receiver::

  LogFile = /tmp/pyalarm/$NAME_$DATE_$MESSAGE.log
  
  AlarmReceivers = ACTION(alarm:command,controls02:10000/test/folder/tmp-folderds/SaveText,
                             '$NAME_$DATE_$MESSAGE.txt','$REPORT')

FolderDS documentation: https://github.com/tango-controls/fandango/blob/documentation/doc/devices/FolderDS.rst

Using SNAP database
...................

This database logging will save the alarm state and all associated attributes every time that the alarm is activated/reset.

You should have configured previously an Snapshoting Database (java/mysql service by Soleil).

Then you have to:

 * Set the CreateNewContexts property of PyAlarm to True (it will automatically create a new context on alarm triggering)
 * Or create manually a new context in the database using Bensikin.
 * Set UseSnap=True to trigger snapshots for all alarms 
 * Or simply add the SNAP receiver.
 
Creating a context manually instead of doing it with PyAlarm may allow you to store Tango attributes that do not appear in the formula, thus enabling a sort of alarm-triggered archiving mode.


Triggering Actions from PyAlarm
-------------------------------

See basic details on the user guide:

  https://github.com/tango-controls/PANIC/blob/documentation/doc/PyAlarmUserGuide.rst#id20
  
Here you have some more examples:

.. code::

  # Send an email (equivalent to just %MAIL:address@mail.com)
  %SENDMAIL:ACTION(alarm:command,lab/ct/alarms/SendMail,$DESCRIPTION,$ALARM,address@mail.com)
  
  # Reset another alarm, DONT USE [] TO CONTAIN ARGUMENTS!
  %RESET:ACTION(alarm:command,test/pyalarm/logfile/resetalarm,'TEST','$NAME_$DATE_$DESCRIPTION')
  
  # Reload another device
  %INITLOG:ACTION(alarm:command,test/pyalarm/logfile/init)
  
  # Write a tango attribute
  %WRITE:ACTION(alarm:attribute,sys/tg_test/1/string_scalar,'$NAME_$DATE_$VALUES')
  
  # Execute a command in another tango host
  # in this example a FolderDS saves the alarm log
  %LOG:ACTION(alarm:command,controls02:10000/test/folder/tmp-folderds/SaveText,'$NAME_$DATE_$MESSAGE.txt','$REPORT')

Then declare the AlarmReceivers like::

  ACTION(alarm:command,mach/dummy/motor/move,int(1),int(10))
  ACTION(reset:attribute,mach/dummy/motor/position,int(0)) 
  
The first field is one of each PyAlarm.MESSAGE_TYPES::

  ALARM
  ACKNOWLEDGED
  RECOVERED
  REMINDER
  AUTORESET
  RESET
  DISABLED

Available keywords (managed by PyAlarm.parse_devices()) in ACTION are::

  $TAG / $NAME / $ALARM
  $DEVICE
  $DATE / $DATETIME
  $MESSAGE
  $VALUES
  $REPORT
  $DESCRIPTION

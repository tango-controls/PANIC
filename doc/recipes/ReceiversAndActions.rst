===========================
PANIC Receivers and Actions
===========================

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

Triggering Actions from PyAlarm
===============================

See basic details on the user guide:

  https://github.com/tango-controls/PANIC/blob/documentation/doc/PyAlarmUserGuide.rst#id20
  
Here you have some more examples:

.. code::

  %SENDMAIL:ACTION(alarm:command,lab/ct/alarms/SendMail,$DESCRIPTION,$ALARM,srubio@cells.es)
  %RESET:ACTION(alarm:command,test/pyalarm/logfile/resetalarm,'TEST','$NAME_$DATE_$DESCRIPTION') #DONT USE [] TO CONTAIN ARGUMENTS!
  %INIT:ACTION(alarm:command,test/pyalarm/sim/init)  
  %INITLOG:ACTION(alarm:command,test/pyalarm/logfile/init)
  %WRITE:ACTION(alarm:attribute,sys/tg_test/1/string_scalar,'$NAME_$DATE_$VALUES')
  %LOG:ACTION(alarm:command,controls02:10000/test/folder/tmp-folderds/SaveText,'$NAME_$DATE_$MESSAGE.txt','$REPORT')
  
Then declare the AlarmReceivers like:

 

Available keywords are:

  $TAG / $NAME
  $DEVICE
  $DATE
  +
  $MESSAGE
  $VALUES
  $DATETIME
  $ALARM
  $REPORT
  $DESCRIPTION

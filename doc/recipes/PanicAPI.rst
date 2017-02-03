==========================
Using the PANIC python API
==========================

.. contents::

The Panic Module
----------------

Panic contains the python AlarmAPI for managing the PyAlarm device servers from a client application or a python shell. The panic module is part of the Panic bliss package.::

  import panic
  alarms = panic.api()

Browsing existing alarms
------------------------

The AlarmAPI is a dictionary-like object containing Alarm objects for each registered Alarm tag. In addition the AlarmAPI.get method allows caseless search by tag, device, attribute or receiver::

  alarms.get(self, tag='', device='', attribute='', receiver='')

  alarms.get(device='boreas')
  Out[232]: 
   [Alarm(BL29-BOREAS_STOP:The BakeOut controller has been stop),
   Alarm(BL29-BOREAS_PRESSURE_1:),
   Alarm(BL29-BOREAS_PRESSURE_2:),
   Alarm(BL29-BOREAS_START: BL29-BOREAS bakeout started 
   ...]

  alarms.get(receiver='eshraq')
  Out[234]: 
   [Alarm(RF_LOST_EUROTHERM:),
   Alarm(OVEN_COMMS_FAILED:Oven temperatures not updated in the last 5 minutes),
   Alarm(RF_PRESSURE:The pressure in the cavity exceeds Range),
   Alarm(OVEN_TEMPERATURE:The Temperature of the Oven exceeds Range),
   Alarm(RF_EUROTHERM:),
   Alarm(RF_LOST_MKS:),
   Alarm(RF_TEMPERATURE_MAX2:),
   ...]

  alarms['RF_LOST_MKS'].receivers
  Out[237]: '%SRUBIO,%ESHRAQ,%VACUUM,%LOTHAR,%JNAVARRO'

Adding / Removing alarms
------------------------

The add/remove methods take care of properties modification::

  alarms.add('RF_ON_FIRE','rf/ct/alarms',formula='rf/ct/plc-01/temperature>1000.',message='FIRE!',receivers='rf@cells.es,plc@cells.es')

  alarms.remove('RF_ON_FIRE')

Modifying alarms
----------------

Each Alarm object contains strings with its configuration, if you modify it you must call Alarm.write() method to update the alarm device. An Alarm.rename() method is also available.

  In [235]: alarms['RF_LOST_MKS'].device
  Out[235]: 'sr/rf/alarms'

  In [236]: alarms['RF_LOST_MKS'].formula
  Out[236]: 'SR/RF/VGCT-01/State==UNKNOWN or SR/RF/VGCT-02/State==UNKNOWN'

  In [237]: alarms['RF_LOST_MKS'].receivers
  Out[237]: '%SRUBIO,%ESHRAQ,%VACUUM,%LOTHAR,%JNAVARRO'

  In [238]: alarms['RF_LOST_MKS'].write()

Modifying a receiver in all alarms
----------------------------------

And a fast way for updating alarm receivers::

  [a.replace_receiver('%DFERNANDEZ','%SRUBIO') for a in alarms.get(receiver='fernandez')]


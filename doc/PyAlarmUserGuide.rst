================================
PyAlarm Device Server User Guide
================================

--------------------------------------------------------------------------------------------------------

.. contents::

Description
===========

This device server is used as a alarm logger, it connects to the list of attributes provided and verifies its values.

Its focused on notifying Alarms by log files, Mail, SMS and (some day in the future) electronic logbook.

You can acknowledge these alarms by a proper command.

Internal Structure
==================

The device server behaviour relies on three python objects: AlarmAPI, updateAlarms thread and TangoEval.

Each alarm is independent in terms of formula and receivers; but all alarms within the same PyAlarm device
will share a common evaluation environment determined by PyAlarm properties.

The AlarmAPI
------------

This object encapsulates the access to the alarm configurations database. 
Tango Database is used by default, all alarm configurations are stored as device properties 
of each declared PyAlarm device (AlarmList, AlarmReceivers, AlarmSeverities).

The api object allows to load alarms, reconfigure them and transparently move Alarms between PyAlarm devices.

The updateAlarms thread
-----------------------

This thread will be executed periodically at a rate specified by the PollingPeriod.
All Enabled alarms will be evaluated at each cycle; and if evaluated to a True value (understood as any value not in (0,"",None,False,[],{})).

Once an Alarm has been active by a number of cycles equal to the device AlarmThreshold it will become Active. 
Then the PyAlarm will process all elements of the AlarmReceivers list.

The TangoEval engine
--------------------

This engine will automatically replace each Tango attribute name in the formula by its value. 
It will also provide several methods for searching attribute names in the tango database.

Amongst other features, all values are kept in a cache with a depth equal to the AlarmThreshold+1. 
This cache allows to create alarms using .delta or inspecting the cache for specific behaviors.


Alarm Syntax Recipes
====================

Alarms are parsed and evaluated using *fandango.TangoEval* class.

Sending a Test Message at Startup
---------------------------------

This alarm formula is just "True" ; therefore will be enabled immediately sendin an email message to test@tester.com

.. code-block:: python

   AlarmList -> DEBUG:True
   AlarmDescriptions -> DEBUG:The PyAlarm Device $NAME has been restarted
   AlarmReceivers -> DEBUG: test@tester.com

Testing a device availability
-----------------------------

It is done if you put directly the name of the device or its State as a condition by itself. In the second case and alarm will be triggered either if the Pressure is above threshold or the device is not reachable.

.. code-block:: python

   PRESSURE:SR/VC/VGCT/Pressure > 1e-4
   STATE_AND_PRESSURE:?SR/VC/VGCT and SR/VC/VGCT/Pressure > 1e-4


Getting Tango state/attribute/value/quality/time/delta in formulas
------------------------------------------------------------------

The Alarm syntax allows to add the following clauses to the attribute name (value returned by default):

.. code-block:: python

   some/device/name{/attribute}{.value/all/time/quality/delta/exception} 

*attribute*: if no attribute name is given, then device state is read.

.. code-block:: python

   PLC_Alarm: BL22/CT/EPS-PLC-01 == FAULT

*value*: default, returns the value of the attribute

.. code-block:: python

   Pressure_Alarm: BL22/CT/EPS-PLC-01/CC1_AF.value > 1e-5

*time*: returns the epoch in seconds of the last value read

.. code-block:: python

   Not_Updated: BL22/CT/EPS-PLC-01/CPU_Status.time < (now-60)

*quality* : returns the tango quality value (ATTR_VALID, ATTR_INVALID, ATTR_WARNING, ATTR_ALARM).

.. code-block:: python

   Temperature_Alarm: BL22/CT/EPS-PLC-01/OP_WBAT_OH01_01_TC11.quality == ATTR_ALARM

*delta* : returns the variation of the value in the last N=AlarmThreshold reads (stored in TangoEval.cache array of size AlarmThreshold+1)

.. code-block:: python

   Valve_Just_Closed: BL22/CT/EPS-PLC-01/VALVE_11.delta == -1

*exception* : True if the attribute is unreadable, False otherwise

.. code-block:: python

   Not_Found: BL22/CT/EPS-PLC-01/I_Dont_Exist.exception

*all* : returns the raw attribute object as returned by PyTango.DeviceProxy.read_attribute method.

Creating a periodic self-reset alarm
------------------------------------

A simple clock alarm would use the current time and will set AlarmThreshold, PollingPeriod and AutoReset properties. See this example:

  https://github.com/tango-controls/PANIC/blob/documentation/doc/recipes/CustomAlarms.rst#clock-alarm-triggered-by-time

A single formula clock would be more hackish; this alarm will execute a command on its own formula

.. code-block:: python

   PERIODIC:(FrontEnds/VC/Elotech-01/Temperature and FrontEnds/VC/VGCT-01/P1 \ 
   and (1920<(now%3600)<3200)) or (ResetAlarm('PERIODIC') and False)

Enabling search, expression matching and list comprehensions
------------------------------------------------------------

Having the syntax ``dom/fam/mem/attr.quality`` whould allow us to call attrs like:

.. code-block:: python

   any([ATTR_ALARM==s+'.quality' for s in FIND('dom/fam/*/pressure')])

One way may be using QUALITY, VALUE, TIME key functions:

.. code-block:: python

   any([ATTR_ALARM==QUALITY(s) for s in FIND('dom/fam/*/pressure')]) 

The use of FIND allows PyAlarm to prepare a list Taurus models that can be redirected from an <pre>event_received(...)</pre> hook.

Some list comprehension examples
--------------------------------

.. code-block:: python

   any([s for s in FIND(SR/ID/SCW01/Cooler*Err*)])

equals to 

.. code-block:: python

   any(FIND(SR/ID/SCW01/Cooler*Err*))

The negate:

.. code-block:: python

   any([s==0 for s in FIND(SR/ID/SCW01/Cooler*Err*)])

is equivalent to

.. code-block:: python

   any(not s for s in FIND(SR/ID/SCW01/Cooler*Err*)])

is equivalent to

.. code-block:: python

   not all(FIND(SR/ID/SCW01/Cooler*Err*))

is equivalent to

.. code-block:: python

   [s for s in FIND(SR/ID/SCW01/Cooler*Err*) if not s]


Grouping Alarms in Formulas
---------------------------

The proper way is (for readability I use upper case letters for alarms):

.. code-block:: python

   ALARM_1: just/my/tango/attribute_1
   ALARM_2: just/my/tango/attribute_2

then:

.. code-block:: python

   ALARM_1_OR_2: ALARM_1 or ALARM_2

or:

.. code-block:: python

   ALARM_1_OR_2: any(( ALARM_1 , ALARM_2 ))

or:

.. code-block:: python

   ALARM_ANY: any( FIND(my/alarm/device/ALARM_*) )

Any alarm you declare becomes both a PyAlarm attribute and a variable that you can anywhere (also in other PyAlarm devices). You don't trigger any new read because you just use the result of the formula already evaluated.

The GROUP is used to tell you that a set of conditions has changed from its previous state. GROUP instead will be triggered not if any is True, but if any of them toggles to True. It forces you to put the whole path to the alarm:

.. code-block:: python

   GROUP(my/alarm/device/ALARM_[12])

----

PyAlarm Device Properties
=========================

Distributing Alarms between servers
-----------------------------------

Alarms can be distributed between PyAlarm servers using the PyAlarm/AlarmsList property. A Panic system works well with 1200+ alarms distributed in 75 devices, with loads between 5 and 70 attrs/device. But instead of thinking in terms of N attrs/pyalarm you must distribute load trying to group all attributes from the same host or subsystem.

There are two reasons to do that (and also apply to Archiving):

* When a host is down you'll have a lot of proxy threads in background trying to reconnect to lost devices. If alarms are distributed on rough numbers it becomes a lot of timeouts spreading through the system. When alarms are grouped by host you isolate the problems.

* Same applies for very event-intensive devices. Devices that generate a lot of information will need lower attrs/pyalarm ratio than devices that do not change so much.

But, it is a good advice to keep the overall number of alarms in the system below 10K alarms. For manageability of the log system and avoid avalanches of useless information the logical number of alarms should be around or below 1000.

----

Alarm Declaration Properties
----------------------------

AlarmList
.........

Format of alarms will be:

.. code-block:: python

   TAG1:LT/VC/Dev1
   TAG2:LT/VC/Dev1/State
   TAG3:LT/VC/Dev1/Pressure > 1e-4

NOTE: This property was previously called AlarmsList; it is still loaded if AlarmList is empty for backward compatibility

AlarmDescriptions
.................

Description to be included in emails for each alarm. The format is::

   TAG:AlarmDescriptions...

NOTE: Special Tags like $NAME (for name of PyAlarm device) or $TAG (for name of the Alarm) will be automatically replaced in description.

AlarmReceivers
..............

.. code-block:: python

   TAG1:vacuum@accelerator.es,SMS:+34935924381,file:/tmp/err.log
   vacuum@accelerator.es:TAG1,TAG2,TAG3

Other options are SNAP or ACTION:

.. code-block:: python

   user@cells.es,
   SMS:+34666777888, #If SMS sending available
   SNAP, #Alarm changes will be recorded in SNAP database.
   ACTION(alarm:command,mach/alarm/beep/play_sequence,$DESCRIPTION)


Adding ACTION as receiver
.........................

Executing a command on alarm/disable/reset/acknowledge:

.. code-block:: python

   ACTION(alarm:command,mach/alarm/beep/play_sequence,$DESCRIPTION)

The syntax allow both attribute/command execution and the usage of multiple typed arguments:

.. code-block:: python

   ACTION(alarm:command,mach/dummy/motor/move,int(1),int(10))
   ACTION(reset:attribute,mach/dummy/motor/position,int(0))

Also commands added to the Class property @AllowedCommands@ can be executed:

.. code-block:: python

   ACTION(alarm:system:beep&)

PhoneBook (not implemented yet)
...............................

File where alarm receivers aliases are declared; e.g. 

.. code-block:: python

   User:user@accelerator.es;SMS:+34666555666 
 
Default location is: `` `$HOME/var/alarm_phone_book.log` ``
 
If User and Operator are defined in phonebook, AlarmsReceivers can be:

.. code-block:: python

   TAG2:User,Operator

----

REMINDER / RECOVERED / AUTORESET messages
-----------------------------------------

Reminder
........

If a number of seconds is set, a reminder mail will be sent while the alarm is still active, if 0 no Reminder will be sent.

AlertOnRecovery
...............

A message is sent if an alarm is active but the conditions of the attributes return to a safe value.
To enable the message the content of this property must contain 'email', 'sms' or both. If disabled no RECOVERY/AUTO-RESET messages are sent.

AutoReset
.........

If a number of seconds is set, the alarm will reset if the conditions are no longer active after the given interval.

----

Snapshot properties
-------------------

UseSnap
.......

If false no snapshots will be trigered (unless specifically added to receivers using "SNAP" ),

CreateNewContexts
.................

It enables PyAlarm to create new contexts for alarms if no matching context exists in the database.

----

Alarm Configuration Properties
------------------------------

(In future releases these properties could be individually configurable for each alarm)

**Enable** : If False forces the device to Disabled state and avoids messaging.

**LogFile** : File where alarms are logged Default: `"/tmp/alarm_$NAME.log"`

**FlagFile** : File where a 1 or 0 value will be written depending if theres active alarms or not.\n<br>This file can be used by other notification systems. Default:  `"/tmp/alarm_ds.nagios"`

**PollingPeriod** : Periode in seconds. in which all attributes not event-driven will be polled. Default: `60000`

**MaxAlarmsPerDay** : Max Number of Alarms to be sent each day to the same receiver. Default: `3`

**AlarmThreshold** : Min number of consecutive Events/Pollings that must trigger an Alarm. Default: `3`

**FromAddress** : Address that will appear as Sender in mail and SMS Default: `"controls"`

**SMSConfig** : Arguments for sendSMS command Default: ":"

**MaxMessagesPerAlarm** : To avoid the previous property to send a lot of messages continuously this property has been added to limit the maximum number of messages to be sent each time that an alarm is enabled/recovered/reset.

**StartupDelay** : Time that PyAlarm waits before starting the Alarm evaluation threads.

**EvalTimeout** : Timeout for read_attribute calls, in milliseconds .

**UseProcess** : To create new OS processes instead of threads.

----

Device Server Example
=====================

These will be the typical properties of a PyAlarm device

.. code-block:: python
 
   #---------------------------------------------------------
   # SERVER PyAlarm/AssemblyArea, PyAlarm device declaration
   #---------------------------------------------------------
   PyAlarm/AssemblyArea/DEVICE/PyAlarm: "LAB/VC/Alarms"
   # --- LAB/VC/Alarms properties
   LAB/VC/Alarms->AlarmDescriptions: "OVENPRESSURE:The pressure in the Oven exceeds Range",\
                                  "ADIXENPRESSURE:The pressure in the Roughing Station exceeds Range",\
                                  "OVENTEMPERATURE:The Temperature of the Oven exceeds Range",\
                                  "DEBUG:Just for debugging purposes"
   LAB/VC/Alarms->AlarmReceivers: OVENPRESSURE:somebody@cells.es,someone_else@cells.es,SMS:+34999666333,\
                              ADIXENPRESSURE:somebody@cells.es,someone_else@cells.es,SMS:+34999666333,\
                              OVENTEMPERATURE:somebody@cells.es,someone_else@cells.es,SMS:+34999666333,\
                              DEBUG:somebody@cells.es
   LAB/VC/Alarms->AlarmsList: "OVENPRESSURE:LAB/VC/BestecOven-1/Pressure_mbar > 5e-4",\
                          "OVENRUNNING:LAB/VC/BestecOven-1/MaxValue > 70",\
                          "ADIXENPRESSURE:LAB/VC/Adixen-01/P1 > 1e-4 and OVENRUNNING",\
                          "OVENTEMPERATURE:LAB/VC/BestecOven-1/MaxValue > 220",\
                          "DEBUG:OVENRUNNING and not PCISDOWN"
   LAB/VC/Alarms->PollingPeriod: 30
   LAB/VC/Alarms->SMSConfig: ...


----

Mail Messages
=============

PyAlarm allows to send mail notifications. Each alarm may be configured with :ref:`AlarmReceivers` property to provide
notification list. There is also a `GobalReceivers` property which allows to define notification for all alarms.

PyAlarm supports two ways of sending mails configured with the `MailMethod` class property:

* using `mail` shell command, when *MailMethod* is set to `mail`, which is default,
* or using `smtplib` python library when *MailMethod* is set to `smtp[:host[:port]]`.

As it is now, mail messages are formatted as the following:

Format of Alarm message
-----------------------

.. code-block:: python

   Subject:     LAB/VC/Alarms: Alarm RECOVERED (OVENTEMPERATURE)
   Date:     Wed, 12 Nov 2008 11:52:39 +0100

   TAG: OVENTEMPERATURE
             LAB/VC/BestecOven-1/MaxValue > 220 was RECOVERED at Wed Nov 12 11:52:39 2008

   Alarm receivers are:
             somebody@cells.es
             someone_else@cells.es
   Other Active Alarms are:
             DEBUG:Fri Nov  7 18:37:35 2008:OVENRUNNING and not PCISDOWN
             OVENRUNNING:Fri Nov  7 18:37:17 2008:LAB/VC/BestecOven-1/MaxValue > 70
   Past Alarms were:
             OVENTEMPERATURE:Fri Nov  7 20:49:46 2008


Format of Recovered message
---------------------------

.. code-block:: python

   Subject:     LAB/VC/Alarms: Alarm RECOVERED (OVENTEMPERATURE)
   Date:     Wed, 12 Nov 2008 11:52:39 +0100

   TAG: OVENTEMPERATURE
             LAB/VC/BestecOven-1/MaxValue > 220 was RECOVERED at Wed Nov 12 11:52:39 2008

   Alarm receivers are:
             somebody@cells.es
             someone_else@cells.es
   Other Active Alarms are:
             DEBUG:Fri Nov  7 18:37:35 2008:OVENRUNNING and not PCISDOWN
             OVENRUNNING:Fri Nov  7 18:37:17 2008:LAB/VC/BestecOven-1/MaxValue > 70
   Past Alarms were:
             OVENTEMPERATURE:Fri Nov  7 20:49:46 2008

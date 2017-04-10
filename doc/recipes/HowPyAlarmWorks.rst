How PyAlarm Device Server Works
===============================

This document tries to summarize how PyAlarm processes alarms and executes its actions. 
A full explanation of alarm syntax and each property is available in the PyAlarm user guide, 
but here I provide a summary for convenience.

The device server behaviour relies on three python objects: AlarmAPI, updateAlarms thread and TangoEval.

Each alarm is independent in terms of formula and receivers; but all alarms within the same PyAlarm device
will share a common evaluation environment determined by PyAlarm properties.

.. contents::
  

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

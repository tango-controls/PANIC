=======================
Alarm Formulas Examples
=======================

.. contents::


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
   
Alarm on delta and value
------------------------

This alarm will be triggered whenever a channel (HV*Code attributes) changes its value (delta!=0) and the new value is OFF (value=0)

.. code-block:: python

   any([(changed and value==0) for changed,value in

   zip( FIND(bl*/vc/ipct*/hv*code.delta) ,

   FIND(bl*/vc/ipct*/hv*code.value) )])


Generating Clock Signals
------------------------

Playing with PollingPeriod, AlarmThreshold and AutoReset properties is possible to 
achieve an square signal that keeps the alarm active/inactive at regular intervals.

 CLOCK=NOT CLOCK

The AlarmThreshold applies to both activation and reset of the alarm, so it has to be 
added to the AutoReset period to regulate the duty cycle. Keeping the PollingPeriod and 
AutoReset values very small will generate an accurate frequency (do not expect high accuracy,
that's a trick for testing but not a proper signal generator).

My values for a 10 seconds alarm cycle are::

.. code-block:: python

   PollingPeriod = 0.1
   AlarmThreshold = 50
   AutoReset = 0.0001
 
If you want a more accurate alarm, you can also use the NOW() function. This example generates a
switch every second

.. code-block:: python

   CLOCK = NOW()%2<1
   PollingPeriod=1
   AlarmThreshold-1

AlarmStates
===========

.. contents::

State transitions
-----------------

Alarm States and Severities are defined in panic.properties module.

With PyAlarm > 6.1; GUI will read the current Alarm state from the AlarmList attribute.



For compatibility with older versions, the events of ActiveAlarms will be used instead:

* If ActiveAlarms doesn't cotain tag, alarm.active will be 0, state = NORM
* Activealarms contains tag, alarm.active = activealarms timestamp, state = ACTIVE
* ActiveAlarms is None or Exception, alarm.active will be set to -1. state = ERROR

Disabled States
---------------

Their meanings are:

* OOSRV = Device server is Off (not exported), no process running
* DSUPR = Enabled property is False
* SHLVD = Alarm is listed in DisabledAlarms attribute (temporary disabled)
* ERROR = Device is alive but the alarm is not being evaluated (exported=1 and thread dead or exception).

IEC 62682: AlarmStates Definition and related  Actions
------------------------------------------------------

Different annunciators can be setup for each State change

Reset() can be automatic or forced to be manual

Reminder() : Alarm still ACTIVE, additional action can be configured

RTNUN : Condition recovered (but not Reset)
Alarm ACTIVE : (UNACKED)
Alarm ACKED : (action taken by operator)
RTNUN: return to NORM
NORM: after Reset() or not triggered

First peaks ignored if (t < polling*AlarmThreshold)

SHLVD, DSUPR, OOSRV: Unactive states. 

SHELVED for temporary disabling, 

DSUPR by process condition, 

OOSRV is permanent (device disabled). 

All of them are controlled by the Enable/Disable states/commands of PyAlarm.

In addition, PANIC adds ERROR State to raise problems with Tango devices.




IEC 62682: AlarmStates

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

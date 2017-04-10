* StartupDelay: the device will wait before starting to evaluate the alarms (e.g. giving some time to the system to recover from a powercut).

* Enabled: if False or 0 the PyAlarm it equals to disabling all alarm actions of the device; if it is True the behavior will be the normal expected; if it has a numeric value (e.g. 120) it means that the device will evaluate the alarms but not execute actions during the first 120 seconds (thus alarms can be activated but no action executed). It is used to prevent a restart of the device to re-execute all alarms that were already active.

* EvalTimeout: The proxy timeout used when evaluating the attributes (any read attribute slower than timeout will raise exception).

* AlarmThreshold: number of cycles that an alarm must evaluate to True to be considered active (to avoid alarms on "glitches").

* RethrowAttribute/RethrowState: Whether exceptions on reading attributes or states should be rethrown to higher levels, thus causing the alarm to be triggered. By default alarms are enabled if an State attribute is not readable (RethrowState=True), but when a numeric attribute is not readable its value is just replaced by None (RethowAttribute=False) and the formula evaluated normally.

* Reminder: A new email will be sent every XX seconds if the alarm remains active. When AlertOnRecovery is True an email will be sent also every time when the formula result oscillates from True to False.

* UseProcess: This is an experimental feature, like UseTaurus and others. In general, I advice you to not modify any parameter that is not detailed in the PyAlarm user guide as you may obtain unexpected results. Some parameters are used to test new features still under development and their behavior may vary between commits.

Regarding actions on recovery … this option is planned but not yet fully available. Actually just emails are sent when AlertOnRecovery is True. This feature may be implemented in the next 6 months or so but the syntax is still to be decided. 

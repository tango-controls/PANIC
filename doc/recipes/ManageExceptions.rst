====================================
Exception Management in Panic Alarms
====================================

The exception management will be done using the _raise=RAISE argument of the TangoEval.eval method. 


Three properties control if exceptions will enable the alarm or will be simply ignored.

:IgnoreExceptions: if False then all exceptions will be registered as FailedAlarms and the PyAlarm will change to FAULT whenever an exception is encountered. If no rethrow option is active, FailedAlarms will be displayed in grey in AlarmGUI as "disabled".

:RethrowAttribute: if True, any exception in the formula will set the alarm as active. PyAlarm state will change to ALARM or FAULT if IgnoreExceptions is False and all alarms are in failed state.

:RethrowState: if True, only alarms reading State attributes will be activated by exception. PyAlarm state will change to ALARM or FAULT if IgnoreExceptions is False and all alarms are in failed state.

So, in case of having an alarm reading a faulty attribute, the status of the alarm will be:

:DISABLED: If IgnoreExceptions=False and RethrowAttribute=False

:NOT ACTIVE: If IgnoreExceptions=True and RethrowAttribute=False

:ACTIVE: If IgnoreExceptions=False and RethrowAttribute=True

:ACTIVE: If IgnoreExceptions=True and RethrowAttribute=True






===================================
Exception Management in Panic Alarms
====================================

The exception management will be done using the _raise=RAISE argument of the TangoEval.eval method. 

Three properties control if exceptions will enable the alarm or will be simply ignored.

:IgnoreExceptions: if False then all exceptions will be registered as FailedAlarms and the PyAlarm will change to FAULT whenever an exception is encountered. If no rethrow option is active, FailedAlarms will be displayed in grey in AlarmGUI as "disabled".

:RethrowAttribute: if True, any exception in the formula will set the alarm as active. PyAlarm state will change to ALARM or FAULT if IgnoreExceptions is False and all alarms are in failed state.

:RethrowState: if True, only alarms reading State attributes will be activated by exception. PyAlarm state will change to ALARM or FAULT if IgnoreExceptions is False and all alarms are in failed state.



PyAlarm Startup Modes
=====================

The PyAlarm Startup is controlled by StartupDelay and Enabled properties.

StartupDelay will put the PyAlarm in PAUSED state after a restart; 
to not start to evaluate formulas immediately but after some seconds, 
thus giving time to other devices to start.

The Enabled property will instead control the notification actions:

- If False, no notification will be triggered. 
- If True, all notifications can be sent once StartupDelay has passed.
- If a Number is given, all notifications triggered between startup and t+Enabled will be ignored. 
- Enabled>(AlarmThreshold*PollingPeriod): "Silent restart", activates the Alarms that were presumably 
active before a restart; but do not retriggers the notifications.

Enabled = 120 is the typical case; not triggering notifications until the device has been running for at least 3 minutes.

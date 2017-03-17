========================
PANIC Tests and Examples
========================

.. contents::

GROUP Attributes or Alarms
==========================

There are two ways of setting a GROUP alarm::

  ...
  or
  ...

Generating Clock Signals
========================

Playing with PollingPeriod, AlarmThreshold and AutoReset properties is possible to 
achieve an square signal that keeps the alarm active/inactive at regular intervals.

The AlarmThreshold applies to both activation and reset of the alarm, so it has to be 
added to the AutoReset period to regulate the duty cycle. Keeping the PollingPeriod and 
AutoReset values very small will generate an accurate frequency (do not expect high accuracy,
that's a trick for testing but not a proper signal generator).

My values for a 10 seconds alarm cycle are::

 PollingPeriod = 0.1
 AlarmThreshold = 50
 AutoReset = 0.0001
 

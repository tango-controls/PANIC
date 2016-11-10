=====================
Hierarchies In Alarms
=====================

.. contents::

TOP/BOTTOM
==========

The TOP/BOTTOM just provides a filter for finding alarms where the value of another
alarm is used directly in the formula. It is case sensitive, so you can use lower/upper
case to show/hide alarms in these filters.

To use hierarchies, alarms shall be written using the result of previous ones::

  GAB1 = any([t >5 for t in FIND(tc1:10000/LMC/C01/GAB/*)])
  GAB2 = any([t >5 for t in FIND(tc1:10000/LMC/C02/GAB/*)])
  GAB_ALL= GAB1 or GAB2
  OTHER = tc1:10000/LMC/C02/Other/State != ON
  CAPITAL = GAB_ALL or OTHER

Then, the filter by hierarchy will return::

  TOP (alarms that depend on others): CAPITAL, GAB12
  BOTTOM (alarms isolated or referenced from others): OTHER, GAB_ALL, GAB1, GAB2
 
In this case GAB_ALL appears in both lists; to avoid that just rewrite it using lower case attribute names::

  GAB_ALL = any(FIND('lmc1:10000/lmc/alarms/01/gab*'))

Now you should have only "CAPITAL" as TOP Alarm.

You can reproduce this behaviour from the api calling::

 panic.AlarmAPI().filter_hierarchy('TOP')
 
Alarm GROUP
===========

For an expression matching multiple alarms or attributes, GROUP returns a new formula that will evaluate to True
if any of the alarm changes to active state (.delta) or matches a given condition::

  GROUP(ALARM1, ALARM2, ALARM3)

**NOTE**: BY DEFAULT IS NOT LIKE any(FIND(*)); it will react only on change, not if already active!

**NOTE2**: you must tune your PyAlarm properties to have AlarmThreshold = 1 and AutoReset <= 3 to take profit of this feature.

It uses the read_attribute schema from TangoEval, thus using .delta to keep track of which values has changed. 
For example, GROUP(test/alarms/*/TEST_[ABC]) will be replaced by::
       
  any([t.delta>0 for d in FIND(test/alarms/*/TEST_[ABC].all)])

The GROUP macro can be called with one or several expressions separated by commas and a condition separated by semicolon::

  GROUP(expression1[,expression2;condition)
  
Expressions may contain a device name or not. If no device name is passed then it will search for it in the alarm list::

  expression=[a/dev/name*/]attribute*
  
Thus, a valid GROUP expression is::

  GROUP(LOCAL_ALARM1,t01:10000/an/alarm/dev/ALARM2)
  
If the condition is empty then checks any .delta != 0. It can be modified if the formula contains a semicolon ";" and 
a condition using 'x' as variable; in this case it will be used instead of delta to check for alarm::

  GROUP(bl09/vc/vgct-*/p[12];x>1e-5) => [x>1e-5 for x in FIND(bl09/vc/vgct-*/p[12])]
               

            

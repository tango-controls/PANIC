Alarm Formulas Examples (Max IV, 2014)
--------------------------------------

The proper way is (for readability I use upper case letters for alarms):

  ALARM_1: just/my/tango/attribute_1
  ALARM_2: just/my/tango/attribute_2

then:

  ALARM_1_OR_2: ALARM_1 or ALARM_2

or:

  ALARM_1_OR_2: any(( ALARM_1 , ALARM_2 ))

or:

  ALARM_ANY: any( FIND(my/alarm/device/ALARM_*) )

Any alarm you declare becomes both a PyAlarm attribute and a variable that you can anywhere (also in other PyAlarm devices). You don't trigger any new read because you just use the result of the formula already evaluated.

The GROUP is used to tell you that a set of conditions has changed from its previous state. GROUP instead will be triggered not if any is True, but if any of them toggles to True. It forces you to put the whole path to the alarm:

  GROUP(my/alarm/device/ALARM_[12])

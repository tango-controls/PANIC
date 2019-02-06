====================================
AlarmWikiLink PyAlarm Class Property
====================================

This class property allow to provide links to Wiki pages on alarms.

It is done as a link appearing in alarm window widget, 
if there is `AlarmWikiLink` PyAlarm class property defined.

The link is formed from this property by substitution of `{%ALARM%}`
with actual alarm name. 

So, the value of the property may looks like:: 

    http://wiki.cps.uj.edu.pl/alarms/{%ALARM%}
  

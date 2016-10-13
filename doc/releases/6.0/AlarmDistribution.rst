Alarms Distribution
===================

About distributing load (answer to paul bell, 2014)
---------------------------------------------------

We have 1200+ alarms and system works quite well with it. But regarding distribution of PyAlarm devices and servers the rules must be more intelligent.

Instead of thinking in terms of N attrs/pyalarm you must distribute load trying to group all attributes from the same host or subsystem.

There are two reasons to do that (and also apply to Archiving):

 - When a host is down you'll have a lot of proxy threads in background trying to reconnect to lost devices. If alarms are distributed on rough numbers it becomes a lot of timeouts spreading through the system. When alarms are grouped by host you isolate the problems.

 - Same applies for very event-intensive devices. Devices that generate a lot of information will need lower attrs/pyalarm ratio than devices that do not change so much.

Apart of that ... if you have 1000 alarms just for the linac then you may have a wrong specification. I use to say than "all" should be in the order of 10K ; by experience any number about that is too much. If you need more than 10K of a kind what you really need is to add a level of abstraction (do not check all gauges of a vacuum section, just had an attribute where you can read the max value).

It applies to all Tango systems I've seen (alarms, archiving, save/restore, pool, device tree, ...); if you reach a number above 10K then you must add an abstraction layer. It's not only that you reach a performance limit, also your users will feel too dazed and confused when searching for things.

e.g. Our accelerator group requested 1200 alarms ... and after some months they asked for a filter to show only the 240 they really care about.

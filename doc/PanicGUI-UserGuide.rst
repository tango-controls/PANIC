====================
PANIC GUI User Guide
====================

.. contents::

Description
===========

panic.gui is an stand-alone graphical application to visualize and configure PANIC Alarm Systems.

The panic.gui module also contains widgets that can be embedded in other Tango applications (e.g. Vacca).

Filter levels
=============

There are three levels:

 - AlarmDomain : servers/devices/domains that will be inspected for alarms
 - AlarmView : within the AlarmDomain, stored filters that allow to select a given subsystem
 - UserFilters : defined at runtime in the application using the list combo boxes.
 
 The AlarmDomain will be defined at application startup and will restrict the PyAlarm instances the GUI connects with. 
 It means that whatever AlarmView is chosen afterwards, PyAlarm that are not part of the domain will not be inspected.
 
 AlarmDomain is the "filters" launcher argument existing since Panic 4; since Panic>6 is stored as PANIC.AlarmDomains property.
 
 AlarmView is introduced in Panic>6 and stored as a PANIC free property.
 
 From Panic>7 onwards, domain can be changed in a running application.

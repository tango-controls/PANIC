--------------------------------------
PANIC, a python Alarm System for TANGO
--------------------------------------

.. contents::

Description
===========

PANIC is a set of tools (api, Tango device server, user interface) that provides:

 * Periodic evaluation of a set of conditions.
 * Notification (email, sms, pop-up, speakers)
 * Keep a log of what happened. (files, Tango Snapshots)
 * Taking automated actions (Tango commands / attributes)
 * Tools for configuration/visualization

The Panic package contains the python AlarmAPI for managing the PyAlarm device servers from a client 
application or a python shell. The panic module is used by PyAlarm, Panic Toolbar and Panic GUI.

PANIC IS TESTED ON LINUX ONLY, WINDOWS/MAC MAY NOT BE FULLY SUPPORTED IN MASTER BRANCH

The optional panic submodules are:

 panic.ds : PyAlarm device server
 panic.gui :  Placeholder for the PanicGUI application
 
See the docs at: http://www.pythonhosted.org/panic

Recipes are also available at: https://github.com/tango-controls/PANIC/tree/documentation/doc/recipes

Get the latest release of Panic from: https://github.com/tango-controls/PANIC/releases

See CHANGE log in panic/CHANGES file


Other Project pages
===================

* http://www.tango-controls.org/community/projects/panic-alarm-system
* https://github.com/tango-controls/panic
* https://pypi.python.org/pypi/panic


PyAlarm Device Server
=====================

panic.ds.PyAlarm Device Class

PyAlarm is the alarm device server used by ALBA Alarm System, it requires PyTango and Fandango modules, 
both available from tango-cs.sourceforge.net

Some configuration panels in the GUI require PyAlarm to be available in the PYTHONPATH, to do so you can 
add the PyAlarm.py folder to the PYTHONPATH variable or copy the PyAlarm.py file within the panic folder; 
so it could be loaded as a part of the module.


Panic GUI
=========

panic.gui.AlarmGUI Class

Panic is an application for controlling and managing alarms. It depends on panic and taurus libraries.

It allows the user to visualize existing alarms in a clear form and adding/editing/deleting alarms.
In edit mode user can change name, move alarms to another device, change descriptions and modify formulas.
Additional widgets in which the app is equipped allows alarm history viewing, phonebook editing and 
device settings manipulation.

Authors
=======

Sergi Rubio
Alba Synchrotron 2006-2016

LICENSE AND WARRANTY
====================

see `LICENSE file <https://github.com/tango-controls/fandango/blob/documentation/LICENSE>`_

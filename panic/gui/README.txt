Hi,

This is the Alarms GUI application, and it has some dependencies to be added to the PYTHONPATH environment variable:

 - Panic api (panic module from sourceforge/tango-ds/Servers/Miscellaneous/PyAlarm/Panic)
 - PyAlarm device server ((panic module from sourceforge/tango-ds/Servers/Miscellaneous/PyAlarm)
 - Taurus (from sourceforge/tango-cs
 - PyQt (from Riverbank)
 - python, maybe

Just write a launcher script like:

#!/bin/sh
export PYTHONPATH=/path/to/server:/path/to/API:/path/to/taurus:$PYTHONPATH
cd /path/to/panic_gui/
/usr/bin/python gui.py

Enjoy,

srubio@cells.es

----------------------------------------------------------------------------------
Changelog

VERSION = 6.0; 

Faster startup by delaying SNAP dependency check
Widget modules reorganized
Added New Device dialog
Added LDAP-less generic validator
Widgets adapted to Taurus4 (but not the API yet)

VERSION = 5.5 December 2015 ; 

 - Integration with Taurus GUI
 - Added new signals for interaction with synoptics
 - Many bugs solved

5.4 Added user control, new evaluate() method, and many bugs solved on Ack/Disable/Delete actions.

2015/08/07

Added user validation (if ldap_login module available)
many bugs solved on Ack/Disable/Delete actions
widgets: new API.evaluate() method allows to test formulas on the remote device
alarmattrchange: module removed (unused)
alarmhistory: Added try/except to allow loading of PANIC w/out snaps features

2015/06/08

Re-enabled Regex parsing from system arguments
Enabled PANIC_DEFAULT to set/hide default regexp filters.
Solved Null icon bug on failed alarms
Active and Regular expression filters are now independent

2014/05/05

history: Solved bug on widget resizing
history: Double click opens snapshot
main: added --calc option to main to open just alarm preview panel
preview: using eval from Panic api
Snap_Form renamed to SnapForm

2014/02/03

Small bug solved in line splitting in editor

2013/11/22

Editor refactored to use AlarmFormula widget
Enabled actions on multiple selection
Solved many navigation errors
Added Windows Menu
Added AlarmCalcullator tool

Added edit/save capabilities to AlarmFormula/AlarmPreview
Added WindowManager and get_archive_trend widgets

2013/10/14
Form widgets moved to their own files
Loading default property values from Panic API
Expert panel replaced by new form on Edit
Many bugs removed.
Added Import/Export options.
Added trends as tool.
Solved bugs on alarm sorting
Added checkbox widget for confirmation of changes.
Added new preview panel with formula evaluation.

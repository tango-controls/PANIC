==================
PANIC Test Devices
==================

To load the .csv file (using fandango)::

   csv2tango panic/tests/testdevs.csv
   
To launch all the devices (using screen)::

  screen -dm -S simulator python SimulatorDS/SimulatorDS.py panic-test -v2
  
  INSTANCES="Actions Clock Delay exceptions Group Quality results Value"
  for i in $INSTANCES; do 
    screen -dm -S $i python panic/ds/PyAlarm.py $i -v2; 
  done

Show attributes and alarms for the tests::

  SIMS=$(fandango.sh find_attributes "test/panic/sim-01/(stat|t$|t30|f|r)*")
  taurusform $SIMS&
  taurustrend $(fandango find_attributes "test/panic/*/ck*") &
  taurustrend $(fandango find_attributes "test/panic/*/(wattr|comm|rw)*") &
  
Show the Panic UI::

  python panic/gui/gui.py

For each of the implemented alarms the behaviour is:

* A_VALUE/A_QUALITY should be alternatively toogling following T30 value/quality

* exceptions:
** REATTR: should be orange/True/VALID, and test/panic/reattr should be ALARM
** EXCEPT: should be grey/False/INVALID; and its name added to FailedAlarms 
   array, test/panic/except/state should be FAULT !!*
** NOEXCEPT: should be green/False/VALID

* time and groups:
** CK1,CK5,CK2,CK10 : toggle automatically at different frequencies
** GROUP_OR/GROUP_AND : should match the aggregate of different CK alarms
** GROUP_ALL : should be always active !!*

* actions:
** WATTR : always true, write a 0 on sim/RW attribute every time that is reset 
  and 345 when it triggers again.
** COMM: Will reset WATTR when reseted/triggered again.
** SYSTEM: will save current date at /tmp/date

----

!!*: test not 100% passed for 6.0 release and taurus 3.7 (March 2017)

EXCEPT is green, should be grey
GROUP_ALL is not able to follow the speed of all GROUP signal changes (2 levels)
DEBUG alarms are shown in Orange (should be Yellow)




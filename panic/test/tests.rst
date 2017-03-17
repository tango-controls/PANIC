To load the .csv file

csv2tango panic/tests/testdevs.csv

screen -dm ds/PyAlarm.py Results -v2
screen -dm ds/PyAlarm.py Excepts -v2
screen ds/PyAlarm.py Clock -v2


To play tests

taurustrend $(fandango find_attributes "test/panic/*/ck*")



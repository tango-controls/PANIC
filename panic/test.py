#!/usr/bin/python

start_step = int(sys.argv[1:] or [0])

msg = 'Testing panic/PyAlarm suite'
    
def test_step(n,msg):
    print '-'*80
    print ' '+'Test %s: %s'%(n,msg)
    print '-'*80
    
def check_step(n):
    if start_step<=n:
        test_step(n,msg)
        return True
    else:
        return False
    
print msg

msg="""
#Create the test device

#Launch it; take snapshot of memory usage

NOTE: This testing is not capable of testing email/SMS sending. This will have to be human-tested defining a test receiver:

Basic steps:

 * Create a simulator with attributes suitable for testing.
 * Start the simulators
 * Ensure that all alarms conditions are not enabled reseting attribute values.

<pre><code class="python">"""

import fandango as fun
import panic,time
from fandango import tango
if check_step(0):
    tango.add_new_device('PySignalSimulator/test-alarms','PySignalSimulator','test/test/alarms-test')
    tango.put_device_property('test/test/alarms-test',{
        'DynamicAttributes':"""#ALARM TESTING
        A=READ and VAR('VALUE1') or WRITE and VAR('VALUE1',VALUE)
        B=DevDouble(READ and VAR('B') or WRITE and VAR('B',VALUE))
        S=DevDouble(READ and VAR('B')*sin(t%3.14) or WRITE and VAR('B',VALUE))
        D=DevLong(READ and PROPERTY('DATA',True) or WRITE and WPROPERTY('DATA',VALUE))
        C = DevLong(READ and VAR('C') or WRITE and VAR('C',VALUE))
        T=t""".split('\n'),
        'DynamicStates':
        'STATE=C #INT to STATE conversion'
        })
    fun.Astor().start_servers('PySignalSimulator/test-alarms')
    time.sleep(10.)

simulator = fandango.get_device('test/test/alarms-test')
[simulator.write_attribute(a,0) for a in 'ABSDC']

msg="""</pre>

 * Create 2 PyAlarm instances, to check attribute-based and alarm/group based alarms 
 * Setup the time variables that will manage the alarm cycle
 
<pre><code class="python">"""

alarms = panic.api()

if check_step(1):
    tango.add_new_device('PyAlarm/test-alarms','PyAlarm','test/alarms/alarms-test')
    tango.add_new_device('PyAlarm/test-group','PyAlarm','test/alarms/alarms-group')
    threshold = 3
    polling = 5
    autoreset = 60 
    
    alarmdevs = ['test/alarms/alarms-test','test/alarms/alarms-group']
    props = {
        'Enabled':'15',
        'AlarmThreshold':threshold,
        'AlertOnRecovery':'email',
        'PollingPeriod':polling,
        'Reminder':0,
        'AutoReset':autoreset,
        'RethrowState':True,
        'RethrowAttribute':False,
        'IgnoreExceptions':True,
        'UseSnap':True,
        'CreateNewContexts':True,
        'MaxMessagesPerAlarm':20,
        'FromAddress':'oncall@cells.es',
        'LogLevel':'DEBUG',
        'SMSConfig':':',
        'StartupDelay':0,
        'EvalTimeout':500,
        'UseProcess':False,
        'UseTaurus':False,
    }
    [tango.put_device_property(d,props) for d in alarmdevs]

msg="""</pre>

 * Start the PyAlarm devices and create simple and group Alarms to inspect.
 
<pre><code class="python">"""

if check_step(2):
    receiver = "alarmtests@cells.es,SMS:+3400000000"
    fun.Astor().start_servers('PyAlarm/test-alarms')
    fun.Astor().start_servers('PyAlarm/test-group')
    time.sleep(15.)
    
    alarms.add(tag='TEST_A',formula='test/test/alarms-test/A',device='test/alarms/alarms-test',
        receivers=receiver,overwrite=True)
    alarms.add(tag='TEST_DELTA',device='test/alarms/alarms-test',receivers=receiver,overwrite=True,
        formula = 'not -5<test/sim/test-00/S.delta<5 and ( test/sim/test-00/S, test/sim/test-00/S.delta )')
    alarms.add(tag='TEST_STATE',formula='test/test/alarms-test/State not in (OFF,UNKNOWN,FAULT,ALARM)',
        device='test/alarms/alarms-test',receivers=receiver,overwrite=True)
    alarms.add(tag='TEST_GROUP1',formula='any([d>0 for d in FIND(test/alarms/*/TEST_[ABC].delta)]) and FIND(test/alarms/*/TEST_[ABC])',
        device='test/alarms/alarms-group',receivers=receiver,overwrite=True)
    alarms.add(tag='TEST_GROUP2',formula='GROUP(TEST_[ABC])',
        device='test/alarms/alarms-group',receivers=receiver,overwrite=True)

msg="""</pre>

Test steps:

 * Enable an alarm condition in the simulated A attribute.
 * Alarm should be enabled after 1+AlarmThreshold*PollingPeriod time (and not before)
 * Group alarm should be enabled after 1+AlarmThreshold*PollingPeriod
 
<pre><code class="python">"""

msg="""</pre>
 * Disable alarm condition
 * Alarm should enter in recovery state after AlarmThreshold*PollingPeriod.
 * Alarm should AutoReset after AutoReset period.
 * Group should reset after AutoReset period.

###############################################################################
<pre><code class="python">"""

msg="""</pre>"""

#Load test setup

#Run API methods for testing (take snapshot of memory usage)

## Alarm cycle (activation/recovery/autoreset)

## Test Enable/Disable alarm

## 



## Check memory usage increase in device and api after tests


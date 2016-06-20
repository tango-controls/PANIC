#!/usr/bin/python

import sys,os,re,traceback,time
import fandango
from fandango import tango
import panic


start_step = int((sys.argv[1:] or [0])[0])

msg = 'Testing panic/PyAlarm suite (%d)'%start_step
gb = """</pre>
    """
ge = """
    <pre><code class="python">"""
    
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
      
def check_alarms_vs_archiving(alarms=[]):
  import PyTangoArchiving
  api = panic.api()
  alarms = alarms or [a for a in api if fn.check_device(api[a].device)]
  rd = PyTangoArchiving.Reader()
  archs = rd.get_attributes()
  models = dict((a,api[a].get_attribute(full=1).lower()) for a in alarms)
  alarms = [a for a in alarms if names[a] in archs]
  olds = {}
  for a in sorted(alarms):
    af = names[a]
    olds[a] = rd.get_attribute_values(af,-7200)
  for a in sorted(alarms):
    af = names[a]
    v = fn.tango.read_attribute(af)
    if 1 or olds[a] and olds[a][0][1]!=v:
      print(a,af,olds[a][0][1],v)
  return

    
def main_test():
  print msg

  try:
      
      msg="""
      #Create the test device
      
      #Launch it; take snapshot of memory usage
      
      NOTE: This testing is not capable of testing email/SMS sending. This will have to be human-tested defining a test receiver:
      
      Basic steps:
      
      * Create a simulator with attributes suitable for testing.
      * Start the simulators
      * Ensure that all alarms conditions are not enabled reseting attribute values.
      
      <pre><code class="python">"""
      
      if check_step(0):
          tango.add_new_device('PySignalSimulator/test-alarms','PySignalSimulator','test/test/alarms-test')
          tango.put_device_property('test/test/alarms-test',{
              'DynamicAttributes':map(str.strip,
              """#ALARM TESTING
              A=READ and VAR('VALUE1') or WRITE and VAR('VALUE1',VALUE)
              B=DevDouble(READ and VAR('B') or WRITE and VAR('B',VALUE))
              S=DevDouble(READ and VAR('B')*sin(t%3.14) or WRITE and VAR('B',VALUE))
              D=DevLong(READ and PROPERTY('DATA',True) or WRITE and WPROPERTY('DATA',VALUE))
              C = DevLong(READ and VAR('C') or WRITE and VAR('C',VALUE))
              T=t""".split('\n')),
              'DynamicStates':
              'STATE=C #INT to STATE conversion'
              })
          fandango.Astor().start_servers('PySignalSimulator/test-alarms')
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
      
      N,msg=2,gb+"* Start the PyAlarm devices"+ge
      if check_step(N):
          receiver = "alarmtests@cells.es,SMS:+3400000000"
          fandango.Astor().start_servers('PyAlarm/test-alarms')
          fandango.Astor().start_servers('PyAlarm/test-group')
          time.sleep(15.)
          
      N,msg=3,gb+"* create simple and group Alarms to inspect."+ge
      if check_step(N):
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
      
      N,msg=4,gb+"""
      Test steps:
      
      * Enable an alarm condition in the simulated A attribute.
      * Alarm should be enabled after 1+AlarmThreshold*PollingPeriod time (and not before)
      * Group alarm should be enabled after 1+AlarmThreshold*PollingPeriod
      """+ge
      if check_step(N):
          pass
      
      N,msg=5,gb+"""
      * Disable alarm condition
      * Alarm should enter in recovery state after AlarmThreshold*PollingPeriod.
      * Alarm should AutoReset after AutoReset period.
      * Group should reset after AutoReset period.
      
      ###############################################################################"""+ge
      if check_step(N):
          pass
      
      N,msg=6,gb+"""
      * Testing properties
      ** RethrowAttribute ... None/NaN
      ** RethrowState ... True/False
      ** Enabled ... time or formula or both
      
      ###############################################################################"""+ge
      if check_step(N):
          pass
      msg=ge

  except:
      print traceback.format_exc()

  N,msg = -1,"""Stopping all servers ..."""
  check_step(N)
  fandango.Astor().stop_servers('PySignalSimulator/test-alarms')
  fandango.Astor().stop_servers('PyAlarm/test-alarms')
  fandango.Astor().stop_servers('PyAlarm/test-group')

#Load test setup

#Run API methods for testing (take snapshot of memory usage)

## Alarm cycle (activation/recovery/autoreset)

## Test Enable/Disable alarm

## 



## Check memory usage increase in device and api after tests


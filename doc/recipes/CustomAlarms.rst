Special Alarm Recipes
=====================

Special keys used in Alarm formulas
-----------------------------------

- DEVICE: PyAlarm device name
- DOMAIN,FAMILY,MEMBER: Parts of the device  name
- ALARMS: Alarms managed by this device
- PANIC: API containing all declared alarms
- t: time since the device was started

- T(...): string to time
- str2time(...): string to time
- now, NOW(): current timestamp
- DEVICES: instantiated devices
- DEV(device): DeviceProxy(device)
- NAMES(expression'): Finds all attributes matching the expression and return its names.
- CACHE: Saved values
- PREV: Previous values
- READ(attr): TangoEval.read_attribute(attr)
- FIND('expression'): Finds all attributes matching the expression and return its values.

Expiration Date
---------------

Disabling or re-enabling after a given date

A temporal condition can be achieved using the T() macro in the formula.

To disable an Alarm after a given date::

  T() < T('2013-04-23') and D/F/M.A > V1

To re-enable it after a maintenance period::

  T() > T('2013-04-23') and D/F/M.A > V1


Accessing PyAlarm Values CACHE
------------------------------

The PyAlarm CACHE dictionary contains the last values stored for each tango attribute that 
appeared in the formulas. The size of cache is AlarmTrheshold + 1

Usage::

  PASS_BY_0=[(k,v.time.tv_sec,str(v.value)) for k,t in CACHE.items() for v in t if v.value==0]

  
This will trigger alarm if ALL values in the cache are equal, it is NOT the same as Delta 
because it checks only the first and last values::

  not (lambda l:max(l)-min(l))([v.value for v in CACHE['wr/rf/circ-1/heartbeat']])
 

Clock: Alarm triggered by time
------------------------------

This alarm will be enabled/disabled every 5 seconds.

First, create a new PyAlarm device:

.. code-block:: python

 import fandango as fn
 fn.tango.add_new_device('PyAlarm/Clock','PyAlarm','test/pyalarm/clock')

Add the new alarm (formula will use current time to switch True/False very 5 seconds)

.. code-block:: python
 
 from panic import AlarmAPI
 alarms = AlarmAPI()
 alarms.add(device='test/pyalarm/clock',tag='CLOCK',formula='NOW()%10<5')

Start your device server using Astor, fandango or manually

.. code-block:: python

 import fandango as fn
 fn.Astor('test/pyalarm/clock').start_servers(host='your_hostname')

Then, configure the device properties to react every second for both activation and reset:

.. code-block:: python

 dtest = alarms.devices['test/pyalarm/clock']
 dtest.get_config()
 dtest.config['Enabled'] = 1
 dtest.config['AutoReset'] = 1
 dtest.config['AlarmThreshold'] = 1
 dtest.config['PollingPeriod'] = 1
 alarms.put_db_properties(dtest.name,dtest.config)
 dtest.init()
 
This is the result you can expect when plotting test/pyalarm/clock/CLOCK in a taurustrend:
 
.. image:: clock-events.png
   :height: 100px
   :width: 200 px
   :scale: 50 %
   :alt: alternate text
   :align: right  
  
  

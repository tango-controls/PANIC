PyAlarm Using Events With Taurus
================================

Setting up a PyAlarm getting Tango events from Taurus
-----------------------------------------------------

We will test events using the CLOCK alarm created in the previous recipe (polling should be enabled, this example uses polling on CLOCK attribute at 10 ms):

  https://github.com/tango-controls/panic/blob/documentation/doc/recipes/CustomAlarms.rst#clock-alarm-triggered-by-time


Then, create a new PyAlarm device and the event-based alarm:

.. code-block:: python

  import fandango as fn
  fn.tango.add_new_device('PyAlarm/events','PyAlarm','test/pyalarm/events')
  
  from panic import AlarmAPI
  alarms = AlarmAPI()
  alarms.add(device='test/pyalarm/events',tag='EVENTS',formula='test/pyalarm/clock/clock')

Start your device server using Astor, fandango or manually

.. code-block:: python

  import fandango as fn
  fn.Astor('test/pyalarm/events').start_servers(host='your_hostname')


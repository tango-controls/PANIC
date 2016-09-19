Special keys in Alarm formulas
------------------------------

DEVICE: PyAlarm device name
DOMAIN,FAMILY,MEMBER: Parts of the device  name
ALARMS: Alarms managed by this device
PANIC: API containing all declared alarms
t: time since the device was started

T(...): string to time
str2time(...): string to time
now, NOW(): current timestamp
DEVICES: instantiated devices
DEV(device): DeviceProxy(device)
NAMES(expression'): Finds all attributes matching the expression and return its names.
CACHE: Saved values
PREV: Previous values
READ(attr): TangoEval.read_attribute(attr)
FIND('expression'): Finds all attributes matching the expression and return its values.

Clock: Alarm triggered by time
------------------------------

..  code::

from panic import AlarmAPI
panic = AlarmAPI()
panic.add(device='test/pyalarm/clock',tag='CLOCK',formula='t%10<5')

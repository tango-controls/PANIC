
import fandango as Fn
from fandango.log import InOutLogged
import fandango.tango as Ft
import panic

global api
api = None

@InOutLogged
def test_AlarmAPI():
  global api
  api = panic.api()
  assert api

@InOutLogged
def test_AlarmDS(device=''):
  if not device:
    device = Fn.first((d for d,v in api.devices.items() if v.ping() is not None),None)
  Fn.log.info('Testing AlarmDS(%s)'%device)
  if device:
    device = api.devices.get(device)
    assert Fn.isMapping(device.get_active_alarms())
  return True

@InOutLogged
def test_panic():
  test_AlarmAPI()
  test_AlarmDS()

if __name__ == '__main__':
  test_panic()

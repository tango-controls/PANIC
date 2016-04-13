
import fandango as fn
import fandango.tango as ft
import json,time,sys,os,traceback

df = 'building_ct_alarms-dw.json'
sf = 'building_ct_sqlserver.json'

dd = 'building/ct/alarms-dw'
sd = 'building/ct/sqlserver'

__doc__ = """

Usage
-----

In the HW SIDE:

import alarm_test

devs = alarm_test.extract('building/ct/alarms-dhc')
['building/ct/alarms-dhc', 'building/ct/sqlserver']

alarm_test.export(devs)
['building_ct_alarms-dhc.json','building_ct_sqlserver.json']

----

In the SIMULATORS SIDE:

files = ['building_ct_alarms-dhc.json','building_ct_sqlserver.json']
alarm_test.load('DHC',files)

fandango.Astor('*/DHC').start_servers()

time.sleep(600)

alarm_test.export('building/ct/alarms-dhc','.sim')

----

Back to the HW SIDE

alarm_test.check('building_ct_alarms-dhc.sim',brief=True)

[('building/ct/alarms-dw', 'LastAlarm'),
 ('building/ct/alarms-dw', 'AcknowledgedAlarms'),
 ('building/ct/alarms-dw', 'DisabledAlarms'),
 ('building/ct/alarms-dw', 'Status'),
 ('building/ct/alarms-dw', 'AlarmReceivers'),
 ('building/ct/alarms-dw', 'VersionNumber'),
 ('building/ct/alarms-dw', 'FailedAlarms'),
 ('building/ct/alarms-dw', 'AlarmConfiguration'),
 ('building/ct/alarms-dw', 'SentSMS'),
 ('building/ct/alarms-dw', 'SentEmails'),
 ('building/ct/alarms-dw', 'PhoneBook'),
 ('building/ct/alarms-dw', 'ActiveAlarms'),
 ('building/ct/alarms-dw', 'PastAlarms'),
 ('building/ct/alarms-dw', 'AlarmList')]


"""

def dev2file(d,suffix='.json'):
  return d.replace('/','_')+suffix
  
def file2dev(f):
  return f.split('/')[-1].split('.')[0].replace('_','/')

def extract(target):
  """ Extract devices used in alarms """
  import panic
  api = panic.api()
  target = fn.toList(target)
  alarms = []
  devs = []

  for t in target:
    if t in api:
      alarms.append(t)
    if t in api.devices:
      alarms.extend(api.devices[t].alarms.keys())

  for a in alarms:
    devs.append(api[a].device)
    attrs = api.parse_attributes(a)
    devs.extend(d.rsplit('/',1)[0] for d in attrs)
    
  return sorted(set(map(str.lower,devs)))

def export(devices=[dd,sd],suffix='.json',preffix=''):
  """ save devices in .json files """
  devices = fn.toList(devices)
  files = []
  if preffix and not preffix.endswith('/'):
    preffix+='/'
  for d in devices:
    values = ft.export_device_to_dict(d)
    files.append(preffix+dev2file(d,suffix))
    json.dump(values,open(files[-1],'w'))
  return files 

def check(filename,device='',brief=False):
  """ compare .json files to a real device """
  if not device:
    device = file2dev(filename)

  data = json.load(open(filename))
  vals = dict((str(k),v['value']) for k,v in data['attributes'].items())
  for k,v in vals.items():
    if type(v)==unicode:
      vals[k] = str(v)

  diff = []
  dp = ft.get_device(device)
  attrs = dp.get_attribute_list()
  for k,v in vals.items():
    if not fn.inCl(k,attrs):
      diff.append((device,k,v,None))
    else:
      try:
        w = dp.read_attribute(k).value
        if w!=v:
          diff.append((device,k,v,w))
      except Exception,e:
        diff.append((device,k,v,e))

  if brief:
    diff = [t[:2] for t in diff]
  return diff
     
def load(instance,devices=[df,sf]):
  """ load .json files into simulated devices """
  
  done = []
  devices = fn.toList(devices)
  for dd in devices:
    if os.path.isfile(dd):
      df,dd = dd,file2dev(dd)
    else:
      df,dd = dev2file(dd),dd
    
    data = json.load(open(df))
    
    if data['dev_class'] == 'PyAlarm':
      props = data['properties']
      props = dict((str(k),map(str,v)) for k,v in props.items())

      assert not ft.get_matching_devices(dd), Exception('Device %s Already Exists!!!'%dd)
      ft.add_new_device('PyAlarm/'+instance,'PyAlarm',dd)
      ft.put_device_property(dd,props)
      
    else:
      vals = dict((str(k),v['value']) for k,v in data['attributes'].items())
      dynattrs = []
      for k,v in sorted(vals.items()):
        if k.lower() in ('state','status'):
          continue
        t = type(v).__name__
        if t == 'unicode': t = 'str'
        v = str(v) if t!='str' else "'%s'"%v
        dynattrs.append('%s = %s(%s)'%(k,t,v))

      assert not ft.get_matching_devices(dd), Exception('Device %s Already Exists!!!'%dd)
      ft.add_new_device('PyAttributeProcessor/'+instance,'PyAttributeProcessor',dd)
      ft.put_device_property(dd,'DynamicAttributes',dynattrs)
    
    done.append(dd)

  return done


  
#!/usr/bin/env  python
# -*- coding: iso-8859-15 -*-

import os,sys,time,traceback
import fandango as fd
from fandango.functional import *
import panic

global opts
opts = []

def report2text(report, columns):
    """ report should be a list of dicts or tuples """
    pass
  
def get_panic_report(api=None,timeout=3000.,tries=3, 
                     devfilter = '*',
                     attr = 'ActiveAlarms', 
                     trace=False):
    """
    The key of the results:
      key.count('/') == 0 : alarm
      == 1: server
      == 2: device
      == 4: summary
    """
  
    if api is None: api = panic.api()
    elif isString(api): api = panic.api(api)
    if not len(api.servers): 
      if devfilter == '*':
          api.servers.load_by_name('PyAlarm/*')
      elif isString(devfilter):
          api.servers.load_by_name(devfilter)
      else:
          [api.servers.load_by_name(d) for d in devfilter]
    alldevs = fd.tango.get_all_devices(exported=True)
    #print('%d devices in %s'%(len(alldevs),fd.tango.get_tango_host()))
    
    result = fd.dicts.defaultdict(dict)
    result['//alarms//'] = api.alarms.keys()
    result['//devices//'] = api.devices.keys()
    result['//servers//'] = api.servers.keys()
    result['//attrs//'] = []
    
    off = []
    hung = []
    slow = []
    aslow = []
    errors = {}
    
    for s,ss in api.servers.items():

        admin = ss.get_admin_name()
        try:
            admin = fd.parse_tango_model(admin)['device']
        except:
            print('unable to parse %s'%admin)
            continue
        if admin.lower() not in alldevs:
            off.append(admin)

        result[s]['devices'] = ss.get_classes()['PyAlarm']
        for d in result[s]['devices']:
          
            if isSequence(devfilter):
                if d not in devfilter: 
                    continue
            elif not clsearch(devfilter,d): 
                continue
          
            if admin in off:
                t = END_OF_TIME
                off.append(d)
            else:
                proxy = fd.get_device(d)
                t = get_device_timeout(d,timeout,tries,alldevs,
                      proxy,trace=False,attr=attr)
                if t == END_OF_TIME: hung.append(d)
                if t*1e3 > timeout: slow.append(d)
                
            result[d]['timeout'] = t
            result[d]['attrs'] = 0
            result[d]['alarms'] = len(api.devices[d].alarms)
            polling = float(api.devices[d].config['PollingPeriod'])
            result[d]['polling'] = polling
            
            try:
                evals = get_device_eval_times(proxy,timeout)
                teval = sum(evals.values())
                ratio = teval/float(polling)
                result[d]['eval'],result[d]['ratio'] = teval,ratio
            except:
                evals = {}
                result[d]['eval'],result[d]['ratio'] = -1,-1
            
            for a,aa in api.devices[d].alarms.items():
                attrs = api.parse_attributes(aa['formula'])
                result[d]['attrs'] += len(attrs)
                result[a]['device'] = d
                result[a]['attrs'] = attrs
                result['//attrs//'].extend(attrs)
                result[a]['timeout'] = evals.get(a,-1)
                if result[a]['timeout'] > polling/result[d]['alarms']:
                    aslow.append(a)

    result['//attrs//'] = sorted(set(map(str.lower,result['//attrs//'])))
    result['//off//'] = off
    result['//bloat//'] = [k for k in result 
          if k.count('/')==2 and result[k].get('ratio',-1)>=1.]
    result['//hung//'] = hung
    result['//slow_devices//'] = slow
    result['//slow_alarms//'] = aslow
    
    #print('off devices: %s\n'%(off))
    #print('hung devices: %s\n'%(hung))
    #print('slow devices: %s\n'%(slow))
    #print('bloat devices: %s\n'%([k for k in result 
          #if '/' in k and result[k].get('ratio',-1)>=1.]))
    #print('slow alarms: %s\n'%aslow)
    
    if '-v' in opts:
        print(fd.get_tango_host())
        for k,v in sorted(result.items()):
            if fd.isSequence(v):
                print('%s: %d'%(k,len(v)))
            elif fd.isNumber(v):
                print('%s: %d'%(k,v))

def get_panic_devices(api=None,devfilter='*',exported=False):
    api = api or panic.api()
    devs = [d.lower() for d in api.devices if clmatch(devfilter,d)]
    if exported:
        alldevs = fd.get_all_devices(exported=True)
        devs = [d for d in devs if d in alldevs]
    return devs
  
def get_device_alarms(device,timeout=10000.):
    api = panic.api()
    return sorted((k,a['formula']) for k,a in 
                  api.devices[device].alarms.items())

def get_device_timeout(device,timeout,tries=1,exported=[],
          proxy=None,attr='ActiveAlarms',trace=True):
    exported = exported or fd.tango.get_all_devices(exported=True)
    device = device.lower()
    proxy = proxy or fd.get_device(device)
    t = 0

    if device not in exported:
        if trace:
            print('%s is not exported!'%d)
        return -1

    else:
        for i in range(tries):

            try:
                proxy.set_timeout_millis(int(timeout))
                t0 = now()
                for a in proxy.get_attribute_list():
                    if clmatch(attr,a):
                        proxy.read_attribute(a)
                        time.sleep(1e-5)
                t1 = now()-t0

            except Exception,e:
                if trace:
                    print('%s failed!: %s'%(device,fd.excepts.exc2str(e)))
                #traceback.print_exc()
                t = END_OF_TIME
                break

            t += t1/float(tries)

    return t
  
    
def get_all_timeouts(api=None,devfilter='*',timeout=3000.):
    api = api or panic.api()
    devs = [d.lower() for d in api.devices if clmatch(devfilter,d)]

    print('testing %d devices on %s'%(len(devs),api.tango_host))
    times,failed, down = {},[],[]
    for d in devs:
        t = get_device_timeout(d,timeout,tries=3)
        print(d,t)
        times[d] = t
        if t<0: down.append(d)
        if t==END_OF_TIME: failed.append(d)

    print('')
    print('%d devices were not exported: %s'%(len(down),','.join(down)))
    print('%d devices failed: %s'%(len(failed),','.join(failed)))
    
    return sorted([v,k,len(api.devices[k].alarms)] for k,v in times.items())
  
def get_bad_devices(api=None,devfilter='*',timeout=3000.):
    times = get_all_timeouts(api,devfilter,timeout)
    return [t for t in times if t[-1]>0 and not 0 < t[0]*1e3 < timeout]
  
def evaluate_formula(proxy,formula,timeout=10000.):
    proxy.set_timeout_millis(int(timeout))
    r = proxy.EvaluateFormula(formula)
    try: r = eval(r)
    except: pass
    return r
  
def get_device_eval_times(proxy,timeout=10000.,total=False):
    if isString(proxy): proxy = fd.get_device(proxy)
    vals = evaluate_formula(proxy,'SELF.EvalTimes',timeout)
    if total:
        if len(vals):
            vals = sum(vals.values())
        else:
            vals = -1
    return vals
  
def get_alarm_eval_time(alarm):
    api = panic.api()
    et = get_device_eval_times(api[alarm].device)
    return et[alarm]
  
def get_alarm_data(alarm):
    api = panic.api()
    return api[alarm].to_dict()
  
def get_alarm_variables(alarm,api=None):
    api = api or panic.api()
    return api.parse_attributes(api[alarm].formula)
  
def get_alarms_variables(api=None,alarmfilter='*'):
    api = api or panic.api()
    attrs = {}
    for d,v in api.devices.items():
        for a,vv in v.alarms:
            if clmatch(alarmfilter,a):
                try:
                    attrs[a] = len(get_alarm_variables(a,api))
                except:
                    attrs[a] = -1
        ss = sum([attrs[a] for a in v.alarms if attrs[a]>0])
        print('%s : %s attributes in %s alarms'%(d,ss,len(v.alarms)))
    return attrs
                    
  
def get_devices_eval_times(api=None,devfilter='*',timeout=10000.):
    api = api or panic.api()
    devs = get_panic_devices(api,devfilter,exported=True)
    times = {}
    print('%d devices'%len(devs))
    for d in devs:
        try:
            times[d] = get_device_eval_times(d,timeout,True)
        except:
            times[d] = END_OF_TIME
    return sorted([v,k] 
                   for k,v in times.items())
  
def get_devices_eval_ratio(api=None,devfilter='*',timeout=10000.):
    api = api or panic.api()
    devs = get_panic_devices(api,devfilter,exported=True)
    times = {}
    print('%d devices'%len(devs))
    for d in devs:
        try:
            times[d] = get_device_eval_times(d,timeout,True)
        except:
            times[d] = END_OF_TIME
    return sorted([v/float(api.devices[k].config['PollingPeriod']),v,
                   k,len(api.devices[k].alarms)] 
                   for k,v in times.items())
  
def get_alarms_eval_times(api=None,alarmfilter='*',timeout=10000.):
    api = api or panic.api()
    devs = get_panic_devices(api,exported=True)
    times = {}
    for d in devs:
        try:
            et = get_device_eval_times(d,timeout,False)
        except:
            et = dict((a,END_OF_TIME) for a in api.devices[d].alarms)
            
        for a,t in et.items():
            times[d+'/'+a] = t
            
    return sorted([v,k] for k,v in times.items())
  
  
def main(args=[]):
    global opts
    opts = [a for a in args if a.startswith('-')]
    args = [a for a in args if a not in opts]
    if args:
        quiet = "-v" not in opts
        m = globals().get(args[0].strip(';'),None)
        if m and isCallable(m):
            args = map(str2type,args[1:])
            print('%s(%s)'%(m,args))
            try:
                r = m(*args)
            except:
                r = traceback.format_exc()

            if not quiet:
                if isSequence(r):
                    print('')
                    for i,t in enumerate(r):
                      print('%s: %s'%(i,fd.pprint(t)))#obj2str(t)))
                    print('')
                else:
                    if hasattr(r,'items'): r = dict(r.items())
                    print(fd.pprint(r)) #obj2str(r))
            else:
                print ''

    else:
        print('\n'.join(sorted(l for l,v in globals().items()
                               if l not in fd.functional.__dict__
                               and l!='main'
                               and isCallable(v))))
        
if __name__ == '__main__': main(sys.argv[1:])

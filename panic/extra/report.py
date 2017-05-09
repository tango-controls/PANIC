#!/usr/bin/python

import sys,os,urllib,traceback
try:
  import panic,fandango
  from fandango.functional import *
except:
  sys.path.append('/homelocal/sicilia/lib/python/site-packages')
  import panic,fandango
 
try:
  from fandango import web
except:
  web = None

def get_servers_status(regexp='*',exclude=['bpms','test','sr_vc_']):
    servers = fandango.Astor()
    servers.load_by_name('PyAlarm/*%s*'%regexp)
    servers.load_by_name('Panic*/*%s*'%regexp)
    print('%d servers loaded'%len(servers))
    states = servers.states()
    [states.pop(k) for k in states.keys() if any(e in k for e in exclude)]
    exported = fandango.get_all_devices(exported=True)
    exported = [s for s in states if 'dserver/'+s in exported]
    zombies = sorted(d for d,s in states.items() 
                     if d in exported and s is None)
    off = sorted(d for d,s in states.items() 
                 if d not in zombies and s is None)
    on = sorted(s for s in states if states[s] is not None)

    print('\n')
    for s in off:
      print('%s : %s : OFF'%(servers[s].host,s))
    for s in zombies:
      print('%s : %s : ZOMBIE!'%(servers[s].host,s))
    print('\n')

    failed = []
    for s in on:
      for d in sorted(servers[s].get_device_list()):
        if not fandango.matchCl('(sys|dserver)/*',d):
          ss = fandango.check_device(d)
          p = fandango.tango.get_device_property(d,'pollingperiod')
          if not p: print('%s has no polling defined'%d)
          elif float(p)>1000: print('%s has a wrong polling! %s'%(d,p))
          if str(ss) not in ('ALARM','ON'):
            failed.append(s)
            print('%s : %s : %s : %s' % (servers[s].host,s,d,str(ss)))
            
    print('\n%d servers have failed devices'%len(failed))
    restart = sorted(set(d for l in (off,zombies,failed) for d in l))
    print('%d servers should be restarted'%len(restart))
    print('')
            
    return {'off':off,'on':on,'zombies':zombies,
            'failed':failed,'restart':restart}
  
def restart_servers(servers = [], host = ''):
    if not servers:
      servers = get_servers_status()['restart']
    astor = fandango.Astor()
    astor.load_from_servers_list(servers)
    astor.stop_servers()
    print('waiting ...')
    fandango.wait(10.)
    for s in astor:
      host = host or astor[s].host
      print('Starting %s at %s'%(s,host))
      astor.start_servers(s,host=host)
    return

def generate_html_report(args):
    print('panic.extra.generate_html_report(%s)'%args)
    assert web,'fandango.web not available'
    OUTPUT = args[-1] if len(args) else '/srv/www/htdocs/reports/alarms.html'
    FILTER = args[1] if len(args)>1 else '*'
    HOST = os.getenv('TANGO_HOST',os.getenv('HOST'))
    print 'OUTPUT = %s, FILTER = %s, HOST= %s'% (OUTPUT,FILTER,HOST)
    api = panic.api(FILTER)
    lines = []
    severities = ['ALARM','WARNING','ERROR','INFO','DEBUG']
    txt = '<html>\n'+web.title('Active alarms in %s'%HOST,2)
    summary  = dict((k,0) for k in severities)
    values = {}
    for d in sorted(api.devices):
        try:
            dev = panic.AlarmDS(d,api).get()
            active = dev.read_attribute('ActiveAlarms').value
            values[HOST+'/'+d]=active
            if active:
                lines.append(web.title(d.upper(),3))
                lines.append(web.list_to_ulist([a for a in active]))
                for a in api.get(device=d):
                    if any(s.startswith(a.tag+':') for s in active):
                        summary[a.severity or 'WARNING']+=1
        except Exception,e:
            lines.append(web.title(d.upper(),3))
            se = traceback.format_exc()
            if 'desc =' in se: se = '\n'.join([l for l in se.split('\n') if 'desc =' in l][:1])
            lines.append('<pre>%s</pre>'%se)
    txt+=web.paragraph(', '.join('%s:%s'%(k,summary[k]) for k in severities)+'<hr>')
    txt+='\n'.join(lines)+'\n</html>'
    open(OUTPUT,'w').write(txt)
    import pickle
    pickle.dump(values,open(OUTPUT.rsplit('.',1)[0]+'.pck','w'))
    
if __name__ == '__main__': 
    action = first(sys.argv[1:] or ['help'])
    if action == 'html': 
        generate_html_report(sys.argv[2:])
    if action == 'check': 
        exclude = [a for a in sys.argv[2:] if a.startswith('!')]
        include = '|'.join([a for a in sys.argv[2:] if a not in exclude])
        args = [include or '*'] + iif(list,exclude,[],True)
        print(dict2str(get_servers_status(*args)))
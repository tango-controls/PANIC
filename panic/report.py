#!/usr/bin/python

import sys,os,urllib,traceback
try:
 import panic,fandango
 from fandango import web
except:
 sys.path.append('/homelocal/sicilia/lib/python/site-packages')
 import panic,fandango
 from fandango import web
print sys.argv
OUTPUT = sys.argv[-1] if len(sys.argv)>1 else '/srv/www/htdocs/reports/alarms.html'
FILTER = sys.argv[1] if len(sys.argv)>2 else '*'
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
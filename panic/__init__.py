import os,sys,traceback

import properties
import alarmapi as _panic
from view import AlarmView
from properties import *
from alarmapi import *
from alarmapi import Alarm,AlarmAPI,AlarmDS,api,getAttrValue
#from utils import *

try: __RELEASE__ = open(os.path.dirname(os.path.abspath(__file__))+'/VERSION').read().strip()
except Exception,e: __RELEASE__ = '6.X+'

#CLEAN DEPRECATED FILES
p = __file__.rsplit(os.path.sep,1)[0]
deprecated = [p+os.path.sep+'panic.pyc',p+os.path.sep+'panic.pyo',
              p+os.path.sep+'panic.py',p+os.path.sep+'/gui/widgets.pyo',
              p+os.path.sep+'/gui/widgets.pyc',p+os.path.sep+'/gui/widgets.py',
            ]
for p in deprecated:
    if os.path.exists(p):
        try:
            os.remove(p)
            print('%s removed ...'%p)
        except Exception,e:
            print(e)
            print('panic, CLEAN OLD FILES ERROR!:')
            print('An old file still exists at:\n\t%s'%p)
            print('Import panic as sysadmin and try again')
            print('')
            sys.exit(-1)


_proxies = _panic._proxies


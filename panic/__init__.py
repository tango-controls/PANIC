"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import os,sys,traceback

try: __RELEASE__ = open(os.path.dirname(os.path.abspath(__file__)
                                        )+'/VERSION').read().strip()
except Exception,e: __RELEASE__ = '6.X+'

#CLEAN DEPRECATED FILES
#print('panic.__init__, deprecated files checking ...')
p = __file__.rsplit(os.path.sep,1)[0]
deprecated = [p+os.path.sep+'panic.pyc',p+os.path.sep+'panic.pyo',
              p+os.path.sep+'panic.py',p+os.path.sep+'/gui/widgets.pyo',
              p+os.path.sep+'/gui/widgets.pyc',p+os.path.sep+'/gui/widgets.py',
            ]
for p in deprecated:
    #print('checking %s ...'%p)
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

import properties
import alarmapi as _panic
import alarmapi
import view

from .view import AlarmView
from .properties import *
from .alarmapi import *
from .alarmapi import Alarm,AlarmAPI,AlarmDS,api,getAttrValue
#from utils import *

_proxies = alarmapi._proxies


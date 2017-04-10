import panic as _panic
from panic import *
import os
try: __RELEASE__ = open(os.path.dirname(os.path.abspath(__file__))+'/VERSION').read().strip()
except Exception,e: __RELEASE__ = '6.X+'

_proxies = _panic._proxies


#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
##
## This file is part of Tango Control System
##
## http://www.tango-controls.org/
##
## Author: Sergi Rubio Manrique
##
## This is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This software is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
###########################################################################

__doc__ = "panic.view will contain the AlarmView class for managing"\
          "updated views of the panic system state"

import fandango as fn
from panic import *
from fandango.functional import *
from fandango.threads import ThreadedObject
from fandango.callbacks import EventSource, EventListener
from fandango.log import Logger

class AlarmView(
    EventListener,
    #ThreadedObject,
    Logger):
  
  def __init__(self,name='AlarmView',pattern='*',filters=[]):
    Logger.__init__(self,name)
    self.setLogLevel('INFO')
    EventListener.__init__(self,name)
    self.info('__init__(%s,%s)'%(pattern,filters))
    #ThreadedObject.__init__(self,period=1.,nthreads=1,start=True,min_wait=1e-5,first=0)
    
    
  def event_hook(self, src, type_, value):
    """ 
    EventListener.eventReceived will jump to this method
    Method to implement the event notification
    Source will be an object, type a PyTango EventType, evt_value an AttrValue
    """
    src = src.full_name
    value = getAttrValue(value,True)
   
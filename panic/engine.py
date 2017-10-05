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

__doc__ = "panic.engine"

import fandango.callbacks
import fandango.tango
import fandango.log as fl

global INIT_DONE
INIT_DONE = False

def init_callbacks(period_ms=200.):
    """ Configure fandango.callbacks module to process attribute readings """
    global INIT_DONE
    if not INIT_DONE:
        fl.tracer('panic.engine: init_callbacks(period_ms=%s)'%period_ms)
        fandango.callbacks.EventSource.get_thread().set_period_ms(period_ms)
        fandango.callbacks.EventThread.SHOW_ALIVE = 10000
        fandango.callbacks.EventThread.EVENT_POLLING_RATIO = 1000
        #fandango.callbacks.EventThread.MinWait = 0.01
        fandango.tango.check_device_cached.expire = 60. 
        fandango.tango.get_all_devices.set_keeptime(180)
        INIT_DONE = True
    
if __name__ == '__main__':
    init_callbacks()
    print _INIT_DONE

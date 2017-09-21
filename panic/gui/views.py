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

import os,sys,traceback
import fandango as fd
import fandango.tango as ft

from fandango.qt import Qt,getApplication
from panic.properties import SORT_ORDER

class ViewRawBrowser(Qt.QTextBrowser):
    
    def setModel(self,model,refresh=5000):
        model = getattr(model,'view',model)
        self.model = model
        if not hasattr(self,'_timer'):
            self._timer = Qt.QTimer()
            self.connect(self._timer,Qt.SIGNAL("timeout()"),
                         self.valueChanged)
            self._timer.start(refresh)
            print('AlarmForm._timer(%s)'%refresh)
        self.show()
        
    def valueChanged(self):
        txt = ['tag : '+str(SORT_ORDER)]
        for o in reversed(self.model.ordered):
            txt.append(o.tag+' : '+str(o.sortkey))
        self.setPlainText('\n'.join(txt))

class ViewChooser(Qt.QDialog):
    """
    Allows to choose an AlarmView from a list
    """
    def __init__(self,views=None):
        
        if views is None:
            print('load views from database ...')
            views = ft.get_class_devices('PanicViewDS')
            views.append(ft.get_tango_host())

        print('ViewChooser(%s)'%views)
        self.view = ''
        self.views = fd.dicts.SortedDict()
        for v in views:
            if ':' in v:
                self.views[v] = v
            else:
                desc = ft.get_device(v).Description.split('\n')[0]
                self.views[desc] = v
            
        Qt.QDialog.__init__(self,None)
        #self.setModal(True)
        self.setWindowTitle('PANIC View Chooser')
        self.setLayout(Qt.QVBoxLayout())
        self.layout().addWidget(Qt.QLabel('Choose an AlarmView'))
        self.chooser = Qt.QComboBox()
        self.chooser.addItems(self.views.keys())
        self.layout().addWidget(self.chooser)
        self.button = Qt.QPushButton('Done')
        self.layout().addWidget(self.button)
        self.button.connect(self.button,Qt.SIGNAL('pressed()'),self.done)
        self.button.connect(self.button,Qt.SIGNAL('pressed()'),self.close)
        
    def get_view(self,txt = None):
        try:
            if txt is None:
                txt = str(self.chooser.currentText())
            self.view = self.views[txt]
        except:
            traceback.print_exc()
            self.view = 'err'
        print('ViewChooser(%s) => %s'%(txt,self.view))
        return self.view
        
    def done(self,*args):
        os.environ['PANIC_VIEW'] = self.get_view()
        self.close()
        self.hide()
        
    @staticmethod
    def main(args=[]):
        app = ViewChooser(args or None)
        app.show()
        app.move(getApplication().desktop().screen().rect().center() 
                 - app.rect().center())
        app.exec_()
        #thc.open()
        return app.view
        #print(thc.view)

if __name__ == '__main__':
    app = getApplication()
    ViewChooser.main(sys.argv[1:])

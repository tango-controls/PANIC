import sys, PyTango
from utils import Qt
from taurus.qt.qtgui import container
from taurus.qt.qtgui.panel import TaurusForm

import panic
from panic.widgets import *

if __name__ == "__main__":
    qapp = Qt.QApplication([])
    device = sys.argv[1] if sys.argv else 'sys/tg_test/1'
    attr_list = ['%s/%s'%(device,a) for a in PyTango.DeviceProxy(device).get_attribute_list()]
    tmw = container.TaurusMainWindow()
    taurusForm = TaurusForm(tmw)
    taurusForm.setModel(attr_list)
    tmw.setCentralWidget(taurusForm)
    tmw.statusBar().showMessage('Ready')
    tmw.show()
    s=tmw.splashScreen()
    s.finish(tmw)
    print '*'*80

    toolbar = PanicToolbar(tmw)
    tmw.addToolBar(toolbar)

    sys.exit(qapp.exec_())

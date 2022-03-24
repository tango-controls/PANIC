"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import time,traceback,os,sys
import taurus,fandango,fandango.qt
from fandango.qt import Qt, QtCore, QtGui
from fandango.functional import *
from fandango.objects import Cached
from fandango.excepts import Catched

from taurus.qt.qtgui.base import TaurusBaseWidget
from taurus.qt.qtgui.container import TaurusWidget
from taurus.qt.qtgui.panel import TaurusForm
from taurus.core.util  import Logger

try:
    # Set tangoFormatter as default formatter 
    from taurus.qt.qtgui.base import TaurusBaseComponent
    from taurus.core.tango.util import tangoFormatter
    TaurusBaseComponent.FORMAT = tangoFormatter
except:
    print('tangoFormatter not available (Taurus < 4!?)')

import panic
from panic import getAttrValue
from panic.alarmapi import getPanicProperty, setPanicProperty
from panic.widgets import AlarmValueLabel,getThemeIcon,getIconForAlarm
import getpass

try:
    from PyTangoArchiving.widget.panel import TaurusSingleValueForm
except:
    TaurusSingleValueForm = TaurusForm

dummies = []

def get_user():
    try:
        return getpass.getuser()
    except:
        return ''
    
def clean_str(s):
    return ' '.join(str(s).replace('\r',' ').replace('\n',' ').split())

def print_clean(s):
    print(clean_str(s))

try: TRACE_LEVEL = int(os.getenv('TRACE_LEVEL',-1))
except: TRACE_LEVEL = (traceback.print_exc(),-1)[-1]

def trace(msg,head='',level=0,clean=False,use_taurus=False):
    if level > TRACE_LEVEL: return
    if type(head)==int: head,level = '',head
    msg = fandango.time2str()+':'+str(head)+('\t'*level or ' ')+str(msg)
    if use_taurus:
        if not dummies: 
            dummies.append(Logger())
            dummies[0].setLogLevel('INFO')
        print dummies[0]
        dummies[0].info(msg)
        dummies[0].error(msg)
    else:
        (print_clean if clean else fandango.printf)(msg)
    return

def get_bold_font(points=8):
    font = QtGui.QFont()
    font.setPointSize(points)
    font.setWeight(75)
    font.setBold(True)
    return font
           
def setCheckBox(cb,v):
    try:
        cb.blockSignals(True)
        cb.setChecked(v)
        cb.blockSignals(False)
    except:
        print 'Failed to setCheckBox(%s,%s)'%(cb,v)
        print traceback.format_exc()
        
def getWidgetText(widget,trace=True):
    """ helper to catch encoding exceptions in forms """
    msg = ''
    try:
        if hasattr(widget,'toPlainText'):
          msg = str(widget.toPlainText())
        else:
          msg = str(widget)
    except Exception,e:
        if 'unicode' in str(e).lower():
            #v = QtGui.QMessageBox.warning(None,'Wrong characters', \
                #'PANIC properties accept only ASCII characters, '
                #'please crosscheck your text.' \
                #QtGui.QMessageBox.Ok);
            try:org = widget.text()
            except: org = widget.toPlainText()
            msg = Qt.QInputDialog.getText(None,'Wrong characters',
                'PANIC properties accept only ASCII characters, '
                'please crosscheck your text.',Qt.QLineEdit.Normal,
                org)
            msg = getWidgetText(msg)
        else:
            #QtGui.QMessageBox.warning(None,'Wrong text',str(e))
            raise e
    if trace: print('*'*80+'\n'+'%s => %s'%(widget,msg))
    return msg
    
def getAlarmTimestamp(alarm,attr_value=None,use_taurus=True):
    """
    Returns alarm activation timestamp (or 0) of an alarm object
    """
    trace('panic.gui.getAlarmTimestamp(%s(%s),%s,%s)'
          %(type(alarm),alarm,attr_value,use_taurus))
    #Not using API method, reusing last Taurus polled attribute instead
    try:
        if attr_value is None and use_taurus:
            attr_value = taurus.Attribute(alarm.device+'/ActiveAlarms').read()
            attr_value = getAttrValue(attr_value)
        return alarm.get_time(attr_value=attr_value)
    except:
        trace('getAlarmTimestamp(%s/%s): Failed!'%(alarm.device,alarm.tag))
        trace(fandango.check_device(alarm.device) and traceback.format_exc())
        return 0 #In case of error it must always return 0!!! 
                #(as it is used to set alarm.active)
    
def getAlarmReport(alarm,parent=None):
    print 'getAlarmReport(%s(%s))'%(type(alarm),alarm)
    try:
        if type(alarm) is panic.Alarm:
            alarm = alarm
        elif type(alarm) is str:
            alarm=panic.current()[alarm]
        else:
            alarm=str(alarm.path()).split('.',1)[0]
        details=''#<pre>'
        details+=str(taurus.Device(alarm.device).command_inout(
            'GenerateReport',[alarm.tag])[0])
        #details+='\n\n<a href="'+str(tb.windowTitle())+'">'\
        #+str(tb.windowTitle())+'</a>'
        #details+='</pre>'
    except:
        details = ("<h2>Unable to get Alarm details from %s/%s </h2>"
                   %(alarm.device,alarm.tag))
        details += ('\n\n'+ '-'*80 +'\n\n'+'<pre>%s</pre>'
                    %traceback.format_exc())
    widget = Qt.QDialog(parent)
    widget.setLayout(Qt.QVBoxLayout())
    msg = 'Last %s report:'%alarm.tag
    widget.setWindowTitle(msg)
    print '%s\n%s'%(msg,details)
    widget.layout().addWidget(Qt.QLabel(msg))
    tb = Qt.QTextBrowser(widget)
    tb.setPlainText(details)
    tb.setMinimumWidth(350)
    widget.layout().addWidget(tb)
    widget.setMinimumWidth(350)
    bt = Qt.QDialogButtonBox(Qt.QDialogButtonBox.Ok,Qt.Qt.Horizontal,widget)
    widget.layout().addWidget(bt)
    bt.connect(bt,Qt.SIGNAL("accepted()"),widget.accept)
    return widget
        
def formatAlarm(f):
    from fandango import replaceCl
    if len(f)<80: return f
    else: return 
    
def line2multiline(line,maxwidth=60):
    line = multiline2line(line)
    import re
    def linesplit(l,char):
        if maxwidth<max(len(s) for s in l.split('\n')):
            if re.search('[ ]%s[ ]'%char,l):
                l = clsub('[ ]%s[ ]'%char,'\n%s '%char,l)
        return l
        
    for c in ('else','if','OR','or','AND','and','for','FIND'):
        if len(line)<maxwidth: return line
        line = linesplit(line,c)
        
    return line

def multiline2line(lines):
    bads = '\n\r\t'
    for b in bads:
        lines = lines.replace(b,' ')
    lines = ' '.join(l for l in lines.split() if l)
    return lines

###############################################################################

class iValidatedWidget(object):
    """
    This Class assumes that you have a self.api=PanicAPI() member 
    in your subtype 
    
    Typical usage:
    
        self.setAllowedUsers(self.api.get_admins_for_alarm(len(items)==1 
                and items[0].get_alarm_tag()))
        if not self.validate('onDisable/Enable(%s,%s)'
                %(checked,[a.get_alarm_tag() for a in items])):
            return
            
    This Class requires PanicAdminUsers and UserValidator PyAlarm properties 
    to be declared.
    
      PanicAdminUsers : [root, tester]
      UserValidator : user_login.TangoLoginDialog
    
    """
    KEEP = int(first(getPanicProperty('PanicUserTimeout'),None) or 60)
    
    def init(self,tag=''):
      
        if not hasattr(self,'validator'):
          print('>#'*40)
          self.UserValidator,self.validator = '',None
          log,p = '',str(sys.path)
          try:
              props = getPanicProperty(['UserValidator','PanicAdminUsers'])
              self.UserValidator = fandango.first(props['UserValidator'],'')
              self.AdminUsers = filter(bool,
                                       map(str.strip,props['PanicAdminUsers']))
              if self.UserValidator:
                mod,klass = self.UserValidator.rsplit('.',1)
                mod = fandango.objects.loadModule(mod)
                p = mod.__file__
                klass = getattr(mod,klass)
                self.validator = klass()
                try:
                    log = (getPanicProperty('PanicLogFile') or [''])[0]
                    if log: self.validator.setLogging(True,log)
                except:
                    print('Unable to write log %s'%log)
                    traceback.print_exc()
          except:
              traceback.print_exc()
              print('iValidateWidget: %s module not found in %s'
                    %(self.UserValidator or 'PyAlarm.UserValidator',p))
              return -1

        if self.AdminUsers and not self.UserValidator:
            print(self.AdminUsers,self.UserValidator)
            raise Exception,\
                'iValidateWidget(PanicAdminUsers):'\
                    ' UserValidator property not defined'
            return -1
        if not self.AdminUsers and not self.UserValidator:
            #passwords not available
            return None
        users = sorted(self.api.get_admins_for_alarm(tag))
        if not users: 
            #Not using passwords for this alarm
            self.last_users = None
            return None
        elif self.validator is None:
            #Failed to initialize
            return -1
        else:
            if users != getattr(self,'last_users',[]):
                self.last_valid = 0
            self.validator.setAllowedUsers(users)
            self.last_users = users
            return self.validator
        
    def setAllowedUsers(self,users):
        if self.init() is None: return
        self.validator.setAllowedUsers(users)
        
    def validate(self,msg='',tag=''):
        if getattr(self,'last_valid',0) > time.time()-self.KEEP:
          r = True
          
        else:
          err = self.init(tag)
          if err is None: 
            return True
          if err == -1:
            msg = "%s module not found"%(
                self.UserValidator or 'PyAlarm.UserValidator')
            print('iValidateWidget: %s'%msg)
            Qt.QMessageBox.critical(None,
                "Error!",msg,
                QtGui.QMessageBox.AcceptRole, QtGui.QMessageBox.AcceptRole)
            return False
          
          self.validator.setLogMessage('AlarmForm(%s).Validate(%s): %s'
                                %(tag,msg,tag and self.api[tag].to_str()))
          #print('LdapValidUsers %s'%self.validator.getAllowedUsers())
          r = self.validator.exec_() if self.validator.getAllowedUsers() \
                            else True
          
        if r: self.last_valid = time.time()
        return r

class WindowManager(fandango.objects.Singleton):
    WINDOWS = []
    def __init__(self):
        pass
    @classmethod
    def newWindow(klass,Type,args):
        return klass.addWindow(Type(*args))
    @classmethod
    def addWindow(klass,obj):
        if obj not in klass.WINDOWS:
            klass.WINDOWS.append(obj)
        return obj
    @classmethod
    def getWindows(klass):
        return klass.WINDOWS
    @classmethod
    def getWindowsNames(klass):
        names = []
        for w in klass.WINDOWS:
            try: names.append(str(w.windowTitle()))
            except:pass
        return names
    @classmethod
    def getWindow(klass,window):
        if not fandango.isString(window):
            if window in klass.WINDOWS: 
                return window
        else:
            for w in klass.WINDOWS:
                try:
                    if w.windowTitle()==window:
                        return w
                except:pass
        return None
    @classmethod
    def putOnTop(klass,window):
        w = klass.getWindow(window)
        if 0: #w.isVisible(): #Doesn't work properly
            w.setFocus()
        else:
            (w.hide(),w.show())
    @classmethod
    def closeAll(klass):
        print 'In WindowManager.closeAll(%s)'%klass
        for w in klass.WINDOWS:
            try: w.close()
            except Exception,e: '%s.close() failed: %s'%(w,e)
    def closeKlass(klass,target):
        for w in klass.WINDOWS:
            if isinstance(w,target):
                try: w.close()
                except Exception,e: '%s.close() failed: %s'%(w,e)

class CleanMainWindow(Qt.QMainWindow,WindowManager):
    def closeEvent(self,event): 
        self.closeAll()
    

###############################################################################

global SNAP_ALLOWED
SNAP_ALLOWED = True

def get_snap_api():
    trace('get_snap_api()',level=-1)
    global SNAP_ALLOWED
    if SNAP_ALLOWED is True:
      try:
          from PyTangoArchiving import snap
          #from PyTangoArchiving.widget.snaps import *
          db = panic.alarmapi.get_tango() #fandango.get_database()
          assert list(db.get_device_exported_for_class('SnapManager'))
          SNAP_ALLOWED = snap.SnapAPI(load=False)
          
      except Exception,e:
          trace('PyTangoArchiving.Snaps not available: '\
              'HISTORY VIEWER DISABLED: '+traceback.format_exc(),'WARNING',-1)
          SNAP_ALLOWED = None
    
    trace('get_snap_api(): %s'%SNAP_ALLOWED,level=-1)
    return SNAP_ALLOWED

def get_archive_trend(models=None,length=4*3600,show=False):
    # This method is to be added to 
    # PyTangoArchiving.widgets.trend in next releases
    import taurus.qt.qtgui.plot as tplot
    import taurus.external.qt as xqt
    
    tt = tplot.TaurusTrend()
    try:
        tt.setXDynScale(True)
        tt.setUseArchiving(True)
        tt.setModelInConfig(False)
        tt.disconnect(tt.axisWidget(tt.xBottom), 
                      Qt.SIGNAL("scaleDivChanged ()"), tt._scaleChangeWarning)
        xMax = time.time() #tt.axisScaleDiv(Qwt5.QwtPlot.xBottom).upperBound()
        rg = length #abs(self.str2deltatime(str(self.ui.xRangeCB.currentText())))
        xMin=xMax-rg
        tt.setAxisScale(xqt.Qwt5.QwtPlot.xBottom,xMin, xMax)
        if models: tt.setModel(models)
        if show: tt.show()
        tt.setWindowTitle('Trend')
    except:
        print 'Exception in set_pressure_trend(%s)'%tt
        print traceback.format_exc()
    return tt
        
###############################################################################
        
class AlarmFormula(Qt.QSplitter): #Qt.QFrame):
  
    def __init__(self,model=None,parent=None,device=None,
                 _locals=None,allow_edit=False):
        Qt.QWidget.__init__(self,parent)
        #Singletone, reuses existing object ... Sure? 
        #What happens if filters apply?
        self.api = panic.current() 
        self.setModel(model,device)
        if _locals: self._locals.update(_locals)
        self.test = self.api._eval #fandango.TangoEval()
        #self.test._trace = True
        self.allow_edit = False
        self.initStyle()
        
    def setModel(self,model=None,device=None):
        if model and model in self.api:
            self.obj = self.api[model]
            self.formula = self.obj.formula
        else:
            self.obj = model if hasattr(model,'formula') else None
            self.formula = model if self.obj is None else self.obj.formula
            
        self.device = device or getattr(self.obj,'device',None)
        self._locals = device and \
            dict(zip('DOMAIN FAMILY MEMBER'.split(),self.device.split('/'))) \
                or {}
        
    @staticmethod
    def showAlarmFormula():
        d = Qt.QDialog()
        d.setLayout(Qt.QVBoxLayout())
        d.layout().addWidget(AlarmFormula())
        d.exec_()
        return d
        
    def initStyle(self,show=False):
        print 'In AlarmFormula.initStyle(%s)' %(self.obj or self.formula)
        try:
            self.org_formula = self.formula
            self.setChildrenCollapsible(False)
            self.setOrientation(Qt.Qt.Vertical)
            ###################################################################
            upperPanel = Qt.QFrame() #self
            upperPanel.setLayout(Qt.QGridLayout())
            self.insertWidget(0,upperPanel)
            self.editcb = Qt.QCheckBox('Edit')
            self.undobt = Qt.QPushButton()
            self.savebt = Qt.QPushButton()
            l = Qt.QLabel('Formula:')
            l.setFont(get_bold_font())

            self.tf = fandango.qt.QDropTextEdit() #Qt.QTextBrowser()
            self.tf.setMinimumHeight(80)
            if self.obj is not None:
                self.tf.setClickHook(self.onEdit)
                #@todo setClickHook stop working for unknown reasons !?!?!
                self.tf.setReadOnly(True)
                self.tf.setEnabled(False)
                self.connect(self.editcb,Qt.SIGNAL('toggled(bool)'),self.onEdit)
                upperPanel.layout().addWidget(self.editcb,0,4,1,1)
                self.undobt.setIcon(getThemeIcon('edit-undo'))
                self.undobt.setToolTip('Undo changes in formula')
                self.undobt.setEnabled(True)
                self.connect(self.undobt,Qt.SIGNAL('pressed()'),self.undoEdit)
                upperPanel.layout().addWidget(self.undobt,0,5,1,1)
                self.savebt.setIcon(getThemeIcon('media-floppy'))
                self.savebt.setToolTip('Save Alarm Formula')
                self.savebt.setEnabled(False)
                upperPanel.layout().addWidget(self.savebt,0,6,1,1)
                self.connect(self.savebt,Qt.SIGNAL('pressed()'),self.onSave)

            upperPanel.layout().addWidget(l,0,0,1,1)
            u = 2
            upperPanel.layout().addWidget(self.tf,1,0,u,7)    
            ###################################################################
            #lowerPanel,row = Qt.QFrame(),0 #self,2
            #lowerPanel.setLayout(Qt.QGridLayout())
            #self.insertWidget(1,lowerPanel)
            #l = Qt.QLabel('Result:')
            #l.setFont(get_bold_font())
            #lowerPanel.layout().addWidget(l,row,0,1,1)
            self.tb = Qt.QTextEdit()
            self.tb.setMinimumHeight(50)
            self.tb.setReadOnly(True)
            self.redobt = Qt.QPushButton("Evaluate")
            self.redobt.setIcon(getThemeIcon('view-refresh'))
            self.redobt.setToolTip('Update result')
            self.connect(self.redobt,Qt.SIGNAL('pressed()'),self.updateResult)
            #lowerPanel.layout().addWidget(self.redobt,row,6,1,1)
            #lowerPanel.layout().addWidget(self.tb,row+1,0,1,7)
            upperPanel.layout().addWidget(self.redobt,u+1,5,1,2)
            ###################################################################
            #Refresh from formula:
            if self.formula: self.updateFormula(self.formula)
            if show: self.show()
            print 'AlarmFormula.initStyle(%s) finished.'%self.formula
        except:
            print traceback.format_exc()
            print 'Unable to show AlarmFormula(%s)'%self.formula
            
    def onEdit(self,checked=True):
        print 'In AlarmFormula.onEdit(%s)'%checked
        self.tf.setReadOnly(not checked)
        self.tf.setEnabled(checked)
        #Order is not trivial, to avoid recursion
        self.editcb.setChecked(checked) 
        if self.updateFormula()!=self.org_formula and not checked:
            self.undoEdit()
        self.savebt.setEnabled(self.updateFormula()!=self.org_formula)
        if checked: self.emit(Qt.SIGNAL("onEdit()"))
        else: self.emit(Qt.SIGNAL("onReadOnly()"))
        
    def onSave(self,ask=False):
        print 'In AlarmFormula.onSave()'
        if ask:
            v = QtGui.QMessageBox.warning(None,'Pending Changes', \
                'Do you want to save %s changes?'%self.obj.tag, \
                QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel);
            if v == QtGui.QMessageBox.Cancel: return
        f = self.toPlainText()
        self.obj.setup(formula=f,write=True)
        self.org_formula = f
        self.emit(Qt.SIGNAL("onSave"),self.obj)
        
    def onClose(self):
        print 'In AlarmFormula.onClose()'
        if self.obj and self.toPlainText()!=self.org_formula:
            v = QtGui.QMessageBox.warning(None,'Pending Changes', \
                '%s Formula has been modified, '\
                    'do you want to save your changes?'%self.obj.tag, \
                QtGui.QMessageBox.Ok|QtGui.QMessageBox.Cancel);
            if v == QtGui.QMessageBox.Cancel: return
            self.onSave()
        self.emit(Qt.SIGNAL("onClose()"))
        
    def undoEdit(self):
        print 'In AlarmFormula.undoEdit()'
        self.updateFormula(self.org_formula)
        if self.editcb.isChecked(): self.onEdit(False)
        
    def isEditable(self):
        return self.editcb.isChecked()
    
    def setReadOnly(self,checked): 
        self.onEdit(not checked)
    def setClickHook(self,hook):
        self.tf.setClickHook(hook)
    def clear(self): 
        self.tf.clear()
    def setText(self,text): 
        self.updateFormula(text)
    def toPlainText(self,text=None): 
        return multiline2line(text or str(self.tf.toPlainText()))
            
    def updateFormula(self,formula = '',parse=True):
        """
        This method will take the formula text box and will store two variables:
         - self.formula: unprocessed formula in a single row
         - self.test.formula: formula with all alarms and attributes replaced
        """
        text = getWidgetText(self.tf)
        self.formula = formula or multiline2line(text)
        self.tf.setPlainText(line2multiline(self.formula))
        if self.org_formula is None: self.org_formula = formula
        print('In AlarmFormula.updateFormula(%s,changed=%s)'
              %(self.formula,formula!=self.org_formula))
        if self.formula: 
            self.test.formula = self.api.replace_alarms(self.formula)
        if parse: 
            self.test.formula = self.test.parse_formula(self.test.formula)
        new_text = line2multiline('%s'%self.test.formula)
        self.tb.setToolTip(new_text)
        return self.test.formula
            
    def updateResult(self,formula = ''):
        print('In AlarmFormula.updateResult(%s(%s))'%(type(formula),formula))
        formula = self.updateFormula(formula,parse=not self.device)
        if self.org_formula and formula!=self.org_formula: 
            print('\tformula changed!')
        print('\n'.join(map(str,zip('obj device formula test'.split(),
                        (self.obj,self.device,formula,self.test.formula)))))
        if formula:
            try:
                result = '%s: %s'%(self.device,
                    self.api.evaluate(
                        formula if self.device else self.test.formula,
                        device=self.device,timeout=10000,_locals=self._locals))
            except Exception,e: 
                result = '%s: %s: %s' % (self.device,type(e).__name__,e)
                print result
        else:
            result = traceback.format_exc()
            print result
        self.tb.setPlainText('%s'%result)
        self.tb.setParent(self,Qt.Qt.Dialog)
        self.tb.setWindowModality(Qt.Qt.WindowModal)
        self.tb.show()
        vals = self.api.parse_attributes(self.test.formula)
        models=[]
        
class AttributesPreview(Qt.QFrame):
    
    def __init__(self,model='',parent=None,source=None):
        Qt.QWidget.__init__(self,parent)
        self.model = model
        self.source = source
        self.test = panic.current()._eval
        self.test._trace = True
        self.initStyle()
        self.updateAttributes(self.model)
        
    def initStyle(self):
        print 'In AttributesPreview.initStyle()'
        try:
            self.setLayout(Qt.QGridLayout())
            self.redobt = Qt.QPushButton()
            self.redobt.setIcon(getThemeIcon('view-refresh'))
            self.redobt.setToolTip('Update result')
            self.form = TaurusSingleValueForm()
            self.form.setWithButtons(False)            
            self.form.setWindowTitle('Preview')
            self.layout().addWidget(self.redobt,0,6,1,1)
            self.layout().addWidget(
                Qt.QLabel('Values of attributes used in the Alarm formula:'),
                0,0,1,1)
            self.layout().addWidget(self.form,1,0,1,7)
            self.connect(self.redobt,Qt.SIGNAL('pressed()'),
                         self.updateAttributes)
        except:
            print traceback.format_exc()
    
    @Catched
    def updateAttributes(self,model=None):
        print('AttributesPreview.updateAttributes(%s)'%model)
        if not model and self.source:
            try:
                if hasattr(self.source,'formula'): model = self.source.formula
                elif hasattr(self.source,'__call__'): model = self.source()
                else: model = str(self.source or '')
            except: print(traceback.format_exc())
        
        if not fandango.isSequence(model): 
            ms,model = self.test.parse_variables(model or ''),set()
            for var in ms:
                dev,attr = var[0],var[1]
                if ':' in dev and not dev.startswith('tango://'):
                    dev = 'tango://'+dev
                model.add(dev+'/'+attr)
            
        self.model = sorted(model)
        print('In AttributesPreview.updateAttributes(%s)'%model)
        self.form.setModel(model)
        [tvalue.setLabelConfig("<attr_fullname>") 
            for tvalue in self.form.getItems()]
        print('In AttributesPreview.updateAttributes(%s)'%'done')
        
    ###########################################################################

class AlarmPreview(Qt.QDialog):
    
    def __init__(self,tag=None,formula=None,parent=None,allow_edit=False):
        Qt.QDialog.__init__(self,parent)
        self.tag = getattr(tag,'tag',tag or '')
        self.formula = formula
        #Singletone, reuses existing object ... Sure? 
        #What happens if filters apply?
        self.api = panic.current() 
        self.initStyle()
    
    @staticmethod
    def showCurrentAlarmPreview(gui,tag=None,formula=None):
        """It gets current Alarm from GUI and tries to show it up"""
        form = AlarmPreview(tag=tag or gui.getCurrentAlarm(),
                            formula=formula or None,parent=gui.parent())
        #form.exec_()
        form.show()
        gui.connect(gui,Qt.SIGNAL('closed()'),form.close)
        return form
        
    @staticmethod
    def showEmptyAlarmPreview(gui=None):
        print('In AlarmPreview.showEmptyAlarmPreview(%s)'%type(gui))
        form = getattr(gui,'_AlarmFormulaPreview',None) or AlarmPreview()
        form.setModal(False)
        if not gui:
            #using exec_ to avoid "C++ object has been deleted" error
            form.exec_() 
        else:
            if gui: gui._AlarmFormulaPreview = form
            gui.connect(gui,Qt.SIGNAL('closed()'),form.close)
            form.show()
        return form
            
    def initStyle(self,show=False):
        tag,formula = self.tag,self.formula 
        #tag = getattr(tag,'tag',tag) or self.tag
        #formula = formula or getattr(obj,'formula','') or self.formula
        self.org_formula = formula
        print 'In AlarmPreview.updateStyle(%s,%s)' %(tag,formula)
        try:
            self.setLayout(Qt.QVBoxLayout())
            self.setMinimumSize(500, 500)
            self.frame = Qt.QSplitter()
            self.frame.setOrientation(Qt.Qt.Vertical)
            self.layout().addWidget(self.frame)
            self.upperPanel = AlarmFormula(self.tag or formula)
            self.lowerPanel = AttributesPreview(
                                        source=self.upperPanel.updateFormula)
            self.lowerPanel.setMinimumHeight(250)
            self.frame.insertWidget(0,self.upperPanel)
            self.frame.insertWidget(1,self.lowerPanel)
            self.setWindowTitle("%s Alarm Formula Preview"%(tag or ''))
            #Refresh from formula:
            #upperPanel.updateFormula(formula)
            if self.upperPanel.formula: self.lowerPanel.updateAttributes()
            if show: self.show()
            print 'AlarmGUI.showAlarmPreview(%s) finished.'%tag
            print self.frame.sizes()
        except:
            print traceback.format_exc()
            print 'Unable to showAlarmPreview(%s)'%tag
            
    def closeEvent(self,event):
        self.upperPanel.onClose()
        
    def getAlarmReport(self, url):
        try:
          if type(url) is str:
            alarm=url
          else:
            alarm=str(url.path()).split('.',1)[0]
          details=''#<pre>'
          details+=str(taurus.Device(self.api[alarm].device
                        ).command_inout('GenerateReport',[alarm])[0])
          #details+='\n\n<a href="'+str(tb.windowTitle())+'">'
          #+str(tb.windowTitle())+'</a>'
          #details+='</pre>'
        except:
          details = ("<h2>Unable to get Alarm details from %s/%s </h2>"
                     %(self.api[alarm].device,alarm))
          details += ('\n\n'+ '-'*80 +'\n\n'+'<pre>%s</pre>'
                      %traceback.format_exc())
        return details
          
###############################################################################
# GUI utils

def addOkCancelButtons(widget,cancel=True):
    qb = Qt.QDialogButtonBox(widget)
    qb.addButton(qb.Ok)
    if cancel: qb.addButton(qb.Cancel)
    widget.layout().addWidget(qb)
    widget.connect(qb,Qt.SIGNAL("accepted()"),widget.accept)
    if cancel: widget.connect(qb,Qt.SIGNAL("rejected()"),widget.reject)
    return
    
def AlarmsSelector(alarms,text='Choose alarms to modify',):
    qw = Qt.QDialog()
    qw.setModal(True)
    qw.setLayout(Qt.QVBoxLayout())
    qw.layout().addWidget(Qt.QLabel(text))
    qw.layout().addWidget(Qt.QLabel())
    [qw.layout().addWidget(Qt.QCheckBox(a,qw)) for a in alarms]
    addOkCancelButtons(qw)
    if qw.exec_():
        alarms = [str(c.text()) for c in qw.children() 
                  if isinstance(c,Qt.QCheckBox) and c.isChecked()]
    else: 
        alarms = []
    return alarms
    
class clickableQLineEdit(QtGui.QLineEdit):
    """
    This class is a QLineEdit that executes a 'hook' method 
    every time is double-clicked\
    """
    def __init__(self,*args):#,**kwargs):
      self.my_hook = None
      QtGui.QLineEdit.__init__(self,*args)#,**kwargs)

    def setClickHook(self,hook):
      """ the hook must be a function or callable """
      self.my_hook = hook #self.onEdit

    def mouseDoubleClickEvent(self,event):
      if self.my_hook is not None:
        self.my_hook()
      else:
        try: QtGui.QLineEdit.mouseDoubleClickEvent(self)
        except: pass

class clickableQTextEdit(QtGui.QTextEdit):
    """
    This class is a QLineEdit that executes a 'hook' method 
    every time is double-clicked\
    """
    def __init__(self,*args):#,**kwargs):
      self.my_hook = None
      QtGui.QTextEdit.__init__(self,*args)#,**kwargs)

    def setClickHook(self,hook):
      """ the hook must be a function or callable """
      self.my_hook = hook #self.onEdit

    def mouseDoubleClickEvent(self,event):
      if self.my_hook is not None:
        self.my_hook()
      else:
        try: QtGui.QTextEdit.mouseDoubleClickEvent(self)
        except: pass

###############################################################################
        
#class htmlWidget(QtGui.QWidget):
    #def __init__(self,parent=None):
        #QtGui.QWidget.__init__(self,parent)
        #self._htmlW = htmlviewForm()
        #self._htmlW.htmlviewSetupUi(self)

    #def buildReport(self, alarm):
        #self._htmlW.buildReport(alarm)

    ##def displayReport(self, report):
        ##self._htmlW.displayReport(report)

    #def show(self):
        #QtGui.QWidget.show(self)

if __name__ == '__main__':
    import sys
    qapp = Qt.QApplication(sys.argv)
    form = AlarmPreview(*sys.argv[1:])
    form.show()
    qapp.exec_()

try:
    from fandango.doc import get_fn_autodoc
    __doc__ = get_fn_autodoc(__name__,vars())
except:
    import traceback
    traceback.print_exc()

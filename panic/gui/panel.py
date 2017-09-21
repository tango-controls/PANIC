"""
This file belongs to the PANIC Alarm Suite, 
developed by ALBA Synchrotron for Tango Control System
GPL Licensed 
"""

import sys, os, traceback, time
import fandango as fd
from fandango.qt import Qt, QtCore, QtGui, DoubleClickable

import panic
from panic import AlarmAPI, AlarmView
from panic.gui.actions import QAlarmManager

 
@DoubleClickable
class QAlarmPanelLabel(Qt.QLabel):
    
    def __init__(self,*args,**kwargs):
        Qt.QLabel.__init__(self,*args)
        self._alarm = kwargs.get('alarm',None)

    def mousePressEvent(self, event):
        '''reimplemented to provide drag events'''
        #QtKlass.mousePressEvent(self, event)
        Qt.QLabel.mousePressEvent(self,event)
        if self._alarm:
            print('mouse over %s'%(self._alarm.tag))
            self.parent().setCurrentAlarm(self._alarm)
            self.parent()._manager = self            
            if event.button() == Qt.Qt.RightButton: 
                #self.dragStartPosition = event.pos()        
                self.parent().onContextMenu(event.pos())
                
class QAlarmPanelWidget(Qt.QWidget):
    
    def __init__(self,parent=None):
        Qt.QWidget.__init__(self,parent)
        self.setLayout(Qt.QVBoxLayout())
        self.bar = Qt.QWidget()
        self.bar.setLayout(Qt.QHBoxLayout())
        self.bar.setMaximumHeight(50)
        self.modelline = Qt.QLineEdit()
        self.modelbt = Qt.QPushButton('Apply')
        map(self.bar.layout().addWidget,(self.modelline,self.modelbt))
        self.main = QAlarmPanel(self)
        map(self.layout().addWidget,(self.bar,self.main))    
        
    def setModel(self,model=None):
        if model is None: model = str(self.modelline.text())
        else: self.modelline.setText(str(model))
        self.bar.hide()        
    
class QAlarmPanel(QAlarmManager,Qt.QWidget):
    
    REFRESH_TIME = 3000
    
    def setModel(self,model=None,rows=0,cols=0,side=0,fontsize=0,**kwargs):
        print('QAlarmPanel.setModel(%s)'%model)
        import panic,math
        
        if isinstance(model,AlarmView):
            self.view = model
            self.api = self.view.api
        else: #if fd.isString(model):
            self.api = panic.AlarmAPI(model,extended=True)
            self.view = AlarmView(api=self.api,verbose=False)
            
        self.tags = self.view.sort(sortkey=('priority','tag'),keep=False)
        self.alarms = self.view.alarms
        self.old_devs = set()
        self.actives = []
        self.panels = []
        self.setCurrentAlarm(None)
        
        self.fontsize = fontsize
        
        if rows and not cols:
            self.rows = int(rows)
            self.cols = int(math.ceil((1+len(self.tags))/self.rows))
        elif cols and not rows:
            self.rows = int(math.ceil((1+len(self.tags))/cols))
            self.cols = int(cols)
        else:
            self.cols = int(cols or math.ceil(math.sqrt(1+len(self.tags))))
            self.rows = int(rows or ((self.cols-1) 
                     if self.cols*(self.cols-1)>=1+len(self.tags)
                     else self.cols))
        
        self.setLayout(Qt.QGridLayout())
        self.labels = []
        for i in range(self.rows):
            self.labels.append([])
            for j in range(self.cols):
                self.labels[i].append(QAlarmPanelLabel(self))
                self.layout().addWidget(self.labels[i][j],i,j,1,1)
        self.logo = self.labels[-1][-1]
        self.logo.setClickHook(self.showGUI)
                
        self._title = 'PANIC Alarm Panel (%s)'%str(
                                                model or fd.get_tango_host())
        self.setWindowTitle(self._title)
        url = os.path.dirname(panic.__file__)+'/gui/icon/panic-6-big.png'
        px = Qt.QPixmap(url)
        self.setWindowIcon(Qt.QIcon(px))        
        #self.labels[self.rows-1][self.cols-1].resize(50,50)        

        print('QAlarmPanel(%s): %d alarms , %d cols, %d rows: %s'
              %(model,len(self.tags),self.cols, self.rows, 
                fd.log.shortstr(self.tags)) + '\n'+'#'*80)
                
        self.refreshTimer = Qt.QTimer()
        Qt.QObject.connect(self.refreshTimer, 
                           Qt.SIGNAL("timeout()"), self.updateAlarms)

        self.refreshTimer.start(self.REFRESH_TIME)
        side = side or (min((self.rows,self.cols))==1 and 50) or 50#70#120
        if all((cols,rows,side)):
            width,height = side*cols,side*rows
            self.logo.setPixmap(px.scaled(side,side))
        else:
            width,height = min((800,side*self.cols)),min((800,side*self.rows))
            self.logo.setPixmap(px.scaled(side,side)) #70,70))
            #px.scaled(height/self.rows,height/self.rows))
        #if (width/self.rows)>=50: 
        self.resize(width,height)
        self.show()
        
    def closeEvent(self,event):
        self.stop()
        Qt.QWidget.closeEvent(self,event)
        
    def stop(self):
        self.refreshTimer.stop()
        
    def updateAlarms(self):
        # Sorting will be kept at every update
        c = 0
        for i in range(self.rows):
            for j in range(self.cols):
                if c >= len(self.tags): break
                self.updateCell(i,j,self.alarms[self.tags[c]])
                c += 1
        self.setWindowTitle(self._title+': '+fd.time2str())
        self.refreshTimer.setInterval(self.REFRESH_TIME)
        
    def showGUI(self):
        from panic.gui import AlarmGUI
        self.alarmApp = AlarmGUI(parent=self,
                            filters='*',#'|'.join(args),
                            api=self.api,
                            #options=opts,
                            mainwindow=True)
        self.alarmApp.show()
        
    def updateCell(self,i,j,alarm):
        changed = True
        label = self.labels[i][j]
        label._alarm = alarm
        
        if alarm.state in ('OOSRV','ERROR'):
            color = 'white'
            font = ['grey','red'][alarm.state=='ERROR']
        elif alarm.active:
            if alarm.tag in self.actives:
                changed = False
            else:
                self.actives.append(alarm.tag)
                
            if alarm.priority in ('ALARM','ERROR'):
                color = 'red'
                font = 'white'
            elif alarm.priority == 'WARNING':
                color = 'orange'
                font = 'white'
            else:
                color = 'yellow'
                font = 'grey'
                
        elif str(alarm.state) == 'NORM':
            if alarm.tag not in self.actives:
                changed = False
            else:
                self.actives.remove(alarm.tag)
            color = 'lime'
            font = 'grey'
        else:
            color = 'grey'
            font = 'black'
            
        minfont = 7 #6
        size = self.fontsize or max(minfont,int(140/self.cols))
        ssheet = ("QLabel { background-color : %s; color : %s; "
            "font : bold %dpx ; qproperty-alignment : AlignCenter; }"
            %(color,font,size))
        label.setStyleSheet(ssheet)
        
        try:
            if not label.getClickHook():
                f = lambda a=alarm,s=self:s.showPanel(a)
                label.setClickHook(f)
        except:
            traceback.print_exc()
            
        tooltip = str(label.toolTip()).split('<pre>')[-1].split('</pre>')[0]
        if not tooltip: changed = True
        sep = '\n' #'<br>\n\r'
        try:
            if alarm.state not in ('OOSRV','ERROR'):
                if changed:
                    #print('updateCell(%s,%s,%s,%s,%s)'%(
                        #i,j,alarm,alarm.active,alarm.state))                    
                    dp = alarm.get_ds().get()
                    if alarm.get_ds().get_version() < '6.2.0':
                        r = dp.GenerateReport([alarm.tag])
                    else:
                        r = dp.GetAlarmInfo([alarm.tag,
                                            'SETTINGS','STATE','VALUES'])
                    r = [w for l in r for w in l.split('\n')]
                    tooltip = sep.join(fd.log.shortstr(l.strip()) for l in r)
            else:
                tooltip = self.view.get_alarm_as_text(alarm,sep=sep)
        except:
            traceback.print_exc()
            self.old_devs.add(alarm.device)
            tooltip = self.view.get_alarm_as_text(alarm,sep=sep)
            
        label.setToolTip('<p style="font-size:10px; '
            'qproperty-alignment: AlignLeft; '
            'background-color:white; '
            'color: grey"><pre>%s</pre></p>'%tooltip)
        
        text = '\n'.join(self.minsplit(alarm.tag,))
                                       #minsplit=int(80/(2*self.cols))))
        #text += '\n%s'%alarm.priority.lower()
        label.setText(text)
        #"QLabel { background-color : %s; color : black; font : bold 20px ;
        #qproperty-alignment : AlignCenter; }"%(['red','lime','lime','yellow']
        
    def showPanel(self,alarm):
        import panic.gui.editor
        app = panic.gui.editor.AlarmForm()
        self.panels.append(app)
        app.setAlarmData(alarm)
        app.show()
        
    @staticmethod
    def minsplit(seq,sep='_',minsplit=None):
        if minsplit is None: minsplit = max(map(len,seq.split(sep)))
        o,r,i = seq,[],0
        while 0 <= i < len(seq):
            seq = seq[i:]
            i = seq.find(sep,minsplit)
            q = seq[:i]
            if i>0 and q: 
                r.append(q)
                i+=1
            else:
                r.append(seq)
        if len(r)==1 and len(r[0])>minsplit: r = r[0].rsplit(sep,1)
        #print('minsplit(%s): %s'%(o,r))
        return r        

    @staticmethod
    def main(*args):
        import fandango,fandango.qt,sys
        opts = fandango.linos.sysargs_to_dict(split=True) #(args,opts)
        print('in QAlarmPanel.main(%s,%s)'%(args,opts))
        filters = fandango.first(args or opts[0] or ['*'])
        app = fandango.qt.getApplication()
        w = QAlarmPanel()
        if '-v' in args: 
            import fandango.callbacks
            fandango.callbacks.EventSource.thread().setLogLevel('DEBUG')
            w.view.setLogLevel('DEBUG')
        w.setModel(filters,**opts[1])
        w.show()
        t = (app.activeWindow())
        if not t: 
            print('No Active Window, launch QApplication.exec()')
            sys.exit(app.exec_())
        
if __name__ == '__main__':       
    QAlarmPanel.main(*[a for a in sys.argv[1:] if not a.startswith('-')])

try:
    from fandango.doc import get_fn_autodoc
    __doc__ = get_fn_autodoc(__name__,vars())
except:
    import traceback
    traceback.print_exc()        


import sys, os, traceback
from os import path
import panic
import fandango as fn
import fandango.tango as ft 

__doc__ = """
name = 'TEST_X'
PanicTester.filename = __file__
PanicTester.usage = 'Usage:\n\tpython %s receiver sender [options]'

receiver, sender, options = PanicTester.parse_args()

servers['PyAlarm/test_tg']['test/pyalarm/tg'].update({
    'TGConfig': sender,
    })
phonebook = {
    '%TESTER':receiver
    }
tags['TEST_TG'] = {
    'device': 'test/pyalarm/tg',
    'formula': '1',
    'description': 'Testing alarm sending using telegram',
    'receivers': '%TESTER',
    }
    
PanicTester.main(name, servers, tags, phonebook)
"""


class PanicTester(fn.Object):
    
    tangodb = None
    alarms = None
    tags = {}
    receiver = ''
    sender = ''
    options = []
    filename = 'test_*.py'
    usage = 'Usage:\n\tpython %s receiver sender [options]'
    defaults = {
        'PollingPeriod': 3,
        'AlarmThreshold': 1,
        'StartupDelay' : 3,
        'Enabled' : 1,   
        }
    
    def __init__(self, name, receiver, sender, options = [], defaults = {}):
        self.name = name
        self.receiver = receiver
        self.sender = sender
        self.defaults = defaults or self.defaults
        self.tangodb = ft.get_database()
        self.alarms = panic.api()
        
    def log(self, msg):
        fn.log.info('%s: %s' % (self.name, msg))
        
    @staticmethod
    def get_usage(filename=''):
        return PanicTester.usage % filename
    
    @classmethod
    def parse_args(cls, args = []):
        args = args or sys.argv[1:]
        if not args or 'help' in args:
            print(cls.get_usage())
            sys.exit(0)
        cls.receiver, cls.sender = args[0], args[1]
        cls.options = args[2:]
        return cls.receiver, cls.sender, cls.options
    
    @staticmethod
    def main(name, servers, tags, phonebook = {}, args = []):

        args = PanicTester.parse_args(args)
        tester = PanicTester(name, args[0], args[1], args[2])
        tester.servers, tester.tags = servers, tags
        tester.cleanup(servers)
        tester.configure(servers = servers, tags = tags, phonebook = phonebook)
        try:
            tester.run()
        except:
            traceback.print_exc()
        finally:
            tester.cleanup(delete = False)
            
        tester.log('DONE')        
        
    @fn.Catched
    def configure(self, servers, tags, phonebook):
        """
        servers['PyAlarm/test_tg']['test/pyalarm/tg'].update({
            'TGConfig': sender,
            })
        phonebook = {
            '%TESTER':receiver
            }
        tags['TEST_TG'] = {
            'device': 'test/pyalarm/tg',
            'formula': '1',
            'description': 'Testing alarm sending using telegram',
            'receivers': '%TESTER',
            }
        """
        self.log('CONFIGURE '+'>'*40)
        self.servers = servers
        self.tags = tags
        self.phonebook = phonebook
            
        for s,devs in servers.items():
            for d,props in devs.items():
                ft.add_new_device('PyAlarm/'+s,'PyAlarm',d)

        self.alarms.load()
        [self.alarms.edit_phonebook(k,v) 
            for k,v in phonebook.items()]

        for a,props in tags.items():
            self.alarms.add(a,**props)
            
        for s,devs in servers.items():
            for d,props in devs.items():
                dct = PanicTester.defaults.copy()
                dct.update(props)
                self.alarms.put_db_properties(d,dct)
                
    @fn.Catched
    def cleanup(self, servers=None, delete=True):
        servers = servers or self.servers
        self.log('CLEANUP '+'>'*40)
        try:
            astor = fn.Astor()
            [astor.load_by_name('PyAlarm/'+s) for s in servers]
            print('Server States:' + str(astor.states()))
            print('Stopping ...')
            astor.stop_servers()
        except:
            traceback.print_exc()
            
        if delete:
            print('deleting alarms ...')
            for a in self.tags:
                try:
                    self.alarms.remove(a)
                except:
                    pass        

            print('deleting devices ...')
            for s,devs in self.servers.items():
                for d in devs:
                    try:
                        self.tangodb.delete_device(d)
                    except:
                        traceback.print_exc()
        
    @fn.Catched
    def run(self):
        ### LAUNCH DEVICES
        dspath = path.join(path.dirname(path.abspath(panic.__file__)),
                        'ds','PyAlarm.py')
        self.log('RUN '+'>'*40)
        for s in self.servers:
            os.system(dspath+' ' + s + ' -v2 &')
        fn.wait(30.)

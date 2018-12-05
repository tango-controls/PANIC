
import fandango as fn
from tester import PanicTester

name = 'TEST_TELEGRAM'
PanicTester.filename = __file__
PanicTester.usage = 'Usage:\n\tpython %s TG:receiver sender_token'

receiver, sender, options = PanicTester.parse_args()

#PanicTester.defaults = {
        #'PollingPeriod': 3,
        #'AlarmThreshold': 1,
        #'StartupDelay' : 0,
        #'Enabled' : 1,    
        #}

servers = {'test_tg': {
    'test/pyalarm/tg': {
        'TGConfig': sender,
    }, }, }

tags = { 
    'TEST_TG': {
        'device': 'test/pyalarm/tg',
        'formula': '1',
        'description': 'Testing alarm sending using telegram',
        'receivers': '%TESTER',
    }, }

phonebook = {
    '%TESTER':receiver
    }

if __name__ == '__main__':
    PanicTester.main(name, servers, tags, phonebook)

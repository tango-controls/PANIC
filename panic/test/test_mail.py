
import sys, os, traceback
from os import path
import panic
import fandango as fn
import fandango.tango as ft 

global tangodb, alarms, receiver, sender, smtp_host

def main():
    global tangodb, alarms, receiver, sender, smtp_host
    args = sys.argv[1:]
    if not args or 'help' in str(args):
        print('Usage: test_mail.py receiver sender smtp_host:port')
        sys.exit(0)
        
    receiver, sender, smtp_host = args[:3]
    if ':' not in smtp_host: smtp_host += ':25'

    tangodb = ft.get_database()
    alarms = panic.api()    
    
    cleanup()
    configure()
    try:
        run()
    except:
        traceback.print_exc()
    finally:
        cleanup(delete = False)
    fn.log.info('MAIL_TEST: DONE')

@fn.Catched
def cleanup(delete=True):
    global tangodb, alarms
    fn.log.info('MAIL_TEST: CLEANUP '+'>'*40)
    try:
        servers = fn.Astor('PyAlarm/test_mail')
        print('Server States:' + str(servers.states()))
        print('Stopping ...')
        servers.stop_servers()
    except:
        traceback.print_exc()
        
    if delete:
        print('deleting alarms ...')
        for a in ('TEST_MAIL','TEST_SMTP'):
            try:
                alarms.remove(a)
            except:
                pass        

        print('deleting devices ...')
        for d in ('test/pyalarm/sendmail','test/pyalarm/smtpmail',
                'test/pyalarm/smtp'):
            try:
                tangodb.delete_device(d)
            except:
                traceback.print_exc()

@fn.Catched    
def configure():
    global tangodb, alarms
    fn.log.info('MAIL_TEST: CONFIGURE '+'>'*40)
        
    ft.add_new_device('PyAlarm/test_mail','PyAlarm','test/pyalarm/sendmail')
    ft.add_new_device('PyAlarm/test_mail','PyAlarm','test/pyalarm/smtpmail')    

    alarms.load()
    alarms.edit_phonebook('%TEST_MAIL',receiver)

    alarms.add('TEST_MAIL',
            'test/pyalarm/sendmail',
            formula = '1',
            description = 'Testing alarm sending using sendmail',
            receivers = '%TEST_MAIL')

    alarms.put_db_properties('test/pyalarm/sendmail',{
        'MailMethod':'mail', 
        'FromAddress': 'oncall-noreply@cells.es',
        'PollingPeriod':3,'AlarmThreshold':1, 'StartupDelay':0, 'Enabled':'1'})

    alarms.add('TEST_SMTP',
            'test/pyalarm/smtpmail',
            formula = '1',
            description = 'Testing alarm sending using smtplib',
            receivers = '%TEST_MAIL')

    alarms.put_db_properties('test/pyalarm/smtpmail',{
        'MailMethod':'smtp:%s'%smtp_host, 
        'FromAddress': 'oncall-noreply@cells.es',
        'PollingPeriod':3,'AlarmThreshold':1, 'StartupDelay':0, 'Enabled':'1'})

@fn.Catched
def run():
    ### LAUNCH DEVICES
    dspath = path.join(path.dirname(path.abspath(panic.__file__)),
                       'ds','PyAlarm.py')
    fn.log.info('MAIL_TEST: RUN '+'>'*40)
    os.system(dspath+' test_mail -v2 &')
    fn.wait(30.)

if __name__ == '__main__':
    main()

=====
PANIC
=====

by Sergi Rubio — 2006, 2016

.. contents::

Description
===========

The Package for Alarms and Notification of Incidents from Controls 

PANIC Alarm System is a set of tools (api, Tango device server, user interface) that provides:

*    Periodic evaluation of a set of conditions.
*    Notification (email, sms, pop-up, speakers)
*    Keep a log of what happened. (files, Tango Snapshots)
*    Taking automated actions (Tango commands / attributes)
*    Tools for configuration/visualization.

 
Other Documentation in this same repository

*    PANIC presentation at PCAPAC'14: Panic Talk at PCAPAC'14
*    The Panic python API: PanicAPI.rst
*    The PyAlarm User Guide: PyAlarmUserGuide.rst
*    The Panic UI manual: panicdoc.html

Launch your PANIC System in few steps
=====================================

Dependencies 
------------

You must have PyTango + Tango + MySQL up and running and your TANGO_HOST and PYTHONPATH environment variables properly set.

PyTango is available at PyPI: https://pypi.python.org/pypi/PyTango

Get the code
------------

**ALL OF THIS IS DEPRECATED; GET THE PACKAGES FROM https://github.com/tango-controls INSTEAD**

Fandango library (functional tools for tango) is required to be in your PYTHONPATH::

    svn co https://tango-cs.svn.sourceforge.net/svnroot/tango-cs/share/fandango/trunk/fandango fandango

You can download PyAlarm and the panic api from tango-ds at sourceforge::
 
    svn co https://svn.code.sf.net/p/tango-ds/code/DeviceClasses/SoftwareSystem/PyAlarm/trunk
 
The PANIC User Interface is available in the /clients branch::
 
    svn co  https://svn.code.sf.net/p/tango-ds/code/Clients/python/Panic/trunk
 
Setup your Tango database
-------------------------

Create your devices from a python console (or Jive)::

    import PyTango
    db = PyTango.Database()
     
     
    def add_new_device(server,klass,device):
    dev_info = PyTango.DbDevInfo()
    dev_info.name = device
    dev_info.klass = klass
    dev_info.server = server
    get_database().add_device(dev_info)
     
     
    #Create a PyAlarm device
    add_new_device('PyAlarm/1','PyAlarm','test/alarms/1')
     
     
    #I'll add a simulator, but you can't use TangoTest or whatever device you want:
    add_new_device('PySignalSimulator/1','PySignalSimulator','test/sim/1')
    db.put_device_property('test/sim/1',{'DynamicAttributes':['A=t%100']})

 
From shell, launch your PyAlarm and Simulator devices::
 

    # python PyAlarm/PyAlarm.py 1 &
    # python PySignalSimulator/PySignalSimulator.py 1 &

Create a TEST_ALARM using the API::
 

    import panic
    alarms = panic.api()
    alarms.add('TEST_ALARM',formula='(test/sim/1/A%15 > 5)',description='test',receivers='your@mail')

 
Run the panic application and configure your Alarms
---------------------------------------------------
 
::

    python Panic/gui.py

See the application manual: http://plone.tango-controls.org/tools/panic/panic-ui/

If you want to see faster changes in the alarm cycle try to set the following configuration values (Tools->Adv.Config)::

  PollingPeriod = 1
  AlarmThreshold = 1
  AutoReset = 5
  Notification Services


The syntax for sending an email (from linux, you'll need the "mail" command available in the system, from windows you'll have to set as receiver a command from a device running in a linux machine)::

    DeviceProxy("your/alarm/device").command_inout("SendMail",["Bonjour,\n\nthis is a test message\n\nau revoire","RE: testing","your-name@tango-controls.org"])

The other command we have for notification is SendSMS; but it requires our smslib.py file that is specific to our SMS provider (it uses http transactions to send the messages). If you're interested on it you'll have to write your own smslib.py file to use it.

 
FestivalDS, Speech and pop-ups
------------------------------

There's another notification device you can use, the FestivalDS. It provides speech synthesizing and pop-ups in a linux environment (it requires "festival" and "libnotify-bin" linux packages)::

    https://svn.code.sf.net/p/tango-ds/code/DeviceClasses/InputOutput/FestivalDS/trunk

The commands are::

    Play(string): speech to speakers
    Beep(): beep!
    Play_sequence(string):  it just makes some beeps before and after the speech
    PopUp(title,text,[seconds]): shows a pop-up with title/text for the given time

And that's all regarding our current notifiers, for database we don't have anything yet, as we use the device properties to store all the data. You'll find more information in the PyAlarm user guide.

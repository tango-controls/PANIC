Installing PANIC on a New System
================================

Dependencies
------------

PANIC is available from Github, PyPI and as Debian or SuSE packages.

If you install from SuSE or Debian packages dependencies will be automatically installed.

If not, then you'll need Tango, PyTango and Fandango for the server side (including its dependencies, ZMQ, numpy, ...). 

For the client side you'll also need Taurus library and PyQt4.

You should be able to get all these packages also from www.tango-controls.org

Run the GUI and create a PyAlarm
--------------------------------

Running "setup.py install" should install the panic-gui script in your system. 

But if you don't want to install the application you can just run python panic/gui/gui.py to launch the client.

In your first run it will apply completely empty. Just create your first PyAlarm instance going to the  "Config" icon in the toolbar and pushing "Create New" button.

Now you can create your first PyAlarm pushing "New" in the main widget. You'll be prompted to fill the gaps, for a first installation I recommend this alarm:

 TAG: TEST_LOG
 Description: just testing
 Severity: WARNING
 Receivers: your_mail@your_domain.com
 Formula: True

This simple alarm will allow you to check if email sending works properly.

Run the PyAlarm Server
----------------------

Use Astor or the shell to start your newly created PyAlarm:

 python ds/PyAlarm.py TEST -v4
 
After ~45 seconds (if you didn't modified the default configuration) you'll receive your first email from PANIC. 

Now head to the configuration docs to know all the options you have for tuning the behaviour.

========================
PanicAdminUsers property
========================

.. contents::

The PanicAdminUsers property will contain all users enabled to modify an alarm.

Although, any user identified as an email receiver of an alarm will be allowed to change it.

The propery is check from the get_admins_for_alarm() method in AlarmAPI.

The method will be used to call the setAllowedUsers() of a validator plugin.

The methods that the i*ValidatedWidget decorator requires of a validator are:

 * setLogging()
 * setAllowedUsers()
 * setLogMessage()
 * exec_()


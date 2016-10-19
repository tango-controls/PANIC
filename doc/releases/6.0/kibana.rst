http://www.tango-controls.org/community/forum/post/1123/

we've added a tiny feature to PyAlarm which pushes each alarm event as a JSON document to a simple "logger" device (using a command), which in turn stores the event in elasticsearch. The historical data can then be viewed through the kibana web UI, where users can do various filtering and also set up specific views. So far it has been pretty solid, with very low maintenance.

I'm attaching a kibana screenshot from our controlroom. The UI is a bit strange but powerful once you get used to it. However, the main benefit is that we're not developing it ourselves :)

Caveat: we're currently using ES 1.X and kibana 3, but the current version of ES is 2.X and kibana 3 is no longer compatible. Kibana 4 is a complete rewrite and works quite differently, with an even more confusing UI. We're not sure whether to migrate or how. 

----

PyAlarm Elasticsearch logging
-----------------------------

The purpose of these changes is to enable PyAlarm to push all alarm events into a database, in this case Elasticsearch but it should be pretty easy to support other databases if desired. The main reason we're going with ES is that it is already established as a platform for storing logs, and has some mature UI tools for this such as Kibana.

I've tried to compile the changes we've made to PyAlarm to support logging to elasticsearch. The system has been in use for about 1 year now and has worked pretty well. The solution also requires another part, namely the "logger" device. It is a separate device that has an "Alarm" command that takes a JSON string and stores that as a document in elasticsearch. This device is currently undergoing some work, mainly to support newer versions of ES, but we will make it available soon.

This is not a patch, since I think we've diverged from the main branch of PyAlarm. We tried to make the changes as lcal as we could so it should be easy to just put it in. You can of course refactor this as you like if you think it would fit better in some other way.

We added an optional string property called "LoggerDevice". It can be configured with the name of a "logger" device. If a logger device is configured, we try to create a proxy to it in "init_device", and if this is successdul, save it in an internal variable called "self._loggerds". If the property is not set, the PyAlarm behavior is not affected.

Then, there are a few additions to the "send_alarm" method in PyAlarm:
----
if self._loggerds:
    # send alarm data to the logger device
    report = self.generate_json(tag_name, message=message, values=values)
    self._loggerds.alarm(report)  
----
and "free_alarm" method:
----
if self._loggerds:
    # send alarm data to the logger device
    report = self.generate_json(tag_name, message=message, user_comment=comment)
    self._loggerds.alarm(report)
----

(Note: The communication with the logger device should perhaps be done in an asynchronous way, so that it won't block PyAlarm if the logger device is slow.)

They call the following method that was added to PyAlarm:

----
def generate_json(self, tag_name, message='DETAILS',
                  values=None, user_comment=None, html=False):
    """
    Take an alarm and turn it into a JSON string representation.
    The format of this string is dictated by the Logger
    device, and follows the shape of the Alarm object.
    """
    
    # Check alarm
    try:
        msg = "Generating a json report for alarm {0}"
        self.info(msg.format(tag_name))
        alarm = self.Alarms[tag_name]
    except KeyError:
        return self.warn('Unknown alarm: {0}'.format(tag_name))

    # Helper function
    def cast_dict(dct):
        """Convert Boost.Enum objects to strings"""
        boost_eval_type = PyTango._PyTango.AttrQuality.__base__
        for key, value in dct.items():
            if isinstance(value, boost_eval_type):
                dct[key] = str(value)

    # Build dictionary
    try:
        self.info("Building dictionary for alarm {0}".format(tag_name))
        _values = values or self.PastValues.get(tag_name) or {}
        cast_dict(_values)  # Convert Boost.Enum objects to string
        report = {
            "timestamp": int(time.time() * 1000),
            "alarm_tag": tag_name,
            "message": message.strip(),
            "values": [{"attribute": attr, "value": value}
                       for attr, value in _values.items()],
            "device": self.get_name().strip(),
            "description": alarm.parse_description().strip(),
            "severity": alarm.parse_severity().strip(),
            "instance": alarm.instance,
            "formula": alarm.formula.strip()
        }
        if user_comment:
            report["user_comment"] = user_comment
        if alarm.recovered:
            report["recovered_at"] = int(alarm.recovered * 1000)
        if alarm.active:
            report["active_since"] = int(alarm.active * 1000)
    except Exception as exc:
        msg = 'Unexpected exception while building dictionary'
        msg = 'for alarm {0}: '.format(tag_name)
        return self.warn(msg + repr(exc))

    # Dump the json string
    try:
        self.info("Dumping json for alarm {0}".format(tag_name))
        string = json.dumps(report) 
    except Exception as exc:
        msg = 'Unexpected exception while dumping json'
        msg = 'for alarm {0}: '.format(tag_name)
        return self.warn(msg + repr(exc))
    else:
        self.debug(string.replace('%', '%%'))

    # Return json
    return string
----

Finally, in order for each alarm "event" to be identifiable in the DB, we added an "instance" field to the Alarm object that is a unique ID that ties each activation and deactivation of an alarm together. This is not really necessary for the operation, but it may turn out to be useful in the future. The point is that if you have the activation event of an alarm it makes it easy to find when it was deactivated, and vice versa.

In Alarm we added the method:
----
    def activate(self):
        self.active = time.time()
        self.instance = str(uuid4())  # import uuid4 from uuid
----
And then in PyAlarm replaced the line:
----
    self.Alarms[tag_name].active = time.time()
----
with
----
    self.Alarms[tag_name].activate()
----

That's it!

/Johan
<<<<<<< HEAD

=======
>>>>>>> 071b37fbdbbfd8ca5d0f69166f5cf3b45e316f50

Alarm properties that control if exceptions trigger alarms or not ...

        'RethrowState':
            [PyTango.DevBoolean,
            "Whether exceptions in State reading will be rethrown.",
            [ True ] ],#Overriden by panic.DefaultPyAlarmProperties

        'RethrowAttribute':
            [PyTango.DevBoolean,
            "Whether exceptions in Attribute reading will be rethrown.",
            [ False ] ],#Overriden by panic.DefaultPyAlarmProperties

        'IgnoreExceptions':
            [PyTango.DevBoolean,
            "If True unreadable values will be replaced by None instead of Exception.",
            [ True ] ],#Overriden by panic.DefaultPyAlarmProperties

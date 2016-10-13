http://www.tango-controls.org/community/forum/post/1123/

we've added a tiny feature to PyAlarm which pushes each alarm event as a JSON document to a simple "logger" device (using a command), which in turn stores the event in elasticsearch. The historical data can then be viewed through the kibana web UI, where users can do various filtering and also set up specific views. So far it has been pretty solid, with very low maintenance.

I'm attaching a kibana screenshot from our controlroom. The UI is a bit strange but powerful once you get used to it. However, the main benefit is that we're not developing it ourselves :)

Caveat: we're currently using ES 1.X and kibana 3, but the current version of ES is 2.X and kibana 3 is no longer compatible. Kibana 4 is a complete rewrite and works quite differently, with an even more confusing UI. We're not sure whether to migrate or how. 

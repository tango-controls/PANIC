AlarmView data flow
===================

__init__ does:


buildList() is called from:
* onReload()
* onRefresh()
* onFilter()

buildList() does:
* gets alarm that match severity: findListSource()
* regExFiltering()
* filterByState()
* orders by result of alarmSorter()
* triggers changed if list size changed
* then, compares each ordered value with previous order
* if an alarm is new: modelsQueue.put(..,row,..alarm,..)
* if device has changed, adds new model

findListSource:
* called by buildList

showList() is called from:
* onReload()
* onRefresh()
* onFilter()

onReload() will:
* call api.load()
* adjust size of columns
* clean removed alarms

onRefresh() just calls buildList and showList.

hurry() method is called after New/Init and forces onReload() after 1s
onFilter() method is called after Reset/Acknowledge/Disable or any change on filters
It will trigger buildList() and showList() and resets timers


showList() does:
* remembers selected items
* removes all items from list
* applies active and time sorting filters
* adds new items to list widget
* reapplies previous selection


onRefresh called by refreshTimer (REFRESH_TIME = 5s)
onReload called by reloadTimer (60 s) and onClone()






Creation of Tango Attribute
===========================

self.__subscription_state will keep if the attribute have been subscribed or not

__subscription_event is a threading.Event

_events_working is initalized to False

__chg_evt_id will remember the subscription id
__cfg_evt_id is similar

TaurusAttribute.__init__ is also called

cleanUp()
---------

will unsubscribeConfEvents and call TaurusAttribute.cleanUp

write()
-------

After a write() of a ReadWrite attribute this method is called (value = read_attribute):

    self.poll(single=False, value=result, time=time.time())

It is not called if isUsingEvents() returned True

poll()
------

if single: return self.read(cache=False)
else: self.decode(kwargs['value'])

except: fire Error event
else: fire Periodic event

subscription_event.set() is called always

the 'time' argument seems not used at all (taken from attr_value?)

attr_value returned by decode is a TangoAttrValue

read()
------

if cache = True the cache is checked:

 if delta attr_time < polling_period:
  value (or error) is returned
 else:
  proceeds to next condition
  
if cache is False or (not isPollingActive and state in (Pending, Unsubscribed)):

 return read_attribute()
 
elif state in (Subscribing,Pending):
 event.wait() !?!?! Hungs until subscription finishes?
 
last attr_value is returned
 
 

ListenerAPI
===========

fireRegisterEvent(listener)
---------------------------

v = read()
fireEvent(Config/Change,v,listener)

addListener()
-------------------

That's the method were subscription is triggered, state
checks are based on initial state, so calls to subscribeEvents
do not affect later checks.

if first calls TaurusAttribute.addListener(); if fails it returns
It is checked that listeners>=1

If it is unsubscribed and it is firstListener ===> subscribeEvents()

if len(listeners)>1 and (was Subscribed or isPollingActive()):
 fireRegisterEvent()

If Concurrent, event is queued with taurus.Manager.addJob

return result of TaurusAttribute.addListener

removeLIstener()
-------------------------

If it was the last listener it calls unsubscribeEvents()

returns TaurusAttribute.removeListener()

isUsingEvents()
----------------------

returns state == Subscribed

subscribeEvents()
--------------------------

subscriptionEvent is renewed !?! (previous event is overriden)

state => Subscribing

First it tries to subscribe:
chg_evt_id = DeviceProxy.subscribe_event(attr,CHANGE,self,filters=[])

If fails then:
state => Pending
activatePolling()
chg_evt_id = DeviceProxy.subscribe_event(attr,CHANGE,self,filters=[],stateless=True)

stateless=True means that a thread is started to try subscribing every 10 seconds.

What happens to this thread if device is killed or events disabled!?!?

Which callback is executed?

If the attribute is subscribed with NO stateless flag and then the device dies? 

Is the  keep alive thread enabled or not?

unsubscribeEvents()
-----------------------------

dp.unsubscribe_event()
deactivatePolling()
state => Unsubscribed

Note, this happens independently of which is the previous state (Subscribed or Pending)
So ... UNSUBSCRIBING  ALWAYS DEACTIVATES POLLING!?

subscribeConfEvents():
--------------------------------

It is very different from subscribing change events.

The subscription call is always stateless; no state is changed and if it fails (device is dead?)
then a manual call to attribute info is done.

BUT!, it is using the deviceproxy.attribute_query, that will not work if the device is dead.
A call to the database device should be used instead.

Then ... what will happend with the configuration event if the attribute does not send that config event?

?

pushEvent()
-----------------

if it is a config event, gets the config and then tries to read the value (.getValueObj(cache=False)

If it is an attribute event: gets attribute value
 state => Subscribed()
 deactivatePolling() (it it is not forced)
 triggers fireEvent(listeners) (concurrent or not)
 
If error and has EVENT_TO_POLLING_EXCEPTIONS
 if polling not active: Activate Polling
 No event fired for Listeners!!
 
 elif error:
  value = None, get the error
  state = Subscribed !?
  deactivatePolling() !?
  fireEvent(listeners)
  
  class TangoAttributeEventListener(EventListener)
  ------------------------------------------------------------------------
  
  A class that stores timestamp for each different value of event received; it may have some application.
  
  NOTE: This behavior described does not seem to be implemented.
  
  

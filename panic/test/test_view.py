import os

try:
  reload(panic.view)
except:
  import panic.view

domain = '|'.join(os.getenv('INSTANCES').split())

view = panic.view.AlarmView(domain=domain,verbose=True,filters='!ck') #filters={'tag':'A_*'})

import fandango as fn

while 1:
  c = raw_input('command or exit?')
  if c == 'exit': break
  try:
    if c: print(fn.evalX(c,_locals=locals()))
  except Exception,e: print(e)




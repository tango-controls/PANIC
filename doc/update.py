"""
This script will regenerate recipes and devices .rst files
"""

import os,shutil

print('Updating .rst index files ...')

rheader = """
=============
PANIC Recipes
=============

.. toctree::
   :maxdepth: 2

"""

dheader = """
=============
PANIC Devices
=============

.. toctree::
   :maxdepth: 2

"""

print('Copy icons ...')
shutil.copy2('../panic/gui/icon/panic-6.png','.')
shutil.copy2('../panic/gui/icon/panic-6-banner.png','.')

#contents::

recipes = ('recipes',rheader,'recipes.rst')
devices = ('ds',dheader,'devices.rst')

for data in (recipes,devices):
 try:
  folder,header,filename = data
  files = [f for f in os.listdir(folder) if '.rst' in f]
  for f in files:
    header += '\n   '+folder+'/'+f.split('.rst')[0]
  header += '\n\n'
  o = open(filename,'w')
  o.write(header)
  o.close()
 except:
  print('%s failed!'%str(data))
  
  
  

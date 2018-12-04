"""
To test this script just run:

mkdir /tmp/builds/
python setup.py install --root=/tmp/builds
/tmp/builds/usr/bin/PyAlarm -? -v4

"""

from setuptools import setup, find_packages


install_requires = ['taurus',
                    'fandango',
                    'PyTango',]


package_data = {
  '': ['VERSION'],
  'panic': [
    'gui/icon/*',
    ],
  }

scripts = [
  './bin/PyAlarm',
  './bin/panic',
  ]

entry_points = {
        'console_scripts': [
            #'panic-gui=panic.gui.gui:main_gui',
        ],
}

author = 'Sergi Rubio'
email = 'srubio@cells.es'
download_url = 'https://github.com/tango-controls/panic'
description = 'PANIC, a python Alarm System for TANGO'
long_description = """PANIC is a set of tools (api, Tango device server, user interface) that provides:

 * Periodic evaluation of a set of conditions.
 * Notification (email, sms, pop-up, speakers)
 * Keep a log of what happened. (files, Tango Snapshots)
 * Taking automated actions (Tango commands / attributes)
 * Tools for configuration/visualization
"""

setup(
    name="panic",
    version=open('panic/VERSION').read().strip(),
    author = author,
    author_email = email,
    maintainer = author,
    maintainer_email = email,
    description = description,
    long_description = long_description,
    download_url = download_url,
    packages=find_packages(),
    #long_description=read('README'),
    package_data=package_data,
    install_requires=install_requires,
    entry_points=entry_points,
    scripts=scripts,
    include_package_date=True,
)



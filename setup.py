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


package_data = {'': ['VERSION']}

scripts = [
  './bin/PyAlarm',
  './bin/panic-gui',
  ]

entry_points = {
        'console_scripts': [
            #'panic-gui=panic.gui.gui:main_gui',
        ],
}


setup(
    name="panic",
    version=open('panic/VERSION').read().strip(),
    packages=find_packages(),
    package_data=package_data,
    install_requires=install_requires,
    entry_points=entry_points,
    scripts=scripts,
)



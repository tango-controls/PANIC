"""
To test this script just run:

mkdir /tmp/builds/
python setup.py install --root=/tmp/builds
/tmp/builds/usr/bin/PyAlarm -? -v4

"""

from setuptools import setup, find_packages
setup(
    name="python-panic",
    version=open('VERSION').read().strip(),
    packages=find_packages(exclude=["tags", ]),
    entry_points={
        'console_scripts': [
            'PyAlarm = panic.ds.PyAlarm:main',
        ],
    }
)



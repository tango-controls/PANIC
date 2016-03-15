

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



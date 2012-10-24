# coding=utf-8

# Python 2.5 compatibility.
from __future__ import with_statement

import os.path
import sys
from setuptools import setup, find_packages


VERSION = '0.3-dev'


def read_relative_file(filename):
    """Returns contents of the given file.
    Filename argument must be relative to this module.
    """
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return f.read()


setup(
    name='fileconveyor',
    version=VERSION,
    url='http://fileconveyor.org',
    download_url='https://github.com/wimleers/fileconveyor',
    author='Wim Leers',
    license='Unlicense',
    description="Daemon to detect, process and sync files to CDNs.",
    long_description=read_relative_file('README.txt'),
    platforms='Any',
    classifiers = [
        'Development Status :: 4 - Beta',
        'License :: Public Domain',
        'Operating System :: OS Independent',
    ],
    packages=find_packages(),
    include_package_data = True,
    install_requires=[
        'setuptools',
        'cssutils',
        'boto==1.6b',
        'python-cloudfiles>=1.4.0',
        'django>=1.3',
        'django-cumulus>=1.0.5',
    ] + (
        ["pyinotify>0.8.0"] if "linux" in sys.platform else []
    ),
)

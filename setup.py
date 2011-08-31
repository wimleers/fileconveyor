# coding=utf-8
import os.path
from setuptools import setup, find_packages


VERSION = '0.1-dev'


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
    ],
)

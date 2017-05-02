#!/usr/bin/env python3

from setuptools import setup

setup(
    name='noio_ws',
    description='noio_ws - sans-io websockets',
    long_description='A sans-io python implementation of the websocket protocol',
    license='MIT',
    version='0.0.1',
    author='Mark Jameson - aka theelous3',
    url='https://github.com/theelous3/noio_ws',
    packages=['noio_ws'],
    install_requires=['h11'],
    classifiers=['Programming Language :: Python :: 3']
)

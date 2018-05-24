#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import find_packages

depends = [
    'flask',
    'requests',
]

setup(name='sync-sample',
      version='0.0.1',
      author='Jeffrey Hwang',
      author_email='support@resilio.com',
      url='https://resilio.com',
      packages = find_packages(),
      install_requires=depends
)

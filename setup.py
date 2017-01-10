#!/usr/bin/python3.4

from setuptools import setup, find_packages

setup(
    name = 'lbproxy',
    version = '1.0.0',
    description = 'loadbalancer automation framework',
    long_description = 'loadbalancer automation framework',
    author = 'Dan Achim',
    author_email = 'dan@hostatic.ro',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    license = 'Apache',
    scripts=['src/sbin/lbproxyd', 'src/sbin/lbproxy-collector'],
    data_files=[('/etc/lbproxy', ['src/etc/lbproxy.cfg'])],
)

# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='pyplecs',
    version='0.0.0',
    description='automatization of plecs simulations',
    long_description=readme,
    author='riccardo tinivella',
    author_email='tinix84@gmail.com',
    url='https://github.com/tinix84/pyplecs',
    license=license,
    packages=find_packages(exclude=('data', 'tests', 'docs', 'matlab_func')),
    install_requires=['numpy', 'scipy', 'pandas', 'plotly'],  
)

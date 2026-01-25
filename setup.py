# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='pyplecs',
    version='1.0.0',
    description='Advanced PLECS simulation automation with web UI, REST API, and optimization',
    long_description=readme,
    author='riccardo tinivella',
    author_email='tinix84@gmail.com',
    url='https://github.com/tinix84/pyplecs',
    license=license,
    packages=find_packages(exclude=('data', 'tests', 'docs', 'matlab_func')),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'pyplecs-api=pyplecs.api:main',
            'pyplecs-gui=pyplecs.webgui:main',
            'pyplecs-mcp=pyplecs.mcp:main',
            'pyplecs-setup=pyplecs.cli.installer:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
    include_package_data=True,
    package_data={
        'pyplecs': ['config/*.yml', 'webgui/templates/*', 'webgui/static/*'],
    },
)

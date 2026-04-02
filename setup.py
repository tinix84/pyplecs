# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    readme = f.read()

with open('LICENSE', encoding='utf-8') as f:
    license = f.read()

# Read requirements from requirements.txt, following -r includes
def _read_requirements(path):
    reqs = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('-r '):
                reqs.extend(_read_requirements(line[3:].strip()))
            else:
                reqs.append(line)
    return reqs

requirements = _read_requirements('requirements.txt')

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

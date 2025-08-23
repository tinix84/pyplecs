# Sphinx configuration for PyPLECS docs
import os
import sys
from datetime import datetime

# Add project root to sys.path so autodoc can import pyplecs
sys.path.insert(0, os.path.abspath('..'))

project = 'PyPLECS'
author = 'PyPLECS Team'
copyright = f'{datetime.now().year}, {author}'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Autodoc settings
autodoc_typehints = 'description'

# napoleon settings (Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False

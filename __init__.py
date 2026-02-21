"""
Tool for orchestrating documentation builds using Sphinx.

>>> __name__
'coherent.docs'
"""

__requires__ = [
    'coherent.build',
    'pip-run',
    'sphinx >= 3.5',
    'jaraco.packaging >= 9.3',
    'rst.linker >= 1.9',
    'furo',
    'sphinx-lint',
]

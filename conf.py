from __future__ import annotations

extensions = [
    'sphinx.ext.autodoc',
    'jaraco.packaging.sphinx',
]

master_doc = "index"
html_theme = "furo"

# Be strict about any broken references
nitpicky = True
nitpick_ignore: list[tuple[str, str]] = []

# Include Python intersphinx mapping to prevent failures
# jaraco/skeleton#51
extensions += ['sphinx.ext.intersphinx']
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# Preserve authored syntax for defaults
autodoc_preserve_defaults = True

# Add support for linking usernames, PyPI projects, Wikipedia pages
github_url = 'https://github.com/'
extlinks = {
    'user': (f'{github_url}%s', '@%s'),
    'pypi': ('https://pypi.org/project/%s', '%s'),
    'wiki': ('https://wikipedia.org/wiki/%s', '%s'),
}
extensions += ['sphinx.ext.extlinks']

# local

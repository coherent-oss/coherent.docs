import contextlib
import os
import pathlib
import subprocess
import sys
import urllib.request

import pip_run.deps
import pip_run.launch
from coherent.build import bootstrap

DOC_DEPS = [
    'sphinx >= 3.5',
    'jaraco.packaging >= 9.3',
    'rst.linker >= 1.9',
    'furo',
    'sphinx-lint',
]

CONF_PY_URL = (
    'https://raw.githubusercontent.com/jaraco/skeleton/refs/heads/main/docs/conf.py'
)


def load_conf_py():
    return urllib.request.urlopen(CONF_PY_URL).read().decode('utf-8')


def get_package_name():
    """
    Discover the package name from the VCS remote origin or the directory name.

    >>> get_package_name()
    'coherent.docs'
    """
    try:
        origin = subprocess.check_output(
            ['git', 'remote', 'get-url', 'origin'],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        name = origin.rpartition('/')[2].removesuffix('.git')
        if name:
            return name
    except Exception:
        pass
    return pathlib.Path('.').absolute().name


def find_modules(package_name: str, root: pathlib.Path = pathlib.Path()) -> list[str]:
    """
    Find all public modules (no underscore-prefixed components) in the package.

    Handles both flat layout (root has ``__init__.py``) and traditional layout
    (package in a subdirectory).

    >>> find_modules('nopackage', pathlib.Path('/nonexistent'))
    ['nopackage']
    """
    if (root / '__init__.py').exists():
        # Flat layout: the repo root IS the package
        pkg_dir = root

        def to_module(parts):
            if not parts:
                return package_name
            return f'{package_name}.{".".join(parts)}'

    else:
        # Traditional layout: package lives in a subdirectory
        top = package_name.replace('-', '_').split('.')[0]
        pkg_dir = root / top
        if not pkg_dir.exists():
            return [package_name]

        def to_module(parts):
            if not parts:
                return top
            return f'{top}.{".".join(parts)}'

    modules = []
    for path in sorted(pkg_dir.rglob('*.py')):
        rel = path.relative_to(pkg_dir)
        parts = rel.with_suffix('').parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        if any(p.startswith('_') for p in parts):
            continue
        modules.append(to_module(parts))

    # Root module first, then alphabetical
    modules.sort(key=lambda m: (m.count('.'), m))
    return modules


def make_index_rst(package_name: str, modules: list[str]) -> str:
    """
    Generate ``index.rst`` content from the skeleton boilerplate plus
    ``automodule`` directives for each public module.
    """
    entries = []
    for mod in modules:
        if mod != modules[0]:
            label = mod.split('.')[-1].replace('_', ' ').title()
            entries.append(f'\n{label}\n{"-" * len(label)}\n')
        entries.append(
            f'\n.. automodule:: {mod}\n'
            f'   :members:\n'
            f'   :undoc-members:\n'
            f'   :show-inheritance:\n'
        )
    body = ''.join(entries)
    return (
        'Welcome to |project| documentation!\n'
        '===================================\n'
        '\n'
        '.. sidebar-links::\n'
        '   :home:\n'
        '   :pypi:\n'
        '\n'
        '.. toctree::\n'
        '   :maxdepth: 1\n'
        '\n'
        '   history\n'
        f'{body}\n'
        '\n'
        'Indices and tables\n'
        '==================\n'
        '\n'
        '* :ref:`genindex`\n'
        '* :ref:`modindex`\n'
        '* :ref:`search`\n'
    )


def build_env(target, *, orig=os.environ):
    """
    Build the environment for invoking sphinx, inserting the installed
    packages path onto PYTHONPATH.

    >>> env = build_env('foo', orig=dict(PYTHONPATH='bar'))
    >>> env['PYTHONPATH'].replace(os.pathsep, ':')
    'foo:bar'
    """
    overlay = dict(
        PYTHONPATH=pip_run.launch._path_insert(
            orig.get('PYTHONPATH', ''), os.fspath(target)
        ),
        PYTHONSAFEPATH='1',
    )
    return {**orig, **overlay}


@contextlib.contextmanager
def configure_docs(package_name: str):
    """
    Create the ``docs/`` directory and generate ``conf.py`` and ``index.rst``
    (only if they do not already exist), yielding for the sphinx build, then
    cleaning up any files we created.
    """
    docs = pathlib.Path('docs')
    docs.mkdir(exist_ok=True)
    modules = find_modules(package_name)
    with (
        bootstrap.assured(docs / 'conf.py', load_conf_py),
        bootstrap.assured(
            docs / 'index.rst', lambda: make_index_rst(package_name, modules)
        ),
    ):
        yield


@contextlib.contextmanager
def project_on_path():
    """
    Install the target project plus doc build dependencies in an ephemeral
    environment and yield the installation home path.
    """
    deps = pip_run.deps.load('--editable', '.', *DOC_DEPS)
    with bootstrap.write_pyproject(), deps as home:
        yield home


def run():
    package_name = get_package_name()
    with project_on_path() as home:
        with configure_docs(package_name):
            cmd = [
                sys.executable,
                '-m',
                'sphinx',
                '-b',
                'html',
                'docs',
                'build/docs',
                *sys.argv[1:],
            ]
            raise SystemExit(subprocess.call(cmd, env=build_env(home)))

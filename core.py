import contextlib
import importlib.resources
import os
import pathlib
import subprocess
import sys

import pip_run.deps
import pip_run.launch
from coherent.build import bootstrap, discovery


def find_modules(package_name: str, root: pathlib.Path = pathlib.Path()) -> list[str]:
    """
    Find all public modules in the package using the essential layout.

    >>> find_modules('nopackage', pathlib.Path('/nonexistent'))
    ['nopackage']
    """
    if not (root / '__init__.py').exists():
        return [package_name]

    def to_module(path):
        parts = path.relative_to(root).with_suffix('').parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        return '.'.join((package_name,) + parts) if parts else package_name

    def is_public(path):
        parts = path.relative_to(root).with_suffix('').parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        return not any(p.startswith('_') for p in parts)

    return sorted(
        set(map(to_module, filter(is_public, root.rglob('*.py')))),
        key=lambda m: (m.count('.'), m),
    )


def make_modules_rst(modules: list[str]) -> str:
    """
    Generate the automodule directives for each public module.
    """

    def module_section(mod, is_first):
        if is_first:
            header = ''
        else:
            label = mod.split('.')[-1].replace('_', ' ').title()
            header = f'\n{label}\n' + '-' * len(label) + '\n'
        return (
            header
            + f'\n.. automodule:: {mod}\n'
            + '   :members:\n'
            + '   :undoc-members:\n'
            + '   :show-inheritance:\n'
        )

    return ''.join(module_section(m, i == 0) for i, m in enumerate(modules))


def make_index_rst(package_name: str, modules: list[str]) -> str:
    """
    Generate ``index.rst`` content from the template plus
    ``automodule`` directives for each public module.
    """
    template = (
        importlib.resources.files(__package__)
        .joinpath('index.tmpl.rst')
        .read_text('utf-8')
    )
    return template.format(modules=make_modules_rst(modules))


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


def load_conf_py():
    return (
        importlib.resources.files(__package__)
        .joinpath('conf.py')
        .read_text('utf-8')
    )


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
    deps = pip_run.deps.load('--editable', '.[doc]')
    with bootstrap.write_pyproject(), deps as home:
        yield home


def run():
    package_name = discovery.best_name()
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


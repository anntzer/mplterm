"""
setuptools helper.

The following decorators are provided::

    # Define extension modules with the possibility to import setup_requires.
    @setup.add_extensions
    def make_extensions():
        import some_setup_requires
        yield Extension(...)

    # Add a pth hook.
    @setup.register_pth_hook("hook_name.pth")
    def _hook():
        # hook contents.
"""

import functools
import inspect
from pathlib import Path
import re

import setuptools
# find_namespace_packages itself bounds support to setuptools>=40.1.
from setuptools import Extension, find_namespace_packages, find_packages
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install_lib import install_lib


__all__ = ["Extension", "find_namespace_packages", "find_packages", "setup"]


class build_ext_mixin:
    _ext_gens_called = False

    def finalize_options(self):
        if not self._ext_gens_called:
            self.distribution.ext_modules[:] = [
                ext for ext_gen in _ext_gens for ext in ext_gen()]
            if len(self.distribution.ext_modules) == 1:
                ext, = self.distribution.ext_modules
                if (not ext.depends
                        and all(src.parent == Path("src")
                                for src in map(Path, ext.sources))):
                    ext.depends = ["setup.py", *Path("src").glob("*.*")]
            self._ext_gens_called = True
        super().finalize_options()


class pth_hook_mixin:
    def run(self):
        super().run()
        for fname, name, source in _pth_hooks:
            with Path(self.install_dir, fname).open("w") as file:
                file.write("import os; exec({!r}); {}()"
                           .format(source, name))

    def get_outputs(self):
        return (super().get_outputs()
                + [str(Path(self.install_dir, fname))
                   for fname, _, _ in _pth_hooks])


def setup(**kwargs):
    cmdclass = kwargs.setdefault("cmdclass", {})
    cmdclass["build_ext"] = type(
        "build_ext_with_extensions",
        (build_ext_mixin, cmdclass.get("build_ext", build_ext)),
        {})
    cmdclass["develop"] = type(
        "develop_with_pth_hook",
        (pth_hook_mixin, cmdclass.get("develop", develop)),
        {})
    cmdclass["install_lib"] = type(
        "install_lib_with_pth_hook",
        (pth_hook_mixin, cmdclass.get("install_lib", install_lib)),
        {})
    kwargs.setdefault(
        # Don't tag wheels as dist-specific if no extension.
        "ext_modules", [Extension("", [])] if _ext_gens else [])
    setuptools.setup(**kwargs)


def register_pth_hook(fname, func=None):
    if func is None:
        return functools.partial(register_pth_hook, fname)
    source = inspect.getsource(func)
    if not re.match(r"\A@setup\.register_pth_hook.*\ndef ", source):
        raise SyntaxError("register_pth_hook must be used as a toplevel "
                          "decorator to a function")
    _, source = source.split("\n", 1)
    d = {}
    exec(source, {}, d)
    if set(d) != {func.__name__}:
        raise SyntaxError(
            "register_pth_hook should define a single function")
    _pth_hooks.append((fname, func.__name__, source))


_ext_gens = []
_pth_hooks = []
setup.add_extensions = _ext_gens.append
setup.register_pth_hook = register_pth_hook

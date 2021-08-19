Notes on terminal image protocols
=================================

sixel
-----

- sixel implementations, all by @saitoha:

  - Support is implemented in ImageMagick_.
  - libsixel_ is a standalone C implementation, and includes ctypes bindings
    (libsixel-python_; the Python package is named ``libsixel``).  Currently
    unmaintained, but has been `forked <libsixel-fork_>`_.
  - PySixel_ is a pure Python implementation; a Cythonized version of the
    (untyped) Python source is also provided (the Python package is named
    ``sixel``).

.. _ImageMagick: https://imagemagick.org/
.. _PySixel: https://pypi.org/project/PySixel/
.. _libsixel-fork: https://github.com/libsixel/libsixel
.. _libsixel-python: https://pypi.org/project/libsixel-python/
.. _libsixel: https://saitoha.github.io/libsixel/

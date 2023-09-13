mplterm: terminal backend(s) for Matplotlib
===========================================

| |GitHub|

..
    |PyPI|

.. |GitHub|
   image:: https://img.shields.io/badge/github-anntzer%2Fmplterm-brightgreen
   :target: https://github.com/anntzer/mplterm
.. |PyPI|
   image:: https://img.shields.io/pypi/v/mplterm.svg
   :target: https://pypi.python.org/pypi/mplterm

``mplterm`` supports outputting Matplotlib figures directly to some terminals.
Currently, ``mplterm`` supports (to various degrees) the iterm2_, kitty_, and
sixel_ protocols, but other protocols may be implemented in the future.

This package's implementation is inspired by itermplot_ and other terminal
integrations for Matplotlib, as listed below.  (Unlike ``itermplot``,
``mplterm`` does not support Matplotlib animations.)

Install with pip_ (``pip install git+https://github.com/anntzer/mplterm``).
Use by setting your Matplotlib backend to ``module://mplterm`` (e.g. by setting
the ``MPLBACKEND`` environment variable to ``module://mplterm``, or by calling
``matplotlib.use("module://mplterm")``).  The protocol to be used is normally
auto-detected, but can also be configured manually.

Protocols
---------

- The ``iterm2`` protocol is supported by the iterm2 and wsltty_ terminals.
  Note that plain mintty_ is not supported.
- The ``kitty`` protocol is only supported by the kitty terminal.  The
  implementation is currently based on ``icat``, and thus requires ImageMagick.
- The ``sixel`` protocol requires a `sixel-capable terminal`_ (xterm_ and
  mlterm_ are known to work) and ImageMagick≥7.0.1.  Note that ``mplterm`` will
  automatically and silently set (once) the ``numColorRegisters`` resource to
  its maximum allowed value.

Configuration
-------------

Configuration is done via the ``MPLTERM`` environment variable, which should be
set to a semicolon-separate list of codes:

- ``backend=...``: Set the underlying rendering backend (by default, "agg").
- ``protocol=...``: Force the protocol to one of ``iterm2``, ``kitty``, or
  ``sixel``.
- ``transparency``: Make the figure and axes background transparent, if the
  protocol supports transparency (the sixel protocol, implemented via
  ImageMagick_, doesn't support it).
- ``revvideo``: Reverse-video the colors (similarly to ``itermplot``).

Other terminal backends for Matplotlib
--------------------------------------

- ``iterm2``:

  - itermplot_.

- ``kitty``:

  - matplotlib-backend-kitty_.
  - xontrib-kitty_.

- ``sixel``:

  - matplotlib-sixel_ (not on PyPI; uses ``ImageMagick``'s sixel support).
  - sixelplot_ (wraps PySixel_; not a Matplotlib backend but rather provides
    ``sixelplot.show()`` which displays the current figure).

.. _ImageMagick: https://imagemagick.org/
.. _ipykernel: https://pypi.org/project/ipykernel/
.. _iterm2: https://iterm2.com/documentation-images.html
.. _itermplot: https://pypi.org/project/itermplot/
.. _kitty: https://sw.kovidgoyal.net/kitty/graphics-protocol/
.. _matplotlib-backend-kitty: https://github.com/jktr/matplotlib-backend-kitty
.. _matplotlib-sixel: https://github.com/koppa/matplotlib-sixel
.. _matplotlib-sixel: https://github.com/koppa/matplotlib-sixel
.. _mintty: https://mintty.github.io/
.. _mlterm: http://mlterm.sourceforge.net/
.. _pip: https://pip.pypa.io/
.. _PySixel: https://pypi.org/project/PySixel/
.. _sixel-capable terminal: https://github.com/saitoha/libsixel#terminal-requirements
.. _sixel: https://en.wikipedia.org/wiki/Sixel
.. _sixelplot: https://pypi.org/project/sixelplot/
.. _xontrib-kitty: https://pypi.org/project/xontib-kitty/
.. _xterm: https://invisible-island.net/xterm/
.. _wsltty: https://github.com/mintty/wsltty

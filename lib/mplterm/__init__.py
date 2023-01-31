"""Terminal backend(s) for Matplotlib."""

from contextlib import ExitStack, contextmanager
import importlib.metadata
import os

from matplotlib.backend_bases import FigureManagerBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
import numpy as np

from . import _iterm2, _kitty, _sixel
from ._util import _detect_terminal


try:
    __version__ = importlib.metadata.version("mplterm")
except ImportError:
    __version__ = "0+unknown"


@contextmanager
def _shrinked(fig, size):
    """
    Temporarily make a figure fit in an terminal by shrinking it if needed.
    """
    tw, th = size
    fw, fh = fig.get_size_inches()
    factor = max(fw * fig.dpi / tw, fh * fig.dpi / th, 1)
    try:
        fig.set_size_inches((fw / factor, fh / factor))
        yield
    finally:
        fig.set_size_inches(fw, fh)


def _transparized(fig):
    """Temporarily make a figure transparent, as done by ``Figure.savefig``."""
    stack = ExitStack()
    for obj in [fig, *fig.axes]:
        stack.callback(obj.set_facecolor, obj.get_facecolor())
        obj.set_facecolor("none")
    return stack


def _revvideo(mem):
    """Reverse-video an RGBA buffer."""
    rgba = np.array(mem)
    rgba[..., :3] = 0xff - rgba[..., :3]
    return rgba.data


def _get_options():
    """Parse the MPLTERM environment variable into individual options."""
    return os.environ.get("MPLTERM", "").split(":") or []


_PROTOCOLS = {
    cls.__name__.lower(): cls for cls in [
        _iterm2.Iterm2, _kitty.Kitty, _sixel.Sixel]}


def _detect_protocol():
    """Detect and instantiate the protocol to use."""
    try:
        opt = [opt for opt in _get_options() if opt.startswith("proto=")][-1]
    except IndexError:
        pass
    else:
        return _PROTOCOLS[opt.split("=", 1)[1]]()
    term = _detect_terminal()
    if term in ["iTerm2", "mintty"]:
        return _iterm2.Iterm2()
    elif term in ["kitty"]:
        return _kitty.Kitty()
    elif term in ["mlterm", "XTerm"]:
        return _sixel.Sixel()
    else:
        raise RuntimeError(f"{term} is not a supported terminal")


class _MpltermFigureManager(FigureManagerBase):
    def show(self):
        proto = _detect_protocol()
        fig = self.canvas.figure
        with ExitStack() as stack:
            size = proto.get_pixel_size()
            if size is not None:
                stack.enter_context(_shrinked(fig, size))
            if proto.supports_transparency and "tr" in _get_options():
                stack.enter_context(_transparized(fig))
            fig.draw(self.canvas.get_renderer())
        mem = self.canvas.buffer_rgba()
        if "rv" in _get_options():
            mem = _revvideo(mem)
        proto.display(mem)


class _FigureCanvasMplterm(FigureCanvasAgg):
    supports_blit = False
    manager_class = _MpltermFigureManager


FigureCanvas = _FigureCanvasMplterm
FigureManager = _MpltermFigureManager

"""Terminal backend(s) for Matplotlib."""

from contextlib import ExitStack, contextmanager
import importlib.metadata
from io import BytesIO
import os

from matplotlib.backend_bases import FigureManagerBase
import numpy as np
from PIL import Image

from . import _iterm2, _kitty, _sixel
from ._util import _detect_terminal_and_device_attributes


try:
    __version__ = importlib.metadata.version("mplterm")
except ImportError:
    __version__ = "0+unknown"


_PROTOCOLS = {
    cls.__name__.lower(): cls for cls in [
        _iterm2.Iterm2, _kitty.Kitty, _sixel.Sixel]}


def _load_options():
    opts = {
        "backend": "agg",
        "protocol": None,
        "transparency": None,
        "revvideo": None,
    }
    for word in filter(None, os.environ.get("MPLTERM", "").split(";")):
        if word.startswith("backend="):
            opts["backend"] = word.removeprefix("backend=")
        elif word.startswith("protocol="):
            opts["protocol"] = word.removeprefix("protocol=")
        elif word == "transparency":
            opts["transparency"] = True
        elif word == "revvideo":
            opts["revvideo"] = True
        else:
            raise ValueError(f"Unknown option: {word}")
    if opts["protocol"] is None:
        term, da = _detect_terminal_and_device_attributes()
        if term in ["iTerm2", "mintty"]:
            opts["protocol"] = "iterm2"
        elif term in ["kitty"]:
            opts["protocol"] = "kitty"
        elif "4" in da or term == "XTerm":
            # If on XTerm without sixel support, still set the protocol to
            # sixel to get the relevant error message.
            opts["protocol"] = "sixel"
        else:  # Else, error out at showtime.
            opts["protocol"] = f"unsupported-terminal:{term}"
    return opts


_OPTIONS = _load_options()


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


class _MpltermFigureManager(FigureManagerBase):
    def show(self):
        proto = _PROTOCOLS[_OPTIONS["protocol"]]()
        fig = self.canvas.figure
        with ExitStack() as stack:
            size = proto.get_pixel_size()
            if size is not None:
                stack.enter_context(_shrinked(fig, size))
            if proto.supports_transparency and _OPTIONS["transparency"]:
                stack.enter_context(_transparized(fig))
            try:
                fig.draw(self.canvas.get_renderer())
                mem = self.canvas.buffer_rgba()
            except Exception:  # builtin cairo backend support.
                buf = BytesIO()
                fig.savefig(buf, format="png")
                mem = np.asarray(Image.open(buf))
                if mem.shape[-1] == 3:
                    mem = np.dstack(
                        [mem, np.full(mem.shape[:2], 0xff, np.uint8)])
        if _OPTIONS["revvideo"]:
            mem = _revvideo(mem)
        proto.display(mem)


_backend_module = (lambda name: importlib.import_module(
    name.removeprefix("module://") if name.startswith("module://")
    else f"matplotlib.backends.backend_{name.lower()}"))(_OPTIONS["backend"])


class _FigureCanvasMplterm(_backend_module.FigureCanvas):
    supports_blit = False
    manager_class = _MpltermFigureManager


FigureCanvas = _FigureCanvasMplterm
FigureManager = _MpltermFigureManager

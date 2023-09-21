"""Terminal backend(s) for Matplotlib."""

from contextlib import ExitStack, contextmanager
import importlib.metadata
from io import BytesIO
import os

from matplotlib.backend_bases import FigureManagerBase
import numpy as np
from PIL import Image

from . import _iterm2, _kitty, _sixel, _util


try:
    __version__ = importlib.metadata.version("mplterm")
except ImportError:
    __version__ = "0+unknown"


_PROTOCOLS = {
    cls.__name__.lower(): cls for cls in [
        # In default priority order.
        _kitty.Kitty,
        _iterm2.Iterm2,
        _sixel.Sixel,
    ]}


def _load_options():
    opts = {
        "backend": "agg",
        "protocols": [*_PROTOCOLS],
        "transparency": None,
        "revvideo": None,
    }
    for word in filter(None, os.environ.get("MPLTERM", "").split(";")):
        if word.startswith("backend="):
            opts["backend"] = word.removeprefix("backend=")
        elif word.startswith("protocols="):
            opts["protocols"] = word.removeprefix("protocols=").split(",")
        elif word == "transparency":
            opts["transparency"] = True
        elif word == "revvideo":
            opts["revvideo"] = True
        else:
            raise ValueError(f"Unknown option: {word}")
    if len(opts["protocols"]) > 1:
        for proto in opts["protocols"]:
            if _PROTOCOLS[proto].is_supported():
                opts["protocols"] = [proto]
                break
        else:  # Error out at showtime.
            term, da = _util.detect_terminal_and_device_attributes()
            opts["protocols"] = [f"unsupported-terminal:{term or '<unknown>'}"]
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
        proto = _PROTOCOLS[_OPTIONS["protocols"][0]]()
        fig = self.canvas.figure
        with ExitStack() as stack:
            size = _util.get_pixel_size()
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

"""Terminal backend(s) for Matplotlib."""

from contextlib import ExitStack, contextmanager
import functools
import importlib.metadata
from io import BytesIO
import itertools
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Timer
from weakref import WeakValueDictionary

from matplotlib.animation import Animation
from matplotlib.backend_bases import FigureManagerBase, TimerBase
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
        "transparency": False,
        "revvideo": False,
        "debug": False,
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
        elif word == "debug":
            opts["debug"] = True
        else:
            raise ValueError(f"Unknown option: {word}")
    return opts


def _adjust_protocol(opts):  # Split out so that debugging can be in effect.
    if len(opts["protocols"]) > 1:
        for proto in opts["protocols"]:
            if _PROTOCOLS[proto].is_supported():
                opts["protocols"] = [proto]
                break
        else:  # Error out at showtime.
            term, da = _util.detect_terminal_and_device_attributes()
            opts["protocols"] = [f"unsupported-terminal:{term or '<unknown>'}"]


_OPTIONS = _load_options()
_adjust_protocol(_OPTIONS)
_backend_module = (lambda name: importlib.import_module(
    name.removeprefix("module://") if name.startswith("module://")
    else f"matplotlib.backends.backend_{name.lower()}"))(_OPTIONS["backend"])


def get_protocol():
    return _OPTIONS["protocols"]


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
    _animation_ids = itertools.count()

    def show(self):
        proto = _PROTOCOLS[_OPTIONS["protocols"][0]]()

        with ExitStack() as stack:
            size = _util.get_pixel_size()
            if size is not None:
                stack.enter_context(_shrinked(self.canvas.figure, size))
            if proto.supports_transparency and _OPTIONS["transparency"]:
                stack.enter_context(_transparized(self.canvas.figure))

            if self.canvas._timers:
                if proto.display_frame is _util.Protocol.display_frame:
                    # Block timers so that they don't try to advance animations
                    # at the same time as the save loop, which would be racy.
                    for timer in self.canvas._timers.values():
                        timer.blocked = True
                    if mpl.__version_info__ < (3, 11):  # mpl#26774
                        self.canvas.draw()
                    for _, timer in sorted(self.canvas._timers.items()):
                        for cb, *_ in timer.callbacks:
                            anim = getattr(cb, "__self__", None)
                            if not isinstance(anim, Animation):
                                continue
                            with TemporaryDirectory() as tmpdir:
                                path = Path(tmpdir, "out.gif")
                                anim.save(path)
                                proto.display_gif(path)
                else:
                    self.canvas.draw()
                    self.canvas._frame_displayer = functools.partial(
                        proto.display_frame, next(self._animation_ids))
            else:
                self.canvas.draw()
                try:
                    mem = self.canvas.buffer_rgba()
                except Exception:  # builtin cairo backend support.
                    buf = BytesIO()
                    self.canvas.figure.savefig(buf, format="png")
                    mem = np.asarray(Image.open(buf))
                    if mem.shape[-1] == 3:
                        mem = np.dstack(
                            [mem, np.full(mem.shape[:2], 0xff, np.uint8)])
                if _OPTIONS["revvideo"]:
                    mem = _revvideo(mem)
                proto.display(mem)


class _TimerMplterm(TimerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocked = False
        self._running = False

    def _timer_start(self):
        if self.blocked:
            return
        self._running = True
        Timer(self.interval / 1000, self._on_timer).start()

    def _on_timer(self):
        super()._on_timer()
        if self._running and not self.single_shot:
            self._timer_start()
        else:
            self._timer_stop()

    def _timer_stop(self):
        self._running = False


class _FigureCanvasMplterm(_backend_module.FigureCanvas):
    supports_blit = False
    manager_class = _MpltermFigureManager
    _timer_cls = _TimerMplterm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timer_count = itertools.count()
        self._timers = WeakValueDictionary()
        self._frame_displayer = None

    def new_timer(self, *args, **kwargs):
        # Hooking new_timer to keep track of existing animations is a trick
        # from itermplot.
        timer = self._timers[next(self._timer_count)] = \
            super().new_timer(*args, **kwargs)
        return timer

    def draw(self, *args, **kwargs):
        super().draw(*args, **kwargs)
        if self._frame_displayer:
            self._frame_displayer(self.buffer_rgba())


FigureCanvas = _FigureCanvasMplterm
FigureManager = _MpltermFigureManager

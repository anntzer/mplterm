import base64
from io import BytesIO
import sys

import PIL

from . import _util
from ._util import Protocol


class Iterm2(Protocol):
    supports_transparency = True

    @staticmethod
    def is_supported():
        term, da = _util.detect_terminal_and_device_attributes()
        return term.startswith(("iTerm2 ", "mintty ", "WezTerm "))

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        buf = BytesIO()
        PIL.Image.frombuffer("RGBA", (w, h), mem).save(buf, format="png")
        b64 = base64.b64encode(buf.getbuffer())
        sys.stdout.buffer.write(
            b"\x1b]1337;File=size=%d;inline=1:%s\a" % (len(b64), b64))

    @staticmethod
    def display_gif(path):
        contents = path.read_bytes()
        b64 = base64.b64encode(contents)
        sys.stdout.buffer.write(
            b"\x1b]1337;File=size=%d;inline=1:%s\a" % (len(b64), b64))

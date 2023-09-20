import base64
from io import BytesIO
import sys

import PIL

from ._util import Protocol


class Iterm2(Protocol):
    supports_transparency = True

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        buf = BytesIO()
        PIL.Image.frombuffer("RGBA", (w, h), mem).save(buf, format="png")
        png = buf.getbuffer()
        b64png = base64.b64encode(png)
        sys.stdout.buffer.write(
            b"\x1b]1337;File=size=%d;inline=1:%s\a" % (len(png), b64png))

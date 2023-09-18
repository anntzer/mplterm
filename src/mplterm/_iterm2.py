import base64
from io import BytesIO
import sys

import PIL

from ._util import Protocol, _csi, _csi_regex, _term_query


class Iterm2(Protocol):
    supports_transparency = True

    @staticmethod
    def get_pixel_size():  # XTWINOPS
        h, w = _term_query(_csi("14t"), _csi_regex(r"4;(\d+);(\d+)t"))
        return None if h is w is None else (int(w), int(h))

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        buf = BytesIO()
        PIL.Image.frombuffer("RGBA", (w, h), mem).save(buf, format="png")
        png = buf.getbuffer()
        b64png = base64.b64encode(png)
        sys.stdout.buffer.write(
            b"\x1b]1337;File=size=%d;inline=1:%s\a" % (len(png), b64png))

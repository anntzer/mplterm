from io import BytesIO
import subprocess

import PIL

from ._util import Protocol


def _icat(args, **kwargs):
    return subprocess.run(["kitty", "+kitten", "icat", *args], **kwargs)


class Kitty(Protocol):
    supports_transparency = True

    @staticmethod
    def get_pixel_size():
        cp = _icat(["--print-window-size"], capture_output=True)
        w, h = map(int, cp.stdout.split(b"x"))
        return w, h

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        buf = BytesIO()
        PIL.Image.frombuffer("RGBA", (w, h), mem).save(buf, format="png")
        _icat([], input=buf.getbuffer())

from io import BytesIO
import subprocess

import PIL

from ._util import Protocol


def _icat(args, **kwargs):
    # TODO: Directly support image protocol (will also work for WezTerm), also
    # re: animations.
    return subprocess.run(["kitty", "+kitten", "icat", *args], **kwargs)


class Kitty(Protocol):
    supports_transparency = True

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        buf = BytesIO()
        PIL.Image.frombuffer("RGBA", (w, h), mem).save(buf, format="png")
        _icat([], input=buf.getbuffer())

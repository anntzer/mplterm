import base64
import sys

from ._util import Protocol, term_query


class Kitty(Protocol):
    supports_transparency = True

    @staticmethod
    def is_supported():
        return bool(term_query("\x1b_Gi=1,s=1,v=1,a=q,f=24;AAAA\x1b\\",
                               "(\x1b_Gi=1;OK\x1b\\\\)")[0])

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        b64img = base64.b64encode(mem)
        n_chunks = (len(b64img) - 1) // 4096 + 1
        for i in range(n_chunks):
            sys.stdout.buffer.write(
                b"\x1b_Ga=T,s=%d,v=%d,m=%d;%s\x1b\\"
                % (w, h, i < n_chunks - 1, b64img[i * 4096 : (i + 1) * 4096]))

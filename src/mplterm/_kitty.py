import base64
import curses
import re
import sys

from ._util import Protocol, term_query


def _write_g(**kwargs):
    data = kwargs.pop("data", None)
    cmd = (("\x1b_G" + ",".join(f"{k}={v}" for k, v in kwargs.items()))
           .encode("latin-1"))
    if data:
        b64 = base64.b64encode(data)
        n_chunks = (len(b64) - 1) // 4096 + 1
        for i in range(n_chunks):
            sys.stdout.buffer.write(
                b"%s,m=%d;%s\x1b\\"
                % (cmd, i < n_chunks - 1, b64[i * 4096 : (i + 1) * 4096]))
    else:
        sys.stdout.buffer.write(b"%s\x1b\\" % cmd)
    sys.stdout.buffer.flush()


class Kitty(Protocol):
    supports_transparency = True
    _ids = {}  # holder_id: {kitty_id: ..., frame_idx: ...}

    @staticmethod
    def is_supported():
        return bool(term_query("\x1b_Gi=1,s=1,v=1,a=q,f=24;AAAA\x1b\\",
                               "(\x1b_Gi=1;OK\x1b\\\\)")[0])

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        _write_g(q=2, a="T", s=w, v=h, data=mem)

    @classmethod
    def display_frame(cls, holder_id, mem):
        if holder_id not in cls._ids:
            h, w, _ = mem.shape
            try:
                curses.cbreak()
                _write_g(I=1, a="T", s=w, v=h, data=mem)
                buf = b""
                while True:
                    buf += sys.stdin.buffer.read(1)
                    match = re.fullmatch(br"\x1b_Gi=(\d+),I=1;(.*)\x1b\\", buf)
                    if match:
                        break
            finally:  # Unclear why initscr/endwin won't work here.
                curses.nocbreak()
            if match.group(2) != b"OK":
                raise RuntimeError(match.group(2))
            kitty_id = match.group(1).decode("latin-1")
            cls._ids[holder_id] = {"kitty_id": kitty_id, "frame_idx": 1}
            _write_g(q=2, a="a", i=kitty_id, c=1)

        else:
            d = cls._ids[holder_id]
            d["frame_idx"] += 1
            h, w, _ = mem.shape
            _write_g(q=2, i=d["kitty_id"], a="f", s=w, v=h, data=mem)
            _write_g(q=2, i=d["kitty_id"], a="a", c=d["frame_idx"])

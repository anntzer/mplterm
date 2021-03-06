import functools
from subprocess import Popen, PIPE

from ._util import (
    Protocol, _csi, _csi_regex, _detect_terminal, _term_query, _TermError)


@functools.lru_cache(None)
def _getset_max_color_registers():  # XTSMGRAPHICS
    """
    Set the numColorRegisters resource to its maximum value, and return it.
    """
    err, num = _term_query(_csi("?1;4;S"), _csi_regex(r"\?1;(\d);(\d+)S"))
    if err != "0":
        raise _TermError
    err, num = _term_query(
        _csi("?1;3;%sS" % num), _csi_regex(r"\?1;(\d);(\d+)S"))
    if err != "0":
        raise _TermError
    return int(num)


class Sixel(Protocol):
    supports_transparency = False

    @functools.lru_cache(None)
    def __new__(cls):
        # Primary DA.
        props, = _term_query(_csi("c"), _csi_regex(r"\?\d+;(.*)c"))
        if "4" not in props.split(";"):
            msg = (f"The current terminal does not support sixel graphics "
                   f"(primary device attributes: {props})")
            if _detect_terminal() == "XTerm":
                msg += ("; if using xterm, consider starting it with e.g. "
                        "'xterm -ti vt340'")
            raise OSError(msg)
        return object.__new__(cls)

    @staticmethod
    def get_pixel_size():  # XTWINOPS
        reply = _term_query(_csi("14t"), _csi_regex(r"4;(\d+);(\d+)t"))
        h, w = map(int, reply)
        return w, h

    @staticmethod
    def display(mem):
        h, w, _ = mem.shape
        ncolors = _getset_max_color_registers()
        args = [
            "convert",
            "-size", f"{w}x{h}", "-depth", "8", "rgba:-",
            "-colors", f"{ncolors}", "sixel:-",
        ]
        with Popen(args, stdin=PIPE) as proc:
            proc.stdin.write(mem)

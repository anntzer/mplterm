import functools
from subprocess import Popen, PIPE

from . import _util
from ._util import Protocol, _csi, _csi_regex


@functools.lru_cache(None)
def _getset_max_color_registers():  # XTSMGRAPHICS
    """
    Set the numColorRegisters resource to its maximum value, and return it.
    """
    err, num = _util.term_query(_csi("?1;4;S"), _csi_regex(r"\?1;(\d);(\d+)S"))
    if err != "0":  # Fallback to standard if terminal does not support query.
        return 256
    # Allow setting numColorRegisters to fail, to handle non-xterms with a
    # fixed number of color registers, such as tmux.  WezTerm even skips the
    # third reply parameter, just indicating failure (CSI?1;2S).
    _util.term_query(_csi(f"?1;3;{num}S"), _csi_regex(r"\?1;(\d)(:;(\d+))?S"))
    return int(num)


class Sixel(Protocol):
    supports_transparency = False

    @staticmethod
    def is_supported():
        term, da = _util.detect_terminal_and_device_attributes()
        # If on XTerm without sixel support, still pretend to support it
        # initially, to get the relevant error message below.
        return "4" in da or term and term.startswith("XTerm(")

    @functools.lru_cache(None)
    def __new__(cls):
        # Primary DA.
        term, da = _util.detect_terminal_and_device_attributes()
        if "4" not in da:
            msg = (f"The current terminal ({term or '<unknown>'}) does not "
                   f"support sixel graphics (primary device attributes: "
                   f"{';'.join(da)})")
            if term == "XTerm":
                msg += ("; if using xterm, consider starting it with e.g. "
                        "'xterm -ti vt340'")
            raise OSError(msg)
        return object.__new__(cls)

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

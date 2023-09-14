from abc import ABC, abstractmethod
import curses
import functools
import re
import sys


class Protocol(ABC):
    @property
    @abstractmethod
    def supports_transparency(self):
        """Whether the terminal supports transparent images."""

    @staticmethod
    def get_pixel_size():
        """Query the (width, height) in pixels of a terminal."""

    @staticmethod
    @abstractmethod
    def display(mem):
        """Output an RGBA buffer to the terminal."""


# Helpers for generating control sequences and replies.
def _csi(x): return "\x1b[" + x
def _csi_regex(x): return r"\x1b\[" + x


@functools.lru_cache(None)
def _term_query(cmd, pattern, *, add_terminator=True):
    """
    Send a control sequence and wait for a reply matching *pattern*.

    For practicality, *cmd* and *pattern* are strs and get latin-1-encoded.
    """
    # End the queries with a (widely supported) Primary DA query to avoid
    # hanging on terminals that do not support the first (this trick comes from
    # notcurses).
    if add_terminator:
        cmd = f"{cmd}{_csi('c')}"
        pattern = f"(?:{pattern})?" + _csi_regex(r"\?\d+[;0-9]*c")
    regex = re.compile(pattern.encode("latin-1"))
    curses.initscr()
    try:
        curses.cbreak()
        sys.stdout.buffer.write(cmd.encode("latin-1"))
        sys.stdout.buffer.flush()
        buf = b""
        while True:
            buf += sys.stdin.buffer.read(1)
            match = regex.fullmatch(buf)
            if match:
                break
        return [group.decode("latin-1") if group else None
                for group in match.groups()]
    finally:
        curses.endwin()


@functools.lru_cache(None)
def _detect_terminal_and_device_attributes():
    """Detect the terminal in use."""
    xtv, = _term_query(_csi(">0q"), r"(?:\x1bP>\|(\w+).*\x1b\\)?")
    # Even with no primary DA reported there may or may not be a semicolon
    # before the final "c" (xterm says no, kitty says yes).
    da, = _term_query(
        _csi("c"), _csi_regex(r"\?\d+([;0-9]*)c"), add_terminator=False)
    return xtv, [] if not da or da == ";" else da.removeprefix(";").split(";")

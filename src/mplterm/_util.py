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


class _TermError(Exception):
    pass


# Helpers for generating control sequences and replies.
def _csi(x): return "\x1b\x5b" + x  # ESC [, but don't mess up autoindent.
def _csi_regex(x): return "\x1b\\\x5b" + x


@functools.lru_cache(None)
def _term_query(cmd, pattern):
    """
    Send a control sequence and wait for a reply matching *pattern*.

    For practicality, *cmd* and *pattern* are strs and get latin-1-encoded.
    """
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
        return [group.decode("latin-1") for group in match.groups()]
    finally:
        curses.endwin()


@functools.lru_cache(None)
def _detect_terminal_and_device_attributes():
    """Detect the terminal in use."""
    # Query XTVERSION, and then Primary DA to avoid hanging on terminals that
    # do not support XTVERSION (this trick comes from notcurses).  XTVERSION's
    # reply doesn't start with CSI, so it will not be accidentally captured by
    # the second regex.
    xtv, da = _term_query(
        _csi(">0q") + _csi("c"), "(.*)" + _csi_regex("?[^;]+;(.*)c"))
    prefix = "\x1bP>|"
    suffix = "\x1b\\"
    if not xtv.startswith(prefix) or not xtv.endswith(suffix):
        raise RuntimeError("Failed to detect a supported terminal")
    return (xtv.removeprefix(prefix).removesuffix(suffix).split()[0],
            da.split(";"))

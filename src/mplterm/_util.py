from abc import ABC, abstractmethod
import array
import curses
import functools
import os
import re
import sys
import warnings

import mplterm


class Protocol(ABC):
    @property
    @abstractmethod
    def supports_transparency(self):
        """Whether the protocol supports transparent images."""

    @property
    @abstractmethod
    def is_supported(self):
        """Whether the terminal supports this protocol."""

    @staticmethod
    @abstractmethod
    def display(mem):
        """Display RGBA memoryview *mem*."""

    @staticmethod
    def display_frame(holder_id, mem):
        """Display RGBA memoryview *mem* at position *holder_id*."""

    @staticmethod
    def display_gif(path):
        """Display the GIF file read from the given *path*."""


# Helpers for generating control sequences and replies.
def _csi(x): return "\x1b[" + x
def _csi_regex(x): return "\x1b\\[" + x


@functools.lru_cache(None)
def term_query(cmd, pattern, *, add_terminator=True):
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
        end_regex = re.compile(
            (".*" + _csi_regex(r"\?\d+[;0-9]*c") + r"\Z").encode("latin-1"))
    cmd = cmd.encode("latin-1")
    regex = re.compile(pattern.encode("latin-1"))
    match = None

    def status_report(status):
        return (
            f"STATE: {status}\n"
            f"QUERY: {cmd.decode('latin-1').replace('\x1b', '\u238b')}\n"
            f"MATCH: {pattern.replace('\x1b', '\u238b')}\n"
            f"READ:  {buf.decode('latin-1').replace('\x1b', '\u238b')}"
        )

    try:
        curses.initscr()
        try:
            curses.cbreak()
            sys.stdout.buffer.write(cmd)
            sys.stdout.buffer.flush()
            buf = b""
            while True:
                buf += sys.stdin.buffer.read(1)
                match = regex.fullmatch(buf)
                # Assume that matching the end regex directly *also*
                # implies that the actual query failed (maybe because it is
                # unsupported); e.g. iterm2 has a non-standard reply to kitty
                # graphics protocol queries.
                if match or (add_terminator and end_regex.match(buf)):
                    break
        finally:
            curses.endwin()
    except KeyboardInterrupt:
        warnings.warn(status_report("interrupt"))
        raise
    # To reach this point, match must have ended (with success or failure).
    # This block is here so that debug-printing occurs after endwin().
    if not match:
        if mplterm._OPTIONS["debug"]:
            print(status_report("fail"), file=sys.stderr)
        return None
    if mplterm._OPTIONS["debug"]:
        print(status_report("ok"), file=sys.stderr)
    return [group.decode("latin-1") if group else None
            for group in match.groups()]


def xtgettcap(name):
    name = "".join(map("{:02X}".format, name.encode("latin-1")))
    status, value = term_query.__wrapped__(  # Skip cache, due to xtsettcap.
        # In the reply, iterm2 uppercases the hex name whereas xterm & kitty
        # repeat it as given, so match it case-insensitively.
        f"\x1bP+q{name}\x1b\\",
        f"\x1bP([01])\\+r(?i:{name})(?:=([0-9a-fA-F]*))?\x1b\\\\")
    if status is None:
        return None
    elif status == "1":
        return bytes.fromhex(value).decode("latin-1")
    elif status == "0":
        raise RuntimeError(
            "Invalid XTGETTCAP request"
            + (f"; got unexpected payload: {value}" if value else ""))
    else:
        assert False


@functools.lru_cache(None)
def detect_terminal_and_device_attributes():
    """Detect the terminal in use."""
    xtv, = term_query(_csi(">0q"), r"(?:\x1bP>\|(.*)\x1b\\)?")
    # Even with no primary DA reported there may or may not be a semicolon
    # before the final "c" (xterm says no, kitty says yes).
    da, = term_query(
        _csi("c"), _csi_regex(r"\?\d+([;0-9]*)c"), add_terminator=False)
    return xtv, [] if not da or da == ";" else da.removeprefix(";").split(";")


def _get_pixel_size_xtwinops():
    hw = term_query(_csi("14t"), _csi_regex(r"4;(\d+);(\d+)t"))
    if hw is not None:
        h, w = hw
        return int(w), int(h)


def _get_pixel_size_tiocgwinsz():
    buf = array.array("H", [0, 0, 0, 0])
    try:
        import fcntl
        import termios
        with open(os.ctermid()) as fd:
            fcntl.ioctl(fd, termios.TIOCGWINSZ, buf)
    except (ImportError, OSError):
        pass
    else:
        _, _, w, h = buf
        if w and h:
            return w, h


def get_pixel_size():
    """Query the (width, height) in pixels of a terminal."""
    return _get_pixel_size_xtwinops() or _get_pixel_size_xtwinops() or None

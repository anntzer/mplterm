import importlib.metadata


try:
    __version__ = importlib.metadata.version("mplterm")
except ImportError:
    __version__ = "0+unknown"

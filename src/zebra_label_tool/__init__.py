"""Lightweight Zebra/ZPL label generation and printing tool."""

from .zpl import generate_zpl

__version__ = "0.2.4"

__all__ = ["__version__", "generate_zpl"]

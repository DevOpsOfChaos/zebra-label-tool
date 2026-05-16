"""Compatibility launcher for the Zebra Label Tool desktop application."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from zebra_label_tool.app import run


if __name__ == "__main__":
    run()

"""Python version compatibility shims for the services layer."""

import sys

if sys.version_info >= (3, 12):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

__all__ = ["TypedDict"]

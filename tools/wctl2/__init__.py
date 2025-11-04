"""
Typer-based implementation of the WEPPcloud control helper.

The package exposes the :class:`CLIContext` utility that centralises environment
loading and Compose configuration for all commands.
"""

from .context import CLIContext

__all__ = ["CLIContext"]

__version__ = "0.1.0"

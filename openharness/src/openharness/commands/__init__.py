"""Command system - slash commands for the CLI."""

from .registry import CommandRegistry, Command, run_command

__all__ = ["CommandRegistry", "Command", "run_command"]

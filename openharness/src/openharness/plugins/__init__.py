"""Plugin subsystem - plugin.json loading and command/agent registration."""

from .loader import PluginLoader, PluginMeta

__all__ = ["PluginLoader", "PluginMeta"]

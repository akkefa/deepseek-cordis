"""A Python plugin runtime developed in reviewed, incremental phases."""

from __future__ import annotations

import logging

from .config import ConfigValidator
from .context import Context
from .effects import Effect, EffectMeta
from .errors import CordisError, ValidationError, ValidationIssue
from .events import Events, is_bailed
from .fiber import Fiber, FiberState
from .metadata import PluginMeta, PluginSpec, inspect_plugin, plugin_meta
from .registry import PluginRuntime, Registry
from .scope import ScopeLabel, current_context
from .service import Service

# Let applications configure logging. Without this, an unconfigured process
# would emit library errors through logging's last-resort stderr handler.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "ConfigValidator",
    "Context",
    "ValidationError",
    "ValidationIssue",
    "CordisError",
    "Effect",
    "EffectMeta",
    "Events",
    "Fiber",
    "FiberState",
    "PluginMeta",
    "PluginSpec",
    "inspect_plugin",
    "plugin_meta",
    "PluginRuntime",
    "Registry",
    "Service",
    "ScopeLabel",
    "current_context",
    "is_bailed",
]

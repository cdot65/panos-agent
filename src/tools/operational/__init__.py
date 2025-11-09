"""Operational command tools for PAN-OS monitoring."""

from src.tools.operational.interfaces import show_interfaces
from src.tools.operational.routing import show_routing_table
from src.tools.operational.sessions import show_sessions
from src.tools.operational.system import show_system_resources

OPERATIONAL_TOOLS = [
    show_interfaces,
    show_routing_table,
    show_sessions,
    show_system_resources,
]

__all__ = [
    "OPERATIONAL_TOOLS",
    "show_interfaces",
    "show_routing_table",
    "show_sessions",
    "show_system_resources",
]

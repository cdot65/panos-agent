"""PAN-OS agent tools.

Exports all tools for use in autonomous and deterministic graphs.
Includes both Firewall and Panorama tools.
"""

from src.tools.address_groups import ADDRESS_GROUP_TOOLS
from src.tools.address_objects import ADDRESS_TOOLS
from src.tools.device_groups import DEVICE_GROUP_TOOLS
from src.tools.nat_policies import NAT_POLICY_TOOLS
from src.tools.orchestration.commit_operations import commit_changes
from src.tools.orchestration.crud_operations import crud_operation
from src.tools.panorama_operations import PANORAMA_OPERATIONS_TOOLS
from src.tools.security_policies import SECURITY_POLICY_TOOLS
from src.tools.service_groups import SERVICE_GROUP_TOOLS
from src.tools.services import SERVICE_TOOLS
from src.tools.template_stacks import TEMPLATE_STACK_TOOLS
from src.tools.templates import TEMPLATE_TOOLS

# All tools combined for autonomous agent
ALL_TOOLS = [
    # Firewall Object CRUD tools (22 tools)
    *ADDRESS_TOOLS,  # 5 tools
    *ADDRESS_GROUP_TOOLS,  # 5 tools
    *SERVICE_TOOLS,  # 5 tools
    *SERVICE_GROUP_TOOLS,  # 5 tools
    # Firewall Policy tools (9 tools)
    *SECURITY_POLICY_TOOLS,  # 5 tools
    *NAT_POLICY_TOOLS,  # 4 tools
    # Panorama Management tools (19 tools)
    *DEVICE_GROUP_TOOLS,  # 5 tools
    *TEMPLATE_TOOLS,  # 5 tools
    *TEMPLATE_STACK_TOOLS,  # 5 tools
    *PANORAMA_OPERATIONS_TOOLS,  # 4 tools
    # Orchestration tools (2 tools)
    crud_operation,  # Unified CRUD
    commit_changes,  # Commit workflow
]

__all__ = [
    "ALL_TOOLS",
    # Firewall tools
    "ADDRESS_TOOLS",
    "ADDRESS_GROUP_TOOLS",
    "SERVICE_TOOLS",
    "SERVICE_GROUP_TOOLS",
    "SECURITY_POLICY_TOOLS",
    "NAT_POLICY_TOOLS",
    # Panorama tools
    "DEVICE_GROUP_TOOLS",
    "TEMPLATE_TOOLS",
    "TEMPLATE_STACK_TOOLS",
    "PANORAMA_OPERATIONS_TOOLS",
    # Orchestration
    "crud_operation",
    "commit_changes",
]

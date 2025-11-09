"""Autonomous mode graph - ReAct agent for PAN-OS automation.

ReAct pattern: agent → tools → agent loop with full tool access.
Natural language interface for exploratory PAN-OS automation.
"""

import logging
from datetime import datetime
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_core.messages.base import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

from src.core.checkpoint_manager import get_checkpointer
from src.core.client import get_device_context
from src.core.config import AgentContext, get_settings
from src.core.memory_store import (
    get_firewall_operation_summary,
    retrieve_firewall_config,
    store_firewall_config,
)
from src.core.retry_policies import PANOS_RETRY_POLICY
from src.core.state_schemas import AutonomousState
from src.core.store_context import set_store
from src.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# System prompt for autonomous agent
AUTONOMOUS_SYSTEM_PROMPT = """You are an AI assistant specialized in automating Palo Alto Networks PAN-OS firewalls.

You have access to tools for managing:
- Address objects and groups
- Service objects and groups
- Security policies
- NAT policies

**Your capabilities:**
- Create, read, update, delete, and list PAN-OS objects
- Answer questions about firewall configuration
- Provide recommendations for security best practices
- Execute complex multi-step automation workflows

**Important guidelines:**
- Always verify object existence before creating to avoid errors
- Use descriptive names for objects (e.g., "web-server-10.1.1.100" not "obj1")
- Tag objects appropriately for organization
- Provide clear explanations of what you're doing
- Ask for clarification if requirements are ambiguous
- NEVER delete objects without user confirmation

**Error handling:**
- If an operation fails, explain why and suggest alternatives
- Check dependencies before deleting objects (e.g., address groups reference addresses)

**Response format:**
- Be concise but informative
- Use bullet points for lists
- Provide examples when helpful
- Always confirm successful operations

You are in **autonomous mode** - you have full tool access and can make decisions independently.
Use your judgment to complete tasks efficiently while following security best practices.
"""


async def initialize_device_context(state: AutonomousState) -> AutonomousState:
    """Initialize device context at graph start.

    Detects device type (Firewall or Panorama) and populates device context
    in state for context-aware operations.

    Args:
        state: Current autonomous state

    Returns:
        Updated state with device_context
    """
    # Get device context from client (initializes connection if needed)
    device_context = await get_device_context()

    if device_context:
        logger.info(
            f"Device detected: {device_context['device_type']} "
            f"(model: {device_context['model']}, version: {device_context['version']})"
        )
        return {"device_context": device_context}
    else:
        logger.warning("Failed to detect device context - proceeding without device info")
        return {}  # Return empty dict to avoid changing state


async def call_agent(
    state: AutonomousState, *, runtime: Runtime[AgentContext], store: BaseStore
) -> AutonomousState:
    """Call LLM agent with tools and memory context.

    Retrieves firewall operation history from store and adds it to system prompt
    to provide context about previous operations.

    Args:
        state: Current autonomous state
        runtime: Runtime context with model configuration
        store: BaseStore instance for memory access

    Returns:
        Updated state with agent response
    """
    from src.core.client import get_device_context

    settings = get_settings()

    # Initialize device context if not already set
    device_context = state.get("device_context")
    if not device_context:
        device_context = await get_device_context()
        if device_context:
            logger.debug(
                f"Initialized device context: {device_context['device_type'].value} "
                f"(vsys: {device_context.get('vsys', 'vsys1')})"
            )

    # Retrieve memory context from store
    memory_context = ""
    try:
        # Get firewall operation summary
        summary = get_firewall_operation_summary(hostname=settings.panos_hostname, store=store)

        if summary and summary.get("total_objects", 0) > 0:
            # Build memory context string
            context_parts = []
            context_parts.append(f"**Firewall Memory Context ({settings.panos_hostname}):**")
            context_parts.append(f"- Total objects: {summary['total_objects']}")

            # Add config type breakdown
            if summary.get("config_types"):
                type_breakdown = ", ".join(f"{k}: {v}" for k, v in summary["config_types"].items())
                context_parts.append(f"- Object types: {type_breakdown}")

            # Add recent operations (last 5)
            recent_ops = summary.get("recent_operations", [])[:5]
            if recent_ops:
                context_parts.append("\n**Recent operations:**")
                for op in recent_ops:
                    op_name = op.get("object_name", "unknown")
                    op_type = op.get("operation", "unknown")
                    timestamp = op.get("timestamp", "")[:10]  # Just date
                    context_parts.append(f"- {op_type} {op_name} ({timestamp})")

            memory_context = "\n".join(context_parts) + "\n\n"
            logger.debug(f"Retrieved memory context: {summary['total_objects']} objects")
    except Exception as e:
        logger.warning(f"Failed to retrieve memory context: {e}")

    # Build system prompt with memory context
    system_prompt = AUTONOMOUS_SYSTEM_PROMPT
    if memory_context:
        system_prompt = memory_context + AUTONOMOUS_SYSTEM_PROMPT

    # Get runtime context or use defaults
    context = runtime.context if (runtime and runtime.context) else AgentContext()

    # Initialize LLM with tools using runtime context
    llm = ChatAnthropic(
        model=context.model_name,
        temperature=context.temperature,
        max_tokens=context.max_tokens,
        api_key=settings.anthropic_api_key,
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    # Prepend system message
    messages = [SystemMessage(content=system_prompt)] + list[BaseMessage](state["messages"])

    # Get response (ainvoke for async)
    response = await llm_with_tools.ainvoke(messages)

    # Return updated state with device context
    result = {"messages": [response]}
    if device_context:
        result["device_context"] = device_context
    return result


def route_after_agent(
    state: AutonomousState,
) -> Literal["tools", "END"]:
    """Route based on whether agent called tools.

    Args:
        state: Current autonomous state

    Returns:
        Next node name
    """
    last_message = state["messages"][-1]

    # Check if agent made tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"Agent called {len(last_message.tool_calls)} tools")
        return "tools"

    # Agent finished - no more tool calls
    logger.info("Agent finished (no tool calls)")
    return END


async def store_operations(state: AutonomousState, *, store: BaseStore) -> AutonomousState:
    """Store operation results in memory after tool execution.

    Extracts tool call results and stores them in the store for future context.

    Args:
        state: Current autonomous state
        store: BaseStore instance for memory storage

    Returns:
        Unchanged state (pass-through)
    """
    settings = get_settings()
    hostname = settings.panos_hostname

    try:
        # Look for tool call results in messages
        # Tool results appear as ToolMessage after AIMessage with tool_calls
        messages = state.get("messages", [])
        tool_calls_found = False

        # Track operations by config type
        operations_by_type: dict[str, list[dict]] = {}

        # Scan messages for tool calls and results
        for i, msg in enumerate(messages):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                # Found tool calls - look for corresponding results
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})

                    # Map tool names to config types
                    config_type = None
                    operation = None
                    object_name = None

                    if tool_name.startswith("address_"):
                        config_type = "address_objects"
                        operation = tool_name.split("_")[-1]  # create, read, update, delete, list
                        object_name = tool_args.get("name")
                    elif tool_name.startswith("service_") and not tool_name.startswith(
                        "service_group"
                    ):
                        config_type = "services"
                        operation = tool_name.split("_")[-1]
                        object_name = tool_args.get("name")
                    elif tool_name.startswith("address_group_"):
                        config_type = "address_groups"
                        operation = tool_name.split("_")[-1]
                        object_name = tool_args.get("name")
                    elif tool_name.startswith("service_group_"):
                        config_type = "service_groups"
                        operation = tool_name.split("_")[-1]
                        object_name = tool_args.get("name")
                    elif tool_name.startswith("security_policy_"):
                        config_type = "security_policies"
                        operation = tool_name.split("_")[-1]
                        object_name = tool_args.get("name")
                    elif tool_name.startswith("nat_policy_"):
                        config_type = "nat_policies"
                        operation = tool_name.split("_")[-1]
                        object_name = tool_args.get("name")
                    elif tool_name == "crud_operation":
                        # Unified CRUD tool
                        config_type = tool_args.get("object_type", "unknown")
                        operation = tool_args.get("operation", "unknown")
                        object_name = tool_args.get("name")

                    # Only track create/update/delete operations (not read/list)
                    if config_type and operation in ("create", "update", "delete") and object_name:
                        if config_type not in operations_by_type:
                            operations_by_type[config_type] = []

                        operations_by_type[config_type].append(
                            {
                                "operation": operation,
                                "object_name": object_name,
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                            }
                        )
                        tool_calls_found = True

        # Store operations for each config type
        if tool_calls_found:
            for config_type, operations in operations_by_type.items():
                # Retrieve existing config
                existing_config = retrieve_firewall_config(hostname, config_type, store)

                # Update with new operations
                recent_ops = existing_config.get("recent_operations", []) if existing_config else []
                recent_ops.extend(operations)
                # Keep only last 10 operations
                recent_ops = recent_ops[-10:]

                # Update count (rough estimate - actual count would require API call)
                count = existing_config.get("count", 0) if existing_config else 0
                if operations:
                    # Increment for creates, decrement for deletes
                    creates = sum(1 for op in operations if op["operation"] == "create")
                    deletes = sum(1 for op in operations if op["operation"] == "delete")
                    count = max(0, count + creates - deletes)

                # Store updated config
                store_firewall_config(
                    hostname=hostname,
                    config_type=config_type,
                    data={
                        "last_updated": datetime.utcnow().isoformat() + "Z",
                        "count": count,
                        "recent_operations": recent_ops,
                    },
                    store=store,
                )
                logger.debug(f"Stored {len(operations)} operations for {config_type} on {hostname}")

    except Exception as e:
        logger.warning(f"Failed to store operations in memory: {e}")

    return state


def create_autonomous_graph(store: BaseStore | None = None, checkpointer=None) -> StateGraph:
    """Create autonomous ReAct agent graph.

    Args:
        store: Optional BaseStore instance. If None, uses InMemoryStore.
        checkpointer: Optional checkpointer instance. If None, uses sync SqliteSaver.

    Returns:
        Compiled StateGraph with checkpointer and store for autonomous mode
    """
    from langgraph.store.memory import InMemoryStore

    if store is None:
        store = InMemoryStore()

    # Set store in context for subgraphs and tools to access
    set_store(store)

    if checkpointer is None:
        checkpointer = get_checkpointer()

    workflow = StateGraph(AutonomousState, context_schema=AgentContext)

    # Create tool node
    tool_node = ToolNode(ALL_TOOLS)

    # Add nodes
    workflow.add_node("initialize_device_context", initialize_device_context)
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", tool_node, retry=PANOS_RETRY_POLICY)
    workflow.add_node("store_operations", store_operations)

    # Add edges
    workflow.add_edge(START, "initialize_device_context")
    workflow.add_edge("initialize_device_context", "agent")

    # Conditional routing after agent
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            END: END,
        },
    )

    # After tools, store operations then return to agent
    workflow.add_edge("tools", "store_operations")
    workflow.add_edge("store_operations", "agent")

    # Compile with checkpointer and store for memory
    return workflow.compile(checkpointer=checkpointer, store=store)

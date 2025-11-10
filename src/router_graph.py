"""Main router graph - Intelligent routing between autonomous and deterministic modes.

Top-level graph that:
1. Analyzes user requests using router subgraph
2. Routes to either autonomous (ReAct) or deterministic (workflow) graph
3. Returns unified response to user

This provides seamless user experience while optimizing execution pattern.
"""

import logging
import uuid
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from src.autonomous_graph import create_autonomous_graph
from src.core.checkpoint_manager import get_checkpointer
from src.core.client import get_device_context
from src.core.state_schemas import RouterState
from src.core.store_context import set_store
from src.core.subgraphs.router import create_router_subgraph
from src.deterministic_graph import create_deterministic_graph
from src.workflows.definitions import WORKFLOWS

logger = logging.getLogger(__name__)


async def initialize_device_context(state: RouterState) -> RouterState:
    """Initialize device context at graph start.

    Detects device type (Firewall or Panorama) and populates device context
    in state for context-aware operations.

    Args:
        state: Current router state

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


async def classify_request(state: RouterState) -> RouterState:
    """Classify user request and determine routing.

    Invokes router subgraph to analyze request and make routing decision.

    Args:
        state: Current router state with messages

    Returns:
        Updated state with routing decision from router subgraph
    """
    # Create router subgraph
    router_subgraph = create_router_subgraph()

    # Invoke router subgraph
    try:
        result = await router_subgraph.ainvoke(state)

        # Extract routing decision
        route_to = result.get("route_to", "autonomous")
        routing_reason = result.get("routing_reason", "No reason provided")
        confidence = result.get("confidence_score", 0.0)
        matched_workflow = result.get("matched_workflow")

        logger.info(
            f"Routing decision: {route_to} "
            f"(confidence: {confidence:.2f}, workflow: {matched_workflow})"
        )

        # Return full router result merged with current state
        return {**state, **result}

    except Exception as e:
        logger.error(f"Router classification failed: {e}")
        # Fallback to autonomous on error
        return {
            **state,
            "route_to": "autonomous",
            "routing_reason": f"Router failed: {e}",
            "confidence_score": 0.0,
        }


def route_decision(state: RouterState) -> Literal["execute_autonomous", "execute_deterministic"]:
    """Route to autonomous or deterministic graph based on classification.

    Args:
        state: Current router state with route_to decision

    Returns:
        Next node name: "execute_autonomous" or "execute_deterministic"
    """
    route_to = state.get("route_to", "autonomous")

    if route_to == "deterministic":
        logger.info("Routing to deterministic workflow execution")
        return "execute_deterministic"
    else:
        logger.info("Routing to autonomous ReAct execution")
        return "execute_autonomous"


async def execute_autonomous(state: RouterState, *, config: RunnableConfig) -> RouterState:
    """Execute request using autonomous ReAct agent.

    Creates and invokes autonomous graph for flexible, adaptive execution.

    Args:
        state: Current router state
        config: Runtime config with store and checkpointer

    Returns:
        Updated state with autonomous execution results
    """
    logger.info("Executing in autonomous mode")

    # Extract configurable from parent config to pass to subgraph
    parent_configurable = config.get("configurable", {})

    # Create config for autonomous graph with parent's store/checkpointer
    subgraph_config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),  # Unique thread for this execution
            "store": parent_configurable.get("store"),  # Pass parent's store
            "checkpointer": parent_configurable.get("checkpointer"),  # Pass parent's checkpointer
        }
    }

    # Create autonomous graph with store/checkpointer
    autonomous_graph = create_autonomous_graph(subgraph_config)

    try:
        # Prepare state for autonomous graph (needs AutonomousState format)
        autonomous_state = {
            "messages": state.get("messages", []),
            "device_context": state.get("device_context"),
        }

        # Invoke autonomous graph with subgraph config
        result = await autonomous_graph.ainvoke(autonomous_state, subgraph_config)

        # Extract messages from result
        result_messages = result.get("messages", [])

        logger.info(f"Autonomous execution complete: {len(result_messages)} messages")

        # Return state with updated messages
        return {
            **state,
            "messages": result_messages,
        }

    except Exception as e:
        logger.error(f"Autonomous execution failed: {e}")
        # Return error message
        error_msg = AIMessage(
            content=f"❌ Autonomous execution failed: {e}"
        )
        return {
            **state,
            "messages": list(state.get("messages", [])) + [error_msg],
        }


async def execute_deterministic(state: RouterState, *, config: RunnableConfig) -> RouterState:
    """Execute request using deterministic workflow.

    Creates and invokes deterministic graph with matched workflow.

    Args:
        state: Current router state with matched_workflow
        config: Runtime config with store and checkpointer

    Returns:
        Updated state with workflow execution results
    """
    workflow_name = state.get("matched_workflow")
    extracted_params = state.get("extracted_params", {})

    logger.info(f"Executing workflow: {workflow_name}")

    # Get workflow definition
    workflow_def = WORKFLOWS.get(workflow_name)
    if not workflow_def:
        logger.error(f"Workflow {workflow_name} not found")
        error_msg = AIMessage(
            content=f"❌ Error: Workflow '{workflow_name}' not found."
        )
        return {
            **state,
            "messages": list(state.get("messages", [])) + [error_msg],
        }

    # Prepare workflow message
    # We need to format the user's request as a workflow invocation
    workflow_invocation = HumanMessage(content=f"workflow: {workflow_name}")

    # Extract configurable from parent config to pass to subgraph
    parent_configurable = config.get("configurable", {})

    # Create config for deterministic graph with parent's store/checkpointer
    subgraph_config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "store": parent_configurable.get("store"),  # Pass parent's store
            "checkpointer": parent_configurable.get("checkpointer"),  # Pass parent's checkpointer
        }
    }

    # Create deterministic graph with store/checkpointer
    deterministic_graph = create_deterministic_graph(subgraph_config)

    try:
        # Prepare state for deterministic graph (needs DeterministicState format)
        # Include the workflow steps directly if we have them
        deterministic_state = {
            "messages": [workflow_invocation],
            "workflow_name": workflow_name,
            "workflow_steps": workflow_def.get("steps", []),
            "current_step_index": 0,
            "step_results": [],
            "continue_workflow": True,
            "workflow_complete": False,
            "error_occurred": False,
            "extracted_params": extracted_params,  # Pass extracted params for validation
            "workflow_parameters": None,  # Will be populated by validation node
            "device_context": state.get("device_context"),
        }

        # Deterministic graph will validate and collect any missing parameters
        # before executing workflow steps

        # Invoke deterministic graph with subgraph config
        result = await deterministic_graph.ainvoke(deterministic_state, subgraph_config)

        # Extract messages from result
        result_messages = result.get("messages", [])

        logger.info(
            f"Deterministic execution complete: workflow_complete={result.get('workflow_complete')}"
        )

        # Return state with updated messages
        # Prepend routing info message
        routing_info = AIMessage(
            content=f"ℹ️ Routing to workflow: **{workflow_name}** "
            f"(confidence: {state.get('confidence_score', 0.0):.2f})\n"
            f"Reason: {state.get('routing_reason', 'N/A')}\n"
        )

        return {
            **state,
            "messages": list(state.get("messages", [])) + [routing_info] + result_messages,
        }

    except Exception as e:
        logger.error(f"Deterministic execution failed: {e}")
        # Return error message
        error_msg = AIMessage(
            content=f"❌ Workflow execution failed: {e}"
        )
        return {
            **state,
            "messages": list(state.get("messages", [])) + [error_msg],
        }


async def format_response(state: RouterState) -> RouterState:
    """Format final response for user.

    Adds any final formatting or metadata to response.

    Args:
        state: Current router state with execution results

    Returns:
        Final state with formatted response
    """
    # For now, just pass through
    # Could add routing metadata, execution time, etc.
    logger.info("Formatting final response")
    return state


def create_router_graph(config: RunnableConfig) -> StateGraph:
    """Create main router graph with intelligent mode selection.

    Top-level graph that routes between autonomous and deterministic modes.

    Graph flow:
    START → initialize_device_context → classify_request → route_decision →
    [execute_autonomous | execute_deterministic] → format_response → END

    Args:
        config: RunnableConfig from LangGraph Studio/CLI.
                Can contain 'store' and 'checkpointer' in configurable dict.

    Returns:
        Compiled StateGraph with checkpointer and store for router mode
    """
    from langgraph.store.memory import InMemoryStore

    # Extract store and checkpointer from config if provided
    configurable = config.get("configurable", {})
    store = configurable.get("store")
    checkpointer = configurable.get("checkpointer")

    if store is None:
        store = InMemoryStore()

    # Set store in context for subgraphs and tools to access
    set_store(store)

    # Note: checkpointer should be provided by caller (LangGraph Studio/CLI)
    # If None, graph will work but won't persist state between invocations
    # Don't create sync SqliteSaver here - it won't work in async context

    workflow = StateGraph(RouterState)

    # Add nodes
    workflow.add_node("initialize_device_context", initialize_device_context)
    workflow.add_node("classify_request", classify_request)
    workflow.add_node("execute_autonomous", execute_autonomous)
    workflow.add_node("execute_deterministic", execute_deterministic)
    workflow.add_node("format_response", format_response)

    # Add edges
    workflow.add_edge(START, "initialize_device_context")
    workflow.add_edge("initialize_device_context", "classify_request")

    # Conditional routing based on classification
    workflow.add_conditional_edges(
        "classify_request",
        route_decision,
        {
            "execute_autonomous": "execute_autonomous",
            "execute_deterministic": "execute_deterministic",
        },
    )

    # Both execution paths lead to format_response
    workflow.add_edge("execute_autonomous", "format_response")
    workflow.add_edge("execute_deterministic", "format_response")

    # End after formatting
    workflow.add_edge("format_response", END)

    # Compile with checkpointer and store
    return workflow.compile(checkpointer=checkpointer, store=store)


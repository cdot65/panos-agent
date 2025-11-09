"""Deterministic mode graph - Step-by-step workflow execution.

Executes predefined workflows with LLM-based conditional routing.
More predictable than autonomous mode, similar to Ansible playbooks.
"""

import logging
import uuid
from datetime import datetime
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore

from src.core.checkpoint_manager import get_checkpointer
from src.core.client import get_device_context
from src.core.memory_store import store_workflow_execution
from src.core.state_schemas import DeterministicState
from src.core.store_context import set_store
from src.core.subgraphs.deterministic import create_deterministic_workflow_subgraph

logger = logging.getLogger(__name__)

# Import workflow definitions (will create this module next)
try:
    from src.workflows.definitions import WORKFLOWS
except ImportError:
    logger.warning("Workflow definitions not found, using empty dict")
    WORKFLOWS = {}


async def initialize_device_context(state: DeterministicState) -> DeterministicState:
    """Initialize device context at graph start.

    Detects device type (Firewall or Panorama) and populates device context
    in state for context-aware operations.

    Args:
        state: Current deterministic state

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


async def load_workflow_definition(state: DeterministicState) -> DeterministicState:
    """Load workflow definition from user message.

    Extracts workflow name from last message and loads definition.

    Args:
        state: Current deterministic state

    Returns:
        Updated state with workflow steps loaded
    """
    from src.core.client import get_device_context

    # Initialize device context if not already set
    device_context = state.get("device_context")
    if not device_context:
        device_context = await get_device_context()
        if device_context:
            logger.debug(
                f"Initialized device context: {device_context['device_type'].value} "
                f"(vsys: {device_context.get('vsys', 'vsys1')})"
            )

    # Extract workflow name from last message
    last_message = state["messages"][-1]
    user_input = last_message.content

    # Try to extract workflow name (format: "run workflow: <name>")
    workflow_name = None
    if "workflow:" in user_input.lower():
        workflow_name = user_input.lower().split("workflow:")[1].strip()
    else:
        # Assume entire message is workflow name
        workflow_name = user_input.strip()

    logger.info(f"Loading workflow: {workflow_name}")

    # If workflow_steps are already provided in state, use them (for testing/direct invocation)
    if "workflow_steps" in state and state["workflow_steps"]:
        result = {
            **state,
            "current_step_index": 0,
            "step_results": [],
            "continue_workflow": True,
            "workflow_complete": False,
            "error_occurred": False,
        }
        if device_context:
            result["device_context"] = device_context
        return result

    # Look up workflow definition
    if workflow_name not in WORKFLOWS:
        available = ", ".join(WORKFLOWS.keys()) if WORKFLOWS else "None"
        return {
            **state,
            "workflow_steps": [],
            "current_step_index": 0,
            "step_results": [],
            "continue_workflow": False,
            "workflow_complete": True,
            "error_occurred": True,
            "messages": state["messages"]
            + [
                {
                    "role": "assistant",
                    "content": f"❌ Error: Workflow '{workflow_name}' not found.\n\nAvailable workflows: {available}",
                }
            ],
        }

    workflow_def = WORKFLOWS[workflow_name]

    result = {
        **state,
        "workflow_steps": workflow_def["steps"],
        "current_step_index": 0,
        "step_results": [],
        "continue_workflow": True,
        "workflow_complete": False,
        "error_occurred": False,
    }
    if device_context:
        result["device_context"] = device_context
    return result


async def execute_workflow(state: DeterministicState, *, store: BaseStore) -> DeterministicState:
    """Execute workflow using deterministic workflow subgraph.

    Stores workflow execution history in memory after completion.

    Args:
        state: Current deterministic state
        store: BaseStore instance for memory storage

    Returns:
        Updated state with workflow execution results
    """
    if state.get("error_occurred"):
        return state  # Skip if error during load

    # Create workflow subgraph
    workflow_subgraph = create_deterministic_workflow_subgraph()

    # Extract workflow name (from loading step)
    last_message = state["messages"][-1]
    user_input = last_message.content
    workflow_name = (
        user_input.lower().split("workflow:")[-1].strip()
        if "workflow:" in user_input.lower()
        else user_input.strip()
    )

    execution_id = str(uuid.uuid4())
    started_at = datetime.utcnow().isoformat() + "Z"

    # Invoke workflow subgraph (async)
    try:
        result = await workflow_subgraph.ainvoke(
            {
                "workflow_name": workflow_name,
                "workflow_params": {},  # Could extract from user message
                "steps": state["workflow_steps"],
                "current_step": 0,
                "step_outputs": [],
                "overall_result": None,
                "message": "",
            },
            config={"configurable": {"thread_id": str(uuid.uuid4())}},
        )

        completed_at = datetime.utcnow().isoformat() + "Z"
        step_outputs = result.get("step_outputs", [])
        overall_result = result.get("overall_result", {})

        # Determine status
        status = "success"
        if state.get("error_occurred"):
            status = "failed"
        elif overall_result and overall_result.get("status") == "partial":
            status = "partial"

        # Store workflow execution history
        try:
            store_workflow_execution(
                workflow_name=workflow_name,
                execution_data={
                    "workflow_name": workflow_name,
                    "execution_id": execution_id,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "status": status,
                    "steps_executed": len(step_outputs),
                    "steps_total": len(state.get("workflow_steps", [])),
                    "results": step_outputs,
                    "metadata": {
                        "thread_id": str(uuid.uuid4()),
                    },
                },
                store=store,
            )
            logger.debug(f"Stored workflow execution history: {workflow_name}/{execution_id}")
        except Exception as e:
            logger.warning(f"Failed to store workflow execution history: {e}")

        # Update state with results
        return {
            **state,
            "step_results": step_outputs,
            "workflow_complete": True,
            "messages": state["messages"] + [{"role": "assistant", "content": result["message"]}],
        }

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        # Store failed execution
        try:
            store_workflow_execution(
                workflow_name=workflow_name,
                execution_data={
                    "workflow_name": workflow_name,
                    "execution_id": execution_id,
                    "started_at": started_at,
                    "completed_at": datetime.utcnow().isoformat() + "Z",
                    "status": "failed",
                    "steps_executed": 0,
                    "steps_total": len(state.get("workflow_steps", [])),
                    "results": [],
                    "error": str(e),
                    "metadata": {},
                },
                store=store,
            )
        except Exception as store_error:
            logger.warning(f"Failed to store failed workflow execution: {store_error}")

        return {
            **state,
            "error_occurred": True,
            "workflow_complete": True,
            "messages": state["messages"]
            + [{"role": "assistant", "content": f"❌ Workflow execution failed: {e}"}],
        }


def route_after_load(state: DeterministicState) -> Literal["execute_workflow", "END"]:
    """Route based on whether workflow loaded successfully.

    Args:
        state: Current deterministic state

    Returns:
        Next node name
    """
    if state.get("error_occurred"):
        return END
    return "execute_workflow"


def create_deterministic_graph(store: BaseStore | None = None, checkpointer=None) -> StateGraph:
    """Create deterministic workflow execution graph.

    Args:
        store: Optional BaseStore instance. If None, uses InMemoryStore.
        checkpointer: Optional checkpointer instance. If None, uses sync SqliteSaver.

    Returns:
        Compiled StateGraph with checkpointer and store for deterministic mode
    """
    from langgraph.store.memory import InMemoryStore

    if store is None:
        store = InMemoryStore()

    # Set store in context for subgraphs and tools to access
    set_store(store)

    if checkpointer is None:
        checkpointer = get_checkpointer()

    workflow = StateGraph(DeterministicState)

    # Add nodes
    workflow.add_node("initialize_device_context", initialize_device_context)
    workflow.add_node("load_workflow_definition", load_workflow_definition)
    workflow.add_node("execute_workflow", execute_workflow)

    # Add edges
    workflow.add_edge(START, "initialize_device_context")
    workflow.add_edge("initialize_device_context", "load_workflow_definition")

    # Conditional routing after load
    workflow.add_conditional_edges(
        "load_workflow_definition",
        route_after_load,
        {
            "execute_workflow": "execute_workflow",
            END: END,
        },
    )

    # End after execution
    workflow.add_edge("execute_workflow", END)

    # Compile with checkpointer and store for memory
    return workflow.compile(checkpointer=checkpointer, store=store)

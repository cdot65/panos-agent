"""Deterministic mode graph - Step-by-step workflow execution.

Executes predefined workflows with LLM-based conditional routing.
More predictable than autonomous mode, similar to Ansible playbooks.
"""

import logging
import uuid
from datetime import datetime
from typing import Literal

from langchain_core.runnables import RunnableConfig
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
        # Get collected workflow parameters from validation node
        workflow_params = state.get("workflow_parameters", {})
        logger.info(f"Executing workflow with parameters: {workflow_params}")

        result = await workflow_subgraph.ainvoke(
            {
                "workflow_name": workflow_name,
                "workflow_params": workflow_params,  # Use collected parameters
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
            await store_workflow_execution(
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
            await store_workflow_execution(
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


def prompt_user_for_parameters(missing_params: list[str], param_descriptions: dict) -> dict:
    """Prompt user for missing workflow parameters via CLI.

    Args:
        missing_params: List of parameter names that need values
        param_descriptions: Dict mapping param names to descriptions

    Returns:
        Dict of collected parameter values
    """
    from rich.console import Console
    from rich.prompt import Prompt

    console = Console()
    collected = {}

    console.print("\n📝 [bold]Workflow Parameter Collection[/bold]")
    console.print("The following parameters are needed to execute this workflow:\n")

    for param in missing_params:
        description = param_descriptions.get(param, f"Value for {param}")

        # Format prompt with description
        prompt_text = f"[cyan]{param}[/cyan] ({description})"

        # Collect value
        value = Prompt.ask(prompt_text)
        collected[param] = value

    console.print("\n✅ Parameters collected!\n")
    return collected


def filter_and_substitute_workflow_steps(
    steps: list[dict], workflow_params: dict, workflow_name: str
) -> list[dict]:
    """Filter steps based on collected params and substitute values.

    Only includes steps where the user provided the necessary parameters.
    This allows users to skip optional workflow components.

    For web_server_setup:
    - Step 0 (address): Include if server_ip OR server_name provided
    - Step 1 (HTTP service): Include if http_port provided
    - Step 2 (HTTPS service): Include if https_port provided
    - Step 3 (service group): Include if BOTH services are included
    - Step 4 (list services): Always include (query operation)

    Args:
        steps: Workflow steps with default params
        workflow_params: Collected parameters (empty strings filtered out)
        workflow_name: Name of workflow for workflow-specific logic

    Returns:
        Filtered and substituted steps
    """
    import copy

    # Deep copy to avoid modifying original
    all_steps = copy.deepcopy(steps)
    filtered_steps = []

    # Track which services were created for service group logic
    http_service_included = False
    https_service_included = False

    # Workflow-specific filtering and substitution
    if workflow_name == "web_server_setup" and len(all_steps) >= 5:
        # Step 0: Address - include if user provided server_ip or server_name
        if workflow_params.get("server_ip") or workflow_params.get("server_name"):
            step = all_steps[0]
            if workflow_params.get("server_name"):
                step["params"]["name"] = workflow_params["server_name"]
            if workflow_params.get("server_ip"):
                step["params"]["value"] = workflow_params["server_ip"]
            filtered_steps.append(step)
            logger.debug("Including address creation step")
        else:
            logger.info("Skipping address creation - no server_ip or server_name provided")

        # Step 1: HTTP service - include if user provided http_port
        if workflow_params.get("http_port"):
            step = all_steps[1]
            step["params"]["port"] = workflow_params["http_port"]
            filtered_steps.append(step)
            http_service_included = True
            logger.debug("Including HTTP service creation step")
        else:
            logger.info("Skipping HTTP service creation - no http_port provided")

        # Step 2: HTTPS service - include if user provided https_port
        if workflow_params.get("https_port"):
            step = all_steps[2]
            step["params"]["port"] = workflow_params["https_port"]
            filtered_steps.append(step)
            https_service_included = True
            logger.debug("Including HTTPS service creation step")
        else:
            logger.info("Skipping HTTPS service creation - no https_port provided")

        # Step 3: Service group - only include if both services are being created
        if http_service_included and https_service_included:
            filtered_steps.append(all_steps[3])
            logger.debug("Including service group creation step")
        else:
            logger.info("Skipping service group - not creating both HTTP and HTTPS services")

        # Step 4: List services - always include (query operation)
        filtered_steps.append(all_steps[4])
        logger.debug("Including service list step")

    else:
        # For other workflows or if step count doesn't match, include all steps with substitution
        logger.warning(
            f"Unknown workflow '{workflow_name}' or unexpected step count, "
            "including all steps without filtering"
        )
        filtered_steps = all_steps

    logger.info(
        f"Filtered workflow steps: {len(filtered_steps)}/{len(all_steps)} "
        f"steps included based on provided parameters"
    )

    return filtered_steps


async def validate_and_collect_parameters(state: DeterministicState) -> DeterministicState:
    """Validate extracted params and prompt user for missing required ones.

    Args:
        state: Current deterministic state

    Returns:
        Updated state with workflow_parameters populated and steps substituted
    """
    workflow_name = state.get("workflow_name")

    # If no workflow name, skip validation (shouldn't happen)
    if not workflow_name:
        logger.warning("No workflow name in state, skipping parameter validation")
        return {"workflow_parameters": {}}

    # Get workflow definition
    workflow_def = WORKFLOWS.get(workflow_name)
    if not workflow_def:
        logger.warning(f"Workflow {workflow_name} not found, skipping parameter validation")
        return {"workflow_parameters": {}}

    # Get extracted parameters from router
    extracted_params_raw = state.get("extracted_params", {})
    extracted_params = extracted_params_raw.get("parameters", {}) if extracted_params_raw else {}

    # Get workflow metadata
    required_params = workflow_def.get("required_params", [])
    optional_params = workflow_def.get("optional_params", [])
    param_descriptions = workflow_def.get("parameter_descriptions", {})

    logger.info(f"Validating parameters for workflow '{workflow_name}'")
    logger.debug(f"Required: {required_params}, Optional: {optional_params}")
    logger.debug(f"Extracted: {extracted_params}")

    # Find missing required parameters
    missing_required = [
        p for p in required_params
        if p not in extracted_params or not extracted_params.get(p) or extracted_params[p] == "not_provided"
    ]

    # Find missing optional parameters that might improve execution
    missing_optional = [
        p for p in optional_params
        if p not in extracted_params or not extracted_params.get(p)
    ]

    # If no required params missing and all optional provided, we're good
    if not missing_required and not missing_optional:
        logger.info("All parameters provided, no collection needed")
        final_params = extracted_params
    else:
        # Prompt user for missing parameters
        params_to_collect = missing_required + missing_optional

        logger.info(f"Collecting {len(params_to_collect)} missing parameters from user")

        collected_params = prompt_user_for_parameters(params_to_collect, param_descriptions)

        # Merge extracted and collected (filter out empty strings)
        final_params = {**extracted_params}
        for key, value in collected_params.items():
            if value:  # Only use non-empty collected values
                final_params[key] = value

    logger.info(f"Parameter collection complete: {len(final_params)} total parameters")
    logger.debug(f"Final parameters: {final_params}")

    # Filter steps based on collected parameters and substitute values
    original_steps = state.get("workflow_steps", [])
    filtered_steps = filter_and_substitute_workflow_steps(
        original_steps, final_params, workflow_name
    )

    return {
        "workflow_parameters": final_params,
        "workflow_steps": filtered_steps,
    }


def route_after_load(state: DeterministicState) -> Literal["validate_parameters", "END"]:
    """Route based on whether workflow loaded successfully.

    Args:
        state: Current deterministic state

    Returns:
        Next node name
    """
    if state.get("error_occurred"):
        return END
    return "validate_parameters"


def create_deterministic_graph(config: RunnableConfig) -> StateGraph:
    """Create deterministic workflow execution graph.

    Args:
        config: RunnableConfig from LangGraph Studio/CLI.
                Can contain 'store' and 'checkpointer' in configurable dict.

    Returns:
        Compiled StateGraph with checkpointer and store for deterministic mode
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

    workflow = StateGraph(DeterministicState)

    # Add nodes
    workflow.add_node("initialize_device_context", initialize_device_context)
    workflow.add_node("load_workflow_definition", load_workflow_definition)
    workflow.add_node("validate_parameters", validate_and_collect_parameters)
    workflow.add_node("execute_workflow", execute_workflow)

    # Add edges
    workflow.add_edge(START, "initialize_device_context")
    workflow.add_edge("initialize_device_context", "load_workflow_definition")

    # Conditional routing after load
    workflow.add_conditional_edges(
        "load_workflow_definition",
        route_after_load,
        {
            "validate_parameters": "validate_parameters",
            END: END,
        },
    )

    # After validation, proceed to execution
    workflow.add_edge("validate_parameters", "execute_workflow")

    # End after execution
    workflow.add_edge("execute_workflow", END)

    # Compile with checkpointer and store for memory
    return workflow.compile(checkpointer=checkpointer, store=store)

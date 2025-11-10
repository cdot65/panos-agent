"""Router subgraph for intelligent routing between autonomous and deterministic modes.

Analyzes user requests and determines optimal execution pattern:
- ReAct (autonomous) for exploratory, ad-hoc, or complex adaptive tasks
- Deterministic workflow for standard, repeatable, auditable operations
"""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.core.intent_classifier import (
    calculate_confidence,
    check_forced_routing,
    classify_user_intent,
    extract_parameters,
    make_routing_decision,
    match_workflow_semantic,
)
from src.core.state_schemas import RouterState
from src.workflows.definitions import WORKFLOWS

logger = logging.getLogger(__name__)


async def parse_user_request(state: RouterState) -> RouterState:
    """Extract user request from messages and classify intent.

    First node in router subgraph - analyzes the user's natural language
    request to understand what they want to do.

    Args:
        state: Current router state with messages

    Returns:
        Updated state with:
        - user_request: Extracted request string
        - intent_classification: Classified intent dictionary
    """
    # Extract user request from last message
    messages = state.get("messages", [])
    if not messages:
        logger.error("No messages in router state")
        return {
            **state,
            "user_request": "",
            "intent_classification": None,
            "route_to": "autonomous",
            "routing_reason": "No user input provided",
        }

    last_message = messages[-1]
    user_request = last_message.content if hasattr(last_message, "content") else str(last_message)

    logger.info(f"Parsing user request: {user_request[:100]}...")

    # Check for forced routing keywords first
    forced_route = check_forced_routing(user_request)
    if forced_route:
        logger.info(f"Forced routing to {forced_route} mode")
        return {
            **state,
            "user_request": user_request,
            "intent_classification": None,
            "route_to": forced_route,
            "routing_reason": f"User request contains keywords indicating {forced_route} mode",
            "confidence_score": 1.0 if forced_route == "deterministic" else 0.0,
        }

    # Classify intent using LLM
    try:
        intent = await classify_user_intent(user_request)

        return {
            **state,
            "user_request": user_request,
            "intent_classification": intent,
        }

    except Exception as e:
        logger.error(f"Failed to classify intent: {e}")
        # Fallback to autonomous on classification failure
        return {
            **state,
            "user_request": user_request,
            "intent_classification": None,
            "route_to": "autonomous",
            "routing_reason": f"Intent classification failed: {e}",
        }


async def match_workflows(state: RouterState) -> RouterState:
    """Match user intent against available workflows.

    Uses semantic similarity to find best matching workflow(s).

    Args:
        state: Current router state with intent classification

    Returns:
        Updated state with:
        - matched_workflow: Best matching workflow name or None
        - workflow_alternatives: List of alternative matches
        - confidence_score: Workflow match confidence (partial)
    """
    # Skip if already routed
    if state.get("route_to"):
        return state

    intent = state.get("intent_classification")
    if not intent:
        logger.warning("No intent classification available for workflow matching")
        return {
            **state,
            "matched_workflow": None,
            "workflow_alternatives": [],
            "confidence_score": 0.0,
        }

    # Match workflows using LLM
    try:
        workflow_name, match_confidence, alternatives = await match_workflow_semantic(
            intent, WORKFLOWS
        )

        logger.info(f"Workflow matching complete: {workflow_name} ({match_confidence:.2f})")

        return {
            **state,
            "matched_workflow": workflow_name,
            "workflow_alternatives": alternatives,
            "confidence_score": match_confidence,
        }

    except Exception as e:
        logger.error(f"Failed to match workflows: {e}")
        return {
            **state,
            "matched_workflow": None,
            "workflow_alternatives": [],
            "confidence_score": 0.0,
        }


async def extract_workflow_params(state: RouterState) -> RouterState:
    """Extract parameters from user request for matched workflow.

    Attempts to extract parameter values from natural language to populate
    workflow execution parameters.

    Args:
        state: Current router state with matched workflow

    Returns:
        Updated state with:
        - extracted_params: Dictionary of parameter values
        - confidence_score: Updated with parameter completeness
    """
    # Skip if no workflow matched or already routed
    if not state.get("matched_workflow") or state.get("route_to"):
        return state

    workflow_name = state["matched_workflow"]
    workflow_def = WORKFLOWS.get(workflow_name)

    if not workflow_def:
        logger.error(f"Workflow {workflow_name} not found in definitions")
        return state

    user_request = state.get("user_request", "")

    # Extract parameters using LLM
    try:
        extraction_result = await extract_parameters(
            user_request, workflow_name, workflow_def
        )

        parameters = extraction_result.get("parameters", {})
        completeness = extraction_result.get("completeness", 0.0)

        logger.info(
            f"Parameter extraction complete: {len(parameters)} params, "
            f"completeness={completeness:.2f}"
        )

        return {
            **state,
            "extracted_params": parameters,
            "confidence_score": completeness,  # Will be combined in next step
        }

    except Exception as e:
        logger.error(f"Failed to extract parameters: {e}")
        return {
            **state,
            "extracted_params": {},
            "confidence_score": 0.0,
        }


async def calculate_routing_confidence(state: RouterState) -> RouterState:
    """Calculate overall routing confidence score.

    Combines intent clarity, workflow match, and parameter completeness
    into a single confidence score for routing decision.

    Args:
        state: Current router state

    Returns:
        Updated state with final confidence_score
    """
    # Skip if already routed
    if state.get("route_to"):
        return state

    intent = state.get("intent_classification", {})
    workflow_match_conf = state.get("confidence_score", 0.0)
    param_completeness = 0.0

    # Get parameter completeness if we extracted params
    if state.get("extracted_params") is not None:
        # Parameter completeness was stored in confidence_score temporarily
        # during extract_workflow_params - this is the actual match confidence
        # We need both values, so let's recalculate
        matched_workflow = state.get("matched_workflow")
        if matched_workflow:
            workflow_def = WORKFLOWS.get(matched_workflow, {})
            required_params = workflow_def.get("required_params", [])
            extracted_params = state.get("extracted_params", {})

            # Calculate completeness
            if required_params:
                found = sum(
                    1
                    for p in required_params
                    if p in extracted_params
                    and extracted_params[p] not in [None, "not_provided"]
                )
                param_completeness = found / len(required_params)
            else:
                # No required params means 100% complete
                param_completeness = 1.0

    user_request = state.get("user_request", "")

    # Calculate combined confidence
    overall_confidence = calculate_confidence(
        intent, workflow_match_conf, param_completeness, user_request
    )

    logger.info(f"Overall routing confidence: {overall_confidence:.2f}")

    return {
        **state,
        "confidence_score": overall_confidence,
    }


async def make_routing_decision_node(state: RouterState) -> RouterState:
    """Make final routing decision based on confidence and matches.

    Decides whether to route to autonomous (ReAct) or deterministic (workflow)
    execution based on all gathered information.

    Args:
        state: Current router state with confidence score

    Returns:
        Updated state with:
        - route_to: "autonomous" or "deterministic"
        - routing_reason: Explanation of decision
    """
    # Skip if already routed (by forced routing)
    if state.get("route_to"):
        return state

    confidence = state.get("confidence_score", 0.0)
    workflow_name = state.get("matched_workflow")
    alternatives = state.get("workflow_alternatives", [])

    # Make decision
    route_to, reason = make_routing_decision(confidence, workflow_name, alternatives)

    logger.info(f"Routing decision: {route_to} - {reason}")

    return {
        **state,
        "route_to": route_to,
        "routing_reason": reason,
    }


def route_complete(state: RouterState) -> Literal["END"]:
    """Router complete - always routes to END.

    Args:
        state: Current router state

    Returns:
        Always returns END
    """
    return END


def create_router_subgraph() -> StateGraph:
    """Create router subgraph for intelligent mode selection.

    The router analyzes user requests and determines whether to route
    to autonomous (ReAct) or deterministic (workflow) execution.

    Graph flow:
    START → parse_user_request → match_workflows → extract_workflow_params →
    calculate_routing_confidence → make_routing_decision_node → END

    Returns:
        Compiled StateGraph for router (no checkpointer - stateless)
    """
    workflow = StateGraph(RouterState)

    # Add nodes
    workflow.add_node("parse_user_request", parse_user_request)
    workflow.add_node("match_workflows", match_workflows)
    workflow.add_node("extract_workflow_params", extract_workflow_params)
    workflow.add_node("calculate_routing_confidence", calculate_routing_confidence)
    workflow.add_node("make_routing_decision_node", make_routing_decision_node)

    # Add edges (linear flow)
    workflow.add_edge(START, "parse_user_request")
    workflow.add_edge("parse_user_request", "match_workflows")
    workflow.add_edge("match_workflows", "extract_workflow_params")
    workflow.add_edge("extract_workflow_params", "calculate_routing_confidence")
    workflow.add_edge("calculate_routing_confidence", "make_routing_decision_node")
    workflow.add_edge("make_routing_decision_node", END)

    # Compile without checkpointer (stateless subgraph)
    return workflow.compile()


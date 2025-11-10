"""Intent classification system for intelligent routing.

Uses LLM to understand user intent, match workflows, and extract parameters
for intelligent routing between autonomous and deterministic execution modes.
"""

import json
import logging
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Routing thresholds
ROUTING_THRESHOLDS = {
    "deterministic_min": 0.80,  # Minimum confidence for workflow routing
    "clarification_min": 0.60,  # Below this, don't ask, just use autonomous
    "multi_match_diff": 0.10,  # Max difference between top matches to ask for clarification
}

# Keywords that force specific routing
AUTONOMOUS_KEYWORDS = [
    "explore",
    "investigate",
    "analyze",
    "troubleshoot",
    "debug",
    "find",
    "show me",
    "what",
    "how many",
    "which",
]

DETERMINISTIC_KEYWORDS = [
    "workflow",
    "standard",
    "procedure",
    "checklist",
    "run",
    "execute",
]


# System prompts for classification
INTENT_CLASSIFICATION_PROMPT = """You are an expert at understanding firewall automation requests.

Analyze the user's request and extract the following information in JSON format:

1. **primary_intent**: The main action the user wants (create, modify, delete, query, setup, analyze, list)
2. **target_objects**: List of PAN-OS object types involved (address, service, security_policy, nat_policy, address_group, service_group)
3. **entities**: Dictionary of specific values mentioned:
   - ips: List of IP addresses or subnets mentioned
   - names: List of object names mentioned
   - ports: List of ports mentioned
   - zones: List of zones mentioned
4. **multi_step**: Boolean indicating if this appears to be a multi-step operation
5. **keywords**: List of significant keywords from the request
6. **complexity**: Rating from 1-5 (1=simple single operation, 5=complex multi-step workflow)

Respond ONLY with valid JSON, no additional text.

Example:
Input: "Create address for 10.1.1.50 named web-server"
Output: {
  "primary_intent": "create",
  "target_objects": ["address"],
  "entities": {
    "ips": ["10.1.1.50"],
    "names": ["web-server"],
    "ports": [],
    "zones": []
  },
  "multi_step": false,
  "keywords": ["create", "address"],
  "complexity": 1
}"""


WORKFLOW_MATCHING_PROMPT = """You are an expert at matching user requests to predefined workflows.

Given the user's intent and a list of available workflows, determine the best match.

User Intent:
{intent}

Available Workflows:
{workflows}

Analyze the request and respond with valid JSON containing:
1. **workflow_name**: Name of the best matching workflow, or "none" if no good match
2. **confidence**: Float from 0.0 to 1.0 indicating match quality
3. **reasoning**: Brief explanation of why this workflow matches (or doesn't)
4. **alternative_matches**: List of other possible workflow names with their confidence scores (format: [["workflow_name", 0.75], ...])

Matching guidelines:
- Check semantic similarity between request and workflow description
- Consider keyword overlap
- Match intent patterns in workflows
- Confidence > 0.8: Strong match
- Confidence 0.6-0.8: Possible match
- Confidence < 0.6: Weak match, probably better to use flexible autonomous mode

Respond ONLY with valid JSON, no additional text."""


PARAMETER_EXTRACTION_PROMPT = """You are an expert at extracting parameters from natural language for workflow execution.

Extract parameter values from the user's request to populate the workflow parameters.

User Request:
{user_request}

Workflow: {workflow_name}
Description: {workflow_description}

Required Parameters: {required_params}
Optional Parameters: {optional_params}
Parameter Descriptions: {param_descriptions}

Analyze the request and extract parameter values. For each parameter:
- If mentioned in request: extract the value
- If not mentioned but required: set to "not_provided"
- If not mentioned and optional: set to null

Respond with valid JSON in this format:
{
  "parameters": {
    "param_name": "extracted_value",
    "other_param": null
  },
  "completeness": 0.85,
  "missing_required": ["param1", "param2"],
  "notes": "Brief notes about extraction"
}

The completeness score should be:
- 1.0 if all required params found
- Proportional to (found_params / total_params) if some missing

Respond ONLY with valid JSON, no additional text."""


async def classify_user_intent(user_input: str) -> dict:
    """Classify user intent using LLM.

    Analyzes the user's natural language request and extracts:
    - Primary intent (create, modify, delete, etc.)
    - Target objects (address, service, policy, etc.)
    - Specific entities (IPs, names, ports)
    - Complexity indicators

    Args:
        user_input: User's natural language request

    Returns:
        Dictionary containing classified intent with keys:
        - primary_intent: str
        - target_objects: list[str]
        - entities: dict
        - multi_step: bool
        - keywords: list[str]
        - complexity: int (1-5)

    Raises:
        Exception: If classification fails (caller should handle)
    """
    settings = get_settings()

    try:
        llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.0,  # Deterministic for classification
            api_key=settings.anthropic_api_key,
        )

        messages = [
            SystemMessage(content=INTENT_CLASSIFICATION_PROMPT),
            ("user", user_input),
        ]

        response = await llm.ainvoke(messages)
        content = response.content

        # Parse JSON response
        try:
            intent_data = json.loads(content)
            logger.info(f"Intent classified: {intent_data.get('primary_intent', 'unknown')}")
            return intent_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent classification JSON: {e}")
            logger.debug(f"LLM response: {content}")
            # Return fallback intent
            return {
                "primary_intent": "unknown",
                "target_objects": [],
                "entities": {"ips": [], "names": [], "ports": [], "zones": []},
                "multi_step": False,
                "keywords": [],
                "complexity": 3,
            }

    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        raise


async def match_workflow_semantic(intent: dict, workflows: dict) -> tuple[Optional[str], float, list]:
    """Match user intent to workflows using semantic similarity.

    Uses LLM to compare the user's intent against available workflow
    descriptions and metadata to find the best match.

    Args:
        intent: Classified intent dictionary from classify_user_intent()
        workflows: Dictionary of workflow definitions

    Returns:
        Tuple of (workflow_name, confidence_score, alternatives)
        - workflow_name: Name of best matching workflow or None
        - confidence_score: Float 0.0-1.0
        - alternatives: List of tuples [(workflow_name, score), ...]

    Raises:
        Exception: If matching fails (caller should handle)
    """
    settings = get_settings()

    try:
        # Prepare workflow summaries for LLM
        workflow_summaries = []
        for name, workflow_def in workflows.items():
            summary = {
                "name": name,
                "display_name": workflow_def.get("name", name),
                "description": workflow_def.get("description", ""),
                "keywords": workflow_def.get("keywords", []),
                "intent_patterns": workflow_def.get("intent_patterns", []),
            }
            workflow_summaries.append(summary)

        llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.0,
            api_key=settings.anthropic_api_key,
        )

        prompt = WORKFLOW_MATCHING_PROMPT.format(
            intent=json.dumps(intent, indent=2),
            workflows=json.dumps(workflow_summaries, indent=2),
        )

        messages = [
            SystemMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        content = response.content

        # Parse JSON response
        try:
            match_data = json.loads(content)
            workflow_name = match_data.get("workflow_name")
            confidence = match_data.get("confidence", 0.0)
            alternatives = match_data.get("alternative_matches", [])

            # Convert "none" to None
            if workflow_name == "none":
                workflow_name = None

            logger.info(
                f"Workflow match: {workflow_name} (confidence: {confidence:.2f})"
            )

            return workflow_name, confidence, alternatives

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse workflow matching JSON: {e}")
            logger.debug(f"LLM response: {content}")
            return None, 0.0, []

    except Exception as e:
        logger.error(f"Workflow matching failed: {e}")
        raise


async def extract_parameters(
    user_input: str, workflow_name: str, workflow_def: dict
) -> dict:
    """Extract parameters from user input for workflow execution.

    Uses LLM to identify and extract parameter values from natural language.

    Args:
        user_input: User's natural language request
        workflow_name: Name of the matched workflow
        workflow_def: Workflow definition dictionary

    Returns:
        Dictionary containing:
        - parameters: Dict of parameter names to extracted values
        - completeness: Float 0.0-1.0 indicating how many params found
        - missing_required: List of required params not found
        - notes: String with extraction notes

    Raises:
        Exception: If extraction fails (caller should handle)
    """
    settings = get_settings()

    try:
        required_params = workflow_def.get("required_params", [])
        optional_params = workflow_def.get("optional_params", [])
        param_descriptions = workflow_def.get("parameter_descriptions", {})

        llm = ChatAnthropic(
            model=settings.model_name,
            temperature=0.0,
            api_key=settings.anthropic_api_key,
        )

        prompt = PARAMETER_EXTRACTION_PROMPT.format(
            user_request=user_input,
            workflow_name=workflow_name,
            workflow_description=workflow_def.get("description", ""),
            required_params=json.dumps(required_params),
            optional_params=json.dumps(optional_params),
            param_descriptions=json.dumps(param_descriptions, indent=2),
        )

        messages = [
            SystemMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)
        content = response.content

        # Parse JSON response
        try:
            extraction_data = json.loads(content)
            completeness = extraction_data.get("completeness", 0.0)
            logger.info(
                f"Parameters extracted for {workflow_name}: completeness={completeness:.2f}"
            )
            return extraction_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse parameter extraction JSON: {e}")
            logger.debug(f"LLM response: {content}")
            # Return empty extraction
            return {
                "parameters": {},
                "completeness": 0.0,
                "missing_required": required_params,
                "notes": "Parameter extraction failed",
            }

    except Exception as e:
        logger.error(f"Parameter extraction failed: {e}")
        raise


def calculate_confidence(
    intent: dict,
    workflow_match_confidence: float,
    parameter_completeness: float,
    user_input: str,
) -> float:
    """Calculate overall routing confidence score.

    Combines multiple factors to determine confidence in routing decision:
    - Intent clarity
    - Workflow match quality
    - Parameter completeness
    - Contextual factors (keywords, complexity)

    Args:
        intent: Classified intent dictionary
        workflow_match_confidence: Confidence from workflow matching (0.0-1.0)
        parameter_completeness: Completeness from parameter extraction (0.0-1.0)
        user_input: Original user request

    Returns:
        Overall confidence score (0.0-1.0)
    """
    # Base calculation from components
    intent_clarity = 1.0 if intent.get("primary_intent") != "unknown" else 0.3
    complexity_factor = 1.0 - (intent.get("complexity", 3) - 1) / 10  # Lower complexity = higher confidence

    # Weighted combination
    confidence = (
        intent_clarity * 0.3
        + workflow_match_confidence * 0.4
        + parameter_completeness * 0.2
        + complexity_factor * 0.1
    )

    # Check for forcing keywords
    user_input_lower = user_input.lower()

    # Force autonomous if exploratory keywords found
    if any(keyword in user_input_lower for keyword in AUTONOMOUS_KEYWORDS):
        logger.info("Autonomous keyword detected, lowering confidence")
        confidence = min(confidence, 0.5)  # Force below threshold

    # Boost confidence if deterministic keywords found
    if any(keyword in user_input_lower for keyword in DETERMINISTIC_KEYWORDS):
        logger.info("Deterministic keyword detected, boosting confidence")
        confidence = min(confidence * 1.2, 1.0)

    return confidence


def make_routing_decision(
    confidence: float,
    workflow_name: Optional[str],
    alternatives: list,
) -> tuple[str, str]:
    """Make final routing decision based on confidence and matches.

    Args:
        confidence: Overall confidence score (0.0-1.0)
        workflow_name: Best matching workflow name or None
        alternatives: List of alternative workflow matches

    Returns:
        Tuple of (route_to, reason)
        - route_to: "autonomous" or "deterministic"
        - reason: Human-readable explanation
    """
    # No workflow match → autonomous
    if workflow_name is None:
        return (
            "autonomous",
            "No matching workflow found. Using flexible autonomous mode.",
        )

    # Low confidence → autonomous
    if confidence < ROUTING_THRESHOLDS["deterministic_min"]:
        return (
            "autonomous",
            f"Low confidence ({confidence:.2f}) in workflow match. Using autonomous mode for flexibility.",
        )

    # Check for ambiguous matches (multiple high-confidence alternatives)
    if alternatives:
        # Get top alternative score
        top_alt_score = max(alt[1] for alt in alternatives) if alternatives else 0.0
        workflow_match_conf = confidence / 0.4  # Reverse the weight calculation (approximate)

        # If top alternative is very close to best match, it's ambiguous
        if workflow_match_conf - top_alt_score < ROUTING_THRESHOLDS["multi_match_diff"]:
            return (
                "autonomous",
                f"Multiple similar workflow matches found. Using autonomous mode to clarify intent.",
            )

    # High confidence + clear match → deterministic
    return (
        "deterministic",
        f"Matched workflow '{workflow_name}' with high confidence ({confidence:.2f}).",
    )


def check_forced_routing(user_input: str) -> Optional[str]:
    """Check if user input contains keywords that force specific routing.

    Args:
        user_input: User's request

    Returns:
        "autonomous" or "deterministic" if forced, None otherwise
    """
    user_input_lower = user_input.lower()

    # Check for forcing keywords
    if any(keyword in user_input_lower for keyword in AUTONOMOUS_KEYWORDS):
        return "autonomous"

    if any(keyword in user_input_lower for keyword in DETERMINISTIC_KEYWORDS):
        return "deterministic"

    return None


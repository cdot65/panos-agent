"""Workflow discovery tool for autonomous agent.

Allows the ReAct agent to search for and recommend workflows that match
user intent, enabling the agent to suggest using deterministic workflows
when appropriate.
"""

import logging

from langchain_core.tools import tool

from src.workflows.definitions import WORKFLOWS, list_workflows

logger = logging.getLogger(__name__)


@tool
def discover_workflows(user_intent: str = "") -> str:
    """Search available workflows that match user's intent or list all workflows.

    This tool helps the autonomous agent find relevant predefined workflows
    that could handle the user's request more efficiently and predictably.

    Use this tool when:
    - User asks about available workflows
    - User's request might match a standard workflow
    - You want to suggest a workflow instead of ad-hoc tool calls
    - User asks "what workflows can help with X?"

    Args:
        user_intent: Description of what the user wants to do (optional).
                    If empty, returns list of all workflows.

    Returns:
        String with matching workflows or all workflows with descriptions.

    Examples:
        >>> discover_workflows("set up web server")
        "Found 2 matching workflows:
        1. web_server_setup: Create address and service objects for a web server
        2. complete_security_workflow: End-to-end: create objects, create policy, commit changes"

        >>> discover_workflows()
        "Available workflows (6 total):
        1. simple_address: Create a single address object with validation
        2. web_server_setup: Create address and service objects for a web server
        ..."
    """
    try:
        if not user_intent or user_intent.strip() == "":
            # List all workflows
            workflow_names = list_workflows()
            result = [f"📋 **Available Workflows ({len(workflow_names)} total):**\n"]

            for i, name in enumerate(workflow_names, 1):
                workflow_def = WORKFLOWS[name]
                display_name = workflow_def.get("name", name)
                description = workflow_def.get("description", "No description")
                result.append(f"{i}. **{display_name}** (`{name}`)")
                result.append(f"   {description}\n")

            result.append(
                "\n💡 **Tip:** Use `discover_workflows('your intent')` to find workflows matching specific needs."
            )

            return "\n".join(result)

        # Search for matching workflows based on intent
        user_intent_lower = user_intent.lower()
        matches = []

        for name, workflow_def in WORKFLOWS.items():
            score = 0.0
            match_reasons = []

            # Check description match
            description = workflow_def.get("description", "").lower()
            if any(word in description for word in user_intent_lower.split()):
                score += 0.3
                match_reasons.append("description")

            # Check keywords match
            keywords = [k.lower() for k in workflow_def.get("keywords", [])]
            matching_keywords = [kw for kw in keywords if kw in user_intent_lower]
            if matching_keywords:
                score += 0.4 * (len(matching_keywords) / max(len(keywords), 1))
                match_reasons.append(f"keywords: {', '.join(matching_keywords)}")

            # Check intent patterns match
            intent_patterns = [p.lower() for p in workflow_def.get("intent_patterns", [])]
            for pattern in intent_patterns:
                # Check if pattern words are in user intent
                pattern_words = set(pattern.split())
                intent_words = set(user_intent_lower.split())
                overlap = len(pattern_words & intent_words)
                if overlap > 0:
                    score += 0.3 * (overlap / len(pattern_words))
                    match_reasons.append("intent pattern")
                    break

            # If any match found, add to results
            if score > 0.2:  # Minimum threshold
                matches.append(
                    {
                        "name": name,
                        "display_name": workflow_def.get("name", name),
                        "description": workflow_def.get("description", ""),
                        "score": score,
                        "reasons": match_reasons,
                        "keywords": workflow_def.get("keywords", []),
                        "required_params": workflow_def.get("required_params", []),
                        "optional_params": workflow_def.get("optional_params", []),
                    }
                )

        # Sort by score (descending)
        matches.sort(key=lambda x: x["score"], reverse=True)

        if not matches:
            return (
                f"🔍 No workflows found matching '{user_intent}'.\n\n"
                f"This might be better handled with flexible autonomous mode using tools directly.\n"
                f"Or try `discover_workflows()` to see all available workflows."
            )

        # Format results
        result = [
            f"🎯 **Found {len(matches)} workflow(s) matching '{user_intent}':**\n"
        ]

        for i, match in enumerate(matches[:5], 1):  # Top 5 matches
            result.append(
                f"{i}. **{match['display_name']}** (`{match['name']}`) - Match: {match['score']:.0%}"
            )
            result.append(f"   {match['description']}")

            if match["required_params"]:
                result.append(
                    f"   Required params: {', '.join(match['required_params'])}"
                )

            if match["optional_params"]:
                result.append(
                    f"   Optional params: {', '.join(match['optional_params'])}"
                )

            result.append(f"   Matched on: {', '.join(match['reasons'])}\n")

        if len(matches) > 5:
            result.append(f"... and {len(matches) - 5} more matches")

        result.append(
            "\n💡 **Suggestion:** You can suggest using one of these workflows "
            "to the user for more predictable and auditable execution."
        )

        return "\n".join(result)

    except Exception as e:
        logger.error(f"Workflow discovery failed: {e}")
        return f"❌ Error discovering workflows: {e}"


@tool
def get_workflow_details(workflow_name: str) -> str:
    """Get detailed information about a specific workflow.

    Use this tool to get complete details about a workflow including
    all steps, parameters, and execution flow.

    Args:
        workflow_name: Name of the workflow (e.g., 'web_server_setup')

    Returns:
        String with complete workflow details.

    Examples:
        >>> get_workflow_details("web_server_setup")
        "Workflow: Web Server Setup
        Description: Create address and service objects for a web server
        Steps: 5
        ..."
    """
    try:
        workflow_def = WORKFLOWS.get(workflow_name)

        if not workflow_def:
            available = ", ".join(list_workflows())
            return (
                f"❌ Workflow '{workflow_name}' not found.\n\n"
                f"Available workflows: {available}\n"
                f"Use `discover_workflows()` for detailed list."
            )

        # Format detailed info
        result = [f"📋 **Workflow: {workflow_def.get('name', workflow_name)}**\n"]

        result.append(f"**ID:** `{workflow_name}`")
        result.append(f"**Description:** {workflow_def.get('description', 'N/A')}")

        # Keywords
        keywords = workflow_def.get("keywords", [])
        if keywords:
            result.append(f"**Keywords:** {', '.join(keywords)}")

        # Intent patterns
        patterns = workflow_def.get("intent_patterns", [])
        if patterns:
            result.append(f"\n**Intent Patterns:**")
            for pattern in patterns:
                result.append(f"  - \"{pattern}\"")

        # Parameters
        required = workflow_def.get("required_params", [])
        optional = workflow_def.get("optional_params", [])
        param_desc = workflow_def.get("parameter_descriptions", {})

        result.append(f"\n**Parameters:**")
        if required:
            result.append(f"  Required: {', '.join(required)}")
        else:
            result.append(f"  Required: None")

        if optional:
            result.append(f"  Optional: {', '.join(optional)}")

        if param_desc:
            result.append(f"\n**Parameter Details:**")
            for param, desc in param_desc.items():
                result.append(f"  - {param}: {desc}")

        # Steps
        steps = workflow_def.get("steps", [])
        result.append(f"\n**Execution Steps ({len(steps)} total):**")

        for i, step in enumerate(steps, 1):
            step_name = step.get("name", f"Step {i}")
            step_type = step.get("type", "unknown")
            tool = step.get("tool", "N/A")

            result.append(f"  {i}. {step_name}")
            result.append(f"     Type: {step_type}")

            if step_type == "tool_call":
                result.append(f"     Tool: {tool}")
                params = step.get("params", {})
                if params:
                    result.append(f"     Params: {list(params.keys())}")

            elif step_type == "approval":
                message = step.get("message", "N/A")
                result.append(f"     Approval: {message}")

        result.append(
            f"\n💡 **Usage:** Recommend this workflow to user or execute it "
            f"via the deterministic graph."
        )

        return "\n".join(result)

    except Exception as e:
        logger.error(f"Get workflow details failed: {e}")
        return f"❌ Error getting workflow details: {e}"


# Export tools for agent
__all__ = ["discover_workflows", "get_workflow_details"]


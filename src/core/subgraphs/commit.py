"""PAN-OS commit workflow subgraph.

Handles firewall commits with optional approval gates and job polling.

Workflow:
1. Validate commit input
2. Check if approval required (HITL gate)
3. Execute commit
4. Poll job status (if sync mode)
5. Format response

Features:
- Sync/async modes
- Job status polling
- Human approval gates
- Detailed error reporting
"""

import asyncio
import logging

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.core.client import get_panos_client
from src.core.panos_api import PanOSAPIError, PanOSConnectionError, commit, get_job_status
from src.core.panos_models import JobStatus
from src.core.retry_policies import PANOS_COMMIT_RETRY_POLICY
from src.core.state_schemas import CommitState

logger = logging.getLogger(__name__)


async def validate_commit_input(state: CommitState) -> CommitState:
    """Validate commit operation inputs.

    Args:
        state: Current commit state

    Returns:
        Updated state with validation result
    """
    logger.info("Validating commit operation")

    # Description is optional
    description = state.get("description", "Commit via PAN-OS Agent")

    return {
        **state,
        "description": description,
    }


async def check_approval_required(state: CommitState) -> CommitState:
    """Check if human approval is required before commit.

    Args:
        state: Current commit state

    Returns:
        Updated state with approval status
    """
    if not state.get("require_approval", False):
        # No approval required, proceed
        return {**state, "approval_granted": True}

    logger.info("Requesting human approval for commit")

    # Use LangGraph interrupt for HITL
    approval = interrupt(
        {
            "type": "commit_approval",
            "message": f"Approve commit: {state.get('description', 'No description')}?",
            "description": state.get("description"),
        }
    )

    if approval:
        logger.info("Commit approved by user")
        return {**state, "approval_granted": True}
    else:
        logger.info("Commit rejected by user")
        return {
            **state,
            "approval_granted": False,
            "message": "❌ Commit rejected by user",
            "error": "User did not approve commit",
        }


async def execute_commit(state: CommitState) -> CommitState:
    """Execute PAN-OS commit operation.

    Args:
        state: Current commit state

    Returns:
        Updated state with commit job details
    """
    if not state.get("approval_granted", True):
        # Skip if not approved
        return state

    description = state.get("description", "Commit via PAN-OS Agent")

    logger.info(f"Executing commit: {description}")

    try:
        client = await get_panos_client()

        # Execute commit (returns job ID)
        job_id = await commit(description, client, partial=False)

        logger.info(f"Commit initiated, job ID: {job_id}")

        return {
            **state,
            "commit_job_id": job_id,
            "job_status": "PEND",  # Pending
        }

    except PanOSConnectionError as e:
        logger.error(f"Commit connection failed: {e}")
        return {
            **state,
            "error": f"Connection error: {e}",
            "message": f"❌ Commit failed: {e}",
        }
    except PanOSAPIError as e:
        logger.error(f"Commit API error: {e}")
        return {
            **state,
            "error": f"API error: {e}",
            "message": f"❌ Commit failed: {e}",
        }
    except Exception as e:
        logger.error(f"Commit failed: {e}")
        return {
            **state,
            "error": str(e),
            "message": f"❌ Commit failed: {e}",
        }


async def poll_job_status(state: CommitState) -> CommitState:
    """Poll commit job status until completion.

    Args:
        state: Current commit state

    Returns:
        Updated state with final job status
    """
    if state.get("error"):
        # Skip if commit failed
        return state

    if not state.get("sync", True):
        # Async mode - return immediately
        return {
            **state,
            "message": f"✅ Commit initiated (job ID: {state.get('commit_job_id')})",
        }

    # Sync mode - poll until completion
    job_id = state.get("commit_job_id")
    if not job_id:
        return {
            **state,
            "error": "No job ID found",
            "message": "❌ Commit job ID missing",
        }

    logger.info(f"Polling job {job_id} status...")

    try:
        client = await get_panos_client()

        # Poll job status
        max_polls = 60  # Max 5 minutes (60 * 5 seconds)
        poll_interval = 5  # 5 seconds

        for poll_count in range(max_polls):
            try:
                # Get job status
                job_status_response = await get_job_status(job_id, client)

                logger.info(
                    f"Job {job_id} status: {job_status_response.status} "
                    f"({job_status_response.progress}%)"
                )

                if job_status_response.status == JobStatus.FINISHED:
                    # Success
                    logger.info(f"Commit completed: {job_status_response.result}")

                    return {
                        **state,
                        "job_status": "FIN",
                        "job_result": {
                            "status": "FIN",
                            "result": job_status_response.result,
                        },
                        "message": f"✅ Commit completed successfully (job {job_id})",
                    }

                elif job_status_response.status == JobStatus.FAILED:
                    # Failure
                    details = job_status_response.details or "Unknown error"
                    logger.error(f"Commit failed: {details}")

                    return {
                        **state,
                        "job_status": "FAIL",
                        "job_result": {"status": "FAIL", "details": details},
                        "error": details,
                        "message": f"❌ Commit failed: {details}",
                    }

                elif job_status_response.status in [JobStatus.PENDING, JobStatus.ACTIVE]:
                    # Still running
                    await asyncio.sleep(poll_interval)
                    continue

            except PanOSAPIError as poll_error:
                logger.warning(f"Error polling job status: {poll_error}")
                await asyncio.sleep(poll_interval)
                continue

        # Timeout
        logger.warning(f"Job {job_id} polling timeout")
        return {
            **state,
            "job_status": "TIMEOUT",
            "message": f"⚠️ Commit job {job_id} polling timeout (check firewall manually)",
        }

    except PanOSConnectionError as e:
        logger.error(f"Connection error polling commit job: {e}")
        return {
            **state,
            "error": f"Connection error: {e}",
            "message": f"❌ Error polling commit job: {e}",
        }
    except Exception as e:
        logger.error(f"Error polling commit job: {e}")
        return {
            **state,
            "error": str(e),
            "message": f"❌ Error polling commit job: {e}",
        }


async def format_commit_response(state: CommitState) -> CommitState:
    """Format final commit response.

    Args:
        state: Current commit state

    Returns:
        Updated state with formatted message
    """
    if state.get("message"):
        # Message already set
        return state

    # Default success message
    job_id = state.get("commit_job_id")
    return {
        **state,
        "message": f"✅ Commit operation completed (job {job_id})",
    }


def create_commit_subgraph() -> StateGraph:
    """Create commit workflow subgraph.

    Returns:
        Compiled StateGraph for commit operations
    """
    workflow = StateGraph(CommitState)

    # Add nodes (all async now)
    workflow.add_node("validate_commit_input", validate_commit_input)
    workflow.add_node("check_approval_required", check_approval_required)
    workflow.add_node("execute_commit", execute_commit, retry=PANOS_COMMIT_RETRY_POLICY)
    workflow.add_node("poll_job_status", poll_job_status, retry=PANOS_COMMIT_RETRY_POLICY)
    workflow.add_node("format_commit_response", format_commit_response)

    # Add edges
    workflow.add_edge(START, "validate_commit_input")
    workflow.add_edge("validate_commit_input", "check_approval_required")
    workflow.add_edge("check_approval_required", "execute_commit")
    workflow.add_edge("execute_commit", "poll_job_status")
    workflow.add_edge("poll_job_status", "format_commit_response")
    workflow.add_edge("format_commit_response", END)

    return workflow.compile()

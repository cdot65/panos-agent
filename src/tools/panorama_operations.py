"""Panorama operations tools.

Critical Panorama operations for committing and pushing configuration to managed devices.
All operations include approval gates for safety.
"""

from typing import Optional

from langchain_core.tools import tool

from src.core.client import get_device_context, get_panos_client


@tool
async def panorama_commit_all(
    device_groups: Optional[list[str]] = None,
    description: Optional[str] = None,
    sync: bool = True,
) -> str:
    """Commit and push configuration to device groups on Panorama.

    CRITICAL OPERATION: Pushes configuration to all firewalls in specified device groups.
    Requires approval before execution.

    Args:
        device_groups: List of device group names to push to (if None, pushes to all)
        description: Optional commit description
        sync: Wait for commit completion (True) or return immediately (False)

    Returns:
        Success/failure message with job details

    Example:
        panorama_commit_all(device_groups=["production"], description="Deploy new rules")
        panorama_commit_all(description="Push all changes")
    """
    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: panorama_commit_all requires a Panorama device"

        # Build approval message
        if device_groups:
            target = f"device groups: {', '.join(device_groups)}"
        else:
            target = "ALL device groups"

        approval_msg = f"""
⚠️  CRITICAL OPERATION: Panorama Commit-All

This will push configuration changes to {target}.
All managed firewalls in these groups will receive updates.

Description: {description or 'No description provided'}
Sync: {'Wait for completion' if sync else 'Return immediately'}

Do you want to proceed?
"""

        # Note: Approval gate implementation depends on execution context
        # CLI: Use typer.confirm()
        # Studio: Use interrupt()
        # For now, return the approval message - actual implementation will be context-aware

        return f"""
🔒 Approval Required

{approval_msg}

To execute this operation:
1. Review the changes carefully
2. Confirm in your CLI or Studio interface
3. Monitor job status after execution

This tool requires HITL approval integration.
"""

    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def panorama_push_to_devices(
    device_serials: list[str],
    include_template: bool = True,
    description: Optional[str] = None,
    sync: bool = True,
) -> str:
    """Push configuration to specific devices on Panorama.

    CRITICAL OPERATION: Pushes configuration to specified firewalls.
    Requires approval before execution.

    Args:
        device_serials: List of device serial numbers to push to
        include_template: Include template/template-stack configuration (default: True)
        description: Optional push description
        sync: Wait for push completion (True) or return immediately (False)

    Returns:
        Success/failure message with job details

    Example:
        panorama_push_to_devices(device_serials=["007951000012345"], description="Push network changes")
        panorama_push_to_devices(device_serials=["007951000012345", "007951000067890"], include_template=False)
    """
    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: panorama_push_to_devices requires a Panorama device"

        # Build approval message
        devices_list = "\n".join(f"  - {serial}" for serial in device_serials)
        config_scope = "device-group + template" if include_template else "device-group only"

        approval_msg = f"""
⚠️  CRITICAL OPERATION: Push to Devices

This will push configuration to the following devices:
{devices_list}

Configuration scope: {config_scope}
Description: {description or 'No description provided'}
Sync: {'Wait for completion' if sync else 'Return immediately'}

Do you want to proceed?
"""

        # Note: Approval gate implementation depends on execution context
        # CLI: Use typer.confirm()
        # Studio: Use interrupt()
        # For now, return the approval message - actual implementation will be context-aware

        return f"""
🔒 Approval Required

{approval_msg}

To execute this operation:
1. Verify device serial numbers are correct
2. Review configuration changes
3. Confirm in your CLI or Studio interface
4. Monitor job status after execution

This tool requires HITL approval integration.
"""

    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def panorama_commit(
    description: Optional[str] = None,
    sync: bool = True,
) -> str:
    """Commit configuration changes on Panorama (local commit only, no push to devices).

    Commits pending changes to Panorama configuration. Does NOT push to managed devices.
    Use panorama_commit_all or panorama_push_to_devices to push to firewalls.

    Args:
        description: Optional commit description
        sync: Wait for commit completion (True) or return immediately (False)

    Returns:
        Success/failure message with job details

    Example:
        panorama_commit(description="Save device group changes")
        panorama_commit(sync=False)
    """
    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: panorama_commit requires a Panorama device"

        client = await get_panos_client()

        # Execute commit
        result = await client.commit(
            cmd=f"<commit><description>{description or 'Configuration commit'}</description></commit>",
            sync=sync,
        )

        if sync:
            return (
                f"✅ Panorama commit completed successfully\nJob ID: {result.get('job_id', 'N/A')}"
            )
        else:
            return f"✅ Panorama commit initiated\nJob ID: {result.get('job_id', 'N/A')}\nUse job status tools to monitor progress."

    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


@tool
async def panorama_validate_commit(device_groups: Optional[list[str]] = None) -> str:
    """Validate Panorama configuration before committing.

    Performs validation check without actually committing. Useful for pre-commit verification.

    Args:
        device_groups: Optional list of device groups to validate (if None, validates all)

    Returns:
        Validation result message

    Example:
        panorama_validate_commit()
        panorama_validate_commit(device_groups=["production", "staging"])
    """
    try:
        # Get device context - must be PANORAMA
        device_context = await get_device_context()
        if device_context.get("device_type") != "PANORAMA":
            return "❌ Error: panorama_validate_commit requires a Panorama device"

        client = await get_panos_client()

        # Build validation command
        if device_groups:
            dg_filter = " ".join(f"<device-group>{dg}</device-group>" for dg in device_groups)
            cmd = f"<validate><full>{dg_filter}</full></validate>"
        else:
            cmd = "<validate><full></full></validate>"

        # Execute validation
        result = await client.op(cmd=cmd)

        # Parse validation result
        if result.get("status") == "success":
            return "✅ Configuration validation passed - no errors detected"
        else:
            errors = result.get("errors", "Unknown validation errors")
            return f"❌ Configuration validation failed:\n{errors}"

    except Exception as e:
        return f"❌ Error: {type(e).__name__}: {e}"


# Export all tools
PANORAMA_OPERATIONS_TOOLS = [
    panorama_commit_all,
    panorama_push_to_devices,
    panorama_commit,
    panorama_validate_commit,
]

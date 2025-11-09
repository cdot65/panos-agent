"""Session monitoring operational tools."""

from typing import Optional

from langchain_core.tools import tool

from src.core.client import get_panos_client
from src.core.panos_api import operational_command


@tool
async def show_sessions(
    source: Optional[str] = None,
    destination: Optional[str] = None,
    application: Optional[str] = None,
) -> str:
    """Show active firewall sessions with optional filters.

    Args:
        source: Filter by source IP address (e.g., "10.1.1.5")
        destination: Filter by destination IP address (e.g., "8.8.8.8")
        application: Filter by application name (e.g., "web-browsing")

    Returns:
        List of active sessions with details including:
        - Source and destination IPs/ports
        - Application
        - State
        - Duration
        - Bytes transferred

    Examples:
        show_sessions()
        show_sessions(source="10.1.1.5")
        show_sessions(application="ssl")
    """
    try:
        client = await get_panos_client()

        # Build command with filters
        if source or destination or application:
            # Use filtered session query
            filters = []
            if source:
                filters.append(f"<source>{source}</source>")
            if destination:
                filters.append(f"<destination>{destination}</destination>")
            if application:
                filters.append(f"<application>{application}</application>")

            filter_xml = "".join(filters)
            cmd = f"<show><session><all><filter>{filter_xml}</filter></all></session></show>"
        else:
            # Show all sessions
            cmd = "<show><session><all></all></session></show>"

        result = await operational_command(cmd, client)

        # Parse session count
        total_elem = result.find(".//total")
        total_sessions = total_elem.text if total_elem is not None else "0"

        # Parse session entries
        sessions = []
        for entry in result.findall(".//entry"):
            src = entry.findtext(".//source", "N/A")
            src_port = entry.findtext(".//sport", "")
            dst = entry.findtext(".//dst", "N/A")
            dst_port = entry.findtext(".//dport", "")
            app = entry.findtext(".//application", "N/A")
            state = entry.findtext(".//state", "N/A")
            duration = entry.findtext(".//duration", "0")
            bytes_sent = entry.findtext(".//bytes", "0")

            # Format session info
            src_info = f"{src}:{src_port}" if src_port else src
            dst_info = f"{dst}:{dst_port}" if dst_port else dst

            session_info = (
                f"{src_info:22} → {dst_info:22} | "
                f"App: {app:15} | State: {state:10} | "
                f"Duration: {duration}s | Bytes: {bytes_sent}"
            )
            sessions.append(session_info)

        # Build response
        filter_desc = ""
        if source:
            filter_desc += f" from {source}"
        if destination:
            filter_desc += f" to {destination}"
        if application:
            filter_desc += f" app={application}"

        if not sessions:
            return f"No active sessions found{filter_desc}"

        header = f"Active Sessions{filter_desc} (Total: {total_sessions}):"
        # Limit display to first 50 sessions to avoid overwhelming output
        display_sessions = sessions[:50]
        suffix = (
            f"\n... ({len(sessions) - 50} more sessions not shown)" if len(sessions) > 50 else ""
        )

        return header + "\n" + "\n".join(display_sessions) + suffix

    except Exception as e:
        return f"❌ Error querying sessions: {type(e).__name__}: {e}"

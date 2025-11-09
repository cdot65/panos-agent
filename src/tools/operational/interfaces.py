"""Interface operational tools."""

from langchain_core.tools import tool

from src.core.client import get_panos_client
from src.core.panos_api import operational_command


@tool
async def show_interfaces() -> str:
    """Show all network interfaces and their status.

    Returns interface details including:
    - Interface name (ethernet1/1, etc.)
    - IP address/subnet
    - Link status (up/down)
    - Speed/duplex

    Example:
        show_interfaces()
    """
    try:
        client = await get_panos_client()

        # Execute operational command
        cmd = "<show><interface>all</interface></show>"
        result = await operational_command(cmd, client)

        # Parse XML response
        interfaces = []
        for iface in result.findall(".//entry"):
            name = iface.get("name", "Unknown")
            ip_elem = iface.find(".//ip")
            status_elem = iface.find(".//state")
            speed_elem = iface.find(".//speed")
            duplex_elem = iface.find(".//duplex")

            ip = ip_elem.text if ip_elem is not None else "N/A"
            status = status_elem.text if status_elem is not None else "unknown"
            speed = speed_elem.text if speed_elem is not None else "N/A"
            duplex = duplex_elem.text if duplex_elem is not None else "N/A"

            # Format interface info
            interface_info = f"{name}: {ip} | Status: {status}"
            if speed != "N/A" or duplex != "N/A":
                interface_info += f" | {speed}/{duplex}"

            interfaces.append(interface_info)

        if not interfaces:
            return "No interfaces found"

        return "Network Interfaces:\n" + "\n".join(interfaces)

    except Exception as e:
        return f"❌ Error querying interfaces: {type(e).__name__}: {e}"

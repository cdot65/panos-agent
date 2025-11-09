"""Routing table operational tools."""

from langchain_core.tools import tool

from src.core.client import get_panos_client
from src.core.panos_api import operational_command


@tool
async def show_routing_table() -> str:
    """Show the routing table with all routes.

    Returns routing information including:
    - Destination network
    - Next hop
    - Interface
    - Metric
    - Route flags (connected, static, etc.)

    Example:
        show_routing_table()
    """
    try:
        client = await get_panos_client()

        # Execute operational command
        cmd = "<show><routing><route></route></routing></show>"
        result = await operational_command(cmd, client)

        # Parse XML response
        routes = []
        for route in result.findall(".//entry"):
            destination = route.findtext(".//destination", "N/A")
            nexthop = route.findtext(".//nexthop", "N/A")
            interface = route.findtext(".//interface", "N/A")
            metric = route.findtext(".//metric", "N/A")
            flags = route.findtext(".//flags", "")

            # Format route entry
            route_info = f"{destination:18} via {nexthop:15} dev {interface:10} metric {metric}"
            if flags:
                route_info += f" [{flags}]"

            routes.append(route_info)

        if not routes:
            return "No routes found in routing table"

        header = f"{'Destination':<18} {'Next Hop':<19} {'Interface':<14} Metric/Flags"
        separator = "-" * 70
        return f"Routing Table:\n{header}\n{separator}\n" + "\n".join(routes)

    except Exception as e:
        return f"❌ Error querying routing table: {type(e).__name__}: {e}"

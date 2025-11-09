"""Routing table operational tools."""

import json

from langchain_core.tools import tool

from src.core.client import get_panos_client
from src.core.panos_api import operational_command


@tool
async def show_routing_table() -> str:
    """Show the routing table with all routes.

    Automatically detects and queries the appropriate routing engine:
    - Standard routing engine (default)
    - Advanced routing engine (if enabled)

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

        # Try standard routing table first
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

        # If no routes found, try advanced routing engine
        routing_type = "Standard"
        if not routes:
            cmd = "<show><advanced-routing><route></route></advanced-routing></show>"
            result = await operational_command(cmd, client)
            routing_type = "Advanced"

            # Parse advanced routing response (JSON format)
            # Extract JSON from <json> tag
            json_text = result.findtext(".//json", "")

            if json_text:
                try:
                    route_data = json.loads(json_text)

                    # Iterate through VRFs (logical routers)
                    for vrf_name, prefixes in route_data.items():
                        # Iterate through prefixes
                        for prefix, route_list in prefixes.items():
                            # Each prefix can have multiple route entries
                            for route_entry in route_list:
                                destination = route_entry.get("prefix", "N/A")
                                protocol = route_entry.get("protocol", "N/A")
                                metric = route_entry.get("metric", 0)

                                # Get nexthop information
                                nexthops = route_entry.get("nexthops", [])
                                if nexthops:
                                    nexthop_info = nexthops[0]  # Use first nexthop
                                    nexthop_ip = nexthop_info.get("ip", "")
                                    interface = nexthop_info.get("interfaceName", "")

                                    # Handle connected/local routes (no IP)
                                    if not nexthop_ip:
                                        if nexthop_info.get("directlyConnected"):
                                            nexthop_ip = "connected"
                                        else:
                                            nexthop_ip = "local"
                                else:
                                    nexthop_ip = "N/A"
                                    interface = "N/A"

                                # Format route entry with protocol type
                                route_info = f"{destination:18} via {nexthop_ip:15} dev {interface:15} metric {metric}"
                                route_info += f" [{protocol}]"

                                routes.append(route_info)

                except json.JSONDecodeError as e:
                    return f"❌ Error parsing advanced routing table JSON: {e}"

        if not routes:
            return "No routes found in routing table (checked both standard and advanced routing engines)"

        # Format header based on routing engine type
        if routing_type == "Advanced":
            header = f"{'Destination':<18} {'Next Hop':<19} {'Interface':<17} Metric/Protocol"
            separator = "-" * 80
        else:
            header = f"{'Destination':<18} {'Next Hop':<19} {'Interface':<14} Metric/Flags"
            separator = "-" * 70

        engine_note = f" ({routing_type} Routing Engine)" if routing_type == "Advanced" else ""
        return f"Routing Table{engine_note}:\n{header}\n{separator}\n" + "\n".join(routes)

    except Exception as e:
        return f"❌ Error querying routing table: {type(e).__name__}: {e}"

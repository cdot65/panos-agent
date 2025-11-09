"""System resource monitoring tools."""

from langchain_core.tools import tool

from src.core.client import get_panos_client
from src.core.panos_api import operational_command


@tool
async def show_system_resources() -> str:
    """Show system resource usage including CPU, memory, and disk.

    Returns resource utilization details:
    - CPU usage percentage
    - Memory usage (used/total)
    - Disk usage (used/total)
    - Warnings if any resource exceeds 80%

    Example:
        show_system_resources()
    """
    try:
        client = await get_panos_client()

        # Execute operational command
        cmd = "<show><system><resources></resources></system></show>"
        result = await operational_command(cmd, client)

        # Parse resource information
        resources = []
        warnings = []

        # CPU usage
        cpu_elem = result.find(".//cpu-load-average")
        if cpu_elem is not None:
            # Try different possible paths for CPU info
            one_min = cpu_elem.findtext(".//one-minute", "N/A")
            five_min = cpu_elem.findtext(".//five-minute", "N/A")
            fifteen_min = cpu_elem.findtext(".//fifteen-minute", "N/A")

            resources.append(
                f"CPU Load Average: {one_min} (1m), {five_min} (5m), {fifteen_min} (15m)"
            )

            # Check if load average is high (>80% of cores, simplified check)
            try:
                if float(one_min) > 0.8:
                    warnings.append("⚠️  High CPU load detected")
            except (ValueError, TypeError):
                pass

        # Memory usage
        mem_total_elem = result.find(".//mem-total")
        mem_free_elem = result.find(".//mem-free")

        if mem_total_elem is not None and mem_free_elem is not None:
            try:
                mem_total = int(mem_total_elem.text)
                mem_free = int(mem_free_elem.text)
                mem_used = mem_total - mem_free
                mem_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0

                # Convert to human-readable format (KB to GB)
                mem_total_gb = mem_total / (1024 * 1024)
                mem_used_gb = mem_used / (1024 * 1024)

                resources.append(
                    f"Memory: {mem_used_gb:.2f}GB / {mem_total_gb:.2f}GB ({mem_percent:.1f}%)"
                )

                if mem_percent > 80:
                    warnings.append(f"⚠️  High memory usage: {mem_percent:.1f}%")
            except (ValueError, TypeError):
                resources.append("Memory: Unable to parse memory information")

        # Disk usage
        disk_elem = result.find(".//disk-usage")
        if disk_elem is not None:
            for disk in disk_elem.findall(".//entry"):
                disk_name = disk.get("name", "Unknown")
                total = disk.findtext(".//total", "N/A")
                available = disk.findtext(".//available", "N/A")
                used_pct = disk.findtext(".//used-percent", "N/A")

                resources.append(
                    f"Disk ({disk_name}): {used_pct}% used (Total: {total}, Available: {available})"
                )

                # Check disk usage warning
                try:
                    used_percent = float(used_pct.rstrip("%"))
                    if used_percent > 80:
                        warnings.append(f"⚠️  High disk usage on {disk_name}: {used_pct}%")
                except (ValueError, TypeError):
                    pass

        if not resources:
            return "No system resource information available"

        # Build response
        response = "System Resources:\n" + "\n".join(resources)

        if warnings:
            response += "\n\n" + "\n".join(warnings)

        return response

    except Exception as e:
        return f"❌ Error querying system resources: {type(e).__name__}: {e}"

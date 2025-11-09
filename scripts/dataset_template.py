#!/usr/bin/env python3
"""Generate terse dataset template for developers."""

TEMPLATE = """# Quick Dataset Template - Copy & Modify
from langchain_core.messages import HumanMessage

MY_DATASET = [
    # Simple query → expected_tool
    {"name": "List objects", "input": {"messages": [HumanMessage(content="List address objects")]}, 
     "expected_tool": "address_list", "category": "simple_list", "mode": "autonomous"},
    
    # CRUD create → expected_tool
    {"name": "Create object", "input": {"messages": [HumanMessage(content="Create address web-server at 192.168.1.100")]}, 
     "expected_tool": "address_create", "category": "crud_create", "mode": "autonomous"},
    
    # Multi-step → expected_tools (list)
    {"name": "Multi-step", "input": {"messages": [HumanMessage(content="Create server1 at 10.1.1.1, then server2 at 10.1.1.2")]}, 
     "expected_tools": ["address_create", "address_create"], "category": "multi_step", "mode": "autonomous"},
    
    # Error case → expected_behavior
    {"name": "Error handling", "input": {"messages": [HumanMessage(content="Create address bad at 999.999.999.999")]}, 
     "expected_behavior": "error_handling", "category": "error_case", "mode": "autonomous"},
    
    # Workflow → expected_steps
    {"name": "Workflow", "input": {"messages": [HumanMessage(content="workflow: simple_address")]}, 
     "expected_steps": 2, "category": "workflow", "mode": "deterministic"},
]

# Usage: make dataset-create DATASET=my-dataset
# Or: python scripts/create_custom_dataset.py --name my-dataset --examples my_dataset.py
"""

if __name__ == "__main__":
    print(TEMPLATE)

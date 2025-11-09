#!/usr/bin/env python3
"""Helper script to create custom evaluation datasets.

Usage:
    python scripts/create_custom_dataset.py --name my-dataset --examples examples.json
    python scripts/create_custom_dataset.py --name production-tests --interactive
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.evaluate import create_langsmith_dataset, load_langsmith_dataset
from src.core.config import get_settings


def load_examples_from_file(file_path: str) -> List[Dict[str, Any]]:
    """Load examples from JSON file.

    Args:
        file_path: Path to JSON file with examples

    Returns:
        List of example dictionaries
    """
    with open(file_path) as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "examples" in data:
            return data["examples"]
        else:
            raise ValueError(f"Invalid JSON format in {file_path}")


def create_example_interactive() -> Dict[str, Any]:
    """Create example interactively.

    Returns:
        Example dictionary
    """
    print("\n" + "=" * 60)
    print("Create New Example")
    print("=" * 60)

    name = input("Example name: ").strip()
    if not name:
        raise ValueError("Name is required")

    print("\nInput (user query/prompt):")
    prompt = input("> ").strip()
    if not prompt:
        raise ValueError("Prompt is required")

    print("\nExpected behavior:")
    print("  1. Tool name (e.g., 'address_create')")
    print("  2. Multiple tools (comma-separated)")
    print("  3. Expected steps (for workflows)")
    print("  4. Error handling")
    print("  5. None (no specific expectation)")

    choice = input("Choice (1-5): ").strip()

    example = {
        "name": name,
        "input": {"messages": [HumanMessage(content=prompt)]},
        "category": input("Category: ").strip() or "general",
        "mode": input("Mode (autonomous/deterministic) [autonomous]: ").strip() or "autonomous",
    }

    if choice == "1":
        example["expected_tool"] = input("Expected tool name: ").strip()
    elif choice == "2":
        tools = input("Expected tools (comma-separated): ").strip()
        example["expected_tools"] = [t.strip() for t in tools.split(",")]
    elif choice == "3":
        example["expected_steps"] = int(input("Expected steps: ").strip())
    elif choice == "4":
        example["expected_behavior"] = "error_handling"
    # choice == 5: no expectation

    return example


def extend_existing_dataset(dataset_name: str, new_examples: List[Dict[str, Any]]) -> None:
    """Extend existing LangSmith dataset with new examples.

    Args:
        dataset_name: Name of existing dataset
        new_examples: List of new examples to add
    """
    settings = get_settings()
    if not settings.langsmith_api_key:
        raise ValueError("LangSmith API key not configured. Set LANGSMITH_API_KEY in .env")

    from langsmith import Client

    client = Client(api_key=settings.langsmith_api_key)
    dataset = client.read_dataset(dataset_name=dataset_name)

    # Prepare new examples
    inputs_list = []
    outputs_list = []
    metadata_list = []

    for ex in new_examples:
        inputs_list.append(ex["input"])
        outputs_list.append(
            {
                "expected_tool": ex.get("expected_tool"),
                "expected_tools": ex.get("expected_tools"),
                "expected_steps": ex.get("expected_steps"),
                "expected_behavior": ex.get("expected_behavior"),
                "category": ex.get("category", "unknown"),
                "mode": ex.get("mode", "autonomous"),
            }
        )
        metadata_list.append({"name": ex.get("name", "")})

    # Add examples to existing dataset
    client.create_examples(
        inputs=inputs_list,
        outputs=outputs_list,
        dataset_id=dataset.id,
        metadata=metadata_list,
    )

    print(f"\n✅ Added {len(new_examples)} examples to dataset '{dataset_name}'")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Create or extend LangSmith evaluation datasets")
    parser.add_argument(
        "--name",
        required=True,
        help="Dataset name (e.g., 'panos-agent-production-v1')",
    )
    parser.add_argument(
        "--examples",
        help="Path to JSON file with examples",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Create examples interactively",
    )
    parser.add_argument(
        "--extend",
        help="Extend existing dataset (provide dataset name)",
    )
    parser.add_argument(
        "--description",
        help="Dataset description",
    )

    args = parser.parse_args()

    # Load examples
    examples = []
    if args.examples:
        examples = load_examples_from_file(args.examples)
        print(f"Loaded {len(examples)} examples from {args.examples}")
    elif args.interactive:
        print("Interactive mode: Create examples one by one")
        while True:
            try:
                example = create_example_interactive()
                examples.append(example)
                more = input("\nAdd another example? (y/n): ").strip().lower()
                if more != "y":
                    break
            except (ValueError, KeyboardInterrupt) as e:
                if isinstance(e, KeyboardInterrupt):
                    print("\n\nCancelled.")
                    return
                print(f"Error: {e}")
    else:
        parser.error("Must provide --examples or --interactive")

    if not examples:
        print("No examples to add.")
        return

    # Create or extend dataset
    if args.extend:
        extend_existing_dataset(args.extend, examples)
    else:
        description = args.description or f"Custom evaluation dataset: {args.name}"
        create_langsmith_dataset(args.name, examples, description=description)
        print(f"\n✅ Created dataset '{args.name}' with {len(examples)} examples")


if __name__ == "__main__":
    main()

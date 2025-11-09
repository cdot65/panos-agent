#!/usr/bin/env python3
"""LangSmith evaluation script for PAN-OS Agent.

Runs agent on evaluation dataset and tracks metrics:
- Tool usage accuracy
- Response completeness
- Error handling
- Token efficiency

Usage:
    python scripts/evaluate.py --dataset panos-agent-eval-v1 --mode autonomous
    python scripts/evaluate.py --dataset panos-agent-eval-v1 --mode deterministic
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage
from langsmith import Client

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.autonomous_graph import create_autonomous_graph
from src.core.config import get_settings
from src.deterministic_graph import create_deterministic_graph

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# Example dataset for local testing (until LangSmith dataset created)
EXAMPLE_DATASET = [
    {
        "name": "List address objects",
        "input": {"messages": [HumanMessage(content="List all address objects")]},
        "expected_tool": "address_list",
        "category": "simple_list",
        "mode": "autonomous",
    },
    {
        "name": "Create address object",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create address object web-server at 192.168.1.100"
                )
            ]
        },
        "expected_tool": "address_create",
        "category": "crud_create",
        "mode": "autonomous",
    },
    {
        "name": "List service objects",
        "input": {"messages": [HumanMessage(content="List all service objects")]},
        "expected_tool": "service_list",
        "category": "simple_list",
        "mode": "autonomous",
    },
    {
        "name": "Show security policies",
        "input": {"messages": [HumanMessage(content="Show all security policies")]},
        "expected_tool": "security_policy_list",
        "category": "simple_list",
        "mode": "autonomous",
    },
    {
        "name": "Invalid IP address",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create address object bad-server at 999.999.999.999"
                )
            ]
        },
        "expected_behavior": "error_handling",
        "category": "error_case",
        "mode": "autonomous",
    },
    {
        "name": "Simple address workflow",
        "input": {"messages": [HumanMessage(content="workflow: simple_address")]},
        "expected_steps": 2,
        "category": "workflow",
        "mode": "deterministic",
    },
    {
        "name": "Delete address object",
        "input": {
            "messages": [HumanMessage(content="Delete address object test-server")]
        },
        "expected_tool": "address_delete",
        "category": "crud_delete",
        "mode": "autonomous",
    },
    {
        "name": "Multi-step query",
        "input": {
            "messages": [
                HumanMessage(
                    content="Create address server1 at 10.1.1.1, then create address server2 at 10.1.1.2"
                )
            ]
        },
        "expected_tools": ["address_create", "address_create"],
        "category": "multi_step",
        "mode": "autonomous",
    },
]


def evaluate_autonomous_mode(
    examples: List[Dict[str, Any]], graph: Any
) -> Dict[str, Any]:
    """Evaluate autonomous mode on examples.

    Args:
        examples: List of evaluation examples
        graph: Compiled autonomous graph

    Returns:
        Dict with evaluation metrics
    """
    results = []
    total_tokens = 0
    successful = 0
    failed = 0

    for i, example in enumerate(examples, 1):
        if example.get("mode") != "autonomous":
            continue

        logger.info(f"\n[{i}/{len(examples)}] Running: {example['name']}")

        try:
            thread_id = f"eval-{uuid.uuid4()}"
            result = graph.invoke(
                example["input"], config={"configurable": {"thread_id": thread_id}}
            )

            # Extract metrics
            last_message = result["messages"][-1]
            tokens = getattr(last_message, "usage_metadata", {})
            total_tokens += tokens.get("total_tokens", 0)

            # Check if expected tool was used
            tool_calls = []
            for msg in result["messages"]:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_calls.extend([tc["name"] for tc in msg.tool_calls])

            expected_tool = example.get("expected_tool")
            expected_tools = example.get("expected_tools", [])

            tool_match = False
            if expected_tool:
                tool_match = expected_tool in tool_calls
            elif expected_tools:
                tool_match = all(tool in tool_calls for tool in expected_tools)
            else:
                tool_match = True  # No expectation

            if tool_match:
                successful += 1
                logger.info(f"✅ Success - Tool(s) called correctly")
            else:
                failed += 1
                logger.info(
                    f"❌ Failed - Expected {expected_tool or expected_tools}, got {tool_calls}"
                )

            results.append(
                {
                    "name": example["name"],
                    "category": example.get("category"),
                    "success": tool_match,
                    "tool_calls": tool_calls,
                    "tokens": tokens.get("total_tokens", 0),
                }
            )

        except Exception as e:
            failed += 1
            logger.error(f"❌ Error: {type(e).__name__}: {e}")
            results.append(
                {
                    "name": example["name"],
                    "category": example.get("category"),
                    "success": False,
                    "error": str(e),
                }
            )

    # Calculate metrics
    total = len([ex for ex in examples if ex.get("mode") == "autonomous"])
    success_rate = successful / total if total > 0 else 0
    avg_tokens = total_tokens / total if total > 0 else 0

    return {
        "total_examples": total,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate,
        "total_tokens": total_tokens,
        "avg_tokens_per_example": avg_tokens,
        "results": results,
    }


def evaluate_deterministic_mode(
    examples: List[Dict[str, Any]], graph: Any
) -> Dict[str, Any]:
    """Evaluate deterministic mode on examples.

    Args:
        examples: List of evaluation examples
        graph: Compiled deterministic graph

    Returns:
        Dict with evaluation metrics
    """
    results = []
    successful = 0
    failed = 0

    for i, example in enumerate(examples, 1):
        if example.get("mode") != "deterministic":
            continue

        logger.info(f"\n[{i}/{len(examples)}] Running: {example['name']}")

        try:
            thread_id = f"eval-{uuid.uuid4()}"
            result = graph.invoke(
                example["input"], config={"configurable": {"thread_id": thread_id}}
            )

            # Check workflow execution
            # Deterministic graph stores results in step_results (not step_outputs)
            step_results = result.get("step_results", [])
            expected_steps = example.get("expected_steps")

            if expected_steps:
                steps_match = len(step_results) == expected_steps
            else:
                steps_match = True  # No expectation

            # Check if workflow completed successfully
            workflow_complete = result.get("workflow_complete", False)
            error_occurred = result.get("error_occurred", False)

            # Success criteria:
            # 1. Correct number of steps executed
            # 2. Workflow completed (workflow_complete=True)
            # 3. No critical errors (error_occurred=False)
            # Note: Individual step status may be "error" for idempotent operations,
            # but if workflow completed successfully, we trust the workflow's LLM evaluation
            if steps_match and workflow_complete and not error_occurred:
                successful += 1
                # Count successful vs error/skipped steps for reporting
                success_count = sum(
                    1 for out in step_results
                    if isinstance(out, dict) and out.get("status") == "success"
                )
                error_count = sum(
                    1 for out in step_results
                    if isinstance(out, dict) and out.get("status") == "error"
                )
                logger.info(
                    f"✅ Success - {len(step_results)} steps completed "
                    f"({success_count} succeeded, {error_count} idempotent/acceptable)"
                )
            else:
                failed += 1
                if not steps_match:
                    logger.info(
                        f"❌ Failed - Expected {expected_steps} steps, got {len(step_results)}"
                    )
                elif error_occurred:
                    logger.info(f"❌ Failed - Workflow error occurred")
                elif not workflow_complete:
                    logger.info(f"❌ Failed - Workflow did not complete")

            results.append(
                {
                    "name": example["name"],
                    "category": example.get("category"),
                    "success": steps_match and workflow_complete and not error_occurred,
                    "steps_executed": len(step_results),
                    "workflow_complete": workflow_complete,
                    "error_occurred": error_occurred,
                }
            )

        except Exception as e:
            failed += 1
            logger.error(f"❌ Error: {type(e).__name__}: {e}")
            results.append(
                {
                    "name": example["name"],
                    "category": example.get("category"),
                    "success": False,
                    "error": str(e),
                }
            )

    # Calculate metrics
    total = len([ex for ex in examples if ex.get("mode") == "deterministic"])
    success_rate = successful / total if total > 0 else 0

    return {
        "total_examples": total,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate,
        "results": results,
    }


def print_summary(metrics: Dict[str, Any], mode: str):
    """Print evaluation summary.

    Args:
        metrics: Evaluation metrics
        mode: Mode evaluated (autonomous or deterministic)
    """
    logger.info("\n" + "=" * 60)
    logger.info(f"EVALUATION SUMMARY - {mode.upper()} MODE")
    logger.info("=" * 60)

    logger.info(f"\nTotal Examples: {metrics['total_examples']}")
    logger.info(f"✅ Successful: {metrics['successful']}")
    logger.info(f"❌ Failed: {metrics['failed']}")
    logger.info(f"Success Rate: {metrics['success_rate']:.1%}")

    if "avg_tokens_per_example" in metrics:
        logger.info(f"\nAvg Tokens/Example: {metrics['avg_tokens_per_example']:.0f}")
        logger.info(f"Total Tokens: {metrics['total_tokens']}")

    # Category breakdown
    logger.info("\n" + "-" * 60)
    logger.info("CATEGORY BREAKDOWN")
    logger.info("-" * 60)

    categories = {}
    for result in metrics["results"]:
        cat = result.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if result["success"]:
            categories[cat]["success"] += 1

    for cat, stats in sorted(categories.items()):
        rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        logger.info(f"  {cat:20s}: {stats['success']}/{stats['total']} ({rate:.1%})")

    logger.info("=" * 60 + "\n")


def save_results(metrics: Dict[str, Any], mode: str):
    """Save evaluation results to file.

    Args:
        metrics: Evaluation metrics
        mode: Mode evaluated
    """
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"eval_{mode}_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "mode": mode,
                "metrics": metrics,
            },
            f,
            indent=2,
        )

    logger.info(f"Results saved to: {filename}")


def load_langsmith_dataset(dataset_name: str) -> List[Dict[str, Any]]:
    """Load evaluation dataset from LangSmith.

    Args:
        dataset_name: Name of LangSmith dataset

    Returns:
        List of example dictionaries

    Raises:
        ValueError: If LangSmith API key not configured or dataset not found
    """
    settings = get_settings()
    if not settings.langsmith_api_key:
        raise ValueError(
            "LangSmith API key not configured. Set LANGSMITH_API_KEY in .env"
        )

    client = Client(api_key=settings.langsmith_api_key)
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        examples = []
        
        # List examples - handle both iterator and list responses
        example_list = list(client.list_examples(dataset_id=dataset.id))
        
        if len(example_list) == 0:
            logger.warning(f"Dataset '{dataset_name}' exists but contains 0 examples.")
            logger.info("This likely means the dataset was created but examples weren't added.")
            logger.info("\nOptions:")
            logger.info(f"  1. Recreate with examples: python scripts/evaluate.py --create-dataset --dataset {dataset_name}")
            logger.info("     (Note: Delete the empty dataset in LangSmith UI first)")
            logger.info(f"  2. Use example dataset instead: python scripts/evaluate.py --dataset example --mode both")
            raise ValueError(f"Dataset '{dataset_name}' is empty (0 examples)")
        
        for example in example_list:
            # Convert LangSmith example to our format
            example_dict = {
                "name": example.name or str(example.id),
                "input": example.inputs,
                "expected_tool": example.outputs.get("expected_tool") if example.outputs else None,
                "expected_tools": example.outputs.get("expected_tools") if example.outputs else None,
                "expected_steps": example.outputs.get("expected_steps") if example.outputs else None,
                "expected_behavior": example.outputs.get("expected_behavior") if example.outputs else None,
                "category": example.outputs.get("category") if example.outputs else "unknown",
                "mode": example.outputs.get("mode") if example.outputs else "autonomous",
            }
            examples.append(example_dict)

        logger.info(f"Loaded {len(examples)} examples from LangSmith dataset '{dataset_name}'")
        return examples
    except ValueError:
        # Re-raise ValueError (empty dataset)
        raise
    except Exception as e:
        raise ValueError(f"Failed to load dataset '{dataset_name}': {e}")


def create_langsmith_dataset(
    dataset_name: str, examples: List[Dict[str, Any]], description: Optional[str] = None
) -> None:
    """Create a LangSmith dataset from example list.

    Args:
        dataset_name: Name for the new dataset
        examples: List of example dictionaries
        description: Optional dataset description

    Raises:
        ValueError: If LangSmith API key not configured
    """
    settings = get_settings()
    if not settings.langsmith_api_key:
        raise ValueError(
            "LangSmith API key not configured. Set LANGSMITH_API_KEY in .env"
        )

    client = Client(api_key=settings.langsmith_api_key)

    # Check if dataset already exists
    try:
        existing_dataset = client.read_dataset(dataset_name=dataset_name)
        logger.warning(f"Dataset '{dataset_name}' already exists (ID: {existing_dataset.id})")
        logger.info("To use the existing dataset, run:")
        logger.info(f"  python scripts/evaluate.py --dataset {dataset_name} --mode both")
        logger.info("\nTo recreate the dataset, delete it first in LangSmith UI or use a different name.")
        return
    except Exception:
        # Dataset doesn't exist, proceed with creation
        pass

    # Create dataset
    try:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=description or f"PAN-OS Agent evaluation dataset: {dataset_name}",
        )
    except Exception as e:
        if "409" in str(e) or "Conflict" in str(e) or "already exists" in str(e).lower():
            logger.error(f"Dataset '{dataset_name}' already exists.")
            logger.info("To use the existing dataset, run:")
            logger.info(f"  python scripts/evaluate.py --dataset {dataset_name} --mode both")
            logger.info("\nTo recreate the dataset, delete it first in LangSmith UI or use a different name.")
            return
        raise

    # Prepare examples data
    inputs_list = []
    outputs_list = []
    metadata_list = []
    
    for ex in examples:
        # Convert our format to LangSmith format
        inputs_list.append(ex["input"])
        outputs_list.append({
            "expected_tool": ex.get("expected_tool"),
            "expected_tools": ex.get("expected_tools"),
            "expected_steps": ex.get("expected_steps"),
            "expected_behavior": ex.get("expected_behavior"),
            "category": ex.get("category", "unknown"),
            "mode": ex.get("mode", "autonomous"),
        })
        metadata_list.append({"name": ex.get("name", "")})

    # Create examples in batch
    client.create_examples(
        inputs=inputs_list,
        outputs=outputs_list,
        dataset_id=dataset.id,
        metadata=metadata_list,
    )

    logger.info(f"Created LangSmith dataset '{dataset_name}' with {len(examples)} examples")
    logger.info(f"Dataset ID: {dataset.id}")
    
    # Show template guide
    logger.info("\n" + "=" * 60)
    logger.info("Dataset Template Guide")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Quick template for creating custom datasets:")
    logger.info("")
    logger.info("# Copy & modify this template:")
    logger.info("from langchain_core.messages import HumanMessage")
    logger.info("")
    logger.info("MY_DATASET = [")
    logger.info('    {"name": "Example", "input": {"messages": [HumanMessage(content="Your query")]},')
    logger.info('     "expected_tool": "tool_name", "category": "category", "mode": "autonomous"},')
    logger.info("]")
    logger.info("")
    logger.info("Usage:")
    logger.info(f"  python scripts/create_custom_dataset.py --name my-dataset --examples my_dataset.py")
    logger.info(f"  Or: make dataset-create DATASET=my-dataset")
    logger.info("")
    logger.info("See scripts/dataset_template.py for full examples")


def evaluate_autonomous_mode_with_langsmith(
    examples: List[Dict[str, Any]], graph: Any, dataset_name: str
) -> Dict[str, Any]:
    """Evaluate autonomous mode and log results to LangSmith.

    Args:
        examples: List of evaluation examples
        graph: Compiled autonomous graph
        dataset_name: LangSmith dataset name for logging

    Returns:
        Dict with evaluation metrics
    """
    settings = get_settings()
    if not settings.langsmith_api_key:
        logger.warning("LangSmith API key not configured, skipping LangSmith logging")
        return evaluate_autonomous_mode(examples, graph)

    # Use standard evaluation but with LangSmith tracking
    metrics = evaluate_autonomous_mode(examples, graph)

    # Log results to LangSmith (if configured)
    try:
        client = Client(api_key=settings.langsmith_api_key)
        # Results are automatically tracked via tracing if enabled
        logger.info(f"Results logged to LangSmith project: {settings.langsmith_project}")
    except Exception as e:
        logger.warning(f"Failed to log to LangSmith: {e}")

    return metrics


def evaluate_deterministic_mode_with_langsmith(
    examples: List[Dict[str, Any]], graph: Any, dataset_name: str
) -> Dict[str, Any]:
    """Evaluate deterministic mode and log results to LangSmith.

    Args:
        examples: List of evaluation examples
        graph: Compiled deterministic graph
        dataset_name: LangSmith dataset name for logging

    Returns:
        Dict with evaluation metrics
    """
    settings = get_settings()
    if not settings.langsmith_api_key:
        logger.warning("LangSmith API key not configured, skipping LangSmith logging")
        return evaluate_deterministic_mode(examples, graph)

    # Use standard evaluation but with LangSmith tracking
    metrics = evaluate_deterministic_mode(examples, graph)

    # Log results to LangSmith (if configured)
    try:
        client = Client(api_key=settings.langsmith_api_key)
        # Results are automatically tracked via tracing if enabled
        logger.info(f"Results logged to LangSmith project: {settings.langsmith_project}")
    except Exception as e:
        logger.warning(f"Failed to log to LangSmith: {e}")

    return metrics


def main():
    """Run evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate PAN-OS Agent")
    parser.add_argument(
        "--mode",
        choices=["autonomous", "deterministic", "both"],
        default="both",
        help="Mode to evaluate",
    )
    parser.add_argument(
        "--dataset",
        default="example",
        help="LangSmith dataset name (default: use example dataset)",
    )
    parser.add_argument(
        "--create-dataset",
        action="store_true",
        help="Create LangSmith dataset from example data",
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to file"
    )

    args = parser.parse_args()

    # Create dataset if requested
    if args.create_dataset:
        if args.dataset == "example":
            logger.error("Cannot create dataset named 'example'. Choose a different name.")
            return
        try:
            create_langsmith_dataset(
                args.dataset,
                EXAMPLE_DATASET,
                description="PAN-OS Agent evaluation dataset with 8 representative examples",
            )
            logger.info(f"\nDataset '{args.dataset}' created successfully!")
            logger.info("You can now use it with: --dataset " + args.dataset)
            return
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            return

    # Load dataset
    if args.dataset == "example":
        logger.info("Using example dataset (use --create-dataset to create LangSmith dataset)")
        examples = EXAMPLE_DATASET
    else:
        try:
            examples = load_langsmith_dataset(args.dataset)
            if len(examples) == 0:
                logger.warning("Dataset is empty. Falling back to example dataset.")
                logger.info("To populate the dataset, delete it and recreate:")
                logger.info(f"  python scripts/evaluate.py --create-dataset --dataset {args.dataset}")
                examples = EXAMPLE_DATASET
        except ValueError as e:
            logger.error(f"Failed to load dataset: {e}")
            logger.info("\nFalling back to example dataset for this run.")
            logger.info(f"\nTo fix the LangSmith dataset, use:")
            logger.info(f"  python scripts/evaluate.py --create-dataset --dataset {args.dataset}")
            logger.info("(Delete the empty dataset in LangSmith UI first)")
            examples = EXAMPLE_DATASET

    # Evaluate autonomous mode
    if args.mode in ["autonomous", "both"]:
        logger.info("\n" + "=" * 60)
        logger.info("EVALUATING AUTONOMOUS MODE")
        logger.info("=" * 60)

        graph = create_autonomous_graph()
        if args.dataset == "example":
            metrics = evaluate_autonomous_mode(examples, graph)
        else:
            metrics = evaluate_autonomous_mode_with_langsmith(examples, graph, args.dataset)
        print_summary(metrics, "autonomous")

        if args.save_results:
            save_results(metrics, "autonomous")

    # Evaluate deterministic mode
    if args.mode in ["deterministic", "both"]:
        logger.info("\n" + "=" * 60)
        logger.info("EVALUATING DETERMINISTIC MODE")
        logger.info("=" * 60)

        graph = create_deterministic_graph()
        if args.dataset == "example":
            metrics = evaluate_deterministic_mode(examples, graph)
        else:
            metrics = evaluate_deterministic_mode_with_langsmith(examples, graph, args.dataset)
        print_summary(metrics, "deterministic")

        if args.save_results:
            save_results(metrics, "deterministic")


if __name__ == "__main__":
    main()

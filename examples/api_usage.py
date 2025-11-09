"""LangGraph SDK API Usage Examples

Examples of using the deployed PAN-OS Agent via the LangGraph Python SDK.

Prerequisites:
    pip install langgraph-sdk

Environment Variables:
    export LANGSMITH_API_KEY=lsv2_pt_...
    export AGENT_URL=https://panos-agent-prod.api.langsmith.com
"""

import asyncio
import os
from typing import Optional

from langgraph_sdk import get_client


async def example_1_create_thread():
    """Example 1: Create a new conversation thread."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # Create a new thread
    thread = await client.threads.create()
    print(f"✅ Created thread: {thread['thread_id']}")

    return thread["thread_id"]


async def example_2_run_autonomous_agent(thread_id: Optional[str] = None):
    """Example 2: Run agent in autonomous mode with natural language."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # Create thread if not provided
    if not thread_id:
        thread = await client.threads.create()
        thread_id = thread["thread_id"]
        print(f"Created thread: {thread_id}")

    # Run the agent
    print("\n🤖 Running autonomous agent...")
    response = await client.runs.create(
        thread_id=thread_id,
        assistant_id="autonomous",  # Use autonomous graph
        input={
            "messages": [
                {
                    "role": "user",
                    "content": "List all address objects on the firewall",
                }
            ]
        },
    )

    print(f"✅ Run completed: {response['run_id']}")
    print(f"\nResponse:\n{response}")

    return thread_id


async def example_3_stream_autonomous_agent():
    """Example 3: Stream agent responses in real-time."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # Create thread
    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    print(f"\n📡 Streaming from thread: {thread_id}")

    # Stream the response
    async for chunk in client.runs.stream(
        thread_id=thread_id,
        assistant_id="autonomous",
        input={
            "messages": [
                {
                    "role": "user",
                    "content": "Create an address object called web-server with IP 10.0.1.100",
                }
            ]
        },
        stream_mode="updates",  # Stream graph updates
    ):
        print(f"📦 Chunk: {chunk}")


async def example_4_run_deterministic_workflow(thread_id: Optional[str] = None):
    """Example 4: Run predefined deterministic workflow."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # Create thread if not provided
    if not thread_id:
        thread = await client.threads.create()
        thread_id = thread["thread_id"]
        print(f"Created thread: {thread_id}")

    # Run deterministic workflow
    print("\n📋 Running deterministic workflow...")
    response = await client.runs.create(
        thread_id=thread_id,
        assistant_id="deterministic",  # Use deterministic graph
        input={
            "messages": [
                {
                    "role": "user",
                    "content": "workflow: simple_address",  # Workflow name
                }
            ]
        },
    )

    print(f"✅ Workflow completed: {response['run_id']}")
    print(f"\nResponse:\n{response}")

    return thread_id


async def example_5_get_thread_state(thread_id: str):
    """Example 5: Get current state of a thread."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # Get thread state
    state = await client.threads.get_state(thread_id)

    print(f"\n📊 Thread State for {thread_id}:")
    print(f"Messages: {len(state.get('values', {}).get('messages', []))}")
    print(f"Next: {state.get('next', [])}")
    print(f"\nFull state:\n{state}")

    return state


async def example_6_get_thread_history(thread_id: str):
    """Example 6: Get conversation history from a thread."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # Get thread history
    history = await client.threads.get_history(thread_id)

    print(f"\n📜 Thread History for {thread_id}:")
    async for checkpoint in history:
        print(f"\nCheckpoint: {checkpoint['checkpoint_id']}")
        print(f"  Step: {checkpoint['metadata'].get('step', 'N/A')}")
        print(f"  Messages: {len(checkpoint.get('values', {}).get('messages', []))}")


async def example_7_list_all_threads():
    """Example 7: List all threads (for debugging/admin)."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    # List threads
    threads = await client.threads.list()

    print("\n📋 All Threads:")
    for thread in threads:
        print(f"  - {thread['thread_id']}")
        print(f"    Created: {thread.get('created_at', 'N/A')}")
        print(f"    Updated: {thread.get('updated_at', 'N/A')}")


async def example_8_continue_conversation(thread_id: str):
    """Example 8: Continue an existing conversation."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    print(f"\n💬 Continuing conversation in thread: {thread_id}")

    # Send follow-up message
    response = await client.runs.create(
        thread_id=thread_id,
        assistant_id="autonomous",
        input={
            "messages": [
                {
                    "role": "user",
                    "content": "Now show me all service objects",
                }
            ]
        },
    )

    print(f"✅ Response: {response['run_id']}")
    return response


async def example_9_with_custom_model():
    """Example 9: Run agent with custom model selection."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    print(f"\n🎯 Running with Haiku (fast, cheap)...")

    # Run with custom runtime context
    response = await client.runs.create(
        thread_id=thread_id,
        assistant_id="autonomous",
        input={
            "messages": [
                {
                    "role": "user",
                    "content": "List address objects",
                }
            ]
        },
        config={
            "configurable": {
                "context": {
                    "model_name": "claude-haiku-4-5-20251001",
                    "temperature": 0.0,
                }
            }
        },
    )

    print(f"✅ Run completed with Haiku: {response['run_id']}")


async def example_10_error_handling():
    """Example 10: Handle errors gracefully."""
    client = get_client(
        url=os.environ.get("AGENT_URL", "http://localhost:8000"),
        api_key=os.environ.get("LANGSMITH_API_KEY"),
    )

    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    print("\n❌ Testing error handling...")

    try:
        # Send a request that might fail
        response = await client.runs.create(
            thread_id=thread_id,
            assistant_id="autonomous",
            input={
                "messages": [
                    {
                        "role": "user",
                        "content": "Delete address object that-does-not-exist",
                    }
                ]
            },
        )

        print(f"Response: {response}")

    except Exception as e:
        print(f"❌ Caught error: {type(e).__name__}: {e}")
        print("✅ Error handled gracefully")


async def run_all_examples():
    """Run all examples in sequence."""
    print("=" * 80)
    print("PAN-OS Agent API Usage Examples")
    print("=" * 80)

    # Example 1: Create thread
    thread_id = await example_1_create_thread()

    # Example 2: Run autonomous agent
    await example_2_run_autonomous_agent(thread_id)

    # Example 3: Stream responses
    await example_3_stream_autonomous_agent()

    # Example 4: Run deterministic workflow
    workflow_thread = await example_4_run_deterministic_workflow()

    # Example 5: Get thread state
    await example_5_get_thread_state(thread_id)

    # Example 6: Get thread history
    await example_6_get_thread_history(thread_id)

    # Example 7: List all threads
    await example_7_list_all_threads()

    # Example 8: Continue conversation
    await example_8_continue_conversation(thread_id)

    # Example 9: Custom model
    await example_9_with_custom_model()

    # Example 10: Error handling
    await example_10_error_handling()

    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)


async def main():
    """Main entry point - run specific example or all."""
    import sys

    if len(sys.argv) > 1:
        example_num = sys.argv[1]
        examples = {
            "1": example_1_create_thread,
            "2": lambda: example_2_run_autonomous_agent(),
            "3": example_3_stream_autonomous_agent,
            "4": lambda: example_4_run_deterministic_workflow(),
            "5": lambda: example_5_get_thread_state("example-thread-id"),
            "6": lambda: example_6_get_thread_history("example-thread-id"),
            "7": example_7_list_all_threads,
            "8": lambda: example_8_continue_conversation("example-thread-id"),
            "9": example_9_with_custom_model,
            "10": example_10_error_handling,
        }

        if example_num in examples:
            print(f"Running Example {example_num}...")
            await examples[example_num]()
        else:
            print(f"Unknown example: {example_num}")
            print("Available examples: 1-10")
    else:
        # Run all examples
        await run_all_examples()


if __name__ == "__main__":
    asyncio.run(main())

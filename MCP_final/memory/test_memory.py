"""
Test & Verification Suite for Short-Term Memory & Scratchpad
==============================================================
Location: memory/test_memory.py
"""

import sys
from pathlib import Path

# Ensure root directory is in sys.path for imports
sys.path.append(str(Path(__file__).parent.parent))

from memory.short_term import ShortTermMemoryManager


def mock_promote_or_drop_router(evicted_message: dict) -> None:
    """Simulates eviction routing callback."""
    print("\n" + "=" * 65)
    print("🚨 [EVICTION CALLBACK TRIGGERED]")
    print(f"Role:            {evicted_message.get('role', 'unknown').upper()}")
    print(f"Evicted Content: {evicted_message.get('content')}")
    print("Action:          Passing message to Promote-or-Drop Router...")
    print("=" * 65 + "\n")


def run_memory_demo():
    print("\n==================================================")
    print("  RUNNING SHORT-TERM MEMORY & SCRATCHPAD TEST     ")
    print("==================================================\n")

    # 1. Initialize Memory Manager (Buffer size = 2 turns)
    memory = ShortTermMemoryManager(
        max_buffer_turns=2,
        eviction_callback=mock_promote_or_drop_router
    )

    # 2. Populate Scratchpad State with ACTUAL values (not '...')
    print("---> 1. Populating Scratchpad State...")
    memory.set_goal(
        goal="Verify Medical Exemption & Winter Moratorium",
        subgoal="Check waiver active status and freeze rules for Account #104",
        plan=[
            "1. Query customer account waiver status",
            "2. Retrieve state winter disconnection policy",
            "3. Determine disconnection protection eligibility"
        ]
    )
    memory.update_account_context(
        account_id="104",
        metadata={"service_type": "Electric & Gas", "zip_code": "60611", "status": "Active"}
    )

    # 3. Add Conversation Turns
    print("---> 2. Adding Conversation Turns...")
    memory.add_message("user", "My doctor filed a medical exemption last week. Is Account #104 protected?")
    memory.add_message("assistant", "Let me check the database records for Account #104.")

    print("\n[Adding Turn 3 - Triggers Buffer Overflow & Eviction]")
    memory.add_message("user", "Also, can you check if there is an active winter moratorium in zip code 60611?")

    # 4. Verify Final State Sent to LLM Context Payload
    print("\n---> 3. Verifying Final LLM Context Payload...")
    full_payload = memory.get_full_context_messages()
    
    for idx, msg in enumerate(full_payload):
        role = msg["role"].upper()
        content = msg["content"]
        print(f"--- Context Payload Item {idx + 1} [{role}] ---")
        print(content)
        print("-" * 50)

    # 5. Programmatic Assertions
    assert memory.scratchpad["account_id"] == "104", "Account ID was lost!"
    assert len(memory.message_buffer) == 2, "Buffer size exceeded capacity!"
    print("\n✅ ALL PROGRAMMATIC ASSERTIONS PASSED!\n")


if __name__ == "__main__":
    run_memory_demo()
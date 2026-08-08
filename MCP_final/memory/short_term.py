"""
Short-Term Memory Manager
=========================
Location: memory/short_term.py

Manages active conversation history, applies Zone-Based Pruning for LLM context,
and routes evicted turns through the Promote-or-Drop Router into Episodic Memory.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure root directory is in sys.path
sys.path.append(str(Path(__file__).parent.parent))

from memory.strategies import ContextStrategies
from memory.router import PromoteOrDropRouter


class ShortTermMemoryManager:
    """
    Stateful buffer for managing real-time agent context window and eviction callbacks.
    """

    def __init__(self, max_active_turns: int = 6, scratchpad_header: str = ""):
        self.max_active_turns = max_active_turns
        self.scratchpad_header = scratchpad_header
        self.active_buffer: List[Dict[str, Any]] = []
        self.router = PromoteOrDropRouter()

    def add_message(
        self, 
        role: str, 
        content: str, 
        session_id: str = "SESSION_104", 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Appends a message to the active buffer. If the buffer exceeds max_active_turns,
        evicted turns are automatically sent to the router for Episodic Memory evaluation.
        """
        message = {"role": role, "content": content}
        self.active_buffer.append(message)

        # Check for eviction threshold
        if len(self.active_buffer) > self.max_active_turns:
            evicted_msg = self.active_buffer.pop(0)
            print(f"\n⚡ [BUFFER EVICTION TRIGGERED]: Buffer size exceeded {self.max_active_turns} turns.")
            self.router.evaluate_and_route(
                evicted_msg=evicted_msg,
                session_id=session_id,
                active_metadata=metadata
            )

    def get_pruned_context(self) -> List[Dict[str, Any]]:
        """
        Renders the active buffer into an optimized payload ready for the LLM using Strategy 4 (Zone-Based Pruning).
        """
        # Mask tool outputs first
        masked_buffer = ContextStrategies.apply_observation_masking(self.active_buffer, max_tool_chars=100)
        
        # Apply Zone-Based Pruning
        return ContextStrategies.apply_zone_based_pruning(
            messages=masked_buffer,
            scratchpad_header=self.scratchpad_header,
            max_tool_chars=100,
            recent_dialogue_window=self.max_active_turns
        )

    def update_scratchpad(self, new_header: str) -> None:
        """Updates the protected Zone 1 Scratchpad content."""
        self.scratchpad_header = new_header


# =============================================================================
# LOCAL SANITY TEST FOR SHORT-TERM MEMORY MANAGER
# =============================================================================
if __name__ == "__main__":
    print("\n==================================================")
    print("  TESTING SHORT-TERM MEMORY & ROUTER INTEGRATION  ")
    print("==================================================")

    scratchpad = "=== PROTECTED SCRATCHPAD ===\nAccount ID: 104\nStatus: Pending Moratorium Review"
    mem_mgr = ShortTermMemoryManager(max_active_turns=6, scratchpad_header=scratchpad)

    # Push 7 messages to trigger 1 eviction
    turns = [
        ("user", "My doctor filed medical exemption MED-88391 for Account #104."),
        ("assistant", "Checking DB for waiver verification..."),
        ("tool", "SQL_EXECUTION_LOG: SELECT * FROM waivers WHERE account_id=104"),
        ("assistant", "Waiver verified. Checking grid weather status..."),
        ("tool", "SMART_GRID_TELEMETRY: TEMP=18F STATUS=COLD_SNAP_ACTIVE"),
        ("user", "What is my balance?"),
        ("assistant", "Your current balance is $450.25 across overdue invoices."),
    ]

    for role, content in turns:
        mem_mgr.add_message(role, content, session_id="SESSION_CHI_104")

    print("\n" + "=" * 60)
    print("               RENDERED LLM CONTEXT PAYLOAD               ")
    print("=" * 60)
    payload = mem_mgr.get_pruned_context()
    for idx, msg in enumerate(payload, 1):
        print(f"[{idx}] Role: {msg['role']:<10} | Content: {msg['content'][:80]}...")

    print("\n✅ SHORT-TERM MEMORY INTEGRATION TEST COMPLETE!\n")
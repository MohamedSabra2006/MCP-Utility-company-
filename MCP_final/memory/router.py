"""
Promote-or-Drop Eviction Router (Episodic Memory Store)
======================================================
Location: memory/router.py

Evaluates short-term memory evicted turns. If an evicted turn contains 
event-critical interaction details, it is PROMOTED into an Episodic Memory 
Record with an explicit promotion justification. Otherwise, transient chat 
turns are DROPPED with an explicit drop reason.
"""

import re
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class EpisodicMemoryRecord:
    """
    Represents a structured Episodic Memory entry.
    Stores interaction history as discrete, contextual event episodes.
    """
    episode_id: str
    timestamp: str
    role: str
    event_type: str
    event_summary: str
    promotion_reason: str
    raw_snippet: str
    context_metadata: Dict[str, Any]


class PromoteOrDropRouter:
    """
    Router that intercepts evicted messages from short-term memory buffer
    and routes important interaction events into the Episodic Memory Store.
    """

    def __init__(self):
        # Dedicated Episodic Memory Store (List of EpisodicMemoryRecord)
        self.episodic_memory_store: List[EpisodicMemoryRecord] = []

    def evaluate_and_route(
        self, 
        evicted_msg: Dict[str, Any], 
        session_id: str = "SESSION_104",
        active_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[EpisodicMemoryRecord], str]:
        """
        Evaluates an evicted message. Promotes event-rich turns to Episodic Memory
        or drops transient chatter, logging the explicit rationale for the decision.

        :param evicted_msg: Raw dictionary of the evicted turn {"role": ..., "content": ...}.
        :param session_id: Identifier for the current conversation episode.
        :param active_metadata: Current session context metadata.
        :return: Tuple of (EpisodicMemoryRecord or None, decision_reason_string).
        """
        role = evicted_msg.get("role", "").lower()
        content = evicted_msg.get("content", "")
        metadata = active_metadata or {}

        # Rule 1: Check for explicit Assistant dialogue without tool calls
        if role == "assistant" and "TOOL" not in content and "QUERY" not in content:
            reason = "Dropped: Routine assistant conversational response containing no tool outputs or state changes."
            print(f"🗑️ [DROP]: {reason}")
            return None, reason

        # Rule 2: Evaluate for Episodic Event Triggers and determine promotion reason
        event_type, promotion_reason = self._detect_event_type_and_reason(content)

        if event_type and promotion_reason:
            # --- PROMOTE TO EPISODIC MEMORY ---
            record = EpisodicMemoryRecord(
                episode_id=session_id,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                role=role,
                event_type=event_type,
                event_summary=self._generate_event_summary(content, event_type),
                promotion_reason=promotion_reason,
                raw_snippet=content[:150] + "..." if len(content) > 150 else content,
                context_metadata=metadata.copy()
            )
            
            # Save into Episodic Store
            self.episodic_memory_store.append(record)
            print(f"🚀 [PROMOTE -> EPISODIC MEMORY]: {event_type}")
            print(f"   └─ Reason: {promotion_reason}")
            return record, promotion_reason
        else:
            # --- DROP TRANSIENT CHATTER ---
            reason = "Dropped: User message identified as transient conversational filler with no critical metadata."
            print(f"🗑️ [DROP]: {reason}")
            return None, reason

    def _detect_event_type_and_reason(self, content: str) -> Tuple[Optional[str], Optional[str]]:
        """Identifies key episodic event types and constructs the promotion rationale."""
        # Medical / Waiver Filing Events
        if re.search(r'medical|waiver|doctor|exemption|MED-\d+', content, re.IGNORECASE):
            return (
                "EPISODE_WAIVER_SUBMISSION_EVENT",
                "Promoted: Contains customer medical exemption reference or waiver submission details."
            )

        # Moratorium / Zip Code Policy Inquiries
        if re.search(r'moratorium|cold snap|zip|60611|disconnection', content, re.IGNORECASE):
            return (
                "EPISODE_POLICY_INQUIRY_EVENT",
                "Promoted: Contains cold-snap moratorium inquiry or zip-code disconnection protection constraints."
            )

        # Billing / Invoice Query Events
        if re.search(r'balance|invoice|overdue|billing|paid', content, re.IGNORECASE):
            return (
                "EPISODE_BILLING_LOOKUP_EVENT",
                "Promoted: Contains billing ledger actions, overdue balance inquiries, or payment state."
            )

        # Critical System / Database Executions
        if "SQL_EXECUTION_LOG" in content or "SMART_GRID" in content:
            return (
                "EPISODE_TOOL_EXECUTION_EVENT",
                "Promoted: Contains critical system execution logs, SQL queries, or sensor telemetry dumps."
            )

        return None, None

    def _generate_event_summary(self, content: str, event_type: str) -> str:
        """Generates a concise summary for the episodic record."""
        clean_text = content.replace("\n", " ")
        if len(clean_text) > 100:
            return f"{event_type}: {clean_text[:100]}..."
        return f"{event_type}: {clean_text}"

    def get_episodic_history(self) -> List[Dict[str, Any]]:
        """Returns all promoted episodic records as dictionary objects including the promotion reason."""
        return [
            {
                "episode_id": r.episode_id,
                "timestamp": r.timestamp,
                "role": r.role,
                "event_type": r.event_type,
                "summary": r.event_summary,
                "promotion_reason": r.promotion_reason,
                "snippet": r.raw_snippet
            }
            for r in self.episodic_memory_store
        ]


# =============================================================================
# LOCAL SANITY TEST FOR ROUTER MODULE WITH REASONS
# =============================================================================
if __name__ == "__main__":
    print("\n==================================================")
    print("  TESTING PROMOTE-OR-DROP ROUTER (WITH REASONS)   ")
    print("==================================================\n")

    router = PromoteOrDropRouter()
    session_id = "SESSION_CHI_104"
    metadata = {"account_id": "104", "zip_code": "60611"}

    # Simulate 3 evicted turns passing through the router callback
    evicted_turn_1 = {
        "role": "user",
        "content": "My doctor filed a medical exemption last week under ref MED-88391. Is Account #104 protected?"
    }
    evicted_turn_2 = {
        "role": "assistant",
        "content": "Let me check the database records for Account #104."
    }
    evicted_turn_3 = {
        "role": "user",
        "content": "Okay thanks, I will wait."
    }

    print("--- Processing Evicted Turn 1 ---")
    router.evaluate_and_route(evicted_turn_1, session_id, metadata)

    print("\n--- Processing Evicted Turn 2 ---")
    router.evaluate_and_route(evicted_turn_2, session_id, metadata)

    print("\n--- Processing Evicted Turn 3 ---")
    router.evaluate_and_route(evicted_turn_3, session_id, metadata)

    print("\n" + "=" * 80)
    print("                FINAL EPISODIC MEMORY STORE CONTENTS                ")
    print("=" * 80)
    for record in router.get_episodic_history():
        print(f"• [{record['timestamp']}] Session: {record['episode_id']}")
        print(f"  Event Type:       {record['event_type']}")
        print(f"  Promotion Reason: {record['promotion_reason']}")
        print(f"  Summary:          {record['summary']}")
        print(f"  Raw Snippet:      {record['snippet']}\n")

    print("✅ EPISODIC ROUTER TEST COMPLETED SUCCESSFULLY WITH REASON LOGGING!\n")
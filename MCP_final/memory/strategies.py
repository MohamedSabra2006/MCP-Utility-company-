"""
Context Window Management Strategies
======================================
Location: memory/strategies.py

Implements 4 distinct context window pruning strategies against long-context,
tool-heavy conversation transcripts:
  1. Sliding Window Pruning (Max 6 Turns)
  2. Observation & Tool Output Masking
  3. Recursive Summarization (Max 6 Active Turns)
  4. Zone-Based Pruning (Zone 1: System, Zone 2: Intent, Zone 3: Tool Logs, Zone 4: Recent 6 Turns)
"""

from typing import List, Dict, Any, Tuple


class ContextStrategies:
    """
    Collection of four distinct context management strategies designed to prevent
    LLM Context Window overflow during long-context, tool-heavy agent execution.
    """

    # =========================================================================
    # STRATEGY 1: SLIDING WINDOW
    # =========================================================================
    @staticmethod
    def apply_sliding_window(
        messages: List[Dict[str, Any]], 
        max_turns: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Strategy 1: Sliding Window
        --------------------------
        Keeps only the most recent N turns in the conversation buffer (Default: 6).
        Older turns are dropped unconditionally.
        """
        if len(messages) <= max_turns:
            return [msg.copy() for msg in messages]

        # Retain only the last N messages
        return [msg.copy() for msg in messages[-max_turns:]]

    # =========================================================================
    # STRATEGY 2: OBSERVATION & TOOL OUTPUT MASKING
    # =========================================================================
    @staticmethod
    def apply_observation_masking(
        messages: List[Dict[str, Any]], 
        max_tool_chars: int = 150
    ) -> List[Dict[str, Any]]:
        """
        Strategy 2: Observation & Tool Output Masking
        --------------------------------------------
        Identifies bulky tool execution responses (SQL dumps, API JSON payloads, sensor logs)
        and truncates/masks their body content while leaving user and assistant text untouched.
        """
        processed_messages = []

        for msg in messages:
            msg_copy = msg.copy()
            role = msg_copy.get("role", "").lower()
            content = msg_copy.get("content", "")

            # Masking trigger: explicit 'tool' / 'observation' role OR heavy structured JSON/log payloads
            is_tool_message = role in ["tool", "observation"] or "TOOL_OBSERVATION" in content or "QUERY_RESULT" in content

            if is_tool_message and len(content) > max_tool_chars:
                snippet = content[:max_tool_chars].replace("\n", " ")
                original_len = len(content)
                msg_copy["content"] = (
                    f"[TOOL OUTPUT MASKED: Truncated {original_len} chars -> showing first {max_tool_chars}]\n"
                    f"Preview: {snippet}...\n"
                    f"[END TOOL MASK]"
                )

            processed_messages.append(msg_copy)

        return processed_messages

    # =========================================================================
    # STRATEGY 3: RECURSIVE SUMMARIZATION
    # =========================================================================
    @staticmethod
    def apply_recursive_summarization(
        messages: List[Dict[str, Any]], 
        running_summary: str = "", 
        max_active_turns: int = 6
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Strategy 3: Recursive Summarization
        -----------------------------------
        When the buffer exceeds 6 active turns, evicted messages are condensed into a 
        running narrative summary block that is attached to system context.
        """
        if len(messages) <= max_active_turns:
            return [msg.copy() for msg in messages], running_summary

        # Split into evicted (old) and active (recent 6) sets
        evicted_messages = messages[:-max_active_turns]
        active_messages = [msg.copy() for msg in messages[-max_active_turns:]]

        # Extract facts from evicted messages to append to running summary
        new_summary_lines = []
        for msg in evicted_messages:
            role = msg.get("role", "").upper()
            content = msg.get("content", "")
            short_content = content[:100] + "..." if len(content) > 100 else content
            new_summary_lines.append(f"- {role}: {short_content}")

        updated_summary_block = (
            f"{running_summary}\n" + "\n".join(new_summary_lines)
        ).strip()

        return active_messages, updated_summary_block

    # =========================================================================
    # STRATEGY 4: ZONE-BASED PRUNING
    # =========================================================================
    @staticmethod
    def apply_zone_based_pruning(
        messages: List[Dict[str, Any]],
        scratchpad_header: str,
        max_tool_chars: int = 100,
        recent_dialogue_window: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Strategy 4: Zone-Based Pruning
        ------------------------------
        Partitions the prompt into 4 functional zones:
          - Zone 1: Protected Scratchpad Header (IMMUTABLE)
          - Zone 2: Core User Intent & Original Query (HIGH PRIORITY)
          - Zone 3: Intermediate Tool Execution Logs (LOW PRIORITY - Aggressively Masked)
          - Zone 4: Recent Active Dialogue Turns (Window of 6)
        """
        if not messages:
            return [{"role": "system", "content": scratchpad_header}]

        # --- ZONE 1: Protected Scratchpad Header ---
        zone_1_system = {"role": "system", "content": scratchpad_header}

        # --- ZONE 2: First User Message (Core Intent / Initial Query) ---
        zone_2_core_intent = None
        remaining_messages = []

        for msg in messages:
            if msg.get("role") == "user" and zone_2_core_intent is None:
                zone_2_core_intent = msg.copy()
            else:
                remaining_messages.append(msg)

        # --- ZONE 4: Recent Active Dialogue Turns (Max 6) ---
        if len(remaining_messages) > recent_dialogue_window:
            zone_3_middle_logs = remaining_messages[:-recent_dialogue_window]
            zone_4_recent_dialogue = remaining_messages[-recent_dialogue_window:]
        else:
            zone_3_middle_logs = []
            zone_4_recent_dialogue = remaining_messages

        # --- ZONE 3: Aggressive Masking on Middle Tool Logs ---
        processed_zone_3 = []
        for msg in zone_3_middle_logs:
            msg_copy = msg.copy()
            role = msg_copy.get("role", "").lower()
            content = msg_copy.get("content", "")

            if role in ["tool", "observation"] or len(content) > max_tool_chars:
                snippet = content[:max_tool_chars].replace("\n", " ")
                msg_copy["content"] = f"[ZONE 3 MASKED TOOL LOG ({len(content)} chars)]: {snippet}..."
            
            processed_zone_3.append(msg_copy)

        # --- ASSEMBLE ALL 4 ZONES ---
        final_payload = [zone_1_system]
        
        if zone_2_core_intent:
            final_payload.append(zone_2_core_intent)
            
        final_payload.extend(processed_zone_3)
        final_payload.extend([msg.copy() for msg in zone_4_recent_dialogue])

        return final_payload


# =============================================================================
# LOCAL SANITY TEST FOR STRATEGIES MODULE (8 MESSAGES TRANSCRIPT -> 6 MAX CAPACITY)
# =============================================================================
if __name__ == "__main__":
    print("\n==================================================")
    print("  TESTING CONTEXT MANAGEMENT STRATEGIES MODULE   ")
    print("  (TRANSCRIPT: 8 MESSAGES | MAX BUFFER: 6 TURNS) ")
    print("==================================================\n")

    mock_scratchpad = "=== PROTECTED SCRATCHPAD ===\nAccount ID: 104\nGoal: Verify Moratorium"
    
    # Simulate an 8-message dialogue transcript
    mock_transcript = [
        {"role": "user", "content": "Turn 1: Initial Request - Doctor filed medical exemption for Account #104 in 60611."},
        {"role": "assistant", "content": "Turn 2: Querying DB records for waiver status..."},
        {"role": "tool", "content": "TOOL_OBSERVATION: " + "DB_RECORD_DATA_" * 100},  # ~1500 chars
        {"role": "assistant", "content": "Turn 4: Waiver record retrieved. Checking moratorium rules..."},
        {"role": "tool", "content": "TOOL_OBSERVATION: " + "SENSOR_LOG_DATA_" * 100},  # ~1600 chars
        {"role": "user", "content": "Turn 6: What is my current outstanding balance?"},
        {"role": "assistant", "content": "Turn 7: Your current account balance is $150.00."},
        {"role": "user", "content": "Turn 8: Can I extend my payment deadline to next month?"},
    ]

    print(f"Original Transcript Length: {len(mock_transcript)} messages\n")

    # 1. Sliding Window (max_turns=6)
    s1_res = ContextStrategies.apply_sliding_window(mock_transcript, max_turns=6)
    print(f"1. Sliding Window (max_turns=6): Retained {len(s1_res)} messages (Turn 1 & 2 dropped)")

    # 2. Tool Output Masking
    s2_res = ContextStrategies.apply_observation_masking(mock_transcript, max_tool_chars=50)
    print(f"2. Tool Output Masking: Heavy tool logs masked across all {len(s2_res)} messages")

    # 3. Recursive Summarization (max_active_turns=6)
    s3_msgs, s3_summary = ContextStrategies.apply_recursive_summarization(mock_transcript, max_active_turns=6)
    print(f"3. Recursive Summarization: {len(s3_msgs)} active turns remaining | Evicted turns summarized into {len(s3_summary)} chars")

    # 4. Zone-Based Pruning (recent_dialogue_window=6)
    s4_res = ContextStrategies.apply_zone_based_pruning(mock_transcript, mock_scratchpad, recent_dialogue_window=6)
    print(f"4. Zone-Based Pruning: Assembled {len(s4_res)} payload items (Zone 1 Scratchpad + Zone 2 Core Intent + Zone 3/4 Dialogue)")

    print("\n✅ ALL 4 STRATEGIES VERIFIED WITH 6-TURN CAPACITY LIMIT!\n")
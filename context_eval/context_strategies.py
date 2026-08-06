"""
Context Window Management Strategies for NCEDC Agent
Implements:
1. Sliding Window
2. Observation / Tool-Output Masking
3. Recursive Summarization
4. Zone-Based Pruning
"""

import json
from typing import List, Dict, Any

class ContextManager:
    @staticmethod
    def sliding_window(messages: List[Dict[str, Any]], window_size: int = 10) -> List[Dict[str, Any]]:
        """Strategy 1: Retains only the last N messages."""
        return messages[-window_size:] if len(messages) > window_size else messages

    @staticmethod
    def observation_masking(messages: List[Dict[str, Any]], keep_last_tools: int = 3) -> List[Dict[str, Any]]:
        """
        Strategy 2: Masks/truncates older tool outputs to save tokens,
        preserving recent tool results and full user/assistant dialogue.
        """
        masked = []
        tool_count = 0
        
        # Traverse backwards to keep last N tool outputs intact
        for msg in reversed(messages):
            if msg.get("role") == "tool" or "tool_calls" in msg:
                tool_count += 1
                if tool_count > keep_last_tools:
                    # Truncate content
                    masked_msg = msg.copy()
                    masked_msg["content"] = "[TOOL OUTPUT MASKED / TRUNCATED FOR CONTEXT OPTIMIZATION]"
                    masked.append(masked_msg)
                else:
                    masked.append(msg)
            else:
                masked.append(msg)
                
        return list(reversed(masked))

    @staticmethod
    def recursive_summarization(messages: List[Dict[str, Any]], trigger_len: int = 15) -> List[Dict[str, Any]]:
        """
        Strategy 3: Summarizes turns older than trigger_len into a compact summary block.
        """
        if len(messages) <= trigger_len:
            return messages
            
        older_messages = messages[:-trigger_len]
        recent_messages = messages[-trigger_len:]
        
        # Extract key points from older messages (Simulated summary representation)
        summary_lines = []
        for m in older_messages:
            content = str(m.get("content", ""))
            if "dialysis" in content.lower() or "medical" in content.lower() or "oxygen" in content.lower():
                summary_lines.append(f"Critical Note Found: {content[:100]}...")
            elif m.get("role") == "user":
                summary_lines.append(f"User Query: {content[:50]}")

        summary_text = "SUMMARY OF EARLIER TURNS:\n" + ("\n".join(summary_lines) if summary_lines else "General administrative setup and queries.")
        
        summary_block = {
            "role": "system",
            "content": summary_text
        }
        
        return [summary_block] + recent_messages

    @staticmethod
    def zone_based_pruning(
        system_prompt: Dict[str, Any],
        scratchpad: Dict[str, Any],
        history: List[Dict[str, Any]],
        max_history_turns: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Strategy 4: Preserves Zone 1 (System Prompt) and Zone 2 (Scratchpad/Current Plan)
        unconditionally, while applying strict pruning to Zone 3 (Message History).
        """
        zone_1 = [system_prompt]
        zone_2 = [{
            "role": "system",
            "content": f"CURRENT AGENT SCRATCHPAD / WORKING GOAL:\n{json.dumps(scratchpad)}"
        }] if scratchpad else []
        
        zone_3 = history[-max_history_turns:] if len(history) > max_history_turns else history
        
        return zone_1 + zone_2 + zone_3
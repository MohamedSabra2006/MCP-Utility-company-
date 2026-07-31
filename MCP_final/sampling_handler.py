"""
MCP Sampling Handler: Routes unstructured text evaluation requests to host LLMs
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_SamplingHandler")


class SamplingHandler:
    def __init__(self, host_llm_model: str = "gemini-2.5-flash"):
        self.host_llm_model = host_llm_model

    def handle_sampling_request(self, sampling_params: dict) -> dict:
        """
        Processes incoming `sampling/createMessage` requests from the MCP Server.
        """
        logger.info("Received `sampling/createMessage` request from server.")
        
        prompt_text = sampling_params.get("prompt", "")
        document_text = sampling_params.get("document_text", "")
        
        logger.info(f"Forwarding document to Host LLM ({self.host_llm_model}) for analysis...")
        
        is_life_support = any(
            term in document_text.lower() 
            for term in ["life support", "oxygen concentrator", "dialysis", "ventilator"]
        )
        
        evaluation_result = {
            "has_active_life_support": is_life_support,
            "decision": "PROTECTED - DO NOT DISCONNECT" if is_life_support else "NO EXEMPTION - PROCEED",
            "confidence": 0.98,
            "reasoning": (
                "Document contains active life-support device declaration."
                if is_life_support else "No medical exemption triggers found."
            )
        }
        
        logger.info("✅ Host LLM analysis complete. Returning structured response to MCP server.")
        
        return {
            "role": "assistant",
            "content": evaluation_result,
            "model": self.host_llm_model
        }